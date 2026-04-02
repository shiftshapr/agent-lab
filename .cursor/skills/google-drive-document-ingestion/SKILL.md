---
name: google-drive-document-ingestion
description: >-
  Ingest documents from Google Drive into the meta-layer knowledge graph. Converts Word docs, 
  PDFs, and Google Docs to structured knowledge, extracts concepts, and adds to Neo4j. Use when 
  the user wants to process Drive documents, mentions "ingest from Drive", "add Drive docs to graph", 
  or needs to organize Google Drive content into their knowledge base.
---

# Google Drive Document Ingestion

## Overview

This skill provides an end-to-end pipeline for ingesting documents from Google Drive into the meta-layer knowledge graph. It handles document conversion, content extraction, concept identification, and graph storage.

## When to Use

Trigger on:
- "Ingest documents from Google Drive"
- "Add my Drive docs to the knowledge graph"
- "Process new documents in Drive"
- "Sync Drive folder to meta-layer"
- "Convert Drive documents to knowledge"

## Prerequisites

### Google Drive API Setup
1. Enable Google Drive API in Google Cloud Console
2. Create service account credentials
3. Store credentials in `config/google-drive-credentials.json`
4. Share target Drive folders with service account email

### Required Dependencies
```bash
# Install required packages
uv add google-api-python-client google-auth google-auth-oauthlib
uv add python-docx PyPDF2 mammoth  # Document conversion
uv add neo4j  # Graph database
```

## Core Workflow

### 1. Document Discovery
```python
# List documents in specified Drive folder
python scripts/list-drive-documents.py --folder-id <FOLDER_ID>
```

### 2. Document Conversion
```python
# Convert documents to markdown
python scripts/convert-drive-documents.py --folder-id <FOLDER_ID> --output-dir knowledge/drive-imports/
```

### 3. Content Extraction & Graph Ingestion
```python
# Extract concepts and add to meta-layer graph
python scripts/ingest-drive-knowledge.py --input-dir knowledge/drive-imports/
```

## Document Processing Pipeline

### Supported Formats
- **Google Docs**: Export as HTML, convert to markdown
- **Microsoft Word (.docx)**: Extract with python-docx + mammoth
- **PDF**: Extract text with PyPDF2, preserve structure
- **Plain text**: Direct ingestion

### Content Structure Preservation
- **Headings**: Converted to markdown headers for chunking
- **Tables**: Preserved as markdown tables
- **Images**: Downloaded and referenced with alt text
- **Comments**: Extracted as annotations
- **Metadata**: Author, creation date, modification date

### Knowledge Extraction
For each document:
1. **Source Node**: Create MLSource with Drive metadata
2. **Chunking**: Split by headings/paragraphs into MLChunk nodes
3. **Concept Detection**: Identify MLConcept and MLPrimitive references
4. **Relationship Mapping**: Link chunks to concepts via ABOUT relationships

## Configuration

### Drive Folder Mapping
Configure in `config/drive-ingestion.yaml`:
```yaml
folders:
  - id: "1ABC123..."
    name: "Research Papers"
    category: "research"
    auto_ingest: true
  - id: "1DEF456..."
    name: "Meeting Notes"
    category: "notes"
    auto_ingest: false

processing:
  chunk_size: 1000
  overlap: 200
  extract_images: true
  preserve_comments: true
```

### Concept Mapping Rules
```yaml
concept_extraction:
  # Auto-detect these meta-layer concepts
  concepts:
    - "collective intelligence"
    - "stigmergy"
    - "meta-layer"
    - "overlay application"
  
  # Map document sections to node types
  section_mapping:
    "Abstract": "summary"
    "Introduction": "context"
    "Conclusion": "insight"
```

## Utility Scripts

### Document Listing
```bash
python scripts/list-drive-documents.py --folder-id <ID> [--recursive]
# Output: JSON list of documents with metadata
```

### Batch Conversion
```bash
python scripts/convert-drive-documents.py \
  --folder-id <ID> \
  --output-dir knowledge/drive-imports/ \
  --formats docx,pdf,gdoc
```

### Incremental Sync
```bash
python scripts/sync-drive-changes.py --since "2024-01-01"
# Only process documents modified since date
```

### Validation
```bash
python scripts/validate-drive-ingestion.py --check-graph
# Verify all documents were properly ingested
```

## Integration with Existing Workflows

### Work Log Integration
After Drive ingestion, update work log:
```python
# Add successful ingestions to work log
python scripts/log-drive-ingestion.py --session-id <ID>
```

### Meta-Layer Graph Integration
Uses existing `add-to-meta-layer-graph` patterns:
- Creates proper MLSource nodes with Drive provenance
- Links to existing concepts when detected
- Maintains relationship consistency

## Monitoring & Maintenance

### Change Detection
```bash
# Set up webhook for Drive changes (optional)
python scripts/setup-drive-webhook.py --folder-id <ID>
```

### Batch Processing Status
```bash
python scripts/drive-ingestion-status.py
# Shows: pending, processing, completed, failed documents
```

### Cleanup
```bash
python scripts/cleanup-drive-cache.py --older-than 30d
# Remove temporary files and conversion artifacts
```

## Error Handling

### Common Issues
- **Permission denied**: Check service account has folder access
- **Conversion failed**: Document may be corrupted or unsupported format
- **Graph connection**: Ensure Neo4j is running (`docker compose up -d`)
- **Rate limits**: Implement exponential backoff for Drive API calls

### Recovery
```bash
# Retry failed documents
python scripts/retry-failed-ingestions.py --session-id <ID>

# Reset document status
python scripts/reset-document-status.py --document-id <ID>
```

## Security & Privacy

### Data Handling
- Documents are processed locally, not sent to external services
- Temporary files are cleaned up after processing
- Service account credentials are stored securely
- No document content is logged (only metadata)

### Access Control
- Service account has read-only access to specified folders
- Generated knowledge respects original document permissions
- Sensitive documents can be excluded via configuration

## Related Skills
- **work-log-ingestion**: For processing ingestion results
- **add-to-meta-layer-graph**: For manual concept addition
- **master-calendar**: For scheduling regular ingestion runs