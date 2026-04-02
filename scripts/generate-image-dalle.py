#!/usr/bin/env python3
"""
Generate images using OpenAI DALL-E 3.

Requires OPENAI_API_KEY in .env (use your OpenAI account, not MiniMax).
Usage:
  .venv/bin/python scripts/generate-image-dalle.py "A sunset over mountains"
  .venv/bin/python scripts/generate-image-dalle.py "Futuristic city" --output images/city.png --size 1792x1024
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate images with OpenAI DALL-E 3")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output path (default: data/outputs/<timestamp>.png)")
    parser.add_argument("--size", default="1024x1024", choices=["1024x1024", "1792x1024", "1024x1792"], help="Image size")
    parser.add_argument("--quality", default="standard", choices=["standard", "hd"], help="standard or hd")
    parser.add_argument("--style", default="vivid", choices=["vivid", "natural"], help="vivid or natural")
    args = parser.parse_args()

    load_env()
    # Use OPENAI_IMAGE_API_KEY for DALL-E (real OpenAI). Falls back to OPENAI_API_KEY if set and base_url is OpenAI.
    api_key = os.environ.get("OPENAI_IMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_IMAGE_BASE_URL") or "https://api.openai.com/v1"
    if not api_key:
        print("Set OPENAI_IMAGE_API_KEY in .env (your OpenAI account key for DALL-E)", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = Path(args.output)
    else:
        from datetime import datetime
        out_dir = AGENT_LAB_ROOT / "data" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"dalle_{ts}.png"

    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from openai import OpenAI
    except ImportError:
        print("Install: .venv/bin/pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.images.generate(
        model="dall-e-3",
        prompt=args.prompt,
        n=1,
        size=args.size,
        quality=args.quality,
        style=args.style,
        response_format="b64_json",
    )
    import base64
    img_data = base64.b64decode(response.data[0].b64_json)
    out_path.write_bytes(img_data)
    print(str(out_path))


if __name__ == "__main__":
    main()
