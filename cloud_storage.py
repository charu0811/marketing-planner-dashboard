"""
Cloud Storage integration for marketing assets.
Supports AWS S3 and Azure Blob Storage.
"""
import os
import json
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "cloud_storage_config.json")

# Default config structure
DEFAULT_CONFIG = {
    "provider": "",  # "s3" or "azure"
    "s3": {
        "access_key_id": "",
        "secret_access_key": "",
        "bucket_name": "",
        "region": "us-east-1",
        "folder_prefix": "marketing-assets/"
    },
    "azure": {
        "connection_string": "",
        "container_name": "",
        "folder_prefix": "marketing-assets/"
    }
}


def load_config() -> Dict[str, Any]:
    """Load cloud storage config."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            # Merge with defaults for any missing keys
            for key in DEFAULT_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_CONFIG[key]
            return config
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """Save cloud storage config."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def get_status() -> Dict[str, Any]:
    """Get current cloud storage status and configuration."""
    config = load_config()
    provider = config.get("provider", "")
    
    if not provider:
        return {
            "configured": False,
            "provider": None,
            "message": "No cloud storage configured. Choose S3 or Azure."
        }
    
    if provider == "s3":
        s3_config = config.get("s3", {})
        if s3_config.get("access_key_id") and s3_config.get("bucket_name"):
            # Test connection
            try:
                import boto3
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=s3_config["access_key_id"],
                    aws_secret_access_key=s3_config["secret_access_key"],
                    region_name=s3_config.get("region", "us-east-1")
                )
                s3.head_bucket(Bucket=s3_config["bucket_name"])
                return {
                    "configured": True,
                    "provider": "s3",
                    "bucket": s3_config["bucket_name"],
                    "region": s3_config.get("region", "us-east-1"),
                    "connected": True
                }
            except Exception as e:
                return {
                    "configured": True,
                    "provider": "s3",
                    "bucket": s3_config["bucket_name"],
                    "connected": False,
                    "error": str(e)
                }
        return {
            "configured": False,
            "provider": "s3",
            "message": "S3 credentials not fully configured."
        }
    
    elif provider == "azure":
        azure_config = config.get("azure", {})
        if azure_config.get("connection_string") and azure_config.get("container_name"):
            try:
                from azure.storage.blob import BlobServiceClient
                blob_service = BlobServiceClient.from_connection_string(
                    azure_config["connection_string"]
                )
                container = blob_service.get_container_client(azure_config["container_name"])
                container.get_container_properties()
                return {
                    "configured": True,
                    "provider": "azure",
                    "container": azure_config["container_name"],
                    "connected": True
                }
            except Exception as e:
                return {
                    "configured": True,
                    "provider": "azure",
                    "container": azure_config["container_name"],
                    "connected": False,
                    "error": str(e)
                }
        return {
            "configured": False,
            "provider": "azure",
            "message": "Azure credentials not fully configured."
        }
    
    return {
        "configured": False,
        "provider": None,
        "message": "Invalid provider configured."
    }


def configure_s3(access_key_id: str, secret_access_key: str, bucket_name: str, 
                 region: str = "us-east-1", folder_prefix: str = "marketing-assets/"):
    """Configure AWS S3 storage."""
    config = load_config()
    config["provider"] = "s3"
    config["s3"] = {
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
        "bucket_name": bucket_name,
        "region": region,
        "folder_prefix": folder_prefix.rstrip('/') + '/' if folder_prefix else ""
    }
    save_config(config)
    return {"success": True, "message": "S3 configured successfully."}


def configure_azure(connection_string: str, container_name: str, 
                    folder_prefix: str = "marketing-assets/"):
    """Configure Azure Blob Storage."""
    config = load_config()
    config["provider"] = "azure"
    config["azure"] = {
        "connection_string": connection_string,
        "container_name": container_name,
        "folder_prefix": folder_prefix.rstrip('/') + '/' if folder_prefix else ""
    }
    save_config(config)
    return {"success": True, "message": "Azure Blob Storage configured successfully."}


def _get_s3_client():
    """Get an S3 client."""
    config = load_config()
    s3_config = config.get("s3", {})
    
    import boto3
    return boto3.client(
        's3',
        aws_access_key_id=s3_config["access_key_id"],
        aws_secret_access_key=s3_config["secret_access_key"],
        region_name=s3_config.get("region", "us-east-1")
    )


def _get_azure_client():
    """Get Azure Blob container client."""
    config = load_config()
    azure_config = config.get("azure", {})
    
    from azure.storage.blob import BlobServiceClient
    blob_service = BlobServiceClient.from_connection_string(
        azure_config["connection_string"]
    )
    return blob_service.get_container_client(azure_config["container_name"])


def upload_file(file_bytes: bytes, filename: str, subfolder: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload a file to the configured cloud storage.
    Returns the URL and metadata or error.
    """
    config = load_config()
    provider = config.get("provider", "")
    
    if not provider:
        return {"error": "No cloud storage configured."}
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'
    
    # Generate unique filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{filename}"
    
    if provider == "s3":
        return _upload_to_s3(file_bytes, safe_filename, subfolder, content_type, config)
    elif provider == "azure":
        return _upload_to_azure(file_bytes, safe_filename, subfolder, content_type, config)
    
    return {"error": f"Unknown provider: {provider}"}


def _upload_to_s3(file_bytes: bytes, filename: str, subfolder: Optional[str], 
                  content_type: str, config: Dict) -> Dict[str, Any]:
    """Upload to AWS S3."""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_config = config["s3"]
        s3 = _get_s3_client()
        bucket = s3_config["bucket_name"]
        prefix = s3_config.get("folder_prefix", "")
        
        # Build the key (path in S3)
        if subfolder:
            key = f"{prefix}{subfolder}/{filename}"
        else:
            key = f"{prefix}{filename}"
        
        # Upload with content type
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        
        # Generate a presigned URL for preview (valid for 7 days)
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=7 * 24 * 3600  # 7 days
        )
        
        # Also get the permanent S3 URI
        region = s3_config.get("region", "us-east-1")
        permanent_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        
        return {
            "success": True,
            "filename": filename,
            "key": key,
            "preview_url": url,
            "permanent_url": permanent_url,
            "content_type": content_type,
            "size": len(file_bytes),
            "provider": "s3"
        }
    except Exception as e:
        return {"error": f"S3 upload failed: {str(e)}"}


def _upload_to_azure(file_bytes: bytes, filename: str, subfolder: Optional[str],
                     content_type: str, config: Dict) -> Dict[str, Any]:
    """Upload to Azure Blob Storage."""
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
        from datetime import timezone
        
        azure_config = config["azure"]
        prefix = azure_config.get("folder_prefix", "")
        container_name = azure_config["container_name"]
        
        # Build the blob name (path in container)
        if subfolder:
            blob_name = f"{prefix}{subfolder}/{filename}"
        else:
            blob_name = f"{prefix}{filename}"
        
        blob_service = BlobServiceClient.from_connection_string(
            azure_config["connection_string"]
        )
        container = blob_service.get_container_client(container_name)
        blob = container.get_blob_client(blob_name)
        
        # Upload with content type
        content_settings = ContentSettings(content_type=content_type)
        blob.upload_blob(file_bytes, content_settings=content_settings, overwrite=True)
        
        # Generate SAS URL for preview (valid for 7 days)
        # Extract account details from connection string
        conn_str_parts = dict(x.split('=', 1) for x in azure_config["connection_string"].split(';') if '=' in x)
        account_name = conn_str_parts.get("AccountName", "")
        account_key = conn_str_parts.get("AccountKey", "")
        
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        preview_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        permanent_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        
        return {
            "success": True,
            "filename": filename,
            "blob_name": blob_name,
            "preview_url": preview_url,
            "permanent_url": permanent_url,
            "content_type": content_type,
            "size": len(file_bytes),
            "provider": "azure"
        }
    except Exception as e:
        return {"error": f"Azure upload failed: {str(e)}"}


def list_files(subfolder: Optional[str] = None) -> Dict[str, Any]:
    """List files in cloud storage."""
    config = load_config()
    provider = config.get("provider", "")
    
    if not provider:
        return {"error": "No cloud storage configured."}
    
    if provider == "s3":
        return _list_s3_files(subfolder, config)
    elif provider == "azure":
        return _list_azure_files(subfolder, config)
    
    return {"error": f"Unknown provider: {provider}"}


def _list_s3_files(subfolder: Optional[str], config: Dict) -> Dict[str, Any]:
    """List files from S3."""
    try:
        s3_config = config["s3"]
        s3 = _get_s3_client()
        bucket = s3_config["bucket_name"]
        prefix = s3_config.get("folder_prefix", "")
        
        if subfolder:
            prefix = f"{prefix}{subfolder}/"
        
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
        
        files = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            # Skip "folder" objects
            if key.endswith('/'):
                continue
            
            # Get filename from key
            filename = key.split('/')[-1]
            
            # Generate presigned URL
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=7 * 24 * 3600
            )
            
            # Determine file type
            content_type, _ = mimetypes.guess_type(filename)
            
            files.append({
                "name": filename,
                "key": key,
                "size": obj['Size'],
                "last_modified": obj['LastModified'].isoformat(),
                "preview_url": url,
                "content_type": content_type or "application/octet-stream",
                "is_previewable": _is_previewable(content_type)
            })
        
        return {
            "files": files,
            "provider": "s3",
            "bucket": bucket,
            "prefix": prefix
        }
    except Exception as e:
        return {"error": f"S3 list failed: {str(e)}"}


def _list_azure_files(subfolder: Optional[str], config: Dict) -> Dict[str, Any]:
    """List files from Azure Blob Storage."""
    try:
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import timezone
        
        azure_config = config["azure"]
        container_name = azure_config["container_name"]
        prefix = azure_config.get("folder_prefix", "")
        
        if subfolder:
            prefix = f"{prefix}{subfolder}/"
        
        container = _get_azure_client()
        blobs = container.list_blobs(name_starts_with=prefix)
        
        # Extract account details
        conn_str_parts = dict(x.split('=', 1) for x in azure_config["connection_string"].split(';') if '=' in x)
        account_name = conn_str_parts.get("AccountName", "")
        account_key = conn_str_parts.get("AccountKey", "")
        
        files = []
        for blob in blobs:
            # Skip "folder" markers
            if blob.name.endswith('/'):
                continue
            
            filename = blob.name.split('/')[-1]
            content_type, _ = mimetypes.guess_type(filename)
            
            # Generate SAS URL
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob.name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(days=7)
            )
            
            preview_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob.name}?{sas_token}"
            
            files.append({
                "name": filename,
                "blob_name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                "preview_url": preview_url,
                "content_type": content_type or "application/octet-stream",
                "is_previewable": _is_previewable(content_type)
            })
        
        return {
            "files": files,
            "provider": "azure",
            "container": container_name,
            "prefix": prefix
        }
    except Exception as e:
        return {"error": f"Azure list failed: {str(e)}"}


def _is_previewable(content_type: Optional[str]) -> bool:
    """Check if a file type can be previewed in browser."""
    if not content_type:
        return False
    return content_type.startswith(('image/', 'video/', 'audio/', 'application/pdf', 'text/'))


def delete_file(key_or_blob: str) -> Dict[str, Any]:
    """Delete a file from cloud storage."""
    config = load_config()
    provider = config.get("provider", "")
    
    if not provider:
        return {"error": "No cloud storage configured."}
    
    if provider == "s3":
        try:
            s3_config = config["s3"]
            s3 = _get_s3_client()
            s3.delete_object(Bucket=s3_config["bucket_name"], Key=key_or_blob)
            return {"success": True, "deleted": key_or_blob}
        except Exception as e:
            return {"error": f"S3 delete failed: {str(e)}"}
    
    elif provider == "azure":
        try:
            container = _get_azure_client()
            blob = container.get_blob_client(key_or_blob)
            blob.delete_blob()
            return {"success": True, "deleted": key_or_blob}
        except Exception as e:
            return {"error": f"Azure delete failed: {str(e)}"}
    
    return {"error": f"Unknown provider: {provider}"}


def get_preview_url(key_or_blob: str) -> Dict[str, Any]:
    """Get a fresh preview URL for a specific file."""
    config = load_config()
    provider = config.get("provider", "")
    
    if not provider:
        return {"error": "No cloud storage configured."}
    
    if provider == "s3":
        try:
            s3_config = config["s3"]
            s3 = _get_s3_client()
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3_config["bucket_name"], 'Key': key_or_blob},
                ExpiresIn=7 * 24 * 3600
            )
            return {"url": url, "provider": "s3"}
        except Exception as e:
            return {"error": f"S3 URL generation failed: {str(e)}"}
    
    elif provider == "azure":
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import timezone
            
            azure_config = config["azure"]
            container_name = azure_config["container_name"]
            
            conn_str_parts = dict(x.split('=', 1) for x in azure_config["connection_string"].split(';') if '=' in x)
            account_name = conn_str_parts.get("AccountName", "")
            account_key = conn_str_parts.get("AccountKey", "")
            
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=key_or_blob,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(days=7)
            )
            
            url = f"https://{account_name}.blob.core.windows.net/{container_name}/{key_or_blob}?{sas_token}"
            return {"url": url, "provider": "azure"}
        except Exception as e:
            return {"error": f"Azure URL generation failed: {str(e)}"}
    
    return {"error": f"Unknown provider: {provider}"}


def clear_config():
    """Clear all cloud storage configuration."""
    save_config(DEFAULT_CONFIG.copy())
    return {"success": True, "message": "Cloud storage configuration cleared."}
