# -*- coding: utf-8 -*-
"""견적 담당자 목록 — 담당자가 바뀌면 이 파일만 고치면 됩니다.

- 견적폼 '담당자' 드롭다운, 이메일·전화 자동입력, 견적번호 기호(DLP날짜-기호-순번)가
  모두 이 목록에서 만들어집니다 (서버가 견적폼을 내려줄 때 자동으로 채움).
- id(기호)는 견적번호에 들어가므로 기존 담당자의 기호는 바꾸지 마세요.
  담당자가 교체되면 같은 기호를 이어받거나(예: 2026-11 장진호→황영태 F), 새 기호(G, H…)를 씁니다.
- 순서는 드롭다운에 보이는 순서입니다.
"""

DEPARTMENT = "애니트론사업부"

STAFF = [
    {"id": "A", "name": "이훈수", "title": "이사", "email": "hslee@bitekps.com", "phone": "010-3252-0593"},
    {"id": "B", "name": "차재원", "title": "차장", "email": "cjw@bitekps.com", "phone": "010-5035-7791"},
    {"id": "C", "name": "하철용", "title": "차장", "email": "cyha@bitekps.com", "phone": "010-6206-7656"},
    {"id": "D", "name": "노재익", "title": "차장", "email": "jake@bitekps.com", "phone": "010-6419-0945"},
    {"id": "E", "name": "전준영", "title": "과장", "email": "methu78@bitekps.com", "phone": "010-2866-4914"},
    {"id": "F", "name": "황영태", "title": "대리", "email": "ythwang@bitekps.com", "phone": "010-8255-5067"},
]


def display_name(person):
    """드롭다운·견적서에 찍히는 이름 (예: '애니트론사업부 황영태 대리')"""
    return f"{DEPARTMENT} {person['name']} {person['title']}"
