"""
OneDrive integration for the Marketing Task Manager.

This module provides backup/sync of the SQLite database to OneDrive
using the Microsoft Graph API (personal or business accounts).

Setup:
1. Register an app at https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps
2. Add redirect URI: http://localhost:8501
3. API permissions: Files.ReadWrite, User.Read
4. Set your credentials in Streamlit secrets or .env

Usage in Streamlit:
    - Users authenticate via OAuth2 flow
    - DB is backed up to OneDrive on save operations
    - DB can be restored from OneDrive backup
"""

import os
import json
import time
import requests
import streamlit as st
from datetime import datetime

# OneDrive config
ONEDRIVE_FOLDER = "WylthTaskManager"
DB_BACKUP_NAME = "tasks_backup.db"
EXCEL_EXPORT_NAME = "marketing_tasks_export.xlsx"

# Microsoft Graph endpoints
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
SCOPES = "Files.ReadWrite User.Read offline_access"


def get_onedrive_config():
    """Get OneDrive OAuth config from Streamlit secrets or environment."""
    try:
        client_id = st.secrets.get("ONEDRIVE_CLIENT_ID", "") or os.environ.get("ONEDRIVE_CLIENT_ID", "")
        client_secret = st.secrets.get("ONEDRIVE_CLIENT_SECRET", "") or os.environ.get("ONEDRIVE_CLIENT_SECRET", "")
        redirect_uri = st.secrets.get("ONEDRIVE_REDIRECT_URI", "") or os.environ.get("ONEDRIVE_REDIRECT_URI", "http://localhost:8501")
    except Exception:
        client_id = os.environ.get("ONEDRIVE_CLIENT_ID", "")
        client_secret = os.environ.get("ONEDRIVE_CLIENT_SECRET", "")
        redirect_uri = os.environ.get("ONEDRIVE_REDIRECT_URI", "http://localhost:8501")
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def is_onedrive_configured():
    """Check if OneDrive credentials are set."""
    config = get_onedrive_config()
    return bool(config["client_id"])


def get_auth_url():
    """Generate the OAuth2 authorization URL."""
    config = get_onedrive_config()
    params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "redirect_uri": config["redirect_uri"],
        "scope": SCOPES,
        "response_mode": "query",
    }
    return AUTH_URL + "?" + "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())


def exchange_code_for_token(code):
    """Exchange authorization code for access token."""
    config = get_onedrive_config()
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code",
        "scope": SCOPES,
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code == 200:
        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        return token_data
    return None


def refresh_access_token(refresh_token):
    """Refresh an expired access token."""
    config = get_onedrive_config()
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": SCOPES,
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code == 200:
        token_data = resp.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        return token_data
    return None


def get_valid_token():
    """Get a valid access token, refreshing if needed."""
    if "onedrive_token" not in st.session_state:
        return None

    token_data = st.session_state.onedrive_token
    if time.time() > token_data.get("expires_at", 0) - 60:
        # Token expired, refresh it
        new_token = refresh_access_token(token_data.get("refresh_token", ""))
        if new_token:
            st.session_state.onedrive_token = new_token
            return new_token["access_token"]
        else:
            del st.session_state.onedrive_token
            return None

    return token_data["access_token"]


def get_user_info(access_token):
    """Get the authenticated user's info."""
    resp = requests.get(f"{GRAPH_BASE}/me", headers={"Authorization": f"Bearer {access_token}"})
    if resp.status_code == 200:
        return resp.json()
    return None


def ensure_folder(access_token):
    """Ensure the backup folder exists in OneDrive."""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Check if folder exists
    resp = requests.get(f"{GRAPH_BASE}/me/drive/root:/{ONEDRIVE_FOLDER}", headers=headers)
    if resp.status_code == 200:
        return True

    # Create folder
    data = {"name": ONEDRIVE_FOLDER, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"}
    resp = requests.post(f"{GRAPH_BASE}/me/drive/root/children", headers=headers, json=data)
    return resp.status_code in (200, 201, 409)


def upload_file_to_onedrive(access_token, local_path, remote_filename):
    """Upload a file to the OneDrive backup folder."""
    if not ensure_folder(access_token):
        return False, "Could not create backup folder"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
    remote_path = f"/{ONEDRIVE_FOLDER}/{remote_filename}"

    with open(local_path, "rb") as f:
        content = f.read()

    # Use simple upload for files < 4MB
    if len(content) < 4 * 1024 * 1024:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/root:{remote_path}:/content",
            headers=headers,
            data=content
        )
        if resp.status_code in (200, 201):
            return True, "Uploaded successfully"
        return False, f"Upload failed: {resp.status_code}"

    return False, "File too large for simple upload"


def download_file_from_onedrive(access_token, remote_filename, local_path):
    """Download a file from OneDrive backup folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    remote_path = f"/{ONEDRIVE_FOLDER}/{remote_filename}"

    resp = requests.get(f"{GRAPH_BASE}/me/drive/root:{remote_path}:/content", headers=headers)
    if resp.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(resp.content)
        return True, "Downloaded successfully"
    return False, f"Download failed: {resp.status_code}"


def list_backups(access_token):
    """List files in the OneDrive backup folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GRAPH_BASE}/me/drive/root:/{ONEDRIVE_FOLDER}:/children", headers=headers)
    if resp.status_code == 200:
        items = resp.json().get("value", [])
        return [(item["name"], item.get("size", 0), item.get("lastModifiedDateTime", "")) for item in items]
    return []


def backup_db_to_onedrive():
    """Backup the SQLite database to OneDrive."""
    access_token = get_valid_token()
    if not access_token:
        return False, "Not authenticated with OneDrive"

    from database import DB_PATH
    if not os.path.exists(DB_PATH):
        return False, "Database file not found"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_name = f"tasks_backup_{timestamp}.db"

    # Also upload as the "latest" backup
    success1, msg1 = upload_file_to_onedrive(access_token, DB_PATH, DB_BACKUP_NAME)
    success2, msg2 = upload_file_to_onedrive(access_token, DB_PATH, remote_name)

    if success1:
        return True, f"Backed up to OneDrive ({remote_name})"
    return False, msg1


def restore_db_from_onedrive():
    """Restore the SQLite database from OneDrive."""
    access_token = get_valid_token()
    if not access_token:
        return False, "Not authenticated with OneDrive"

    from database import DB_PATH
    success, msg = download_file_from_onedrive(access_token, DB_BACKUP_NAME, DB_PATH)
    return success, msg


def export_tasks_to_excel_onedrive(tasks):
    """Export current tasks as Excel file to OneDrive."""
    access_token = get_valid_token()
    if not access_token:
        return False, "Not authenticated with OneDrive"

    try:
        import openpyxl
        from io import BytesIO

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tasks"

        # Header
        headers = ["Date", "Content", "Type", "Platforms", "Status", "Owner", "Approval", "Comment", "Link", "Priority", "Source"]
        ws.append(headers)

        for t in tasks:
            ws.append([
                t.get('date', ''),
                t.get('content', ''),
                t.get('type', ''),
                ", ".join(t.get('platforms', [])),
                t.get('status', ''),
                t.get('owner', ''),
                t.get('approval', ''),
                t.get('comment', ''),
                t.get('link', ''),
                t.get('priority', ''),
                t.get('source', ''),
            ])

        # Save to temp file
        temp_path = "/tmp/marketing_tasks_export.xlsx"
        wb.save(temp_path)

        success, msg = upload_file_to_onedrive(access_token, temp_path, EXCEL_EXPORT_NAME)
        os.remove(temp_path)
        return success, msg
    except Exception as e:
        return False, str(e)


def render_onedrive_sidebar():
    """Render the OneDrive section in the Streamlit sidebar."""
    st.markdown("### ☁️ OneDrive Sync")

    if not is_onedrive_configured():
        st.info("OneDrive not configured. Add `ONEDRIVE_CLIENT_ID` and `ONEDRIVE_CLIENT_SECRET` to your Streamlit secrets or environment variables.")
        with st.expander("Setup Instructions"):
            st.markdown("""
            1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
            2. Click **New registration**
            3. Name: `Wylth Task Manager`
            4. Redirect URI: `http://localhost:8501` (Web)
            5. After creating, copy the **Application (client) ID**
            6. Go to **Certificates & secrets** → New client secret
            7. Add to `.streamlit/secrets.toml`:
            ```toml
            ONEDRIVE_CLIENT_ID = "your-client-id"
            ONEDRIVE_CLIENT_SECRET = "your-client-secret"
            ONEDRIVE_REDIRECT_URI = "http://localhost:8501"
            ```
            """)
        return

    # Check auth state
    access_token = get_valid_token()

    if not access_token:
        # Check if we have an auth code in query params
        query_params = st.query_params
        auth_code = query_params.get("code")

        if auth_code:
            token_data = exchange_code_for_token(auth_code)
            if token_data:
                st.session_state.onedrive_token = token_data
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Authentication failed. Please try again.")
                st.query_params.clear()

        auth_url = get_auth_url()
        st.markdown(f"[🔐 Sign in with Microsoft]({auth_url})")
        return

    # Authenticated — show user info and actions
    user_info = get_user_info(access_token)
    if user_info:
        st.success(f"Connected as **{user_info.get('displayName', 'User')}**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Backup to OneDrive", use_container_width=True):
            success, msg = backup_db_to_onedrive()
            if success:
                st.toast(f"✅ {msg}")
            else:
                st.error(msg)

    with col2:
        if st.button("📥 Restore from OneDrive", use_container_width=True):
            success, msg = restore_db_from_onedrive()
            if success:
                st.toast("✅ Database restored from OneDrive!")
                st.rerun()
            else:
                st.error(msg)

    if st.button("📊 Export Excel to OneDrive", use_container_width=True):
        from database import get_all_tasks
        tasks = get_all_tasks()
        success, msg = export_tasks_to_excel_onedrive(tasks)
        if success:
            st.toast("✅ Excel exported to OneDrive!")
        else:
            st.error(msg)

    # List backups
    with st.expander("📁 OneDrive Backups"):
        backups = list_backups(access_token)
        if backups:
            for name, size, modified in backups:
                st.text(f"{name} ({size//1024}KB) — {modified[:10]}")
        else:
            st.caption("No backups found")

    if st.button("🚪 Disconnect OneDrive", use_container_width=True):
        if "onedrive_token" in st.session_state:
            del st.session_state.onedrive_token
        st.rerun()
