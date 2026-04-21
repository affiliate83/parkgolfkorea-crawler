import os
import requests
import json
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

WP_URL = os.getenv('WP_URL')
WP_USER = os.getenv('WP_USER')
WP_APP_PASS = os.getenv('WP_APP_PASS')

REST_BASE = {
    'post': 'posts',
    'page': 'pages',
    'parkgolf_event': 'parkgolf_event',
    'parkgolf_course': 'parkgolf_course',
}


def create_wp_post(title, content, post_type='post', category_id=None, event_date_start=''):
    """
    워드프레스에 포스트를 생성합니다.
    - 뉴스: post_type='post', category_id=파크골프뉴스 카테고리ID
    - 대회: post_type='parkgolf_event'
    """
    if not WP_URL or not WP_USER or not WP_APP_PASS:
        print("[오류] .env 파일에 워드프레스 연결 정보가 설정되지 않았습니다.")
        return None

    rest_base = REST_BASE.get(post_type, post_type + 's')
    api_url = f"{WP_URL}/wp-json/wp/v2/{rest_base}"
    auth = (WP_USER, WP_APP_PASS)
    headers = {'Content-Type': 'application/json'}
    
    data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    # 카테고리가 지정된 경우 (뉴스)
    if category_id and post_type == 'post':
        data['categories'] = [category_id]
        
    # 대회/이벤트인 경우 날짜 메타데이터 추가
    if post_type == 'parkgolf_event' and event_date_start:
        data['meta'] = {'event_date_start': event_date_start}
    
    try:
        response = requests.post(api_url, auth=auth, headers=headers, data=json.dumps(data))
        if response.status_code == 201:
            post_id = response.json().get('id')
            print(f"[성공] {post_type} 등록 완료! ID: {post_id} | 제목: {title}")
            return post_id
        else:
            print(f"[실패] 상태 코드: {response.status_code}")
            print(f"상세 내용: {response.text}")
            return None
    except Exception as e:
        print(f"[오류] 워드프레스 통신 중 에러 발생: {e}")
        return None
