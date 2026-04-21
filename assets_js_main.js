// 파크골프 코리아 - 메인 자바스크립트

document.addEventListener('DOMContentLoaded', function () {

    // ===== 모바일 메뉴 토글 =====
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileNav     = document.getElementById('mobileNav');

    if (mobileMenuBtn && mobileNav) {
        mobileMenuBtn.addEventListener('click', function () {
            mobileNav.classList.toggle('open');
            const icon = mobileMenuBtn.querySelector('i');
            icon.classList.toggle('fa-bars');
            icon.classList.toggle('fa-times');
        });
    }

    // ===== 헤더 검색 토글 =====
    const searchToggle   = document.getElementById('searchToggle');
    const headerSearchBar = document.getElementById('headerSearchBar');
    const searchClose    = document.getElementById('searchClose');

    if (searchToggle && headerSearchBar) {
        searchToggle.addEventListener('click', function () {
            headerSearchBar.classList.toggle('open');
            if (headerSearchBar.classList.contains('open')) {
                headerSearchBar.querySelector('input').focus();
            }
        });
    }

    if (searchClose && headerSearchBar) {
        searchClose.addEventListener('click', function () {
            headerSearchBar.classList.remove('open');
        });
    }

    // ===== 스크롤 시 헤더 그림자 강화 =====
    const header = document.querySelector('.site-header');
    if (header) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                header.style.boxShadow = '0 4px 20px rgba(0,0,0,0.15)';
            } else {
                header.style.boxShadow = '0 2px 10px rgba(0,0,0,0.08)';
            }
        });
    }

    // ===== 통계 카운트업 애니메이션 =====
    function animateCounter(el, target, suffix = '') {
        let current = 0;
        const step = target / 60;
        const timer = setInterval(function () {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = Math.floor(current).toLocaleString() + suffix;
        }, 16);
    }

    const heroStats = document.querySelector('.hero-stats');
    const statItems = document.querySelectorAll('.stat-item strong');
    if (heroStats && statItems.length > 0) {
        const targets  = [1200, 150, 500000];
        const suffixes = ['+', '+', '+'];
        let animated   = false;

        const observer = new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting && !animated) {
                animated = true;
                statItems.forEach((el, i) => {
                    animateCounter(el, targets[i], suffixes[i]);
                });
            }
        });
        observer.observe(heroStats);
    }

    // ===== 부드러운 스크롤 =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ===== 외부 클릭 시 모바일 메뉴 닫기 =====
    document.addEventListener('click', function (e) {
        if (mobileNav && mobileNav.classList.contains('open')) {
            if (!mobileNav.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                mobileNav.classList.remove('open');
                const icon = mobileMenuBtn.querySelector('i');
                icon.classList.add('fa-bars');
                icon.classList.remove('fa-times');
            }
        }
    });

    console.log('✅ 파크골프 코리아 스크립트 로드 완료');
});
