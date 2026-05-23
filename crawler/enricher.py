"""파크골프장 AI 콘텐츠 풍부화 모듈 (Claude Haiku)"""
import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

# wptexturize 백틱 변환 + 리터럴 코드펜스 이중 제거
_FENCE_RE = re.compile(r'```[^\n`]*\n?|&#8220;`[a-z]*\s*', re.IGNORECASE)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def enrich_course(data: dict) -> str:
    """파크골프장 정보를 바탕으로 FAQ 및 추가 콘텐츠 생성. 실패 시 빈 문자열 반환."""
    client = _get_client()
    if client is None:
        return ''

    name     = data.get('name', '해당 파크골프장')
    address  = data.get('address', '')
    phone    = data.get('phone', '')
    hours    = data.get('hours', '')
    fee      = data.get('fee', '')
    region   = data.get('region', '')
    holes    = data.get('holes', '')

    # 알려진 정보만 포함
    known = []
    if address:
        known.append(f"주소: {address}")
    if phone:
        known.append(f"전화: {phone}")
    if hours:
        known.append(f"운영시간: {hours}")
    if fee:
        known.append(f"이용요금: {fee}")
    if holes:
        known.append(f"홀 수: {holes}")
    if region:
        known.append(f"지역: {region}")
    known_text = '\n'.join(known) if known else '정보 없음'

    prompt = f"""파크골프장 정보 사이트에 게재할 보충 콘텐츠를 HTML로 작성해주세요.

골프장명: {name}
{known_text}

아래 섹션을 순서대로 HTML로만 출력하세요 (다른 텍스트 없이):

<h2>{name} 이용 안내</h2>
(이 파크골프장에 대한 간략한 소개 2~3문장. 위치, 특징, 추천 대상 포함. <p> 태그 사용)

<h2>파크골프 초보자 팁</h2>
(파크골프를 처음 방문하는 사람을 위한 실용적인 팁 3~4가지. <ul><li> 태그 사용)

<h2>자주 묻는 질문</h2>
<div class='faq-item'><h3 class='faq-q'>Q. 주차가 가능한가요?</h3><p class='faq-a'>A. 대부분의 파크골프장은 무료 주차장을 운영합니다. 정확한 주차 가능 여부는 방문 전 {phone if phone else '해당 시설'}에 문의하시기 바랍니다.</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 장비를 빌릴 수 있나요?</h3><p class='faq-a'>A. (파크골프 장비 대여 관련 일반적인 안내)</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 예약이 필요한가요?</h3><p class='faq-a'>A. (예약 관련 일반적인 안내)</p></div>
<div class='faq-item'><h3 class='faq-q'>Q. 초보자도 이용할 수 있나요?</h3><p class='faq-a'>A. (초보자 이용 관련 안내)</p></div>

규칙:
- HTML 속성은 반드시 작은따옴표 사용 (큰따옴표 금지)
- 코드 펜스(```) 절대 사용 금지
- 마크다운 문법 사용 금지
- 쉽고 친근한 말투
- Q/A 내용은 일반적인 파크골프장 정보를 바탕으로 실용적으로 작성"""

    try:
        msg = _get_client().messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1800,
            messages=[{'role': 'user', 'content': prompt}],
        )
        result = _FENCE_RE.sub('', msg.content[0].text).strip()
        return result
    except Exception as e:
        print(f"  [enricher] API 오류: {e}")
        return ''
