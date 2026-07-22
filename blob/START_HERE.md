# 👋 START HERE - Blob Storage (Frontend Only!)

## Welcome! 🎉

You have a **frontend-only Azure Blob Storage integration** - **NO BACKEND NEEDED!**

Direct browser uploads to Azure using SAS tokens. Pure JavaScript. Works anywhere.

## 🎯 What This Does

Uploads images from your dropzone (id="dropzone") directly to Azure Blob Storage:
- **Naming**: `taskname_img_{timestamp}.{ext}`
- **No server**: Direct browser → Azure
- **Fast**: No proxy, straight to cloud
- **Simple**: Just 3 script tags

## ⚡ Quick Setup (5 Minutes)

### Step 1: Generate SAS Token (2 min)

Go to [Azure Portal](https://portal.azure.com) → Storage Account:

1. **Security + networking** → **Shared access signature**
2. Configure:
   - Services: **Blob** ✓
   - Resource types: **Container** ✓ **Object** ✓
   - Permissions: **Read** ✓ **Write** ✓ **Delete** ✓ **List** ✓
   - Expiry: **1 year from now**
3. Click **"Generate SAS and connection string"**
4. Copy the **SAS token** (starts with `?sv=...`)

### Step 2: Enable CORS (1 min)

Same storage account → **Settings** → **CORS**:
- Allowed origins: `*`
- Allowed methods: `GET, PUT, DELETE, OPTIONS`
- Allowed headers: `*`
- Click **Save**

### Step 3: Configure (1 min)

Open `blob_config_ui.html` in browser:
- Paste SAS token + account name
- Click **Save Configuration**
- Should see ✓ Success!

### Step 4: Test It (1 min)

Open `test_blob.html` in browser:
- ✓ Test 1: Configuration OK
- ✓ Test 2: Upload image
- ✓ Test 3: View image

## ✅ Done! No Python, No Server Needed!

## 🔌 Add to Your App

```html
<!-- Add these 3 lines before </body> -->
<script src="blob/blob_storage.js"></script>
<script src="blob/blob_config.js"></script>
<script src="blob/blob_upload.js"></script>

<script>
  async function handleFiles(files) {
    await handleFilesWithBlob(files);
  }
</script>
```

Images now upload directly to Azure! 🎉

## 📖 Documentation

| File | What's Inside |
|------|---------------|
| **README_FRONTEND.md** ⭐ | Frontend-only guide |
| **SETUP_FRONTEND_ONLY.md** ⭐ | Detailed setup |
| **test_blob.html** | Browser test suite |
| **blob_config_ui.html** | Configuration UI |

## 🆘 Need Help?

**Configuration**: Open `blob_config_ui.html`
**Testing**: Open `test_blob.html`
**Guide**: Read `README_FRONTEND.md`
**CORS issues**: Check Azure CORS settings

## 🚀 Next Step

**Open this in your browser:**
```
blob/blob_config_ui.html
```

Paste your SAS token and you're done!

---

**No Python. No Backend. Just JavaScript!** 🎉
**Questions?** → `README_FRONTEND.md`
**Setup help?** → `SETUP_FRONTEND_ONLY.md`
