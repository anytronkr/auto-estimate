# Pipedrive 연동 설정 가이드

## 1. Pipedrive API 토큰 발급

1. Pipedrive에 로그인
2. 우측 상단 프로필 클릭 → "개인 설정"
3. 좌측 메뉴에서 "API" 클릭
4. "API 토큰" 복사

## 2. 파이프라인 및 스테이지 ID 확인

### 파이프라인 ID 확인:
1. Pipedrive에서 "견적서생성" 파이프라인으로 이동
2. URL에서 파이프라인 ID 확인: `https://company.pipedrive.com/pipeline/1/deals`
   - 위 예시에서 파이프라인 ID는 `1`

### 스테이지 ID 확인:
1. 파이프라인에서 첫 번째 스테이지 우클릭
2. "스테이지 편집" 클릭
3. URL에서 스테이지 ID 확인: `https://company.pipedrive.com/settings/pipelines/1/stages/1`
   - 위 예시에서 스테이지 ID는 `1`

## 3. 사용자 ID 확인

각 담당자의 사용자 ID를 확인하려면:
1. Pipedrive에서 "설정" → "사용자 및 권한"
2. 각 사용자의 ID 확인

## 4. 설정 파일 생성

1. `pipedrive_config.py` 파일을 복사하여 `pipedrive_config_local.py` 생성
2. 실제 값들로 수정:

```python
# Pipedrive API 토큰
PIPEDRIVE_API_TOKEN = "실제_API_토큰"

# Pipedrive 도메인
PIPEDRIVE_DOMAIN = "company.pipedrive.com"

# 파이프라인 및 스테이지 ID
PIPEDRIVE_PIPELINE_ID = "1"
PIPEDRIVE_STAGE_ID = "1"

# 담당자별 사용자 ID 매핑
PIPEDRIVE_USER_MAPPING = {
    "이훈수": 1,      # 실제 사용자 ID로 변경
    "차재원": 2,      # 실제 사용자 ID로 변경
    "장진호": 3,      # 실제 사용자 ID로 변경
}
```

## 5. 동작 방식

1. 견적서 작성 시 담당자 선택
2. PDF 생성 버튼 클릭
3. 시스템이 자동으로:
   - 구글 스프레드시트에 데이터 저장
   - PDF 파일 생성 및 업로드
   - **Pipedrive에 거래 생성** (새로 추가된 기능)

## 6. Pipedrive 거래 매핑

| 견적서 필드 | Pipedrive 필드 | 설명 |
|------------|---------------|------|
| `supplier_person` | 소유자(Owner) | 담당자 이름으로 사용자 매칭 |
| `receiver_company` | 조직(Organization) | 수신자 회사명 |
| `receiver_person` | 이름(Name) | 수신자 담당자명 |
| `final_total` | 가치(Value) | 최종견적(VAT 포함) |
| `estimate_number` | 거래명 | 회사명 - 견적번호 형식 |

## 7. 테스트

설정 완료 후:
1. 견적서 작성
2. PDF 생성 버튼 클릭
3. Pipedrive에서 "견적서생성" 파이프라인 확인
4. 해당 담당자의 파이프라인에 거래가 생성되었는지 확인 