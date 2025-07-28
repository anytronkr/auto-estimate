import gspread
gc = gspread.service_account(filename='creds.json')
sh = gc.open_by_key('1aItq8Vd9qAaEuN7EmOv5XYI_cf9nOX1kweOKfNMDZrg')
ws = sh.sheet1

# A15 셀에 "테스트"라는 값을 써봅니다.
ws.update('A15', '테스트')
print("쓰기 성공!")