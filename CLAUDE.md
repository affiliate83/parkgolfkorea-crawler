# 파크골프코리아 프로젝트 가이드

## 프로젝트 개요
전국 파크골프 통합 정보 플랫폼. 워드프레스 기반 웹사이트의 오류 수정, 파이썬 자동 크롤링 시스템 구축, 쿠팡 파트너스 및 구글 애드센스 수익화를 목표로 한다.

- **작업 디렉토리**: E:\projects\parkgolfkkorea
- **사이트**: parkgolfkorea.com (WordPress)
- **담당**: 안티그라비티

## 기술 스택
- CMS: WordPress (PHP, functions.php, 커스텀 포스트 타입)
- 크롤러: Python 3.11+ (requests, BeautifulSoup4, Playwright)
- 연동: WordPress REST API (Application Password 인증)
- 스케줄러: GitHub Actions 또는 Windows Task Scheduler
- DB(크롤러): SQLite (중복 방지용)

## 프로젝트 구조
E:\projects\parkgolfkkorea  crawler/
    main.py
    sources/       - news.py, events.py, courses.py
    poster/        - wordpress.py
    utils/         - dedup.py, logger.py
  .env             - WP 인증 정보 등 (Git 제외 필수)
  .gitignore
  requirements.txt

## 코드 스타일 규칙
- 커밋 메시지는 한글로 작성 (예: feat: 지역별 탭 오류 수정)
- .env 파일은 절대 Git에 커밋하지 말 것
- 크롤러 요청 간격 최소 2~5초 딜레이 유지 (robots.txt 준수)
- WP REST API 인증은 Application Password만 사용 (Basic Auth 플러그인 금지)

## 주요 명령어
- **이 PC에서는 `python` 대신 `py` 명령어 사용** (python은 인식 안 됨)
- pip install -r requirements.txt : 크롤러 의존성 설치
- py crawler/main.py : 크롤러 수동 실행
- wp post list --post_type=parkgolf_event : WP-CLI 이벤트 포스트 확인

## 수익화 전략
- 1단계: 쿠팡 파트너스 (애드센스 승인 전) - 정적 이미지+링크 방식
- 2단계: 구글 애드센스 (콘텐츠 충분 후 신청)

## 앱 빌드 규칙 (E:\projects\parkgolfkkorea-app)
- **빌드 전 반드시 버전 확인**: `grep -E "version|versionCode" app.json app.config.js`
- versionCode는 app.json과 app.config.js **둘 다** 동시에 올려야 함
- versionName(version)과 versionCode 규칙: version "1.0.X" ↔ versionCode X+2 (현재 1.0.11/12)
- 새 네이티브 모듈 추가 시 반드시 새 빌드 필요
- 빌드 명령어: `eas build --platform android --profile production` (앱 폴더에서 실행)
- Play Console 제출: 빌드 완료 후 .aab 다운로드 → 프로덕션 → 새 릴리즈

## 주의사항
- 쿠팡 파트너스 링크는 정적 이미지+a태그 방식으로만 삽입 (iframe 스크립트 방식 사용 금지)
- 자동 포스팅 글에는 반드시 중복 체크 후 업로드
- 구글 애드센스 승인 전까지 쿠팡 파트너스로 수익화 운영

## 커뮤니케이션 규칙
- 명령어를 제공할 때는 반드시 다음을 함께 설명할 것:
  1. 이 명령어가 무엇을 하는지 (목적)
  2. 어디서 실행해야 하는지 (터미널, VS Code, CMD 등)
  3. 실행 후 어떤 결과가 나와야 정상인지