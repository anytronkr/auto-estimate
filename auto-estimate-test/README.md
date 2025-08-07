# Auto Estimate System - Test Version

## 📋 프로젝트 개요
자동 견적서 생성 시스템 - Google Sheets, Google Drive, Pipedrive 연동

## 🚀 배포 방법

### 1. Render.com 배포
1. Render.com 계정 생성
2. "New Web Service" 선택
3. GitHub 저장소 연결
4. 환경 변수 설정

### 2. 필수 환경 변수 설정
Render.com 대시보드에서 다음 환경 변수를 설정하세요:

```
GOOGLE_CREDENTIALS={"type":"service_account","project_id":"your-project-id",...}
TEMPLATE_SHEET_ID=1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg
ESTIMATE_FOLDER_ID=1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg
PIPEDRIVE_API_KEY=your-pipedrive-api-key
```

### 3. Google Service Account 설정
1. Google Cloud Console에서 Service Account 생성
2. Google Drive API, Google Sheets API 활성화
3. Service Account 키 JSON 파일 생성
4. JSON 내용을 `GOOGLE_CREDENTIALS` 환경 변수에 설정

## 🧪 테스트 방법

### 1. 기본 테스트
- **메인 페이지**: `https://your-app.onrender.com/`
- **파일 접근 테스트**: `https://your-app.onrender.com/test-file-access`
- **파일 복사 테스트**: `https://your-app.onrender.com/test-drive-copy`
- **폴더 접근 테스트**: `https://your-app.onrender.com/test-folder-access`

### 2. 전체 플로우 테스트
1. 메인 페이지 접속
2. "견적서 생성 시작" 버튼 클릭
3. 견적서 데이터 입력
4. PDF 생성 및 Pipedrive 연동 확인

## 📁 파일 구조
```
auto-estimate-test/
├── main.py              # FastAPI 메인 애플리케이션
├── config.py            # 설정 및 자격증명 관리
├── requirements.txt     # Python 의존성
├── index.html          # 메인 페이지
├── estimate_form.html  # 견적서 입력 폼
├── preview.html        # 견적서 미리보기
├── pdf-sharing.html    # PDF 공유 페이지
├── .gitignore          # Git 무시 파일
└── README.md           # 이 파일
```

## 🔧 주요 기능
- ✅ Google Sheets 템플릿 복사
- ✅ 견적서 데이터 입력 및 검증
- ✅ PDF 생성 및 Google Drive 업로드
- ✅ Pipedrive CRM 연동
- ✅ 파일 ID 기반 독립 작업

## 🐛 문제 해결
- **404 File not found**: 폴더 ID가 올바른지 확인
- **권한 오류**: Service Account 권한 설정 확인
- **환경 변수 오류**: JSON 형식 확인

## 📞 지원
문제가 발생하면 로그를 확인하고 환경 변수 설정을 점검하세요. 