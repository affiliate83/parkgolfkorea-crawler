import os
import sys
import io
import re
import hashlib
import sqlite3
import logging
import datetime
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from newspaper import Article
import anthropic
from dotenv import load_dotenv

# Windows 콘솔 한글 깨짐 방지
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

DB_PATH = Path(__file__).parent / 'dedup.db'
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
logger = logging.getLogger('parkgolf')


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


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def extract_article_body(url: str) -> str:
    """실제 기사 URL에서 본문 추출. newspaper4k → BeautifulSoup 순서로 시도."""
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


def rewrite_with_claude(title: str, body: str, content_type: str = 'news') -> str:
    """Claude API로 기사 본문을 재구성하여 독창적인 콘텐츠 생성"""
    if not ANTHROPIC_API_KEY:
        return body

    if content_type == 'event':
        prompt = f"""다음 파크골프 대회/이벤트 관련 기사를 파크골프 코리아 사이트 독자를 위해 재구성해주세요.

규칙:
- 원문의 핵심 정보(대회명, 일시, 장소, 참가 방법 등)는 반드시 유지하되, 문장과 표현은 새롭게 작성
- 도입부에 파크골프 동호인을 위한 짧은 참여 독려 문장 추가
- 대회 정보를 단락 2~4개로 나눠 가독성 있게 구성
- HTML <p> 태그로 각 단락 감싸기
- 마지막 단락에 참가 독려 코멘트 추가
- 출력은 HTML <p> 태그만, 코드블록(```)이나 다른 설명 없이 순수 HTML만 출력

기사 제목: {title}

기사 본문:
{body[:3000]}"""
    else:
        prompt = f"""다음 파크골프 관련 뉴스 기사를 파크골프 코리아 사이트 독자를 위해 재구성해주세요.

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

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        rewritten = message.content[0].text.strip()
        rewritten = re.sub(r'^```[a-z]*\n?', '', rewritten)
        rewritten = re.sub(r'\n?```$', '', rewritten)
        rewritten = rewritten.strip()
        logger.info(f"  [Claude 재구성 완료] {len(rewritten)}자")
        return rewritten
    except Exception as e:
        logger.warning(f"  [Claude 재구성 실패, 원문 사용] {e}")
        return body
