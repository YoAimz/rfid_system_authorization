from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from pymongo import MongoClient
import json
import datetime
import logging
import asyncio
import os
import semver
from config import *
from card_manager import CardManager
from security_monitor import SecurityMonitor
from update_manager import UpdateManager
from vulnerability_scanner import VulnerabilityScanner
from backup_manager import BackupManager
from mqtt_handler import MQTTHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Secure RFID Access System")

# Initialize managers in correct order to handle dependencies
backup_manager = BackupManager(None)
card_manager = CardManager(backup_manager)
backup_manager.card_manager = card_manager

security_monitor = SecurityMonitor(card_manager)
update_manager = UpdateManager()
vuln_scanner = VulnerabilityScanner(card_manager)
mqtt_handler = MQTTHandler(card_manager, security_monitor)

# MongoDB connection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTIONS['cards']]
logs_collection = db[MONGO_COLLECTIONS['logs']]

# Startup Event
@app.on_event("startup")
async def startup_event():
    # Start MQTT handler
    mqtt_handler.start()
    
    # Start backup scheduler
    asyncio.create_task(backup_manager.start_scheduled_backups())
    
    logger.info("All services started successfully")

# Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    # Clean up connections and resources
    mongo_client.close()
    logger.info("System shutdown completed")

# API Endpoints for card management
@app.post("/cards/")
async def add_card(card_id: str, description: str = ""):
    if card_manager.add_card(card_id, description):
        return {"status": "success", "message": "Card added"}
    raise HTTPException(status_code=400, detail="Failed to add card")

@app.delete("/cards/{card_id}")
async def remove_card(card_id: str):
    if card_manager.remove_card(card_id):
        return {"status": "success", "message": "Card removed"}
    raise HTTPException(status_code=404, detail="Card not found")

@app.get("/cards/sync/{device_id}")
async def sync_cards(device_id: str):
    cards = card_manager.sync_cards_to_device(device_id)
    return {"device_id": device_id, "cards": cards}

# Security and monitoring
@app.get("/security/logs")
async def get_security_logs(days: int = 7):
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    return {"logs": card_manager.get_security_logs(since)}

@app.post("/security/scan")
async def run_security_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(vuln_scanner.scan_system)
    return {"status": "success", "message": "Security scan initiated"}

@app.get("/security/vulnerabilities")
async def get_vulnerabilities():
    return {"vulnerabilities": vuln_scanner.get_recent_findings()}

# Backup management
@app.post("/system/backup")
async def create_backup(background_tasks: BackgroundTasks, backup_type: str = "manual"):
    background_tasks.add_task(backup_manager.create_backup, backup_type)
    return {"status": "success", "message": f"{backup_type} backup initiated"}

@app.get("/system/backups")
async def list_backups():
    backups = backup_manager.backup_collection.find(
        {},
        {'_id': 1, 'timestamp': 1, 'type': 1}
    ).sort('timestamp', -1)
    return {"backups": list(backups)}

@app.post("/system/restore/{backup_id}")
async def restore_backup(backup_id: str):
    if await backup_manager.restore_backup(backup_id):
        return {"status": "success", "message": "System restored from backup"}
    raise HTTPException(status_code=400, detail="Restore failed")

# System updates and OTA
@app.post("/system/update")
async def upload_update(
    background_tasks: BackgroundTasks,
    version: str,
    file: UploadFile = File(...),
    changelog: str = ""
):
    if await update_manager.register_new_version(version, file, changelog):
        background_tasks.add_task(
            update_manager.process_update,
            version
        )
        return {"status": "success", "message": "Update registered"}
    raise HTTPException(status_code=400, detail="Failed to register update")

@app.get("/system/updates/available")
async def check_updates(device_id: str, current_version: str):
    updates = update_manager.get_available_updates(current_version)
    return {"updates": updates}

@app.get("/firmware/{version}")
async def get_firmware(version: str):
    """Download specific firmware version"""
    file_path = update_manager.get_firmware_file(version)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Firmware not found")
    return FileResponse(
        file_path,
        filename=f"firmware_v{version}.bin",
        media_type="application/octet-stream"
    )

@app.get("/firmware/latest")
async def get_latest_firmware():
    """Get latest firmware version info"""
    manifest = update_manager.load_manifest()
    if not manifest['versions']:
        raise HTTPException(status_code=404, detail="No firmware available")
    
    latest = max(manifest['versions'], 
                key=lambda x: semver.parse(x['version']))
    return {
        "version": latest['version'],
        "checksum": latest['checksum'],
        "size": latest['size'],
        "changelog": latest['changelog']
    }

# Access logs
@app.get("/access-logs/")
async def get_access_logs(limit: int = 100):
    logs = list(logs_collection.find(
        {}, 
        {'_id': 0}
    ).sort(
        [('server_timestamp', -1)]
    ).limit(limit))
    return {"access_logs": logs}

@app.get("/access-logs/{rfid_uid}")
async def get_access_logs_by_uid(rfid_uid: str):
    logs = list(logs_collection.find({"uid": rfid_uid}, {'_id': 0}))
    if not logs:
        raise HTTPException(status_code=404, detail="RFID not found")
    return {"access_logs": logs}

# System status and health
@app.get("/system/health")
async def health_check():
    health_status = {
        "database": "healthy" if mongo_client.admin.command('ping') else "unhealthy",
        "mqtt": "connected" if mqtt_handler.client.is_connected() else "disconnected",
        "backup_system": "running" if backup_manager.last_backup else "not initialized",
    }
    return health_status

@app.get("/system/status")
async def system_status():
    return {
        "total_cards": collection.count_documents({}),
        "total_logs": logs_collection.count_documents({}),
        "last_backup": backup_manager.get_latest_backup(),
        "system_uptime": "Running",  # Can be extended with actual uptime
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)