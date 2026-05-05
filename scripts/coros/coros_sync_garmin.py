import os
import sys 
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.split(os.path.abspath(__file__))[0]  # Current directory
config_path = CURRENT_DIR.rsplit('/', 1)[0]  # Parent directory
sys.path.append(config_path)

from coros_client import CorosClient
from config  import DB_DIR, COROS_FIT_DIR
from coros_db import CorosDB
from garmin.garmin_client import GarminClient


SYNC_CONFIG = {
    'GARMIN_AUTH_DOMAIN': '',
    'GARMIN_EMAIL': '',
    'GARMIN_PASSWORD': '',
    'GARMIN_NEWEST_NUM': 0,
    "COROS_EMAIL": '',
    "COROS_PASSWORD": '',
}

def init(coros_db):
    ## Check if database exists
    db_path = os.path.join(DB_DIR, coros_db.coros_db_name)
    logger.info(f"Database path: {db_path}")
    if not os.path.exists(db_path):
        ## Initialize database tables
        logger.info("Initializing database...")
        coros_db.initDB()
    if not os.path.exists(COROS_FIT_DIR):
        logger.info(f"Creating FIT directory: {COROS_FIT_DIR}")
        os.mkdir(COROS_FIT_DIR)


if __name__ == "__main__":
  logger.info("=== Starting Coros to Garmin Sync ===")
  
  # Read panel variables or GitHub Action environment variables
  for k in SYNC_CONFIG:
      if os.getenv(k):
          v = os.getenv(k)
          SYNC_CONFIG[k] = v

  COROS_EMAIL = SYNC_CONFIG["COROS_EMAIL"]
  COROS_PASSWORD = SYNC_CONFIG["COROS_PASSWORD"]
  corosClient = CorosClient(COROS_EMAIL, COROS_PASSWORD)

  GARMIN_EMAIL = SYNC_CONFIG["GARMIN_EMAIL"]
  GARMIN_PASSWORD = SYNC_CONFIG["GARMIN_PASSWORD"]
  GARMIN_AUTH_DOMAIN = SYNC_CONFIG["GARMIN_AUTH_DOMAIN"]
  GARMIN_NEWEST_NUM = SYNC_CONFIG["GARMIN_NEWEST_NUM"]
  logger.info(f"Garmin domain: {GARMIN_AUTH_DOMAIN}")

  garminClient = GarminClient(GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_AUTH_DOMAIN, GARMIN_NEWEST_NUM)
  # Immediate login to detect errors early
  garminClient._ensure_login()
  logger.info("Garmin client authenticated successfully")


  ## Database name
  db_name = "coros.db"
  ## Create DB connection
  coros_db = CorosDB(db_name)
  ## Initialize database location and download file location
  init(coros_db)

  logger.info("Fetching all Coros activities...")
  all_activities = corosClient.getAllActivities()
  if all_activities == None or len(all_activities) == 0:
      logger.warning("No activities found in Coros account. Exiting.")
      exit(0)
  
  logger.info(f"Found {len(all_activities)} activities in Coros")
  for activity in all_activities:
      activity_id = activity["labelId"]
      sport_type = activity["sportType"]
      coros_db.saveActivity(activity_id, sport_type)
  logger.info("All activities saved to database")



  logger.info("Checking for unsynchronized activities...")
  un_sync_list = coros_db.getUnSyncActivity()
  if un_sync_list == None or len(un_sync_list) == 0:
      logger.info("No unsynchronized activities found. All activities are up to date!")
      exit(0)
  
  logger.info(f"Found {len(un_sync_list)} activities to sync to Garmin")
  success_count = 0
  duplicate_count = 0
  error_count = 0
  
  for un_sync in un_sync_list:
    try:
      id = un_sync["id"]
      sport_type = un_sync["sportType"]
      logger.info(f"Processing activity {id} (sport type: {sport_type})")
      
      logger.info(f"Downloading activity {id} from Coros...")
      file = corosClient.downloadActivitie(id, sport_type)
      file_path = os.path.join(COROS_FIT_DIR, f"{id}.fit")
      with open(file_path, "wb") as fb:
          fb.write(file.data)
      logger.info(f"Activity {id} downloaded successfully")
      
      logger.info(f"Uploading activity {id} to Garmin...")
      upload_status = garminClient.upload_activity(file_path)
      logger.info(f"Activity {id}.fit upload status: {upload_status}")
      
      if upload_status == "SUCCESS":
        coros_db.updateSyncStatus(id)
        success_count += 1
        logger.info(f"✓ Activity {id} successfully synced to Garmin")
      elif upload_status == "DUPLICATE_ACTIVITY":
        coros_db.updateSyncStatus(id)
        duplicate_count += 1
        logger.info(f"⊘ Activity {id} already exists in Garmin")
      else:
        coros_db.updateExceptionSyncStatus(id)
        error_count += 1
        logger.error(f"✗ Activity {id} upload failed with status: {upload_status}")
      
    except Exception as err:
      logger.error(f"✗ Error processing activity {id}: {err}")
      coros_db.updateExceptionSyncStatus(id)
      error_count += 1
  
  logger.info("=== Sync Summary ===")
  logger.info(f"Successfully synced: {success_count}")
  logger.info(f"Duplicates skipped: {duplicate_count}")
  logger.info(f"Errors: {error_count}")
  logger.info("=== Sync Complete ===")