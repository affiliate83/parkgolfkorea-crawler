import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from utils import logger, is_duplicate, strip_html, extract_article_body, rewrite_with_claude

NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')
CATEGORY_NEWS_ID = os.getenv('CATEGORY_NEWS_ID')
CATEGORY_NEWS_ID = int(CATEGORY_NEWS_ID) if CATEGORY_NEWS_ID else None


def scrape() -> list:
    """네이버 뉴스 API로 '파크골프' 최신 기사 수집 후 Claude로 재구성"""
    logger.info("[뉴스 수집] 네이버 뉴스 API '파크골프' 검색 중...")

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.error("[오류] 네이버 API 키가 .env에 설정되지 않았습니다.")
        return []

    params = {'query': '파크골프', 'display': 20, 'sort': 'date'}
    naver_headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
    }

    try:
        response = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers=naver_headers, params=params, timeout=10
        )
        response.raise_for_status()
        items = response.json().get('items', [])
        logger.info(f"  API 응답: {len(items)}건")
    except Exception as e:
        logger.error(f"[오류] 네이버 뉴스 API 호출 실패: {e}")
        return []

    results = []
    for item in items[:5]:
        title = strip_html(item.get('title', ''))
        original_link = item.get('originallink', '')
        naver_link = item.get('link', '')
        desc = strip_html(item.get('description', '내용 없음'))
        link = original_link or naver_link

        if not title or not link:
            continue

        # 제목에 '파크골프'가 포함된 기사만 허용
        if '파크골프' not in title:
            logger.info(f"  [무관 기사 제외] {title[:40]}")
            continue

        if is_duplicate(title, link):
            logger.info(f"  [중복 건너뜀] {title[:40]}")
            continue

        logger.info(f"  [수집] {title[:50]}")

        body_html = extract_article_body(original_link) if original_link else ''
        if not body_html and naver_link:
            body_html = extract_article_body(naver_link)
        if not body_html:
            logger.info("  [본문 추출 실패] API 요약으로 대체")
            body_html = desc

        body_html = rewrite_with_claude(title, body_html, content_type='news')

        content_html = f"""<p>파크골프 관련 최신 뉴스를 전해드립니다.</p>
{body_html}
<p><a href="{original_link or naver_link}" target="_blank" rel="noopener noreferrer">👉 기사 원문 보러가기</a></p>"""

        results.append({
            "title": title,
            "content": content_html,
            "link": link,
            "post_type": "post",
            "category_id": CATEGORY_NEWS_ID,
        })
        time.sleep(2)

    return results
