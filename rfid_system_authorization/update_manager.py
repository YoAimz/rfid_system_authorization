from fastapi import UploadFile
import hashlib
import aiofiles
import semver
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UpdateManager:
    def __init__(self):
        self.updates_dir = "firmware_updates/"
        self.manifest_file = "update_manifest.json"
        os.makedirs(self.updates_dir, exist_ok=True)
        
    async def register_new_version(self, version: str, file: UploadFile, changelog: str):
        """Register new firmware version"""
        try:
            # Validate version format
            semver.parse(version)
            
            # Save firmware file
            file_path = os.path.join(self.updates_dir, f"firmware_v{version}.bin")
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Calculate firmware checksum
            checksum = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            
            # Update manifest with new version
            manifest = self.load_manifest()
            manifest['versions'].append({
                'version': version,
                'file': file_path,
                'checksum': checksum,
                'size': file_size,
                'changelog': changelog,
                'released': datetime.now().isoformat(),
                'status': 'testing'
            })
            
            self.save_manifest(manifest)
            logger.info(f"New firmware version {version} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register update: {e}")
            return False
    
    def get_available_updates(self, current_version: str):
        """Get list of available updates for a device"""
        try:
            manifest = self.load_manifest()
            current = semver.parse(current_version)
            
            # Filter updates newer than current version
            available_updates = []
            for ver in manifest['versions']:
                if semver.parse(ver['version']) > current:
                    available_updates.append({
                        'version': ver['version'],
                        'checksum': ver['checksum'],
                        'size': ver['size'],
                        'changelog': ver['changelog']
                    })
            
            return sorted(available_updates, 
                         key=lambda x: semver.parse(x['version']))
                         
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return []
    
    def get_firmware_file(self, version: str):
        """Get firmware file path for specific version"""
        try:
            manifest = self.load_manifest()
            for ver in manifest['versions']:
                if ver['version'] == version:
                    return ver['file']
            return None
        except Exception as e:
            logger.error(f"Error getting firmware file: {e}")
            return None

    def load_manifest(self):
        """Load update manifest"""
        if not os.path.exists(self.manifest_file):
            return {'versions': []}
        with open(self.manifest_file, 'r') as f:
            return json.load(f)
            
    def save_manifest(self, manifest):
        """Save update manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)