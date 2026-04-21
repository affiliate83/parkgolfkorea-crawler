# 🛠️ 파크골프 코리아 - 지역 탭 필터링 버그 원인 및 해결 방법

## 🔍 버그 원인 분석
보내주신 파일을 분석한 결과, 원인을 정확하게 찾았습니다!

`page-courses.php` 파일에서 지역 탭을 누르면 아래와 같이 워드프레스 REST API를 호출합니다.
`.../wp-json/wp/v2/parkgolf_course?region=seoul`

문제는 워드프레스 기본 시스템상 API에서 `region`이라는 변수를 사용할 때는 반드시 **글자(slug)가 아닌 숫자(Term ID)를 보내야만 정상으로 인식**한다는 점입니다. 
숫자 대신 'seoul', 'busan' 같은 영문 슬러그를 보냈기 때문에, 워드프레스가 "잘못된 요청"으로 판단하여 데이터를 아무것도 보내주지 않고 에러를 반환했던 것입니다.

---

## ✅ 해결 방법 (2가지 파일 수정)

이 문제를 해결하려면 'region' 대신 **'region_slug'**라는 새로운 이름으로 데이터를 주고받도록 살짝만 코드를 수정해주면 완벽하게 작동합니다.

### 1️⃣ `functions.php` 수정 (워드프레스 테마 함수)
`functions.php` 파일의 맨 밑에 있는 **15번 항목**(`parkgolf_rest_region_filter`) 부분을 아래 코드로 **완전히 교체**해 주세요.

```php
// ============================================================
// 15. ★ REST API - region taxonomy 슬러그 필터 지원 (버그 수정됨)
// ============================================================
// REST API에 'region_slug' 파라미터 사용을 허가합니다.
add_filter('rest_parkgolf_course_collection_params', function($query_params) {
    $query_params['region_slug'] = array(
        'description' => 'Region slug',
        'type'        => 'string',
    );
    return $query_params;
});

function parkgolf_rest_region_filter( $args, $request ) {
    // 'region' 대신 'region_slug'로 받아서 필터링합니다.
    if ( ! empty( $request['region_slug'] ) ) {
        $slugs = array_map( 'sanitize_text_field', explode( ',', $request['region_slug'] ) );
        $args['tax_query'] = array(
            array(
                'taxonomy' => 'region',
                'field'    => 'slug',
                'terms'    => $slugs,
                'operator' => 'IN',
            ),
        );
    }
    return $args;
}
add_filter( 'rest_parkgolf_course_query', 'parkgolf_rest_region_filter', 10, 2 );
```

### 2️⃣ `page-courses.php` 수정 (골프장 목록 페이지 템플릿)
`page-courses.php` 파일의 아래쪽 `<script>` 부분에서 `doSearch()` 함수 안의 URL 생성 로직 딱 **한 줄만 변경**해 주세요.

**[기존 코드]** (약 197번째 줄)
```javascript
if (currentRegion) url += `&region=${encodeURIComponent(currentRegion)}`;
```

**[수정할 코드]** (region을 region_slug로 변경)
```javascript
if (currentRegion) url += `&region_slug=${encodeURIComponent(currentRegion)}`;
```

---

이 두 곳만 수정하시고 사이트에서 지역 탭을 눌러보시면, 수도권, 대구/경북 등 각 지역의 파크골프장 카드들이 아주 빠르고 완벽하게 필터링되어 나타날 것입니다! 

수정하시고 잘 작동하는지 확인해 주세요!
