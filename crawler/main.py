import time
from utils import logger, mark_published
from sources import news, events
from wp_api import create_wp_post


def run():
    logger.info("=" * 40)
    logger.info("⛳ 파크골프 코리아 - 자동 크롤러 봇 시작")
    logger.info("=" * 40)

    all_data = []
    all_data += news.scrape()
    all_data += events.scrape()

    # 뉴스/이벤트 간 동일 링크 중복 제거
    seen_links = set()
    deduped = []
    for item in all_data:
        if item['link'] not in seen_links:
            seen_links.add(item['link'])
            deduped.append(item)
        else:
            logger.info(f"  [교차 중복 제거] {item['title'][:40]}")
    all_data = deduped

    logger.info(f"[진행] 총 {len(all_data)}개의 새로운 콘텐츠를 발견했습니다.")

    success_count = 0
    for item in all_data:
        logger.info(f" -> 발행 시도: [{item['post_type']}] {item['title'][:40]}")
        post_id = create_wp_post(
            title=item['title'],
            content=item['content'],
            post_type=item['post_type'],
            category_id=item.get('category_id'),
        )
        if post_id:
            mark_published(item['title'], item.get('link', ''))
            success_count += 1
        time.sleep(3)

    logger.info("=" * 40)
    logger.info(f"⛳ 크롤링 완료 — 발행 성공: {success_count}/{len(all_data)}건")
    logger.info("=" * 40)


if __name__ == "__main__":
    run()
