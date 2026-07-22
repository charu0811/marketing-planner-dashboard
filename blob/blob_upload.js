/**
 * Blob Storage Upload Integration for Dropzone (Frontend Only)
 *
 * Direct upload to Azure Blob Storage from browser - NO BACKEND NEEDED!
 * Uses Azure Blob Storage REST API with SAS token authentication
 *
 * Prerequisites:
 * 1. Include blob_storage.js before this file
 * 2. Configure credentials via blob_config_ui.html or JavaScript
 *
 * Usage: Include this script after blob_storage.js in your HTML
 */

// Store blob URLs for each asset
const assetBlobUrls = new Map();

/**
 * Upload image directly to Azure Blob Storage (no backend)
 * @param {File} file - The image file to upload
 * @param {string} taskName - The task name for blob naming
 * @returns {Promise<Object>} Upload result with preview_url
 */
async function uploadToBlobStorage(file, taskName) {
  if (!window.blobStorage) {
    console.error('Blob storage client not initialized');
    return { error: 'Blob storage not initialized. Include blob_storage.js first.' };
  }

  try {
    const result = await window.blobStorage.uploadImage(file, taskName || 'untitled');
    return result;
  } catch (error) {
    console.error('Blob upload error:', error);
    return { error: error.message };
  }
}

/**
 * Get preview URL for a blob
 * @param {string} blobName - The blob name
 * @returns {string} Preview URL with SAS token
 */
function getBlobPreviewUrl(blobName) {
  if (!window.blobStorage) {
    console.error('Blob storage client not initialized');
    return null;
  }

  const result = window.blobStorage.getPreviewUrl(blobName);
  return result.success ? result.url : null;
}

/**
 * Check blob storage status (frontend only)
 * @returns {Object} Status object
 */
function checkBlobStatus() {
  if (!window.blobStorage) {
    return { configured: false, message: 'Blob storage not initialized' };
  }
  return window.blobStorage.getStatus();
}

/**
 * Enhanced handleFiles function that uploads to blob storage (frontend only)
 * Replace the existing handleFiles function in index.html with this
 */
async function handleFilesWithBlob(files) {
  const MAX = 3.5 * 1024 * 1024;

  // Check if blob storage is configured
  const blobStatus = checkBlobStatus();
  const useBlobStorage = blobStatus.configured;
  
  // Get current task name for blob naming
  const taskNameInput = document.getElementById('taskName');
  const taskName = taskNameInput ? taskNameInput.value.trim() || 'untitled' : 'untitled';
  
  for (const file of files) {
    if (file.size > MAX) {
      showToast(`${file.name} is too large (max ~3.5MB)`);
      continue;
    }
    
    // Read file as data URL for local preview
    const dataUrl = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
    
    const assetId = uid('a');
    const meta = {
      id: assetId,
      name: file.name,
      type: file.type || 'application/octet-stream',
      size: file.size
    };
    
    // Upload to Blob Storage if configured and file is an image
    if (useBlobStorage && file.type.startsWith('image/')) {
      try {
        showToast(`Uploading ${file.name} to blob storage...`);
        const uploadResult = await uploadToBlobStorage(file, taskName);
        
        if (uploadResult.success) {
          meta.blob_url = uploadResult.preview_url;
          meta.blob_name = uploadResult.blob_name;
          meta.permanent_url = uploadResult.permanent_url;
          
          // Store the blob URL for this asset
          assetBlobUrls.set(assetId, uploadResult.preview_url);
          
          showToast(`✓ Uploaded to blob: ${file.name}`);
        }
      } catch (error) {
        console.warn('Blob upload failed, storing locally', error);
        showToast(`Blob upload failed for ${file.name}, storing locally`);
      }
    }
    
    // Upload to OneDrive if connected (existing functionality)
    if (typeof odState !== 'undefined' && odState.authenticated) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('subfolder', state.editingId || 'unsorted');
        const uploadRes = await fetch(API + '/api/onedrive/upload', { method: 'POST', body: formData });
        const uploadData = await uploadRes.json();
        if (uploadData.success) {
          meta.onedrive_url = uploadData.web_url || uploadData.share_link || '';
          meta.onedrive_id = uploadData.id || '';
        }
      } catch (e) {
        console.warn('OneDrive upload failed, storing locally', e);
      }
    }
    
    state.modalAssets.push(meta);
    
    if (state.editingId) {
      await storeAssetBlob(state.editingId, assetId, { name: file.name, type: meta.type, dataUrl });
    } else {
      state._pendingAssetBlobs = state._pendingAssetBlobs || {};
      state._pendingAssetBlobs[assetId] = { name: file.name, type: meta.type, dataUrl };
    }
  }
  
  document.getElementById('fileInput').value = '';
  renderAssetList();
}

// Export for use in index.html
if (typeof window !== 'undefined') {
  window.handleFilesWithBlob = handleFilesWithBlob;
  window.uploadToBlobStorage = uploadToBlobStorage;
  window.getBlobPreviewUrl = getBlobPreviewUrl;
  window.checkBlobStatus = checkBlobStatus;
  window.assetBlobUrls = assetBlobUrls;
}
