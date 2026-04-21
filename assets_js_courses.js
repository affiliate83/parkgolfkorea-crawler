// 파크골프장 목록 페이지 스크립트

document.addEventListener('DOMContentLoaded', function () {

    const regionTabs  = document.querySelectorAll('.filter-tab');
    const courseCards = document.querySelectorAll('.course-card');
    const searchInput = document.getElementById('courseSearch');
    const gridViewBtn = document.getElementById('gridView');
    const listViewBtn = document.getElementById('listView');
    const courseGrid  = document.getElementById('courseGrid');

    let currentRegion = 'all';
    let currentSearch = '';

    // URL 파라미터로 초기화
    const urlParams   = new URLSearchParams(window.location.search);
    const regionParam = urlParams.get('region');
    const searchParam = urlParams.get('s');

    if (regionParam) {
        currentRegion = regionParam;
        regionTabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.region === regionParam) tab.classList.add('active');
        });
    }

    if (searchParam && searchInput) {
        currentSearch = searchParam;
        searchInput.value = searchParam;
    }

    // 필터 함수
    function filterCourses() {
        let visible = 0;
        courseCards.forEach(card => {
            const matchRegion = currentRegion === 'all' || card.dataset.region === currentRegion;
            const cardText    = card.textContent.toLowerCase();
            const matchSearch = currentSearch === '' || cardText.includes(currentSearch.toLowerCase());
            if (matchRegion && matchSearch) {
                card.classList.remove('hidden');
                visible++;
            } else {
                card.classList.add('hidden');
            }
        });
    }

    // 지역 탭 클릭
    regionTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            regionTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentRegion = this.dataset.region;
            filterCourses();
        });
    });

    // 검색 입력
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            currentSearch = this.value.trim();
            filterCourses();
        });
    }

    // 그리드 / 리스트 뷰 토글
    if (gridViewBtn && listViewBtn && courseGrid) {
        gridViewBtn.addEventListener('click', function () {
            courseGrid.classList.remove('list-view');
            gridViewBtn.classList.add('active');
            listViewBtn.classList.remove('active');
        });
        listViewBtn.addEventListener('click', function () {
            courseGrid.classList.add('list-view');
            listViewBtn.classList.add('active');
            gridViewBtn.classList.remove('active');
        });
    }

    // 초기 필터 실행
    filterCourses();
});
