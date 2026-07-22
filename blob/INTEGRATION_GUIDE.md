# Blob Storage Integration Guide

## Step 1: Configure Azure Blob Storage Credentials

1. Copy the template config file:
   ```bash
   cp blob/blob_config.json.template blob/blob_config.json
   ```

2. Edit `blob/blob_config.json` and add your credentials:
   ```json
   {
     "account_name": "your_actual_account_name",
     "account_key": "your_actual_account_key",
     "container_name": "marketing-assets",
     "folder_prefix": "task-images/"
   }
   ```

   **Get your credentials from Azure Portal:**
   - Go to: Azure Portal → Storage Accounts → Your Account
   - Under "Security + networking" → "Access keys"
   - Copy the "Storage account name" and one of the keys

3. Add `blob/blob_config.json` to `.gitignore` to keep credentials secure

## Step 2: Install Required Package

```bash
pip install azure-storage-blob
```

Or add to `requirements.txt`:
```
azure-storage-blob>=12.19.0
```

## Step 3: Add API Routes to server.py

Add the blob router to your `server.py`:

```python
# At the top of server.py, add:
from blob.blob_api import router as blob_router

# After creating the FastAPI app, add:
app.include_router(blob_router)
```

## Step 4: Integrate Frontend (index.html)

Add the blob upload script to `index.html` before the closing `</body>` tag:

```html
<!-- Blob Storage Integration -->
<script src="/blob/blob_upload.js"></script>
<script>
  // Override the handleFiles function to use blob storage
  async function handleFiles(files) {
    await handleFilesWithBlob(files);
  }
</script>
```

## Step 5: Modify renderAssetList to Show Blob URLs

Update the `renderAssetList` function in `index.html` to display blob preview URLs:

```javascript
function renderAssetList() {
  const list = document.getElementById('assetList');
  if (!state.modalAssets.length) {
    list.innerHTML = '<div style="font-size:11px;color:var(--ink-42);padding:8px;">No assets yet</div>';
    return;
  }
  
  list.innerHTML = state.modalAssets.map(a => {
    const previewUrl = a.blob_url || a.onedrive_url || '#';
    const isImage = a.type.startsWith('image/');
    
    return `
      <div class="asset-item">
        <div class="aname">
          ${isImage && a.blob_url ? `<img src="${a.blob_url}" style="max-width:40px;max-height:40px;margin-right:8px;border-radius:4px;">` : ''}
          <span>${esc(a.name)}</span>
          ${a.blob_url ? '<span style="color:var(--teal);font-size:10px;margin-left:4px;">☁ Blob</span>' : ''}
        </div>
        <div class="aacts">
          ${previewUrl !== '#' ? `<button onclick="viewAsset('${a.id}')" style="font-size:10px;">Preview</button>` : ''}
          <button onclick="removeAsset('${a.id}')" style="color:var(--rust);font-size:10px;">×</button>
        </div>
      </div>
    `;
  }).join('');
}
```

## Step 6: Update viewAsset to Use Blob URLs

```javascript
async function viewAsset(assetId) {
  const asset = state.modalAssets.find(a => a.id === assetId);
  if (!asset) return;
  
  const content = document.getElementById('lightboxContent');
  
  // Use blob URL if available
  if (asset.blob_url) {
    if (asset.type.startsWith('image/')) {
      content.innerHTML = `<img src="${asset.blob_url}">`;
    } else if (asset.type.startsWith('video/')) {
      content.innerHTML = `<video src="${asset.blob_url}" controls autoplay></video>`;
    }
    document.getElementById('lightbox').classList.add('open');
    return;
  }
  
  // Fallback to existing behavior
  if (!state.editingId) {
    showToast('Save the task first');
    return;
  }
  
  const blob = await fetchAssetBlob(state.editingId, assetId);
  if (!blob) {
    showToast('Could not load asset');
    return;
  }
  
  if (blob.type.startsWith('image/')) {
    content.innerHTML = `<img src="${blob.dataUrl}">`;
  } else if (blob.type.startsWith('video/')) {
    content.innerHTML = `<video src="${blob.dataUrl}" controls autoplay></video>`;
  } else {
    const a = document.createElement('a');
    a.href = blob.dataUrl;
    a.download = blob.name;
    a.click();
    return;
  }
  
  document.getElementById('lightbox').classList.add('open');
}
```

## Step 7: Test the Integration

1. Start the server:
   ```bash
   python server.py
   ```

2. Open the app in browser

3. Create or edit a task

4. Drop an image into the dropzone (id="dropzone")

5. The image should:
   - Upload to Azure Blob Storage
   - Be stored with name: `taskname_img_{timestamp}.{ext}`
   - Display a preview from the blob URL
   - Show a "☁ Blob" indicator

## Naming Convention

Images are stored in blob storage with the format:
```
{folder_prefix}{sanitized_task_name}_img_{timestamp}.{ext}
```

Example:
- Task name: "Instagram Post - Q1 Campaign"
- Result: `task-images/Instagram_Post___Q1_Campaign_img_20240117_143022.jpg`

## API Endpoints

- `GET /api/blob/status` - Check configuration status
- `POST /api/blob/configure` - Set credentials (alternative to config file)
- `POST /api/blob/upload` - Upload image (Form: file, task_name)
- `GET /api/blob/preview/{blob_name}` - Get fresh preview URL
- `GET /api/blob/list?task_name=...` - List images for a task
- `DELETE /api/blob/delete/{blob_name}` - Delete an image

## Troubleshooting

### "Blob storage not configured"
- Check `blob/blob_config.json` exists and has valid credentials
- Verify container exists in Azure Portal

### "Upload failed"
- Check Azure Storage Account access keys are correct
- Ensure container exists and has appropriate permissions
- Verify network connectivity to Azure

### Preview images not loading
- SAS URLs expire after 7 days - refresh the preview
- Check CORS settings in Azure Storage Account if loading from different domain
