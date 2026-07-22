/**
 * Blob Storage Configuration Manager
 * Manages Azure Blob Storage credentials in the browser
 */

class BlobConfigManager {
  constructor() {
    this.storageKey = 'blob_storage_config';
  }

  /**
   * Load configuration from localStorage
   */
  loadConfig() {
    const stored = localStorage.getItem(this.storageKey);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse blob config:', e);
      }
    }
    return this.getDefaultConfig();
  }

  /**
   * Get default configuration
   */
  getDefaultConfig() {
    return {
      account_name: '',
      sas_token: '',
      container_name: 'marketing-assets',
      folder_prefix: 'task-images/'
    };
  }

  /**
   * Save configuration to localStorage
   */
  saveConfig(config) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(config));
      return { success: true, message: 'Configuration saved successfully' };
    } catch (e) {
      return { error: `Failed to save: ${e.message}` };
    }
  }

  /**
   * Clear configuration
   */
  clearConfig() {
    localStorage.removeItem(this.storageKey);
    return { success: true, message: 'Configuration cleared' };
  }

  /**
   * Validate configuration
   */
  validateConfig(config) {
    const errors = [];
    
    if (!config.account_name || config.account_name.trim() === '') {
      errors.push('Account name is required');
    }
    
    if (!config.sas_token || config.sas_token.trim() === '') {
      errors.push('SAS token is required');
    }
    
    if (!config.container_name || config.container_name.trim() === '') {
      errors.push('Container name is required');
    }

    // Validate SAS token format (should start with sv= or ?)
    if (config.sas_token && !config.sas_token.includes('sv=')) {
      errors.push('Invalid SAS token format');
    }

    return {
      valid: errors.length === 0,
      errors: errors
    };
  }

  /**
   * Test connection to Azure Blob Storage
   */
  async testConnection(config) {
    try {
      const { account_name, container_name, sas_token } = config;
      
      // Try to list blobs in container (with max results = 1)
      const url = `https://${account_name}.blob.core.windows.net/${container_name}?${sas_token}&restype=container&comp=list&maxresults=1`;
      
      const response = await fetch(url);
      
      if (response.ok) {
        return { 
          success: true, 
          message: 'Connection successful!',
          account: account_name,
          container: container_name
        };
      } else {
        const errorText = await response.text();
        return { 
          error: `Connection failed: ${response.status} - ${errorText}` 
        };
      }
    } catch (error) {
      return { error: `Connection failed: ${error.message}` };
    }
  }

  /**
   * Generate SAS token helper info
   */
  getSASTokenHelp() {
    return {
      title: 'How to Generate SAS Token',
      steps: [
        '1. Go to Azure Portal (portal.azure.com)',
        '2. Navigate to your Storage Account',
        '3. Go to "Security + networking" → "Shared access signature"',
        '4. Configure permissions:',
        '   - Allowed services: Blob',
        '   - Allowed resource types: Container, Object',
        '   - Allowed permissions: Read, Write, Delete, List',
        '5. Set expiry date (e.g., 1 year from now)',
        '6. Click "Generate SAS and connection string"',
        '7. Copy the "SAS token" (starts with ?sv=...)',
        '8. Paste it in the configuration'
      ],
      permissions: 'Required: Read, Write, Delete, List',
      expiry: 'Recommended: 1 year or more'
    };
  }
}

// Create global instance
window.blobConfigManager = new BlobConfigManager();

/**
 * Configure blob storage (called from UI)
 */
async function configureBlobStorage(accountName, sasToken, containerName, folderPrefix) {
  const config = {
    account_name: accountName.trim(),
    sas_token: sasToken.trim().replace(/^\?/, ''), // Remove leading ? if present
    container_name: containerName.trim() || 'marketing-assets',
    folder_prefix: folderPrefix.trim() || 'task-images/'
  };

  // Validate
  const validation = window.blobConfigManager.validateConfig(config);
  if (!validation.valid) {
    return { error: validation.errors.join(', ') };
  }

  // Test connection
  const testResult = await window.blobConfigManager.testConnection(config);
  if (testResult.error) {
    return testResult;
  }

  // Save configuration
  const saveResult = window.blobConfigManager.saveConfig(config);
  if (saveResult.error) {
    return saveResult;
  }

  // Reload blob storage client with new config
  if (window.blobStorage) {
    window.blobStorage.config = config;
  }

  return { 
    success: true, 
    message: 'Configuration saved and tested successfully!',
    ...testResult
  };
}

// Export for global use
window.configureBlobStorage = configureBlobStorage;
