# 🚀 Auto Estimate System - 배포 가이드

## 📋 사전 준비사항

### 1. Google Cloud Console 설정
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 다음 API 활성화:
   - Google Drive API
   - Google Sheets API
4. Service Account 생성:
   - IAM & Admin > Service Accounts
   - "Create Service Account" 클릭
   - 이름: `quotation-api`
   - 역할: Editor
5. Service Account 키 생성:
   - JSON 형식 선택
   - 키 파일 다운로드

### 2. Pipedrive API 설정
1. [Pipedrive](https://app.pipedrive.com/) 계정 생성
2. API 토큰 생성:
   - Settings > Personal preferences > API
   - API 토큰 복사

## 🚀 Render.com 배포

### 1단계: GitHub 저장소 생성
1. GitHub에서 새 저장소 생성
2. `auto-estimate-test` 폴더의 모든 파일을 업로드

### 2단계: Render.com 설정
1. [Render.com](https://render.com/) 접속
2. "New Web Service" 클릭
3. GitHub 저장소 연결
4. 설정:
   - **Name**: `auto-estimate-system`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### 3단계: 환경 변수 설정
Render.com 대시보드에서 다음 환경 변수를 설정:

#### 필수 환경 변수
```
GOOGLE_CREDENTIALS={"type":"service_account","project_id":"your-project-id","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"quotation-api@your-project.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/quotation-api%40your-project.iam.gserviceaccount.com","universe_domain":"googleapis.com"}

TEMPLATE_SHEET_ID=1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg

ESTIMATE_FOLDER_ID=1g05Y9LbrGg9-uq9p1g_CI1ejeLaeInWB

PIPEDRIVE_API_KEY=your-pipedrive-api-token
```

#### 선택적 환경 변수
```
TZ=Asia/Seoul
```

## 🧪 테스트 방법

### 1. 기본 연결 테스트
배포 완료 후 다음 URL로 테스트:

- **메인 페이지**: `https://your-app.onrender.com/`
- **파일 접근 테스트**: `https://your-app.onrender.com/test-file-access`
- **파일 복사 테스트**: `https://your-app.onrender.com/test-drive-copy`
- **폴더 접근 테스트**: `https://your-app.onrender.com/test-folder-access`

### 2. 전체 플로우 테스트
1. 메인 페이지 접속
2. "견적서 생성 시작" 버튼 클릭
3. 견적서 데이터 입력:
   - 공급자/담당자 선택
   - 제품 정보 입력 (최대 8개)
   - 견적 정보 확인
4. "견적서 생성" 버튼 클릭
5. 미리보기 페이지에서 "PDF 파일 생성하기" 클릭
6. PDF 생성 및 Pipedrive 연동 확인

## 🐛 문제 해결

### 일반적인 오류

#### 1. 404 File not found
- **원인**: 폴더 ID가 잘못됨
- **해결**: 올바른 Google Drive 폴더 ID 확인

#### 2. 권한 오류
- **원인**: Service Account 권한 부족
- **해결**: Google Drive에서 폴더 공유 설정

#### 3. 환경 변수 오류
- **원인**: JSON 형식 오류
- **해결**: `GOOGLE_CREDENTIALS` JSON 형식 확인

#### 4. 배포 실패
- **원인**: 의존성 문제
- **해결**: `requirements.txt` 확인

### 로그 확인
Render.com 대시보드에서 로그를 확인하여 오류 원인 파악

## 📞 지원
문제가 발생하면:
1. Render.com 로그 확인
2. 환경 변수 설정 점검
3. Google Cloud Console 권한 확인
4. Pipedrive API 토큰 확인 