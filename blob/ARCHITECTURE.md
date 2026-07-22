# Blob Storage Architecture

## System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                        (index.html)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 1. User drops image in dropzone
                         │    (id="dropzone")
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND JAVASCRIPT                          │
│                   (blob_upload.js)                             │
├─────────────────────────────────────────────────────────────────┤
│  • Reads file from dropzone                                    │
│  • Gets task name from form                                    │
│  • Creates FormData with file + task_name                      │
│  • Calls: POST /api/blob/upload                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 2. Upload request
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI SERVER                              │
│                    (server.py + blob_api.py)                   │
├─────────────────────────────────────────────────────────────────┤
│  • Receives file upload                                        │
│  • Validates: size, type (images only)                         │
│  • Calls: blob.upload_image()                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 3. Upload to blob
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  BLOB STORAGE MODULE                            │
│                   (blob_storage.py)                            │
├─────────────────────────────────────────────────────────────────┤
│  • Sanitizes task name                                         │
│  • Creates blob name: taskname_img_{timestamp}.{ext}           │
│  • Uploads to Azure Blob Storage                               │
│  • Generates SAS URL (7-day expiry)                            │
│  • Returns: preview_url, blob_name, permanent_url              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 4. Upload to Azure
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AZURE BLOB STORAGE                             │
│              (Cloud Storage Service)                           │
├─────────────────────────────────────────────────────────────────┤
│  Container: marketing-assets                                    │
│  Path: task-images/{taskname}_img_{timestamp}.{ext}            │
│                                                                 │
│  ✓ Scalable cloud storage                                      │
│  ✓ Global CDN delivery                                         │
│  ✓ Secure SAS token access                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 5. Returns URLs
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND RESPONSE                            │
│                    (blob_upload.js)                            │
├─────────────────────────────────────────────────────────────────┤
│  • Receives: preview_url, blob_name, permanent_url             │
│  • Stores in asset metadata                                    │
│  • Displays preview image using preview_url                    │
│  • Shows "☁ Blob" indicator                                   │
│  • Saves to task when user clicks "Save task"                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Upload Process
1. **User Action**: Drops image in dropzone
2. **Frontend**: Reads file, prepares FormData
3. **API Call**: `POST /api/blob/upload` with file + task_name
4. **Server**: Validates file (size, type)
5. **Blob Module**: 
   - Sanitizes task name → "My Task" → "My_Task"
   - Creates blob name → "My_Task_img_20240117_143022.jpg"
   - Uploads to Azure
   - Generates SAS URL
6. **Azure**: Stores file, returns URL
7. **Response**: Returns preview_url, blob_name to frontend
8. **Display**: Shows image preview with blob URL

### Preview Process
1. **User Action**: Clicks preview on asset
2. **Frontend**: Checks if `asset.blob_url` exists
3. **Display**: Shows image directly from blob URL
4. **Refresh**: If URL expired (7 days), call `GET /api/blob/preview/{blob_name}`

### Delete Process
1. **User Action**: Clicks remove on asset
2. **Frontend**: Removes from UI
3. **API Call**: `DELETE /api/blob/delete/{blob_name}` (optional)
4. **Azure**: Blob deleted from storage

## File Structure

```
blob/
├── __init__.py                 # Package initialization
├── blob_storage.py             # Core Azure Blob operations
├── blob_api.py                 # FastAPI routes
├── blob_upload.js              # Frontend integration
├── blob_config.json.template   # Config template
├── blob_config.json            # Actual config (gitignored)
├── blob_config_ui.html         # Web UI for setup
├── setup_blob.py               # Interactive setup script
├── test_blob.py                # Test suite
├── README.md                   # Overview
├── INTEGRATION_GUIDE.md        # Step-by-step guide
├── SETUP_SUMMARY.md            # Quick reference
└── ARCHITECTURE.md             # This file
```

## API Endpoints

### Status & Configuration
```
GET  /api/blob/status
     → Returns: { configured, connected, account, container }

POST /api/blob/configure
     ← Body: { account_name, account_key, container_name, folder_prefix }
     → Returns: { success, message }
```

### Upload & Retrieve
```
POST /api/blob/upload
     ← FormData: { file: File, task_name: String }
     → Returns: { success, blob_name, preview_url, permanent_url, size }

GET  /api/blob/preview/{blob_name}
     → Returns: { success, url, expires_in }
```

### List & Delete
```
GET  /api/blob/list?task_name={name}
     → Returns: { success, images: [...], count }

DELETE /api/blob/delete/{blob_name}
       → Returns: { success, deleted }
```

## Image Naming Convention

**Pattern**: `{sanitized_task_name}_img_{timestamp}.{ext}`

**Examples**:
- Task: "Instagram Post" → `Instagram_Post_img_20240117_143022.jpg`
- Task: "Q1 Campaign!" → `Q1_Campaign__img_20240117_143030.png`
- Task: "2024-Report" → `2024_Report_img_20240117_143045.pdf`

**Sanitization Rules**:
- Keep: alphanumeric, hyphens, underscores
- Replace: everything else with underscore
- Preserve: original file extension

## Storage Organization

```
Azure Storage Account: {account_name}
  └── Container: marketing-assets
      └── Folder: task-images/
          ├── Task_A_img_20240117_140000.jpg
          ├── Task_A_img_20240117_141500.png
          ├── Task_B_img_20240117_142000.jpg
          └── Task_C_img_20240117_143000.gif
```

## Security

### SAS Tokens
- **Purpose**: Temporary access to blobs
- **Duration**: 7 days
- **Permissions**: Read-only
- **Renewal**: Call `/api/blob/preview/{blob_name}` for fresh URL

### Access Keys
- **Storage**: `blob/blob_config.json` (gitignored)
- **Encryption**: Not encrypted in config (server-side only)
- **Scope**: Full account access
- **Best Practice**: Rotate keys regularly in Azure Portal

### CORS
If loading images from different domain:
1. Go to Azure Portal → Storage Account
2. Settings → Resource sharing (CORS)
3. Add allowed origins

## Performance

### Upload
- **Client → Server**: FormData upload
- **Server → Azure**: Direct blob upload
- **Network**: Depends on image size & internet speed
- **Typical**: 1-3 seconds for 1MB image

### Preview
- **First load**: Uses SAS URL from Azure
- **Cached**: Browser caches image
- **CDN**: Azure serves via global CDN
- **Typical**: 100-500ms

## Error Handling

### Frontend
```javascript
try {
  const result = await uploadToBlobStorage(file, taskName);
  if (result.success) {
    // Show success
  }
} catch (error) {
  console.warn('Blob upload failed, storing locally', error);
  // Fallback to local storage
}
```

### Backend
```python
def upload_image(file_bytes, filename, task_name):
    try:
        # Upload logic
        return { "success": True, ... }
    except Exception as e:
        return { "error": f"Upload failed: {str(e)}" }
```

## Scalability

- **Storage**: Unlimited (Azure Blob)
- **Bandwidth**: High (Azure CDN)
- **Concurrent Uploads**: Handled by FastAPI async
- **Cost**: Pay per GB stored + bandwidth
- **Limits**: 10MB per image (configurable)

## Monitoring

### Logs
- Server logs: Upload success/failure
- Azure Portal: Blob metrics, requests, bandwidth

### Metrics
- Total storage used
- Number of blobs
- Request count
- Bandwidth usage
- Average latency
