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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 정적 파일 서빙 설정 제거 (루트 경로와 충돌 방지)
# app.mount("/static", StaticFiles(directory="."), name="static")

# Health check 엔드포인트 (Render.com용)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Estimate API is running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Keep-alive 엔드포인트 (서버 활성 상태 유지)
@app.get("/ping")
async def ping():
    return {"pong": datetime.now().isoformat()}

# PDF export 및 구글 드라이브 업로드 함수
FOLDER_ID = get_google_drive_folder_id()

# 견적서 템플릿 스프레드시트 ID
TEMPLATE_SHEET_ID = os.environ.get("TEMPLATE_SHEET_ID", "1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg")
# TEMPLATE_SHEET_ID = "1Rf7dGonf0HgAfZ-XS3cW1Hp3V-NiOTWbt8m_qRtyzBY"  # 원래 ID (Service Account 접근 불가)
# 견적서 저장 폴더 ID
# "양식" 폴더 ID를 여기에 설정하세요
# Google Drive에서 "양식" 폴더로 이동 후 URL에서 폴더 ID 확인
# 예: https://drive.google.com/drive/folders/1AbCDeFgHiJKlmNOpQRstuVWxyz1234567
ESTIMATE_FOLDER_ID = os.environ.get("ESTIMATE_FOLDER_ID", "1g05Y9LbrGg9-uq9p1g_CI1ejeLaeInWB")
# ESTIMATE_FOLDER_ID = "1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg"  # 임시 설정
# ESTIMATE_FOLDER_ID = "1WNknyHABe-co_ypAM0uGM_Z9z_62STeS"  # 원래 폴더 (Service Account 접근 불가)

def get_credentials():
    """Google Service Account 자격증명 가져오기"""
    print("=== 자격증명 로드 시작 ===")
    
    # 환경변수에서 직접 로드 (권장 방법)
    try:
        creds = get_google_credentials()
        if creds:
            print(f"✅ 환경변수에서 자격증명 로드 성공 - 타입: {type(creds)}")
            return creds
        else:
            print("⚠️ 환경변수에서 자격증명 로드 실패")
    except Exception as e:
        print(f"❌ 환경변수에서 자격증명 로드 중 오류: {e}")
    
    # 로컬 파일에서 fallback (개발용)
    if os.path.exists(CREDS_PATH):
        print("📁 로컬 creds.json 파일에서 자격증명 로드 시도")
        try:
            creds = service_account.Credentials.from_service_account_file(
                CREDS_PATH,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.file',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
            )
            print("✅ 로컬 파일에서 자격증명 로드 성공")
            return creds
        except Exception as e:
            print(f"❌ 로컬 파일에서 자격증명 로드 실패: {e}")
    else:
        print(f"❌ 로컬 파일 {CREDS_PATH}이 존재하지 않습니다")
    
    print("❌ Google Service Account 자격증명을 찾을 수 없습니다.")
    print("=== 자격증명 로드 종료 ===")
    return None

def copy_estimate_template():
    """견적서 템플릿 스프레드시트를 복사하여 새 파일 생성"""
    try:
        print("견적서 템플릿 복사 시작...")
        
        # 시간 동기화 진단
        current_time = datetime.now()
        print(f"현재 서버 시간: {current_time}")
        print(f"현재 서버 시간 (UTC): {current_time.utcnow()}")
        print(f"현재 타임스탬프: {time.time()}")
        
        creds = get_credentials()
        if not creds:
            return {"status": "error", "message": "Google Service Account 자격증명을 가져올 수 없습니다."}
        
        print("자격증명 타입:", type(creds))
        print("자격증명 만료 시간:", getattr(creds, 'expiry', 'N/A'))
        
        print("Google Drive API 서비스 생성 중...")
        
        # 자격증명 새로고침 시도 (더 강력한 방법)
        try:
            if hasattr(creds, 'refresh'):
                print("자격증명 새로고침 시도...")
                from google.auth.transport.requests import Request as GoogleRequest
                creds.refresh(GoogleRequest())
                print("자격증명 새로고침 완료")
        except Exception as refresh_error:
            print("자격증명 새로고침 실패:", refresh_error)
            # 새로고침 실패해도 계속 진행
        
        # Google Drive API 서비스 생성 (타임아웃 설정 추가)
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        # 현재 시간을 YYMMDD HHmm 형식으로 포맷
        now = datetime.now()
        formatted_date = now.strftime("%y%m%d %H%M")
        
        # 새 파일명 생성
        new_filename = f"견적서_DLP_{formatted_date}"
        
        # 파일 복사 요청
        copy_metadata = {
            'name': new_filename,
            'parents': [ESTIMATE_FOLDER_ID]  # 지정된 폴더에 저장
        }
        
        # 스프레드시트 복사
        copied_file = service.files().copy(
            fileId=TEMPLATE_SHEET_ID,
            body=copy_metadata
        ).execute()
        
        new_file_id = copied_file['id']
        
        print(f"견적서 템플릿 복사 완료: {new_filename} (ID: {new_file_id})")
        
        return {
            "status": "success",
            "file_id": new_file_id,
            "filename": new_filename,
            "message": "견적서 템플릿이 성공적으로 복사되었습니다."
        }
        
    except Exception as e:
        print(f"견적서 템플릿 복사 중 오류: {str(e)}")
        return {
            "status": "error",
            "message": f"견적서 템플릿 복사 중 오류가 발생했습니다: {str(e)}"
        }

def get_pipedrive_settings():
    """환경변수에서 Pipedrive 설정 가져오기"""
    config = get_pipedrive_config()
    
    # 로컬 개발용 fallback
    if not config['api_token']:
        try:
            from pipedrive_config_local import (
                PIPEDRIVE_API_TOKEN, PIPEDRIVE_DOMAIN, 
                PIPEDRIVE_PIPELINE_ID, PIPEDRIVE_STAGE_ID, PIPEDRIVE_USER_MAPPING
            )
            config = {
                'api_token': PIPEDRIVE_API_TOKEN,
                'domain': PIPEDRIVE_DOMAIN,
                'pipeline_id': PIPEDRIVE_PIPELINE_ID,
                'stage_id': PIPEDRIVE_STAGE_ID,
                'user_mapping': PIPEDRIVE_USER_MAPPING
            }
            print("Pipedrive 설정 로드 성공")
            print(f"API Token: {PIPEDRIVE_API_TOKEN[:10]}...")
            print(f"Domain: {PIPEDRIVE_DOMAIN}")
            print(f"Pipeline ID: {PIPEDRIVE_PIPELINE_ID}")
            print(f"Stage ID: {PIPEDRIVE_STAGE_ID}")
            print(f"User Mapping: {PIPEDRIVE_USER_MAPPING}")
        except ImportError:
            print("pipedrive_config_local.py 파일을 찾을 수 없습니다.")
            config = {
                'api_token': 'your_pipedrive_api_token_here',
                'domain': 'your_pipedrive_domain.pipedrive.com',
                'pipeline_id': 1,
                'stage_id': 1,
                'user_mapping': {
                    "이훈수": 1,
                    "차재원": 2,
                    "장진호": 3,
                }
            }
    
    return config

def export_sheet_to_pdf(sheet_id, pdf_filename, creds, gid=0):
    # 구글 시트 PDF로 export (OAuth2 토큰 필요)
    try:
        print(f"DEBUG: export_sheet_to_pdf 함수 시작")
        print(f"DEBUG: sheet_id: {sheet_id}")
        print(f"DEBUG: pdf_filename: {pdf_filename}")
        print(f"DEBUG: gid: {gid}")
        print(f"DEBUG: creds 타입: {type(creds)}")
        
        # 토큰 가져오기 시도 (서비스 계정 방식)
        print(f"DEBUG: 토큰 가져오기 시작")
        try:
            # 서비스 계정 Credentials에서 토큰 가져오기
            from google.auth.transport import requests as google_requests
            creds.refresh(google_requests.Request())
            token = creds.token
            print(f"DEBUG: 토큰 갱신 후 가져옴")
        except Exception as token_e:
            print(f"DEBUG: 토큰 가져오기 실패: {str(token_e)}")
            token = None
        
        if not token:
            print("DEBUG: 유효한 토큰을 가져올 수 없습니다.")
            return False
            
        print(f"DEBUG: 토큰 획득 성공 - 길이: {len(token)}")
        print(f"DEBUG: Token: {token[:20]}...")
        
        # Google Sheets의 첫 번째 시트 gid를 동적으로 가져오기
        try:
            sheets_service = build('sheets', 'v4', credentials=creds)
            spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                # 첫 번째 시트의 gid 사용
                first_sheet_gid = sheets[0]['properties']['sheetId']
                print(f"DEBUG: 첫 번째 시트 gid: {first_sheet_gid}")
                gid = first_sheet_gid
        except Exception as e:
            print(f"DEBUG: 시트 정보 가져오기 실패: {e}")
            # 기본값 0 사용
        
        # Google Sheets API를 사용한 PDF 생성 시도
        try:
            print(f"DEBUG: Google Sheets API PDF 생성 시도")
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Google Sheets를 PDF로 export
            request = drive_service.files().export_media(
                fileId=sheet_id,
                mimeType='application/pdf'
            )
            
            with open(pdf_filename, 'wb') as f:
                f.write(request.execute())
            
            print(f"DEBUG: Google Sheets API PDF 생성 성공: {pdf_filename}")
            return True
            
        except Exception as api_e:
            print(f"DEBUG: Google Sheets API PDF 생성 실패: {api_e}")
            # 기존 방식으로 fallback
        
        url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=pdf"
            f"&gid={gid}"
            "&size=A4"
            "&portrait=true"
            "&scale=2"              # 맞춤 비율로 변경
            "&top_margin=0.3"
            "&bottom_margin=0.3"
            "&left_margin=0.3"
            "&right_margin=0.3"
            "&sheetnames=false"
            "&printtitle=false"
            "&pagenumbers=false"
            "&gridlines=false"      # 그리드라인 숨김
            "&fzr=false"
        )
        print(f"DEBUG: Export URL: {url}")
        
        headers = {"Authorization": f"Bearer {token}"}
        print(f"DEBUG: PDF 요청 URL: {url}")
        response = requests.get(url, headers=headers)
        print(f"DEBUG: 응답코드: {response.status_code}")
        print(f"DEBUG: 응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            with open(pdf_filename, "wb") as f:
                f.write(response.content)
            print(f"DEBUG: PDF 파일 생성 성공: {pdf_filename}")
            print(f"DEBUG: PDF 파일 크기: {len(response.content)} bytes")
            return True
        else:
            print(f"DEBUG: PDF export 실패 - Status: {response.status_code}")
            print(f"DEBUG: 응답 본문 (처음 500자): {response.text[:500]}")
            return False
    except Exception as e:
        print(f"DEBUG: PDF export 예외 발생: {str(e)}")
        return False

def upload_pdf_to_drive(pdf_path, folder_id, file_name, creds):
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

COUNT_FILE = "pdf_count.json"

def count_pdf_today():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(COUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    count = data.get(today, 0) + 1
    data[today] = count
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return count

# Pipedrive API 함수들
def get_pipedrive_user_id(supplier_person):
    """담당자 이름에서 Pipedrive 사용자 ID를 찾습니다."""
    pipedrive_settings = get_pipedrive_settings()
    for name, user_id in pipedrive_settings['user_mapping'].items():
        if name in supplier_person:
            return user_id
    return None

def get_pipedrive_stage_id(supplier_person):
    """담당자 이름에서 Pipedrive 스테이지 ID를 반환합니다."""
    pipedrive_settings = get_pipedrive_settings()
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
            
        pipedrive_settings = get_pipedrive_settings()
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
        
        pipedrive_settings = get_pipedrive_settings()
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
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 한글 폰트 등록 (더 간단한 방법)
        try:
            # reportlab의 기본 한글 폰트 사용
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
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
                    # 제품 타입이 없으면 기본값 설정
                    product_type = product.get('type', '')
                    if not product_type:
                        # 제품명에서 타입 추정
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

def upload_file_to_pipedrive_deal(deal_id, file_path, file_name):
    """Pipedrive 거래에 파일을 업로드합니다."""
    file_handle = None
    try:
        if not deal_id or not file_path:
            print("거래 ID 또는 파일 경로가 없습니다.")
            return None
            
        pipedrive_settings = get_pipedrive_settings()
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
        pipedrive_settings = get_pipedrive_settings()
        deal_data = {
            "title": deal_title,
            "value": final_total,
            "currency": "KRW",
            "pipeline_id": int(pipedrive_settings['pipeline_id']),
            "stage_id": stage_id,
            "user_id": user_id,
            "visible_to": 3  # 전체 회사에서 볼 수 있도록 설정 (1: 소유자만, 3: 전체 회사, 5: 공개)
        }
        
        # 조직과 담당자 ID가 있으면 추가
        if org_id:
            deal_data["org_id"] = org_id
        if person_id:
            deal_data["person_id"] = person_id
        
        # Pipedrive API 호출 (Query Parameter 방식으로 변경)
        pipedrive_settings = get_pipedrive_settings()
        url = f"https://{pipedrive_settings['domain']}/api/v1/deals?api_token={pipedrive_settings['api_token']}"
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"Pipedrive API 호출 정보:")
        print(f"URL: {url}")
        print(f"Token: {pipedrive_settings['api_token'][:10]}...")
        print(f"Headers: {headers}")
        print(f"Data: {deal_data}")
        
        response = requests.post(url, headers=headers, json=deal_data)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
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

# 설정 확인용 엔드포인트 추가
@app.get("/pipedrive-config")
async def get_pipedrive_config():
    """현재 Pipedrive 설정을 반환합니다."""
    pipedrive_settings = get_pipedrive_settings()
    return {
        "api_token": pipedrive_settings['api_token'][:10] + "..." if pipedrive_settings['api_token'] else "설정되지 않음",
        "domain": pipedrive_settings['domain'],
        "pipeline_id": pipedrive_settings['pipeline_id'],
        "stage_id": pipedrive_settings['stage_id'],
        "user_mapping": pipedrive_settings['user_mapping']
    }

# 파이프라인 목록 확인용 엔드포인트 추가
@app.get("/pipedrive-pipelines")
async def get_pipedrive_pipelines():
    """사용 가능한 Pipedrive 파이프라인 목록을 반환합니다."""
    try:
        pipedrive_settings = get_pipedrive_settings()
        url = f"https://{pipedrive_settings['domain']}/api/v1/pipelines?api_token={pipedrive_settings['api_token']}"
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            pipelines = result.get('data', [])
            return {
                "status": "success",
                "pipelines": [
                    {
                        "id": pipeline.get('id'),
                        "name": pipeline.get('name'),
                        "active": pipeline.get('active_flag')
                    }
                    for pipeline in pipelines
                ]
            }
        else:
            return {
                "status": "error",
                "message": f"파이프라인 목록 조회 실패: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"파이프라인 목록 조회 오류: {str(e)}"
        }

# 파이프라인 4의 스테이지 목록 확인용 엔드포인트 추가
@app.get("/pipedrive-stages/{pipeline_id}")
async def get_pipedrive_stages(pipeline_id: int):
    """특정 파이프라인의 스테이지 목록을 반환합니다."""
    try:
        pipedrive_settings = get_pipedrive_settings()
        url = f"https://{pipedrive_settings['domain']}/api/v1/stages?pipeline_id={pipeline_id}&api_token={pipedrive_settings['api_token']}"
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            stages = result.get('data', [])
            return {
                "status": "success",
                "pipeline_id": pipeline_id,
                "stages": [
                    {
                        "id": stage.get('id'),
                        "name": stage.get('name'),
                        "order_nr": stage.get('order_nr'),
                        "active": stage.get('active_flag')
                    }
                    for stage in stages
                ]
            }
        else:
            return {
                "status": "error",
                "message": f"스테이지 목록 조회 실패: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"스테이지 목록 조회 오류: {str(e)}"
        }

# HTML 파일 서빙 엔드포인트들
@app.get("/")
async def root():
    """루트 페이지 - 견적서 생성 시작 페이지 (랜딩 페이지)"""
    print("루트 경로 요청됨 - index.html 서빙 시도")
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        print(f"index.html 파일 읽기 성공, 길이: {len(content)}")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content)
    except FileNotFoundError:
        print("index.html 파일을 찾을 수 없습니다.")
        return {"error": "index.html 파일을 찾을 수 없습니다."}
    except Exception as e:
        print(f"파일 읽기 오류: {str(e)}")
        return {"error": f"파일 읽기 오류: {str(e)}"}

@app.get("/estimate_form.html")
async def estimate_form():
    """견적서 작성 페이지"""
    print("estimate_form.html 경로 요청됨")
    return FileResponse("estimate_form.html")

@app.get("/preview.html")
async def preview():
    """견적서 미리보기 페이지"""
    return FileResponse("preview.html")

@app.get("/pdf-sharing.html")
async def pdf_sharing():
    """PDF 공유 페이지"""
    return FileResponse("pdf-sharing.html")

# 간단한 테스트 엔드포인트
@app.get("/test")
async def test_endpoint():
    """간단한 테스트 엔드포인트"""
    return {"status": "success", "message": "서버가 정상적으로 작동 중입니다."}

@app.post("/create-estimate-template")
async def create_estimate_template():
    """견적서 템플릿 스프레드시트를 복사하여 새 파일 생성"""
    print("=== 견적서 템플릿 생성 API 호출됨 ===")
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f"creds.json 파일 존재: {os.path.exists(CREDS_PATH)}")
    print(f"템플릿 스프레드시트 ID: {TEMPLATE_SHEET_ID}")
    print(f"대상 폴더 ID: {ESTIMATE_FOLDER_ID}")
    
    result = copy_estimate_template()
    print("=== 견적서 템플릿 생성 결과:", result, "===")
    return result

# 테스트용 엔드포인트 추가
@app.post("/test-pipedrive")
async def test_pipedrive(request: Request):
    """Pipedrive 거래 생성 테스트용 엔드포인트"""
    try:
        # 테스트 데이터
        test_data = {
            "supplier_person": "애니트론사업부 이훈수 이사",
            "receiver_company": "테스트회사",
            "receiver_person": "테스트담당자",
            "receiver_contact": "test@test.com",
            "estimate_number": "TEST-2025-001",
            "products": [
                {
                    "name": "테스트제품",
                    "total": 1000000
                }
            ]
        }
        
        # Pipedrive 거래 생성 테스트
        deal_id = create_pipedrive_deal(test_data)
        
        if deal_id:
            return {
                "status": "success",
                "message": f"테스트 거래 생성 성공! 거래 ID: {deal_id}",
                "deal_id": deal_id
            }
        else:
            return {
                "status": "error",
                "message": "테스트 거래 생성 실패"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"테스트 중 오류 발생: {str(e)}"
        }

@app.post("/estimate")
async def fill_estimate(request: Request):
    data = await request.json()
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

    # 일반 필드
    for key in ["estimate_date", "estimate_number", "supplier_person", "supplier_contact", 
                "receiver_company", "receiver_person", "receiver_contact", "delivery_date"]:
        if key in data:
            updates.append({
                "range": CELL_MAP[key],
                "values": [[data[key]]]
            })

    # 제품 정보
    products = data.get("products", [])
    for i in range(8):
        product = products[i] if i < len(products) else {}
        for field in ["type", "name", "detail", "qty", "price", "total", "note"]:
            cell_key = f"products[{i}][{field}]"
            value = product.get(field, "")
            updates.append({
                "range": CELL_MAP[cell_key],
                "values": [[value]]
            })

    ws.batch_update(updates)
    return {"status": "success"}

@app.post("/collect-data")
async def collect_data(request: Request):
    """
    데이터 수집용 스프레드시트에 데이터 추가, PDF 업로드, Pipedrive 거래 생성
    (PDF 생성/업로드/링크 전달 로직을 예전 방식으로 롤백)
    """
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
        
        # PDF 파일 생성 및 업로드 (예전 방식)
        pdf_link = ""
        pdf_id = ""
        pdf_file_path = ""
        file_id = data.get("fileId", "")
        print(f"DEBUG: file_id = {file_id}")
        print(f"DEBUG: 전체 데이터 = {data}")
        
        try:
            product_name = ""
            if products and products[0].get("name"):
                product_name = products[0]["name"]
            estimate_number = data.get("estimate_number", "")
            def clean_filename(s):
                import re
                return re.sub(r'[^\w\s-]', '', s).strip()
            clean_product_name = clean_filename(product_name)
            pdf_filename = f"애니트론견적서_{clean_product_name}_{estimate_number}.pdf"
            # PDF 생성 (Google Sheet export)
            print(f"DEBUG: PDF 생성 시도 - file_id: '{file_id}', pdf_filename: '{pdf_filename}'")
            print(f"DEBUG: file_id 타입: {type(file_id)}, 길이: {len(file_id) if file_id else 0}")
            if file_id and export_sheet_to_pdf(file_id, pdf_filename, creds):
                pdf_file_path = pdf_filename
                # Google Drive 업로드
                pdf_id, pdf_link = upload_pdf_to_drive(pdf_file_path, FOLDER_ID, pdf_filename, creds)
                print(f"DEBUG: Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                # 임시 파일 삭제
                try:
                    if os.path.exists(pdf_file_path):
                        os.remove(pdf_file_path)
                        print(f"DEBUG: 임시 파일 정리 완료 - {pdf_file_path}")
                except Exception as e:
                    print(f"DEBUG: 임시 파일 정리 실패 - {str(e)}")
            else:
                print("DEBUG: PDF export 실패 또는 file_id 없음")
                # Fallback: 테스트 PDF 생성 시도
                print("DEBUG: 테스트 PDF 생성 시도")
                if create_test_pdf(pdf_filename, data):
                    pdf_file_path = pdf_filename
                    # Google Drive 업로드
                    pdf_id, pdf_link = upload_pdf_to_drive(pdf_file_path, FOLDER_ID, pdf_filename, creds)
                    print(f"DEBUG: 테스트 PDF Google Drive 업로드 성공 - {pdf_id}, {pdf_link}")
                    # 임시 파일 삭제
                    try:
                        if os.path.exists(pdf_file_path):
                            os.remove(pdf_file_path)
                            print(f"DEBUG: 임시 파일 정리 완료 - {pdf_file_path}")
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
        
        # PDF 생성이 실패했는지 확인
        if not pdf_link:
            return {
                "status": "error",
                "message": "Google Sheets PDF export 실패: 시트 권한 또는 설정 확인 필요"
            }
        
        # Pipedrive 거래 생성
        pipedrive_deal_id = create_pipedrive_deal(data)
        
        # 거래 생성 성공 시 PDF 파일 업로드
        if pipedrive_deal_id and pdf_file_path and isinstance(pdf_file_path, str):
            upload_file_to_pipedrive_deal(pipedrive_deal_id, pdf_file_path, pdf_filename)
            try:
                if os.path.exists(pdf_file_path):
                    os.remove(pdf_file_path)
                    print(f"DEBUG: 임시 파일 정리 완료 - {pdf_file_path}")
            except Exception as e:
                print(f"DEBUG: 임시 파일 정리 실패 - {str(e)}")
        
        # 거래 생성 성공 시 Pipedrive에 노트(메모) 추가
        if pipedrive_deal_id:
            try:
                pipedrive_settings = get_pipedrive_settings()
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
            pdf_link,                           # S: 견적파일(PDF)
            pipedrive_deal_id                   # T: Pipedrive 거래 ID
        ]
        ws.append_row(row_data)
        pdf_count = count_pdf_today()  # PDF 카운트 증가
        success_message = f"견적 데이터 및 PDF가 성공적으로 추가되었습니다. (오늘 PDF 생성 {pdf_count}회)"
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
            "pdf_count_today": pdf_count,
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
        
        # 파일 복사 시도
        copied = service.files().copy(
            fileId=test_file_id,
            body={
                "name": f"복사된파일_테스트_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                "parents": [target_folder_id]
            }
        ).execute()
        
        copied_file_id = copied["id"]
        print(f"✅ 파일 복사 성공: {copied_file_id}")
        
        # 복사된 파일 정보 가져오기
        file_info = service.files().get(fileId=copied_file_id).execute()
        file_name = file_info.get("name", "Unknown")
        
        # 테스트 파일 삭제 (정리)
        service.files().delete(fileId=copied_file_id).execute()
        print(f"✅ 테스트 파일 삭제 완료: {file_name}")
        
        return {
            "status": "success",
            "message": "파일 복사 테스트 성공",
            "복사된파일ID": copied_file_id,
            "파일명": file_name,
            "테스트파일ID": test_file_id,
            "대상폴더ID": target_folder_id
        }
        
    except Exception as e:
        print(f"❌ 파일 복사 테스트 실패: {e}")
        return {
            "status": "error",
            "message": f"파일 복사 테스트 실패: {str(e)}",
            "테스트파일ID": TEMPLATE_SHEET_ID,
            "대상폴더ID": ESTIMATE_FOLDER_ID
        }

@app.get("/test-file-access")
async def test_file_access():
    """Google Drive 파일 접근 테스트 엔드포인트"""
    try:
        print("=== Google Drive 파일 접근 테스트 시작 ===")
        
        creds = get_credentials()
        if not creds:
            return {"error": "자격증명을 가져올 수 없습니다"}
        
        service = build("drive", "v3", credentials=creds)
        
        # 테스트할 파일 ID
        test_file_id = TEMPLATE_SHEET_ID
        print(f"테스트 파일 ID: {test_file_id}")
        
        # 파일 정보 가져오기
        file_info = service.files().get(fileId=test_file_id).execute()
        
        file_name = file_info.get("name", "Unknown")
        file_type = file_info.get("mimeType", "Unknown")
        owners = file_info.get("owners", [])
        owner_email = owners[0].get("emailAddress", "Unknown") if owners else "Unknown"
        
        print(f"✅ 파일 정보 가져오기 성공")
        print(f"파일명: {file_name}")
        print(f"파일타입: {file_type}")
        print(f"소유자: {owner_email}")
        
        # 권한 정보 가져오기
        permissions = service.permissions().list(fileId=test_file_id).execute()
        permission_list = []
        
        for perm in permissions.get('permissions', []):
            email = perm.get('emailAddress', 'N/A')
            role = perm.get('role', 'N/A')
            permission_list.append({"email": email, "role": role})
            print(f"권한: {email} - {role}")
        
        return {
            "status": "success",
            "message": "파일 접근 테스트 성공",
            "파일정보": {
                "id": test_file_id,
                "name": file_name,
                "type": file_type,
                "owner": owner_email
            },
            "권한정보": permission_list
        }
        
    except Exception as e:
        print(f"❌ 파일 접근 테스트 실패: {e}")
        return {
            "status": "error",
            "message": f"파일 접근 테스트 실패: {str(e)}",
            "테스트파일ID": TEMPLATE_SHEET_ID
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
