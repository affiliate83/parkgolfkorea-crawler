"""기존 파크골프장(parkgolf_course) 포스트에 AI 풍부화 콘텐츠 소급 적용"""
import sys
import os
import re
import time
import base64
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from enricher import enrich_course

WP_URL      = os.getenv('WP_URL')
WP_USER     = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')

AUTH_HEADER = {
    'Authorization': 'Basic ' + base64.b64encode(
        f'{WP_USER}:{WP_APP_PASS}'.encode()
    ).decode(),
    'Content-Type': 'application/json'
}

# 한 번 실행에 처리할 최대 포스트 수 (API 비용 제어)
BATCH_SIZE = int(os.getenv('ENRICH_BATCH', '50'))


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


def parse_course_data(post: dict) -> dict:
    """포스트에서 골프장 정보 추출 (메타 우선, 없으면 content 파싱)"""
    meta = post.get('meta', {}) or {}
    title = extract_text(post.get('title', {}).get('rendered', ''))
    raw = post.get('content', {}).get('raw', '')

    address = meta.get('course_address', '')
    phone   = meta.get('course_phone', '')
    homepage = meta.get('course_homepage', '')

    # 메타에 없으면 content 테이블에서 파싱
    if not address:
        m = re.search(r'📍\s*주소</th><td>([^<]+)', raw)
        if m:
            address = m.group(1).strip()
    if not phone:
        m = re.search(r'📞\s*전화</th><td>([^<]+)', raw)
        if m:
            phone = m.group(1).strip()
            if phone in ('정보 없음', '현장 문의'):
                phone = ''

    # 운영시간/요금이 테이블에 실제 값으로 채워진 경우 추출
    hours = ''
    m = re.search(r'🕐\s*운영시간</th><td>([^<]+)', raw)
    if m and m.group(1).strip() not in ('현장 문의', '정보 없음'):
        hours = m.group(1).strip()

    fee = ''
    m = re.search(r'💰\s*이용요금</th><td>([^<]+)', raw)
    if m and m.group(1).strip() not in ('현장 문의', '정보 없음'):
        fee = m.group(1).strip()

    return {
        'name':    title,
        'address': address,
        'phone':   phone,
        'hours':   hours,
        'fee':     fee,
        'region':  '',
    }


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
    print('🤖 파크골프장 AI 풍부화 시작')
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

            # 이미 풍부화된 포스트 건너뜀
            if 'faq-item' in raw:
                skip += 1
                continue

            processed += 1
            print(f'[{processed}] {title}')

            data = parse_course_data(post)
            enriched = enrich_course(data)

            if not enriched:
                print('  ⚠️  AI 생성 실패, 건너뜀')
                fail += 1
                continue

            new_content = raw.rstrip() + '\n\n' + enriched
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
