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
    
    # 제품1 (A16-G16)
    "products[0][type]": "A16",      # 구분
    "products[0][name]": "B16",      # 제품명
    "products[0][detail]": "C16",    # 상세정보
    "products[0][qty]": "D16",       # 수량
    "products[0][price]": "E16",     # 단가
    "products[0][total]": "F16",     # 합계
    "products[0][note]": "G16",      # 비고
    
    # 제품2 (A17-G17)
    "products[1][type]": "A17",      # 구분
    "products[1][name]": "B17",      # 제품명
    "products[1][detail]": "C17",    # 상세정보
    "products[1][qty]": "D17",       # 수량
    "products[1][price]": "E17",     # 단가
    "products[1][total]": "F17",     # 합계
    "products[1][note]": "G17",      # 비고
    
    # 제품3 (A18-G18)
    "products[2][type]": "A18",      # 구분
    "products[2][name]": "B18",      # 제품명
    "products[2][detail]": "C18",    # 상세정보
    "products[2][qty]": "D18",       # 수량
    "products[2][price]": "E18",     # 단가
    "products[2][total]": "F18",     # 합계
    "products[2][note]": "G18",      # 비고
    
    # 제품4 (A19-G19)
    "products[3][type]": "A19",      # 구분
    "products[3][name]": "B19",      # 제품명
    "products[3][detail]": "C19",    # 상세정보
    "products[3][qty]": "D19",       # 수량
    "products[3][price]": "E19",     # 단가
    "products[3][total]": "F19",     # 합계
    "products[3][note]": "G19",      # 비고
    
    # 제품5 (A20-G20)
    "products[4][type]": "A20",      # 구분
    "products[4][name]": "B20",      # 제품명
    "products[4][detail]": "C20",    # 상세정보
    "products[4][qty]": "D20",       # 수량
    "products[4][price]": "E20",     # 단가
    "products[4][total]": "F20",     # 합계
    "products[4][note]": "G20",      # 비고
    
    # 제품6 (A21-G21)
    "products[5][type]": "A21",      # 구분
    "products[5][name]": "B21",      # 제품명
    "products[5][detail]": "C21",    # 상세정보
    "products[5][qty]": "D21",       # 수량
    "products[5][price]": "E21",     # 단가
    "products[5][total]": "F21",     # 합계
    "products[5][note]": "G21",      # 비고
    
    # 제품7 (A22-G22)
    "products[6][type]": "A22",      # 구분
    "products[6][name]": "B22",      # 제품명
    "products[6][detail]": "C22",    # 상세정보
    "products[6][qty]": "D22",       # 수량
    "products[6][price]": "E22",     # 단가
    "products[6][total]": "F22",     # 합계
    "products[6][note]": "G22",      # 비고
    
    # 제품8 (A23-G23)
    "products[7][type]": "A23",      # 구분
    "products[7][name]": "B23",      # 제품명
    "products[7][detail]": "C23",    # 상세정보
    "products[7][qty]": "D23",       # 수량
    "products[7][price]": "E23",     # 단가
    "products[7][total]": "F23",     # 합계
    "products[7][note]": "G23",      # 비고
    "delivery_date": "B31",          # 납기일 (B30 → B31로 변경)
    
    # 기존 호환성을 위한 별칭
    "company_name": "F5",
    "contact_person": "F6", 
    "contact_email": "B11",
    "contact_phone": "B12",
    "project_name": "D10",
    "total_amount": "F23"
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
        
        # private_key 개행 문자 처리 (JWT 서명 오류의 주요 원인)
        if 'private_key' in info:
            private_key = info['private_key']
            print(f"원본 private_key 길이: {len(private_key)}")
            print(f"원본 private_key 시작: {private_key[:50]}...")
            print(f"\\n 포함 여부: {'\\n' in private_key}")
            
            if '\\n' in private_key:
                info['private_key'] = private_key.replace('\\n', '\n')
                print("✅ private_key 개행 문자 변환 완료")
            
            # 변환 후 확인
            converted_key = info['private_key']
            print(f"변환된 private_key 길이: {len(converted_key)}")
            print(f"변환된 private_key 시작: {converted_key[:50]}...")
            print(f"실제 개행 문자 포함 여부: {chr(10) in converted_key}")
            
            # private_key 유효성 검증
            if not info['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                print("❌ private_key 형식이 올바르지 않습니다")
                print(f"private_key 시작 부분: {info['private_key'][:100]}...")
                return None
            
            if not info['private_key'].strip().endswith('-----END PRIVATE KEY-----'):
                print("❌ private_key 끝 부분이 올바르지 않습니다")
                print(f"private_key 끝 부분: ...{info['private_key'][-100:]}")
                return None
        
        # 추가 검증
        print(f"client_email: {info.get('client_email', 'MISSING')}")
        print(f"private_key_id: {info.get('private_key_id', 'MISSING')}")
        print(f"project_id: {info.get('project_id', 'MISSING')}")
        
        # 시간 동기화 문제 해결을 위한 NTP 시간 가져오기
        import time
        from datetime import datetime, timezone
        import socket
        import struct
        
        def get_ntp_time():
            """NTP 서버에서 정확한 시간 가져오기"""
            try:
                # NTP 서버 목록 (Google, Cloudflare, NIST)
                ntp_servers = ['time.google.com', 'time.cloudflare.com', 'time.nist.gov']
                
                for server in ntp_servers:
                    try:
                        # NTP 패킷 생성
                        ntp_packet = b'\x1b' + 47 * b'\0'
                        
                        # UDP 소켓으로 NTP 서버에 요청
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                            s.settimeout(5)  # 5초 타임아웃
                            s.sendto(ntp_packet, (server, 123))
                            response = s.recv(1024)
                            
                        # NTP 응답에서 시간 추출 (바이트 40-43)
                        ntp_time = struct.unpack('!I', response[40:44])[0]
                        # NTP epoch (1900-01-01)을 Unix epoch (1970-01-01)로 변환
                        unix_time = ntp_time - 2208988800
                        
                        print(f"✅ NTP 시간 획득 성공 ({server}): {unix_time}")
                        return unix_time
                        
                    except Exception as e:
                        print(f"⚠️ NTP 서버 {server} 실패: {e}")
                        continue
                        
                print("❌ 모든 NTP 서버 접근 실패")
                return None
                
            except Exception as e:
                print(f"❌ NTP 시간 획득 실패: {e}")
                return None
        
        # NTP에서 정확한 시간 가져오기
        ntp_time = get_ntp_time()
        local_time = int(time.time())
        
        print(f"로컬 Unix 타임스탬프: {local_time}")
        print(f"NTP Unix 타임스탬프: {ntp_time}")
        
        if ntp_time:
            time_diff = abs(ntp_time - local_time)
            print(f"시간 차이: {time_diff}초")
            
            if time_diff > 30:  # 30초 이상 차이나면 경고
                print(f"⚠️ 시간 동기화 문제 감지: {time_diff}초 차이")
            
            # NTP 시간을 기준으로 datetime 생성
            ntp_datetime = datetime.fromtimestamp(ntp_time, tz=timezone.utc)
            print(f"정확한 UTC 시간: {ntp_datetime}")
        else:
            ntp_datetime = datetime.now(timezone.utc)
            print(f"로컬 UTC 시간 사용: {ntp_datetime}")
        
        # 자격증명 생성 (정확한 시간으로)
        print("자격증명 생성 시도 중...")
        try:
            # JWT 시간을 정확하게 맞추기 위한 커스텀 자격증명 생성
            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
            )
            
            # 시간 동기화를 위해 토큰 재생성 강제
            try:
                import google.auth.transport.requests
                request = google.auth.transport.requests.Request()
                
                # 토큰 만료 시간을 현재 시간보다 이전으로 설정하여 강제 새로고침
                credentials.expiry = ntp_datetime if ntp_time else datetime.now(timezone.utc)
                
                credentials.refresh(request)
                print("✅ 시간 동기화 토큰 새로고침 성공")
            except Exception as refresh_e:
                print(f"⚠️ 토큰 새로고침 실패: {refresh_e}")
                # 실패해도 계속 진행
        except Exception as cred_error:
            print(f"❌ Credentials 생성 중 오류: {cred_error}")
            print(f"오류 타입: {type(cred_error)}")
            return None
        
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