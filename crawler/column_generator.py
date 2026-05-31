# -*- coding: utf-8 -*-
"""
파크골프 칼럼 자동 생성 및 WordPress 발행
- 하루 2편씩 자동 생성 (GitHub Actions 스케줄)
- 발행된 주제는 columns_done.txt 에 기록해 중복 방지
"""
import sys, os, re, time, base64, requests, anthropic
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

WP_URL      = os.getenv('WP_URL')
WP_USER     = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

AUTH = (WP_USER, WP_APP_PASS)
DONE_FILE = os.path.join(os.path.dirname(__file__), 'columns_done.txt')
COLUMNS_PER_RUN = 2

# ── 칼럼 주제 목록 ──────────────────────────────────────────────
TOPICS = [
    ("파크골프, 왜 지금 이렇게 인기일까?", "파크골프가 최근 급성장한 이유와 사회적 배경 분석"),
    ("파크골프 입문 전 꼭 알아야 할 것들", "파크골프를 시작하기 전 준비해야 할 마음가짐과 기초 지식"),
    ("파크골프와 일반 골프의 결정적 차이", "파크골프와 골프의 장비, 규칙, 비용, 접근성 비교"),
    ("파크골프가 노년 건강에 좋은 이유", "파크골프의 운동 효과와 고령자 건강 증진 연구 분석"),
    ("파크골프 동호회, 이렇게 즐겨라", "파크골프 동호회 활동의 장점과 좋은 팀 고르는 법"),
    ("파크골프 비용 현실적으로 따져보기", "파크골프 입문부터 정기 라운드까지 실제 비용 분석"),
    ("파크골프 클럽, 비싼 게 정말 좋을까?", "파크골프 클럽 가격과 성능의 상관관계 현실적 분석"),
    ("파크골프 스코어 줄이는 실전 전략", "파크골프 타수를 줄이기 위한 코스 공략 전략과 멘탈 관리"),
    ("파크골프 에티켓, 왜 중요한가", "파크골프장에서 에티켓이 중요한 이유와 실천 방법"),
    ("파크골프 부상 예방법 — 어깨·허리를 지켜라", "파크골프 중 자주 발생하는 부위별 부상 예방 스트레칭"),
    ("파크골프로 만난 사람들 — 사회적 연결의 힘", "파크골프가 만들어주는 인간관계와 커뮤니티의 가치"),
    ("파크골프 날씨별 라운드 전략", "맑은 날, 흐린 날, 바람 부는 날 파크골프 공략법"),
    ("파크골프 초보자 한 달 후기 — 무엇이 달라졌나", "파크골프를 시작한 지 한 달 후 변화와 소감 칼럼"),
    ("파크골프 용품 구매 전 꼭 읽어야 할 글", "파크골프 클럽·공·가방 구매 시 후회 없는 선택 가이드"),
    ("파크골프 대회, 처음 나가보니", "파크골프 대회 첫 참가 경험과 준비 팁 칼럼"),
    ("파크골프 코스 난이도, 어떻게 읽는가", "파크골프 코스 설계와 난이도 요소 분석"),
    ("파크골프와 골프, 둘 다 해본 사람의 솔직한 비교", "두 종목을 경험한 입장에서 본 파크골프의 장단점"),
    ("파크골프 연습장 vs 실전 코스, 차이는?", "파크골프 연습장과 실제 코스의 차이점과 효율적 활용법"),
    ("파크골프 스윙, 혼자 교정하는 법", "파크골프 스윙 자가 교정 방법과 체크리스트"),
    ("파크골프가 가족 여가로 딱인 이유", "파크골프가 세대 통합 가족 여가 활동으로 적합한 이유"),
    ("파크골프 전국 명소 — 꼭 가봐야 할 코스 5곳", "전국 파크골프 명소 코스 특징과 방문 포인트"),
    ("파크골프 실력 정체기, 이렇게 돌파하라", "파크골프 실력 향상이 멈췄을 때 극복하는 방법"),
    ("파크골프, 봄에 시작하기 좋은 이유", "봄 파크골프의 매력과 시즌 준비 방법"),
    ("파크골프 여름 라운드 꿀팁", "무더운 여름 파크골프를 즐기는 방법과 건강 주의사항"),
    ("파크골프 가을, 최고의 시즌을 즐기는 법", "가을 파크골프의 매력과 단풍 속 라운드 즐기는 법"),
    ("파크골프 겨울에도 즐길 수 있다", "겨울 파크골프 준비 방법과 방한 용품 추천"),
    ("파크골프 입문 장비 세트, 이렇게 구성하라", "파크골프 입문자가 처음 구매해야 할 장비 구성 가이드"),
    ("파크골프 공, 브랜드별 특징 비교", "파크골프 공 브랜드별 비거리·내구성·가격 비교 분석"),
    ("파크골프 가방 종류와 선택법", "파크골프 캐디백, 카트백, 보스턴백 종류와 선택 기준"),
    ("파크골프 그라운드 매너 완벽 정리", "파크골프장에서 지켜야 할 그라운드 매너와 그 이유"),
]

# ── 유틸 ────────────────────────────────────────────────────────
def load_done():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_done(title):
    with open(DONE_FILE, 'a', encoding='utf-8') as f:
        f.write(title + '\n')

def get_guide_category_id():
    res = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        auth=AUTH,
        params={'search': '가이드', 'per_page': 10},
        timeout=10
    )
    for cat in res.json():
        if '가이드' in cat.get('name', ''):
            return cat['id']
    return None

def generate_column(title, description):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""파크골프 정보 사이트를 위한 칼럼을 작성해주세요.

제목: {title}
주제: {description}

요구사항:
- 한국어로 작성
- 칼럼 특유의 따뜻하고 공감가는 문체 사용
- 소제목(h2) 4개 이상 포함
- 총 본문 1,500자 이상
- HTML 형식 (WordPress 게시용)
- <h2>, <p>, <ul>, <li>, <strong> 태그 사용
- 광고성 문구, 외부 링크 금지
- HTML body 내용만 출력 (html/head/body 태그 제외)"""

    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=3000,
        messages=[{'role': 'user', 'content': prompt}]
    )
    content = msg.content[0].text
    content = re.sub(r'^```(?:html)?\s*\n?', '', content.strip())
    content = re.sub(r'\n?```\s*$', '', content.strip())
    return content.strip()

def publish(title, content, cat_id):
    data = {'title': title, 'content': content, 'status': 'publish'}
    if cat_id:
        data['categories'] = [cat_id]
    res = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=AUTH,
        json=data,
        timeout=20
    )
    if res.status_code == 201:
        print(f"[OK] 발행 완료: {title} (ID {res.json()['id']})")
        return True
    print(f"[FAIL] {res.status_code} - {res.text[:200]}")
    return False

# ── 메인 ────────────────────────────────────────────────────────
def main():
    done = load_done()
    pending = [(t, d) for t, d in TOPICS if t not in done]

    if not pending:
        print("[INFO] 모든 칼럼 주제가 발행 완료되었습니다.")
        return

    cat_id = get_guide_category_id()
    count = 0

    for title, desc in pending:
        if count >= COLUMNS_PER_RUN:
            break
        print(f"[생성중] {title}")
        try:
            content = generate_column(title, desc)
            if publish(title, content, cat_id):
                save_done(title)
                count += 1
                time.sleep(3)
        except Exception as e:
            print(f"[오류] {title}: {e}")

    print(f"[완료] {count}편 발행")

if __name__ == '__main__':
    main()
