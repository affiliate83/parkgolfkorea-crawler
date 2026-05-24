"""
얇은 콘텐츠 파크골프장 페이지 noindex 처리
전화/주소/이용요금/운영시간이 모두 비어있는 페이지를 검색 결과에서 제외
"""
import sys
import os
import time
import base64
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

WP_URL      = os.getenv('WP_URL')
WP_USER     = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')

AUTH_HEADER = {
    'Authorization': 'Basic ' + base64.b64encode(
        f'{WP_USER}:{WP_APP_PASS}'.encode()
    ).decode(),
    'Content-Type': 'application/json',
}

EMPTY_VALUES = {'', '정보 없음', '현장 문의', '문의', '-', '해당 없음', '없음', 'none', 'null'}


def is_thin(meta: dict) -> bool:
    """핵심 정보가 3개 이상 비어있으면 thin으로 판정"""
    def empty(v):
        return str(v or '').strip().lower() in EMPTY_VALUES

    score = 0
    if empty(meta.get('course_phone')):    score += 1
    if empty(meta.get('course_fee')):      score += 1
    if empty(meta.get('course_hours')):    score += 1

    addr = str(meta.get('course_address') or '').strip()
    if not addr or len(addr) < 8:          score += 1

    return score >= 3


def detect_seo_plugin(meta: dict) -> str:
    keys = set(meta.keys())
    if any('yoast' in k for k in keys):
        return 'yoast'
    if any('rank_math' in k for k in keys):
        return 'rankmath'
    if any('aioseo' in k for k in keys):
        return 'aioseo'
    return 'unknown'


def apply_noindex(post_id: int, seo_plugin: str) -> bool:
    if seo_plugin == 'yoast':
        payload = {'meta': {'_yoast_wpseo_meta-robots-noindex': '1'}}
    elif seo_plugin == 'rankmath':
        payload = {'meta': {'rank_math_robots': ['noindex']}}
    elif seo_plugin == 'aioseo':
        payload = {'meta': {'_aioseo_robots_noindex': '1', '_aioseo_robots_default': '0'}}
    else:
        return False

    res = requests.post(
        f'{WP_URL}/wp-json/wp/v2/parkgolf_course/{post_id}',
        headers=AUTH_HEADER,
        json=payload,
        timeout=20,
    )
    return res.status_code in (200, 201)


def fetch_all_courses():
    posts, page = [], 1
    while True:
        res = requests.get(
            f'{WP_URL}/wp-json/wp/v2/parkgolf_course',
            headers=AUTH_HEADER,
            params={'per_page': 100, 'page': page, 'context': 'edit',
                    '_fields': 'id,title,meta'},
            timeout=30,
        )
        if res.status_code != 200:
            print(f'  [오류] {res.status_code}: {res.text[:200]}')
            break
        batch = res.json()
        if not batch:
            break
        posts.extend(batch)
        total = int(res.headers.get('X-WP-TotalPages', 1))
        print(f'  {page}/{total} 페이지 로드 (누계 {len(posts)}개)', end='\r')
        if page >= total:
            break
        page += 1
    print()
    return posts


def main():
    print('=' * 60)
    print('🔍 얇은 콘텐츠 파크골프장 noindex 처리')
    print('=' * 60)

    print('\n[1단계] 전체 골프장 포스트 조회 중...')
    all_posts = fetch_all_courses()
    print(f'  → 총 {len(all_posts)}개 조회 완료')

    if not all_posts:
        print('[종료] 포스트를 가져오지 못했습니다.')
        return

    # SEO 플러그인 감지 (Rank Math 설치 확인됨 — 감지 실패 시 강제 적용)
    sample_meta = all_posts[0].get('meta', {}) or {}
    seo_plugin = detect_seo_plugin(sample_meta)
    if seo_plugin == 'unknown':
        seo_plugin = 'rankmath'
    print(f'\n[2단계] SEO 플러그인: {seo_plugin}')

    # thin 분류
    thin_posts  = [p for p in all_posts if is_thin(p.get('meta', {}) or {})]
    ok_posts    = [p for p in all_posts if not is_thin(p.get('meta', {}) or {})]

    print(f'\n[3단계] 콘텐츠 분류 결과')
    print(f'  정상 (정보 충분):    {len(ok_posts):4d}개')
    print(f'  얇은 콘텐츠 (thin): {len(thin_posts):4d}개')
    print(f'  비율: {len(thin_posts)/len(all_posts)*100:.1f}%')

    if not thin_posts:
        print('\n처리할 thin 페이지가 없습니다.')
        return

    print(f'\n[샘플] 얇은 콘텐츠 예시 (상위 5개):')
    for p in thin_posts[:5]:
        m = p.get('meta', {}) or {}
        print(f"  - {p['title']['rendered']}")
        print(f"    전화:{m.get('course_phone','')!r}  "
              f"요금:{m.get('course_fee','')!r}  "
              f"시간:{m.get('course_hours','')!r}")

    if seo_plugin == 'unknown':
        print('\n[중단] SEO 플러그인 미감지로 noindex 적용 불가.')
        print('  WordPress 관리자 → 설치된 플러그인을 확인해주세요.')
        return

    print(f'\n[4단계] noindex 적용 중... ({seo_plugin})')
    print('-' * 60)

    success = fail = 0
    for i, post in enumerate(thin_posts, 1):
        ok = apply_noindex(post['id'], seo_plugin)
        if ok:
            success += 1
        else:
            fail += 1
            print(f"  ❌ 실패 [{post['id']}] {post['title']['rendered']}")

        if i % 50 == 0 or i == len(thin_posts):
            print(f'  진행: {i}/{len(thin_posts)} (성공 {success} / 실패 {fail})')

        time.sleep(0.2)

    print()
    print('=' * 60)
    print(f'✅ 완료: noindex 적용 {success}개 | 실패 {fail}개')
    print('=' * 60)


if __name__ == '__main__':
    main()
