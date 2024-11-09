from datetime import datetime, timedelta
import asyncio
import json
import os
import logging
from pymongo import MongoClient
from config import *

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, card_manager):
        self.card_manager = card_manager
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.backup_collection = self.db[MONGO_COLLECTIONS['backup']]
        
        # For file backup
        self.backup_path = "backups/"
        os.makedirs(self.backup_path, exist_ok=True)
        
        # Backup settings
        self.daily_backup_hour = 2  # 02:00
        self.weekly_backup_day = 6  # Saturday
        self.monthly_backup_day = 1  # First day of month
        
        # Retention policy
        self.retention = {
            'daily': 7,      # Keep daily backups for 7 days
            'weekly': 4,     # Keep weekly backups for 4 weeks
            'monthly': 12,   # Keep monthly backups for 12 months
            'card_change': 5 # Keep the 5 most recent card change backups
        }
        
        # Initialize latest backup timestamps
        self.last_backup = {}
        
    async def start_scheduled_backups(self):
        """Start scheduled backups"""
        logger.info("Starting scheduled backup system")
        while True:
            try:
                now = datetime.now()
                
                # Check if it's time for backup
                if now.hour == self.daily_backup_hour and now.minute == 0:
                    await self.create_backup('daily')
                    
                    # Check for weekly backup
                    if now.weekday() == self.weekly_backup_day:
                        await self.create_backup('weekly')
                        
                    # Check for monthly backup
                    if now.day == self.monthly_backup_day:
                        await self.create_backup('monthly')
                        
                    # Clean up old backups
                    await self.cleanup_old_backups()
                    
                # Wait until next minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in backup scheduler: {e}")
                await asyncio.sleep(60)

    async def handle_card_change(self, change_type: str, card_id: str):
        """Handle backup on card change"""
        try:
            backup_type = f"card_{change_type}"
            await self.create_backup(backup_type, {
                'card_id': card_id,
                'change_type': change_type
            })
            logger.info(f"Created backup after {change_type} card: {card_id}")
        except Exception as e:
            logger.error(f"Failed to create backup after card change: {e}")
    
    async def create_backup(self, backup_type='daily', metadata=None):
        """Create system backup in both MongoDB and file"""
        try:
            # Get all data
            cards = list(self.db[MONGO_COLLECTIONS['cards']].find({}))
            logs = list(self.db[MONGO_COLLECTIONS['logs']].find({}))
            
            backup_data = {
                "timestamp": datetime.now(),
                "type": backup_type,
                "data": {
                    "cards": cards,
                    "logs": logs
                },
                "metadata": metadata or {}
            }
            
            # Save to MongoDB
            result = self.backup_collection.insert_one(backup_data)
            logger.info(f"{backup_type.capitalize()} backup saved to MongoDB: {result.inserted_id}")
            
            # Save as file
            filename = f"{backup_type}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.backup_path, filename)
            
            # Convert datetime to string for JSON
            backup_data["timestamp"] = backup_data["timestamp"].isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, default=str)
            logger.info(f"{backup_type.capitalize()} backup saved to file: {filepath}")
            
            # Update latest backup time
            self.last_backup[backup_type] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
            
    async def cleanup_old_backups(self):
        """Clean up old backups according to retention policy"""
        try:
            for backup_type, retention_days in self.retention.items():
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                # Keep at least X number of backups for card changes
                if backup_type.startswith('card_'):
                    # Get all card change backups sorted by date
                    backups = list(self.backup_collection.find(
                        {"type": backup_type}
                    ).sort("timestamp", -1))
                    
                    # Keep only the X most recent
                    if len(backups) > self.retention['card_change']:
                        for backup in backups[self.retention['card_change']:]:
                            # Remove from MongoDB
                            self.backup_collection.delete_one({"_id": backup["_id"]})
                            
                            # Remove corresponding file
                            for filename in os.listdir(self.backup_path):
                                if filename.startswith(f"{backup_type}_backup_"):
                                    backup_time = datetime.strptime(
                                        filename.split('_')[-1].split('.')[0],
                                        '%Y%m%d_%H%M%S'
                                    )
                                    if backup_time.isoformat() == backup["timestamp"]:
                                        os.remove(os.path.join(self.backup_path, filename))
                else:
                    # Regular time-based cleanup for other backup types
                    self.backup_collection.delete_many({
                        "type": backup_type,
                        "timestamp": {"$lt": cutoff_date}
                    })
                    
                    # Clean up file backups
                    for filename in os.listdir(self.backup_path):
                        if filename.startswith(f"{backup_type}_backup_"):
                            file_path = os.path.join(self.backup_path, filename)
                            file_date_str = filename.split('_')[2].split('.')[0]
                            file_date = datetime.strptime(file_date_str, '%Y%m%d')
                            
                            if file_date < cutoff_date:
                                os.remove(file_path)
                                logger.info(f"Removed old backup file: {filename}")
                                
            logger.info("Cleanup of old backups completed")
            
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            
    async def restore_backup(self, backup_id):
        """Restore from backup"""
        try:
            backup = self.backup_collection.find_one({"_id": backup_id})
            if not backup:
                logger.error(f"Backup not found: {backup_id}")
                return False
                
            # Restore data
            for collection_name, data in backup["data"].items():
                self.db[collection_name].delete_many({})  # Clear existing data
                if data:  # If there's data to restore
                    self.db[collection_name].insert_many(data)
            
            logger.info(f"System restored from backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def get_latest_backup(self):
        """Get latest backup"""
        return self.backup_collection.find_one(
            sort=[("timestamp", -1)]
        )

    async def validate_backup(self, backup_id):
        """Validate a specific backup"""
        try:
            backup = self.backup_collection.find_one({"_id": backup_id})
            if not backup:
                return False
                
            # Check that all required collections exist
            required_collections = ['cards', 'logs']
            for collection in required_collections:
                if collection not in backup['data']:
                    return False
                    
            # Check that data is correctly formatted
            for collection, data in backup['data'].items():
                if not isinstance(data, list):
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return False