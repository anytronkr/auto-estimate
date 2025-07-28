# 견적서 자동 생성 시스템

Google Sheets 기반 견적서를 자동으로 생성하고 Pipedrive CRM에 연동하는 FastAPI 애플리케이션입니다.

## 🚀 Render.com 배포

### 1. GitHub 저장소 준비
```bash
# 현재 프로젝트를 GitHub에 업로드
git init
git add .
git commit -m "Initial commit for Render deployment"
git branch -M main
git remote add origin https://github.com/yourusername/estimate-api.git
git push -u origin main
```

### 2. Render.com에서 배포
1. [Render.com](https://render.com)에 가입
2. "New Web Service" 클릭
3. GitHub 저장소 연결
4. 다음 설정으로 구성:
   - **Name**: `estimate-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### 3. 환경 변수 설정
Render.com 대시보드에서 다음 환경 변수를 설정:

#### Google Sheets API
- `GOOGLE_CREDENTIALS`: Google Service Account JSON 내용 (전체 JSON을 한 줄로)

#### Pipedrive API
- `PIPEDRIVE_API_TOKEN`: Pipedrive API 토큰
- `PIPEDRIVE_DOMAIN`: Pipedrive 도메인 (예: anytronkr.pipedrive.com)
- `PIPEDRIVE_PIPELINE_ID`: 파이프라인 ID
- `PIPEDRIVE_STAGE_ID`: 스테이지 ID

#### Google Drive
- `GOOGLE_DRIVE_FOLDER_ID`: PDF 저장할 Google Drive 폴더 ID

## 📁 파일 구조

```
견적프로그램/
├── main.py                 # FastAPI 메인 애플리케이션
├── config.py              # 기본 설정
├── requirements.txt       # Python 의존성
├── render.yaml           # Render.com 배포 설정
├── Procfile              # Render.com 프로세스 설정
├── runtime.txt           # Python 버전
├── .gitignore           # Git 무시 파일
├── estimate_form.html    # 견적서 작성 폼
├── preview.html         # 견적서 미리보기
├── pdf-sharing.html     # PDF 공유 페이지
└── wordpress_templates/ # 워드프레스 연동 템플릿
    ├── estimate-form-template.php
    ├── preview-template.php
    ├── pdf-sharing-template.php
    └── js/
        └── estimate-api.js
```

## 🔧 환경 변수 설정 방법

### Google Service Account 설정
1. Google Cloud Console에서 Service Account 생성
2. Google Sheets API, Google Drive API 활성화
3. JSON 키 파일 다운로드
4. JSON 내용을 `GOOGLE_CREDENTIALS` 환경 변수에 설정

### Pipedrive 설정
1. Pipedrive API 토큰 생성
2. 파이프라인 및 스테이지 ID 확인
3. 환경 변수에 설정

## 🌐 워드프레스 연동

### 1. 워드프레스 템플릿 업로드
`wordpress_templates/` 폴더의 PHP 파일들을 워드프레스 테마에 업로드

### 2. 페이지 생성
- 견적서 작성: `/auto-quote/input-quote`
- 견적서 미리보기: `/auto-quote/preview`
- PDF 공유: `/auto-quote/pdf-sharing`

### 3. CORS 설정 확인
Render.com 배포 후 도메인이 CORS 허용 목록에 포함되어 있는지 확인

## 📊 API 엔드포인트

- `GET /health`: 헬스 체크
- `GET /estimate_form.html`: 견적서 작성 폼
- `GET /preview.html`: 견적서 미리보기
- `GET /pdf-sharing.html`: PDF 공유 페이지
- `POST /estimate`: 견적서 데이터 처리
- `POST /collect-data`: PDF 생성 및 Pipedrive 연동

## 🔍 문제 해결

### 배포 후 문제
1. Render.com 로그 확인
2. 환경 변수 설정 확인
3. Google API 권한 확인
4. CORS 설정 확인

### 로컬 테스트
```bash
pip install -r requirements.txt
python main.py
```

## 📞 지원

문제가 발생하면 Render.com 로그를 확인하거나 GitHub Issues에 문의해주세요. 