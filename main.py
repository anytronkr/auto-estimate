import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import gspread
from config import (
    CREDS_PATH, CELL_MAP, API_HOST, API_PORT, 
    DATA_COLLECTION_SHEET_ID, DATA_COLLECTION_COLUMNS,
    get_google_credentials, get_pipedrive_config, get_google_drive_folder_id
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import requests
import json
from datetime import datetime, timedelta
import re
import time

app = FastAPI()

# 서버 시작 시 시간대 정보 출력
@app.on_event("startup")
async def startup_event():
    import os
    import json
    print("=== 서버 시작 이벤트 시작 ===")
    
    try:
        # 시간대 환경변수 설정 (UTC로 강제)
        os.environ['TZ'] = 'UTC'
        import time
        try:
            time.tzset()  # Linux/Unix에서만 작동
        except:
            pass  # Windows에서는 무시
        
        current_time = datetime.now()
        utc_time = datetime.utcnow()
        timezone_info = os.environ.get('TZ', 'Not set')
        
        # 시간 차이 계산 수정
        time_diff = current_time - utc_time
        time_diff_seconds = abs(time_diff.total_seconds())
        
        print(f"=== 서버 시작 시간대 정보 ===")
        print(f"현재 시간: {current_time}")
        print(f"UTC 시간: {utc_time}")
        print(f"시간대 환경변수 (TZ): {timezone_info}")
        print(f"시간 차이 (초): {time_diff_seconds:.2f}초")
        print(f"시간 차이 (분): {time_diff_seconds/60:.2f}분")
        print(f"================================")
        
        # 환경 변수 확인
        print("=== 환경 변수 확인 ===")
        print(f"PORT: {os.environ.get('PORT', 'Not set')}")
        print(f"GOOGLE_CREDENTIALS 존재: {'GOOGLE_CREDENTIALS' in os.environ}")
        print(f"PIPEDRIVE_API_TOKEN 존재: {'PIPEDRIVE_API_TOKEN' in os.environ}")
        print("================================")
        
        # Google 자격증명을 creds.json 파일로 저장 (gspread용)
        print("=== Google 자격증명 파일 생성 ===")
        google_creds = os.getenv("GOOGLE_CREDENTIALS")
        if google_creds:
            try:
                # JSON 파싱하여 유효성 확인
                creds_data = json.loads(google_creds)
                
                # creds.json 파일로 저장
                with open("creds.json", "w", encoding="utf-8") as f:
                    json.dump(creds_data, f, indent=2, ensure_ascii=False)
                
                print("✅ creds.json 파일 생성 완료")
                print(f"파일 크기: {os.path.getsize('creds.json')} bytes")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON 파싱 오류: {e}")
            except Exception as e:
                print(f"❌ creds.json 파일 생성 오류: {e}")
        else:
            print("❌ GOOGLE_CREDENTIALS 환경 변수가 설정되지 않음")
        
        print("=== 서버 시작 이벤트 완료 ===")
        
    except Exception as e:
        print(f"❌ 서버 시작 중 오류: {e}")
        import traceback
        traceback.print_exc()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bitekps.com",
        "https://www.bitekps.com",
        "http://localhost:3000",  # 개발용
        "http://localhost:9000"   # 로컬 개발용
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="."), name="static")

# Google Drive API 설정
TEMPLATE_SHEET_ID = os.environ.get("TEMPLATE_SHEET_ID", "1Rf7dGonf0HgAfZ-XS3cW1Hp3V-NiOTWbt8m_qRtyzBY")
ESTIMATE_FOLDER_ID = os.environ.get("ESTIMATE_FOLDER_ID", "1WNknyHABe-co_ypAM0uGM_Z9z_62STeS")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/ping")
async def ping():
    """핑 엔드포인트"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}

def get_credentials():
    """Google Service Account 자격증명 가져오기"""
    try:
        print("자격증명 생성 중... ✅ Google Service Account 자격증명 로드 성공")
        print("✅ 환경변수에서 자격증명 로드 성공")
        print(f"- 타입: {type(get_google_credentials())}")
        
        return get_google_credentials()
    except Exception as e:
        print(f"❌ 자격증명 생성 실패: {e}")
        return None

def copy_estimate_template():
    """견적서 템플릿을 복사하여 새 파일 생성"""
    try:
        print("=== 견적서 템플릿 복사 시작 ===")
        
        creds = get_credentials()
        if not creds:
            return {"status": "error", "message": "자격증명을 가져올 수 없습니다."}
        
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        # 파일명 생성
        now = datetime.now()
        new_filename = f"견적서_DLP_{now.strftime('%y%m%d_%H%M%S')}"
        
        # 복사 메타데이터
        copy_metadata = {
            'name': new_filename,
            'parents': [ESTIMATE_FOLDER_ID]
        }
        
        print(f"템플릿 파일 ID: {TEMPLATE_SHEET_ID}")
        print(f"대상 폴더 ID: {ESTIMATE_FOLDER_ID}")
        print("파일 복사 시도 중...")
        
        # 스프레드시트 복사 (더 강력한 오류 처리)
        try:
            copied_file = service.files().copy(
                fileId=TEMPLATE_SHEET_ID,
                body=copy_metadata,
                supportsAllDrives=True,  # 공유 드라이브 지원
                fields='id,name,webViewLink'
            ).execute()
            
            new_file_id = copied_file['id']
            web_view_link = copied_file.get('webViewLink', '')
            
            print(f"견적서 템플릿 복사 완료: {new_filename} (ID: {new_file_id})")
            print(f"웹 뷰 링크: {web_view_link}")
            
            return {
                "status": "success",
                "file_id": new_file_id,
                "filename": new_filename,
                "web_view_link": web_view_link,
                "message": "견적서 템플릿이 성공적으로 복사되었습니다."
            }
            
        except Exception as copy_error:
            print(f"파일 복사 실패: {copy_error}")
            
            # 더 자세한 오류 정보 제공
            error_msg = str(copy_error)
            if "403" in error_msg:
                return {
                    "status": "error",
                    "message": "권한이 없습니다. Service Account가 템플릿 파일과 대상 폴더에 대한 편집 권한이 필요합니다."
                }
            elif "404" in error_msg:
                return {
                    "status": "error", 
                    "message": "파일 또는 폴더를 찾을 수 없습니다. ID를 확인해주세요."
                }
            else:
                return {
                    "status": "error",
                    "message": f"파일 복사 중 오류가 발생했습니다: {error_msg}"
                }
        
    except Exception as e:
        print(f"견적서 템플릿 복사 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"견적서 템플릿 복사 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/estimate")
async def fill_estimate(request: Request):
    try:
        data = await request.json()
        print(f"=== /estimate 엔드포인트 호출됨 ===")
        print(f"받은 데이터: {data}")
        print(f"estimate_date 존재: {'estimate_date' in data}")
        if 'estimate_date' in data:
            print(f"estimate_date 값: {data.get('estimate_date')}")
        
        # CELL_MAP 디버깅
        print(f"CELL_MAP 키 개수: {len(CELL_MAP)}")
        print(f"CELL_MAP 키 목록: {list(CELL_MAP.keys())}")
        print(f"'estimate_date' in CELL_MAP: {'estimate_date' in CELL_MAP}")
        print(f"'estimate_number' in CELL_MAP: {'estimate_number' in CELL_MAP}")
        
        file_id = data.get("fileId")
        
        # fileId가 없거나 템플릿 변수인 경우 새로운 템플릿 생성
        if not file_id or file_id == "{{24.id}}" or "{{" in str(file_id) or "}}" in str(file_id):
            print("fileId가 없거나 템플릿 변수입니다. 새로운 템플릿을 생성합니다.")
            template_result = copy_estimate_template()
            
            if template_result["status"] == "success":
                file_id = template_result["file_id"]
                print(f"새로운 템플릿 생성 완료: {file_id}")
            else:
                return {"status": "error", "msg": f"템플릿 생성 실패: {template_result['message']}"}
        
        if not file_id:
            return {"status": "error", "msg": "fileId 없음"}

        creds = get_credentials()
        if not creds:
            return {"status": "error", "msg": "Google Service Account 자격증명을 가져올 수 없습니다."}

        sh = gspread.service_account(filename=CREDS_PATH)
        sh = sh.open_by_key(file_id)
        ws = sh.sheet1

        # 1. 파일명 변경
        estimate_number = data.get("estimate_number", "").strip()
        if estimate_number:
            try:
                sh.update_title(estimate_number)
            except Exception as e:
                print("파일명 변경 실패:", e)

        updates = []

        # 일반 필드 (estimate_date는 사용자 입력, estimate_number는 자동 생성)
        for key in ["supplier_person", "supplier_contact", 
                    "receiver_company", "receiver_person", "receiver_contact", "delivery_date"]:
            if key in data:
                updates.append({
                    "range": CELL_MAP[key],
                    "values": [[data[key]]]
                })
        
        # estimate_date 처리 (사용자 입력값)
        if "estimate_date" in data and data.get("estimate_date"):
            if "estimate_date" in CELL_MAP:
                updates.append({
                    "range": CELL_MAP["estimate_date"],
                    "values": [[data["estimate_date"]]]
                })
            else:
                print(f"❌ CELL_MAP에 'estimate_date' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")
        else:
            # estimate_date가 없으면 현재 날짜로 설정
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            if "estimate_date" in CELL_MAP:
                updates.append({
                    "range": CELL_MAP["estimate_date"],
                    "values": [[current_date]]
                })
                print(f"estimate_date가 없어서 현재 날짜로 설정: {current_date}")
            else:
                print(f"❌ CELL_MAP에 'estimate_date' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")
        
        # estimate_number 자동 생성
        from datetime import datetime
        current_date_short = datetime.now().strftime("%y%m%d")
        supplier_person = data.get("supplier_person", "UNKNOWN")
        
        # 담당자 ID 매핑
        person_id_map = {
            "이훈수": "1", "차재원": "2", "장진호": "3", 
            "하철용": "4", "노재익": "5", "전준영": "6"
        }
        person_id = person_id_map.get(supplier_person, "0")
        
        # 오늘 발행 횟수 (현재 시간의 분으로 대체)
        today_count = datetime.now().minute
        
        auto_estimate_number = f"DLP{current_date_short}-{person_id}-{today_count}"
        if "estimate_number" in CELL_MAP:
            updates.append({
                "range": CELL_MAP["estimate_number"],
                "values": [[auto_estimate_number]]
            })
            print(f"estimate_number 자동 생성: {auto_estimate_number}")
        else:
            print(f"❌ CELL_MAP에 'estimate_number' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")

        # 제품 정보
        products = data.get("products", [])
        for i in range(8):
            product = products[i] if i < len(products) else {}
            for field in ["type", "name", "detail", "qty", "price", "total", "note"]:
                cell_key = f"products[{i}][{field}]"
                value = product.get(field, "")
                if cell_key in CELL_MAP:
                    updates.append({
                        "range": CELL_MAP[cell_key],
                        "values": [[value]]
                    })
                else:
                    print(f"❌ CELL_MAP에 '{cell_key}' 키가 없습니다.")

        ws.batch_update(updates)
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ fill_estimate 함수에서 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"견적서 생성 중 오류가 발생했습니다: {str(e)}"}

@app.get("/test-cell-map")
async def test_cell_map():
    """CELL_MAP 상태 확인용 엔드포인트"""
    try:
        return {
            "status": "success",
            "cell_map_keys": list(CELL_MAP.keys()),
            "cell_map_count": len(CELL_MAP),
            "estimate_date_exists": "estimate_date" in CELL_MAP,
            "estimate_number_exists": "estimate_number" in CELL_MAP,
            "sample_keys": {
                "estimate_date": CELL_MAP.get("estimate_date", "NOT_FOUND"),
                "estimate_number": CELL_MAP.get("estimate_number", "NOT_FOUND"),
                "supplier_person": CELL_MAP.get("supplier_person", "NOT_FOUND")
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "cell_map_type": str(type(CELL_MAP))
        }

@app.get("/")
async def root():
    """메인 페이지"""
    return FileResponse("index.html")

@app.get("/estimate_form.html")
async def estimate_form():
    """견적서 작성 폼"""
    return FileResponse("estimate_form.html")

@app.get("/preview.html")
async def preview():
    """미리보기 페이지"""
    return FileResponse("preview.html")

@app.get("/pdf-sharing.html")
async def pdf_sharing():
    """PDF 공유 페이지"""
    return FileResponse("pdf-sharing.html")

@app.post("/create-estimate-template")
async def create_estimate_template():
    """견적서 템플릿 스프레드시트를 복사하여 새 파일 생성"""
    print("=== 견적서 템플릿 생성 API 호출됨 ===")
    result = copy_estimate_template()
    print("=== 견적서 템플릿 생성 결과:", result, "===")
    return result

@app.post("/collect-data")
async def collect_data(request: Request):
    """데이터 수집용 스프레드시트에 데이터 추가"""
    print("=== /collect-data 엔드포인트 호출됨 ===")
    try:
        data = await request.json()
        print(f"받은 데이터: {data}")
        
        # Google Sheets 연결
        creds = get_credentials()
        if not creds:
            return {"status": "error", "msg": "Google Service Account 자격증명을 가져올 수 없습니다."}

        sh = gspread.service_account(filename=CREDS_PATH)
        sh = sh.open_by_key(DATA_COLLECTION_SHEET_ID)
        ws = sh.sheet1
        
        # 견적서 링크 생성
        estimate_link = f"https://docs.google.com/spreadsheets/d/{data.get('fileId', '')}/edit"
        
        # 제품 데이터 추출 (최대 8개)
        products = data.get("products", [])
        product_names = []
        for i in range(8):  # 최대 8개 제품
            if i < len(products) and products[i].get("name"):
                product_names.append(products[i].get("name"))
            else:
                product_names.append("")  # 빈 제품은 빈 문자열
        
        # 최종견적 계산 (VAT 포함)
        total_sum = sum(product.get("total", 0) for product in products if product.get("total"))
        vat = round(total_sum * 0.1)
        final_total = total_sum + vat
        
        # 한 행에 모든 데이터 배치
        row_data = [
            data.get("estimate_date", ""),      # A: 견적일자
            data.get("estimate_number", ""),    # B: 견적번호
            data.get("supplier_person", ""),    # C: 견적담당자
            data.get("receiver_company", ""),   # D: 수신자-회사명
            data.get("receiver_person", ""),    # E: 수신자-담당자
            data.get("receiver_contact", ""),   # F: 수신자-연락처
            data.get("product_category", ""),   # G: 견적제품
            product_names[0],                   # H: 제품1
            product_names[1],                   # I: 제품2
            product_names[2],                   # J: 제품3
            product_names[3],                   # K: 제품4
            product_names[4],                   # L: 제품5
            product_names[5],                   # M: 제품6
            product_names[6],                   # N: 제품7
            product_names[7],                   # O: 제품8
            final_total,                        # P: 최종견적(VAT포함)
            data.get("delivery_date", ""),      # Q: 납기일
            estimate_link,                      # R: 견적파일(엑셀)
            "",                                 # S: 견적파일(PDF) - 나중에 추가
            ""                                  # T: Pipedrive 거래 ID - 나중에 추가
        ]
        ws.append_row(row_data)
        
        return {
            "status": "success",
            "message": "견적 데이터가 성공적으로 추가되었습니다.",
            "estimate_link": estimate_link
        }
    except Exception as e:
        print(f"데이터 수집 오류: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return {"status": "error", "message": f"데이터 수집 실패: {str(e)}"}

@app.get("/test-drive-copy")
async def test_copy():
    """Google Drive 파일 복사 테스트 엔드포인트"""
    try:
        print("=== Google Drive 파일 복사 테스트 시작 ===")
        
        creds = get_credentials()
        if not creds:
            return {"error": "자격증명을 가져올 수 없습니다"}
        
        service = build("drive", "v3", credentials=creds)
        
        # 테스트할 파일 ID (현재 설정된 템플릿 파일)
        test_file_id = TEMPLATE_SHEET_ID
        print(f"테스트 파일 ID: {test_file_id}")
        
        # 복사될 폴더 ID
        target_folder_id = ESTIMATE_FOLDER_ID
        print(f"대상 폴더 ID: {target_folder_id}")
        
        # 파일 존재 여부 및 권한 확인
        try:
            file_info = service.files().get(
                fileId=test_file_id,
                fields='id,name,parents,owners,permissions'
            ).execute()
            print(f"✅ 소스 파일 존재 확인: {file_info.get('name', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ 소스 파일 접근 실패: {e}")
            return {"error": f"소스 파일 접근 실패: {str(e)}"}
        
        # 폴더 존재 여부 및 권한 확인
        try:
            folder_info = service.files().get(
                fileId=target_folder_id,
                fields='id,name,owners,permissions'
            ).execute()
            print(f"✅ 대상 폴더 존재 확인: {folder_info.get('name', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ 대상 폴더 접근 실패: {e}")
            return {"error": f"대상 폴더 접근 실패: {str(e)}"}
        
        return {
            "status": "success",
            "message": "파일 및 폴더 접근 테스트 성공",
            "테스트파일ID": test_file_id,
            "대상폴더ID": target_folder_id
        }
        
    except Exception as e:
        print(f"❌ 파일 복사 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"파일 복사 테스트 실패: {str(e)}",
            "테스트파일ID": TEMPLATE_SHEET_ID,
            "대상폴더ID": ESTIMATE_FOLDER_ID
        }

@app.get("/setup-drive-permissions")
async def setup_permissions():
    """Google Drive 권한 설정 엔드포인트"""
    return setup_drive_permissions()

def setup_drive_permissions():
    """Google Drive 파일 및 폴더에 Service Account 권한 설정"""
    try:
        print("=== Google Drive 권한 설정 시작 ===")
        
        creds = get_credentials()
        if not creds:
            return {"status": "error", "message": "자격증명을 가져올 수 없습니다."}
        
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        service_account_email = getattr(creds, 'service_account_email', '')
        
        if not service_account_email:
            return {"status": "error", "message": "Service Account 이메일을 가져올 수 없습니다."}
        
        print(f"Service Account 이메일: {service_account_email}")
        
        # 템플릿 파일에 권한 추가
        try:
            template_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': service_account_email
            }
            
            service.permissions().create(
                fileId=TEMPLATE_SHEET_ID,
                body=template_permission,
                fields='id'
            ).execute()
            print(f"✅ 템플릿 파일 권한 설정 완료")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"⚠️ 템플릿 파일 권한이 이미 존재합니다: {e}")
            else:
                print(f"❌ 템플릿 파일 권한 설정 실패: {e}")
        
        # 대상 폴더에 권한 추가
        try:
            folder_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': service_account_email
            }
            
            service.permissions().create(
                fileId=ESTIMATE_FOLDER_ID,
                body=folder_permission,
                fields='id'
            ).execute()
            print(f"✅ 대상 폴더 권한 설정 완료")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"⚠️ 대상 폴더 권한이 이미 존재합니다: {e}")
            else:
                print(f"❌ 대상 폴더 권한 설정 실패: {e}")
        
        return {"status": "success", "message": "권한 설정이 완료되었습니다."}
        
    except Exception as e:
        print(f"권한 설정 중 오류: {e}")
        return {"status": "error", "message": f"권한 설정 실패: {str(e)}"}

@app.get("/test")
async def test_endpoint():
    """간단한 테스트 엔드포인트"""
    return {"status": "success", "message": "서버가 정상적으로 작동 중입니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT) 