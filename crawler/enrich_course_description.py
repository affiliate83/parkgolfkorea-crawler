"""
파크골프장 코스 소개 및 특징 섹션 추가
기존 faq-item 풍부화는 됐지만 course-desc 마커가 없는 포스트 대상
"""
import sys
import os
import re
import time
import base64
import requests
import anthropic
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

WP_URL      = os.getenv('WP_URL')
WP_USER     = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

AUTH_HEADER = {
    'Authorization': 'Basic ' + base64.b64encode(
        f'{WP_USER}:{WP_APP_PASS}'.encode()
    ).decode(),
    'Content-Type': 'application/json'
}

BATCH_SIZE = int(os.getenv('DESC_BATCH', '50'))

_client = None


def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def get_courses(page: int):
    res = requests.get(
        f'{WP_URL}/wp-json/wp/v2/parkgolf_course',
        headers=AUTH_HEADER,
        params={'per_page': 50, 'page': page, 'status': 'publish', 'context': 'edit'},
        timeout=20,
    )
    if res.status_code != 200:
        return []
    return res.json()


def extract_text(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html).strip()


def parse_meta(post: dict) -> dict:
    meta = post.get('meta', {}) or {}
    raw = post.get('content', {}).get('raw', '')
    title = extract_text(post.get('title', {}).get('rendered', ''))

    address = meta.get('course_address', '') or ''
    phone   = meta.get('course_phone', '') or ''
    fee     = meta.get('course_fee', '') or ''
    hours   = meta.get('course_hours', '') or ''

    if not address:
        m = re.search(r'주소</th><td>([^<]+)', raw)
        if m:
            address = m.group(1).strip()
    if not fee:
        m = re.search(r'이용요금</th><td>([^<]+)', raw)
        if m and m.group(1).strip() not in ('현장 문의', '정보 없음'):
            fee = m.group(1).strip()
    if not hours:
        m = re.search(r'운영시간</th><td>([^<]+)', raw)
        if m and m.group(1).strip() not in ('현장 문의', '정보 없음'):
            hours = m.group(1).strip()

    # 지역 추출 (주소 앞 두 단어)
    region = ''
    if address:
        parts = address.split()
        region = ' '.join(parts[:2]) if len(parts) >= 2 else parts[0]

    return {
        'name': title,
        'address': address,
        'phone': phone,
        'fee': fee,
        'hours': hours,
        'region': region,
    }


def generate_description(data: dict) -> str:
    name    = data['name']
    address = data['address']
    region  = data['region']
    fee     = data['fee']
    hours   = data['hours']

    known = []
    if address:
        known.append(f"주소: {address}")
    if hours:
        known.append(f"운영시간: {hours}")
    if fee:
        known.append(f"이용요금: {fee}")
    known_text = '\n'.join(known) if known else ''

    prompt = f"""파크골프 정보 사이트에 게재할 코스 소개 및 특징 HTML을 작성해주세요.

골프장명: {name}
{known_text}

아래 내용을 HTML로만 출력하세요 (설명 텍스트, 마크다운, 코드펜스 없이):

<div class='course-desc'>
<h2>{name} 코스 소개</h2>
(이 파크골프장의 위치 환경, 코스 분위기, 주변 자연환경을 3~4문장으로 소개.
지역({region})의 지리적 특성(강변·도심공원·산림·해안 등)을 반영.
<p> 태그 사용)

<h2>코스 특징 및 난이도</h2>
(코스 구성 특징, 지형 난이도, 초보자/중급자 적합 여부를 <ul><li>로 4~5가지 설명)

<h2>이용 시 참고 사항</h2>
(방문 전 알아두면 좋은 팁, 복장, 준비물, 주차 정보 등 실용적 내용 3~4가지. <ul><li> 태그)
</div>

규칙:
- HTML 속성은 반드시 작은따옴표 사용
- 코드펜스(```) 절대 사용 금지
- 마크다운 문법 금지
- 없는 사실 단정 금지 (홀 수, 정확한 거리 등 확인 안 된 수치 사용 금지)
- 자연스럽고 유익한 한국어로 작성"""

    try:
        msg = get_client().messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        result = msg.content[0].text.strip()
        # 코드펜스 제거
        result = re.sub(r'^```(?:html)?\s*\n?', '', result)
        result = re.sub(r'\n?```\s*$', '', result.strip())
        return result.strip()
    except Exception as e:
        print(f"  [API 오류] {e}")
        return ''


def update_post(post_id: int, new_content: str) -> bool:
    res = requests.post(
        f'{WP_URL}/wp-json/wp/v2/parkgolf_course/{post_id}',
        headers=AUTH_HEADER,
        json={'content': new_content},
        timeout=30,
    )
    return res.status_code in (200, 201)


def main():
    print('=' * 60)
    print('🏌️ 파크골프장 코스 설명 추가')
    print(f'   배치 크기: {BATCH_SIZE}개')
    print('=' * 60)

    processed = success = skip = fail = 0
    page = 1

    while processed < BATCH_SIZE:
        courses = get_courses(page)
        if not courses:
            break

        for post in courses:
            if processed >= BATCH_SIZE:
                break

            post_id = post['id']
            title = extract_text(post.get('title', {}).get('rendered', ''))
            raw = post.get('content', {}).get('raw', '')

            # 이미 코스 설명 추가된 포스트 건너뜀
            if 'course-desc' in raw:
                skip += 1
                continue

            processed += 1
            print(f'[{processed}] {title} (ID: {post_id})')

            data = parse_meta(post)
            desc_html = generate_description(data)

            if not desc_html:
                print('  ⚠️  생성 실패')
                fail += 1
                continue

            new_content = raw.rstrip() + '\n\n' + desc_html
            if update_post(post_id, new_content):
                print(f'  ✅ 완료')
                success += 1
            else:
                print(f'  ❌ 업데이트 실패')
                fail += 1

            time.sleep(2)

        page += 1

    print()
    print('=' * 60)
    print(f'완료: 성공 {success}개 | 스킵(기존) {skip}개 | 실패 {fail}개')
    print('=' * 60)


if __name__ == '__main__':
    main()
