# ============================================================
# 네이버 지도 크롤러 - 파크골프장 상세 정보 업데이터
# 사용법: python naver_map_updater.py
#
# 설치 필요:
#   pip install playwright
#   playwright install chromium
# ============================================================

import sys
import asyncio
import os
import re
import base64
import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

WP_URL            = os.getenv("WP_URL")
WP_USER           = os.getenv("WP_USER")
WP_APP_PASS       = os.getenv("WP_APP_PASS")
NAVER_CLIENT_ID   = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(
        f"{WP_USER}:{WP_APP_PASS}".encode()
    ).decode(),
    "Content-Type": "application/json"
}

NAVER_LOCAL_HEADER = {
    "X-Naver-Client-Id":     NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

# ============================================================
# WordPress에서 파크골프장 목록 가져오기
# ============================================================
def get_wp_courses():
    """등록된 파크골프장 전체 목록 반환"""
    courses = []
    page = 1
    while True:
        res = requests.get(
            f"{WP_URL}/wp-json/wp/v2/parkgolf_course",
            headers=AUTH_HEADER,
            params={"per_page": 100, "page": page, "status": "publish"},
            timeout=15
        )
        if res.status_code != 200:
            break
        data = res.json()
        if not data:
            break
        for post in data:
            title   = re.sub(r'<[^>]+>', '', post["title"]["rendered"]).strip()
            content = post["content"]["rendered"]
            courses.append({
                "id":      post["id"],
                "title":   title,
                "content": content,
            })
        page += 1
    print(f"✅ WordPress 골프장 {len(courses)}개 로드 완료")
    return courses


def needs_update(content):
    """운영시간 또는 홈페이지가 '현장 문의'/'정보 없음'인 경우 업데이트 필요"""
    return "현장 문의" in content or "정보 없음" in content


# ============================================================
# 네이버 로컬 API - 전화번호 / 주소 (신뢰도 높음)
# ============================================================
def get_naver_local_info(name):
    """네이버 로컬 검색 API로 전화번호·주소 반환"""
    try:
        res = requests.get(
            "https://openapi.naver.com/v1/search/local.json",
            headers=NAVER_LOCAL_HEADER,
            params={"query": name, "display": 1},
            timeout=10
        )
        if res.status_code != 200:
            return {}, {}
        items = res.json().get("items", [])
        if not items:
            return {}, {}
        item = items[0]
        phone   = item.get("telephone", "").strip()
        address = item.get("roadAddress", "") or item.get("address", "")
        address = re.sub(r'<[^>]+>', '', address).strip()
        return phone, address
    except Exception:
        return "", ""


# ============================================================
# 네이버 지도 크롤링 (운영시간 / 요금 / 홈페이지 전용)
# ============================================================
async def get_detail_frame(page):
    """entryIframe 또는 searchIframe 반환 (구/신 네이버 지도 URL 형식 모두 지원)"""
    await page.wait_for_timeout(2000)

    # 신형식: /place/{ID}가 URL에 있으면 searchIframe이 이미 상세 패널
    # (isCorrectAnswer=true로 자동 리다이렉트된 경우)
    if "/place/" in page.url:
        try:
            fl = page.frame_locator("#searchIframe")
            await fl.locator("body").wait_for(timeout=5000)
            return fl
        except Exception:
            pass

    # 구형식: entryIframe
    for frame in page.frames:
        if "entry" in frame.url:
            return frame
    try:
        fl = page.frame_locator("#entryIframe")
        await fl.locator("body").wait_for(timeout=5000)
        return fl
    except Exception:
        pass
    return None


async def get_naver_map_info(page, name):
    """네이버 지도에서 장소명으로 검색 후 상세 정보 반환"""
    info = {"phone": "", "hours": "", "homepage": "", "parking": "", "address": "", "fee": ""}

    # ── 네이버 로컬 API로 전화/주소 먼저 확보 (가장 신뢰도 높음) ──
    api_phone, api_address = get_naver_local_info(name)
    if api_phone:
        info["phone"] = api_phone
    if api_address:
        info["address"] = api_address

    try:
        search_url = f"https://map.naver.com/v5/search/{name}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # ── entryIframe이 바로 열린 경우 (결과 1개) ──────────
        detail_frame = await get_detail_frame(page)

        # ── 결과 목록에서 첫 번째 클릭 필요한 경우 ───────────
        # /place/ URL이면 이미 상세 페이지 → searchIframe이 상세 패널이므로 클릭 불필요
        if not detail_frame and "/place/" in page.url:
            print(f"  ⚠️ 상세 패널 로딩 실패: {name}")
            return info

        if not detail_frame:
            search_fl = page.frame_locator("#searchIframe")
            clicked = False

            # 검색 결과 첫 번째 장소 클릭
            # CSS 모듈 클래스(UEzoS, TYaxT 등)는 배포마다 변경 → 구조 기반 셀렉터 우선
            click_selectors = [
                "a.place_bluelink",        # 네이버 지도 고유 의미론적 클래스
                "ul > li:first-child a",   # 첫 번째 목록 아이템의 링크
                "li:first-child > a",      # li 직계 자식 a
                "li:first-child a",        # li 하위 a
                "[data-nclick] a",         # 네이버 클릭 추적 속성
                "a[data-entry-id]",        # 장소 ID 속성
                "a[class*='name']",        # 이름 관련 클래스
                "a[class*='title']",       # 제목 관련 클래스
                "li.UEzoS a",              # 이전 클래스 호환
                "a.TYaxT", "a._3XamX", ".CHC5F a",
            ]
            for sel in click_selectors:
                if clicked:
                    break
                try:
                    els = search_fl.locator(sel)
                    count = await els.count()
                    for idx in range(min(count, 5)):
                        el = els.nth(idx)
                        href = await el.get_attribute("href", timeout=2000) or ""
                        # 명확한 블로그/SNS 외부 링크만 제외
                        if any(x in href for x in [
                            "blog.naver.com", "post.naver.com", "cafe.naver.com",
                            "youtube.com", "instagram.com", "facebook.com",
                        ]):
                            continue

                        pages_before = len(page.context.pages)
                        await el.click(timeout=4000)
                        await page.wait_for_timeout(2000)

                        # 새 탭이 열렸으면 블로그 링크 → 즉시 닫고 다음 요소 시도
                        if len(page.context.pages) > pages_before:
                            for p in page.context.pages:
                                if p != page:
                                    await p.close()
                            continue

                        # 현재 탭이 외부로 이동했으면 복구 후 다음 요소 시도
                        if "map.naver.com" not in page.url:
                            await page.go_back()
                            await page.wait_for_timeout(2000)
                            continue

                        clicked = True
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue

            if not clicked:
                print(f"  ⚠️ 검색 결과 클릭 실패: {name}")
                return info

            detail_frame = await get_detail_frame(page)

        if not detail_frame:
            print(f"  ⚠️ 상세 패널 없음: {name}")
            return info

        # ── 홈 탭 강제 클릭 (사진/소식 탭에 착지한 경우 대비) ─
        # ⚠️ :has-text('홈') 사용 금지 → "홈페이지" 링크까지 매칭되어 블로그가 열림
        # get_by_text(exact=True) 또는 role=tab 으로 정확히 탭만 클릭
        try:
            clicked_tab = False
            # role=tab 으로 정확한 탭 찾기
            tab_el = detail_frame.get_by_role("tab", name="홈")
            if await tab_el.count() > 0:
                await tab_el.first.click(timeout=2000)
                clicked_tab = True
            if not clicked_tab:
                # exact=True 로 텍스트가 정확히 "홈"인 요소만
                tab_el2 = detail_frame.get_by_text("홈", exact=True)
                if await tab_el2.count() > 0:
                    await tab_el2.first.click(timeout=2000)
                    clicked_tab = True
            if clicked_tab:
                await page.wait_for_timeout(1500)
                # 탭 클릭이 새 탭을 열었으면 즉시 닫기
                for p in page.context.pages:
                    if p != page:
                        await p.close()
        except Exception:
            pass

        # ── 전화번호: tel: 링크 우선 ────────────────────────
        try:
            el = detail_frame.locator("a[href^='tel:']").first
            href = await el.get_attribute("href", timeout=3000)
            if href:
                info["phone"] = href.replace("tel:", "").strip()
        except Exception:
            pass

        # 전화번호 버튼 클릭 후 재시도 (클릭해야 번호 노출되는 경우)
        if not info["phone"]:
            try:
                for btn_sel in ["a:has-text('전화')", "button:has-text('전화')", "[class*='phone']"]:
                    try:
                        await detail_frame.locator(btn_sel).first.click(timeout=2000)
                        await page.wait_for_timeout(1000)
                        el = detail_frame.locator("a[href^='tel:']").first
                        href = await el.get_attribute("href", timeout=2000)
                        if href:
                            info["phone"] = href.replace("tel:", "").strip()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        # ── 전체 텍스트에서 정보 추출 ─────────────────────────
        try:
            body_text = await detail_frame.locator("body").inner_text(timeout=6000)

            # 전화번호 보조: API 실패 시 텍스트 패턴으로 보완
            if not info["phone"]:
                phone_m = re.search(r'(\d{2,4}-\d{3,4}-\d{4})', body_text)
                if phone_m:
                    info["phone"] = phone_m.group(1)

            # 주소 보조: API 실패 시 텍스트에서 추출 (시/군/구 + 읍/면/동/로/길 필수)
            if not info["address"]:
                addr_m = re.search(
                    r'((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[^\n]*?(?:시|군|구)[^\n]*?(?:읍|면|동|로|길)[^\n]{0,20})',
                    body_text
                )
                if addr_m:
                    info["address"] = addr_m.group(1).strip()

            # 운영시간
            hours_patterns = [
                r'(매일\s*[\d:~\s]+)',
                r'(평일\s*[\d:~\s]+)',
                r'(영업\s*시간[^\n]{0,50})',
                r'([\d]{1,2}:[\d]{2}\s*[-~]\s*[\d]{1,2}:[\d]{2})',
                r'(\d{1,2}:\d{2}에\s*영업\s*시작)',  # "10:00에 영업 시작" 형식
                r'(24시간\s*영업)',
                r'(영업\s*중[^\n]{0,30})',
            ]
            for pattern in hours_patterns:
                m = re.search(pattern, body_text)
                if m:
                    info["hours"] = m.group(1).strip()
                    break

            # 이용요금: 금액 패턴 추출
            if not info.get("fee"):
                fee_m = re.search(r'(\d{1,3},?\d{3}원)', body_text)
                if fee_m:
                    info["fee"] = fee_m.group(1)

            # 주차
            if "주차" in body_text:
                m = re.search(r'(주차[^\n]{0,40})', body_text)
                if m:
                    info["parking"] = m.group(1).strip()

        except Exception:
            pass

        # ── 전화번호 못 찾은 경우 "정보" 탭 fallback ─────────
        if not info["phone"]:
            try:
                tab_info = detail_frame.get_by_role("tab", name="정보")
                if await tab_info.count() > 0:
                    await tab_info.first.click(timeout=2000)
                    await page.wait_for_timeout(1500)
                    info_text = await detail_frame.locator("body").inner_text(timeout=5000)
                    phone_m = re.search(r'(\d{2,4}-\d{3,4}-\d{4})', info_text)
                    if phone_m:
                        info["phone"] = phone_m.group(1)
                    # 정보 탭 확인 후 홈 탭으로 복귀
                    tab_home = detail_frame.get_by_role("tab", name="홈")
                    if await tab_home.count() > 0:
                        await tab_home.first.click(timeout=2000)
                        await page.wait_for_timeout(1000)
            except Exception:
                pass

        # ── 홈페이지 링크 ─────────────────────────────────────
        # blog.naver.com은 허용 (공식 블로그 홈페이지), map.naver.com만 제외
        hp_selectors = [
            "a[href^='http']:not([href*='map.naver'])",
            "a.place_bluelink[href^='http']",
        ]
        for sel in hp_selectors:
            try:
                els = detail_frame.locator(sel)
                count = await els.count()
                for idx in range(min(count, 5)):
                    href = await els.nth(idx).get_attribute("href", timeout=2000)
                    if not href or not href.startswith("http"):
                        continue
                    if "map.naver.com" in href or "place.naver.com" in href:
                        continue
                    info["homepage"] = href.strip()
                    break
                if info["homepage"]:
                    break
            except Exception:
                continue

        print(f"  📋 전화={info['phone'] or '없음'} | 주소={info['address'][:15] if info['address'] else '없음'} | 운영={info['hours'][:20] if info['hours'] else '없음'}")

    except Exception as e:
        print(f"  ❌ 오류: {name} — {e}")

    return info


# ============================================================
# WordPress 포스트 콘텐츠 업데이트
# ============================================================
def build_updated_content(title, old_content, info):
    """기존 콘텐츠에서 주소 추출 후 새 정보로 테이블 재생성"""

    # 주소: 네이버 지도 우선, 없으면 기존 콘텐츠에서 추출
    naver_address = info.get("address", "")
    addr_match = re.search(r'📍 주소</th><td>(.*?)</td>', old_content)
    old_address = addr_match.group(1).strip() if addr_match else "정보 없음"
    address = naver_address if naver_address else old_address

    # 기존 전화번호 유지 (새 정보가 없으면)
    phone_match = re.search(r'📞 전화</th><td>(.*?)</td>', old_content)
    old_phone = phone_match.group(1).strip() if phone_match else ""

    # 기존 분류 유지
    cat_match = re.search(r'🏷️ 분류</th><td>(.*?)</td>', old_content)
    category = cat_match.group(1).strip() if cat_match else "파크골프장"

    # 기존 홈페이지 유지 (새 정보가 없으면)
    hp_match = re.search(r'🌐 홈페이지</th><td>(.*?)</td>', old_content)
    old_hp = hp_match.group(1).strip() if hp_match else ""

    # 최종값 결정 (새 정보 우선, 없으면 기존값)
    final_phone    = info.get("phone") or old_phone or "정보 없음"
    final_hours    = info.get("hours") or "현장 문의"
    final_fee      = info.get("fee") or "현장 문의"
    final_parking  = info.get("parking") or "현장 문의"
    final_homepage = info.get("homepage") or (old_hp if old_hp and "정보 없음" not in old_hp else "")

    if final_homepage:
        hp_cell = f'<a href="{final_homepage}" target="_blank" rel="noopener">{final_homepage}</a>'
    else:
        hp_cell = "정보 없음"

    content = f"""<div class="course-intro">
<p><strong>{title}</strong>은(는) {address}에 위치한 파크골프장입니다.</p>
<p>정확한 운영시간 및 요금은 아래 연락처로 문의하시거나 현장에서 확인하시기 바랍니다.</p>
</div>

<div class="course-info-table">
<table class="wp-block-table">
<thead><tr><th>항목</th><th>내용</th></tr></thead>
<tbody>
<tr><th>📍 주소</th><td>{address}</td></tr>
<tr><th>📞 전화</th><td>{final_phone}</td></tr>
<tr><th>🏷️ 분류</th><td>{category}</td></tr>
<tr><th>💰 이용요금</th><td>{final_fee}</td></tr>
<tr><th>🕐 운영시간</th><td>{final_hours}</td></tr>
<tr><th>🚗 주차</th><td>{final_parking}</td></tr>
<tr><th>🌐 홈페이지</th><td>{hp_cell}</td></tr>
</tbody>
</table>
</div>

<p style="font-size:13px;color:#888;margin-top:16px;">※ 위 정보는 네이버 지도 기준이며, 실제와 다를 수 있습니다. 방문 전 반드시 전화로 확인하세요.</p>"""

    return content


def update_wp_post(post_id, new_content, meta=None):
    """WordPress 포스트 콘텐츠 + 메타 필드 업데이트 (최대 3회 재시도)"""
    import time
    payload = {"content": new_content}
    if meta:
        payload["meta"] = meta
    for attempt in range(3):
        try:
            res = requests.post(
                f"{WP_URL}/wp-json/wp/v2/parkgolf_course/{post_id}",
                headers=AUTH_HEADER,
                json=payload,
                timeout=30
            )
            return res.status_code in [200, 201]
        except Exception as e:
            if attempt < 2:
                print(f"  ⚠️ 연결 오류, {attempt+1}회 재시도 중... ({e})")
                time.sleep(5)
            else:
                print(f"  ❌ 3회 재시도 실패: {e}")
                return False


# ============================================================
# 메인 실행
# ============================================================
async def main():
    print("=" * 60)
    print("🗺️  네이버 지도 → WordPress 파크골프장 정보 업데이터")
    print("=" * 60)

    # WordPress 연결 확인
    test = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", headers=AUTH_HEADER, timeout=10)
    if test.status_code != 200:
        print(f"❌ WordPress 연결 실패: {test.status_code}")
        return
    print(f"✅ WordPress 연결 성공: {test.json().get('name', '')}\n")

    # 골프장 목록 가져오기
    courses = get_wp_courses()
    to_update = [c for c in courses if needs_update(c["content"])]
    print(f"📋 업데이트 필요: {len(to_update)}개 / 전체 {len(courses)}개\n")

    if not to_update:
        print("✅ 모든 골프장 정보가 이미 채워져 있습니다.")
        return

    success = skip = fail = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,  # 디버깅용 True로 바꾸면 백그라운드 실행
            args=["--lang=ko-KR"]
        )
        context = await browser.new_context(
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        total = len(to_update)
        for i, course in enumerate(to_update, 1):
            # 이전 코스 처리 중 열린 잔여 탭 정리
            for p in context.pages:
                if p != page:
                    await p.close()

            print(f"\n[{i}/{total}] 🔍 {course['title']}")

            info = await get_naver_map_info(page, course["title"])

            # 유효한 정보가 하나라도 있으면 업데이트
            has_new_info = any([
                info.get("phone"),
                info.get("hours"),
                info.get("homepage"),
                info.get("parking"),
                info.get("address"),  # 주소만 찾아도 업데이트
            ])

            if not has_new_info:
                print(f"  ⏭️ 네이버 지도에 정보 없음, 스킵")
                skip += 1
            else:
                new_content = build_updated_content(
                    course["title"], course["content"], info
                )
                # 메타 필드도 함께 업데이트
                meta = {}
                if info.get("phone"):
                    meta["course_phone"] = info["phone"]
                if info.get("hours"):
                    meta["course_hours"] = info["hours"]
                if info.get("parking"):
                    meta["course_parking"] = info["parking"]
                if info.get("address"):
                    meta["course_address"] = info["address"]
                if info.get("fee"):
                    meta["course_fee"] = info["fee"]

                if update_wp_post(course["id"], new_content, meta or None):
                    print(f"  ✅ 업데이트 완료: {course['title']}")
                    success += 1
                else:
                    print(f"  ❌ WordPress 업데이트 실패: {course['title']}")
                    fail += 1

            # 네이버 봇 차단 방지 딜레이
            await page.wait_for_timeout(4000)

        await browser.close()

    print("\n" + "=" * 60)
    print(f"🎉 완료!")
    print(f"   ✅ 업데이트 성공: {success}개")
    print(f"   ⏭️ 정보 없어 스킵: {skip}개")
    print(f"   ❌ 실패: {fail}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
