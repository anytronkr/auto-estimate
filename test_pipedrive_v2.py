"""
Pipedrive API v2 마이그레이션 사전 점검 (읽기 전용, 아무것도 수정하지 않음)

- 토큰 값은 환경변수에서만 읽고 절대 출력하지 않음
- 이 스크립트의 출력(상태코드/성공여부)만 복사해서 공유하면 됨 (토큰/실제 데이터 노출 없음)
- 실행: PowerShell에서 set-local-env.ps1 로 환경변수 채운 뒤 `python test_pipedrive_v2.py`
"""
import os
import requests

TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN", "")
DOMAIN = os.environ.get("PIPEDRIVE_DOMAIN", "")

if not TOKEN or not DOMAIN or "여기에" in DOMAIN:
    print("❌ PIPEDRIVE_API_TOKEN / PIPEDRIVE_DOMAIN이 설정되지 않았습니다.")
    print("   set-local-env.ps1 에 값을 채운 뒤, 같은 PowerShell 창에서 다시 실행해 주세요.")
    raise SystemExit(1)

V1 = f"https://{DOMAIN}/api/v1"
V2 = f"https://{DOMAIN}/api/v2"


def check(label, url, params=None):
    try:
        res = requests.get(url, params={**(params or {}), "api_token": TOKEN}, timeout=15)
        ok = res.status_code == 200
        body_ok = None
        try:
            body_ok = res.json().get("success")
        except Exception:
            pass
        print(f"{'✅' if ok else '❌'} {label}: HTTP {res.status_code} (success={body_ok})")
        return res
    except Exception as e:
        print(f"❌ {label}: 예외 발생 — {type(e).__name__}: {e}")
        return None


print("=== Pipedrive API v2 점검 시작 (읽기 전용) ===\n")

print("--- 1) v1 기본 동작 확인 (지금까지 쓰던 방식, 기준선) ---")
check("v1 /users/me", f"{V1}/users/me")

print("\n--- 2) v2 인증 방식: api_token 쿼리 파라미터가 v2에서도 되는지 ---")
r = check("v2 /users/me", f"{V2}/users/me")

print("\n--- 3) v2 deals 조회 + 커스텀 필드 구조 확인 ---")
r = check("v2 /deals (limit=1)", f"{V2}/deals", {"limit": 1})
if r is not None and r.status_code == 200:
    try:
        items = r.json().get("data") or []
        if items:
            has_nested = "custom_fields" in items[0]
            print(f"   → custom_fields 중첩 구조 존재: {has_nested} (기대값: True)")
        else:
            print("   → 조회된 거래 없음 (구조 확인 불가, 별도 deal_id로 재확인 필요)")
    except Exception as e:
        print(f"   → 응답 파싱 실패: {e}")

print("\n--- 4) organizations/{id}/deals 대체 방식(org_id 필터) 동작 확인 ---")
check("v2 /deals?org_id=1 (필터 파라미터 수용 여부만 확인)", f"{V2}/deals", {"org_id": 1, "limit": 1})

print("\n--- 5) Notes API v2 존재 여부 ---")
check("v2 /notes (limit=1)", f"{V2}/notes", {"limit": 1})

print("\n--- 6) Files API v2 존재 여부 ---")
check("v2 /files (limit=1)", f"{V2}/files", {"limit": 1})

print("\n=== 점검 완료 — 위 결과를 그대로 복사해서 공유해 주세요 (토큰/실제 데이터 없음) ===")
