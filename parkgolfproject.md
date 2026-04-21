# ⛳ 파크골프 코리아 (Park Golf Korea) 수정 및 개선 프로젝트 계획서

## 1. 개요
본 문서는 파크골프 코리아 웹사이트의 현재 발생 중인 오류를 수정하고, 향후 자동화된 크롤링 및 콘텐츠 배포 시스템을 구축하여 전국적인 파크골프 통합 정보 플랫폼으로 거듭나기 위한 프로젝트 계획서입니다.

- **작업 디렉토리**: `E:\projects\parkgolfkkorea`
- **작성일**: 2026-04-21
- **담당**: 안티그라비티

---

## 2. 작업 우선순위 매트릭스

| 우선순위 | 항목 | 영향도 | 난이도 | 예상 소요 |
|--------|------|--------|--------|---------|
| 🔴 즉시 | 지역별 탭 오류 수정 | 높음 | 낮음 | 2~4시간 |
| 🔴 즉시 | 대회/이벤트 메뉴 분류 오류 수정 | 높음 | 낮음 | 2~4시간 |
| 🟡 단기 | 크롤러 기본 구조 개발 | 높음 | 중간 | 1~2주 |
| 🟡 단기 | 워드프레스 자동 포스팅 연동 | 높음 | 중간 | 1주 |
| 🟢 중기 | SEO 자동화 스크립트 | 중간 | 중간 | 1~2주 |
| 🟢 중기 | 모니터링 및 알림 시스템 | 중간 | 낮음 | 3~5일 |

---

## 3. 기존 사이트 오류 수정 및 개선 방안

### ① 골프장 정보: 지역별 탭 오류 수정

- **증상**: '전체' 탭에서는 721개의 골프장 정보가 정상적으로 노출되나, 지역별 탭 클릭 시 정보가 없다고 표시되는 현상.
- **원인**: 프론트엔드 자바스크립트에서 워드프레스 REST API 호출 시 `region` 파라미터로 영문 슬러그(예: seoul, busan)를 전달하고 있으나, 기본 워드프레스 API는 slug가 아닌 숫자(Term ID)를 요구하여 오류가 발생.
- **해결 방안**:
  1. `functions.php`에 `rest_parkgolf_course_query` 필터를 추가하여 API가 `region_slug` 파라미터를 통해 텍스트로 검색할 수 있도록 지원.
  2. 프론트엔드 자바스크립트(`assets_js_courses.js` 및 `page-courses.php`)의 API 호출 URL 파라미터를 `region`에서 `region_slug`로 변경.

```php
// functions.php 추가 예시
add_filter('rest_parkgolf_course_query', function($args, $request) {
    if ($slug = $request->get_param('region_slug')) {
        $term = get_term_by('slug', $slug, 'region');
        if ($term) {
            $args['tax_query'] = [[
                'taxonomy' => 'region',
                'field'    => 'term_id',
                'terms'    => $term->term_id,
            ]];
        }
    }
    return $args;
}, 10, 2);
```

- **수정 후 검증**: 17개 광역시도 탭 전체 클릭 테스트 필수

### ③ 뉴스/소식 페이지 — 근본 해결 (page-news.php 템플릿 방식)

**기존 방식의 문제**: `add_rewrite_rule`로 `/news/` → `category_name=파크골프뉴스`로 연결하는 방식은 고유주소 새로고침 없이는 즉시 깨지고, 카테고리 슬러그에 종속되어 불안정.

**근본 해결책**: 워드프레스 **실제 페이지(slug: news) + 전용 템플릿 파일** 방식.

#### 실행 순서

**1) 테마 폴더에 `page-news.php` 파일 업로드**

```php
<?php
/**
 * Template Name: 뉴스 목록
 */
get_header();

$paged = (get_query_var('paged')) ? get_query_var('paged') : 1;

$news_query = new WP_Query([
    'post_type'      => 'post',
    'post_status'    => 'publish',
    'posts_per_page' => 12,
    'paged'          => $paged,
    'orderby'        => 'date',
    'order'          => 'DESC',
]);
?>
<div class="main-content-area">
  <div class="container">
    <div class="archive-hero">
      <h1>뉴스/소식</h1>
      <p class="archive-desc">파크골프 최신 뉴스와 소식을 전해드립니다.</p>
    </div>
    <div class="content-sidebar-wrap">
      <main class="main-content">
        <?php if ($news_query->have_posts()): ?>
          <div class="news-card-grid">
            <?php while ($news_query->have_posts()): $news_query->the_post();
              $cats      = get_the_category();
              $cat_name  = !empty($cats) ? $cats[0]->name : '';
              $cat_color = '#1a6e3c';
              if ($cat_name === '대회')       $cat_color = '#e65c00';
              elseif ($cat_name === '이벤트') $cat_color = '#7b2ff7';
              elseif ($cat_name === '소식')   $cat_color = '#0077cc';
              elseif ($cat_name === '협회')   $cat_color = '#c0392b';
            ?>
            <article class="news-card">
              <a href="<?php the_permalink(); ?>" class="news-card-link">
                <?php if (has_post_thumbnail()): ?>
                  <div class="news-card-thumb"><?php the_post_thumbnail('medium'); ?></div>
                <?php else: ?>
                  <div class="news-card-thumb no-img">⛳</div>
                <?php endif; ?>
                <div class="news-card-body">
                  <?php if ($cat_name): ?>
                    <span class="news-cat-badge" style="background:<?php echo $cat_color; ?>">
                      <?php echo esc_html($cat_name); ?>
                    </span>
                  <?php endif; ?>
                  <h2 class="news-card-title"><?php the_title(); ?></h2>
                  <p class="news-card-excerpt"><?php echo wp_trim_words(get_the_excerpt(), 25, '...'); ?></p>
                  <div class="news-card-meta">
                    <span>📅 <?php echo get_the_date('Y.m.d'); ?></span>
                  </div>
                </div>
              </a>
            </article>
            <?php endwhile; wp_reset_postdata(); ?>
          </div>
          <div class="archive-pagination">
            <?php echo paginate_links([
              'base'      => get_pagenum_link(1) . '%_%',
              'format'    => 'page/%#%/',
              'current'   => $paged,
              'total'     => $news_query->max_num_pages,
              'prev_text' => '◀ 이전',
              'next_text' => '다음 ▶',
            ]); ?>
          </div>
        <?php else: ?>
          <div class="no-posts"><p>⛳ 아직 게시물이 없습니다.</p></div>
        <?php endif; ?>
      </main>
      <?php get_sidebar(); ?>
    </div>
  </div>
</div>
<?php get_footer(); ?>
```

**2) 워드프레스 관리자 — 페이지 생성**
- [페이지] → [새 페이지 추가]
- 제목: `뉴스/소식` / 슬러그: `news`
- 페이지 템플릿: **뉴스 목록** (파일 업로드 후 자동으로 목록에 표시됨)
- 내용: 비워두고 발행

**3) 메뉴 수정**
- [외모] → [메뉴] → 기존 '뉴스/소식' 항목 제거
- [페이지] 탭에서 방금 만든 `뉴스/소식` 페이지 선택 → [메뉴에 추가] → 저장

**4) functions.php에서 기존 rewrite rule 제거**
- `add_rewrite_rule('^news/?$', ...)` 코드가 있다면 삭제
- [설정] → [고유주소] → [변경사항 저장] 한 번 클릭 (캐시 갱신)

#### 이 방식이 안정적인 이유

| 항목 | rewrite rule 방식 | page-news.php 방식 |
|------|----------|----------|
| 안정성 | 고유주소 새로고침 필요, 쉽게 깨짐 | 워드프레스 실제 페이지 = 영구적 |
| 카테고리 의존 | `파크골프뉴스` 슬러그 필수 | 카테고리 무관, 모든 포스트 표시 |
| 페이지네이션 | 작동 보장 안 됨 | 완벽 작동 |
| 자동 포스팅 연동 | 카테고리 지정 필요 | 모든 신규 포스트 자동 노출 |

---

### ② 대회/이벤트 및 뉴스/소식 메뉴 분류 오류 수정

- **증상**: '대회/이벤트' 탭을 누르면 글이 나오지만, 해당 글들은 사실 '뉴스/소식' 카테고리에 속해야 하는 글들임. 워드프레스 관리자 페이지의 '대회/이벤트' 관리 메뉴에는 글이 없는 것이 정상.
- **해결 방안**:
  1. **헤더 및 템플릿 연결 수정**: 현재 '대회/이벤트' 메뉴가 일반 글(Post)을 불러오고 있다면, 이를 커스텀 포스트 타입(`parkgolf_event`)만 불러오도록 쿼리를 수정.
  2. **뉴스/소식 템플릿 분리**: 현재 노출되는 정보성 글들은 온전히 '뉴스/소식' 탭으로 연결하여 사이트의 카테고리 정체성을 확립.
  3. **기존 데이터 일괄 이전**: 잘못 분류된 기존 포스트는 DB 쿼리 또는 WP-CLI로 일괄 재분류.

```bash
# WP-CLI 일괄 재분류 예시
wp post list --post_type=post --category_name=대회이벤트 --format=ids | \
  xargs -I{} wp post update {} --post_type=parkgolf_event
```

---

## 4. 향후 발전 계획: 자동화 콘텐츠 플랫폼

매일 최신 정보를 자동으로 수집하여 제공하는 시스템을 구축하여, 운영 리소스를 최소화하고 사용자 방문을 유도합니다.

### ① 데이터 크롤링(Crawling) 시스템 구축

- **수집 대상**:
  - 전국 신규 파크골프장 정보 (주소, 시설, 이용 요금 등)
  - 파크골프 관련 최신 뉴스 및 기사
  - 각 지역별 대회 공고 및 이벤트 일정

- **개발 스택**:
  - Python 3.11+
  - `requests` + `BeautifulSoup4` (정적 페이지)
  - `Selenium` 또는 `Playwright` (동적 JS 렌더링 페이지)
  - 스케줄러: GitHub Actions (무료, 클라우드) 또는 Windows Task Scheduler (로컬)

- **크롤러 디렉토리 구조**:
```
E:\projects\parkgolfkkorea\
├── crawler/
│   ├── main.py              # 진입점 및 스케줄 관리
│   ├── sources/
│   │   ├── news.py          # 뉴스 크롤러
│   │   ├── events.py        # 대회/이벤트 크롤러
│   │   └── courses.py       # 골프장 정보 크롤러
│   ├── poster/
│   │   └── wordpress.py     # WP REST API 포스팅 모듈
│   ├── utils/
│   │   ├── dedup.py         # 중복 제거 로직
│   │   └── logger.py        # 로깅
│   └── config.py            # 환경변수 및 설정
├── .env                     # API 키, WP 인증 정보 (Git 제외)
├── .gitignore
└── requirements.txt
```

- **주요 크롤링 소스 후보**:
  - 대한파크골프협회 공식 사이트
  - 각 광역시도 파크골프협회 사이트
  - 네이버 뉴스 (파크골프 키워드)
  - 지자체 공공 체육시설 API

### ② 자동 포스팅(Auto-Posting) 연동

- 수집된 데이터를 가공하여 워드프레스 REST API를 통해 매일 지정된 시간에 자동으로 사이트에 업로드합니다.
- **작성자 명의**: 모든 자동 업로드 글은 `파크골프 코리아` 공식 관리자 계정 이름으로 발행.
- **중복 방지**: 제목 + URL 기반 해시값을 SQLite DB에 저장하여 동일 콘텐츠 재업로드 차단.
- **분류 자동화**:
  - 골프장 데이터 → `파크골프장` 커스텀 포스트로 신규 등록
  - 기사 및 관련 동향 → `뉴스/소식` (일반 포스트)
  - 대회 공고 → `대회/이벤트` 커스텀 포스트

```python
# wordpress.py 핵심 구조 예시
import requests, os

WP_URL  = os.environ['WP_URL']       # https://parkgolfkorea.com
WP_USER = os.environ['WP_USER']
WP_PASS = os.environ['WP_APP_PASS']  # WP Application Password 사용

def create_post(title, content, post_type='post', category_id=None):
    res = requests.post(
        f'{WP_URL}/wp-json/wp/v2/{post_type}s',
        auth=(WP_USER, WP_PASS),
        json={
            'title':   title,
            'content': content,
            'status':  'publish',
            'categories': [category_id] if category_id else [],
        }
    )
    res.raise_for_status()
    return res.json()['id']
```

### ③ SEO 및 방문자 트래픽 극대화

- 자동 발행되는 글의 제목과 메타 설명을 검색 엔진에 최적화되도록 스크립트가 자동 가공.
- 롱테일 키워드(예: "2026년 대구 파크골프 대회 일정 및 신청방법")를 제목에 자동 포함.
- Yoast SEO 또는 RankMath REST API 연동으로 메타 태그 자동 설정.
- Open Graph / Twitter Card 이미지 자동 지정 (썸네일 없는 글 방지).

---

## 5. 보안 및 운영 고려사항

### 보안
- **인증**: 워드프레스 Application Password 사용 (Basic Auth 플러그인 의존 금지)
- **비밀 관리**: 모든 API 키, DB 비밀번호, WP 계정 정보는 `.env` 파일에만 보관, Git에 절대 커밋 금지
- **크롤링 윤리**: `robots.txt` 준수, 요청 간격 최소 2~5초 딜레이, User-Agent 명시
- **Rate Limit**: WP REST API에 IP당 요청 제한 플러그인 적용 (외부 공격 차단)

### 에러 처리 및 모니터링
- 크롤러 실패 시 이메일 또는 카카오톡 알림 발송
- 포스팅 성공/실패 로그를 날짜별 파일로 저장 (`logs/YYYY-MM-DD.log`)
- 월 1회 사이트 전체 백업 (워드프레스 DB + 업로드 파일)
- 구글 서치콘솔 및 네이버 서치어드바이저 연동 확인

---

## 6. 단계별 실행 일정

| 단계 | 기간 | 주요 작업 |
|------|------|---------|
| Phase 1 | 1주차 | 지역별 탭 오류 수정, 메뉴 분류 오류 수정, **쿠팡 배너 오류 수정 및 정적 배너 삽입** |
| Phase 2 | 2~3주차 | 크롤러 기본 구조 개발, 뉴스/이벤트 소스 1~2개 연동 |
| Phase 3 | 4~5주차 | 워드프레스 자동 포스팅 연동, 중복 방지 로직, **자동글 하단 쿠팡 배너 자동 삽입** |
| Phase 4 | 6~7주차 | SEO 자동화, 알림 시스템 구축, **구글 애드센스 신청 준비 (콘텐츠 50개+ 확보)** |
| Phase 5 | 8주차~ | 크롤링 소스 확대, 골프장 데이터 자동 등록, **애드센스 승인 후 광고 배치 최적화** |

---

## 7. 다음 즉시 실행 항목 체크리스트

- [x] `functions.php` — `region_slug` 파라미터 필터 추가 (완료)
- [x] `assets_js_courses.js` — API 파라미터 `region` → `region_slug` 변경 (완료)
- [x] `page-courses.php` — 동일 파라미터 변경 (완료)
- [x] 대회/이벤트 쿼리 수정 및 링크 분리 (`/events/` 로 연결) (완료)
- [ ] 뉴스/소식 — **rewrite rule 방식 제거**, `page-news.php` 템플릿 방식으로 교체 (아래 §3-③ 참고)
- [x] 쿠팡 파트너스 배너 정적/iframe 코드로 위젯 및 템플릿에 교체 삽입 (완료)
- [x] `.env` 파일 및 `.gitignore` 초기 설정 (크롤러 디렉토리 생성 완료)
- [x] `requirements.txt` 작성 및 가상환경 구성 준비 (완료)
- [ ] 파이썬 크롤러(`crawler.py`) 테스트 실행 및 WP API 연동 확인
- [ ] 실제 대한파크골프협회 크롤링 코드 작성 및 스케줄러 등록

---

## 8. 초기 수익화 전략: 쿠팡 파트너스 연계 및 UI 개선 (애드센스 승인 대기 기간)

현재 구글 애드센스 승인을 대기하는 동안, 실질적인 수익 창출을 위해 **쿠팡 파트너스**를 적극적으로 활용합니다. 
기존에 적용된 쿠팡 배너에서 제품 이미지가 보이지 않는 문제를 해결하고, 사용자 클릭률(CTR)을 높이기 위한 시각적 개선을 진행합니다.

### ① 기존 쿠팡 파트너스 광고 오류 수정
- **증상**: 현재 사이트 내 쿠팡 파트너스 광고 영역에 실제 제품 이미지가 노출되지 않거나 깨지는 현상 발생.
- **원인 분석**: 
  1. 쿠팡 파트너스에서 제공하는 동적 iframe 스크립트가 브라우저의 광고 차단(AdBlock) 확장 프로그램에 의해 차단되었을 가능성.
  2. 워드프레스 테마의 CSS 충돌이나 JavaScript 오류로 인해 외부 스크립트가 렌더링되지 않았을 가능성.
  3. 이미지 URL이 HTTP로 혼용되어 최신 HTTPS 보안 정책에 의해 차단(Mixed Content)되었을 가능성.
- **해결 방안**:
  - 기본 제공되는 동적 배너 스크립트(iframe) 대신, **직접 디자인한 정적 이미지 배너와 직접 클릭 링크(a 태그)** 방식으로 교체하여 브라우저 환경에 구애받지 않고 100% 노출되도록 개선.
  - 모바일과 PC 환경 모두에서 깨지지 않고 선명하게 보이도록 반응형(Responsive) CSS 클래스를 적용.

### ② 맞춤형 상품 큐레이션 및 전략적 배치
사용자의 방문 목적에 맞는 '문맥 타겟팅'으로 클릭을 유도합니다.

- **파크골프장 정보 페이지 (`page-courses.php`)**:
  - 골프장 상세 정보 하단 또는 목록 사이사이에 **[추천 파크골프채], [가성비 골프공], [파크골프 파우치 및 장갑]** 등 실제 장비 이미지가 포함된 배너를 자연스럽게 삽입.
  - "이 파크골프장에 갈 때 필요한 필수 장비"와 같은 문구로 클릭 유도.
- **뉴스/소식 및 가이드 페이지**:
  - 본문 중간과 하단에 관련 장비(예: 초보자 가이드 글에는 '입문용 파크골프 세트') 광고를 배치.
- **크롤링 자동 포스팅 연동**:
  - 파이썬 크롤링으로 자동 발행되는 글 하단에, 미리 세팅해둔 쿠팡 파트너스 상품 리스트 템플릿(이미지+버튼)이 자동으로 추가되어 배포되도록 로직 추가.

### ③ 법적 고지 의무 (필수)
쿠팡 파트너스 운영 시 아래 고지문을 **모든 쿠팡 링크가 포함된 페이지**에 반드시 표시해야 합니다 (공정거래위원회 추천·보증 고시 준수).

> 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

- 푸터 또는 해당 배너 하단에 소형 텍스트로 표기
- 미표기 시 과태료 및 파트너스 계정 정지 위험

### ④ 성과 추적
- 쿠팡 파트너스 대시보드에서 주간 클릭수·수익 확인
- 구글 애널리틱스 UTM 파라미터 추가로 유입 경로별 CTR 비교
  - 예: `?utm_source=parkgolfkorea&utm_medium=banner&utm_campaign=course_page`

### ⑤ 다음 실행 항목 (수익화 관련)
- [ ] 브라우저 개발자 도구를 통해 기존 쿠팡 이미지 누락 원인 파악 및 코드 수정
- [ ] 파크골프 전용 인기 상품(채, 공, 가방 등) 3~5개 쿠팡 파트너스 링크 직접 생성
- [ ] 골프장 상세 페이지 및 템플릿에 정적 방식의 시각적 배너(이미지+구매버튼) 커스텀 삽입
- [ ] 모든 쿠팡 링크 페이지에 제휴 고지문 텍스트 추가
- [ ] 구글 애널리틱스 UTM 파라미터 세팅

---

## 9. 구글 애드센스 승인 준비 요건

애드센스 승인을 받기 위해 아래 조건을 충족해야 합니다.

| 요건 | 기준 | 현황 |
|------|------|------|
| 콘텐츠 수 | 양질의 글 30~50개 이상 | 크롤러 자동 발행으로 충족 예정 |
| 도메인 연령 | 최소 3개월 이상 운영 | 확인 필요 |
| 개인정보처리방침 페이지 | 필수 (단독 페이지) | 없으면 즉시 생성 |
| 이용약관 페이지 | 권고 | 확인 필요 |
| 모바일 반응형 | 필수 | 확인 필요 |
| 불법/저작권 콘텐츠 없음 | 필수 | 크롤링 시 출처 명시 필요 |
| 광고 클릭 유도 문구 없음 | 금지 | 쿠팡 배너에 "클릭하세요" 류 문구 제거 |

- **체크리스트**:
  - [ ] 개인정보처리방침 페이지 생성 (워드프레스 페이지로 추가)
  - [ ] 이용약관 페이지 생성
  - [ ] 크롤링 자동글에 원문 출처 링크 표기
  - [ ] 모바일 반응형 전 페이지 확인
  - [ ] 애드센스 신청 전 콘텐츠 50개 이상 확보 목표
