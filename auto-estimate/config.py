import os

# Google Sheets 설정
CREDS_PATH = "creds.json"
CELL_MAP = {
    "company_name": "B3",
    "contact_person": "B4", 
    "contact_email": "B5",
    "contact_phone": "B6",
    "project_name": "B7",
    "supplier_person": "B8",
    "total_amount": "B9",
    "products": "B10"
}

# API 설정
API_HOST = "0.0.0.0"
API_PORT = int(os.environ.get("PORT", 9000))

# Google Sheets ID
DATA_COLLECTION_SHEET_ID = "1ExR_ZCrqxPgd9GJQQ6P3CXx8Hec0KA1l_W_Hw03_gRE"
DATA_COLLECTION_COLUMNS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

# Render.com 환경변수에서 설정 읽기
def get_google_credentials():
    """환경변수에서 Google Service Account JSON 읽기"""
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
    if credentials_json:
        import json
        from google.oauth2 import service_account
        creds_dict = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    return None

def get_pipedrive_config():
    """환경변수에서 Pipedrive 설정 읽기"""
    return {
        'api_token': os.environ.get("PIPEDRIVE_API_TOKEN"),
        'domain': os.environ.get("PIPEDRIVE_DOMAIN"),
        'pipeline_id': int(os.environ.get("PIPEDRIVE_PIPELINE_ID", 4)),
        'stage_id': int(os.environ.get("PIPEDRIVE_STAGE_ID", 47)),
        'user_mapping': {
            "이훈수": 23659842,
            "차재원": 23787233,
            "장진호": 23823247,
            "하철용": 23839131,
            "노재익": 23839109,
            "전준영": 23839164
        }
    }

def get_google_drive_folder_id():
    """환경변수에서 Google Drive 폴더 ID 읽기"""
    return os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "1uMd2VH07SP1qNsrrwh8IUH4eQuQf6Z9X") 