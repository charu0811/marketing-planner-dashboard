/**
 * Azure Blob Storage Client for Frontend
 * Direct browser upload to Azure Blob Storage using SAS tokens
 * No backend server required!
 */

class BlobStorageClient {
  constructor() {
    this.config = this.loadConfig();
    this.containerClient = null;
  }

  /**
   * Load configuration from localStorage
   */
  loadConfig() {
    const stored = localStorage.getItem('blob_storage_config');
    if (stored) {
      return JSON.parse(stored);
    }
    return {
      account_name: '',
      sas_token: '', // Container-level SAS token
      container_name: 'marketing-assets',
      folder_prefix: 'task-images/'
    };
  }

  /**
   * Save configuration to localStorage
   */
  saveConfig(config) {
    this.config = { ...this.config, ...config };
    localStorage.setItem('blob_storage_config', JSON.stringify(this.config));
    this.containerClient = null; // Reset client
    return { success: true, message: 'Configuration saved' };
  }

  /**
   * Get container URL with SAS token
   */
  getContainerUrl() {
    const { account_name, container_name, sas_token } = this.config;
    if (!account_name || !sas_token) {
      return null;
    }
    return `https://${account_name}.blob.core.windows.net/${container_name}?${sas_token}`;
  }

  /**
   * Get blob URL without SAS (public if container is public)
   */
  getBlobUrl(blobName) {
    const { account_name, container_name } = this.config;
    return `https://${account_name}.blob.core.windows.net/${container_name}/${blobName}`;
  }

  /**
   * Get blob URL with SAS token for secure access
   */
  getBlobUrlWithSAS(blobName) {
    const { account_name, container_name, sas_token } = this.config;
    return `https://${account_name}.blob.core.windows.net/${container_name}/${blobName}?${sas_token}`;
  }

  /**
   * Check if blob storage is configured
   */
  getStatus() {
    const { account_name, sas_token, container_name } = this.config;
    
    if (!account_name || !sas_token) {
      return {
        configured: false,
        message: 'Blob storage not configured. Please provide account name and SAS token.'
      };
    }

    return {
      configured: true,
      connected: true, // We assume connected if configured
      account: account_name,
      container: container_name
    };
  }

  /**
   * Sanitize task name for blob naming
   */
  sanitizeTaskName(taskName) {
    return taskName.replace(/[^a-zA-Z0-9\-_]/g, '_');
  }

  /**
   * Get file type category
   */
  getFileCategory(file) {
    const type = file.type.toLowerCase();
    const ext = file.name.split('.').pop()?.toLowerCase() || '';

    if (type.startsWith('image/')) return 'img';
    if (type.startsWith('video/') || ['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)) return 'video';
    if (type === 'application/pdf' || ext === 'pdf') return 'pdf';
    if (type === 'text/html' || ext === 'html' || ext === 'htm') return 'html';
    if (type.startsWith('text/') || ['txt', 'md', 'csv'].includes(ext)) return 'doc';
    return 'file';
  }

  /**
   * Upload file to blob storage (images, videos, PDFs, HTML, etc.)
   */
  async uploadFile(file, taskName) {
    const status = this.getStatus();
    if (!status.configured) {
      return { error: status.message };
    }

    try {
      // Validate file size (100MB max for videos, 50MB for others)
      const maxSize = file.type.startsWith('video/') ? 100 * 1024 * 1024 : 50 * 1024 * 1024;
      if (file.size > maxSize) {
        const maxSizeMB = Math.round(maxSize / 1024 / 1024);
        return { error: `File too large (max ${maxSizeMB}MB)` };
      }

      // Get file category
      const category = this.getFileCategory(file);

      // Create blob name
      const ext = file.name.split('.').pop() || 'bin';
      const safeName = this.sanitizeTaskName(taskName || 'untitled');
      const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0];
      const blobFilename = `${safeName}_${category}_${timestamp}.${ext}`;
      const blobName = `${this.config.folder_prefix}${blobFilename}`;

      // Get container URL with SAS
      const containerUrl = this.getContainerUrl();
      const blobUrl = `${containerUrl.split('?')[0]}/${blobName}?${this.config.sas_token}`;

      // Upload using Fetch API
      const response = await fetch(blobUrl, {
        method: 'PUT',
        headers: {
          'x-ms-blob-type': 'BlockBlob',
          'Content-Type': file.type || 'application/octet-stream'
        },
        body: file
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} - ${errorText}`);
      }

      // Return success with URLs
      const previewUrl = this.getBlobUrlWithSAS(blobName);
      const permanentUrl = this.getBlobUrl(blobName);

      return {
        success: true,
        blob_name: blobName,
        preview_url: previewUrl,
        permanent_url: permanentUrl,
        content_type: file.type || 'application/octet-stream',
        size: file.size,
        category: category
      };

    } catch (error) {
      return { error: `Upload failed: ${error.message}` };
    }
  }

  /**
   * Upload image (alias for uploadFile with image validation)
   */
  async uploadImage(file, taskName) {
    // Validate it's an image
    if (!file.type.startsWith('image/')) {
      return { error: 'Only image files are allowed. Use uploadFile() for other types.' };
    }
    return this.uploadFile(file, taskName);
  }

  /**
   * Get preview URL for a blob (refresh SAS token)
   */
  getPreviewUrl(blobName) {
    const status = this.getStatus();
    if (!status.configured) {
      return { error: status.message };
    }

    return {
      success: true,
      url: this.getBlobUrlWithSAS(blobName),
      expires_in: 'Depends on your SAS token expiry'
    };
  }
}

// Create global instance
window.blobStorage = new BlobStorageClient();
