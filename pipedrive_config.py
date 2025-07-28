# Pipedrive API 설정
# 이 파일을 복사해서 pipedrive_config_local.py로 만들고 실제 값들을 입력하세요

# Pipedrive API 토큰 (Pipedrive 설정 > 개인 설정 > API에서 확인)
PIPEDRIVE_API_TOKEN = "your_pipedrive_api_token_here"

# Pipedrive 도메인 (예: company.pipedrive.com)
PIPEDRIVE_DOMAIN = "your_domain.pipedrive.com"

# 견적서생성 파이프라인 ID (Pipedrive에서 파이프라인 ID 확인)
PIPEDRIVE_PIPELINE_ID = "1"

# 첫 번째 스테이지 ID (파이프라인의 첫 번째 단계 ID)
PIPEDRIVE_STAGE_ID = "1"

# 담당자별 Pipedrive 사용자 ID 매핑
# Pipedrive에서 각 사용자의 ID를 확인하여 입력하세요
PIPEDRIVE_USER_MAPPING = {
    "이훈수": 1,      # 이훈수 사용자 ID
    "차재원": 2,      # 차재원 사용자 ID  
    "장진호": 3,      # 장진호 사용자 ID
} 