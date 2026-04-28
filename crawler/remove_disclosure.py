"""
기존 뉴스/이벤트 포스트에서 '자동 수집 및 재가공' 문구 일괄 제거
"""
import sys
import os
import re
import base64
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

WP_URL     = os.getenv("WP_URL")
WP_USER    = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(
        f"{WP_USER}:{WP_APP_PASS}".encode()
    ).decode(),
    "Content-Type": "application/json"
}

DISCLOSURE_PATTERN = re.compile(
    r'<hr\s*/?>[\s\S]*?자동 수집 및 재가공[\s\S]*?</p>',
    re.IGNORECASE
)

def get_all_posts(post_type):
    posts = []
    page = 1
    while True:
        res = requests.get(
            f"{WP_URL}/wp-json/wp/v2/{post_type}",
            headers=AUTH_HEADER,
            params={"per_page": 100, "page": page, "status": "publish"},
            timeout=15
        )
        if res.status_code != 200:
            break
        data = res.json()
        if not data:
            break
        posts.extend(data)
        page += 1
    return posts

def update_post(post_type, post_id, new_content):
    res = requests.post(
        f"{WP_URL}/wp-json/wp/v2/{post_type}/{post_id}",
        headers=AUTH_HEADER,
        json={"content": new_content},
        timeout=20
    )
    return res.status_code in [200, 201]

def main():
    print("=" * 60)
    print("🧹 '자동 수집 및 재가공' 문구 일괄 제거")
    print("=" * 60)

    total_fixed = 0

    for post_type in ["posts", "parkgolf_event"]:
        print(f"\n📂 {post_type} 로딩 중...")
        posts = get_all_posts(post_type)
        print(f"   총 {len(posts)}개")

        for post in posts:
            content = post["content"]["rendered"]
            if "자동 수집 및 재가공" not in content:
                continue

            new_content = DISCLOSURE_PATTERN.sub("", content)
            # <hr /> 단독으로 남은 것도 제거
            new_content = re.sub(r'<hr\s*/?>\s*(?=</)', '', new_content)

            title = re.sub(r'<[^>]+>', '', post["title"]["rendered"]).strip()
            if update_post(post_type, post["id"], new_content):
                print(f"  ✅ 제거 완료: {title}")
                total_fixed += 1
            else:
                print(f"  ❌ 실패: {title}")

    print(f"\n🎉 완료: 총 {total_fixed}개 글에서 문구 제거")

if __name__ == "__main__":
    main()
