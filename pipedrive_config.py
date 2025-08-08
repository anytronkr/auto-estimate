# Pipedrive API 설정
# 이 파일을 복사해서 pipedrive_config_local.py로 만들고 실제 값들을 입력하세요

# Pipedrive API 토큰 (Pipedrive 설정 > 개인 설정 > API에서 확인)
PIPEDRIVE_API_TOKEN = "your_pipedrive_api_token_here"

# Pipedrive 도메인 (예: company.pipedrive.com)
PIPEDRIVE_DOMAIN = "api.pipedrive.com"

# 견적서생성 파이프라인 ID (Pipedrive에서 파이프라인 ID 확인)
PIPEDRIVE_PIPELINE_ID = "4"

# 담당자별 Pipedrive 사용자 ID 매핑 (실제 Pipedrive 사용자 ID)
PIPEDRIVE_USER_MAPPING = {
    "이훈수": 23659842,    # hslee@bitekps.com
    "차재원": 23787233,    # cjw@bitekps.com
    "장진호": 23823247,    # jhjang@bitekps.com
    "전준영": 23839164,    # methu78@bitekps.com
    "하철용": 23839131,    # cyha@bitekps.com
    "노재익": 23839109     # jake@bitekps.com
}

# 견적서생성 파이프라인 내 스테이지 ID 매핑
PIPEDRIVE_STAGE_MAPPING = {
    "이훈수": 47,    # 이훈수견적서
    "차재원": 48,    # 차재원견적서
    "전준영": 49,    # 전준영견적서
    "장진호": 50,    # 장진호견적서
    "하철용": 51,    # 하철용견적서
    "노재익": 52     # 노재익견적서
} 