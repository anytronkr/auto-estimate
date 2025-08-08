import os

# Google Sheets 설정
CREDS_PATH = "creds.json"
CELL_MAP = {
    # 기본 정보
    "estimate_date": "F5",           # 견적일자
    "estimate_number": "F6",         # 견적번호
    "supplier_person": "B11",        # 공급자-담당자
    "supplier_email": "B12",         # 공급자-이메일
    "supplier_phone": "B13",         # 공급자-전화번호
    "receiver_company": "D10",       # 수신자-회사명
    "receiver_person": "E11",        # 수신자-담당자
    "receiver_email": "E12",         # 수신자-이메일
    "receiver_phone": "E13",         # 수신자-전화번호
    
    # 제품1 (A15-G15)
    "products[0][type]": "A15",      # 구분
    "products[0][name]": "B15",      # 제품명
    "products[0][detail]": "C15",    # 상세정보
    "products[0][qty]": "D15",       # 수량
    "products[0][price]": "E15",     # 단가
    "products[0][total]": "F15",     # 합계
    "products[0][note]": "G15",      # 비고
    
    # 제품2 (A16-G16)
    "products[1][type]": "A16",      # 구분
    "products[1][name]": "B16",      # 제품명
    "products[1][detail]": "C16",    # 상세정보
    "products[1][qty]": "D16",       # 수량
    "products[1][price]": "E16",     # 단가
    "products[1][total]": "F16",     # 합계
    "products[1][note]": "G16",      # 비고
    
    # 제품3 (A17-G17)
    "products[2][type]": "A17",      # 구분
    "products[2][name]": "B17",      # 제품명
    "products[2][detail]": "C17",    # 상세정보
    "products[2][qty]": "D17",       # 수량
    "products[2][price]": "E17",     # 단가
    "products[2][total]": "F17",     # 합계
    "products[2][note]": "G17",      # 비고
    
    # 제품4 (A18-G18)
    "products[3][type]": "A18",      # 구분
    "products[3][name]": "B18",      # 제품명
    "products[3][detail]": "C18",    # 상세정보
    "products[3][qty]": "D18",       # 수량
    "products[3][price]": "E18",     # 단가
    "products[3][total]": "F18",     # 합계
    "products[3][note]": "G18",      # 비고
    
    # 제품5 (A19-G19)
    "products[4][type]": "A19",      # 구분
    "products[4][name]": "B19",      # 제품명
    "products[4][detail]": "C19",    # 상세정보
    "products[4][qty]": "D19",       # 수량
    "products[4][price]": "E19",     # 단가
    "products[4][total]": "F19",     # 합계
    "products[4][note]": "G19",      # 비고
    
    # 제품6 (A20-G20)
    "products[5][type]": "A20",      # 구분
    "products[5][name]": "B20",      # 제품명
    "products[5][detail]": "C20",    # 상세정보
    "products[5][qty]": "D20",       # 수량
    "products[5][price]": "E20",     # 단가
    "products[5][total]": "F20",     # 합계
    "products[5][note]": "G20",      # 비고
    
    # 제품7 (A21-G21)
    "products[6][type]": "A21",      # 구분
    "products[6][name]": "B21",      # 제품명
    "products[6][detail]": "C21",    # 상세정보
    "products[6][qty]": "D21",       # 수량
    "products[6][price]": "E21",     # 단가
    "products[6][total]": "F21",     # 합계
    "products[6][note]": "G21",      # 비고
    
    # 제품8 (A22-G22) - 마지막 제품은 납기일로 사용
    "products[7][type]": "A22",      # 구분
    "products[7][name]": "B22",      # 제품명
    "products[7][detail]": "C22",    # 상세정보
    "products[7][qty]": "D22",       # 수량
    "products[7][price]": "E22",     # 단가
    "products[7][total]": "F22",     # 합계
    "products[7][note]": "G22",      # 비고
    "delivery_date": "B30",          # 납기일 (올바른 위치)
    
    # 기존 호환성을 위한 별칭
    "company_name": "F5",
    "contact_person": "F6", 
    "contact_email": "B11",
    "contact_phone": "B12",
    "project_name": "D10",
    "total_amount": "F22"
}

# API 설정
API_HOST = "0.0.0.0"
API_PORT = int(os.environ.get("PORT", 9000))

# Google Sheets ID
DATA_COLLECTION_SHEET_ID = os.environ.get("DATA_COLLECTION_SHEET_ID", "1lanDTaqOzAXFQaZcqj91X6kknbpHXREH3bLQrTeVq6Q")
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