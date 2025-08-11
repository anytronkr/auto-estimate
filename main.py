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
        for key in ["supplier_person", "supplier_email", "supplier_phone", 
                    "receiver_company", "receiver_person", "receiver_email", "receiver_phone", "delivery_date"]:
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
        
        # estimate_number 처리 (사용자 입력값 우선, 없으면 자동 생성)
        estimate_number = data.get("estimate_number", "").strip()
        print(f"DEBUG: 받은 estimate_number 데이터: '{estimate_number}'")
        print(f"DEBUG: estimate_number 타입: {type(estimate_number)}")
        print(f"DEBUG: estimate_number 길이: {len(estimate_number) if estimate_number else 0}")
        
        if estimate_number:
            # 사용자가 입력한 견적번호 사용
            if "estimate_number" in CELL_MAP:
                updates.append({
                    "range": CELL_MAP["estimate_number"],
                    "values": [[estimate_number]]
                })
                print(f"사용자 입력 견적번호 사용: {estimate_number}")
            else:
                print(f"❌ CELL_MAP에 'estimate_number' 키가 없습니다. 사용 가능한 키: {list(CELL_MAP.keys())}")
        else:
            # 견적번호가 없으면 자동 생성
            print(f"DEBUG: estimate_number가 비어있어서 자동 생성합니다.")
            from datetime import datetime
            current_date_short = datetime.now().strftime("%y%m%d")
            supplier_person = data.get("supplier_person", "UNKNOWN")
            
            # 담당자 ID 매핑 (A, B, C, D, E, F) - 이미지 기준
            person_id_map = {
                "이훈수": "A", "차재원": "B", "하철용": "C", 
                "노재익": "D", "전준영": "E", "장진호": "F"
            }
            person_id = person_id_map.get(supplier_person, "B")  # 기본값 B
            
            # 오늘 발행 횟수 (실제 PDF 생성 횟수 카운팅)
            today_count = get_today_pdf_count()
            
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
        
        # 제품상세정보 셀들에 텍스트 줄바꿈 포맷 적용
        try:
            detail_cells = [CELL_MAP[f"products[{i}][detail]"] for i in range(8)]
            for cell in detail_cells:
                ws.format(cell, {
                    "wrapStrategy": "WRAP"
                })
            print(f"✅ 제품상세정보 셀들에 텍스트 줄바꿈 포맷 적용 완료: {detail_cells}")
        except Exception as e:
            print(f"⚠️ 셀 포맷 적용 중 오류 (무시됨): {e}")
        
        # 40행부터 페이지 나누기 설정 (강화된 버전)
        try:
            # Google Sheets API를 사용하여 페이지 나누기 설정
            sheets_service = build('sheets', 'v4', credentials=creds)
            
            # 먼저 기존 페이지 나누기 제거
            clear_request = {
                "requests": [
                    {
                        "deleteBanding": {
                            "bandedRangeId": 1
                        }
                    }
                ]
            }
            
            # 40행에 페이지 나누기 추가 (수직 페이지 나누기)
            page_break_request = {
                "requests": [
                    {
                        "insertPageBreak": {
                            "location": {
                                "sheetId": 0,  # 첫 번째 시트
                                "rowIndex": 39  # 40행 (0부터 시작하므로 39)
                            }
                        }
                    }
                ]
            }
            
            # 페이지 나누기 설정 실행
            result = sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=file_id,
                body=page_break_request
            ).execute()
            
            print(f"✅ 40행에 페이지 나누기 설정 완료: {result}")
            
            # 추가로 셀 높이 조정으로 페이지 나누기 효과 강화
            row_height_request = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": 0,
                                "dimension": "ROWS",
                                "startIndex": 38,  # 39행부터
                                "endIndex": 40     # 41행까지
                            },
                            "properties": {
                                "pixelSize": 25  # 행 높이를 25픽셀로 설정
                            },
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=file_id,
                body=row_height_request
            ).execute()
            
            print("✅ 40행 주변 행 높이 조정 완료")
            
        except Exception as e:
            print(f"⚠️ 페이지 나누기 설정 중 오류 (무시됨): {e}")
            import traceback
            traceback.print_exc()
        
        # B47 셀 합치기 해제 (명판/인감 영역)
        try:
            # B47 셀의 합치기 해제
            ws.unmerge('B47')
            print("✅ B47 셀 합치기 해제 완료")
        except Exception as e:
            print(f"⚠️ B47 셀 합치기 해제 중 오류 (무시됨): {e}")
        
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
    """데이터 수집용 스프레드시트에 데이터 추가, PDF 업로드, Pipedrive 거래 생성"""
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
            
            if file_id and export_sheet_to_pdf(file_id, pdf_filename, creds):
                # Google Drive 업로드
                pdf_id, pdf_link = upload_pdf_to_drive(pdf_filename, get_google_drive_folder_id(), pdf_filename, creds)
                print(f"DEBUG: Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                
                # 임시 파일 삭제
                try:
                    if os.path.exists(pdf_filename):
                        os.remove(pdf_filename)
                        print(f"DEBUG: 임시 파일 정리 완료 - {pdf_filename}")
                except Exception as e:
                    print(f"DEBUG: 임시 파일 정리 실패 - {str(e)}")
            else:
                print("DEBUG: PDF export 실패 또는 file_id 없음")
                # Fallback: 테스트 PDF 생성 시도
                print("DEBUG: 테스트 PDF 생성 시도")
                if create_test_pdf(pdf_filename, data):
                    # Google Drive 업로드
                    pdf_id, pdf_link = upload_pdf_to_drive(pdf_filename, get_google_drive_folder_id(), pdf_filename, creds)
                    print(f"DEBUG: 테스트 PDF Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                    
                    # 임시 파일 삭제
                    try:
                        if os.path.exists(pdf_filename):
                            os.remove(pdf_filename)
                            print(f"DEBUG: 임시 파일 정리 완료 - {pdf_filename}")
                    except Exception as e:
                        print(f"DEBUG: 임시 파일 정리 실패 - {str(e)}")
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
        
        # Pipedrive 거래 생성
        pipedrive_deal_id = create_pipedrive_deal(data)
        
        # 거래 생성 성공 시 PDF 파일 업로드
        if pipedrive_deal_id and pdf_filename and os.path.exists(pdf_filename):
            upload_file_to_pipedrive_deal(pipedrive_deal_id, pdf_filename, pdf_filename)
        
        # 거래 생성 성공 시 Pipedrive에 노트(메모) 추가
        if pipedrive_deal_id:
            try:
                pipedrive_settings = get_pipedrive_config()
                note_content = f"견적서명: {pdf_filename}\n엑셀견적서: {estimate_link}\nPDF견적서: {pdf_link}"
                note_url = f"https://{pipedrive_settings['domain']}/api/v1/notes?api_token={pipedrive_settings['api_token']}"
                note_data = {
                    "content": note_content,
                    "deal_id": pipedrive_deal_id
                }
                note_response = requests.post(note_url, json=note_data)
                print(f"Pipedrive 노트 추가 결과: {note_response.status_code} - {note_response.text}")
            except Exception as e:
                print(f"Pipedrive 노트 추가 오류: {str(e)}")
        
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
            final_total,                        # R: 최종견적(VAT포함)
            data.get("delivery_date", ""),      # S: 납기일
            estimate_link,                      # T: 견적파일(엑셀)
            pdf_link,                           # U: 견적파일(PDF)
            pipedrive_deal_id                   # V: Pipedrive 거래 ID
        ]
        ws.append_row(row_data)
        
        success_message = f"견적 데이터 및 PDF가 성공적으로 추가되었습니다."
        if pipedrive_deal_id:
            success_message += f"\nPipedrive 거래가 성공적으로 생성되었습니다. (거래 ID: {pipedrive_deal_id})"
            success_message += f"\nPDF 파일이 Pipedrive 거래에 첨부되었습니다."
        else:
            success_message += "\nPipedrive 거래 생성에 실패했습니다."
        
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

def export_sheet_to_pdf(sheet_id, pdf_filename, creds, gid=0):
    """Google Sheets를 PDF로 export (페이지 나누기 강화)"""
    try:
        print(f"DEBUG: export_sheet_to_pdf 함수 시작")
        print(f"DEBUG: sheet_id: {sheet_id}")
        print(f"DEBUG: pdf_filename: {pdf_filename}")
        print(f"DEBUG: gid: {gid}")
        
        # PDF 생성 전에 페이지 나누기 재확인
        try:
            sheets_service = build('sheets', 'v4', credentials=creds)
            
            # 40행에 강제 페이지 나누기 설정
            force_page_break = {
                "requests": [
                    {
                        "insertPageBreak": {
                            "location": {
                                "sheetId": 0,
                                "rowIndex": 39  # 40행
                            }
                        }
                    }
                ]
            }
            
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=force_page_break
            ).execute()
            
            print("✅ PDF 생성 전 40행 페이지 나누기 재확인 완료")
            
        except Exception as e:
            print(f"⚠️ PDF 생성 전 페이지 나누기 설정 실패: {e}")
        
        # Google Drive API를 사용한 PDF 생성
        try:
            print(f"DEBUG: Google Drive API PDF 생성 시도")
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Google Sheets를 PDF로 export (페이지 설정 포함)
            request = drive_service.files().export_media(
                fileId=sheet_id,
                mimeType='application/pdf'
            )
            
            with open(pdf_filename, 'wb') as f:
                f.write(request.execute())
            
            print(f"DEBUG: Google Drive API PDF 생성 성공: {pdf_filename}")
            return True
            
        except Exception as api_e:
            print(f"DEBUG: Google Drive API PDF 생성 실패: {api_e}")
            return False
            
    except Exception as e:
        print(f"DEBUG: PDF export 예외 발생: {str(e)}")
        return False

def upload_pdf_to_drive(pdf_path, folder_id, file_name, creds):
    """PDF 파일을 Google Drive에 업로드"""
    try:
        drive_service = build('drive', 'v3', credentials=creds)
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
            ['납기일', data.get('delivery_date', '')]
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

def get_pipedrive_user_id(supplier_person):
    """담당자 이름에서 Pipedrive 사용자 ID를 찾습니다."""
    pipedrive_settings = get_pipedrive_config()
    user_mapping = {
        "이훈수": 23659842,    # hslee@bitekps.com
        "차재원": 23787233,    # cjw@bitekps.com
        "장진호": 23823247,    # jhjang@bitekps.com
        "전준영": 23839164,    # methu78@bitekps.com
        "하철용": 23839131,    # cyha@bitekps.com
        "노재익": 23839109     # jake@bitekps.com
    }
    for name, user_id in user_mapping.items():
        if name in supplier_person:
            return user_id
    return None

def get_pipedrive_stage_id(supplier_person):
    """담당자 이름에서 Pipedrive 스테이지 ID를 반환합니다."""
    stage_mapping = {
        "이훈수": 47,    # 이훈수견적서
        "차재원": 48,    # 차재원견적서
        "전준영": 49,    # 전준영견적서
        "장진호": 50,    # 장진호견적서
        "하철용": 51,    # 하철용견적서
        "노재익": 52,    # 노재익견적서
    }
    for name, stage_id in stage_mapping.items():
        if name in supplier_person:
            return stage_id
    return 47  # 기본값: 이훈수견적서

def create_pipedrive_organization(data):
    """Pipedrive에 조직을 생성합니다."""
    try:
        org_name = data.get("receiver_company", "")
        if not org_name:
            return None
            
        pipedrive_settings = get_pipedrive_config()
        url = f"https://{pipedrive_settings['domain']}/api/v1/organizations?api_token={pipedrive_settings['api_token']}"
        headers = {"Content-Type": "application/json"}
        
        org_data = {
            "name": org_name,
            "visible_to": 3  # 전체 회사에서 볼 수 있도록 설정
        }
        
        response = requests.post(url, headers=headers, json=org_data)
        
        if response.status_code == 201:
            result = response.json()
            org_id = result['data']['id']
            print(f"조직 생성 성공: {org_name} (ID: {org_id})")
            return org_id
        else:
            print(f"조직 생성 실패: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"조직 생성 오류: {e}")
        return None

def create_pipedrive_person(data):
    """Pipedrive에 담당자를 생성합니다."""
    try:
        person_name = data.get("receiver_person", "")
        person_email = data.get("receiver_contact", "")
        if not person_name:
            return None
        
        pipedrive_settings = get_pipedrive_config()
        url = f"https://{pipedrive_settings['domain']}/api/v1/persons?api_token={pipedrive_settings['api_token']}"
        headers = {"Content-Type": "application/json"}
        
        person_data = {
            "name": person_name,
            "visible_to": 3  # 전체 회사에서 볼 수 있도록 설정
        }
        if person_email:
            person_data["email"] = [{"value": person_email, "primary": True, "label": "work"}]
        
        response = requests.post(url, headers=headers, json=person_data)
        
        if response.status_code == 201:
            result = response.json()
            person_id = result['data']['id']
            print(f"담당자 생성 성공: {person_name} (ID: {person_id})")
            return person_id
        else:
            print(f"담당자 생성 실패: {response.status_code} - {response.text}")
            return None
        
    except Exception as e:
        print(f"담당자 생성 오류: {e}")
        return None

def create_pipedrive_deal(data):
    """Pipedrive에 거래를 생성합니다."""
    try:
        # 담당자에서 사용자 ID 찾기
        supplier_person = data.get("supplier_person", "")
        user_id = get_pipedrive_user_id(supplier_person)
        
        if not user_id:
            print(f"담당자 '{supplier_person}'에 해당하는 Pipedrive 사용자를 찾을 수 없습니다.")
            return None
        
        # 최종견적 계산
        products = data.get("products", [])
        total_sum = sum(product.get("total", 0) for product in products if product.get("total"))
        vat = round(total_sum * 0.1)
        final_total = total_sum + vat
        
        # 거래명 생성
        deal_title = f"{data.get('receiver_company', '')} - {data.get('estimate_number', '')}"
        
        # Pipedrive 스테이지 ID 매핑 (담당자별)
        stage_id = get_pipedrive_stage_id(supplier_person)
        print(f"담당자: {supplier_person} → 스테이지 ID: {stage_id}")
        
        # 조직과 담당자 생성
        org_id = create_pipedrive_organization(data)
        person_id = create_pipedrive_person(data)
        
        # Pipedrive API 요청 데이터
        pipedrive_settings = get_pipedrive_config()
        deal_data = {
            "title": deal_title,
            "value": final_total,
            "currency": "KRW",
            "pipeline_id": 4,  # 고정
            "stage_id": stage_id,
            "user_id": user_id,
            "visible_to": 3  # 전체 회사에서 볼 수 있도록 설정
        }
        
        # 조직과 담당자 ID가 있으면 추가
        if org_id:
            deal_data["org_id"] = org_id
        if person_id:
            deal_data["person_id"] = person_id
        
        # Pipedrive API 호출
        url = f"https://{pipedrive_settings['domain']}/api/v1/deals?api_token={pipedrive_settings['api_token']}"
        headers = {"Content-Type": "application/json"}
        
        print(f"Pipedrive API 호출 정보:")
        print(f"URL: {url}")
        print(f"Data: {deal_data}")
        
        response = requests.post(url, headers=headers, json=deal_data)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"Pipedrive 거래 생성 성공: {result['data']['id']}")
            return result['data']['id']
        else:
            print(f"Pipedrive 거래 생성 실패: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Pipedrive 거래 생성 오류: {e}")
        return None

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
        
        response = requests.post(url, files=files, data=data)
        
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