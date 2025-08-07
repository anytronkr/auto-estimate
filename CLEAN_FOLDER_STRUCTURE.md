# GitHub 업로드용 폴더 구조 정리

## 🧹 정리 전 vs 정리 후

### 현재 폴더 (정리 전):
```
견적프로그램/
├── main.py ✅ (필요)
├── config.py ✅ (필요)
├── requirements.txt ✅ (필요)
├── render.yaml ✅ (필요)
├── Procfile ✅ (필요)
├── runtime.txt ✅ (필요)
├── .gitignore ✅ (필요)
├── README.md ✅ (필요)
├── estimate_form.html ✅ (필요)
├── preview.html ✅ (필요)
├── pdf-sharing.html ✅ (필요)
├── wordpress_templates/ ✅ (필요)
├── GITHUB_UPLOAD_GUIDE.md ✅ (필요)
├── deployment_guide_render.md ✅ (필요)
├── deployment_guide.md ❌ (불필요)
├── PIPEDRIVE_SETUP.md ❌ (불필요)
├── test_gspread.py ❌ (불필요)
├── test_pipedrive.html ❌ (불필요)
├── pipedrive_config_local.py ❌ (보안상 제외)
├── pipedrive_config.py ❌ (불필요)
├── creds.json ❌ (보안상 제외)
├── pdf_count.json ❌ (불필요)
├── 견적프로그램백업0728.zip ❌ (불필요)
├── logUploaderSettings.ini ❌ (불필요)
├── logUploaderSettings_temp.ini ❌ (불필요)
├── Setup.log ❌ (불필요)
├── RHDSetup.log ❌ (불필요)
└── __pycache__/ ❌ (불필요)
```

### 정리 후 폴더 구조:
```
auto-estimate/
├── main.py
├── config.py
├── requirements.txt
├── render.yaml
├── Procfile
├── runtime.txt
├── .gitignore
├── README.md
├── estimate_form.html
├── preview.html
├── pdf-sharing.html
├── wordpress_templates/
│   ├── estimate-form-template.php
│   ├── preview-template.php
│   ├── pdf-sharing-template.php
│   └── estimate-api.js
└── docs/
    ├── GITHUB_UPLOAD_GUIDE.md
    └── deployment_guide_render.md
```

## 🗑️ 제거할 파일들

### 보안상 제외 (절대 업로드 금지):
- `creds.json` - Google Service Account 키
- `pipedrive_config_local.py` - API 토큰

### 불필요한 파일들:
- `deployment_guide.md` - 중복 가이드
- `PIPEDRIVE_SETUP.md` - 로컬 설정 가이드
- `test_gspread.py` - 테스트 파일
- `test_pipedrive.html` - 테스트 파일
- `pipedrive_config.py` - 불필요한 설정
- `pdf_count.json` - 로컬 데이터
- `견적프로그램백업0728.zip` - 백업 파일
- `logUploaderSettings.ini` - 로그 설정
- `logUploaderSettings_temp.ini` - 임시 설정
- `Setup.log` - 로그 파일
- `RHDSetup.log` - 로그 파일
- `__pycache__/` - Python 캐시

## 📁 정리 방법

### 1. 새 폴더 생성
```
auto-estimate/
```

### 2. 필수 파일만 복사
```
auto-estimate/
├── main.py
├── config.py
├── requirements.txt
├── render.yaml
├── Procfile
├── runtime.txt
├── .gitignore
├── README.md
├── estimate_form.html
├── preview.html
├── pdf-sharing.html
├── wordpress_templates/
└── docs/
```

### 3. GitHub 업로드
- `auto-estimate/` 폴더 전체를 GitHub에 업로드

## ⚠️ 주의사항

### 보안 파일 절대 업로드 금지:
- `creds.json`
- `pipedrive_config_local.py`
- `*.log` 파일들
- `*.ini` 설정 파일들

### 환경 변수로 설정할 정보:
- Google Service Account JSON
- Pipedrive API 토큰
- Google Drive 폴더 ID

## 🎯 최종 폴더 구조

```
auto-estimate/
├── main.py                 # FastAPI 메인 애플리케이션
├── config.py              # 설정 파일
├── requirements.txt       # Python 의존성
├── render.yaml           # Render.com 배포 설정
├── Procfile              # 프로세스 설정
├── runtime.txt           # Python 버전
├── .gitignore           # Git 무시 파일
├── README.md            # 프로젝트 설명
├── estimate_form.html   # 견적서 작성 폼
├── preview.html        # 견적서 미리보기
├── pdf-sharing.html    # PDF 공유 페이지
├── wordpress_templates/ # 워드프레스 템플릿
│   ├── estimate-form-template.php
│   ├── preview-template.php
│   ├── pdf-sharing-template.php
│   └── estimate-api.js
└── docs/               # 문서
    ├── GITHUB_UPLOAD_GUIDE.md
    └── deployment_guide_render.md
```

이 구조로 정리하면 깔끔하고 안전하게 GitHub에 업로드할 수 있습니다! 