# Render.com 배포 가이드

## 🚀 Render.com 배포 단계별 가이드

### 1단계: GitHub 저장소 준비

#### 1.1 Git 초기화 및 커밋
```bash
# 현재 디렉토리에서 Git 초기화
git init

# 모든 파일 추가
git add .

# 첫 번째 커밋
git commit -m "Initial commit for Render deployment"

# 메인 브랜치로 설정
git branch -M main
```

#### 1.2 GitHub 저장소 생성 및 업로드
1. [GitHub.com](https://github.com)에서 새 저장소 생성
2. 저장소 이름: `estimate-api` (또는 원하는 이름)
3. Public 또는 Private 선택
4. README, .gitignore, license 체크 해제
5. 저장소 생성 후 다음 명령어 실행:

```bash
# 원격 저장소 추가
git remote add origin https://github.com/yourusername/estimate-api.git

# GitHub에 푸시
git push -u origin main
```

### 2단계: Render.com 계정 생성 및 서비스 배포

#### 2.1 Render.com 가입
1. [Render.com](https://render.com) 방문
2. GitHub 계정으로 가입
3. 이메일 인증 완료

#### 2.2 새 Web Service 생성
1. Render 대시보드에서 "New +" 클릭
2. "Web Service" 선택
3. GitHub 저장소 연결
4. 저장소 선택 후 "Connect" 클릭

#### 2.3 서비스 설정
```
Name: estimate-api
Environment: Python 3
Region: Frankfurt (EU Central) 또는 Singapore (Asia Pacific)
Branch: main
Root Directory: (비워두기)
Build Command: pip install -r requirements.txt
Start Command: gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### 3단계: 환경 변수 설정

#### 3.1 Google Service Account 설정
1. [Google Cloud Console](https://console.cloud.google.com/) 방문
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. Google Sheets API, Google Drive API 활성화
4. Service Account 생성:
   - IAM & Admin > Service Accounts
   - "Create Service Account" 클릭
   - 이름: `estimate-api-service`
   - 설명: `견적서 API용 서비스 계정`
5. JSON 키 파일 다운로드
6. JSON 파일 내용을 복사하여 환경 변수에 설정

#### 3.2 Render.com 환경 변수 설정
Render.com 대시보드 > Environment > Environment Variables에서 다음 변수들을 추가:

```
GOOGLE_CREDENTIALS = {"type":"service_account","project_id":"your-project-id",...}
PIPEDRIVE_API_TOKEN = 641d9cc3317c7e05d50bd95210d0747a65d7599f
PIPEDRIVE_DOMAIN = anytronkr.pipedrive.com
PIPEDRIVE_PIPELINE_ID = 4
PIPEDRIVE_STAGE_ID = 47
GOOGLE_DRIVE_FOLDER_ID = 1uMd2VH07SP1qNsrrwh8IUH4eQuQf6Z9X
```

### 4단계: 배포 및 테스트

#### 4.1 배포 시작
1. "Create Web Service" 클릭
2. 배포 진행 상황 모니터링
3. 배포 완료 후 제공되는 URL 확인 (예: `https://estimate-api.onrender.com`)

#### 4.2 헬스 체크 테스트
브라우저에서 다음 URL 접속:
```
https://your-app-name.onrender.com/health
```
응답: `{"status": "healthy", "message": "Estimate API is running"}`

### 5단계: 워드프레스 연동

#### 5.1 CORS 설정 확인
Render.com 배포 후 실제 도메인으로 CORS 설정 업데이트:

```python
# main.py에서 CORS 설정 수정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bitekps.com",
        "https://www.bitekps.com",
        "https://your-app-name.onrender.com",  # Render.com 도메인 추가
        "http://localhost:3000",
        "http://localhost:9000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

#### 5.2 워드프레스 템플릿 업데이트
`wordpress_templates/` 폴더의 PHP 파일들에서 API URL을 Render.com 도메인으로 변경:

```php
// estimate-form-template.php
<iframe id="estimate-form" 
        class="estimate-form-iframe" 
        src="https://your-app-name.onrender.com/estimate_form.html" 
        style="display: none;" 
        onload="hideLoading()">
</iframe>
```

```javascript
// estimate-api.js
const API_BASE_URL = 'https://your-app-name.onrender.com';
```

### 6단계: 문제 해결

#### 6.1 배포 실패 시
1. Render.com 로그 확인
2. 환경 변수 설정 확인
3. requirements.txt 의존성 확인
4. Python 버전 호환성 확인

#### 6.2 API 연결 실패 시
1. Google Service Account 권한 확인
2. Pipedrive API 토큰 유효성 확인
3. CORS 설정 확인
4. 네트워크 연결 확인

#### 6.3 로그 확인 방법
```bash
# Render.com 대시보드에서
1. 서비스 선택
2. "Logs" 탭 클릭
3. 실시간 로그 확인
4. 에러 메시지 분석
```

### 7단계: 성능 최적화

#### 7.1 무료 플랜 제한사항
- 월 750시간 사용량
- 15분 비활성 후 슬립 모드
- 512MB RAM, 0.1 CPU

#### 7.2 유료 플랜 업그레이드 (선택사항)
- $7/월: 1GB RAM, 0.5 CPU
- $15/월: 2GB RAM, 1 CPU
- 자동 스케일링 지원

### 8단계: 모니터링 및 유지보수

#### 8.1 정기 점검사항
- Render.com 서비스 상태 확인
- Google API 할당량 확인
- Pipedrive API 사용량 확인
- 로그 분석 및 에러 수정

#### 8.2 백업 및 복구
- GitHub 저장소 정기 백업
- 환경 변수 백업
- 데이터베이스 백업 (필요시)

## 🔧 추가 설정

### 커스텀 도메인 설정 (선택사항)
1. 도메인 구매 또는 기존 도메인 사용
2. DNS 설정에서 CNAME 레코드 추가
3. Render.com에서 Custom Domain 설정

### SSL 인증서
- Render.com에서 자동으로 Let's Encrypt SSL 인증서 제공
- HTTPS 연결 자동 활성화

## 📞 지원

문제가 발생하면:
1. Render.com 문서: https://render.com/docs
2. GitHub Issues에 문의
3. 로그 분석 후 구체적인 에러 메시지 제공

## 🎯 배포 완료 체크리스트

- [ ] GitHub 저장소 생성 및 코드 업로드
- [ ] Render.com 계정 생성
- [ ] Web Service 배포
- [ ] 환경 변수 설정
- [ ] 헬스 체크 통과
- [ ] Google API 연결 테스트
- [ ] Pipedrive API 연결 테스트
- [ ] 워드프레스 연동 테스트
- [ ] CORS 설정 확인
- [ ] SSL 인증서 확인 