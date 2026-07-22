# 🚀 Azure Blob Storage - Frontend Only (No Backend!)

**Direct browser upload to Azure Blob Storage** using SAS tokens. Zero server-side code required!

## ✨ Key Benefits

- ✅ **No Backend** - Pure JavaScript, works in any browser
- ✅ **Direct Upload** - Browser → Azure (fast, no proxy)
- ✅ **SAS Tokens** - Secure, time-limited access
- ✅ **LocalStorage Config** - Credentials stored in browser
- ✅ **Works Offline** - Once configured, no server needed
- ✅ **Simple Integration** - Just 3 script tags

## 📁 Frontend Files

```
blob/
├── 🌐 JavaScript Files (4 files)
│   ├── blob_storage.js       - Core Azure Blob client
│   ├── blob_config.js        - Configuration manager
│   ├── blob_upload.js        - Dropzone integration
│   └── (removed .py files)
│
└── 🎨 HTML Pages (2 files)
    ├── blob_config_ui.html   - Configuration UI
    └── test_blob.html        - Test suite
```

## 🚀 Quick Start (3 Steps)

### Step 1: Generate SAS Token

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Storage Accounts → Your Account**
3. Click: **Security + networking → Shared access signature**
4. Configure:
   - **Allowed services**: ✓ Blob
   - **Allowed resource types**: ✓ Container, ✓ Object
   - **Allowed permissions**: ✓ Read, ✓ Write, ✓ Delete, ✓ List
   - **Start time**: Now
   - **Expiry**: 1 year from now (or your preference)
5. Click: **Generate SAS and connection string**
6. Copy the **SAS token** (starts with `?sv=...`)

### Step 2: Configure in Browser

Open `blob/blob_config_ui.html` in your browser and paste:
- Account Name
- SAS Token
- Container Name (e.g., "marketing-assets")
- Folder Prefix (e.g., "task-images/")

Configuration is saved to `localStorage` in your browser.

### Step 3: Test It

Open `blob/test_blob.html` and:
1. ✓ Test 1: Check configuration
2. ✓ Test 2: Upload test image
3. ✓ Test 3: View uploaded image

## 🔌 Integration in Your App

### Add to `index.html`:

```html
<!-- Add before closing </body> tag -->

<!-- Blob Storage Scripts -->
<script src="blob/blob_storage.js"></script>
<script src="blob/blob_config.js"></script>
<script src="blob/blob_upload.js"></script>

<script>
  // Override handleFiles to use blob storage
  async function handleFiles(files) {
    await handleFilesWithBlob(files);
  }
</script>
```

That's it! Images will now upload directly to Azure.

## 📊 How It Works

```
User drops image in dropzone
    ↓
JavaScript reads file
    ↓
Sanitize task name → "My_Task"
    ↓
Create blob name → "My_Task_img_20240117_143022.jpg"
    ↓
PUT request to Azure with SAS token
    ↓
Azure Blob Storage stores image
    ↓
Generate preview URL (with SAS)
    ↓
Display image in UI
```

## 🔐 Security

### SAS Token Approach
- **What**: Shared Access Signature (time-limited URL token)
- **Stored**: In browser's `localStorage`
- **Scope**: Container-level access
- **Expiry**: You set (recommend 1 year)
- **Permissions**: Read, Write, Delete, List (on blobs only)

### vs Account Key Approach
- ❌ **Account Keys**: Full account access (too risky for frontend)
- ✅ **SAS Tokens**: Limited scope, time-bound, revocable

### Best Practices
1. Set reasonable expiry (e.g., 1 year)
2. Only grant needed permissions
3. Regenerate tokens periodically
4. Never commit SAS tokens to git
5. Use container-level SAS (not account-level)

## 🎯 Example Usage

### Upload Image
```javascript
// Get task name from form
const taskName = document.getElementById('taskName').value;

// Upload image
const result = await window.blobStorage.uploadImage(file, taskName);

if (result.success) {
  console.log('Uploaded:', result.preview_url);
  // Display preview
  img.src = result.preview_url;
} else {
  console.error('Upload failed:', result.error);
}
```

### Check Status
```javascript
const status = window.blobStorage.getStatus();
if (status.configured) {
  console.log('Ready to upload!');
} else {
  console.log('Not configured:', status.message);
}
```

### Get Preview URL
```javascript
const previewUrl = window.blobStorage.getBlobUrlWithSAS('task-images/My_Task_img_20240117_143022.jpg');
img.src = previewUrl;
```

## 📖 API Reference

### BlobStorageClient

```javascript
// Configuration
window.blobStorage.saveConfig({ account_name, sas_token, container_name, folder_prefix })
window.blobStorage.loadConfig()
window.blobStorage.getStatus()

// Upload
await window.blobStorage.uploadImage(file, taskName)

// URLs
window.blobStorage.getBlobUrl(blobName)
window.blobStorage.getBlobUrlWithSAS(blobName)
window.blobStorage.getPreviewUrl(blobName)
```

### BlobConfigManager

```javascript
// Configuration
window.blobConfigManager.saveConfig(config)
window.blobConfigManager.loadConfig()
window.blobConfigManager.validateConfig(config)

// Testing
await window.blobConfigManager.testConnection(config)
window.blobConfigManager.getSASTokenHelp()
```

## 🆘 Troubleshooting

### "Blob storage not configured"
→ Open `blob/blob_config_ui.html` and enter credentials

### "Upload failed: 403 Forbidden"
→ SAS token expired or has wrong permissions

### "Upload failed: 404 Not Found"
→ Container doesn't exist in Azure

### "CORS error"
→ Enable CORS in Azure Portal:
1. Storage Account → Settings → Resource sharing (CORS)
2. Allowed origins: `*` or your domain
3. Allowed methods: `GET, PUT, DELETE, OPTIONS`
4. Allowed headers: `*`
5. Exposed headers: `*`

### "Upload failed: Invalid SAS token"
→ Make sure token includes all required parameters (sv, ss, srt, sp, se, etc.)

## ⚡ Performance

- **Direct Upload**: Browser → Azure (no server proxy)
- **Parallel Uploads**: Multiple images upload simultaneously
- **CDN Delivery**: Azure serves images via global CDN
- **Typical Speed**: 1-3 seconds for 1MB image

## 💰 Cost

Same as backend approach:
- Storage: ~$0.02/GB/month
- Operations: ~$0.004 per 10,000 requests
- Bandwidth: First 100GB free/month

## 🎉 Advantages vs Backend

| Feature | Frontend (SAS) | Backend (API) |
|---------|----------------|---------------|
| Server needed | ❌ No | ✅ Yes |
| Upload speed | ⚡ Direct | 🐌 Proxied |
| Scalability | 🚀 Unlimited | 📊 Server-limited |
| Complexity | ✅ Simple | ❌ Complex |
| Security | ✅ SAS token | ✅ API auth |

## 📝 Notes

- SAS tokens are stored in `localStorage` (browser only)
- Configuration doesn't sync across devices
- Works in all modern browsers
- No CORS issues if configured correctly
- Images upload in parallel
- Naming convention: `taskname_img_{timestamp}.{ext}`

## 🚀 Next Steps

1. ✅ Generate SAS token in Azure Portal
2. ✅ Open `blob_config_ui.html` and configure
3. ✅ Test with `test_blob.html`
4. ✅ Integrate in your app (3 script tags)
5. ✅ Done!

---

**No Python. No Server. No Backend. Just JavaScript!** 🎉
