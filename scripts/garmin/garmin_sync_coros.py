import os
import sys 
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.split(os.path.abspath(__file__))[0]  # 当前目录
config_path = CURRENT_DIR.rsplit('/', 1)[0]  # 上三级目录
sys.path.append(config_path)

from config import DB_DIR, GARMIN_FIT_DIR
from garmin.garmin_client import GarminClient
from garmin.garmin_db import GarminDB
from coros.coros_client import CorosClient
from oss.ali_oss_client import AliOssClient
from oss.aws_oss_client import AwsOssClient
from utils.md5_utils import calculate_md5_file

SYNC_CONFIG = {
    'GARMIN_AUTH_DOMAIN': '',
    'GARMIN_EMAIL': '',
    'GARMIN_PASSWORD': '',
    'GARMIN_NEWEST_NUM': 10000,
    "COROS_EMAIL": '',
    "COROS_PASSWORD": '',
}


def init(coros_db):
    ## 判断RQ数据库是否存在
    db_path = os.path.join(DB_DIR, coros_db.garmin_db_name)
    logger.info(f"Database path: {db_path}")
    if not os.path.exists(db_path):
        ## 初始化建表
        logger.info("Initializing database...")
        coros_db.initDB()
    if not os.path.exists(GARMIN_FIT_DIR):
        logger.info(f"Creating FIT directory: {GARMIN_FIT_DIR}")
        os.mkdir(GARMIN_FIT_DIR)

if __name__ == "__main__":
   logger.info("=== Starting Garmin to Coros Sync ===")
   
   # 首先读取 面板变量 或者 github action 运行变量
  for k in SYNC_CONFIG:
      if os.getenv(k):
          v = os.getenv(k)
          SYNC_CONFIG[k] = v
  
  ## db 名称
  db_name = "garmin.db"
  ## 建立DB链接
  garmin_db = GarminDB(db_name)
  ## 初始化DB位置和下载文件位置
  init(garmin_db)

  GARMIN_EMAIL = SYNC_CONFIG["GARMIN_EMAIL"]
  GARMIN_PASSWORD = SYNC_CONFIG["GARMIN_PASSWORD"]
  GARMIN_AUTH_DOMAIN = SYNC_CONFIG["GARMIN_AUTH_DOMAIN"]
  GARMIN_NEWEST_NUM = SYNC_CONFIG["GARMIN_NEWEST_NUM"]
  logger.info(f"Garmin domain: {GARMIN_AUTH_DOMAIN}")
    
  garminClient = GarminClient(GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_AUTH_DOMAIN, GARMIN_NEWEST_NUM)

  COROS_EMAIL = SYNC_CONFIG["COROS_EMAIL"]
  COROS_PASSWORD = SYNC_CONFIG["COROS_PASSWORD"]
  corosClient = CorosClient(COROS_EMAIL, COROS_PASSWORD)
  corosClient.login()
  
  logger.info("Fetching all Garmin activities...")
  all_activities = garminClient.getAllActivities()
  if all_activities == None or len(all_activities) == 0:
      logger.warning("No activities found in Garmin account. Exiting.")
      exit(0)
  
  logger.info(f"Found {len(all_activities)} activities in Garmin")
  for activity in all_activities:
      activity_id = activity["activityId"]
      garmin_db.saveActivity(activity_id)
  logger.info("All activities saved to database")

  

  logger.info("Checking for unsynchronized activities...")
  un_sync_id_list = garmin_db.getUnSyncActivity()
  if un_sync_id_list == None or len(un_sync_id_list) == 0:
      logger.info("No unsynchronized activities found. All activities are up to date!")
      exit(0)
  
  logger.info(f"Found {len(un_sync_id_list)} activities to sync to Coros")
  file_path_list = []
  
  for un_sync_id in un_sync_id_list:
    try:
      logger.info(f"Downloading activity {un_sync_id} from Garmin...")
      file = garminClient.downloadFitActivity(un_sync_id)
      file_path = os.path.join(GARMIN_FIT_DIR, f"{un_sync_id}.zip")
      with open(file_path, "wb") as fb:
          fb.write(file)

      un_sync_info = {
        "un_sync_id": un_sync_id,
        "file_path": file_path
      }

      file_path_list.append(un_sync_info)
      logger.info(f"Activity {un_sync_id} downloaded successfully")
      
    except Exception as err:
      logger.error(f"Error downloading activity {un_sync_id}: {err}")
  
  success_count = 0
  error_count = 0
  
  for un_sync_info in file_path_list:
    try:
      client = None
      ## 中国区使用阿里云OSS
      if corosClient.regionId == 2:
         logger.info("Using AliCloud OSS")
         client = AliOssClient()
      elif corosClient.regionId == 1 or corosClient.regionId == 3:
         logger.info("Using AWS OSS")
         client = AwsOssClient()

      file_path = un_sync_info["file_path"]
      un_sync_id = un_sync_info["un_sync_id"]
      
      logger.info(f"Uploading activity {un_sync_id} to Coros OSS...")
      oss_obj = client.multipart_upload(file_path,  f"{corosClient.userId}/{calculate_md5_file(file_path)}.zip")
      size = os.path.getsize(file_path)
      
      logger.info(f"Importing activity {un_sync_id} to Coros...")
      upload_result = corosClient.uploadActivity(f"fit_zip/{corosClient.userId}/{calculate_md5_file(file_path)}.zip", calculate_md5_file(file_path), f"{un_sync_id}.zip", size)
      if upload_result:
          garmin_db.updateSyncStatus(un_sync_id)
          success_count += 1
          logger.info(f"✓ Activity {un_sync_id} successfully synced to Coros")
      else:
          garmin_db.updateExceptionSyncStatus(un_sync_id)
          error_count += 1
          logger.error(f"✗ Activity {un_sync_id} upload failed")
    except Exception as err:
      logger.error(f"✗ Error uploading activity {un_sync_id}: {err}")
      garmin_db.updateExceptionSyncStatus(un_sync_id)
      error_count += 1
  
  logger.info("=== Sync Summary ===")
  logger.info(f"Successfully synced: {success_count}")
  logger.info(f"Errors: {error_count}")
  logger.info("=== Sync Complete ===")