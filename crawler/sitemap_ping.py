import os
import requests
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv('WP_URL', 'https://parkgolfk.com')
SITEMAP_URL = f'{WP_URL}/sitemap.xml'


def ping_naver():
    try:
        res = requests.get(
            'https://searchadvisor.naver.com/site/sitemap',
            params={'url': SITEMAP_URL},
            timeout=10,
        )
        print(f'[네이버] ping 완료 (status: {res.status_code})')
    except Exception as e:
        print(f'[네이버] ping 실패: {e}')


def ping_google():
    try:
        res = requests.get(
            'https://www.google.com/ping',
            params={'sitemap': SITEMAP_URL},
            timeout=10,
        )
        print(f'[구글] ping 완료 (status: {res.status_code})')
    except Exception as e:
        print(f'[구글] ping 실패: {e}')


if __name__ == '__main__':
    print(f'사이트맵 ping 시작: {SITEMAP_URL}')
    ping_naver()
    ping_google()
    print('완료')
