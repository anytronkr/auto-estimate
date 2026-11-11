import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import gspread
from staff import STAFF, display_name as staff_display_name
from config import (
    CREDS_PATH, CELL_MAP, API_HOST, API_PORT,
    DATA_COLLECTION_SHEET_ID, DATA_COLLECTION_COLUMNS,
    get_google_credentials, get_google_drive_folder_id
)
# 참고: get_pipedrive_config는 이 파일 하단에 정의된 버전을 사용 (config.py 버전과 중복이었음)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import requests
import json
from datetime import datetime, timedelta
import re
import time
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from google.auth.transport.requests import Request as GoogleRequest

app = FastAPI()

# === Google client 전역 캐시 (요청마다 새로 만드지 않음) ===
_GOOGLE_CREDS = None
_GSPREAD_CLIENT = None
_DRIVE_SERVICE = None

# requests 연결 재사용 (keep-alive 활용)
HTTP = requests.Session()

def get_google_clients():
    """
    creds / gspread / drive service 를 전역 캐시로 재사용.
    만료 시에만 refresh.
    """
    global _GOOGLE_CREDS, _GSPREAD_CLIENT, _DRIVE_SERVICE

    # 첫 번째 호출 시 또는 creds가 None이면 생성
    if _GOOGLE_CREDS is None:
        _GOOGLE_CREDS = get_credentials()
        if not _GOOGLE_CREDS:
            raise RuntimeError("Google credentials 로드 실패")
        print("✅ [캐시] Google credentials 초기 생성 완료")

    # 만료됐거나 토큰이 없으면 refresh
    try:
        if getattr(_GOOGLE_CREDS, "expired", False) or not getattr(_GOOGLE_CREDS, "token", None):
            print("[캐시] creds 만료 감지 → refresh 시도...")
            _GOOGLE_CREDS.refresh(GoogleRequest())
            print("✅ [캐시] creds refresh 완료")
    except Exception as e:
        print(f"⚠️ [캐시] creds.refresh 실패: {e}")

    # gspread 클라이언트 캐시
    if _GSPREAD_CLIENT is None:
        _GSPREAD_CLIENT = gspread.authorize(_GOOGLE_CREDS)
        print("✅ [캐시] gspread client 초기 생성 완료")

    # drive service 캐시
    if _DRIVE_SERVICE is None:
        _DRIVE_SERVICE = build("drive", "v3", credentials=_GOOGLE_CREDS, cache_discovery=False)
        print("✅ [캐시] drive service 초기 생성 완료")

    return _GOOGLE_CREDS, _GSPREAD_CLIENT, _DRIVE_SERVICE

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

# [보안 수정] /static 마운트 제거 — 프로젝트 폴더 전체(creds.json 포함)가
# 인터넷에 공개되던 심각한 취약점. /static은 어디서도 사용되지 않음 (전체 검색 확인).
# 페이지 서빙은 아래 FileResponse 라우트들이 담당.

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
        print("자격증명 생성 중...")
        credentials = get_google_credentials()
        
        if credentials:
            print("✅ 환경변수에서 자격증명 로드 성공")
            print(f"- 타입: {type(credentials)}")
            
            # 토큰 만료 확인 및 새로고침
            try:
                if not credentials.valid:
                    print("토큰이 유효하지 않음, 새로고침 시도...")
                    import google.auth.transport.requests
                    credentials.refresh(google.auth.transport.requests.Request())
                    print("✅ 토큰 새로고침 성공")
                else:
                    print("✅ 토큰이 유효함")
            except Exception as refresh_error:
                print(f"⚠️ 토큰 새로고침 실패: {refresh_error}")
                # 새로고침 실패해도 계속 진행
            
            return credentials
        else:
            print("❌ 자격증명이 None입니다")
            return None
            
    except Exception as e:
        print(f"❌ 자격증명 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def copy_estimate_template():
    """견적서 템플릿을 복사하여 새 파일 생성"""
    try:
        print("=== 견적서 템플릿 복사 시작 ===")

        creds, gc, drive_service = get_google_clients()
        service = drive_service
        
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
            if "invalid_grant" in error_msg or "Invalid JWT" in error_msg:
                print("JWT 서명 오류 감지 - 자격증명 재생성 및 재시도")
                try:
                    # 캐시를 초기화하고 재생성
                    print("캐시 초기화 후 재시도...")
                    global _GOOGLE_CREDS, _GSPREAD_CLIENT, _DRIVE_SERVICE
                    _GOOGLE_CREDS = None
                    _GSPREAD_CLIENT = None
                    _DRIVE_SERVICE = None
                    creds, gc, drive_service = get_google_clients()
                    service = drive_service
                    if creds:
                        copied_file = service.files().copy(
                            fileId=TEMPLATE_SHEET_ID,
                            body=copy_metadata,
                            supportsAllDrives=True,
                            fields='id,name,webViewLink'
                        ).execute()
                        
                        new_file_id = copied_file['id']
                        web_view_link = copied_file.get('webViewLink', '')
                        
                        print(f"재시도 성공: {new_filename} (ID: {new_file_id})")
                        
                        return {
                            "status": "success",
                            "file_id": new_file_id,
                            "filename": new_filename,
                            "web_view_link": web_view_link,
                            "message": "견적서 템플릿이 성공적으로 복사되었습니다."
                        }
                except Exception as retry_error:
                    print(f"재시도도 실패: {retry_error}")
                    return {
                        "status": "error",
                        "message": f"Google 인증 오류입니다. Service Account 키를 확인해주세요. 오류: {str(copy_error)}"
                    }
            elif "403" in error_msg:
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

        # 견적번호 미리보기용 확인 호출 — 실제 생성 없이 오늘 발행 카운트만 반환
        # (이전에는 이 호출이 템플릿 복사 + 발행 카운터 증가까지 실행되는 버그가 있었음)
        if data.get("check_only"):
            today = datetime.now().strftime("%Y-%m-%d")
            cnt = 0
            try:
                if os.path.exists("pdf_count.json"):
                    with open("pdf_count.json", "r", encoding="utf-8") as f:
                        cnt = json.load(f).get(today, 0)
            except Exception as e:
                print(f"⚠️ check_only 카운트 읽기 실패 (0으로 처리): {e}")
            return {"status": "success", "check_only": True, "pdf_count_today": cnt}

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
        
        timer = StepTimer("/estimate")
        file_id = data.get("fileId")

        # fileId가 없거나 템플릿 변수인 경우 새로운 템플릿 생성
        if not file_id or file_id == "{{24.id}}" or "{{" in str(file_id) or "}}" in str(file_id):
            print("fileId가 없거나 템플릿 변수입니다. 새로운 템플릿을 생성합니다.")
            template_result = copy_estimate_template()
            timer.lap("템플릿 복사")

            if template_result["status"] == "success":
                file_id = template_result["file_id"]
                print(f"새로운 템플릿 생성 완료: {file_id}")
            else:
                return {"status": "error", "message": f"템플릿 생성 실패: {template_result['message']}"}

        if not file_id:
            return {"status": "error", "message": "fileId 없음"}

        creds, gc, drive_service = get_google_clients()

        # 내용이 바뀌므로 미리 만들어 둔 PDF가 있으면 버림
        pdf_prefetch_invalidate(file_id)

        # 견적번호 확정: 비어 있으면 새로 채번, 이미 발행목록에 있는 자동번호면 다음 순번으로 교체
        requested_number = data.get("estimate_number", "").strip()
        estimate_number, number_changed = resolve_estimate_number(
            requested_number, data.get("supplier_person", "")
        )
        data["estimate_number"] = estimate_number
        timer.lap("견적번호 중복 확인")

        sh = gc.open_by_key(file_id)
        ws = sh.sheet1
        timer.lap("견적서 파일 열기")

        # 1. 파일명 변경
        if estimate_number:
            try:
                sh.update_title(estimate_number)
            except Exception as e:
                print("파일명 변경 실패:", e)

        updates = []

        # 일반 필드 (estimate_date는 사용자 입력, estimate_number는 자동 생성)
        for key in ["supplier_person", "supplier_email", "supplier_phone",
                    "receiver_company", "receiver_person", "receiver_email", "receiver_phone", "quote_validity", "payment_terms", "delivery_date", "product_training", "extra_note"]:
            if key in data:
                if key in CELL_MAP:
                    print(f"DEBUG: {key} 처리 중 - 값: '{data[key]}', CELL_MAP 위치: '{CELL_MAP.get(key, 'NOT_FOUND')}'")
                    updates.append({
                        "range": CELL_MAP[key],
                        "values": [[data[key]]]
                    })
                else:
                    print(f"❌ CELL_MAP에 '{key}' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")
            else:
                print(f"DEBUG: {key}가 데이터에 없습니다.")
        
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
        
        # estimate_number 처리 (위에서 중복 확인까지 끝난 최종 번호)
        if "estimate_number" in CELL_MAP:
            updates.append({
                "range": CELL_MAP["estimate_number"],
                "values": [[estimate_number]]
            })
            if number_changed:
                print(f"[견적번호] '{requested_number}'는 이미 발행됨 → '{estimate_number}'로 변경")
        else:
            print(f"❌ CELL_MAP에 'estimate_number' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")

        # 제품 정보
        products = data.get("products", [])
        for i in range(10):
            product = products[i] if i < len(products) else {}
            for field in ["type", "name", "detail", "qty", "price", "total", "note"]:
                cell_key = f"products[{i}][{field}]"
                value = product.get(field, "")
                
                # 제품상세정보(detail) 필드의 경우 줄바꿈 처리
                if field == "detail" and value:
                    # HTML의 <br> 태그를 줄바꿈으로 변환
                    value = value.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                    # 연속된 줄바꿈을 하나로 정리
                    value = '\n'.join(line.strip() for line in value.split('\n') if line.strip())
                    # 제품상세정보 앞뒤로 공백 한 줄씩 추가
                    value = f'\n{value}\n'
                
                if cell_key in CELL_MAP:
                    updates.append({
                        "range": CELL_MAP[cell_key],
                        "values": [[value]]
                    })
                else:
                    print(f"❌ CELL_MAP에 '{cell_key}' 키가 없습니다.")

        print(f"DEBUG: 총 {len(updates)}개의 셀 업데이트 예정")
        for i, update in enumerate(updates):
            print(f"DEBUG: 업데이트 {i+1}: {update['range']} = {update['values']}")
        
        ws.batch_update(updates)
        timer.lap("견적 내용 입력")

        # 제품상세정보 셀들에 텍스트 줄바꿈 포맷 적용 (개별 10회 호출 → 배치 1회로 속도 개선)
        try:
            detail_cells = [CELL_MAP[f"products[{i}][detail]"] for i in range(10)]
            ws.batch_format([
                {"range": cell, "format": {"wrapStrategy": "WRAP"}}
                for cell in detail_cells
            ])
            print(f"✅ 제품상세정보 셀 줄바꿈 포맷 일괄 적용 완료: {detail_cells}")
        except Exception as e:
            print(f"⚠️ 셀 포맷 적용 중 오류 (무시됨): {e}")
        
        # 페이지 나누기 설정 제거됨 - 자동 너비 맞춤으로 변경
        print("✅ 페이지 나누기 설정 생략 - 자동 페이지 조정 사용")
        
        # B47 셀 합치기 해제 (명판/인감 영역)
        try:
            # B47 셀의 합치기 해제
            ws.unmerge('B47')
            print("✅ B47 셀 합치기 해제 완료")
        except Exception as e:
            print(f"⚠️ B47 셀 합치기 해제 중 오류 (무시됨): {e}")
        timer.lap("서식 정리")
        timer.total()

        return {
            "status": "success",
            "file_id": file_id,
            "estimate_number": estimate_number,
            "number_changed": number_changed,
            "requested_number": requested_number,
        }
        
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

NO_CACHE = {"Cache-Control": "no-cache"}


def html_page(filename):
    """화면 파일 응답. 'no-cache' = 브라우저가 열 때마다 서버에서 최신 화면을 받음.
    배포하면 영업팀 화면에 바로 새 버전이 뜸 (예전에는 헤더가 없어 몇 시간 예전 화면이 남았음).
    견적폼도 압축 전송 시 약 29KB라 매번 받아도 체감 차이 없음 (2026-11-11 측정 0.16초)"""
    return FileResponse(filename, headers=NO_CACHE)


def staff_options_html():
    """staff.py 담당자 목록 → 견적폼 드롭다운 <option>들"""
    from html import escape
    lines = []
    for p in STAFF:
        name = escape(staff_display_name(p))
        lines.append(
            f'<option value="{name}" data-email="{escape(p["email"])}" '
            f'data-phone="{escape(p["phone"])}" data-id="{escape(p["id"])}">{name}</option>'
        )
    return "\n            ".join(lines)

@app.get("/")
async def root():
    """메인 페이지"""
    return html_page("index.html")

@app.get("/estimate_form.html")
async def estimate_form():
    """견적서 작성 폼 — 담당자 드롭다운은 staff.py에서 채워서 내려줌"""
    with open("estimate_form.html", encoding="utf-8") as f:
        page = f.read()
    page = page.replace("<!--STAFF_OPTIONS-->", staff_options_html(), 1)
    return HTMLResponse(page, headers=NO_CACHE)

@app.get("/preview.html")
async def preview():
    """미리보기 페이지"""
    return html_page("preview.html")

@app.get("/pdf-sharing.html")
async def pdf_sharing():
    """PDF 공유 페이지"""
    return html_page("pdf-sharing.html")

@app.post("/create-estimate-template")
async def create_estimate_template():
    """견적서 템플릿 스프레드시트를 복사하여 새 파일 생성"""
    print("=== 견적서 템플릿 생성 API 호출됨 ===")
    result = copy_estimate_template()
    print("=== 견적서 템플릿 생성 결과:", result, "===")
    return result

@app.post("/collect-data")
async def collect_data(request: Request):
    """데이터 수집용 스프레드시트에 데이터 추가, PDF 업로드, Pipedrive 거래 생성"""
    print("=== /collect-data 엔드포인트 호출됨 ===")
    try:
        data = await request.json()
        print(f"받은 데이터: {data}")
        
        timer = StepTimer("/collect-data")
        # Google Sheets 연결 (캐시 재사용)
        creds, gc, drive_service = get_google_clients()

        sh = gc.open_by_key(DATA_COLLECTION_SHEET_ID)
        ws = sh.sheet1

        # 중복 발행 방지: 같은 견적번호 + 같은 견적서 파일이 이미 발행목록에 있으면
        # (버튼 두 번 클릭, 뒤로가기 후 재클릭 등) PDF·Pipedrive·시트 기록을 다시 하지 않음
        already = find_issued_row(ws, data.get("estimate_number", ""), data.get("fileId", ""))
        timer.lap("발행목록 중복 확인")
        if already:
            print(f"[중복 방지] 이미 발행된 견적 재요청 - {data.get('estimate_number')} (행 {already['row']})")
            return {
                "status": "success",
                "already_issued": True,
                "message": "이미 발행된 견적입니다. 기존 PDF를 보여드립니다.",
                "pdf_link": already["pdf_link"],
                "pdf_id": "",
                "pipedrive_deal_id": already["deal_id"],
            }

        # 견적서 링크 생성
        estimate_link = f"https://docs.google.com/spreadsheets/d/{data.get('fileId', '')}/edit"
        
        # 제품 데이터 추출 (최대 10개)
        products = data.get("products", [])
        product_names = []
        for i in range(10):  # 최대 10개 제품
            if i < len(products) and products[i].get("name"):
                product_names.append(products[i].get("name"))
            else:
                product_names.append("")  # 빈 제품은 빈 문자열
        
        # 최종견적 계산 (VAT 포함)
        total_sum = sum(product.get("total", 0) for product in products if product.get("total"))
        vat = round(total_sum * 0.1)
        final_total = total_sum + vat
        
        # PDF 파일 생성 및 업로드
        pdf_link = ""
        pdf_id = ""
        file_id = data.get("fileId", "")
        print(f"DEBUG: file_id = {file_id}")
        
        try:
            # PDF 파일명 생성
            receiver_company = data.get("receiver_company", "")
            estimate_number = data.get("estimate_number", "")
            
            def clean_filename(s):
                import re
                return re.sub(r'[^\w\s-]', '', s).strip()
            
            clean_company_name = clean_filename(receiver_company)
            pdf_filename = f"애니트론견적서_{clean_company_name}_{estimate_number}.pdf"
            
            # PDF 생성 (Google Sheet export)
            print(f"DEBUG: PDF 생성 시도 - file_id: '{file_id}', pdf_filename: '{pdf_filename}'")
            
            # 미리보기 화면에서 미리 만들어 둔 PDF가 있으면 그걸 사용 (없거나 실패면 지금 변환)
            if file_id and (pdf_prefetch_take(file_id, pdf_filename) or export_sheet_to_pdf(file_id, pdf_filename, creds)):
                timer.lap("PDF 변환")
                # Google Drive 업로드
                pdf_id, pdf_link = upload_pdf_to_drive(pdf_filename, get_google_drive_folder_id(), pdf_filename, creds)
                timer.lap("구글 드라이브 업로드")
                print(f"DEBUG: Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                # ⚠️ 임시 파일 삭제는 Pipedrive 업로드 후로 이동 (아래)
            else:
                print("DEBUG: PDF export 실패 또는 file_id 없음")
                # Fallback: 테스트 PDF 생성 시도
                print("DEBUG: 테스트 PDF 생성 시도")
                if create_test_pdf(pdf_filename, data):
                    # Google Drive 업로드
                    pdf_id, pdf_link = upload_pdf_to_drive(pdf_filename, get_google_drive_folder_id(), pdf_filename, creds)
                    print(f"DEBUG: 테스트 PDF Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                    # ⚠️ 임시 파일 삭제는 Pipedrive 업로드 후로 이동 (아래)
                else:
                    return {
                        "status": "error",
                        "message": "Google Sheets PDF export 실패: 시트 권한 또는 설정 확인 필요"
                    }
        except Exception as e:
            print(f"DEBUG: Google Drive PDF 생성 실패 - {str(e)}")
            return {
                "status": "error",
                "message": f"PDF 생성 중 오류 발생: {str(e)}"
            }
        
        # Pipedrive 거래 처리
        # - 반드시 기존 거래를 선택해야만 진행 가능 (신규 자동 생성 차단)
        selected_deal_id = data.get("pipedrive_deal_id")
        if not selected_deal_id:
            print("Pipedrive 거래 미선택 - 처리 거부")
            return {
                "status": "error",
                "message": "파이프드라이브 거래를 선택해 주세요. 본인 파이프라인에 거래를 먼저 생성하신 후 진행해 주세요."
            }
        pipedrive_deal_id = update_pipedrive_deal_estimate(
            selected_deal_id, data.get("estimate_number", ""), pdf_filename, estimate_link, pdf_link
        )
        timer.lap("Pipedrive 거래 등록")

        # ✅ Pipedrive 업로드 완료 후에 임시 파일 삭제
        try:
            if pdf_filename and os.path.exists(pdf_filename):
                os.remove(pdf_filename)
                print(f"DEBUG: 임시 파일 정리 완료 - {pdf_filename}")
        except Exception as e:
            print(f"DEBUG: 임시 파일 정리 실패 - {str(e)}")
        
        # 한 행에 모든 데이터 배치 (새로운 컬럼 매핑)
        # 첫 번째 제품의 대분류 정보 추출
        major_category = ""
        if products and len(products) > 0:
            major_category = products[0].get("major_category", "")
        
        row_data = [
            data.get("estimate_date", ""),      # A: 견적일자
            data.get("estimate_number", ""),    # B: 견적번호
            data.get("supplier_person", ""),    # C: 견적담당자
            data.get("receiver_company", ""),   # D: 수신자-회사명
            data.get("receiver_person", ""),    # E: 수신자-담당자
            data.get("receiver_email", ""),     # F: 수신자-이메일
            data.get("receiver_phone", ""),     # G: 수신자-전화번호
            data.get("product_category", ""),   # H: 견적제품
            major_category,                     # I: 구분(대분류)
            product_names[0],                   # J: 제품1제품명
            product_names[1],                   # K: 제품2제품명
            product_names[2],                   # L: 제품3제품명
            product_names[3],                   # M: 제품4제품명
            product_names[4],                   # N: 제품5제품명
            product_names[5],                   # O: 제품6제품명
            product_names[6],                   # P: 제품7제품명
            product_names[7],                   # Q: 제품8제품명
            product_names[8],                   # R: 제품9제품명
            product_names[9],                   # S: 제품10제품명
            final_total,                        # T: 최종견적(VAT포함) (R → T로 변경)
            data.get("delivery_date", ""),      # U: 납기일 (S → U로 변경)
            data.get("product_training", ""),   # V: 제품교육 (T → V로 변경)
            estimate_link,                      # W: 견적파일(엑셀) (U → W로 변경)
            pdf_link,                           # X: 견적파일(PDF) (V → X로 변경)
            selected_deal_id                    # Y: Pipedrive 거래 ID — 사용자 선택값을 그대로 기록 (PD API 업데이트 실패와 무관)
        ]
        ws.append_row(row_data)
        timer.lap("발행목록 기록")
        timer.total()

        success_message = f"견적 데이터 및 PDF가 성공적으로 추가되었습니다."
        if pipedrive_deal_id:
            success_message += f"\nPipedrive 거래가 성공적으로 업데이트되었습니다. (거래 ID: {pipedrive_deal_id})"
            success_message += f"\nPDF 파일이 Pipedrive 거래에 첨부되었습니다."
        else:
            success_message += f"\n⚠️ Pipedrive 견적번호 기록에 실패했습니다 (거래 ID {selected_deal_id}는 시트에 저장됨)."
        
        return {
            "status": "success",
            "message": success_message,
            "pdf_link": pdf_link,
            "pdf_id": pdf_id,
            "pipedrive_deal_id": pipedrive_deal_id
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

        creds, gc, service = get_google_clients()
        
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

        creds, gc, service = get_google_clients()
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

def export_sheet_to_pdf(sheet_id, pdf_filename, creds, gid=0):
    """Google Sheets를 PDF로 export (페이지 나누기 강화)"""
    try:
        print(f"DEBUG: export_sheet_to_pdf 함수 시작")
        print(f"DEBUG: sheet_id: {sheet_id}")
        print(f"DEBUG: pdf_filename: {pdf_filename}")
        print(f"DEBUG: gid: {gid}")

        # PDF 생성 전 토큰 갱신 보장
        try:
            if getattr(creds, "expired", False) or not getattr(creds, "token", None):
                print("[PDF] 토큰 만료 감지 → refresh")
                creds.refresh(GoogleRequest())
                print("✅ [PDF] 토큰 갱신 완료")
        except Exception as e:
            print(f"⚠️ [PDF] 토큰 갱신 실패: {e}")

        # PDF 생성 전 페이지 나누기 설정 제거됨 - 자동 조정 사용
        print("✅ PDF 생성 시 자동 페이지 조정 사용")
        
        # URL 방식으로 PDF 생성 (페이지 설정 포함)
        try:
            print(f"DEBUG: URL 방식 PDF 생성 시도 (너비 맞춤으로 변경)")
            
            # 너비 맞춤 설정으로 변경된 URL 방식 사용
            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?" + \
                        f"format=pdf&portrait=true&size=A4&" + \
                        f"fitw=true&fith=false&" + \
                        f"top_margin=0.5&bottom_margin=0.5&" + \
                        f"left_margin=0.5&right_margin=0.5&" + \
                        f"horizontal_alignment=CENTER&" + \
                        f"vertical_alignment=TOP&" + \
                        f"printtitle=false&sheetnames=false&" + \
                        f"pagenum=UNDEFINED&gridlines=false&" + \
                        f"gid={gid}"
            
            print(f"DEBUG: PDF 생성 URL: {export_url}")
            
            # OAuth 토큰으로 요청 (HTTP Session 재사용)
            headers = {'Authorization': f'Bearer {creds.token}'}

            response = HTTP.get(export_url, headers=headers)

            if response.status_code == 200:
                with open(pdf_filename, 'wb') as f:
                    f.write(response.content)
                print(f"DEBUG: URL 방식 PDF 생성 성공: {pdf_filename}")
                return True
            else:
                print(f"DEBUG: URL 방식 PDF 생성 실패: {response.status_code}")

                # 백업: Google Drive API 방식 (캐시된 drive_service 재사용)
                print(f"DEBUG: 백업 방법으로 Google Drive API 시도")
                _, _, cached_drive_service = get_google_clients()
                request = cached_drive_service.files().export_media(
                    fileId=sheet_id,
                    mimeType='application/pdf'
                )

                with open(pdf_filename, 'wb') as f:
                    f.write(request.execute())

                print(f"DEBUG: 백업 방법 PDF 생성 성공: {pdf_filename}")
                return True
            
        except Exception as api_e:
            print(f"DEBUG: PDF 생성 실패: {api_e}")
            return False
            
    except Exception as e:
        print(f"DEBUG: PDF export 예외 발생: {str(e)}")
        return False

def upload_pdf_to_drive(pdf_path, folder_id, file_name, creds):
    """PDF 파일을 Google Drive에 업로드"""
    try:
        _, _, drive_service = get_google_clients()
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink',
            supportsAllDrives=True
        ).execute()
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        print(f"PDF 업로드 실패: {e}")
        return None, None

def create_test_pdf(filename, data):
    """테스트용 PDF 파일을 생성합니다."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        
        # 한글 폰트 등록
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            korean_font = 'STSong-Light'
            print("한글 폰트 등록 성공: STSong-Light")
        except Exception as e:
            print(f"한글 폰트 등록 실패: {e}")
            korean_font = 'Helvetica'
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # 제목 스타일
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=korean_font,
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#21808c')
        )
        
        # 제목 추가
        title = Paragraph(f"견적서 - {data.get('estimate_number', '')}", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # 기본 정보 테이블
        basic_info = [
            ['견적일자', data.get('estimate_date', '')],
            ['견적번호', data.get('estimate_number', '')],
            ['공급자', '(주)바이텍테크놀로지'],
            ['담당자', data.get('supplier_person', '')],
            ['수신자 회사', data.get('receiver_company', '')],
            ['수신자 담당자', data.get('receiver_person', '')],
            ['납기일', data.get('delivery_date', '')],
            ['제품교육', data.get('product_training', '')]
        ]
        
        basic_table = Table(basic_info, colWidths=[3*cm, 12*cm])
        basic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#21808c')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(basic_table)
        story.append(Spacer(1, 20))
        
        # 제품 정보 테이블
        products = data.get('products', [])
        if products:
            product_data = [['구분', '제품명', '상세정보', '수량', '단가(원)', '합계(원)']]
            
            for product in products:
                if product.get('name'):  # 제품명이 있는 경우만 추가
                    product_type = product.get('type', '')
                    if not product_type:
                        name = product.get('name', '')
                        if '라벨' in name or '프린터' in name:
                            product_type = '프린터'
                        elif '패키징' in name:
                            product_type = '장비'
                        else:
                            product_type = '기타'
                    
                    product_data.append([
                        product_type,
                        product.get('name', ''),
                        product.get('detail', ''),
                        str(product.get('qty', '1')),
                        f"{product.get('price', 0):,}",
                        f"{product.get('total', 0):,}"
                    ])
            
            if len(product_data) > 1:  # 헤더 외에 데이터가 있는 경우
                product_table = Table(product_data, colWidths=[2*cm, 3*cm, 4*cm, 1.5*cm, 2.5*cm, 2*cm])
                product_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#21808c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), korean_font),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # 상세정보는 왼쪽 정렬
                ]))
                story.append(product_table)
                story.append(Spacer(1, 20))
        
        # 합계 계산
        total_sum = sum(product.get("total", 0) for product in products if product.get("total"))
        vat = round(total_sum * 0.1)
        final_total = total_sum + vat
        
        # 합계 테이블
        summary_data = [
            ['공급가액', f"{total_sum:,}원"],
            ['부가세 (10%)', f"{vat:,}원"],
            ['총액', f"{final_total:,}원"]
        ]
        
        summary_table = Table(summary_data, colWidths=[4*cm, 4*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#21808c')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        
        # PDF 생성
        doc.build(story)
        return filename
    except Exception as e:
        print(f"테스트 PDF 생성 오류: {str(e)}")
        return None

def get_pipedrive_config():
    """환경변수에서 Pipedrive 설정 가져오기"""
    import os
    return {
        "api_token": os.environ.get("PIPEDRIVE_API_TOKEN", ""),
        "domain": os.environ.get("PIPEDRIVE_DOMAIN", "api.pipedrive.com")
    }

# Pipedrive 견적번호 커스텀필드 키
PIPEDRIVE_QUOTE_NUM_FIELD_KEY = "55c48a15f50d667c26682f95d38a9a06d420369f"

def _pd_extract_search_items(res_json):
    """v1(data.items[].item)과 v2(data가 배열/리스트일 가능성) 검색 응답을 모두 흡수해서
    딜/조직 딕셔너리 리스트로 반환. v2 정확한 응답 구조는 라이브 테스트로 확인 필요."""
    if not res_json.get("success"):
        return []
    data = res_json.get("data")
    if isinstance(data, dict) and data.get("items"):
        return [it.get("item", {}) for it in data["items"] if it.get("item")]
    if isinstance(data, list):
        return data
    return []

def _pd_custom_field_value(data_obj, key):
    """v2 custom_fields.{key}.value 중첩 구조에서 값 읽기 (평면 구조도 방어)"""
    cf = (data_obj or {}).get("custom_fields") or {}
    v = cf.get(key)
    if isinstance(v, dict):
        return v.get("value") or ""
    return v or ""

def _norm_text(s):
    """검색 비교용 정규화: 공백/특수문자 제거 + 소문자 (한글/영문/숫자만 유지)
    예: '(주)경신 이엔피' → '주경신이엔피' — '경신이' 검색어도 매칭됨"""
    return re.sub(r'[^0-9a-zA-Z가-힣]', '', str(s or '')).lower()


# 거래 검색 결과를 1분간 기억 (같은 회사명을 다시 칠 때 바로 표시). 결과 없음은 기억하지 않음
# (방금 만든 거래는 Pipedrive 검색에 수십 초 뒤 잡히므로 '다시 검색'이 항상 새로 찾게)
_DEAL_SEARCH_CACHE = {}  # q -> (저장시각, 결과)
_DEAL_SEARCH_TTL = 60
_PD_POOL = ThreadPoolExecutor(max_workers=8)


@app.get("/search-deals")
def search_deals(q: str = "", debug: int = 0, fresh: int = 0):
    """거래 제목 + 조직명으로 Pipedrive 거래 검색 (공백/특수문자 무시 매칭)

    개선 사항:
    1. 검색어 그대로 + 공백 제거 버전 이중 검색 (Pipedrive는 공백 경계를 넘는 매칭 불가)
    2. 조직명 검색 병행 → 거래 제목에 회사명이 없어도 검색됨
    3. 필터를 엄격한 부분문자열 → 정규화 후 비교로 완화
    4. (2026-11) Pipedrive 호출을 한 번에 동시에 보냄 — 예전엔 최대 14번을 하나씩 순서대로 호출해 약 3초
    5. (2026-11) 결과 1분 기억, fresh=1이면 기억 무시
    """
    q = (q or "").strip()
    if len(q) < 2:
        return {"deals": []}
    cache_key = q.lower()
    if not fresh and not debug:
        hit = _DEAL_SEARCH_CACHE.get(cache_key)
        if hit and time.time() - hit[0] < _DEAL_SEARCH_TTL:
            return {"deals": hit[1], "cached": True}
    TIMEOUT = 10
    try:
        pipedrive_settings = get_pipedrive_config()
        base_url = f"https://{pipedrive_settings['domain']}/api/v2"
        token = pipedrive_settings["api_token"]
        qn = _norm_text(q)

        # 검색어 변형: 입력 그대로 + 공백 제거 버전
        terms = [q]
        q_nospace = q.replace(" ", "")
        if q_nospace != q and len(q_nospace) >= 2:
            terms.append(q_nospace)

        def pd_get(path, params, label):
            try:
                res = HTTP.get(f"{base_url}{path}", params=dict(params, api_token=token), timeout=TIMEOUT)
                return res.json()
            except Exception as e:
                print(f"[WARN] {label} 오류: {e}", flush=True)
                return {}

        # 1) 거래 제목 검색 + 조직명 검색을 동시에
        deal_jobs = [_PD_POOL.submit(pd_get, "/deals/search", {"term": t, "fields": "title", "limit": 30}, f"deals/search '{t}'") for t in terms]
        org_jobs = [_PD_POOL.submit(pd_get, "/organizations/search", {"term": t, "fields": "name", "limit": 10}, f"organizations/search '{t}'") for t in terms]

        raw_deals = {}  # deal_id -> deal dict
        for job in deal_jobs:
            for deal in _pd_extract_search_items(job.result()):
                if deal.get("id"):
                    raw_deals.setdefault(deal["id"], dict(deal))

        org_names = {}  # org_id -> name (제목에 회사명 없는 거래 대비)
        for job in org_jobs:
            for org in _pd_extract_search_items(job.result()):
                oname = org.get("name", "") or ""
                if org.get("id") and qn in _norm_text(oname):
                    org_names[org["id"]] = oname

        # 2) 조직별 거래 목록 — 조직명으로 찾은 조직 + 제목 검색 거래의 조직(등록일 보충용)을 한 번에 동시 조회
        #    v1 /organizations/{id}/deals는 v2에서 폐지 → /deals?org_id= 로 대체
        #    v2 status 필터는 open/won/lost/deleted만 허용 → 생략
        name_org_ids = list(org_names.keys())[:5]  # 과도한 API 호출 방지
        title_org_ids = []  # 검색어에 맞는 제목 검색 거래 중, 위에서 조회하지 않는 조직 (등록일 보충용)
        for deal in raw_deals.values():
            org_info = deal.get("organization") or {}
            oid = org_info.get("id")
            if not oid or oid in name_org_ids or oid in title_org_ids:
                continue
            if qn in _norm_text(deal.get("title", "") or "") or qn in _norm_text(org_info.get("name", "") or ""):
                title_org_ids.append(oid)
        fetch_org_ids = name_org_ids + title_org_ids[:5]
        org_jobs2 = {oid: _PD_POOL.submit(pd_get, "/deals", {"limit": 100, "org_id": oid}, f"org/{oid} deals")
                     for oid in fetch_org_ids}

        add_times = {}  # deal_id -> add_time
        for org_id, job in org_jobs2.items():
            od_data = job.result()
            if not (od_data.get("success") and od_data.get("data")):
                continue
            for d in od_data["data"]:
                add_times[d["id"]] = (d.get("add_time") or "")[:10]
                if org_id in name_org_ids and d["id"] not in raw_deals:
                    raw_deals[d["id"]] = {
                        "id": d["id"],
                        "title": d.get("title", "") or "",
                        "organization": {"id": org_id, "name": org_names[org_id]},
                        "value": d.get("value") or 0,
                        "currency": d.get("currency", "KRW"),
                        "status": d.get("status", ""),
                    }

        # 디버그 모드: 필터링 없이 수집된 원본 반환
        if debug:
            return {"total": len(raw_deals), "raw_items": list(raw_deals.values())}

        # 3) 필터: 정규화 후 제목 또는 조직명에 검색어 포함되면 통과
        deals = []
        for deal in raw_deals.values():
            title = deal.get("title", "") or ""
            org_name = (deal.get("organization") or {}).get("name", "") or ""
            if qn not in _norm_text(title) and qn not in _norm_text(org_name):
                continue
            value = deal.get("value") or 0
            deals.append({
                "id": deal["id"],
                "title": title,
                "org_name": org_name,
                "value": f"{int(value):,}" if value else "-",
                "currency": deal.get("currency", "KRW"),
                "add_time": add_times.get(deal["id"], ""),
                "status": deal.get("status", ""),
            })

        # 최신 생성순 정렬
        deals.sort(key=lambda d: d.get("add_time") or "", reverse=True)
        if deals:
            _DEAL_SEARCH_CACHE[cache_key] = (time.time(), deals)
            if len(_DEAL_SEARCH_CACHE) > 300:  # 오래된 것 정리
                for k in sorted(_DEAL_SEARCH_CACHE, key=lambda k: _DEAL_SEARCH_CACHE[k][0])[:100]:
                    _DEAL_SEARCH_CACHE.pop(k, None)
        return {"deals": deals}
    except Exception as e:
        print(f"Pipedrive 거래 검색 오류: {e}")
        return {"deals": []}


@app.get("/estimate-history")
def estimate_history(person: str = "", q: str = "", limit: int = 20):
    """발행목록(데이터 수집 시트)에서 이전 견적 검색

    - person: 견적담당자 필터 (C열, 정규화 부분일치)
    - q: 거래처명 또는 견적번호 검색 (D열/B열, 정규화 부분일치 — 공백/특수문자 무시)
    - 최신 발행순(시트 아래쪽부터)으로 최대 limit건 반환
    """
    try:
        creds, gc, drive_service = get_google_clients()
        sh = gc.open_by_key(DATA_COLLECTION_SHEET_ID)
        ws = sh.sheet1
        rows = ws.get_all_values()

        pn = _norm_text(person)
        qn = _norm_text(q)
        try:
            limit = max(1, min(int(limit), 50))
        except Exception:
            limit = 20

        items = []
        # 최신 행이 아래쪽에 append되므로 뒤에서부터 탐색 (0행은 헤더)
        for i in range(len(rows) - 1, 0, -1):
            r = list(rows[i]) + [""] * max(0, 25 - len(rows[i]))
            date_s, number, manager, company = r[0], r[1], r[2], r[3]
            if not number and not company:
                continue
            if pn and pn not in _norm_text(manager):
                continue
            if qn and qn not in _norm_text(company) and qn not in _norm_text(number):
                continue
            # W열(견적파일 엑셀 링크)에서 파일 ID 추출
            m = re.search(r"/d/([a-zA-Z0-9_-]+)", r[22] or "")
            items.append({
                "date": date_s,
                "number": number,
                "manager": manager,
                "company": company,
                "total": r[19],          # T열: 최종견적(VAT포함)
                "file_id": m.group(1) if m else "",
                "deal_id": r[24],        # Y열: Pipedrive 거래 ID
            })
            if len(items) >= limit:
                break
        return {"status": "success", "items": items}
    except Exception as e:
        print(f"[ERROR] estimate-history 오류: {e}")
        return {"status": "error", "message": str(e), "items": []}


def _to_number(s):
    """시트 셀 값('20,000,000' 등)을 정수로 변환"""
    s = re.sub(r"[^\d]", "", str(s or ""))
    return int(s) if s else 0


@app.get("/load-estimate")
def load_estimate(file_id: str = ""):
    """기존 견적서 구글시트에서 폼 데이터를 역으로 읽어오기 (CELL_MAP 역방향)

    반환 형식은 폼의 collectEstimateData()와 동일한 구조 —
    프론트의 restoreFormData()로 바로 복원 가능
    """
    if not file_id:
        return {"status": "error", "message": "file_id가 필요합니다."}
    try:
        creds, gc, drive_service = get_google_clients()
        sh = gc.open_by_key(file_id)
        ws = sh.sheet1

        # CELL_MAP 기준 읽기 대상 (한 번의 batch_get으로 조회)
        ranges = ["F5", "F6", "B11", "B12", "B13", "D10", "E11", "E12", "E13",
                  "A16:G25", "B30", "B32", "B33", "B34", "B31"]
        vals = ws.batch_get(ranges)

        def cell(i):
            try:
                return str(vals[i][0][0]).strip()
            except Exception:
                return ""

        products = []
        grid = vals[9] if len(vals) > 9 else []
        for row in grid:
            row = list(row) + [""] * max(0, 7 - len(row))
            name = str(row[1]).strip()
            if not name:
                continue
            products.append({
                "type": str(row[0]).strip(),
                "name": name,
                "detail": str(row[2]).strip(),  # 저장 시 앞뒤로 추가된 공백 줄 제거
                "qty": _to_number(row[3]) or 1,
                "price": _to_number(row[4]),
                "total": _to_number(row[5]),
                "note": str(row[6]).strip(),
            })

        data = {
            "estimate_date": cell(0),
            "estimate_number": cell(1),
            "supplier_person": cell(2),
            "supplier_email": cell(3),
            "supplier_phone": cell(4),
            "receiver_company": cell(5),
            "receiver_person": cell(6),
            "receiver_email": cell(7),
            "receiver_phone": cell(8),
            "quote_validity": cell(10),
            "product_training": cell(11),
            "delivery_date": cell(12),
            "extra_note": cell(13),
            "payment_terms": cell(14),
            "products": products,
        }
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"[ERROR] load-estimate 오류: {e}")
        return {"status": "error", "message": f"견적서를 불러오지 못했습니다: {e}"}


def update_pipedrive_deal_estimate(deal_id, estimate_number, pdf_filename, estimate_link, pdf_link):
    """기존 Pipedrive 거래에 견적번호 추가 및 PDF 첨부

    Deals는 API v2 사용. Notes/Files는 v2 엔드포인트가 아직 없어(2026-07 기준,
    Pipedrive 공식 답변 "Notes는 당분간 v1 계속 사용 권장") v1을 그대로 유지.
    """
    TIMEOUT = 15  # 초
    try:
        pipedrive_settings = get_pipedrive_config()
        base_url_v2 = f"https://{pipedrive_settings['domain']}/api/v2"
        base_url_v1 = f"https://{pipedrive_settings['domain']}/api/v1"
        token = pipedrive_settings["api_token"]

        # 기존 견적번호 가져오기 (누적 저장)
        deal_res = HTTP.get(f"{base_url_v2}/deals/{deal_id}?api_token={token}", timeout=TIMEOUT)
        existing = ""
        if deal_res.status_code == 200:
            existing = _pd_custom_field_value(deal_res.json().get("data"), PIPEDRIVE_QUOTE_NUM_FIELD_KEY)
        else:
            print(f"[WARN] 거래 조회 실패 - deal_id: {deal_id}, status: {deal_res.status_code}, body: {deal_res.text[:200]}")

        # 견적번호 누적 (기존값 있으면 쉼표로 구분)
        new_value = f"{existing}, {estimate_number}".strip(", ") if existing else estimate_number

        # 커스텀 필드 업데이트 (v2: PUT→PATCH, custom_fields 중첩 구조)
        # 주의: 텍스트형 커스텀필드의 정확한 쓰기 body 구조는 실제 토큰으로 라이브 테스트 필요
        update_res = HTTP.patch(
            f"{base_url_v2}/deals/{deal_id}?api_token={token}",
            json={"custom_fields": {PIPEDRIVE_QUOTE_NUM_FIELD_KEY: {"value": new_value}}},
            timeout=TIMEOUT
        )
        print(f"Pipedrive 거래 업데이트 결과: {update_res.status_code} - {update_res.text[:200]}")
        if update_res.status_code not in (200, 201):
            print(f"[ERROR] 커스텀 필드 업데이트 실패 - deal_id: {deal_id}, status: {update_res.status_code}")
            return None

        # PDF 첨부 (Files API v1 유지)
        if pdf_filename and os.path.exists(pdf_filename):
            upload_file_to_pipedrive_deal(deal_id, pdf_filename, pdf_filename)

        # 노트 추가 (Notes API v1 유지)
        note_content = f"견적번호: {estimate_number}\n엑셀견적서: {estimate_link}\nPDF견적서: {pdf_link}"
        HTTP.post(
            f"{base_url_v1}/notes?api_token={token}",
            json={"content": note_content, "deal_id": deal_id},
            timeout=TIMEOUT
        )
        print(f"Pipedrive 기존 거래 업데이트 완료 - deal_id: {deal_id}, 견적번호: {new_value}")
        return deal_id
    except Exception as e:
        print(f"[ERROR] Pipedrive 거래 업데이트 예외 - deal_id: {deal_id}, 오류: {type(e).__name__}: {e}")
        return None


# 참고: create_pipedrive_deal / create_pipedrive_organization / create_pipedrive_person /
# get_pipedrive_user_id / get_pipedrive_stage_id 함수는 2026-05-13 "거래 선택 필수화" 이후
# 미사용 코드가 되어 제거됨. 필요 시 git 히스토리(커밋 54b1e3b 이전) 참조.

def upload_file_to_pipedrive_deal(deal_id, file_path, file_name):
    """Pipedrive 거래에 파일을 업로드합니다."""
    file_handle = None
    try:
        if not deal_id or not file_path:
            print("거래 ID 또는 파일 경로가 없습니다.")
            return None
            
        pipedrive_settings = get_pipedrive_config()
        url = f"https://{pipedrive_settings['domain']}/api/v1/files?api_token={pipedrive_settings['api_token']}"
        
        # 파일 업로드 데이터
        file_handle = open(file_path, 'rb')
        files = {
            'file': (file_name, file_handle, 'application/pdf')
        }
        
        data = {
            'deal_id': deal_id
        }
        
        print(f"Pipedrive 파일 업로드 정보:")
        print(f"URL: {url}")
        print(f"Deal ID: {deal_id}")
        print(f"File: {file_name}")
        
        response = HTTP.post(url, files=files, data=data)

        print(f"File Upload Response Status: {response.status_code}")
        print(f"File Upload Response Text: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            file_id = result.get("data", {}).get("id")
            print(f"Pipedrive 파일 업로드 성공: {file_id}")
            return file_id
        else:
            print(f"Pipedrive 파일 업로드 실패: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Pipedrive 파일 업로드 오류: {str(e)}")
        return None
    finally:
        if file_handle:
            file_handle.close()

# ===== PDF 미리 만들기 =====
# 미리보기 화면이 열리면(/prepare-pdf) 뒤에서 PDF 변환을 먼저 해 두고,
# 'PDF파일 생성하기'(/collect-data)에서 그 파일을 그대로 씀 → PDF 변환 대기시간이 사라짐.
# 견적 내용이 다시 저장되면(/estimate) 버림. 서버가 재시작됐거나 실패했으면 예전처럼 그 자리에서 변환.
_PREFETCH = {}            # file_id -> {"gen": int, "path": str|None, "done": Event, "ok": bool}
_PREFETCH_LOCK = threading.Lock()
_PREFETCH_DIR = os.path.join(tempfile.gettempdir(), "estimate_pdf_prefetch")


def _prefetch_path(file_id, gen):
    os.makedirs(_PREFETCH_DIR, exist_ok=True)
    return os.path.join(_PREFETCH_DIR, f"{re.sub(r'[^A-Za-z0-9_-]', '', file_id)}_{gen}.pdf")


def pdf_prefetch_invalidate(file_id):
    with _PREFETCH_LOCK:
        entry = _PREFETCH.pop(file_id, None)
    if entry and entry.get("path") and os.path.exists(entry["path"]):
        try:
            os.remove(entry["path"])
        except OSError:
            pass


def pdf_prefetch_start(file_id):
    """이미 만들고 있거나 만들어 뒀으면 그대로 두고, 아니면 뒤에서 변환 시작"""
    # 미리보기만 보고 PDF 버튼을 안 누른 경우 남는 파일 정리 (1시간 지난 것)
    cutoff = (time.time() - 3600) * 1000
    with _PREFETCH_LOCK:
        stale = [fid for fid, e in _PREFETCH.items() if e["gen"] < cutoff and e["done"].is_set()]
    for fid in stale:
        pdf_prefetch_invalidate(fid)
    with _PREFETCH_LOCK:
        if file_id in _PREFETCH:
            return "already"
        gen = int(time.time() * 1000)
        entry = {"gen": gen, "path": None, "done": threading.Event(), "ok": False}
        _PREFETCH[file_id] = entry

    def work():
        path = _prefetch_path(file_id, gen)
        ok = False
        try:
            creds, _, _ = get_google_clients()
            ok = export_sheet_to_pdf(file_id, path, creds)
        except Exception as e:
            print(f"[WARN] PDF 미리 만들기 실패 - {file_id}: {e}")
        with _PREFETCH_LOCK:
            current = _PREFETCH.get(file_id)
            if current is entry:          # 그 사이 내용이 바뀌지 않았을 때만 사용 가능으로 표시
                entry["path"] = path if ok else None
                entry["ok"] = ok
            elif ok and os.path.exists(path):
                os.remove(path)
        entry["done"].set()
        print(f"[PDF 미리 만들기] {file_id} {'완료' if ok else '실패'}", flush=True)

    threading.Thread(target=work, daemon=True).start()
    return "started"


def pdf_prefetch_take(file_id, dest_path, wait_seconds=25):
    """미리 만든 PDF를 dest_path로 옮겨 쓰면 True. 아직 만드는 중이면 최대 wait_seconds 기다림."""
    with _PREFETCH_LOCK:
        entry = _PREFETCH.get(file_id)
    if not entry:
        return False
    if not entry["done"].wait(wait_seconds):
        print(f"[PDF 미리 만들기] {file_id} 대기 시간 초과 → 지금 변환", flush=True)
        return False
    with _PREFETCH_LOCK:
        if _PREFETCH.get(file_id) is not entry or not entry["ok"] or not entry["path"]:
            return False
        _PREFETCH.pop(file_id, None)
        src = entry["path"]
    try:
        shutil.move(src, dest_path)
        print(f"[PDF 미리 만들기] {file_id} 미리 만든 PDF 사용", flush=True)
        return True
    except OSError as e:
        print(f"[WARN] 미리 만든 PDF 이동 실패 → 지금 변환: {e}")
        return False


@app.post("/prepare-pdf")
async def prepare_pdf(request: Request):
    """미리보기 화면이 열리면 호출 — PDF 변환을 미리 시작 (기록·업로드는 하지 않음)"""
    try:
        data = await request.json()
    except Exception:
        data = {}
    file_id = str(data.get("fileId") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", file_id):
        return {"status": "skip"}
    return {"status": pdf_prefetch_start(file_id)}


class StepTimer:
    """단계별 소요 시간을 Render 로그에 남김. 로그에서 '[TIMING]'으로 검색."""

    def __init__(self, name):
        self.name = name
        self.start = self.last = time.time()
        self.steps = []

    def lap(self, label):
        now = time.time()
        self.steps.append(f"{label} {now - self.last:.1f}s")
        self.last = now

    def total(self):
        print(f"[TIMING] {self.name} 총 {time.time() - self.start:.1f}s | " + " → ".join(self.steps), flush=True)


# 담당자 → 견적번호 기호 (staff.py가 유일한 원본)
PERSON_ID_MAP = {p["name"]: p["id"] for p in STAFF}
AUTO_NUMBER_RE = re.compile(r"^DLP(\d{6})-([A-Z])-(\d+)$")


def person_letter(supplier_person):
    """'애니트론사업부 황영태 대리'처럼 직함이 붙은 이름에서도 기호를 찾음 (못 찾으면 B)"""
    for name, letter in PERSON_ID_MAP.items():
        if name in (supplier_person or ""):
            return letter
    return "B"


def issued_numbers():
    """발행목록 B열(견적번호) 전체"""
    _, gc, _ = get_google_clients()
    return gc.open_by_key(DATA_COLLECTION_SHEET_ID).sheet1.col_values(2)


def next_seq_from(numbers, date_short, person_id):
    prefix = f"DLP{date_short}-{person_id}-"
    max_seq = 0
    for num in numbers:
        if num.startswith(prefix):
            try:
                max_seq = max(max_seq, int(num[len(prefix):]))
            except ValueError:
                pass
    return max_seq + 1


def get_next_seq_number(date_short, person_id):
    """담당자·날짜별 다음 견적 순번을 시트의 실제 견적번호(B열) 기준으로 계산.

    이전에는 로컬 파일(pdf_count.json)로 카운트했는데, Render 서버가 재배포/재시작될
    때마다 파일이 초기화되어 순번이 1로 되돌아가는 버그가 있었음(같은 날 같은 담당자가
    여러 건 발행해도 전부 -1로 찍혀 중복 견적번호 발생 → 견적성공집계에서 서로 다른
    견적이 같은 견적번호로 오인되어 하나로 합쳐짐). 서버 상태에 의존하지 않도록
    시트에 이미 기록된 최대 순번 + 1로 변경.
    """
    try:
        return next_seq_from(issued_numbers(), date_short, person_id)
    except Exception as e:
        print(f"[ERROR] 견적번호 순번 계산 오류: {e}")
        return 1


def resolve_estimate_number(requested, supplier_person):
    """최종 견적번호와 변경 여부를 반환.

    - 비어 있으면: 오늘 날짜 + 담당자 기호로 새로 채번
    - 'DLP날짜-기호-순번' 형식인데 이미 발행목록에 있으면: 같은 날짜·기호의 다음 순번으로 교체
      (2026-11 이전 폼은 항상 -1을 채워 보내서 서로 다른 견적이 같은 번호로 발행됐음)
    - 직접 입력한 다른 형식의 번호는 그대로 사용
    """
    requested = (requested or "").strip()
    try:
        if not requested:
            date_short = datetime.now().strftime("%y%m%d")
            letter = person_letter(supplier_person)
            return f"DLP{date_short}-{letter}-{get_next_seq_number(date_short, letter)}", False
        m = AUTO_NUMBER_RE.match(requested)
        if not m:
            return requested, False
        numbers = issued_numbers()
        if requested not in numbers:
            return requested, False
        date_short, letter = m.group(1), m.group(2)
        return f"DLP{date_short}-{letter}-{next_seq_from(numbers, date_short, letter)}", True
    except Exception as e:
        # 시트 조회 실패 시 발행은 막지 않음 (번호는 요청값 그대로)
        print(f"[ERROR] 견적번호 중복 확인 실패 (요청값 사용): {e}")
        return requested, False


def find_issued_row(ws, estimate_number, file_id):
    """발행목록에 같은 견적번호 + 같은 견적서 파일(W열 링크)이 있으면 그 행 정보를 반환"""
    if not estimate_number or not file_id:
        return None
    try:
        col_b, col_wy = ws.batch_get(["B:B", "W:Y"])
        for i, row in enumerate(col_b):
            if not row or row[0] != estimate_number:
                continue
            wy = col_wy[i] if i < len(col_wy) else []
            if wy and file_id in wy[0]:
                return {
                    "row": i + 1,
                    "pdf_link": wy[1] if len(wy) > 1 else "",
                    "deal_id": wy[2] if len(wy) > 2 else "",
                }
    except Exception as e:
        print(f"[WARN] 발행목록 중복 확인 실패 (계속 진행): {e}")
    return None


@app.get("/next-estimate-number")
def next_estimate_number(date: str = "", person_id: str = ""):
    """견적폼에서 날짜·담당자를 고르면 발행목록 기준 다음 견적번호를 돌려줌.
    date: YYMMDD 또는 YYYY-MM-DD, person_id: A~F"""
    date_short = re.sub(r"\D", "", date)
    if len(date_short) == 8:
        date_short = date_short[2:]
    person_id = (person_id or "").strip().upper()
    if len(date_short) != 6 or not re.fullmatch(r"[A-Z]", person_id):
        return {"status": "error", "message": "date(YYMMDD)와 person_id(A~F)가 필요합니다."}
    try:
        seq = next_seq_from(issued_numbers(), date_short, person_id)
        return {"status": "success", "estimate_number": f"DLP{date_short}-{person_id}-{seq}", "seq": seq}
    except Exception as e:
        print(f"[ERROR] /next-estimate-number 실패: {e}")
        return {"status": "error", "message": str(e)}

def get_today_pdf_count():
    """오늘 PDF 생성 횟수를 가져오고 +1 증가시킵니다."""
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # pdf_count.json 파일 읽기
        if os.path.exists("pdf_count.json"):
            with open("pdf_count.json", "r", encoding="utf-8") as f:
                count_data = json.load(f)
        else:
            count_data = {}
        
        # 오늘 카운트 가져오기 (없으면 0)
        today_count = count_data.get(today, 0)
        
        # 카운트 +1 증가
        count_data[today] = today_count + 1
        
        # 파일에 저장
        with open("pdf_count.json", "w", encoding="utf-8") as f:
            json.dump(count_data, f, ensure_ascii=False, indent=2)
        
        print(f"오늘 PDF 생성 횟수: {today_count + 1}")
        return today_count + 1
        
    except Exception as e:
        print(f"PDF 카운트 처리 오류: {e}")
        return 1  # 오류 시 기본값 1

@app.get("/test")
async def test_endpoint():
    """간단한 테스트 엔드포인트"""
    return {"status": "success", "message": "서버가 정상적으로 작동 중입니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT) 