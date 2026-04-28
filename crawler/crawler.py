import os
import sys
import io
import re
import time
import datetime
import hashlib
import sqlite3
import logging
import requests
import anthropic
from pathlib import Path
from bs4 import BeautifulSoup
from newspaper import Article
from wp_api import create_wp_post
from dotenv import load_dotenv

# Windows 콘솔 한글 깨짐 방지
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

CATEGORY_NEWS_ID = os.getenv('CATEGORY_NEWS_ID')
CATEGORY_NEWS_ID = int(CATEGORY_NEWS_ID) if CATEGORY_NEWS_ID else None
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# 로그 설정: 콘솔 + 날짜별 파일
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"{datetime.date.today().isoformat()}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SQLite 중복 방지
DB_PATH = Path(__file__).parent / 'dedup.db'

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS published (
            hash TEXT PRIMARY KEY,
            title TEXT,
            published_at TEXT
        )
    """)
    conn.commit()
    return conn


def _make_hash(title: str, link: str) -> str:
    return hashlib.md5(f"{title}|{link}".encode()).hexdigest()


def is_duplicate(title: str, link: str) -> bool:
    conn = _get_db()
    row = conn.execute(
        "SELECT 1 FROM published WHERE hash=?", (_make_hash(title, link),)
    ).fetchone()
    conn.close()
    return row is not None


def mark_published(title: str, link: str):
    conn = _get_db()
    conn.execute(
        "INSERT OR IGNORE INTO published (hash, title, published_at) VALUES (?, ?, ?)",
        (_make_hash(title, link), title, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def _extract_article_body(url: str) -> str:
    """실제 기사 URL에서 본문 추출. newspaper4k → BeautifulSoup 순서로 시도."""
    # 1차: newspaper4k
    try:
        art = Article(url, language='ko')
        art.download()
        art.parse()
        if art.text and len(art.text) > 200:
            paragraphs = [f'<p>{p.strip()}</p>' for p in art.text.split('\n') if p.strip()]
            logger.info(f"  [본문 추출 성공 - newspaper4k] {len(art.text)}자")
            return '\n'.join(paragraphs)
    except Exception as e:
        logger.debug(f"  newspaper4k 실패: {e}")

    # 2차: BeautifulSoup 공통 셀렉터
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        selectors = [
            '#newsct_article', '#articleBodyContents', '#articeBody',
            '.article_body', '.news_body', '.article-body',
            '#article-body', '.content_body', '#content-article',
            'article', '.post_content', '#post-content',
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 200:
                for tag in el.select('script, style, figure, iframe, .ad, .advertisement'):
                    tag.decompose()
                paragraphs = [
                    f'<p>{p.get_text(strip=True)}</p>'
                    for p in el.find_all('p')
                    if len(p.get_text(strip=True)) > 20
                ]
                if paragraphs:
                    logger.info(f"  [본문 추출 성공 - BS4 ({sel})] {len(paragraphs)}단락")
                    return '\n'.join(paragraphs)
    except Exception as e:
        logger.debug(f"  BeautifulSoup 실패: {e}")

    return ''


def _rewrite_with_claude(title: str, body: str) -> str:
    """Claude API로 기사 본문을 재구성하여 독창적인 콘텐츠 생성"""
    if not ANTHROPIC_API_KEY:
        return body

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""다음 파크골프 관련 뉴스 기사를 파크골프 코리아 사이트 독자를 위해 재구성해주세요.

규칙:
- 원문의 핵심 정보와 사실은 유지하되, 문장과 표현은 반드시 새롭게 작성
- 도입부에 파크골프 애호가 관점의 짧은 소개 문장 추가
- 단락을 2~4개로 나눠 가독성 있게 구성
- HTML <p> 태그로 각 단락 감싸기
- 마지막 단락에 파크골프 코리아 독자에게 유용한 한 줄 코멘트 추가
- 출력은 HTML <p> 태그만, 코드블록(```)이나 다른 설명 없이 순수 HTML만 출력

기사 제목: {title}

기사 본문:
{body[:3000]}"""
            }]
        )
        rewritten = message.content[0].text.strip()
        # 마크다운 코드블록 제거 (```html ... ``` 형태)
        rewritten = re.sub(r'^```[a-z]*\n?', '', rewritten)
        rewritten = re.sub(r'\n?```$', '', rewritten)
        rewritten = rewritten.strip()
        logger.info(f"  [Claude 재구성 완료] {len(rewritten)}자")
        return rewritten
    except Exception as e:
        logger.warning(f"  [Claude 재구성 실패, 원문 사용] {e}")
        return body


def scrape_naver_news():
    """네이버 뉴스 검색 API로 '파크골프' 최신 기사 수집 + 본문 추출"""
    logger.info("[뉴스 수집] 네이버 뉴스 API '파크골프' 검색 중...")

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.error("[오류] 네이버 API 키가 .env에 설정되지 않았습니다.")
        return []

    api_url = "https://openapi.naver.com/v1/search/news.json"
    params = {'query': '파크골프', 'display': 10, 'sort': 'date'}
    naver_headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
    }

    try:
        response = requests.get(api_url, headers=naver_headers, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get('items', [])
        logger.info(f"  API 응답: {len(items)}건")
    except Exception as e:
        logger.error(f"[오류] 네이버 API 호출 실패: {e}")
        return []

    scraped_news = []
    for item in items[:5]:
        title = _strip_html(item.get('title', ''))
        # originallink: 실제 언론사 기사 URL / link: 네이버 뉴스 URL
        original_link = item.get('originallink', '')
        naver_link = item.get('link', '')
        desc = _strip_html(item.get('description', '내용 없음'))

        link = original_link or naver_link
        if not title or not link:
            continue

        if is_duplicate(title, link):
            logger.info(f"  [중복 건너뜀] {title}")
            continue

        logger.info(f"  [수집] {title[:50]}")

        # 본문 추출 시도 (originallink 우선, 실패 시 naver_link)
        body_html = _extract_article_body(original_link) if original_link else ''
        if not body_html and naver_link:
            body_html = _extract_article_body(naver_link)

        # 본문 추출 실패 시 API 요약으로 대체
        if not body_html:
            logger.info("  [본문 추출 실패] API 요약으로 대체")
            body_html = desc

        # Claude로 재구성
        body_html = _rewrite_with_claude(title, body_html)

        content_html = f"""<p>파크골프 관련 최신 뉴스를 전해드립니다.</p>
{body_html}
<p><a href="{original_link or naver_link}" target="_blank" rel="noopener noreferrer">👉 기사 원문 보러가기</a></p>"""

        scraped_news.append({
            "title": title,
            "content": content_html,
            "link": link,
            "type": "news"
        })

        time.sleep(2)  # 기사 사이트 요청 간격

    return scraped_news


def run_scraper():
    logger.info("=" * 40)
    logger.info("⛳ 파크골프 코리아 - 자동 크롤러 봇 시작")
    logger.info("=" * 40)

    news_data = scrape_naver_news()

    logger.info("[이벤트 수집] 대한파크골프협회 대회 일정 확인 중... (준비 중)")
    events_data = []

    all_data = news_data + events_data
    logger.info(f"[진행] 총 {len(all_data)}개의 새로운 콘텐츠를 발견했습니다.")

    success_count = 0
    for item in all_data:
        logger.info(f" -> 워드프레스 발행 시도 중: {item['title']}")
        post_id = None
        if item['type'] == 'news':
            post_id = create_wp_post(
                title=item['title'],
                content=item['content'],
                post_type='post',
                category_id=CATEGORY_NEWS_ID
            )
        if post_id:
            mark_published(item['title'], item.get('link', ''))
            success_count += 1
        time.sleep(3)  # robots.txt 준수: 요청 간격 최소 2~5초

    logger.info("=" * 40)
    logger.info(f"⛳ 크롤링 완료 — 발행 성공: {success_count}/{len(all_data)}건")
    logger.info("=" * 40)


if __name__ == "__main__":
    run_scraper()
