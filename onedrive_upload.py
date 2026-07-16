"""
OneDrive integration for uploading marketing assets.
Uses Microsoft Graph API with device code flow for authentication.
Uploads to: /Documents/Marketing Assets/
"""
import os
import json
import msal
import requests
from pathlib import Path

# Azure AD app config - using Microsoft's common multi-tenant endpoint
# You can register your own app at https://portal.azure.com > App registrations
CLIENT_ID = "YOUR_CLIENT_ID"  # Will be set via config
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Files.ReadWrite.All", "User.Read"]

TOKEN_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".onedrive_token_cache.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "onedrive_config.json")

# Target folder in OneDrive
UPLOAD_FOLDER = "/Marketing Assets"


def load_config():
    """Load OneDrive config (client_id)."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save OneDrive config."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def get_client_id():
    """Get the Azure AD client ID from config."""
    config = load_config()
    return config.get("client_id", "")


def set_client_id(client_id):
    """Set the Azure AD client ID."""
    config = load_config()
    config["client_id"] = client_id
    save_config(config)


def _get_cache():
    """Load token cache from disk."""
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, 'r') as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache):
    """Save token cache to disk."""
    if cache.has_state_changed:
        with open(TOKEN_CACHE_PATH, 'w') as f:
            f.write(cache.serialize())


def _get_app():
    """Get MSAL public client application."""
    client_id = get_client_id()
    if not client_id:
        return None
    cache = _get_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority=AUTHORITY,
        token_cache=cache
    )
    return app


def get_auth_status():
    """Check if we have a valid token."""
    app = _get_app()
    if not app:
        return {"authenticated": False, "reason": "no_client_id"}
    
    accounts = app.get_accounts()
    if not accounts:
        return {"authenticated": False, "reason": "no_account"}
    
    # Try silent token acquisition
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        return {
            "authenticated": True,
            "account": accounts[0].get("username", "Unknown")
        }
    return {"authenticated": False, "reason": "token_expired"}


def start_device_flow():
    """Initiate device code flow. Returns the flow dict with user_code and verification_uri."""
    app = _get_app()
    if not app:
        return {"error": "No client_id configured. Set it first via /api/onedrive/config."}
    
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        return {"error": f"Failed to create device flow: {flow.get('error_description', 'Unknown error')}"}
    
    return {
        "user_code": flow["user_code"],
        "verification_uri": flow["verification_uri"],
        "message": flow["message"],
        "flow": flow  # Need this to complete auth
    }


def complete_device_flow(flow):
    """Complete the device code flow after user has authenticated."""
    app = _get_app()
    if not app:
        return {"error": "No client_id configured."}
    
    result = app.acquire_token_by_device_flow(flow)
    _save_cache(app.token_cache)
    
    if "access_token" in result:
        return {
            "success": True,
            "account": result.get("id_token_claims", {}).get("preferred_username", "Authenticated")
        }
    return {
        "error": result.get("error_description", "Authentication failed")
    }


def _get_access_token():
    """Get a valid access token (silently if possible)."""
    app = _get_app()
    if not app:
        return None
    
    accounts = app.get_accounts()
    if not accounts:
        return None
    
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        _save_cache(app.token_cache)
        return result["access_token"]
    return None


def ensure_folder_exists(token):
    """Ensure the Marketing Assets folder exists in OneDrive."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if folder exists
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{UPLOAD_FOLDER}"
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        return True
    
    # Create folder
    url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    body = {
        "name": "Marketing Assets",
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail"
    }
    resp = requests.post(url, headers=headers, json=body)
    return resp.status_code in (200, 201, 409)  # 409 = already exists


def upload_file(file_bytes, filename, subfolder=None):
    """
    Upload a file to OneDrive Marketing Assets folder.
    Returns the sharing link or error.
    """
    token = _get_access_token()
    if not token:
        return {"error": "Not authenticated. Please login first."}
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Ensure base folder exists
    ensure_folder_exists(token)
    
    # Build upload path
    if subfolder:
        path = f"{UPLOAD_FOLDER}/{subfolder}/{filename}"
    else:
        path = f"{UPLOAD_FOLDER}/{filename}"
    
    # For files < 4MB, use simple upload
    if len(file_bytes) < 4 * 1024 * 1024:
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/content"
        resp = requests.put(
            url,
            headers={**headers, "Content-Type": "application/octet-stream"},
            data=file_bytes
        )
        
        if resp.status_code in (200, 201):
            item = resp.json()
            # Get sharing link
            share_link = _create_share_link(token, item["id"])
            return {
                "success": True,
                "filename": filename,
                "web_url": item.get("webUrl", ""),
                "share_link": share_link,
                "size": item.get("size", 0),
                "id": item["id"]
            }
        else:
            return {"error": f"Upload failed: {resp.status_code} - {resp.text}"}
    
    # For larger files, use upload session
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/createUploadSession"
    resp = requests.post(url, headers=headers, json={
        "item": {"@microsoft.graph.conflictBehavior": "rename"}
    })
    
    if resp.status_code not in (200, 201):
        return {"error": f"Failed to create upload session: {resp.text}"}
    
    upload_url = resp.json()["uploadUrl"]
    
    # Upload in chunks (10MB each)
    chunk_size = 10 * 1024 * 1024
    total = len(file_bytes)
    
    for i in range(0, total, chunk_size):
        chunk = file_bytes[i:i + chunk_size]
        end = min(i + chunk_size, total) - 1
        
        chunk_resp = requests.put(
            upload_url,
            headers={
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {i}-{end}/{total}"
            },
            data=chunk
        )
        
        if chunk_resp.status_code in (200, 201):
            # Final chunk - upload complete
            item = chunk_resp.json()
            share_link = _create_share_link(token, item["id"])
            return {
                "success": True,
                "filename": filename,
                "web_url": item.get("webUrl", ""),
                "share_link": share_link,
                "size": item.get("size", 0),
                "id": item["id"]
            }
        elif chunk_resp.status_code != 202:
            return {"error": f"Upload chunk failed: {chunk_resp.text}"}
    
    return {"error": "Upload failed unexpectedly"}


def _create_share_link(token, item_id):
    """Create a sharing link for a file."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/createLink"
    resp = requests.post(url, headers=headers, json={
        "type": "view",
        "scope": "organization"
    })
    if resp.status_code in (200, 201):
        return resp.json().get("link", {}).get("webUrl", "")
    return ""


def list_assets(subfolder=None):
    """List files in the Marketing Assets folder."""
    token = _get_access_token()
    if not token:
        return {"error": "Not authenticated."}
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if subfolder:
        path = f"{UPLOAD_FOLDER}/{subfolder}"
    else:
        path = UPLOAD_FOLDER
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/children"
    resp = requests.get(url, headers=headers, params={"$top": 50})
    
    if resp.status_code == 200:
        items = resp.json().get("value", [])
        return {
            "files": [
                {
                    "name": item["name"],
                    "size": item.get("size", 0),
                    "web_url": item.get("webUrl", ""),
                    "modified": item.get("lastModifiedDateTime", ""),
                    "is_folder": "folder" in item
                }
                for item in items
            ]
        }
    elif resp.status_code == 404:
        return {"files": [], "message": "Folder not found or empty"}
    else:
        return {"error": f"Failed to list: {resp.status_code}"}


def logout():
    """Remove cached tokens."""
    if os.path.exists(TOKEN_CACHE_PATH):
        os.remove(TOKEN_CACHE_PATH)
    return {"success": True, "message": "Logged out"}
