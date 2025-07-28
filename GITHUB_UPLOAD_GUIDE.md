# GitHub 수동 업로드 가이드

## 🚀 Git 설치 없이 GitHub에 업로드하는 방법

### 1단계: GitHub 웹사이트에서 직접 업로드

#### 1.1 GitHub 저장소 접속
1. [GitHub.com](https://github.com)에 로그인
2. `anytronkr/auto-estimate` 저장소로 이동
3. 저장소가 비어있는 상태 확인

#### 1.2 파일 업로드
GitHub 웹사이트에서 직접 파일을 업로드할 수 있습니다:

1. **메인 파일들 업로드:**
   - `main.py` - FastAPI 메인 애플리케이션
   - `config.py` - 설정 파일
   - `requirements.txt` - Python 의존성
   - `render.yaml` - Render.com 배포 설정
   - `Procfile` - 프로세스 설정
   - `runtime.txt` - Python 버전
   - `.gitignore` - Git 무시 파일
   - `README.md` - 프로젝트 설명

2. **HTML 파일들 업로드:**
   - `estimate_form.html` - 견적서 작성 폼
   - `preview.html` - 견적서 미리보기
   - `pdf-sharing.html` - PDF 공유 페이지

3. **워드프레스 템플릿 업로드:**
   - `wordpress_templates/` 폴더 전체

### 2단계: GitHub 웹사이트에서 파일 추가

#### 2.1 파일 추가 방법
1. GitHub 저장소 페이지에서 "Add file" 버튼 클릭
2. "Upload files" 선택
3. 파일들을 드래그 앤 드롭으로 업로드
4. 커밋 메시지 입력: "Initial commit for Render deployment"
5. "Commit changes" 클릭

#### 2.2 폴더 구조 생성
GitHub 웹사이트에서는 폴더를 직접 생성할 수 없으므로:
1. 파일명에 경로 포함: `wordpress_templates/estimate-form-template.php`
2. 또는 나중에 Git 설치 후 폴더 구조 정리

### 3단계: Git 설치 후 정리 (권장)

#### 3.1 Git 설치
1. [Git for Windows](https://git-scm.com/download/win) 다운로드
2. 설치 완료 후 PowerShell 재시작

#### 3.2 로컬 저장소 설정
```bash
# 현재 디렉토리에서
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/anytronkr/auto-estimate.git
git push -u origin main
```

## 📁 업로드할 파일 목록

### 필수 파일들:
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
└── wordpress_templates/ # 워드프레스 템플릿
    ├── estimate-form-template.php
    ├── preview-template.php
    ├── pdf-sharing-template.php
    └── js/
        └── estimate-api.js
```

### 제외할 파일들:
- `creds.json` (Google Service Account 키)
- `pipedrive_config_local.py` (로컬 설정)
- `*.log` (로그 파일들)
- `*.pdf` (생성된 PDF 파일들)
- `__pycache__/` (Python 캐시)

## 🔧 빠른 업로드 방법

### 방법 1: GitHub 웹사이트 직접 업로드
1. GitHub 저장소 페이지 접속
2. "Add file" > "Upload files"
3. 모든 파일을 한 번에 드래그 앤 드롭
4. 커밋 메시지 입력 후 저장

### 방법 2: ZIP 파일로 업로드
1. 프로젝트 폴더를 ZIP으로 압축
2. GitHub에서 "Add file" > "Upload files"
3. ZIP 파일 업로드
4. GitHub에서 자동으로 압축 해제

## ⚠️ 주의사항

### 보안 파일 제외
다음 파일들은 절대 업로드하지 마세요:
- `creds.json` - Google Service Account 키
- `pipedrive_config_local.py` - API 토큰
- `.env` - 환경 변수 파일

### 환경 변수 설정
민감한 정보는 Render.com 환경 변수로 설정:
- Google Service Account JSON
- Pipedrive API 토큰
- 기타 API 키들

## 🎯 다음 단계

파일 업로드 완료 후:
1. Render.com에서 GitHub 저장소 연결
2. 환경 변수 설정
3. 배포 및 테스트

## 📞 문제 해결

### 업로드 실패 시
1. 파일 크기 확인 (100MB 이하)
2. 파일명에 특수문자 없는지 확인
3. 인터넷 연결 상태 확인

### Git 설치 후 문제
1. Git 설정 확인: `git config --global user.name "anytronkr"`
2. 인증 설정: Personal Access Token 사용
3. 브랜치 확인: `git branch -M main` 

## 📝 **터미널 재시작 후 Git 확인**

1. **현재 PowerShell 창을 닫고 새로운 PowerShell 창을 열어주세요**
2. **새 터미널에서 다음 명령어를 실행해주세요:**

```bash
git --version
```

만약 여전히 Git이 인식되지 않는다면, 컴퓨터를 재시작해야 할 수도 있습니다.

## 🚀 **Git 설치 확인 후 진행할 단계:**

Git이 정상적으로 인식되면 다음 단계로 진행하겠습니다:

1. **Git 설정**
2. **auto-estimate 폴더로 이동**
3. **Git 저장소 초기화**
4. **GitHub에 업로드**

터미널을 재시작하신 후 Git이 정상적으로 작동하는지 알려주세요! ✨ 