import requests, os, re, json, base64, sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

WP_URL = os.getenv('WP_URL', 'https://parkgolfk.com')
WP_USER = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')
headers = {
    'Authorization': 'Basic ' + base64.b64encode(f'{WP_USER}:{WP_APP_PASS}'.encode()).decode(),
    'Content-Type': 'application/json',
}

# 1. 현재 콘텐츠 가져오기
r = requests.get(f'{WP_URL}/wp-json/wp/v2/pages/1302', headers=headers, params={'context': 'edit'})
print('GET status:', r.status_code)
if r.status_code != 200:
    print(r.text[:500])
    exit(1)

data = r.json()
content = data['content']['raw']
print('Content length:', len(content))

# 2. 변경 1: 안티그라비티 → 피엠케이
content_new = content.replace('안티그라비티', '피엠케이')
if content_new == content:
    print('WARNING: 안티그라비티 not found')
else:
    print('OK: 안티그라비티 → 피엠케이 치환 완료')

# 3. 변경 2: 광고 및 제휴 안내 섹션 제거
# h2 태그부터 다음 h2 또는 끝까지 제거
pattern = r'<h2[^>]*>광고 및 제휴 안내</h2>.*?(?=<h2|\Z)'
content_new2 = re.sub(pattern, '', content_new, flags=re.DOTALL)
if content_new2 == content_new:
    print('WARNING: 광고 및 제휴 안내 section not found, trying alternate pattern')
    # 줄바꿈 포함 다른 패턴 시도
    pattern2 = r'\n*<h2[^>]*>\s*광고 및 제휴 안내\s*</h2>[\s\S]*?(?=\n<h2|\Z)'
    content_new2 = re.sub(pattern2, '', content_new, flags=re.DOTALL)
    if content_new2 == content_new:
        print('WARNING: still not found, showing nearby content')
        idx = content_new.find('광고')
        print(repr(content_new[idx-50:idx+300]))
    else:
        print('OK: 광고 및 제휴 안내 섹션 제거 완료 (alternate)')
else:
    print('OK: 광고 및 제휴 안내 섹션 제거 완료')

print('New content length:', len(content_new2))

# 4. 업데이트
payload = {'content': content_new2}
r2 = requests.post(f'{WP_URL}/wp-json/wp/v2/pages/1302', headers=headers, json=payload)
print('POST status:', r2.status_code)
if r2.status_code in (200, 201):
    print('SUCCESS: About 페이지 업데이트 완료')
else:
    print('ERROR:', r2.text[:300])
