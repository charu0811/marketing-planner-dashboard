# 🚀 Blob Storage Quick Start

Get up and running with Azure Blob Storage in **5 minutes**!

## Prerequisites ✓

- [ ] Azure Storage Account created
- [ ] Container exists (e.g., "marketing-assets")
- [ ] Have Account Name and Account Key ready
- [ ] Python 3.7+ installed
- [ ] `azure-storage-blob` package installed

## Installation

```bash
# Already in requirements.txt
pip install azure-storage-blob
```

## Setup (Choose ONE method)

### Method 1: Interactive Script ⭐ Recommended
```bash
python blob/setup_blob.py
```
Follow the prompts, paste your credentials, done!

### Method 2: Web UI
```bash
python server.py
# Open browser: http://localhost:8501/blob/blob_config_ui.html
```

### Method 3: Manual Config
```bash
cp blob/blob_config.json.template blob/blob_config.json
nano blob/blob_config.json  # Edit with your credentials
```

## Test It

```bash
python blob/test_blob.py
```

Expected output:
```
============================================================
TEST 1: Checking Blob Storage Status
============================================================
Configured: True
Connected: True
✓ Account: mystorageaccount
✓ Container: marketing-assets

✓ Status check PASSED

============================================================
TEST 2: Uploading Test Image
============================================================
✓ Upload successful!
...

✓ ALL TESTS COMPLETED
```

## Verify in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: Your Storage Account → Containers → marketing-assets
3. Check folder: task-images/
4. You should see: `Test_Task_img_{timestamp}.png`

## Use in Your App

The backend is **already integrated**! ✅

### Upload from Frontend (Optional)

Add to `index.html` before `</body>`:

```html
<script src="/blob/blob_upload.js"></script>
<script>
  // Override handleFiles to use blob storage
  async function handleFiles(files) {
    await handleFilesWithBlob(files);
  }
</script>
```

## Test Upload via API

```bash
# Create a test image
echo "test" > test.txt

# Upload it
curl -X POST http://localhost:8501/api/blob/upload \
  -F "file=@test.txt" \
  -F "task_name=Test Task"
```

Expected response:
```json
{
  "success": true,
  "blob_name": "task-images/Test_Task_img_20240117_143022.txt",
  "preview_url": "https://...blob.core.windows.net/...",
  "permanent_url": "https://...blob.core.windows.net/...",
  "content_type": "text/plain",
  "size": 5
}
```

## Common Issues

### ❌ "Module 'azure' has no attribute 'storage'"
**Fix**: `pip install azure-storage-blob`

### ❌ "Connection failed: The specified container does not exist"
**Fix**: Create container in Azure Portal → Containers → "+ Container"

### ❌ "Authentication failed"
**Fix**: Verify Account Key in Azure Portal → Access keys → Show → Copy again

### ❌ "Blob storage not configured"
**Fix**: Run `python blob/setup_blob.py` and enter credentials

## Next Steps

1. ✅ Configuration complete
2. ✅ Tests passing
3. 📖 Read [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for frontend integration
4. 🎨 Customize settings in `blob_config.json`
5. 🚀 Deploy!

## Cheat Sheet

```bash
# Setup
python blob/setup_blob.py

# Test
python blob/test_blob.py

# Start server
python server.py

# Check status
curl http://localhost:8501/api/blob/status

# Upload test
curl -X POST http://localhost:8501/api/blob/upload \
  -F "file=@image.jpg" \
  -F "task_name=My Task"

# List images
curl http://localhost:8501/api/blob/list

# List for specific task
curl http://localhost:8501/api/blob/list?task_name=My%20Task
```

## Files Overview

| File | Purpose |
|------|---------|
| `blob_storage.py` | Core blob operations |
| `blob_api.py` | API endpoints |
| `blob_upload.js` | Frontend integration |
| `setup_blob.py` | Interactive setup |
| `test_blob.py` | Test suite |
| `blob_config.json` | Your credentials (gitignored) |

## Help

- **Setup issues?** → `python blob/setup_blob.py`
- **Test failing?** → `python blob/test_blob.py`
- **Frontend?** → See `INTEGRATION_GUIDE.md`
- **Architecture?** → See `ARCHITECTURE.md`

---

**Got 5 minutes?** Follow this guide and you're done! 🎉
