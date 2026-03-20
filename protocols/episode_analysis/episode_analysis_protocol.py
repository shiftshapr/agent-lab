"""
Episode Analysis Protocol
Processes episode transcripts into structured investigative records for inscription.
Supports global ledger continuation across episodes.

Projects: projects/monuments/{project_name}/
  - brief/       Project briefing (protocol context)
  - templates/   Output format template
  - input/       Raw episode transcripts
  - output/      Structured episode analyses
  - logs/        Run logs
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Neo4j context injection (optional)
try:
    from protocols.episode_analysis.phase1_validation import validate_phase1
except ImportError:
    validate_phase1 = None  # type: ignore[misc, assignment]

try:
    from protocols.episode_analysis.neo4j_context import get_episode_context
except ImportError:
    def get_episode_context(episode_num: int) -> str:
        return ""

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

AGENT_LAB_ROOT = Path(__file__).parent.parent.parent
PROTOCOLS_DIR  = Path(__file__).parent
PROJECTS_DIR   = AGENT_LAB_ROOT / "projects" / "monuments"


def get_project_path(project: str) -> Path:
    path = PROJECTS_DIR / project
    if not path.is_dir():
        raise FileNotFoundError(f"Project not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Ledger state (cross-episode numbering)
# ---------------------------------------------------------------------------

ID_PATTERNS = {
    "artifact": re.compile(r"A-(\d+(?:\.\d+)?)"),
    "claim":    re.compile(r"C-(\d+)"),
    "node":     re.compile(r"N-(\d+)"),
}


def scan_output_for_ids_neo4j() -> dict[str, float] | None:
    """Query Neo4j for highest A-, C-, N- IDs. Returns None if Neo4j unavailable."""
    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        return None
    
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return None
    
    try:
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "openclaw")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        driver.verify_connectivity()
        
        highest = {"artifact_bundle": 999, "claim": 1000, "node": 0, "node_investigation": 1000}
        
        with driver.session() as session:
            # Get max artifact family ID
            result = session.run(
                "MATCH (af:ArtifactFamily) "
                "RETURN max(toInteger(substring(af.id, 2))) AS max_id"
            )
            record = result.single()
            if record and record["max_id"] is not None:
                highest["artifact_bundle"] = record["max_id"]
            
            # Get max claim ID
            result = session.run(
                "MATCH (c:Claim) "
                "RETURN max(toInteger(substring(c.id, 2))) AS max_id"
            )
            record = result.single()
            if record and record["max_id"] is not None:
                highest["claim"] = record["max_id"]
            
            # Get max person node ID (N-1 to N-999)
            result = session.run(
                "MATCH (p:Person) "
                "WITH toInteger(substring(p.id, 2)) AS node_num "
                "WHERE node_num < 1000 "
                "RETURN max(node_num) AS max_id"
            )
            record = result.single()
            if record and record["max_id"] is not None:
                highest["node"] = record["max_id"]
            
            # Get max investigation target node ID (N-1000+)
            result = session.run(
                "MATCH (it:InvestigationTarget) "
                "WITH toInteger(substring(it.id, 2)) AS node_num "
                "WHERE node_num >= 1000 "
                "RETURN max(node_num) AS max_id"
            )
            record = result.single()
            if record and record["max_id"] is not None:
                highest["node_investigation"] = record["max_id"]
        
        driver.close()
        return highest
    
    except Exception as e:
        print(f"[episode-analysis] Neo4j query failed: {e}")
        return None


def scan_output_for_ids_regex(output_dir: Path) -> dict[str, float]:
    """Scan episode output files for highest A-, C-, N- IDs. Excludes cross_episode_*.md."""
    highest = {"artifact_bundle": 999, "claim": 1000, "node": 0, "node_investigation": 1000}

    for path in output_dir.glob("episode_*.md"):
        text = path.read_text(encoding="utf-8")
        for kind, pattern in ID_PATTERNS.items():
            for m in pattern.finditer(text):
                try:
                    raw = m.group(1)
                    if kind == "artifact":
                        # Artifacts: A-1001.01, A-1001.02, ... Bundle = integer part.
                        bundle = int(float(raw)) if "." in raw else int(raw)
                        if bundle > highest["artifact_bundle"]:
                            highest["artifact_bundle"] = bundle
                        continue
                    val = int(raw)
                    if kind == "node":
                        if val >= 1000:
                            if val > highest["node_investigation"]:
                                highest["node_investigation"] = val
                            continue
                    if val > highest[kind]:
                        highest[kind] = val
                except (ValueError, TypeError):
                    pass

    return highest


def scan_output_for_ids(output_dir: Path) -> dict[str, float]:
    """
    Get highest A-, C-, N- IDs from Neo4j if available, otherwise scan markdown files.
    Neo4j is preferred when NEO4J_URI env var is set.
    """
    # Try Neo4j first
    neo4j_result = scan_output_for_ids_neo4j()
    if neo4j_result is not None:
        print("[episode-analysis] Using Neo4j for ledger state")
        return neo4j_result
    
    # Fall back to regex scanning
    print("[episode-analysis] Using regex file scan for ledger state")
    return scan_output_for_ids_regex(output_dir)


def format_ledger_context(highest: dict[str, float]) -> str:
    next_family = highest["artifact_bundle"] + 1
    next_claim = int(highest["claim"]) + 1
    next_node = int(highest["node"]) + 1
    next_node_inv = int(highest["node_investigation"]) + 1
    forbidden = f" Do NOT use A-1000 through A-{next_family - 1} — those IDs exist in previous episodes." if next_family > 1000 else ""
    return (
        "=== CRITICAL: NEVER REUSE IDs FROM PREVIOUS EPISODES ===\n"
        "Artifact and claim IDs are GLOBAL and UNIQUE across the entire series.\n"
        "Reusing an ID (e.g. C-1000 when C-1000 already exists in Episode 1) CORRUPTS the record.\n"
        "Use ONLY the next available IDs listed below. No exceptions.\n"
        "=== END CRITICAL ===\n\n"
        f"LEDGER CONTINUATION (do not restart numbering):\n"
        f"- Next Artifact Family: A-{next_family}{forbidden} Sub-items use .1, .2, .3 (e.g. A-{next_family}.1, A-{next_family}.2). Create a NEW family whenever the evidentiary source changes (same court filing, same interview, same Instagram story = one family; different source = new family). No episode-wide bundles.\n"
        f"- Next Claim ID: C-{next_claim}. NEVER reuse claim IDs from previous episodes. Start at C-{next_claim} and increment sequentially.\n"
        f"- Next Node ID (people): N-{next_node} — REUSE when same entity. New IDs only for new entities.\n"
        f"- Next Node ID (investigation targets): N-{next_node_inv} — REUSE when same target.\n"
        f"- Nodes: reuse if same entity; otherwise unique sequential. Never renumber.\n"
    )


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def get_llm() -> ChatOpenAI:
    """Use MiniMax if MINIMAX_API_KEY is set (faster); otherwise Ollama."""
    if os.getenv("MINIMAX_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
            base_url="https://api.minimax.io/v1",
            api_key=os.getenv("MINIMAX_API_KEY"),
            temperature=0.2,
            max_tokens=8192,
        )
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen2.5:7b"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "fake"),
        temperature=0.2,
        max_tokens=8192,
    )


# ---------------------------------------------------------------------------
# Protocol execution
# ---------------------------------------------------------------------------

def build_system_prompt(protocol_md: str, template_md: str, ledger_context: str, episode_context: str = "") -> str:
    prompt = (
        "You are an investigative analysis agent following the Episode Analysis Protocol.\n\n"
        "CRITICAL LEDGER RULE: NEVER reuse artifact (A-) or claim (C-) IDs from previous episodes. "
        "IDs are global across the series. Use ONLY the next available IDs provided in the ledger context below.\n\n"
        "PROTOCOL RULES (follow exactly):\n"
        "---\n"
        f"{protocol_md}\n"
        "---\n\n"
        f"{ledger_context}\n\n"
    )
    
    if episode_context:
        prompt += f"{episode_context}\n\n"
    
    prompt += (
        "OUTPUT FORMAT (use this structure):\n"
        "---\n"
        f"{template_md}\n"
        "---\n\n"
        "Output ONLY the structured markdown. No preamble, no commentary. "
        "Preserve exact names. Artifact-first. No rhetorical drift."
    )
    
    return prompt


def process_episode(
    transcript: str,
    episode_num: int,
    llm: ChatOpenAI,
    system_prompt: str,
) -> str:
    user_msg = (
        f"Analyze Episode {episode_num} using the protocol.\n\n"
        f"TRANSCRIPT:\n---\n{transcript}\n---"
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]
    response = llm.invoke(messages)
    text = response.content.strip()
    # Strip <think>...</think>
    if "<think>" in text and "</think>" in text:
        end_tag = "</think>"
        idx = text.find(end_tag)
        if idx >= 0:
            text = text[idx + len(end_tag) :].strip()
    return text


# ---------------------------------------------------------------------------
# Two-phase generation (Phase 1: extract entities; Phase 2: assign IDs from ledger)
# ---------------------------------------------------------------------------

def _load_meme_context(proj_path: Path) -> str:
    """Load canonical meme dictionary for prompt injection."""
    memes_file = proj_path / "canonical" / "memes.json"
    if not memes_file.exists():
        return ""
    try:
        data = json.loads(memes_file.read_text(encoding="utf-8"))
        entries = data.get("entries", {})
        if not entries:
            return ""
        lines = ["CANONICAL MEME DICTIONARY (reference M-N when analyzing memes, euphemisms, codes):"]
        for mid, e in entries.items():
            aliases = f" (aliases: {', '.join(e.get('aliases', []))})" if e.get("aliases") else ""
            lines.append(f"  {mid}: {e.get('canonical_term', '')} [{e.get('type', 'meme')}]{aliases}")
        lines.append("")
        lines.append("For each meme occurrence, record: episode, video_timestamp (HH:MM:SS), quote, speaker_node_ref (who said it), context, and optional tags.")
        return "\n".join(lines) + "\n\n"
    except (json.JSONDecodeError, OSError):
        return ""


def build_phase1_prompt(protocol_md: str, extraction_tmpl: str, episode_context: str = "", meme_context: str = "") -> str:
    """Phase 1: Extract entities without IDs. No ledger in prompt."""
    prompt = (
        "You are an investigative analysis agent. Extract entities from the transcript.\n\n"
        "TWO-PHASE MODE: Do NOT assign A-, C-, N- IDs. Use placeholders: ART_1, ART_1.1, CLAIM_1, NODE_1, NODE_1000.\n"
        "IDs will be assigned in Phase 2 from the central ledger.\n\n"
        "PROTOCOL RULES:\n---\n"
        f"{protocol_md}\n---\n\n"
    )
    if meme_context:
        prompt += f"{meme_context}\n"
    if episode_context:
        prompt += f"{episode_context}\n\n"
    prompt += (
        "OUTPUT: Valid JSON-LD only (BRC222.org compliant). No markdown, no commentary.\n---\n"
        f"{extraction_tmpl}\n---"
    )
    return prompt


def _llm_model_label(llm: ChatOpenAI) -> str:
    """Best-effort model name for provenance."""
    for attr in ("model_name", "model"):
        v = getattr(llm, attr, None)
        if v:
            return str(v)
    return os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "unknown"


_CACHE_CANONICAL_MOD: dict[str, object | None] = {}


def _load_project_canonical_nodes(proj_path: Path) -> object | None:
    """Load {project}/scripts/canonical_nodes.py if present (per-project review hooks)."""
    key = str(proj_path.resolve())
    if key in _CACHE_CANONICAL_MOD:
        return _CACHE_CANONICAL_MOD[key]
    script = proj_path / "scripts" / "canonical_nodes.py"
    if not script.is_file():
        _CACHE_CANONICAL_MOD[key] = None
        return None
    mod_name = "canonical_nodes_hook_" + str(abs(hash(key)) % 1_000_000_000)
    spec = importlib.util.spec_from_file_location(mod_name, script)
    if spec is None or spec.loader is None:
        _CACHE_CANONICAL_MOD[key] = None
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _CACHE_CANONICAL_MOD[key] = mod
    return mod


def _queue_phase1_validation_review(proj_path: Path, episode_num: int, stem: str, errors: list[str]) -> None:
    mod = _load_project_canonical_nodes(proj_path)
    if not mod or not errors:
        return
    log_fn = getattr(mod, "log_phase1_validation_errors", None)
    if callable(log_fn):
        ec = log_fn(episode_num, stem, errors)
        if ec:
            print(f"       [review-queue] logged {ec} ({len(errors)} validation issue(s))")


def _queue_extraction_confidence_review(proj_path: Path, episode_num: int, stem: str, data: dict) -> None:
    if os.getenv("EPISODE_ANALYSIS_EXTRACTION_REVIEW", "1").lower() not in ("1", "true", "yes"):
        return
    mod = _load_project_canonical_nodes(proj_path)
    if not mod:
        return
    collect = getattr(mod, "collect_phase1_extraction_review_items", None)
    log_batch = getattr(mod, "log_extraction_review_batch", None)
    if not callable(collect) or not callable(log_batch):
        return
    items = collect(data)
    if not items:
        return
    ec = log_batch(episode_num, stem, items)
    if ec:
        print(f"       [review-queue] logged {ec} (extraction_review, {len(items)} item(s))")


def inject_extraction_meta(data: dict, transcript: str, model_label: str) -> None:
    """Set meta.transcript_sha256, extraction_timestamp (UTC ISO), model_version. Mutates data."""
    import hashlib

    meta = data.setdefault("meta", {})
    meta["transcript_sha256"] = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    meta["extraction_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["model_version"] = model_label


def run_phase1_extraction(
    transcript: str,
    episode_num: int,
    llm: ChatOpenAI,
    protocol_md: str,
    extraction_tmpl: str,
    episode_context: str,
    meme_context: str = "",
) -> dict | None:
    """Phase 1: Extract entities from transcript. Returns JSON dict or None on parse error."""
    import json

    prompt = build_phase1_prompt(protocol_md, extraction_tmpl, episode_context, meme_context)
    user_msg = f"Extract entities from Episode {episode_num}.\n\nTRANSCRIPT:\n---\n{transcript}\n---"
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_msg),
    ])
    text = response.content.strip()
    if "<think>" in text and "</think>" in text:
        idx = text.find("</think>")
        if idx >= 0:
            text = text[idx + 7 :].strip()
    if "```" in text:
        start = text.find("```json") + 7 if "```json" in text else text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end] if end > 0 else text[start:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"       [two-phase] JSON parse error: {e}")
        return None
    data.setdefault("meta", {})["episode"] = episode_num
    return _ensure_jsonld(data)


def _ensure_jsonld(data: dict) -> dict:
    """Ensure JSON-LD compliance (BRC222.org). Add @context, @type, @id if missing."""
    if "@context" not in data:
        data["@context"] = "https://brc222.org/context/v1"
    if "@type" not in data:
        data["@type"] = "EpisodeAnalysis"
    for art in data.get("artifacts", []):
        art.setdefault("@type", "ArtifactFamily")
        art.setdefault("@id", art.get("family_ref", ""))
        for sub in art.get("sub_items", []):
            sub.setdefault("@type", "Artifact")
            sub.setdefault("@id", sub.get("ref", ""))
    for node in data.get("nodes", []):
        node.setdefault("@type", "InvestigationTarget" if "1000" in str(node.get("ref", "")) else "Person")
        node.setdefault("@id", node.get("ref", ""))
    for claim in data.get("claims", []):
        claim.setdefault("@type", "Claim")
        claim.setdefault("@id", claim.get("ref", ""))
    return data


def _assign_ids_inline(data: dict, ledger: dict) -> tuple[dict[str, str], dict]:
    """Assign real IDs to entity refs. Returns (ref_to_id, updated_ledger)."""
    ref_to_id: dict[str, str] = {}
    next_art = ledger["next_artifact"]
    next_claim = ledger["next_claim"]
    next_node = ledger["next_node"]
    next_node_inv = ledger["next_node_inv"]
    for i, art in enumerate(data.get("artifacts", []), 1):
        fam_ref = art.get("family_ref") or f"ART_{i}"
        ref_to_id[fam_ref] = f"A-{next_art}"
        for j, sub in enumerate(art.get("sub_items", []), 1):
            sub_ref = sub.get("ref") or f"{fam_ref}.{j}"
            ref_to_id[sub_ref] = f"A-{next_art}.{j}"
        next_art += 1
    for node in data.get("nodes", []):
        ref = node.get("ref", "")
        if "1000" in ref or str(node.get("type", "")).lower() == "investigation_target":
            ref_to_id[ref] = f"N-{next_node_inv}"
            next_node_inv += 1
        else:
            ref_to_id[ref] = f"N-{next_node}"
            next_node += 1
    for i, c in enumerate(data.get("claims", []), 1):
        ref_to_id[c.get("ref") or f"CLAIM_{i}"] = f"C-{next_claim}"
        next_claim += 1
    return ref_to_id, {
        "next_artifact": next_art,
        "next_claim": next_claim,
        "next_node": next_node,
        "next_node_inv": next_node_inv,
    }


def _render_two_phase_markdown(data: dict, ref_to_id: dict[str, str]) -> str:
    """Render entity JSON to protocol markdown with real IDs."""
    lines = []
    meta = data.get("meta", {})
    lines.append("# Episode Analysis Output Template\n")
    lines.append("## 1. Meta-Data\n")
    lines.append(f"- **Episode**: {meta.get('episode', '?')}")
    lines.append(f"- **Source**: {meta.get('source', 'Unknown')}")
    lines.append(f"- **Video Timestamp Range**: {meta.get('video_timestamp_range', 'Unknown')}")
    if meta.get("extraction_timestamp"):
        lines.append(f"- **Extraction Timestamp (UTC)**: {meta['extraction_timestamp']}")
    if meta.get("model_version"):
        lines.append(f"- **Model Version**: {meta['model_version']}")
    if meta.get("transcript_sha256"):
        lines.append(f"- **Transcript SHA-256**: {meta['transcript_sha256']}")
    def _sort_ids(refs: list) -> list[str]:
        out = [ref_to_id.get(r, r) for r in refs if ref_to_id.get(r, r)]
        return sorted(set(out), key=lambda x: int(x.split("-")[1]) if "-" in x else 0)

    art_ids = _sort_ids([a.get("family_ref", "") for a in data.get("artifacts", [])])
    claim_ids = _sort_ids([c.get("ref", "") for c in data.get("claims", [])])
    node_ids = _sort_ids([n.get("ref", "") for n in data.get("nodes", [])])
    lines.append("- **Episode Ledger Summary**:")
    lines.append(f"  - Artifact Families Introduced: {', '.join(art_ids) if art_ids else 'None'}")
    lines.append(f"  - Claim Range: {claim_ids[0]}-{claim_ids[-1]}" if len(claim_ids) >= 2 else f"  - Claim Range: {claim_ids[0]}" if claim_ids else "  - Claim Range: None")
    lines.append(f"  - New Nodes Introduced: {', '.join(node_ids) if node_ids else 'None'}")
    lines.append("")
    lines.append("## 2. Executive Summary\n")
    lines.append(data.get("executive_summary", ""))
    lines.append("")
    lines.append("## 3. Artifact Register\n")
    for art in data.get("artifacts", []):
        fid = ref_to_id.get(art.get("family_ref", ""), art.get("family_ref", ""))
        lines.append(f"**{fid}** {art.get('bundle_name', '')}\n")
        for sub in art.get("sub_items", []):
            sid = ref_to_id.get(sub.get("ref", ""), sub.get("ref", ""))
            lines.append(f"**{sid}** {sub.get('description', '')}")
            if sub.get("event_timestamp"):
                lines.append(f"Event Timestamp: {sub['event_timestamp']}")
            if sub.get("video_timestamp"):
                lines.append(f"Video Timestamp: {sub['video_timestamp']}")
            rel_c = [ref_to_id.get(r, r) for r in sub.get("related_claims", [])]
            rel_n = [ref_to_id.get(r, r) for r in sub.get("related_nodes", [])]
            same_as = [ref_to_id.get(r, r) for r in sub.get("same_as_artifact_refs", [])]
            rel_bits = rel_c + rel_n
            if same_as:
                rel_bits.append(f"same_as: {', '.join(same_as)}")
            lines.append(f"*Related: {', '.join(rel_bits)}*")
            if sub.get("transcript_snippet"):
                lines.append(f"Transcript Snippet: {sub['transcript_snippet']}")
            if sub.get("confidence"):
                lines.append(f"Confidence: {sub['confidence']}")
            if sub.get("uncertainty_note"):
                lines.append(f"Uncertainty: {sub['uncertainty_note']}")
            lines.append("")
        lines.append("---\n")
    lines.append("## 4. Node Register\n")
    for node in data.get("nodes", []):
        nid = ref_to_id.get(node.get("ref", ""), node.get("ref", ""))
        lines.append(f"**{nid}** {node.get('name', '')}\n")
        lines.append(node.get("description", ""))
        rel_a = [ref_to_id.get(r, r) for r in node.get("related_artifacts", [])]
        rel_c = [ref_to_id.get(r, r) for r in node.get("related_claims", [])]
        lines.append(f"\n*Related: {', '.join(rel_a + rel_c)}*")
        if node.get("confidence"):
            lines.append(f"\nConfidence: {node['confidence']}")
        if node.get("uncertainty_note"):
            lines.append(f"Uncertainty: {node['uncertainty_note']}")
        lines.append("\n---\n")
    lines.append("## 5. Claim Register\n")
    for claim in data.get("claims", []):
        cid = ref_to_id.get(claim.get("ref", ""), claim.get("ref", ""))
        lines.append(f"**{cid}** {claim.get('label', '')}\n")
        lines.append(f"Claim Timestamp: {claim.get('claim_timestamp', '')}")
        lines.append(f"Claim: {claim.get('claim', '')}")
        if claim.get("transcript_snippet"):
            lines.append(f"Transcript Snippet: {claim['transcript_snippet']}")
        arts = [ref_to_id.get(r, r) for r in claim.get("anchored_artifacts", [])]
        nodes = [ref_to_id.get(r, r) for r in claim.get("related_nodes", [])]
        lines.append(f"Anchored Artifacts: {', '.join(arts)}")
        lines.append(f"Related Nodes: {', '.join(nodes)}")
        if claim.get("contradicts_claim_refs"):
            cc = [ref_to_id.get(r, r) for r in claim["contradicts_claim_refs"]]
            lines.append(f"Contradicts: {', '.join(cc)}")
        if claim.get("supports_claim_refs"):
            sc = [ref_to_id.get(r, r) for r in claim["supports_claim_refs"]]
            lines.append(f"Supports: {', '.join(sc)}")
        if claim.get("confidence"):
            lines.append(f"Confidence: {claim['confidence']}")
        if claim.get("uncertainty_note"):
            lines.append(f"Uncertainty: {claim['uncertainty_note']}")
        lines.append(f"Investigative Direction: {claim.get('investigative_direction', '')}")
        lines.append("\n---\n")
    return "\n".join(lines)


def ingest_episode_to_neo4j(episode_file: Path) -> bool:
    """Ingest a single episode file into Neo4j. Returns True if successful."""
    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        return False
    
    try:
        import subprocess
        scripts_dir = episode_file.parent.parent / "scripts"
        ingest_script = scripts_dir / "neo4j_ingest.py"
        
        if not ingest_script.exists():
            return False
        
        # Same interpreter + env as parent (uv venv, NEO4J_URI from .env / shell)
        result = subprocess.run(
            [sys.executable, str(ingest_script), "--drafts-dir", str(episode_file.parent)],
            capture_output=True,
            text=True,
            timeout=180,
            env=os.environ.copy(),
        )
        
        if result.returncode == 0:
            return True
        else:
            print(f"[episode-analysis] Neo4j ingest warning: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"[episode-analysis] Neo4j ingest failed: {e}")
        return False


def run_episode_analysis_protocol(project: str | None = None) -> None:
    project = project or os.getenv("EPISODE_ANALYSIS_PROJECT", "bride_of_charlie")
    proj_path = get_project_path(project)
    input_subdir  = os.getenv("EPISODE_ANALYSIS_INPUT", "input")
    output_subdir  = os.getenv("EPISODE_ANALYSIS_OUTPUT", "output")
    input_dir  = proj_path / input_subdir
    output_dir = proj_path / output_subdir
    log_dir    = proj_path / "logs"
    brief_dir  = proj_path / "brief"
    tmpl_dir   = proj_path / "templates"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Load protocol (prefer project brief, fallback to shared protocol)
    protocol_path = brief_dir / "monument_zero_briefing.md"
    if not protocol_path.exists():
        protocol_path = PROTOCOLS_DIR / "ep_protocol_v2.md"
    protocol_md = protocol_path.read_text(encoding="utf-8")

    # Load template (or phase-1 extraction template for two-phase mode)
    two_phase = os.getenv("EPISODE_ANALYSIS_TWO_PHASE", "").lower() in ("1", "true", "yes")
    phase1_dir = proj_path / "phase1_output"
    if two_phase:
        extraction_path = tmpl_dir / "bride_charlie_entity_extraction.md"
        template_md = extraction_path.read_text(encoding="utf-8") if extraction_path.exists() else ""
        phase1_dir.mkdir(parents=True, exist_ok=True)
        print("[episode-analysis] Two-phase mode: Phase 1 all episodes, then Phase 2 batch assign from central ledger")
    else:
        template_path = tmpl_dir / "bride_charlie_episode_analysis.md"
        if not template_path.exists():
            template_path = next(tmpl_dir.glob("*.md"), None)
        template_md = template_path.read_text(encoding="utf-8") if template_path else ""

    # Ledger state
    highest = scan_output_for_ids(output_dir)
    ledger_context = format_ledger_context(highest)

    transcripts = sorted(input_dir.glob("*.txt")) + sorted(input_dir.glob("*.md"))
    if not transcripts:
        print(f"[episode-analysis] No transcripts in {input_dir}")
        print("  Place .txt or .md files there and re-run.")
        return

    llm = get_llm()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{timestamp}.log"
    log_lines = []

    print(f"[episode-analysis] Project: {project}")
    print(f"[episode-analysis] Ledger: family A-{highest['artifact_bundle']}+, C-{highest['claim']}, N-{highest['node']}, N-{highest['node_investigation']}+")
    print(f"[episode-analysis] Processing {len(transcripts)} episode(s)...")

    force = os.getenv("EPISODE_ANALYSIS_FORCE", "").lower() in ("1", "true", "yes")
    if force:
        print("[episode-analysis] FORCE mode: re-running all episodes")
        for old in output_dir.glob("episode_*.md"):
            old.unlink()
            print(f"  Removed {old.name} (clean slate for correct ledger)")
        if two_phase:
            for old in phase1_dir.glob("episode_*.json"):
                old.unlink()
                print(f"  Removed {old.name}")
        highest = {"artifact_bundle": 999, "claim": 1000, "node": 0, "node_investigation": 1000}
        ledger_context = format_ledger_context(highest)
        system_prompt = build_system_prompt(protocol_md, template_md, ledger_context)

    neo4j_auto_ingest = os.getenv("NEO4J_AUTO_INGEST", "").lower() in ("1", "true", "yes")

    # -----------------------------------------------------------------------
    # Phase 1 (two-phase) or single-pass
    # -----------------------------------------------------------------------
    for i, path in enumerate(transcripts, 1):
        episode_num = i
        out_name = f"episode_{episode_num:03d}_{path.stem}.md"
        out_path = output_dir / out_name
        phase1_path = phase1_dir / f"episode_{episode_num:03d}_{path.stem}.json" if two_phase else None

        if two_phase:
            if phase1_path and phase1_path.exists() and not force:
                print(f"  [{i}/{len(transcripts)}] {path.name} — SKIP Phase 1 (exists)")
                log_lines.append(f"SKIP Phase 1 {path.name}")
                continue
        else:
            if out_path.exists() and not force:
                print(f"  [{i}/{len(transcripts)}] {path.name} — SKIP (already done)")
                log_lines.append(f"SKIP {path.name} (exists)")
                continue

        print(f"  [{i}/{len(transcripts)}] {path.name}")
        try:
            raw = path.read_text(encoding="utf-8")
            episode_context = get_episode_context(episode_num)

            if two_phase:
                meme_context = _load_meme_context(proj_path)
                data = run_phase1_extraction(
                    raw, episode_num, llm, protocol_md, template_md,
                    episode_context, meme_context,
                )
                if data is None:
                    log_lines.append(f"ERR {path.name}: Phase 1 JSON parse failed")
                    continue
                inject_extraction_meta(data, raw, _llm_model_label(llm))
                schema_path = proj_path / "templates" / "entity_schema.json"
                verrs: list[str] = []
                if validate_phase1:
                    verrs = validate_phase1(
                        data,
                        schema_path if schema_path.is_file() else None,
                    )
                    if verrs:
                        for line in verrs[:15]:
                            print(f"       [validation] {line}")
                        if len(verrs) > 15:
                            print(f"       [validation] ... and {len(verrs) - 15} more")
                        _queue_phase1_validation_review(proj_path, episode_num, path.stem, verrs)
                        strict = os.getenv("EPISODE_ANALYSIS_STRICT_VALIDATION", "1").lower() in (
                            "1",
                            "true",
                            "yes",
                        )
                        if strict:
                            log_lines.append(f"ERR {path.name}: Phase 1 validation failed ({len(verrs)} issue(s))")
                            continue
                        log_lines.append(f"WARN {path.name}: validation issues ignored (strict off)")
                phase1_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                _queue_extraction_confidence_review(proj_path, episode_num, path.stem, data)
                log_lines.append(f"OK  Phase 1 {path.name} -> {phase1_path.name}")
                print(f"       -> {phase1_path.name}")
            else:
                system_prompt = build_system_prompt(protocol_md, template_md, ledger_context, episode_context)
                markdown = process_episode(raw, episode_num, llm, system_prompt)
                out_path.write_text(markdown, encoding="utf-8")
                log_lines.append(f"OK  {path.name} -> {out_name}")
                print(f"       -> {out_name}")

                if neo4j_auto_ingest:
                    if ingest_episode_to_neo4j(out_path):
                        print(f"       -> Neo4j ingested")

                highest = scan_output_for_ids(output_dir)
                ledger_context = format_ledger_context(highest)
        except Exception as exc:
            log_lines.append(f"ERR {path.name}: {exc}")
            print(f"       ERR: {exc}")

    # -----------------------------------------------------------------------
    # Phase 2 batch (two-phase only): assign IDs from central ledger
    # -----------------------------------------------------------------------
    if two_phase:
        phase1_jsons = sorted(phase1_dir.glob("episode_*.json"), key=lambda p: int(re.search(r"episode_(\d+)", p.name, re.I).group(1)) if re.search(r"episode_(\d+)", p.name, re.I) else 0)
        if phase1_jsons:
            print(f"\n[episode-analysis] Phase 2: Assigning IDs from central ledger for {len(phase1_jsons)} episode(s)...")
            try:
                scripts_dir = proj_path / "scripts"
                assign_script = scripts_dir / "assign_ids.py"
                if assign_script.exists():
                    result = subprocess.run(  # noqa: S603
                        [sys.executable, str(assign_script), "--batch", str(phase1_dir), "--drafts", str(output_dir)],
                        cwd=AGENT_LAB_ROOT,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        print(f"       Phase 2 complete: {len(phase1_jsons)} draft(s) written")
                        for line in result.stdout.strip().split("\n"):
                            if line.strip():
                                print(f"       {line}")
                    else:
                        print(f"       Phase 2 failed: {result.stderr}")
                        log_lines.append(f"ERR Phase 2: {result.stderr}")
                else:
                    # Inline batch assign (assign_ids.py not found)
                    ledger = {"next_artifact": 1000, "next_claim": 1000, "next_node": 1, "next_node_inv": 1000}
                    for jpath in phase1_jsons:
                        data = json.loads(jpath.read_text(encoding="utf-8"))
                        ref_to_id, ledger = _assign_ids_inline(data, ledger)
                        md = _render_two_phase_markdown(data, ref_to_id)
                        out_path = output_dir / f"{jpath.stem}.md"
                        out_path.write_text(md, encoding="utf-8")
                    print(f"       Phase 2 complete (inline): {len(phase1_jsons)} draft(s)")
            except Exception as e:
                print(f"       Phase 2 error: {e}")
                log_lines.append(f"ERR Phase 2: {e}")
        else:
            print("[episode-analysis] No Phase 1 outputs to process.")

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[episode-analysis] Done. Log: {log_path}")


if __name__ == "__main__":
    run_episode_analysis_protocol()
