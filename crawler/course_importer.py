# ============================================================
# 파크골프장 정보 일괄 수집기 (네이버 지역검색 API)
# 사용법: python course_importer.py
#
# ※ Naver Local API 제공 정보
#    - 제공: 장소명, 주소, 전화번호, 홈페이지, 분류
#    - 미제공: 운영시간, 이용요금, 주차 → "현장 문의" 표시
# ============================================================

import os
import re
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
WP_URL              = os.getenv("WP_URL")
WP_USER             = os.getenv("WP_USER")
WP_APP_PASS         = os.getenv("WP_APP_PASS")

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(
        f"{WP_USER}:{WP_APP_PASS}".encode()
    ).decode(),
    "Content-Type": "application/json"
}

# ============================================================
# 검색 쿼리 목록 (지역별 세분화)
# ============================================================
SEARCH_QUERIES = [
    # ── 서울 ─────────────────────────────────────────────────
    "서울 강서구 파크골프장", "서울 광진구 파크골프장", "서울 강동구 파크골프장",
    "서울 노원구 파크골프장", "서울 강북구 파크골프장", "서울 마포구 파크골프장",
    "서울 송파구 파크골프장", "서울 중랑구 파크골프장", "서울 은평구 파크골프장",
    "서울 도봉구 파크골프장", "서울 성동구 파크골프장", "서울 동대문구 파크골프장",
    "서울 성북구 파크골프장", "서울 구로구 파크골프장", "서울 영등포구 파크골프장",
    "여의도 파크골프장", "뚝섬 파크골프장", "난지 파크골프장",
    "고덕 파크골프장", "잠실 파크골프장", "한강공원 파크골프장",

    # ── 경기도 ───────────────────────────────────────────────
    "고양 파크골프장", "수원 파크골프장", "성남 파크골프장",
    "용인 파크골프장", "안양 파크골프장", "부천 파크골프장",
    "의정부 파크골프장", "남양주 파크골프장", "김포 파크골프장",
    "파주 파크골프장", "양평 파크골프장", "가평 파크골프장",
    "이천 파크골프장", "여주 파크골프장", "안성 파크골프장",
    "평택 파크골프장", "화성 파크골프장", "시흥 파크골프장",
    "하남 파크골프장", "구리 파크골프장", "포천 파크골프장",
    "양주 파크골프장", "오산 파크골프장", "안산 파크골프장",

    # ── 인천 ─────────────────────────────────────────────────
    "인천 파크골프장", "인천 계양구 파크골프장", "인천 서구 파크골프장",
    "인천 부평구 파크골프장", "인천 강화 파크골프장", "송도 파크골프장",

    # ── 부산 ─────────────────────────────────────────────────
    "부산 강서구 파크골프장", "부산 금정구 파크골프장", "부산 해운대구 파크골프장",
    "낙동강 파크골프장", "을숙도 파크골프장", "부산 북구 파크골프장",
    "에코델타시티 파크골프장",

    # ── 경남 ─────────────────────────────────────────────────
    "창원 파크골프장", "양산 파크골프장", "진주 파크골프장",
    "거제 파크골프장", "통영 파크골프장", "밀양 파크골프장",
    "김해 파크골프장", "함안 파크골프장", "창녕 파크골프장",

    # ── 대구 ─────────────────────────────────────────────────
    "대구 달성군 파크골프장", "대구 수성구 파크골프장", "대구 동구 파크골프장",
    "대구 북구 파크골프장", "대구 달서구 파크골프장", "금호강 파크골프장",

    # ── 경북 ─────────────────────────────────────────────────
    "경주 파크골프장", "포항 파크골프장", "안동 파크골프장",
    "구미 파크골프장", "영주 파크골프장", "문경 파크골프장",
    "김천 파크골프장", "상주 파크골프장", "칠곡 파크골프장",

    # ── 광주/전남 ─────────────────────────────────────────────
    "광주 파크골프장", "순천 파크골프장", "여수 파크골프장",
    "나주 파크골프장", "목포 파크골프장", "담양 파크골프장",
    "영산강 파크골프장",

    # ── 전북 ─────────────────────────────────────────────────
    "전주 파크골프장", "익산 파크골프장", "군산 파크골프장",
    "정읍 파크골프장", "남원 파크골프장", "완주 파크골프장",

    # ── 대전/충남 ─────────────────────────────────────────────
    "대전 파크골프장", "천안 파크골프장", "아산 파크골프장",
    "공주 파크골프장", "서산 파크골프장", "금강 파크골프장",

    # ── 충북 ─────────────────────────────────────────────────
    "청주 파크골프장", "충주 파크골프장", "제천 파크골프장",
    "음성 파크골프장", "진천 파크골프장",

    # ── 강원 ─────────────────────────────────────────────────
    "춘천 파크골프장", "원주 파크골프장", "강릉 파크골프장",
    "홍천 파크골프장", "속초 파크골프장", "철원 파크골프장",
    "평창 파크골프장", "영월 파크골프장",

    # ── 제주 ─────────────────────────────────────────────────
    "제주시 파크골프장", "서귀포 파크골프장",
    "제주 애월 파크골프장", "성산 파크골프장",

    # ── 울산/세종 ─────────────────────────────────────────────
    "울산 파크골프장", "태화강 파크골프장", "세종시 파크골프장",
]

# ============================================================
# 지역 슬러그 매핑
# ============================================================
REGION_SLUG_MAP = [
    (["서울", "여의도", "뚝섬", "난지", "고덕", "잠실", "한강"], "seoul"),
    (["고양", "수원", "성남", "용인", "안양", "부천", "의정부", "남양주",
      "김포", "파주", "양평", "가평", "이천", "여주", "안성", "평택",
      "화성", "시흥", "하남", "구리", "포천", "양주", "경기",
      "오산", "안산", "송도", "분당", "일산", "동탄"], "seoul"),
    (["인천"], "seoul"),
    (["부산", "낙동강", "을숙도", "에코델타"], "busan"),
    (["창원", "양산", "진주", "거제", "통영", "밀양", "김해", "사천",
      "함안", "창녕", "경남"], "busan"),
    (["대구", "달성", "수성", "금호강"], "daegu"),
    (["경주", "포항", "안동", "구미", "영주", "문경", "김천", "상주",
      "칠곡", "경북"], "daegu"),
    (["광주", "순천", "여수", "나주", "목포", "담양", "영산강", "전남"], "gwangju"),
    (["전주", "익산", "군산", "정읍", "남원", "완주", "전북"], "gwangju"),
    (["대전", "천안", "아산", "공주", "서산", "금강", "충남"], "daejeon"),
    (["청주", "충주", "제천", "음성", "진천", "충북"], "daejeon"),
    (["춘천", "원주", "강릉", "홍천", "속초", "철원", "평창", "영월", "강원"], "gangwon"),
    (["제주", "서귀포", "애월", "성산"], "jeju"),
    (["울산", "태화강"], "busan"),
    (["세종"], "daejeon"),
]

REGION_MAP = {}


def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()


def get_region_slug(text):
    for keywords, slug in REGION_SLUG_MAP:
        for kw in keywords:
            if kw in text:
                return slug
    return "seoul"


def search_naver(query):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": query, "display": 5, "sort": "comment"}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            return res.json().get("items", [])
        else:
            print(f"  ⚠️ 네이버 API 오류: {res.status_code}")
            return []
    except Exception as e:
        print(f"  ❌ 검색 오류: {e}")
        return []


def get_region_ids():
    url = f"{WP_URL}/wp-json/wp/v2/region?per_page=100"
    res = requests.get(url, headers=AUTH_HEADER, timeout=10)
    if res.status_code == 200:
        for term in res.json():
            REGION_MAP[term["slug"]] = term["id"]
        print(f"✅ 지역 ID 로드 완료: {list(REGION_MAP.keys())}")
    else:
        print(f"❌ 지역 로드 실패: {res.status_code}")


def get_existing_titles():
    existing = set()
    page = 1
    while True:
        url = f"{WP_URL}/wp-json/wp/v2/parkgolf_course?per_page=100&page={page}&status=publish"
        res = requests.get(url, headers=AUTH_HEADER, timeout=10)
        if res.status_code != 200:
            break
        data = res.json()
        if not data:
            break
        for post in data:
            existing.add(clean_html(post["title"]["rendered"]))
        page += 1
    print(f"✅ 기존 등록 수: {len(existing)}개")
    return existing


def post_to_wp(name, address, road_address, phone, region_slug, category, homepage=""):
    region_id = REGION_MAP.get(region_slug)
    final_address = road_address if road_address else address

    phone_cell    = phone    if phone    else '정보 없음'
    homepage_cell = f'<a href="{homepage}" target="_blank" rel="noopener">{homepage}</a>' if homepage else '정보 없음'

    content = f"""<div class="course-intro">
<p><strong>{name}</strong>은(는) {final_address}에 위치한 파크골프장입니다.</p>
<p>정확한 운영시간 및 요금은 아래 연락처로 문의하시거나 현장에서 확인하시기 바랍니다.</p>
</div>

<div class="course-info-table">
<table class="wp-block-table">
<thead><tr><th>항목</th><th>내용</th></tr></thead>
<tbody>
<tr><th>📍 주소</th><td>{final_address if final_address else '정보 없음'}</td></tr>
<tr><th>📞 전화</th><td>{phone_cell}</td></tr>
<tr><th>🏷️ 분류</th><td>{category if category else '파크골프장'}</td></tr>
<tr><th>💰 이용요금</th><td>현장 문의</td></tr>
<tr><th>🕐 운영시간</th><td>현장 문의</td></tr>
<tr><th>🚗 주차</th><td>현장 문의</td></tr>
<tr><th>🌐 홈페이지</th><td>{homepage_cell}</td></tr>
</tbody>
</table>
</div>

<p style="font-size:13px;color:#888;margin-top:16px;">※ 위 정보는 네이버 지도 기준이며, 실제와 다를 수 있습니다. 방문 전 반드시 전화로 확인하세요.</p>"""

    payload = {
        "title": name,
        "content": content,
        "status": "publish",
        "meta": {
            "course_address":  final_address or "",
            "course_phone":    phone or "",
            "course_homepage": homepage or "",
        }
    }
    if region_id:
        payload["region"] = [region_id]

    res = requests.post(
        f"{WP_URL}/wp-json/wp/v2/parkgolf_course",
        headers=AUTH_HEADER,
        json=payload,
        timeout=15
    )
    return res.status_code in [200, 201]


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🏌️  파크골프장 정보 수집기 (네이버 지역검색 API)")
    print("=" * 60)

    test = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", headers=AUTH_HEADER, timeout=10)
    if test.status_code != 200:
        print(f"❌ WordPress 연결 실패: {test.status_code}")
        exit()
    print(f"✅ WordPress 연결 성공: {test.json().get('name', '')}")

    get_region_ids()
    existing = get_existing_titles()

    success = skip = fail = 0
    seen = set()

    total = len(SEARCH_QUERIES)
    for qi, query in enumerate(SEARCH_QUERIES, 1):
        print(f"\n[{qi}/{total}] 🔍 검색: {query}")
        items = search_naver(query)

        if not items:
            print("  결과 없음")
            time.sleep(0.3)
            continue

        for item in items:
            name         = clean_html(item.get("title", ""))
            address      = item.get("address", "")
            road_address = item.get("roadAddress", "")
            phone        = item.get("telephone", "")
            category     = item.get("category", "")
            homepage     = item.get("link", "")

            combined = name + category

            if "파크골프" not in combined:
                continue

            exclude_keywords = [
                "골프채", "용품", "샵", "shop", "판매", "제작", "쇼핑",
                "스토어", "연습장", "아카데미", "레슨", "학원",
                "식당", "카페", "펜션", "숙박", "호텔",
                "병원", "의원", "약국", "마트", "제조", "수입", "총판",
            ]
            if any(kw in combined for kw in exclude_keywords):
                print(f"  🚫 제외: {name} ({category})")
                continue

            allow_categories = [
                "스포츠시설", "골프장", "파크골프", "체육시설",
                "공원", "레저", "운동시설", "스포츠센터", "체육공원", "생활체육",
            ]
            if category and not any(kw in category for kw in allow_categories):
                if "파크골프장" not in name and "파크골프코스" not in name:
                    print(f"  ⚠️ 카테고리 불일치 스킵: {name} ({category})")
                    continue

            if name in existing or name in seen:
                print(f"  ⏭️ 중복: {name}")
                skip += 1
                continue

            seen.add(name)
            region_slug = get_region_slug(address + road_address + name + query)
            print(f"  ➕ 등록: {name} | {road_address or address} | 전화: {phone or '없음'} | 홈페이지: {homepage or '없음'}")

            if post_to_wp(name, address, road_address, phone, region_slug, category, homepage):
                print(f"  ✅ 성공: {name}")
                success += 1
            else:
                print(f"  ❌ 실패: {name}")
                fail += 1

            time.sleep(0.5)

        time.sleep(0.3)

    print("\n" + "=" * 60)
    print(f"🎉 수집 완료!")
    print(f"   ✅ 신규 등록: {success}개")
    print(f"   ⏭️ 중복 스킵: {skip}개")
    print(f"   ❌ 실패: {fail}개")
    print(f"   📊 총: 기존 {len(existing)}개 + 신규 {success}개")
    print("=" * 60)
