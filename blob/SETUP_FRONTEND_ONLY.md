# ⚡ Frontend-Only Setup Guide (No Backend Required!)

## 🎉 What Changed

**Before**: Python backend with FastAPI, account keys, server-side uploads  
**Now**: Pure JavaScript, SAS tokens, direct browser uploads

### Removed Files (Python)
- ❌ `blob_storage.py` - Replaced with `blob_storage.js`
- ❌ `blob_api.py` - Not needed (no API)
- ❌ `setup_blob.py` - Replaced with HTML UI
- ❌ `test_blob.py` - Replaced with `test_blob.html`
- ❌ `__init__.py` - Not needed

### New Files (JavaScript)
- ✅ `blob_storage.js` - Core Azure Blob client
- ✅ `blob_config.js` - Configuration manager
- ✅ `blob_upload.js` - Dropzone integration (updated)
- ✅ `blob_config_ui.html` - Configuration UI (updated)
- ✅ `test_blob.html` - Browser-based test suite
- ✅ `README_FRONTEND.md` - Frontend documentation

## 🚀 Quick Setup (5 Minutes)

### Step 1: Generate SAS Token (2 min)

1. Open [Azure Portal](https://portal.azure.com)
2. Go to: **Storage Accounts → Your Account**
3. Click: **Security + networking → Shared access signature**
4. **Configure permissions**:
   ```
   Allowed services:       [✓] Blob
   Allowed resource types: [✓] Container [✓] Object
   Allowed permissions:    [✓] Read [✓] Write [✓] Delete [✓] List
   Start time:             Now
   Expiry:                 1 year from now
   Allowed protocols:      HTTPS only
   ```
5. Click: **"Generate SAS and connection string"**
6. Copy the **"SAS token"** (starts with `?sv=2021-...`)

**Important**: Copy the SAS token, not the connection string!

### Step 2: Enable CORS in Azure (1 min)

Still in Azure Portal:
1. Your Storage Account → **Settings → Resource sharing (CORS)**
2. **Blob service tab** → Add a rule:
   ```
   Allowed origins:  *
   Allowed methods:  GET, PUT, DELETE, OPTIONS
   Allowed headers:  *
   Exposed headers:  *
   Max age:          86400
   ```
3. Click **Save**

This allows browser uploads from any domain.

### Step 3: Configure in Browser (1 min)

1. Open `blob/blob_config_ui.html` in your browser
2. Fill in:
   - **Account Name**: Your Azure storage account name
   - **SAS Token**: Paste the token from Step 1
   - **Container Name**: `marketing-assets` (or your container)
   - **Folder Prefix**: `task-images/`
3. Click **"Save Configuration"**
4. Should see: ✓ Configuration saved and tested successfully!

### Step 4: Test Everything (1 min)

1. Open `blob/test_blob.html` in your browser
2. **Test 1**: Should show ✓ Configured
3. **Test 2**: Select an image and upload
4. **Test 3**: Should display the uploaded image

✅ If all tests pass, you're done!

## 🔌 Integration in Your App

### Add to `index.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Marketing Dashboard</title>
</head>
<body>
  
  <!-- Your existing HTML -->
  
  <!-- ADD THESE 3 SCRIPT TAGS BEFORE CLOSING </body> -->
  <script src="blob/blob_storage.js"></script>
  <script src="blob/blob_config.js"></script>
  <script src="blob/blob_upload.js"></script>
  
  <!-- Then override handleFiles function -->
  <script>
    async function handleFiles(files) {
      await handleFilesWithBlob(files);
    }
  </script>
  
</body>
</html>
```

That's it! Images now upload directly to Azure.

## 📊 How It Works

### Old Flow (Backend):
```
Browser → Server (Python) → Azure Blob → Server → Browser
         (slow, 2 hops)
```

### New Flow (Frontend):
```
Browser → Azure Blob
        (fast, direct)
```

### Technical Details:
1. User drops image in dropzone
2. JavaScript reads file with FileReader API
3. Creates blob name: `{taskname}_img_{timestamp}.{ext}`
4. PUT request to Azure REST API with SAS token
5. Azure stores blob and returns 201 Created
6. JavaScript gets URL and displays preview

## 🔐 Security: SAS Tokens Explained

### What is a SAS Token?
A **Shared Access Signature** is a secure URL parameter that grants time-limited access to Azure resources.

### Example SAS Token:
```
?sv=2021-06-08&ss=b&srt=co&sp=rwdl&se=2025-01-17T10:00:00Z&...
```

### Parameters:
- `sv`: Storage version
- `ss`: Services (b=blob)
- `srt`: Resource types (c=container, o=object)
- `sp`: Permissions (r=read, w=write, d=delete, l=list)
- `se`: Expiry time

### Why SAS Tokens > Account Keys?
| Feature | SAS Token | Account Key |
|---------|-----------|-------------|
| Scope | Container only | Full account |
| Expiry | Time-limited | Never expires |
| Revocable | Yes | Only by rotation |
| Frontend-safe | ✅ Yes | ❌ No |

**Never use Account Keys in frontend code!**

## ⚙️ Configuration Storage

Credentials are stored in browser's `localStorage`:

```javascript
// Stored as:
localStorage.setItem('blob_storage_config', JSON.stringify({
  account_name: 'mystorageaccount',
  sas_token: '?sv=2021-06-08&...',
  container_name: 'marketing-assets',
  folder_prefix: 'task-images/'
}));

// Retrieved with:
const config = window.blobStorage.loadConfig();
```

### Pros:
- ✅ Persists across page reloads
- ✅ No server needed
- ✅ Easy to clear/reset

### Cons:
- ❌ Not synced across devices
- ❌ User can see in DevTools (but SAS is time-limited anyway)

## 🎯 Usage Examples

### Basic Upload:
```javascript
const file = document.getElementById('fileInput').files[0];
const taskName = 'Instagram Post Q1';

const result = await window.blobStorage.uploadImage(file, taskName);

if (result.success) {
  console.log('Uploaded!');
  console.log('Preview URL:', result.preview_url);
  document.getElementById('preview').src = result.preview_url;
}
```

### Check Configuration:
```javascript
const status = window.blobStorage.getStatus();
if (!status.configured) {
  alert('Please configure blob storage first!');
  window.location.href = 'blob/blob_config_ui.html';
}
```

### Configure Programmatically:
```javascript
const result = await window.configureBlobStorage(
  'mystorageaccount',
  '?sv=2021-06-08&...',
  'marketing-assets',
  'task-images/'
);

if (result.success) {
  console.log('Configured!');
}
```

## 🆘 Troubleshooting

### Issue: "CORS error"
**Solution**: Enable CORS in Azure Portal (see Step 2 above)

### Issue: "403 Forbidden"
**Causes**:
- SAS token expired → Generate new one
- Wrong permissions → Include rwdl in SAS
- Wrong container → Check container name

### Issue: "404 Not Found"
**Causes**:
- Container doesn't exist → Create it in Azure
- Wrong account name → Check spelling

### Issue: "Configuration not saving"
**Causes**:
- Browser in private/incognito mode → Use normal mode
- localStorage disabled → Enable in browser settings

### Issue: "Upload works but preview doesn't load"
**Solution**: SAS token might be missing read permission. Regenerate with Read permission.

## 📱 Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 50+ | ✅ Supported |
| Firefox | 45+ | ✅ Supported |
| Safari | 10+ | ✅ Supported |
| Edge | 79+ | ✅ Supported |
| IE 11 | - | ❌ Not supported |

Requires: `Fetch API`, `FileReader`, `localStorage`

## 💡 Tips & Best Practices

1. **SAS Expiry**: Set to 1 year, set calendar reminder to regenerate
2. **CORS**: Use specific origins in production, not `*`
3. **File Size**: Validate before upload (10MB max in current code)
4. **Naming**: Sanitize task names (current: alphanumeric + `-_`)
5. **Error Handling**: Always check `result.success` before using URLs

## 🎊 Summary

**What you have now**:
- ✅ Pure JavaScript blob storage client
- ✅ No Python or backend needed
- ✅ Direct browser → Azure uploads
- ✅ SAS token authentication
- ✅ HTML-based configuration UI
- ✅ Browser-based test suite
- ✅ Simple 3-script integration

**What you need**:
- Azure Storage Account (free tier OK)
- SAS token (generated in 2 minutes)
- 3 script tags in your HTML

**Setup time**: ~5 minutes  
**Backend needed**: None ❌  
**Works offline**: Once configured ✅  

---

**Questions?** → See `README_FRONTEND.md`  
**Testing?** → Open `test_blob.html`  
**Configuration?** → Open `blob_config_ui.html`
