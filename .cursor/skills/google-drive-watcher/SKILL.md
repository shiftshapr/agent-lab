---
name: google-drive-watcher
description: >-
  Monitor Google Drive folders for new or updated documents and automatically trigger ingestion 
  workflows. Sets up webhooks and polling to detect changes. Use when user wants to "watch Drive 
  for changes", "auto-ingest new documents", "monitor Drive folder", or set up automated document 
  processing.
---

# Google Drive Watcher

## Overview

Monitors specified Google Drive folders for document changes and automatically triggers ingestion workflows. Supports both webhook-based real-time monitoring and scheduled polling.

## When to Use

Trigger on:
- "Watch this Drive folder for changes"
- "Auto-ingest new documents from Drive"
- "Monitor Drive folder for updates"
- "Set up automatic document processing"
- "Notify me when new docs are added to Drive"

## Monitoring Methods

### 1. Webhook-Based (Real-time)
- Receives instant notifications from Google Drive
- Requires public endpoint (ngrok for development)
- Most efficient for active folders

### 2. Polling-Based (Scheduled)
- Checks for changes on schedule (hourly, daily)
- Works without public endpoint
- Better for low-activity folders

## Setup Workflow

### 1. Configure Watched Folders
```bash
python scripts/setup-drive-watcher.py --folder-id <ID> --name "Research Papers"
```

### 2. Choose Monitoring Method
```bash
# Webhook setup (requires public URL)
python scripts/setup-drive-webhook.py --folder-id <ID> --webhook-url <URL>

# OR polling setup
python scripts/setup-drive-polling.py --folder-id <ID> --interval 3600  # 1 hour
```

### 3. Start Monitoring
```bash
# Start webhook server
python scripts/start-webhook-server.py --port 8080

# OR start polling daemon
python scripts/start-polling-daemon.py
```

## Configuration

### Watcher Configuration (`config/drive-watcher.yaml`)
```yaml
folders:
  - id: "1ABC123..."
    name: "Research Papers"
    webhook_enabled: true
    polling_interval: 3600  # seconds
    auto_ingest: true
    filters:
      - "*.docx"
      - "*.pdf"
      - "*.gdoc"
    exclude_patterns:
      - "~$*"  # Temporary files
      - ".*"   # Hidden files

notifications:
  email: true
  slack_webhook: "https://hooks.slack.com/..."
  work_log: true

processing:
  immediate: true  # Process immediately vs batch
  max_concurrent: 3
  retry_attempts: 3
```

### Webhook Configuration
```yaml
webhook:
  port: 8080
  public_url: "https://your-domain.ngrok.io"
  secret_token: "your-secret-token"
  ssl_verify: true
```

## Event Processing

### Change Detection
When changes are detected:
1. **Validate**: Check if file matches configured filters
2. **Deduplicate**: Avoid processing same change multiple times
3. **Queue**: Add to processing queue with metadata
4. **Notify**: Send notifications if configured
5. **Process**: Trigger ingestion workflow

### Change Types Handled
- **New documents**: Added to watched folders
- **Modified documents**: Content or metadata changes
- **Moved documents**: Into or out of watched folders
- **Renamed documents**: Name changes
- **Deleted documents**: Remove from knowledge graph (optional)

## Utility Scripts

### Watcher Management
```bash
# List active watchers
python scripts/list-drive-watchers.py

# Stop specific watcher
python scripts/stop-drive-watcher.py --folder-id <ID>

# Stop all watchers
python scripts/stop-all-watchers.py
```

### Status Monitoring
```bash
# Check watcher health
python scripts/check-watcher-status.py

# View recent events
python scripts/view-drive-events.py --since "1 hour ago"

# Processing queue status
python scripts/queue-status.py
```

### Manual Triggers
```bash
# Force check for changes
python scripts/force-drive-check.py --folder-id <ID>

# Reprocess recent changes
python scripts/reprocess-changes.py --since "2024-01-01"
```

## Integration Points

### Work Log Integration
```python
# Log watcher events to work log
{
  "text": "Drive watcher: 3 new documents detected in Research Papers",
  "status": "note",
  "attachments": ["drive://folder/1ABC123"],
  "ingest": true
}
```

### Notification Integration
```bash
# Send Slack notification
curl -X POST $SLACK_WEBHOOK -d '{
  "text": "🔍 Drive Watcher: New document detected",
  "attachments": [{
    "title": "document-name.docx",
    "text": "Added to Research Papers folder",
    "color": "good"
  }]
}'
```

### Calendar Integration
```python
# Schedule batch processing
python scripts/schedule-batch-processing.py --time "daily at 9am"
```

## Error Handling & Recovery

### Common Issues
- **Webhook endpoint unreachable**: Falls back to polling
- **API rate limits**: Implements exponential backoff
- **Processing failures**: Retries with increasing delays
- **Duplicate events**: Deduplication based on file ID + timestamp

### Recovery Mechanisms
```bash
# Recover from missed events
python scripts/recover-missed-events.py --since "last successful check"

# Rebuild event history
python scripts/rebuild-event-history.py --folder-id <ID>

# Reset watcher state
python scripts/reset-watcher-state.py --folder-id <ID>
```

## Security Considerations

### Webhook Security
- Validates webhook signatures from Google
- Uses HTTPS for webhook endpoints
- Implements rate limiting and request validation
- Logs security events

### Access Control
- Service account has minimal required permissions
- Webhook endpoints are protected with secret tokens
- Event logs exclude sensitive document content
- Configurable access restrictions per folder

## Performance Optimization

### Efficient Processing
- Batches multiple changes for processing
- Implements intelligent queuing and prioritization
- Caches folder metadata to reduce API calls
- Uses incremental sync for large folders

### Resource Management
```yaml
performance:
  max_queue_size: 1000
  batch_size: 10
  processing_timeout: 300  # seconds
  memory_limit: "512MB"
```

## Monitoring & Alerts

### Health Checks
```bash
# Automated health monitoring
python scripts/health-check.py --alert-on-failure
```

### Metrics Collection
- Events processed per hour/day
- Processing success/failure rates
- API quota usage
- Queue depth and processing latency

### Alerting Rules
```yaml
alerts:
  - name: "High failure rate"
    condition: "failure_rate > 0.1"
    action: "email"
  - name: "Queue backup"
    condition: "queue_depth > 100"
    action: "slack"
```

## Related Skills
- **google-drive-document-ingestion**: For processing detected changes
- **work-log-ingestion**: For logging watcher events
- **master-calendar**: For scheduling polling intervals