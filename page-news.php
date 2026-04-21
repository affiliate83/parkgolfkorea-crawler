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
    <div class="archive-hero" style="background:#1a6e3c; color:#fff; padding:40px 20px; border-radius:10px; margin-bottom:30px; text-align:center;">
      <h1 style="margin:0 0 10px; font-size:28px;">뉴스/소식</h1>
      <p class="archive-desc" style="margin:0; opacity:0.8;">파크골프 최신 뉴스와 소식을 전해드립니다.</p>
    </div>
    <div class="content-sidebar-wrap">
      <main class="main-content">
        <?php if ($news_query->have_posts()): ?>
          <style>
            .news-card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
            @media (max-width: 900px) { .news-card-grid { grid-template-columns: repeat(2,1fr); } }
            @media (max-width: 560px) { .news-card-grid { grid-template-columns: 1fr; } }
            .news-card { background: #fff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden; transition: transform .2s, box-shadow .2s; }
            .news-card:hover { transform: translateY(-4px); box-shadow: 0 6px 20px rgba(0,0,0,.13); }
            .news-card-link { display: block; text-decoration: none; color: inherit; height: 100%; }
            .news-card-thumb { width: 100%; height: 160px; overflow: hidden; background: #f0f0f0; display: flex; align-items: center; justify-content: center; }
            .news-card-thumb img { width: 100%; height: 100%; object-fit: cover; }
            .news-card-body { padding: 14px 16px 16px; }
            .news-card-title { font-size: 15px; font-weight: 700; line-height: 1.5; margin: 0 0 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
            .news-card-excerpt { font-size: 13px; color: #666; line-height: 1.6; margin: 0 0 10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
            .news-cat-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; color:#fff; margin-bottom:8px; }
            .archive-pagination { margin-top: 30px; text-align: center; }
            .archive-pagination .page-numbers { display: inline-block; padding: 8px 14px; margin: 0 4px; background: #fff; border: 1px solid #ddd; border-radius: 5px; color: #333; text-decoration: none; }
            .archive-pagination .page-numbers.current { background: #1a6e3c; color: #fff; border-color: #1a6e3c; }
          </style>
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
                  <div class="news-card-thumb no-img"><span style="font-size:48px;color:#ccc;">⛳</span></div>
                <?php endif; ?>
                <div class="news-card-body">
                  <?php if ($cat_name): ?>
                    <span class="news-cat-badge" style="background:<?php echo $cat_color; ?>">
                      <?php echo esc_html($cat_name); ?>
                    </span>
                  <?php endif; ?>
                  <h2 class="news-card-title"><?php the_title(); ?></h2>
                  <p class="news-card-excerpt"><?php echo wp_trim_words(get_the_excerpt(), 25, '...'); ?></p>
                  <div class="news-card-meta" style="font-size:12px; color:#999;">
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
          <div class="no-posts" style="text-align:center; padding:50px 0;"><p style="font-size:18px; color:#666;">⛳ 아직 게시물이 없습니다.</p></div>
        <?php endif; ?>
      </main>
      <?php get_sidebar(); ?>
    </div>
  </div>
</div>
<?php get_footer(); ?>
