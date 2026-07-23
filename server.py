"""
FastAPI backend for the Marketing Task Manager.
Serves the React frontend and provides REST API for SQLite data.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import database as db
import onedrive_upload as od
import cloud_storage as cs

app = FastAPI(title="Wylth Marketing Task Manager")

# Note: Blob storage is now frontend-only (no backend routes needed)

# --- Init ---
db.init_db()
EXCEL_FILE = os.path.join(os.path.dirname(__file__), "Marketing Planner (Product Team) (2).xlsx")
# Import v2: includes features from column 8 + correct column mapping
IMPORT_VERSION = "v2_features"
if os.path.exists(EXCEL_FILE):
    conn = db.get_connection()
    version_check = db._query_scalar(conn, 
        "SELECT COUNT(*) FROM import_log WHERE filename = %s",
        "SELECT COUNT(*) FROM import_log WHERE filename = ?",
        (IMPORT_VERSION,))
    conn.close()
    if version_check == 0:
        db.import_from_excel(EXCEL_FILE)
        # Mark this version as imported
        conn = db.get_connection()
        if db.DATABASE_URL:
            cur = conn.cursor()
            cur.execute("INSERT INTO import_log (filename, imported_at, row_count) VALUES (%s, %s, %s)",
                        (IMPORT_VERSION, "auto", 0))
            cur.close()
        else:
            conn.execute("INSERT INTO import_log (filename, imported_at, row_count) VALUES (?, ?, ?)",
                         (IMPORT_VERSION, "auto", 0))
        conn.commit()
        conn.close()


# --- Models ---
class TaskCreate(BaseModel):
    content: str
    type: str = ""
    date: str = ""
    owner: str = ""
    status: str = "To Do"
    approval: str = "Draft"
    comment: str = ""
    link: str = ""
    priority: str = ""
    feature_id: str = ""
    platforms: list[str] = []


class TaskUpdate(TaskCreate):
    pass


class StatusUpdate(BaseModel):
    status: str


# --- API Routes ---
@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


@app.get("/api/tasks")
async def get_tasks():
    return db.get_all_tasks()


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    task_data = task.model_dump()
    task_data['id'] = f"t_{uuid.uuid4().hex[:10]}"
    db.create_task(task_data)
    return {"id": task_data['id'], "message": "Task created"}


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task: TaskUpdate):
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    task_data = task.model_dump()
    task_data['id'] = task_id
    db.update_task(task_id, task_data)
    return {"message": "Task updated"}


@app.patch("/api/tasks/{task_id}/status")
async def patch_status(task_id: str, body: StatusUpdate):
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    db.update_task_status(task_id, body.status)
    return {"message": f"Status updated to {body.status}"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete_task(task_id)
    return {"message": "Task deleted"}


@app.get("/api/stats")
async def get_stats():
    return db.get_stats()


@app.get("/api/platforms")
async def get_platforms():
    return db.get_all_platforms()


@app.get("/api/owners")
async def get_owners():
    return db.get_all_owners()


@app.post("/api/platforms")
async def add_platform(body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    db.add_platform(name)
    return {"message": f"Platform '{name}' added"}


@app.post("/api/owners")
async def add_owner(body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    db.add_owner(name)
    return {"message": f"Owner '{name}' added"}


# --- Feature API Routes ---
@app.get("/api/features")
async def get_features():
    return db.get_all_features()


@app.post("/api/features")
async def create_feature(body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    import uuid
    feature_id = f"feat_{uuid.uuid4().hex[:8]}"
    db.create_feature({"id": feature_id, "name": name, "release_date": body.get("release_date", ""), "comments": body.get("comments", "")})
    return {"id": feature_id, "message": f"Feature '{name}' created"}


@app.put("/api/features/{feature_id}")
async def update_feature(feature_id: str, body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    db.update_feature(feature_id, {"name": name, "release_date": body.get("release_date", ""), "comments": body.get("comments", "")})
    return {"message": f"Feature '{name}' updated"}


@app.delete("/api/features/{feature_id}")
async def delete_feature(feature_id: str):
    db.delete_feature(feature_id)
    return {"message": "Feature deleted"}


@app.post("/api/import")
async def reimport():
    if not os.path.exists(EXCEL_FILE):
        raise HTTPException(status_code=404, detail="Excel file not found")
    db.reset_db()
    db.init_db()
    count = db.import_from_excel(EXCEL_FILE)
    return {"message": f"Re-imported {count} tasks", "count": count}


# --- OneDrive API Routes ---
@app.get("/api/onedrive/status")
async def onedrive_status():
    return od.get_auth_status()


@app.post("/api/onedrive/config")
async def onedrive_config(body: dict):
    client_id = body.get("client_id", "").strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    od.set_client_id(client_id)
    return {"message": "Client ID saved"}


@app.post("/api/onedrive/login")
async def onedrive_login():
    result = od.start_device_flow()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    # Store flow temporarily for completion
    app.state.device_flow = result.get("flow")
    return {
        "user_code": result["user_code"],
        "verification_uri": result["verification_uri"],
        "message": result["message"]
    }


@app.post("/api/onedrive/login/complete")
async def onedrive_login_complete():
    flow = getattr(app.state, 'device_flow', None)
    if not flow:
        raise HTTPException(status_code=400, detail="No pending login flow. Call /api/onedrive/login first.")
    result = od.complete_device_flow(flow)
    app.state.device_flow = None
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@app.post("/api/onedrive/upload")
async def onedrive_upload(file: UploadFile = File(...), subfolder: str = Form("")):
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")
    
    result = od.upload_file(file_bytes, file.filename, subfolder or None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/onedrive/files")
async def onedrive_files(subfolder: str = ""):
    result = od.list_assets(subfolder or None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/onedrive/logout")
async def onedrive_logout():
    return od.logout()


# --- Cloud Storage API Routes (S3 / Azure Blob) ---
@app.get("/api/cloud/status")
async def cloud_status():
    return cs.get_status()


@app.post("/api/cloud/config/azure")
async def cloud_config_azure(body: dict):
    connection_string = body.get("connection_string", "").strip()
    container_name = body.get("container_name", "").strip()
    folder_prefix = body.get("folder_prefix", "marketing-assets/")
    
    if not connection_string or not container_name:
        raise HTTPException(status_code=400, detail="connection_string and container_name are required")
    
    result = cs.configure_azure(connection_string, container_name, folder_prefix)
    return result


@app.post("/api/cloud/upload")
async def cloud_upload(file: UploadFile = File(...), subfolder: str = Form("")):
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")
    
    result = cs.upload_file(file_bytes, file.filename, subfolder or None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/cloud/files")
async def cloud_files(subfolder: str = ""):
    result = cs.list_files(subfolder or None)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/cloud/preview/{file_path:path}")
async def cloud_preview(file_path: str):
    result = cs.get_preview_url(file_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/api/cloud/files/{file_path:path}")
async def cloud_delete(file_path: str):
    result = cs.delete_file(file_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/cloud/clear")
async def cloud_clear():
    return cs.clear_config()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8501))
    uvicorn.run(app, host="0.0.0.0", port=port)
