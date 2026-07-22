# Azure Blob Storage Integration

Complete Azure Blob Storage integration for the Marketing Dashboard that enables uploading task images to cloud storage with automatic naming convention `taskname_img_{timestamp}.{ext}`.

## ✨ Features

- ✅ **Cloud Upload**: Direct upload to Azure Blob Storage from dropzone
- ✅ **Smart Naming**: Auto-generates names: `{taskname}_img_{timestamp}.{ext}`
- ✅ **Preview URLs**: Generates secure SAS URLs (7-day expiry)
- ✅ **Image Validation**: Only images allowed, 10MB max size
- ✅ **CDN Delivery**: Fast global image delivery via Azure CDN
- ✅ **Easy Setup**: Interactive setup script + web UI
- ✅ **Full Testing**: Complete test suite included
- ✅ **Secure**: Config file gitignored, SAS token auth

## 🚀 Quick Start (3 Commands)

```bash
# 1. Install Azure package (already in requirements.txt)
pip install azure-storage-blob

# 2. Run interactive setup
python blob/setup_blob.py

# 3. Test everything works
python blob/test_blob.py
```

That's it! Your blob storage is configured and tested.

## 📁 What's Inside

```
blob/
├── 📘 README.md                    ← You are here
├── 📘 SETUP_SUMMARY.md             ← Quick reference guide
├── 📘 INTEGRATION_GUIDE.md         ← Detailed step-by-step instructions
├── 📘 ARCHITECTURE.md              ← System architecture & flow diagrams
│
├── 🐍 blob_storage.py              ← Core Azure Blob operations
├── 🐍 blob_api.py                  ← FastAPI routes
├── 🐍 __init__.py                  ← Package initialization
│
├── 🌐 blob_upload.js               ← Frontend JavaScript integration
├── 🌐 blob_config_ui.html          ← Web UI for configuration
│
├── 🔧 setup_blob.py                ← Interactive setup script
├── 🔧 test_blob.py                 ← Complete test suite
├── 🔧 blob_config.json.template    ← Config template
└── 🔒 blob_config.json             ← Your credentials (gitignored)
```

## 📋 Prerequisites

### You Need:
1. **Azure Storage Account** (free tier available)
2. **Account Name** and **Account Key** from Azure Portal
3. **Container** created (e.g., "marketing-assets")
4. **Python 3.7+** with `azure-storage-blob` package

### Get Credentials:
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Storage Accounts → Your Account**
3. Click: **Security + networking → Access keys**
4. Copy: **Storage account name** and one of the **keys**

## ⚙️ Configuration

### Option 1: Interactive Script (Recommended)
```bash
python blob/setup_blob.py
```
- Guides you through setup
- Tests connection automatically
- Saves config securely

### Option 2: Web UI
```bash
python server.py
# Open: http://localhost:8501/blob/blob_config_ui.html
```

### Option 3: Manual Config File
```bash
cp blob/blob_config.json.template blob/blob_config.json
# Edit blob/blob_config.json with your credentials
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python blob/test_blob.py
```

Tests include:
- ✓ Configuration status
- ✓ Connection to Azure
- ✓ Image upload
- ✓ List images
- ✓ Generate preview URLs
- ✓ Delete images

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/blob/status` | Check configuration status |
| `POST` | `/api/blob/configure` | Set credentials programmatically |
| `POST` | `/api/blob/upload` | Upload image (FormData: file, task_name) |
| `GET` | `/api/blob/preview/{blob_name}` | Get fresh SAS preview URL |
| `GET` | `/api/blob/list?task_name=...` | List images for task |
| `DELETE` | `/api/blob/delete/{blob_name}` | Delete image from blob |

### Example Usage

**Upload Image:**
```bash
curl -X POST http://localhost:8501/api/blob/upload \
  -F "file=@image.jpg" \
  -F "task_name=My Marketing Task"
```

**Get Preview URL:**
```bash
curl http://localhost:8501/api/blob/preview/task-images/My_Marketing_Task_img_20240117_143022.jpg
```

## 🎯 Image Naming

Images are automatically named using this pattern:
```
{folder_prefix}{sanitized_task_name}_img_{timestamp}.{ext}
```

**Examples:**
- Task: "Instagram Post Q1" → `task-images/Instagram_Post_Q1_img_20240117_143022.jpg`
- Task: "Campaign 2024!" → `task-images/Campaign_2024__img_20240117_143030.png`

## 🔗 Integration Status

✅ **Backend**: Already integrated in `server.py`
```python
from blob.blob_api import router as blob_router
app.include_router(blob_router)
```

✅ **Dependencies**: Already in `requirements.txt`
```
azure-storage-blob>=12.20.0
```

✅ **Security**: Config file already in `.gitignore`
```
blob/blob_config.json
```

## 📖 Documentation

- **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Quick reference and checklist
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Frontend integration steps
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and flow

## 🆘 Troubleshooting

### "Blob storage not configured"
```bash
python blob/setup_blob.py
# or visit http://localhost:8501/blob/blob_config_ui.html
```

### "Connection failed"
- Verify credentials in Azure Portal
- Check container exists and name is correct
- Test network connectivity to Azure

### "Upload failed"
```bash
python blob/test_blob.py  # Run diagnostics
```

### "Preview image not loading"
- SAS URLs expire after 7 days - refresh via API
- Check CORS settings if loading from different domain

## 📊 What Happens When User Uploads

```
1. User drops image in dropzone (id="dropzone")
   ↓
2. Frontend reads file + task name
   ↓
3. POST /api/blob/upload with FormData
   ↓
4. Server validates (size, type, format)
   ↓
5. Blob module sanitizes task name
   ↓
6. Upload to Azure: taskname_img_{timestamp}.{ext}
   ↓
7. Azure returns permanent URL
   ↓
8. Generate SAS URL (7-day expiry)
   ↓
9. Return to frontend: preview_url, blob_name
   ↓
10. Display preview image from blob URL
```

## 🔐 Security

- **Config File**: `blob_config.json` is gitignored
- **SAS Tokens**: Read-only, 7-day expiry
- **Validation**: File type and size checked
- **HTTPS**: All Azure connections encrypted

## 💡 Next Steps

1. ✅ Configure credentials (done above)
2. ✅ Test with test suite
3. 📱 Integrate frontend JavaScript (see `INTEGRATION_GUIDE.md`)
4. 🎨 Customize naming convention (optional)
5. 🚀 Deploy to production

## 🤝 Support

- **Issues**: Check `test_blob.py` output
- **Questions**: See `INTEGRATION_GUIDE.md`
- **Architecture**: Read `ARCHITECTURE.md`

---

**Ready to integrate?** → See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for frontend setup

**Need help?** → Run `python blob/test_blob.py` for diagnostics
