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
    import json
    from google.oauth2 import service_account
    
    # Render의 환경변수에서 JSON 문자열을 불러와 파싱
    google_creds = os.getenv("GOOGLE_CREDENTIALS")
    
    print("=== 환경 변수 디버깅 ===")
    print(f"GOOGLE_CREDENTIALS 존재: {'GOOGLE_CREDENTIALS' in os.environ}")
    print(f"GOOGLE_CREDENTIALS 길이: {len(google_creds) if google_creds else 0}")
    if google_creds:
        print(f"GOOGLE_CREDENTIALS 첫 100자: {google_creds[:100]}...")
        print(f"GOOGLE_CREDENTIALS 마지막 50자: ...{google_creds[-50:]}")
    
    if not google_creds:
        print("❌ 환경변수 GOOGLE_CREDENTIALS가 설정되지 않았습니다")
        return None
    
    try:
        # JSON 문자열 → Python 딕셔너리
        print("JSON 파싱 시도 중...")
        info = json.loads(google_creds)
        print(f"JSON 파싱 성공 - 키 개수: {len(info)}")
        print(f"JSON 키들: {list(info.keys())}")
        
        # 필수 키 확인
        required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_keys = [key for key in required_keys if key not in info]
        if missing_keys:
            print(f"❌ 필수 키 누락: {missing_keys}")
            return None
        
        # 자격증명 생성
        print("자격증명 생성 시도 중...")
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )
        
        print("✅ Google Service Account 자격증명 로드 성공")
        return credentials
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        print(f"JSON 문자열 길이: {len(google_creds)}")
        print(f"JSON 문자열 샘플: {google_creds[:200]}...")
        return None
    except Exception as e:
        print(f"❌ 자격증명 생성 오류: {e}")
        import traceback
        traceback.print_exc()
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