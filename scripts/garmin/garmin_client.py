import logging
import os
import time
from enum import Enum, auto
import requests
from requests.exceptions import RetryError

import garth


from .garmin_url_dict import GARMIN_URL_DICT
from config import GARMIN_TOKENS_DIR

logger = logging.getLogger(__name__)


class GarminClient:
  def __init__(self, email, password, auth_domain, newest_num):
        self.auth_domain = auth_domain
        self.email = email
        self.password = password
        self.garthClient = garth
        self.newestNum = int(newest_num)
        self.tokens_dir = GARMIN_TOKENS_DIR
        self._is_logged_in = False
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "origin": GARMIN_URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT"
        }
  
  ## Login method (called only once)
  def _ensure_login(self):
    """Ensure we are logged in to Garmin. Only connects once."""
    if self._is_logged_in:
        return
    
    # Check if already authenticated
    try:
        if hasattr(self.garthClient, 'oauth2_token') and self.garthClient.oauth2_token:
            self._is_logged_in = True
            logger.info("Garmin client already authenticated.")
            return
    except Exception:
        pass
    
    logger.info("Authenticating to Garmin Connect...")
    
    # Create tokens directory if it doesn't exist
    if not os.path.exists(self.tokens_dir):
        os.makedirs(self.tokens_dir, exist_ok=True)
        logger.info(f"Created tokens directory: {self.tokens_dir}")
    
    # Configure domain
    if self.auth_domain and str(self.auth_domain).upper() == "CN":
        self.garthClient.configure(domain="garmin.cn")
    
    # Try to resume existing session first (only if token files exist)
    token_file = os.path.join(self.tokens_dir, "oauth1_token.json")
    if os.path.exists(token_file):
        try:
            self.garthClient.resume(self.tokens_dir)
            logger.info("Garmin tokens restored from previous session.")
            self._is_logged_in = True
            return
        except Exception as e:
            logger.warning(f"Could not resume session: {e}. Will login with credentials.")
    else:
        logger.info("No existing tokens found. Will login with credentials.")
    
    # Login with credentials with retry and exponential backoff
    max_retries = 4  # 4 attempts total
    base_delay = 10  # Start with 10 seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Login attempt {attempt + 1}/{max_retries}...")
            self.garthClient.login(self.email, self.password)
            # Save tokens for future executions
            self.garthClient.save(self.tokens_dir)
            logger.info("✓ Garmin authentication successful!")
            logger.info(f"✓ Tokens saved to: {self.tokens_dir}")
            logger.info("✓ Future runs will use these tokens (no login needed)")
            self._is_logged_in = True
            return
        except RetryError as e:
            if "429" in str(e) or "too many" in str(e).lower():
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 10s, 20s, 40s
                    logger.warning(f"⚠ Rate limit hit (429). Waiting {delay} seconds before retry...")
                    logger.info(f"   (Garmin blocks frequent authentication attempts)")
                    time.sleep(delay)
                else:
                    logger.error("✗ Max retries reached. Garmin rate limit exceeded.")
                    logger.error("✗ SOLUTION: Wait 10-15 minutes before trying again.")
                    logger.error("✗ See TROUBLESHOOTING.md for detailed help.")
                    raise Exception(
                        "Garmin authentication failed: Rate limit exceeded (429). "
                        "Garmin blocks frequent authentication attempts. "
                        "Wait 10-15 minutes before trying again. "
                        "After first successful authentication, tokens will be saved and reused."
                    ) from e
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⚠ Login failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"✗ Login failed after {max_retries} attempts: {e}")
                raise
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Login failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Login failed after {max_retries} attempts: {e}")
                raise
  
  ## Login decorator (simplified)
  def login(func):    
    def ware(self, *args, **kwargs):
      self._ensure_login()
      return func(self, *args, **kwargs)
    return ware
  
  @login 
  def download(self, path, **kwargs):
     return self.garthClient.download(path, **kwargs)
  
  @login 
  def connectapi(self, path, **kwargs):
      return self.garthClient.connectapi(path, **kwargs)
     

  ## Get activities
  def getActivities(self, start:int, limit:int):
     
     params = {"start": str(start), "limit": str(limit)}
     activities =  self.connectapi(path=GARMIN_URL_DICT["garmin_connect_activities"], params=params)
     return activities;

  # ## Get all activities (alternative implementation)
  # def getAllActivities(self): 
  #   all_activities = []
  #   start = 0
  #   limit=100
  #   if 0 < self.newestNum < 100:
  #     limit = self.newestNum
      
  #   while(True):
  #     activities = self.getActivities(start=start, limit=limit)
  #     if len(activities) > 0:
  #       all_activities.extend(activities)
        
  #       if 0 < self.newestNum < 100 or start > self.newestNum:
  #          return all_activities
  #     else:
  #        return all_activities
  #     start += limit

  ## Get all activities
  def getAllActivities(self): 
    all_activities = []
    start = 0
    while(True):
      activities = self.getActivities(start=start, limit=100)
      if len(activities) > 0:
         all_activities.extend(activities)
      else:
         return all_activities
      start += 100

  ## Download activity in raw format
  def downloadFitActivity(self, activity):
    download_fit_activity_url_prefix = GARMIN_URL_DICT["garmin_connect_fit_download"]
    download_fit_activity_url = f"{download_fit_activity_url_prefix}/{activity}"
    response = self.download(download_fit_activity_url)
    return response

  @login  
  def upload_activity(self, activity_path: str):
    """Upload activity in fit format from file."""
    # This code is borrowed from python-garminconnect-enhanced ;-)
    file_base_name = os.path.basename(activity_path)
    file_extension = file_base_name.split(".")[-1]
    allowed_file_extension = (
        file_extension.upper() in ActivityUploadFormat.__members__
    )

    if allowed_file_extension:
       status = "UPLOAD_EXCEPTION"
       try:
        with open(activity_path, 'rb') as file:
          file_data = file.read()
          fields = {
              'file': (file_base_name, file_data, 'text/plain')
          }

          url_path = GARMIN_URL_DICT["garmin_connect_upload"]
          upload_url = f"https://connectapi.{self.garthClient.client.domain}{url_path}"
          self.headers['Authorization'] = str(self.garthClient.client.oauth2_token)
          response = requests.post(upload_url, headers=self.headers, files=fields)
          res_code = response.status_code
          result = response.json()
          uploadId =  result.get("detailedImportResult").get('uploadId')
          isDuplicateUpload = uploadId == None or uploadId == ''
          if res_code == 202 and not isDuplicateUpload:
              status = "SUCCESS"
          elif res_code == 409 and result.get("detailedImportResult").get("failures")[0].get('messages')[0].get('content') == "Duplicate Activity.":
              status = "DUPLICATE_ACTIVITY" 
       except Exception as e:
            logger.error(f"Upload exception: {e}")
            status = "UPLOAD_EXCEPTION"
       return status
    else:
        return "UPLOAD_EXCEPTION"
  

class ActivityUploadFormat(Enum):
  FIT = auto()
  GPX = auto()
  TCX = auto()

class GarminNoLoginException(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, status):
        """Initialize."""
        super(GarminNoLoginException, self).__init__(status)
        self.status = status
