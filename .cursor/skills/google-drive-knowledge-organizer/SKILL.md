---
name: google-drive-knowledge-organizer
description: >-
  Organize Google Drive documents using meta-layer concepts and knowledge graph relationships. 
  Auto-categorizes documents, creates folder structures, generates knowledge maps, and maintains 
  semantic organization. Use when user wants to "organize Drive by concepts", "restructure Drive 
  folders", "categorize documents", or "create knowledge-based Drive organization".
---

# Google Drive Knowledge Organizer

## Overview

Analyzes document content and organizes Google Drive using meta-layer concepts, creating semantic folder structures and maintaining knowledge-based document organization.

## When to Use

Trigger on:
- "Organize my Drive by concepts"
- "Restructure Drive folders using meta-layer"
- "Categorize documents by content"
- "Create knowledge-based Drive organization"
- "Auto-organize Drive documents"
- "Generate Drive knowledge map"

## Core Capabilities

### 1. Content-Based Categorization
- Analyzes document content to identify key concepts
- Maps documents to meta-layer primitives and frameworks
- Groups related documents by semantic similarity
- Suggests folder structures based on content themes

### 2. Semantic Folder Structure
- Creates folder hierarchies based on meta-layer taxonomy
- Organizes by concepts like "Governance", "Trust", "Coordination"
- Maintains both topic-based and format-based organization
- Supports multiple organizational schemes simultaneously

### 3. Knowledge Relationship Mapping
- Identifies connections between documents
- Creates visual knowledge maps of document relationships
- Tracks citation networks and reference patterns
- Suggests document clusters and research themes

## Organization Workflows

### 1. Initial Drive Analysis
```bash
# Analyze entire Drive for organizational opportunities
python scripts/analyze-drive-organization.py --drive-root <FOLDER_ID>
```

### 2. Concept-Based Reorganization
```bash
# Reorganize based on meta-layer concepts
python scripts/reorganize-by-concepts.py --source-folder <ID> --create-structure
```

### 3. Knowledge Map Generation
```bash
# Generate visual knowledge map
python scripts/generate-drive-knowledge-map.py --output knowledge/drive-map.html
```

## Configuration

### Organization Schema (`config/drive-organization.yaml`)
```yaml
organization_schemes:
  meta_layer:
    root_folder: "Meta-Layer Knowledge"
    structure:
      - name: "Concepts"
        subfolders:
          - "Collective Intelligence"
          - "Stigmergy"
          - "Trust Orchestration"
          - "Interface Governance"
      - name: "Primitives"
        subfolders:
          - "Smart Tags"
          - "Bridges"
          - "Overlay Applications"
          - "Presence"
      - name: "Frameworks"
        subfolders:
          - "Metaweb"
          - "Web Cake Model"
          - "Overweb Pattern"

  document_types:
    root_folder: "Document Types"
    structure:
      - name: "Research Papers"
      - name: "Meeting Notes"
      - name: "Drafts"
      - name: "Reference Materials"

content_analysis:
  concept_detection:
    min_confidence: 0.7
    context_window: 500
    use_embeddings: true
  
  relationship_detection:
    citation_patterns: true
    concept_overlap: true
    author_networks: true
```

### Categorization Rules
```yaml
categorization_rules:
  # Auto-categorize by content patterns
  patterns:
    - pattern: "collective intelligence|stigmergy|coordination"
      category: "Coordination Theory"
      confidence: 0.8
    
    - pattern: "overlay|meta-layer|above the webpage"
      category: "Meta-Layer Architecture"
      confidence: 0.9
    
    - pattern: "trust|verification|identity"
      category: "Trust Infrastructure"
      confidence: 0.7

  # File type specific rules
  file_types:
    ".docx": 
      default_category: "Documents"
      analyze_content: true
    ".pdf":
      default_category: "Research"
      extract_metadata: true
    ".gdoc":
      default_category: "Collaborative"
      track_changes: true
```

## Organization Strategies

### 1. Hierarchical Organization
```
Meta-Layer Knowledge/
├── 01-Foundational-Concepts/
│   ├── Collective-Intelligence/
│   ├── Stigmergy/
│   └── Trust-Orchestration/
├── 02-Technical-Primitives/
│   ├── Smart-Tags/
│   ├── Bridges/
│   └── Overlay-Applications/
├── 03-Frameworks/
│   ├── Metaweb/
│   ├── Web-Cake-Model/
│   └── Overweb-Pattern/
└── 04-Applications/
    ├── Use-Cases/
    ├── Implementations/
    └── Case-Studies/
```

### 2. Cross-Reference Organization
- Documents can exist in multiple conceptual folders via shortcuts
- Maintains original locations while providing semantic access
- Creates "Views" folders that group by different criteria
- Supports both hierarchical and network-based organization

### 3. Dynamic Organization
- Automatically updates organization as new documents are added
- Learns from user corrections and preferences
- Adapts folder structures based on content evolution
- Maintains organization history for rollback

## Utility Scripts

### Analysis & Planning
```bash
# Analyze current Drive organization
python scripts/analyze-current-organization.py --report-format html

# Suggest reorganization plan
python scripts/suggest-reorganization.py --dry-run

# Estimate reorganization impact
python scripts/estimate-reorganization.py --show-conflicts
```

### Organization Execution
```bash
# Execute reorganization plan
python scripts/execute-reorganization.py --plan reorganization-plan.json

# Create concept-based folder structure
python scripts/create-concept-folders.py --schema meta_layer

# Batch move documents by category
python scripts/batch-move-documents.py --category "Trust Infrastructure"
```

### Knowledge Mapping
```bash
# Generate document relationship graph
python scripts/generate-document-graph.py --format graphml

# Create concept co-occurrence matrix
python scripts/analyze-concept-cooccurrence.py --output concepts-matrix.csv

# Export knowledge map data
python scripts/export-knowledge-map.py --format json
```

## Integration Features

### Neo4j Integration
- Syncs Drive organization with knowledge graph
- Creates MLSource nodes with Drive folder metadata
- Links documents to concepts based on folder placement
- Maintains bidirectional sync between Drive and graph

### Metadata Enhancement
```python
# Add meta-layer metadata to Drive documents
{
  "concepts": ["collective intelligence", "stigmergy"],
  "primitives": ["smart tags", "bridges"],
  "frameworks": ["metaweb"],
  "organization_version": "2024-01",
  "auto_categorized": true,
  "confidence_score": 0.85
}
```

### Search Enhancement
- Creates searchable tags based on content analysis
- Generates document summaries for quick reference
- Maintains keyword indexes for each organizational category
- Enables semantic search across organized content

## Monitoring & Maintenance

### Organization Health
```bash
# Check organization consistency
python scripts/check-organization-health.py

# Find misplaced documents
python scripts/find-misplaced-documents.py --suggest-moves

# Validate folder structure
python scripts/validate-folder-structure.py --schema meta_layer
```

### Usage Analytics
- Tracks which organizational schemes are most used
- Identifies frequently accessed document clusters
- Monitors search patterns and access frequency
- Suggests optimization based on usage patterns

### Maintenance Tasks
```bash
# Clean up empty folders
python scripts/cleanup-empty-folders.py --dry-run

# Merge duplicate folders
python scripts/merge-duplicate-folders.py --interactive

# Update organization based on new content
python scripts/update-organization.py --incremental
```

## Visualization & Reporting

### Knowledge Maps
- Interactive HTML visualizations of document relationships
- Concept clustering diagrams
- Citation network graphs
- Temporal evolution of knowledge organization

### Organization Reports
```bash
# Generate organization report
python scripts/generate-organization-report.py --format pdf

# Document distribution analysis
python scripts/analyze-document-distribution.py --chart

# Concept coverage report
python scripts/concept-coverage-report.py --missing-concepts
```

### Dashboard Integration
- Real-time organization health metrics
- Document categorization accuracy
- User interaction patterns with organized content
- Organizational scheme effectiveness scores

## Related Skills
- **google-drive-document-ingestion**: For processing organized documents
- **google-drive-watcher**: For maintaining organization as content changes
- **add-to-meta-layer-graph**: For syncing organization with knowledge graph