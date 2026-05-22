// ══════════════════════════════════════════════════════════════
//  TheMaskMan — index.js  (Advanced Design Edition)
//  New features:
//   1.  Scroll-progress bar
//   2.  Custom magnetic cursor (desktop)
//   3.  Ripple effect on buttons
//   4.  3D tilt + parallax on cards
//   5.  IntersectionObserver entrance animations
//   6.  Quick-view modal (product sheet + chart + nav)
//   7.  Wishlist drawer with FAB + badge
//   8.  Advanced stacked toasts (icon, swipe-dismiss)
//   9.  Scroll-to-top FAB
//  10.  Grid / List view toggle
//  11.  Sort bar (newest / price / discount)
//  12.  Recent searches (localStorage)
//  13.  Share via Web Share API or clipboard
//  14.  Confetti micro-burst on save
//  15.  Card quick-view hover button
//  16.  Image parallax on card hover
//  17.  Keyboard nav (⌘K, Esc, ←→ in modal)
// ══════════════════════════════════════════════════════════════

// ── API base ─────────────────────────────────────────────────
const API_BASE = window.API_BASE || (
  window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000/api'
    : `${window.location.origin}/api`
);

function mapProduct(p) {
  const discount = p.discount_pct ? `${Math.round(p.discount_pct)}% OFF` : null;
  return {
    id: p.id,
    title: p.name || 'Untitled Product',
    description: p.description || '',
    category: p.category_name || p.page_name || 'Deals',
    page_slug: p.page_slug || '',
    image_src: p.image_url || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
    image_gallery: p.image_gallery || [],
    lowest_price: p.lowest_price || null,
    deal_url: p.link || '#',
    price_new: p.discounted_price ? `₹${parseFloat(p.discounted_price).toLocaleString()}` : 'N/A',
    price_old: p.price ? `₹${parseFloat(p.price).toLocaleString()}` : null,
    price_discount: discount,
    tags: p.tags || 'hot',
    badge_type: p.badge_type || 'hot',
    badge_label: p.badge_label || (discount ? `🔥 ${discount}` : '✨ New')
  };
}

function mapCategory(c) {
  return {
    id: c.id,
    title: c.name,
    category: c.parent_name || 'General',
    image_src: c.image_url || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
    price_starting: c.starting_price ? `Starting ₹${parseFloat(c.starting_price).toLocaleString()}` : 'View Deals',
    price_count: c.product_count ? `${c.product_count} Products` : 'Explore',
    badge_type: 'hot',
    badge_label: `📁 ${c.parent_name || 'Category'}`,
    products: []
  };
}

// ══════════════════════════════════════════════════════════════
//  1 · SCROLL PROGRESS BAR
// ══════════════════════════════════════════════════════════════
(function () {
  const bar = document.createElement('div');
  bar.id = 'scrollProgress';
  document.head.insertAdjacentHTML('beforeend',
    '<style>#scrollProgress{position:fixed;top:0;left:0;height:3px;width:0%;background:linear-gradient(90deg,#c0ff00,#a8e600,#c0ff00);background-size:200%;z-index:9999;pointer-events:none;animation:pShimmer 2s linear infinite;transition:width .1s linear;}@keyframes pShimmer{0%{background-position:0%}100%{background-position:200%}}</style>');
  document.body.prepend(bar);
  window.addEventListener('scroll', () => {
    const pct = window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100;
    bar.style.width = Math.min(pct, 100) + '%';
  }, { passive: true });
})();

// ══════════════════════════════════════════════════════════════
//  2 · CUSTOM MAGNETIC CURSOR  (desktop only)
// ══════════════════════════════════════════════════════════════
(function () {
  if (window.matchMedia('(pointer:coarse)').matches) return;
  const dot = document.createElement('div');
  const ring = document.createElement('div');
  dot.id = 'cursorDot'; ring.id = 'cursorRing';
  document.body.append(dot, ring);
  let mx = -200, my = -200, rx = -200, ry = -200;
  document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
  (function loop() {
    dot.style.transform = `translate(${mx}px,${my}px)`;
    rx += (mx - rx) * 0.12; ry += (my - ry) * 0.12;
    ring.style.transform = `translate(${rx}px,${ry}px)`;
    requestAnimationFrame(loop);
  })();
  document.addEventListener('mouseover', e => {
    if (e.target.closest('button,a')) { dot.classList.add('ch'); ring.classList.add('ch'); }
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest('button,a')) { dot.classList.remove('ch'); ring.classList.remove('ch'); }
  });
  document.addEventListener('mousedown', () => ring.classList.add('cc'));
  document.addEventListener('mouseup', () => ring.classList.remove('cc'));
})();

// ══════════════════════════════════════════════════════════════
//  3 · RIPPLE  on buttons
// ══════════════════════════════════════════════════════════════
document.addEventListener('click', e => {
  const btn = e.target.closest('button');
  if (!btn || btn.classList.contains('nr')) return;
  const r = btn.getBoundingClientRect();
  const s = Math.max(r.width, r.height) * 2;
  const rip = document.createElement('span');
  rip.className = 'ripple-fx';
  rip.style.cssText = `width:${s}px;height:${s}px;left:${e.clientX - r.left - s / 2}px;top:${e.clientY - r.top - s / 2}px`;
  btn.style.position = 'relative'; btn.style.overflow = 'hidden';
  btn.append(rip);
  rip.addEventListener('animationend', () => rip.remove());
});

// ══════════════════════════════════════════════════════════════
//  4 · 3D TILT + IMAGE PARALLAX  (rAF throttled)
// ══════════════════════════════════════════════════════════════
let tiltRaf = null;
document.addEventListener('mousemove', e => {
  if (tiltRaf) return;
  tiltRaf = requestAnimationFrame(() => {
    tiltRaf = null;
    const card = e.target.closest('.deal-card');
    if (!card) return;
    const r = card.getBoundingClientRect();
    const dx = (e.clientX - r.left - r.width / 2) / (r.width / 2);
    const dy = (e.clientY - r.top - r.height / 2) / (r.height / 2);
    card.style.transform = `perspective(900px) rotateY(${dx * 6}deg) rotateX(${-dy * 6}deg) translateZ(8px)`;
    const img = card.querySelector('.card-img-wrap img');
    if (img) img.style.transform = `translate(${dx * -8}px,${dy * -8}px) scale(1.08)`;
  });
});
document.addEventListener('mouseleave', e => {
  const card = e.target.closest('.deal-card');
  if (card) {
    card.style.transform = '';
    const img = card.querySelector('.card-img-wrap img');
    if (img) img.style.transform = '';
  }
}, true);

// ══════════════════════════════════════════════════════════════
//  5 · INTERSECTION OBSERVER — staggered entrance
// ══════════════════════════════════════════════════════════════
const entryObs = new IntersectionObserver(entries => {
  entries.forEach(en => {
    if (en.isIntersecting) { en.target.classList.add('card-visible'); entryObs.unobserve(en.target); }
  });
}, { threshold: 0.08 });

function observeCards() {
  setTimeout(() => document.querySelectorAll('.deal-card:not(.card-visible)').forEach(c => entryObs.observe(c)), 60);
}

// ══════════════════════════════════════════════════════════════
//  STATE
// ══════════════════════════════════════════════════════════════
let pages = [];
let productCards = [];
let activeFilter = 'all';
let activeCategory = 'all';
let searchQuery = '';
let searchTimer = null;
let lastProductId = null;
let currentSort = 'newest';
let viewMode = localStorage.getItem('tmm_view') || 'grid';
const PER_PAGE = 8;
const saved = new Set(JSON.parse(localStorage.getItem('tmm_saved') || '[]'));
const recentSearches = JSON.parse(localStorage.getItem('tmm_recentsearch') || '[]');

// ── DOM refs ─────────────────────────────────────────────────
const grid = () => document.getElementById('dealsGrid');
const skeletonGrid = document.getElementById('skeletonGrid');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const searchInput = document.getElementById('globalSearch');
const overlayInput = document.getElementById('searchOverlayInput');

// ══════════════════════════════════════════════════════════════
//  8 · ADVANCED TOAST STACK
// ══════════════════════════════════════════════════════════════
let toastStack;
const TICONS = { success: '✓', error: '✕', info: 'ℹ', heart: '♥', copy: '⎘', fire: '🔥' };

function showToast(msg, type = 'success', ms = 2800) {
  if (!toastStack) {
    toastStack = document.createElement('div');
    toastStack.id = 'toastStack';
    document.body.appendChild(toastStack);
  }
  const el = document.createElement('div');
  el.className = `tmm-toast tmm-toast--${type}`;
  el.innerHTML = `<span class="t-ico">${TICONS[type] || '✓'}</span><span class="t-msg">${msg}</span><button class="t-x nr">✕</button>`;
  toastStack.appendChild(el);
  requestAnimationFrame(() => el.classList.add('t-show'));
  const dismiss = () => {
    el.classList.remove('t-show'); el.classList.add('t-out');
    el.addEventListener('transitionend', () => el.remove(), { once: true });
  };
  el.querySelector('.t-x').addEventListener('click', dismiss);
  let sx = 0;
  el.addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
  el.addEventListener('touchend', e => { if (Math.abs(e.changedTouches[0].clientX - sx) > 60) dismiss(); });
  setTimeout(dismiss, ms);
}

// ══════════════════════════════════════════════════════════════
//  SEARCH RESULT BAR
// ══════════════════════════════════════════════════════════════
function ensureSearchBar() {
  if (document.getElementById('searchResultBar')) return;
  const bar = document.createElement('div');
  bar.id = 'searchResultBar'; bar.className = 'search-result-bar';
  bar.innerHTML = `<span id="srbCount"></span><span id="srbQuery"></span><button class="srb-clear nr" id="srbClear">✕ Clear</button>`;
  bar.style.display = 'none';
  grid().parentElement.insertBefore(bar, grid());
  document.getElementById('srbClear').addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    if (overlayInput) overlayInput.value = '';
    handleSearch('');
  });
}

// ══════════════════════════════════════════════════════════════
//  10 + 11 · SORT BAR + VIEW TOGGLE
// ══════════════════════════════════════════════════════════════
function ensureSortBar() {
  if (document.getElementById('sortViewBar')) return;
  const bar = document.createElement('div');
  bar.id = 'sortViewBar'; bar.className = 'sort-view-bar';
  bar.innerHTML = `
    <div class="sort-opts">
      <span class="sort-lbl">Sort:</span>
      ${['newest', 'price-asc', 'price-desc', 'discount'].map((s, i) => {
    const labels = ['Newest', 'Price ↑', 'Price ↓', '% Off'];
    return `<button class="sort-btn nr${s === 'newest' ? ' active' : ''}" data-sort="${s}">${labels[i]}</button>`;
  }).join('')}
    </div>
    <div class="view-tgl">
      <button class="vbtn nr${viewMode === 'grid' ? ' active' : ''}" data-view="grid" title="Grid">
        <svg viewBox="0 0 16 16" width="13" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>
      </button>
      <button class="vbtn nr${viewMode === 'list' ? ' active' : ''}" data-view="list" title="List">
        <svg viewBox="0 0 16 16" width="13" fill="currentColor"><rect x="1" y="2" width="14" height="3" rx="1"/><rect x="1" y="7" width="14" height="3" rx="1"/><rect x="1" y="12" width="14" height="3" rx="1"/></svg>
      </button>
    </div>`;
  grid().parentElement.insertBefore(bar, grid());

  bar.querySelectorAll('.sort-btn').forEach(b => b.addEventListener('click', () => {
    bar.querySelectorAll('.sort-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); currentSort = b.dataset.sort;
    if (searchQuery) handleSearch(searchQuery); else showPages();
  }));

  bar.querySelectorAll('.vbtn').forEach(b => b.addEventListener('click', () => {
    bar.querySelectorAll('.vbtn').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); viewMode = b.dataset.view;
    localStorage.setItem('tmm_view', viewMode);
    grid().classList.toggle('list-view', viewMode === 'list');
    if (searchQuery) handleSearch(searchQuery); else showPages();
  }));
}

// ══════════════════════════════════════════════════════════════
//  7 · WISHLIST DRAWER
// ══════════════════════════════════════════════════════════════
function initWishlistDrawer() {
  if (document.getElementById('wlDrawer')) return;

  const fab = document.createElement('button');
  fab.id = 'wlFab'; fab.className = 'wl-fab'; fab.title = 'My Wishlist';
  fab.innerHTML = `<svg viewBox="0 0 20 20" fill="none" width="20"><path d="M5 3h10a1 1 0 011 1v13l-6-3-6 3V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.7"/></svg><span id="wlBadge" class="wl-badge">${saved.size || ''}</span>`;
  document.body.appendChild(fab);

  const drawer = document.createElement('div');
  drawer.id = 'wlDrawer'; drawer.className = 'wl-drawer';
  drawer.innerHTML = `
    <div class="wl-backdrop" id="wlBack"></div>
    <div class="wl-panel">
      <div class="wl-header">
        <h2>Saved Deals <span id="wlCnt">(${saved.size})</span></h2>
        <button class="wl-close nr" id="wlClose">✕</button>
      </div>
      <div class="wl-body" id="wlBody"></div>
    </div>`;
  document.body.appendChild(drawer);

  fab.addEventListener('click', openWishlist);
  document.getElementById('wlClose').addEventListener('click', closeWishlist);
  document.getElementById('wlBack').addEventListener('click', closeWishlist);
}

// ══════════════════════════════════════════════════════════════
//  NAV INDICATOR
// ══════════════════════════════════════════════════════════════
function initNavIndicator() {
  const nav = document.getElementById('desktopNav');
  const indicator = document.getElementById('navIndicator');
  const links = nav?.querySelectorAll('.nav-link');
  if (!nav || !indicator || !links.length) return;

  function move(el) {
    indicator.style.width = `${el.offsetWidth}px`;
    indicator.style.left = `${el.offsetLeft}px`;
    indicator.style.opacity = '1';
  }

  links.forEach(link => {
    link.addEventListener('mouseenter', () => move(link));
    if (link.classList.contains('active')) {
      // Tiny delay to ensure layout is ready
      setTimeout(() => move(link), 100);
    }
  });

  nav.addEventListener('mouseleave', () => {
    const active = nav.querySelector('.nav-link.active');
    if (active) move(active); else indicator.style.opacity = '0';
  });
}

function updateWlBadge() {
  const b = document.getElementById('wlBadge'); if (b) b.textContent = saved.size || '';
  const c = document.getElementById('wlCnt'); if (c) c.textContent = `(${saved.size})`;
}

function openWishlist() {
  const drawer = document.getElementById('wlDrawer');
  const body = document.getElementById('wlBody');
  if (!drawer) return;
  const all = [...saved].map(id =>
    productCards.find(p => String(p.id) === id) ||
    pages.flatMap(pg => pg.products || []).find(p => String(p.id) === id)
  ).filter(Boolean);

  body.innerHTML = all.length ? all.map(p => `
    <div class="wl-item" data-id="${p.id}">
      <img src="${p.image_src}" alt="${p.title}" onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'"/>
      <div class="wl-info">
        <span class="wl-title">${p.title}</span>
        <span class="wl-price">${p.price_new}</span>
        ${p.price_discount ? `<span class="wl-disc">${p.price_discount}</span>` : ''}
      </div>
      <div class="wl-acts">
        <a href="${p.deal_url || '#'}" target="_blank" rel="noopener noreferrer" class="wl-go">Go →</a>
        <button class="wl-rm nr" data-id="${p.id}">✕</button>
      </div>
    </div>`).join('')
    : `<p class="wl-empty">No saved deals yet.<br/>Hit ♥ on any card.</p>`;

  body.querySelectorAll('.wl-rm').forEach(b => b.addEventListener('click', () => {
    saved.delete(b.dataset.id);
    localStorage.setItem('tmm_saved', JSON.stringify([...saved]));
    b.closest('.wl-item').classList.add('wl-removing');
    setTimeout(openWishlist, 300);
    updateWlBadge(); updateAllSaveBtns();
  }));

  drawer.classList.add('open');
  document.body.classList.add('has-drawer');
}
function closeWishlist() {
  document.getElementById('wlDrawer')?.classList.remove('open');
  document.body.classList.remove('has-drawer');
}
function updateAllSaveBtns() {
  document.querySelectorAll('.save-btn').forEach(b => {
    b.classList.toggle('saved', saved.has(b.dataset.id));
    b.querySelector('path')?.setAttribute('fill', saved.has(b.dataset.id) ? 'currentColor' : 'none');
  });
}

// ══════════════════════════════════════════════════════════════
//  6 · QUICK-VIEW MODAL
// ══════════════════════════════════════════════════════════════
let qvData = [], qvIdx = 0;

function initQuickViewModal() {
  if (document.getElementById('qvModal')) return;
  const m = document.createElement('div');
  m.id = 'qvModal'; m.className = 'qv-modal'; m.setAttribute('role', 'dialog');
  m.innerHTML = `
    <div class="qv-backdrop" id="qvBack"></div>
    <div class="qv-panel">
      <button class="qv-close nr" id="qvClose">✕</button>
      <button class="qv-nav qv-prev nr" id="qvPrev">‹</button>
      <button class="qv-nav qv-next nr" id="qvNext">›</button>
      <div class="qv-body" id="qvBody"></div>
    </div>`;
  document.body.appendChild(m);
  document.getElementById('qvClose').addEventListener('click', closeQV);
  document.getElementById('qvBack').addEventListener('click', closeQV);
  document.getElementById('qvPrev').addEventListener('click', () => navQV(-1));
  document.getElementById('qvNext').addEventListener('click', () => navQV(+1));
}

function openQV(prod, all, idx) {
  initQuickViewModal();
  qvData = all; qvIdx = idx;
  renderQV(prod);
  document.getElementById('qvModal').classList.add('open');
  document.body.classList.add('has-modal');
  document.getElementById('qvPrev').style.display = idx > 0 ? '' : 'none';
  document.getElementById('qvNext').style.display = idx < all.length - 1 ? '' : 'none';
}
function closeQV() {
  document.getElementById('qvModal')?.classList.remove('open');
  document.body.classList.remove('has-modal');
}
function navQV(dir) {
  qvIdx = Math.max(0, Math.min(qvData.length - 1, qvIdx + dir));
  const body = document.getElementById('qvBody');
  body.classList.add('qv-fade');
  setTimeout(() => {
    renderQV(qvData[qvIdx]); body.classList.remove('qv-fade');
    document.getElementById('qvPrev').style.display = qvIdx > 0 ? '' : 'none';
    document.getElementById('qvNext').style.display = qvIdx < qvData.length - 1 ? '' : 'none';
  }, 160);
}

function renderQV(p) {
  const isSaved = saved.has(String(p.id));
  const gallery = [p.image_src, ...p.image_gallery].slice(0, 6);
  const isLowest = p.lowest_price && p.price_new.includes(parseFloat(p.lowest_price).toLocaleString());

  document.getElementById('qvBody').innerHTML = `
    <div class="qv-img-side">
      <img src="${p.image_src}" alt="${p.title}" class="qv-main-img" id="qvMainImg"
           onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'"/>
      <div class="qv-gallery">
        ${gallery.map((img, i) => `
          <img src="${img}" class="qv-thumb ${i === 0 ? 'active' : ''}" 
               onclick="document.getElementById('qvMainImg').src='${img}'; document.querySelectorAll('.qv-thumb').forEach(t=>t.classList.remove('active')); this.classList.add('active');"
               onerror="this.style.display='none'"/>
        `).join('')}
      </div>
    </div>
    <div class="qv-info">
      <div class="qv-header">
        <div class="qv-badge-row">
          <span class="qv-cat">${p.category}</span>
          ${isLowest ? `<span class="qv-lowest-badge">★ All-Time Lowest Price</span>` : ''}
        </div>
        <h2 class="qv-title">${p.title}</h2>
      </div>

      <div class="qv-price-info">
        <div class="qv-prow">
          <span class="qv-pnew">${p.price_new}</span>
          ${p.price_old ? `<span class="qv-pold">${p.price_old}</span>` : ''}
          ${p.price_discount ? `<span class="qv-pdisc">${p.price_discount}</span>` : ''}
        </div>
        <p style="font-size:12px;color:var(--text-faint);margin-top:4px">Includes all active site discounts</p>
      </div>

      <p class="qv-desc">${p.description || 'Verified deal from premium source. Limited time price optimization active.'}</p>
      
      <div class="qv-chart-wrap" style="margin-top:8px">
        <p class="qv-chart-lbl">Historical Price Trend</p>
        <canvas id="qvc-${p.id}" height="100"></canvas>
        <p class="qv-chart-msg" id="qvcm-${p.id}">Analyzing history…</p>
      </div>

      <div class="qv-viewers">
        <span class="v-dot"></span>
        <span>${Math.floor(Math.random() * 25) + 5}</span> buyers tracking this item
      </div>

      <div class="qv-curr-deal">
        <p class="qv-sim-lbl" style="font-size:11px;color:var(--text-faint);margin-bottom:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em">Market Comparison</p>
        <div id="qvsimg-${p.id}" style="display:flex;gap:12px;overflow-x:auto;padding-bottom:12px;scrollbar-width:none"><i>Scanning market...</i></div>
      </div>

      <div class="qv-acts">
        <button class="qv-share nr" title="Share Product" data-url="${p.deal_url}" data-title="${p.title}">
          <svg viewBox="0 0 20 20" fill="none" width="18"><circle cx="15" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="5" cy="10" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="15" cy="16" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M7 11l5.5 3.5M12.5 6.5L7 9.5" stroke="currentColor" stroke-width="1.5"/></svg>
        </button>
        <button class="qv-save ${isSaved ? 'saved' : ''} nr" data-id="${p.id}" title="Save to Wishlist">
          <svg viewBox="0 0 20 20" fill="${isSaved ? 'currentColor' : 'none'}" width="18"><path d="M5 3h10a1 1 0 011 1v13l-6-3-6 3V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.6"/></svg>
        </button>
        <a href="product.html?id=${p.id}" class="qv-pdp-btn nr" title="Full Product Details">
          <svg viewBox="0 0 20 20" fill="none" width="18"><path d="M10 3v14M3 10h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        </a>
        <a href="${p.deal_url}" target="_blank" rel="noopener noreferrer" class="qv-deal-btn">Get Best Deal Now →</a>
      </div>
    </div>`;

  // Interaction: Save
  document.querySelector('.qv-save').addEventListener('click', function () {
    const id = this.dataset.id;
    if (saved.has(id)) {
      saved.delete(id); this.classList.remove('saved');
      this.querySelector('path').setAttribute('fill', 'none');
      showToast('Removed from wishlist', 'info');
    } else {
      saved.add(id); this.classList.add('saved');
      this.querySelector('path').setAttribute('fill', 'currentColor');
      showToast('♥ Saved to Wishlist!', 'heart'); fireConfetti();
    }
    localStorage.setItem('tmm_saved', JSON.stringify([...saved]));
    updateWlBadge(); updateAllSaveBtns();
  });

  // Interaction: Share
  document.querySelector('.qv-share').addEventListener('click', function () {
    shareProduct(this.dataset.url, this.dataset.title);
  });

  loadPriceChart(p.id, `qvc-${p.id}`, `qvcm-${p.id}`);
  loadSimilarProducts(p.id, `qvsimg-${p.id}`);
}

async function loadSimilarProducts(productId, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  try {
    const res = await fetch(`${API_BASE}/products/${productId}/comparisons`);
    if (!res.ok) throw new Error('Not ok');
    const data = await res.json();
    if (!data || !data.length) {
      container.innerHTML = '<span style="font-size:12px;color:var(--text-faint)">No external comparisons available yet.</span>';
      return;
    }
    const label = document.querySelector(`[id="${containerId}"]`).previousElementSibling;
    if (label) label.textContent = "External Price Comparison";

    container.innerHTML = data.slice(0, 3).map(p => `
      <a href="${p.competitor_url}" target="_blank" rel="noopener noreferrer" class="sim-card" style="min-width:120px;background:var(--bg-elevated);border-radius:12px;padding:10px;font-size:12px;text-decoration:none;color:inherit;border:1px solid var(--border);transition:all 0.2s">
        <div style="font-size:10px;text-transform:uppercase;color:var(--text-faint);margin-bottom:4px;font-weight:700">${p.competitor_name}</div>
        <div style="color:var(--accent);font-weight:800;font-size:14px;margin-bottom:4px">₹${parseFloat(p.competitor_price).toLocaleString()}</div>
        <div style="font-size:9px;color:var(--text-faint)">${Math.round(p.similarity_score * 100)}% AI Match</div>
      </a>
    `).join('');
  } catch {
    container.innerHTML = '<span style="font-size:12px;color:var(--text-faint)">Check back later for comparisons.</span>';
  }
}

// ══════════════════════════════════════════════════════════════
//  13 · SHARE
// ══════════════════════════════════════════════════════════════
async function shareProduct(url, title) {
  if (!url || url === '#') { showToast('No link to share', 'error'); return; }
  if (navigator.share) {
    try { await navigator.share({ title: 'TheMaskMan: ' + title, url }); return; }
    catch { return; }
  }
  try { await navigator.clipboard.writeText(url); showToast('Link copied!', 'copy'); }
  catch { showToast('Could not copy', 'error'); }
}

// ══════════════════════════════════════════════════════════════
//  14 · CONFETTI
// ══════════════════════════════════════════════════════════════
function fireConfetti() {
  const colors = ['#c0ff00', '#00ffcc', '#ff6b00', '#ffffff', '#ffb500'];
  for (let i = 0; i < 32; i++) {
    const p = document.createElement('div'); p.className = 'cfetti';
    p.style.cssText = `left:${Math.random() * 100}vw;background:${colors[i % colors.length]};width:${4 + Math.random() * 7}px;height:${4 + Math.random() * 7}px;animation-delay:${Math.random() * .5}s;animation-duration:${.7 + Math.random() * .7}s;border-radius:${Math.random() > .5 ? '50%' : '2px'}`;
    document.body.appendChild(p);
    p.addEventListener('animationend', () => p.remove());
  }
}

// ══════════════════════════════════════════════════════════════
//  9 · SCROLL-TO-TOP FAB
// ══════════════════════════════════════════════════════════════
(function () {
  const fab = document.createElement('button');
  fab.id = 'stFab'; fab.className = 'st-fab nr';
  fab.innerHTML = `<svg viewBox="0 0 20 20" fill="none" width="17"><path d="M10 15V5M5 10l5-5 5 5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  document.body.appendChild(fab);
  window.addEventListener('scroll', () => fab.classList.toggle('visible', window.scrollY > 400), { passive: true });
  fab.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

// ══════════════════════════════════════════════════════════════
//  12 · RECENT SEARCHES
// ══════════════════════════════════════════════════════════════
function saveRecentSearch(q) {
  if (!q || q.length < 2) return;
  const i = recentSearches.indexOf(q);
  if (i > -1) recentSearches.splice(i, 1);
  recentSearches.unshift(q); recentSearches.splice(5);
  localStorage.setItem('tmm_recentsearch', JSON.stringify(recentSearches));
}

function renderRecentSearches() {
  const c = document.getElementById('recentSearches'); if (!c) return;
  if (!recentSearches.length) { c.style.display = 'none'; return; }
  c.style.display = 'block';
  c.innerHTML = `<p class="recent-lbl">Recent</p><div class="recent-chips">
    ${recentSearches.map(q => `<button class="r-chip nr">${q}</button>`).join('')}
    <button class="r-clear nr">Clear</button></div>`;
  c.querySelectorAll('.r-chip').forEach(ch => ch.addEventListener('click', () => {
    if (searchInput) searchInput.value = ch.textContent;
    handleSearch(ch.textContent); closeOverlay();
  }));
  c.querySelector('.r-clear').addEventListener('click', () => {
    recentSearches.length = 0;
    localStorage.removeItem('tmm_recentsearch'); c.style.display = 'none';
  });
}

function injectRecentSearches() {
  const overlay = document.getElementById('searchOverlay');
  if (!overlay || document.getElementById('recentSearches')) return;
  const el = document.createElement('div');
  el.id = 'recentSearches'; el.className = 'recent-searches';
  const body = overlay.querySelector('form') || overlay.querySelector('[class*="body"]') || overlay;
  body.insertBefore(el, body.firstChild);
  renderRecentSearches();
}

// ══════════════════════════════════════════════════════════════
//  SORT HELPERS
// ══════════════════════════════════════════════════════════════
function numPrice(s) { const n = parseFloat((s || '').replace(/[^0-9.]/g, '')); return isNaN(n) ? Infinity : n; }
function sortItems(arr) {
  const a = [...arr];
  if (currentSort === 'price-asc') return a.sort((x, y) => numPrice(x.price_new || x.price_starting) - numPrice(y.price_new || y.price_starting));
  if (currentSort === 'price-desc') return a.sort((x, y) => numPrice(y.price_new || y.price_starting) - numPrice(x.price_new || x.price_starting));
  if (currentSort === 'discount') return a.sort((x, y) => (parseInt((y.price_discount || '0').replace(/\D/g, '')) || 0) - (parseInt((x.price_discount || '0').replace(/\D/g, '')) || 0));
  return a;
}

// ══════════════════════════════════════════════════════════════
//  SKELETON
// ══════════════════════════════════════════════════════════════
function showSkeleton() {
  skeletonGrid?.classList.add('visible');
  const g = grid(); if (g) g.style.display = 'none';
}
function hideSkeleton() {
  skeletonGrid?.classList.remove('visible');
  const g = grid(); if (g) g.style.display = viewMode === 'list' ? 'block' : 'grid';
}

// ══════════════════════════════════════════════════════════════
//  EMPTY STATE
// ══════════════════════════════════════════════════════════════
function renderEmpty(msg) {
  return `<div class="empty-state" style="grid-column:1/-1;text-align:center;padding:5rem 1rem"><div class="empty-icon">🔍</div><h3>${msg}</h3><p>Try different keywords or browse categories above.</p></div>`;
}

// ══════════════════════════════════════════════════════════════
//  FILTER HELPERS
// ══════════════════════════════════════════════════════════════
function matchesFilter(item) { return activeFilter === 'all' || (item.tags || '').split(',').map(t => t.trim()).includes(activeFilter); }
function matchesCategory(item) { return activeCategory === 'all' || (item.category || '').toLowerCase() === activeCategory.toLowerCase(); }

// ══════════════════════════════════════════════════════════════
//  RENDER — Product Card  (enhanced)
// ══════════════════════════════════════════════════════════════
function renderProductCard(p, delay = 0) {
  const bClass = { hot: 'badge-hot', new: 'badge-new', verified: 'badge-verified' };
  const isSaved = saved.has(String(p.id));
  const disc = parseInt((p.price_discount || '').replace(/\D/g, '')) || 0;

  return `
  <article class="deal-card product-card${viewMode === 'list' ? ' list-card' : ''}"
           data-tags="${p.tags || ''}" data-category="${(p.category || '').toLowerCase()}"
           data-id="${p.id}" role="listitem" style="--delay:${delay}ms; cursor:pointer;"
           onclick="if(!event.target.closest('button') && !event.target.closest('a')) window.location.href='product.html?id=${p.id}'">
    <div class="card-badge ${bClass[p.badge_type] || 'badge-hot'}">${p.badge_label}</div>
    ${disc >= 30 ? `<div class="card-heat-strip${disc >= 50 ? ' strip-fire' : ''}"></div>` : ''}
    <div class="card-img-wrap">
      <a href="product.html?id=${p.id}" style="display:block; width:100%; height:100%;">
        <img src="${p.image_src}" alt="${p.image_alt || p.title}" loading="lazy"
             onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'" style="width:100%; height:100%; object-fit:cover;"/>
        <div class="card-img-overlay"></div>
      </a>
      <button class="card-qv-btn nr" data-id="${p.id}">
        <svg viewBox="0 0 20 20" fill="none" width="13"><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M1 10s3-7 9-7 9 7 9 7-3 7-9 7-9-7-9-7z" stroke="currentColor" stroke-width="1.5"/></svg>
        Quick view
      </button>
    </div>
    <div class="card-body">
      <span class="card-category">${p.category || ''}</span>
      <h3 class="card-title"><a href="product.html?id=${p.id}" class="pdp-link">${p.title}</a></h3>
      <p class="card-desc">${p.description || ''}</p>
      <div class="card-price-row">
        <span class="price-new">${p.price_new}</span>
        ${p.price_old ? `<span class="price-old">${p.price_old}</span>` : ''}
        ${p.price_discount ? `<span class="discount-badge">${p.price_discount}</span>` : ''}
      </div>
      <div class="price-chart-wrap" id="chart-${p.id}">
        <canvas id="canvas-${p.id}" height="60"></canvas>
      </div>
      <div class="card-footer">
        <button class="btn-primary btn-sm card-btn view-deal-btn" data-url="${p.deal_url || '#'}" data-id="${p.id}">View Deal →</button>
        <button class="card-alert-btn nr" data-id="${p.id}" data-title="${p.title}" title="Get Price Alert">
          <svg viewBox="0 0 20 20" fill="none" width="14"><path d="M10 2a5 5 0 015 5c0 3.5 1.5 5 1.5 5H3.5s1.5-1.5 1.5-5a5 5 0 015-5z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M8.5 17a2 2 0 003 0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
        <button class="card-share-btn nr" data-url="${p.deal_url || '#'}" data-title="${p.title}" title="Share">
          <svg viewBox="0 0 20 20" fill="none" width="14"><circle cx="15" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="5" cy="10" r="2" stroke="currentColor" stroke-width="1.5"/><circle cx="15" cy="16" r="2" stroke="currentColor" stroke-width="1.5"/><path d="M7 11l5.5 3.5M12.5 6.5L7 9.5" stroke="currentColor" stroke-width="1.5"/></svg>
        </button>
        <button class="btn-icon save-btn${isSaved ? ' saved' : ''}" data-id="${p.id}" aria-label="Save">
          <svg viewBox="0 0 20 20" fill="${isSaved ? 'currentColor' : 'none'}"><path d="M5 3h10a1 1 0 011 1v13l-6-3-6 3V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/></svg>
        </button>
      </div>
    </div>
  </article>`;
}

// ══════════════════════════════════════════════════════════════
//  RENDER — Page Card  (enhanced)
// ══════════════════════════════════════════════════════════════
function renderPage(pg, delay = 0) {
  const chips = (pg.products || []).slice(0, 3).map(p => `
    <div class="sub-chip">
      <img src="${p.image_src}" alt="${p.title}" onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'"/>
      <span>${p.title.split(' ').slice(0, 3).join(' ')}</span>
    </div>`).join('');
  const cat = pg.category || '';
  const pgKey = `pg-${pg.id || cat}`;
  const isSaved = saved.has(pgKey);
  return `
  <article class="deal-card page-card${viewMode === 'list' ? ' list-card' : ''}"
           data-tags="${pg.tags || ''}" data-category="${cat.toLowerCase()}"
           data-page-id="${pg.id || cat}" data-category-name="${cat}" role="listitem" style="--delay:${delay}ms">
    <div class="card-badge badge-page">📂 ${cat}</div>
    <div class="card-img-wrap">
      <img src="${pg.image_src}" alt="${pg.image_alt || cat}" loading="lazy"
           onerror="this.src='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'"/>
      <div class="card-img-overlay"></div>
      <div class="page-card-count">${pg.price_count}</div>
    </div>
    <div class="card-body">
      <span class="card-category">${cat}</span>
      <h3 class="card-title">${pg.title}</h3>
      <p class="card-desc">${pg.description || ''}</p>
      ${chips ? `<div class="sub-chips">${chips}</div>` : ''}
      <div class="card-price-row">
        <span class="price-new">${pg.price_starting}</span>
        <span class="discount-badge" style="background:rgba(255,181,0,.12);color:#ffb500;border-color:rgba(255,181,0,.25)">${pg.price_count}</span>
      </div>
      <div class="card-footer">
        <button class="btn-primary btn-sm card-btn page-explore-btn" data-page-id="${pg.id || cat}" data-category-name="${cat}">Explore Page →</button>
        <button class="btn-icon save-btn${isSaved ? ' saved' : ''}" data-id="${pgKey}" aria-label="Save">
          <svg viewBox="0 0 20 20" fill="${isSaved ? 'currentColor' : 'none'}"><path d="M5 3h10a1 1 0 011 1v13l-6-3-6 3V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.5"/></svg>
        </button>
      </div>
    </div>
  </article>`;
}

// ══════════════════════════════════════════════════════════════
//  EVENT LISTENERS — after render
// ══════════════════════════════════════════════════════════════
function attachSaveListeners() {
  document.querySelectorAll('.save-btn').forEach(btn => {
    btn.onclick = () => {
      const id = btn.dataset.id;
      if (saved.has(id)) {
        saved.delete(id); btn.classList.remove('saved');
        btn.querySelector('path').setAttribute('fill', 'none');
        showToast('Removed from wishlist', 'info');
      } else {
        saved.add(id); btn.classList.add('saved');
        btn.querySelector('path').setAttribute('fill', 'currentColor');
        showToast('♥ Saved!', 'heart'); fireConfetti();
      }
      localStorage.setItem('tmm_saved', JSON.stringify([...saved])); updateWlBadge();
    };
  });

  document.querySelectorAll('.card-share-btn').forEach(b => {
    b.onclick = e => { e.stopPropagation(); shareProduct(b.dataset.url, b.dataset.title); };
  });

  document.querySelectorAll('.card-alert-btn').forEach(b => {
    b.onclick = e => {
      e.stopPropagation();
      b.classList.toggle('alert-active');
      if (b.classList.contains('alert-active')) {
        b.querySelector('svg path:first-child')?.setAttribute('fill', 'currentColor');
        showToast(`🔔 Price alert set for "${b.dataset.title.split(' ').slice(0, 4).join(' ')}…"`, 'success');
      } else {
        b.querySelector('svg path:first-child')?.setAttribute('fill', 'none');
        showToast('Alert removed', 'info');
      }
    };
  });

  document.querySelectorAll('.card-qv-btn').forEach(b => {
    b.onclick = e => {
      e.stopPropagation();
      const id = b.dataset.id;
      const all = [...productCards, ...pages.flatMap(pg => pg.products || [])];
      const idx = all.findIndex(p => String(p.id) === String(id));
      if (idx > -1) openQV(all[idx], all, idx);
    };
  });

  observeCards();
}

function attachPageExploreBtns() {
  document.querySelectorAll('.page-explore-btn').forEach(btn => {
    btn.onclick = () => loadPageProducts(btn.dataset.pageId || btn.dataset.categoryName);
  });
}

// ══════════════════════════════════════════════════════════════
//  DISPLAY — Page Cards
// ══════════════════════════════════════════════════════════════
function showPages() {
  const bar = document.getElementById('searchResultBar');
  if (bar) bar.style.display = 'none';
  if (loadMoreBtn) loadMoreBtn.parentElement.style.display = 'flex';
  const t = document.querySelector('#deals-section .section-title');
  const s = document.querySelector('#deals-section .section-subtitle');
  if (t) t.textContent = 'Featured Categories';
  if (s) s.textContent = 'Tap a category to explore curated deals';
  const filtered = sortItems(pages.filter(pg => matchesFilter(pg) && matchesCategory(pg)));
  const g = grid(); g.classList.toggle('list-view', viewMode === 'list');
  g.innerHTML = filtered.length ? filtered.map((pg, i) => renderPage(pg, i * 55)).join('') : renderEmpty('No pages match this filter');
  attachSaveListeners(); attachPageExploreBtns();
}

// ══════════════════════════════════════════════════════════════
//  DISPLAY — Search Results
// ══════════════════════════════════════════════════════════════
function showSearchResults(results, query) {
  const bar = document.getElementById('searchResultBar');
  if (bar) {
    bar.style.display = 'flex';
    document.getElementById('srbCount').textContent = `${results.length} result${results.length !== 1 ? 's' : ''} for`;
    document.getElementById('srbQuery').textContent = `"${query}"`;
  }
  if (loadMoreBtn) loadMoreBtn.parentElement.style.display = 'none';
  const t = document.querySelector('#deals-section .section-title');
  const s = document.querySelector('#deals-section .section-subtitle');
  if (t) t.textContent = 'Search Results';
  if (s) s.textContent = `Showing products for "${query}"`;
  const sorted = sortItems(results);
  const g = grid(); g.classList.toggle('list-view', viewMode === 'list');
  g.innerHTML = sorted.length ? sorted.map((p, i) => renderProductCard(p, i * 45)).join('') : renderEmpty('No products found');
  attachSaveListeners();
}

// ══════════════════════════════════════════════════════════════
//  LOAD CATEGORY
// ══════════════════════════════════════════════════════════════
async function loadPageProducts(subcatId) {
  showSkeleton();
  try {
    const res = await fetch(`${API_BASE}/products?page_id=${subcatId}&size=50`);
    const data = await res.json();
    const prods = data.items.map(mapProduct);
    hideSkeleton();
    const bar = document.getElementById('searchResultBar');
    if (bar) { bar.style.display = 'flex'; document.getElementById('srbCount').textContent = `${prods.length} products in`; document.getElementById('srbQuery').textContent = 'Page'; }
    if (loadMoreBtn) loadMoreBtn.parentElement.style.display = 'none';
    const t = document.querySelector('#deals-section .section-title'); if (t) t.textContent = 'Page Products';
    const sorted = sortItems(prods);
    const g = grid(); g.classList.toggle('list-view', viewMode === 'list');
    g.innerHTML = sorted.length ? sorted.map((p, i) => renderProductCard(p, i * 45)).join('') : renderEmpty('No products in this page yet');
    attachSaveListeners();
    document.getElementById('deals-section')?.scrollIntoView({ behavior: 'smooth' });
  } catch { hideSkeleton(); showToast('Failed to load page', 'error'); }
}

// ══════════════════════════════════════════════════════════════
//  SEARCH
// ══════════════════════════════════════════════════════════════
async function handleSearch(query) {
  searchQuery = query.trim();
  if (searchInput && searchInput.value !== query) searchInput.value = query;
  if (overlayInput && overlayInput.value !== query) overlayInput.value = query;
  if (!searchQuery) { hideSkeleton(); showPages(); return; }
  showSkeleton(); clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(searchQuery)}`);
      const raw = await res.json();
      const mapped = raw.map(mapProduct);
      hideSkeleton(); saveRecentSearch(searchQuery); showSearchResults(mapped, searchQuery);
    } catch {
      const q = searchQuery.toLowerCase();
      const results = productCards.filter(p =>
        (p.title || '').toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) || (p.tags || '').toLowerCase().includes(q));
      hideSkeleton(); showSearchResults(results, searchQuery);
    }
  }, 300);
}

// ══════════════════════════════════════════════════════════════
//  FETCH
// ══════════════════════════════════════════════════════════════
async function fetchAll() {
  const [pR, prR] = await Promise.all([fetch(`${API_BASE}/pages`), fetch(`${API_BASE}/products?size=20`)]);
  const rawCats = await pR.json();
  const rawProds = await prR.json();
  pages = rawCats.map(mapCategory);
  productCards = rawProds.items.map(mapProduct);
}

// ══════════════════════════════════════════════════════════════
//  FILTER / CATEGORY BUTTONS
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('.filter-btn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.filter-btn').forEach(x => x.classList.remove('active')); b.classList.add('active');
  activeFilter = b.dataset.filter;
  if (searchQuery) handleSearch(searchQuery); else showPages();
}));

document.querySelectorAll('.category-chip').forEach(c => c.addEventListener('click', () => {
  document.querySelectorAll('.category-chip').forEach(x => x.classList.remove('active')); c.classList.add('active');
  activeCategory = c.dataset.category;
  if (searchQuery) handleSearch(searchQuery); else showPages();
  document.getElementById('deals-section')?.scrollIntoView({ behavior: 'smooth' });
}));

// ══════════════════════════════════════════════════════════════
//  SEARCH INPUTS + COMMAND PALETTE (Overlay)
// ══════════════════════════════════════════════════════════════
const searchTriggerBtn = document.getElementById('searchTriggerBtn');
const searchOverlay = document.getElementById('searchOverlay');
const searchOverlayClose = document.getElementById('searchOverlayClose');
const cmdInput = document.getElementById('searchOverlayInput');
const cmdBody = document.getElementById('cmdBody');

function openOverlay() {
  searchOverlay?.classList.add('active'); 
  searchOverlay?.setAttribute('aria-hidden', 'false');
  setTimeout(() => cmdInput?.focus(), 100);
}
function closeOverlay() { 
  searchOverlay?.classList.remove('active'); 
  searchOverlay?.setAttribute('aria-hidden', 'true'); 
}

searchTriggerBtn?.addEventListener('click', openOverlay);
document.getElementById('spSearchBtn')?.addEventListener('click', openOverlay);
document.getElementById('mobileSearchBtn')?.addEventListener('click', openOverlay);
document.getElementById('mobileSavedBtn')?.addEventListener('click', openWishlist);
searchOverlayClose?.addEventListener('click', closeOverlay);
searchOverlay?.addEventListener('click', e => { 
  if (e.target === searchOverlay) closeOverlay(); 
});

let cmdSearchTimer;
cmdInput?.addEventListener('input', e => {
  clearTimeout(cmdSearchTimer);
  const q = e.target.value.trim().toLowerCase();
  if (!q) {
    if(cmdBody) cmdBody.innerHTML = `<div class="cmd-section-title">Type to search deals...</div>`;
    return;
  }
  cmdSearchTimer = setTimeout(() => {
    const all = [...productCards, ...pages.flatMap(pg => pg.products || [])];
    const results = all.filter(p => (p.title||'').toLowerCase().includes(q) || (p.category||'').toLowerCase().includes(q)).slice(0, 5);
    if(cmdBody) {
      if(results.length) {
        cmdBody.innerHTML = `<div class="cmd-section-title">Results</div>` + results.map(p => `
          <div class="cmd-item" data-id="${p.id}" onclick="window.location.href='product.html?id=${p.id}'">
            <div class="cmd-item-img" style="background-image:url('${p.image_src}')"></div>
            <div class="cmd-item-info">
              <div class="cmd-item-title">${p.title}</div>
              <div class="cmd-item-desc">${p.category} • ${p.price_new}</div>
            </div>
          </div>
        `).join('');
      } else {
        cmdBody.innerHTML = `<div class="cmd-section-title">No results found for "${q}"</div>`;
      }
    }
  }, 250);
});

// 17 · KEYBOARD SHORTCUTS
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openOverlay(); }
  if (e.key === 'Escape') { closeQV(); closeOverlay(); closeWishlist(); }
  
  if (searchOverlay?.classList.contains('active') && cmdBody) {
    const items = Array.from(cmdBody.querySelectorAll('.cmd-item'));
    if (!items.length) return;
    let activeIdx = items.findIndex(el => el.classList.contains('active'));
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (activeIdx > -1) items[activeIdx].classList.remove('active');
      activeIdx = (activeIdx + 1) % items.length;
      items[activeIdx].classList.add('active');
      items[activeIdx].scrollIntoView({ block: 'nearest' });
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (activeIdx > -1) items[activeIdx].classList.remove('active');
      activeIdx = (activeIdx - 1 + items.length) % items.length;
      items[activeIdx].classList.add('active');
      items[activeIdx].scrollIntoView({ block: 'nearest' });
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIdx > -1) items[activeIdx].click();
      else if (items.length > 0) items[0].click();
    }
  }

  if (document.getElementById('qvModal')?.classList.contains('open')) {
    if (e.key === 'ArrowLeft') navQV(-1);
    if (e.key === 'ArrowRight') navQV(+1);
  }
});

// ══════════════════════════════════════════════════════════════
//  MOBILE SIDEBAR
// ══════════════════════════════════════════════════════════════
const sidebar = document.getElementById('mobileSidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
document.getElementById('mobileMenuBtn')?.addEventListener('click', () => { sidebar?.classList.add('open'); sidebarOverlay?.classList.add('active'); });
document.getElementById('sidebarClose')?.addEventListener('click', () => { sidebar?.classList.remove('open'); sidebarOverlay?.classList.remove('active'); });
sidebarOverlay?.addEventListener('click', () => { sidebar?.classList.remove('open'); sidebarOverlay?.classList.remove('active'); });

// ══════════════════════════════════════════════════════════════
//  HEADER SCROLL & SMART STICKY PILL / DARK MODE
// ══════════════════════════════════════════════════════════════
const siteHeader = document.getElementById('siteHeader');
const stickyPill = document.getElementById('stickyPill');
let lastScrollY = window.scrollY;

window.addEventListener('scroll', () => {
  const currentScrollY = window.scrollY;
  siteHeader?.classList.toggle('scrolled', currentScrollY > 20);
  
  if (currentScrollY > 120) {
    if (currentScrollY > lastScrollY) {
      siteHeader?.classList.add('hide-up');
      stickyPill?.classList.add('active');
    } else {
      siteHeader?.classList.remove('hide-up');
      stickyPill?.classList.remove('active');
    }
  } else {
    siteHeader?.classList.remove('hide-up');
    stickyPill?.classList.remove('active');
  }
  lastScrollY = currentScrollY;
}, { passive: true });

const modeToggle = document.getElementById('modeToggle');
const isDark = localStorage.getItem('tmm_dark') !== 'false';
document.body.classList.toggle('dark', isDark);

function updateToggleUI(dark) {
  // SVG Morph styles are purely handled via CSS .dark targeting path elements
  if (!modeToggle) return;
}
updateToggleUI(isDark);

modeToggle?.addEventListener('click', () => {
  const d = document.body.classList.toggle('dark');
  localStorage.setItem('tmm_dark', d);
  updateToggleUI(d);
});

// ══════════════════════════════════════════════════════════════
//  CONTEXTUAL UI / NAV INDICATOR / MEGA MENU
// ══════════════════════════════════════════════════════════════
function updateAccountSavings() {
  const savingsVal = document.getElementById('accountSavingsVal');
  if (!savingsVal) return;
  const mockSavingsAmt = saved.size * 1250; 
  savingsVal.textContent = mockSavingsAmt > 0 ? `₹${mockSavingsAmt.toLocaleString()}` : '₹0';
}
setInterval(updateAccountSavings, 2000);
setTimeout(updateAccountSavings, 500);


function setupMegaMenu() {
  const megaSubcats = document.getElementById('megaSubcats');
  const megaSpotlight = document.getElementById('megaSpotlight');
  if (megaSubcats) {
    const catsToShow = pages.slice(0, 4);
    if(catsToShow.length) {
      megaSubcats.innerHTML = catsToShow.map(c => `
        <a href="#" class="mega-subcard">
          <div class="mega-subimg" style="background-image:url('${c.image_src}')"></div>
          <span>${c.title}</span>
        </a>
      `).join('');
    }
  }
  if (megaSpotlight && productCards.length) {
    const spot = productCards.find(p => p.price_discount && parseInt(p.price_discount) >= 40) || productCards[0];
    if (spot) {
      megaSpotlight.innerHTML = `
        <div class="spotlight-badge">${spot.price_discount || 'Hot Deal'}</div>
        <div class="spotlight-img" style="background-image:url('${spot.image_src}')"></div>
        <div class="spotlight-info">
          <h5>${spot.title}</h5>
          <div class="spotlight-price">${spot.price_new}</div>
        </div>
        <a href="product.html?id=${spot.id}" class="spotlight-btn">Shop Now</a>
      `;
    }
  }
}
setTimeout(setupMegaMenu, 1500);

// ══════════════════════════════════════════════════════════════
//  NEWSLETTER
// ══════════════════════════════════════════════════════════════
document.getElementById('newsletterForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const email = document.getElementById('emailInput')?.value?.trim(); if (!email) return;
  try { await fetch(`${API_BASE}/newsletter`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }); } catch { }
  showToast('✓ Subscribed!', 'success');
  if (document.getElementById('emailInput')) document.getElementById('emailInput').value = '';
});

// ══════════════════════════════════════════════════════════════
//  LOAD MORE
// ══════════════════════════════════════════════════════════════
let currentProductPage = 1;
if (typeof loadMoreBtn !== 'undefined' && loadMoreBtn) {
  loadMoreBtn.addEventListener('click', async () => {
    loadMoreBtn.classList.add('loading');
    try {
      currentProductPage++;
      const res = await fetch(`${API_BASE}/products?size=${PER_PAGE}&page=${currentProductPage}`);
      const moreRaw = await res.json();
      const more = moreRaw.items.map(mapProduct);
      if (!more.length) { loadMoreBtn.textContent = 'No more deals'; loadMoreBtn.disabled = true; return; }

    productCards.push(...more);
    more.forEach((p, i) => grid().insertAdjacentHTML('beforeend', renderProductCard(p, i * 45)));
    attachSaveListeners();
    if (more.length < PER_PAGE) { loadMoreBtn.textContent = 'No more deals'; loadMoreBtn.disabled = true; }
  } catch { showToast('Failed to load more', 'error'); }
    finally { loadMoreBtn.classList.remove('loading'); }
  });
}

// ══════════════════════════════════════════════════════════════
//  VIEW DEAL
// ══════════════════════════════════════════════════════════════
document.addEventListener('click', e => {
  const b = e.target.closest('.view-deal-btn'); if (!b) return;
  const url = b.dataset.url;
  if (!url || url === '#') { showToast('No deal link available', 'error'); return; }
  window.open(url, '_blank', 'noopener,noreferrer');
});

// ══════════════════════════════════════════════════════════════
//  PRICE CHART  (shared by card + modal)
// ══════════════════════════════════════════════════════════════
async function loadPriceChart(productId, canvasId, msgId) {
  const cId = canvasId || ('canvas-' + productId);
  const canvas = document.getElementById(cId); if (!canvas) return;
  const wrap = canvasId ? null : document.getElementById('chart-' + productId);
  const msg = msgId ? document.getElementById(msgId) : null;
  try {
    const res = await fetch(`${API_BASE}/products/${productId}/price-history`);
    const data = await res.json();
    if (!data.length || data.length < 2) {
      if (wrap) wrap.style.display = 'none';
      if (msg) msg.textContent = 'Not enough data yet.'; return;
    }
    if (wrap) wrap.style.display = 'block';
    if (msg) msg.style.display = 'none';
    if (canvas._ci) canvas._ci.destroy();
    const mn = Math.min(...data.map(d => d.price));
    const mx = Math.max(...data.map(d => d.price));
    canvas._ci = new window.Chart(canvas, {
      type: 'line',
      data: {
        labels: data.map(d => d.date),
        datasets: [{
          data: data.map(d => d.price),
          borderColor: '#c0ff00',
          backgroundColor: ctx => {
            const canvas = ctx.chart.ctx.canvas;
            const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, canvas.height);
            g.addColorStop(0, 'rgba(192,255,0,0.3)'); g.addColorStop(1, 'rgba(192,255,0,0)'); return g;
          },
          borderWidth: 3, 
          pointRadius: 0, 
          pointHoverRadius: 6,
          pointBackgroundColor: '#c0ff00', 
          pointBorderColor: '#0a0a0a', 
          pointBorderWidth: 2,
          fill: true, 
          tension: 0.4,
          borderCapStyle: 'round'
        }]
      },
      options: {
        responsive: true, 
        maintainAspectRatio: false,
        layout: { padding: { top: 10, bottom: 0, left: 0, right: 10 } },
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(10,10,10,0.95)', 
            borderColor: 'rgba(192,255,0,0.3)', 
            borderWidth: 1,
            titleColor: '#c0ff00', 
            bodyColor: '#fff', 
            padding: 12,
            cornerRadius: 8,
            titleFont: { size: 12, weight: 'bold', family: 'Inter' },
            bodyFont: { size: 14, weight: '600', family: 'Inter' },
            displayColors: false,
            callbacks: { 
              label: ctx => '₹' + ctx.parsed.y.toLocaleString('en-IN'),
              title: items => {
                const d = new Date(items[0].label);
                return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
              }
            }
          }
        },
        scales: {
          x: { 
            ticks: { 
              color: '#888', 
              font: { size: 10, family: 'Inter' }, 
              maxTicksLimit: 6,
              callback: function(val, index) {
                const d = new Date(this.getLabelForValue(val));
                return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
              }
            }, 
            grid: { display: false }, 
            border: { display: false } 
          },
          y: { 
            ticks: { 
              color: '#888', 
              font: { size: 10, family: 'Inter' }, 
              callback: v => '₹' + (v >= 1000 ? (v/1000).toFixed(1) + 'k' : v),
              maxTicksLimit: 5
            }, 
            grid: { color: 'rgba(255,255,255,0.05)', drawTicks: false }, 
            border: { display: false }, 
            min: Math.floor(mn * 0.98), 
            max: Math.ceil(mx * 1.02) 
          }
        }
      }
    });
  } catch { if (wrap) wrap.style.display = 'none'; }
}

// ══════════════════════════════════════════════════════════════
//  FALLBACK DATA
// ══════════════════════════════════════════════════════════════
const FALLBACK_PRODUCT_CARDS = [
  { id: 1, badge_type: 'hot', badge_label: '🔥 Hot', image_src: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80', image_alt: 'Nike Air Max', category: 'Footwear', title: 'Nike Air Max 270 React', description: 'Iconic cushioning meets modern style. Limited stock.', price_new: '₹3,499', price_old: '₹7,999', price_discount: '56% OFF', tags: 'hot,fashion', deal_url: '#' },
  { id: 2, badge_type: 'new', badge_label: '✨ New', image_src: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80', image_alt: 'Sony Headphones', category: 'Gadgets', title: 'Sony WH-1000XM5 ANC', description: 'Industry-leading noise cancellation, 30hr battery.', price_new: '₹18,990', price_old: '₹32,990', price_discount: '42% OFF', tags: 'new,gadgets', deal_url: '#' },
  { id: 3, badge_type: 'verified', badge_label: '✅ Verified', image_src: 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80', image_alt: 'H&M', category: 'Fashion', title: 'H&M Weekend Sale', description: 'Up to 60% off on apparel this weekend only.', price_new: 'From ₹499', price_old: '₹1,299', price_discount: '60% OFF', tags: 'verified,fashion', deal_url: '#' }
];
const FALLBACK_PAGE_CARDS = [
  { id: 1, name: 'Shoes under ₹1,000', slug: 'shoes_under_1000', parent_name: 'Footwear', image_src: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80', price_starting: 'Starting ₹399', price_count: '200+ Products', tags: 'hot,fashion' },
  { id: 2, name: 'Earphones under ₹999', slug: 'earphones_under_999', parent_name: 'Gadgets', image_src: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80', price_starting: 'Starting ₹199', price_count: '150+ Products', tags: 'new,gadgets' },
  { id: 3, name: 'Clothing under ₹1,500', slug: 'clothing_under_1500', parent_name: 'Fashion', image_src: 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80', price_starting: 'Starting ₹499', price_count: '500+ Products', tags: 'verified,fashion' }
];

// ══════════════════════════════════════════════════════════════
//  CHATBOT AI
// ══════════════════════════════════════════════════════════════
function initChatbot() {
  const fab = document.getElementById('chatbotFab');
  const win = document.getElementById('chatbotWindow');
  const close = document.getElementById('chatbotClose');
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const body = document.getElementById('chatbotBody');

  if (!fab || !win || !form || !input || !body) return;

  fab.addEventListener('click', () => {
    win.classList.toggle('active');
    if (win.classList.contains('active')) input.focus();
  });
  close.addEventListener('click', () => win.classList.remove('active'));

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
  }

  async function streamText(element, text) {
    element.innerHTML = '';
    const words = text.split(' ');
    for (let i = 0; i < words.length; i++) {
        element.innerHTML += words[i] + ' ';
        body.scrollTop = body.scrollHeight;
        await new Promise(r => setTimeout(r, 45)); // smooth 45ms pacing for premium streaming effect
    }
  }

  function appendUserMsg(txt) {
    const row = document.createElement('div');
    row.className = 'chat-row user';
    row.innerHTML = `<div class="chat-msg user-msg">${escapeHtml(txt)}</div>`;
    body.appendChild(row);
    body.scrollTop = body.scrollHeight;
  }

  function appendBotTyping() {
    const row = document.createElement('div');
    row.className = 'chat-row bot';
    row.id = 'botTypingRow';
    row.innerHTML = `<div class="chat-msg bot-msg"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
    body.appendChild(row);
    body.scrollTop = body.scrollHeight;
    return row;
  }

  function handleMessageSend(txt) {
    txt = txt.trim();
    if (!txt) return;
    input.value = '';
    appendUserMsg(txt);
    
    // Remove previous suggestions to keep chat clean
    document.querySelectorAll('.chat-suggestions').forEach(el => el.remove());
    
    const typingRow = appendBotTyping();

    fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: txt })
    }).then(r => r.json()).then(async data => {
      if (document.getElementById('botTypingRow')) {
        typingRow.remove();
      }
      
      const row = document.createElement('div');
      row.className = 'chat-row bot';
      const msgBubble = document.createElement('div');
      msgBubble.className = 'chat-msg bot-msg';
      row.appendChild(msgBubble);
      body.appendChild(row);

      // Stream AI text
      const replyText = data.text || data.reply || data.response || "I couldn't process that request.";
      await streamText(msgBubble, replyText);

      // Add sources if available
      if (data.sources && data.sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'chat-sources';
        sourcesDiv.innerHTML = `<strong>Sources:</strong> ` + data.sources.map((s, i) => `<a href="${s}" target="_blank">Link ${i+1}</a>`).join(', ');
        msgBubble.appendChild(sourcesDiv);
      }

      // Map intelligent product cards natively
      if (data.products && data.products.length > 0) {
        const prodContainer = document.createElement('div');
        prodContainer.className = 'chat-products';
        prodContainer.innerHTML = data.products.map(p => `
          <a href="${p.deal_url}" target="_blank" class="chat-product-card">
            <img src="${p.image_src}" class="chat-product-img" onerror="this.src='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&q=80'">
            <div class="chat-product-info">
              <div class="chat-product-title">${escapeHtml(p.title)}</div>
              <div class="chat-product-price">${escapeHtml(p.price)}</div>
              <div class="chat-product-tag">${escapeHtml(p.discount)}</div>
            </div>
          </a>
        `).join('');
        row.appendChild(prodContainer);
      }

      // Add interactive smart suggestions
      if (data.suggestions && data.suggestions.length > 0) {
        const suggContainer = document.createElement('div');
        suggContainer.className = 'chat-suggestions';
        suggContainer.innerHTML = data.suggestions.map(s => `<button class="chat-chip">${escapeHtml(s)}</button>`).join('');
        row.appendChild(suggContainer);

        // Bind clicks to chips recursively
        suggContainer.querySelectorAll('.chat-chip').forEach(chip => {
          chip.addEventListener('click', () => {
            handleMessageSend(chip.textContent);
          });
        });
      }

      body.scrollTop = body.scrollHeight;

    }).catch(e => {
      if (document.getElementById('botTypingRow')) typingRow.remove();
      const row = document.createElement('div');
      row.className = 'chat-row bot';
      row.innerHTML = `<div class="chat-msg bot-msg" style="color:#EF4444">Oops, connection failed. My servers might be offline.</div>`;
      body.appendChild(row);
      body.scrollTop = body.scrollHeight;
    });
  }

  form.addEventListener('submit', e => {
    e.preventDefault();
    handleMessageSend(input.value);
  });
}

// ══════════════════════════════════════════════════════════════
//  HERO — populate with real data
// ══════════════════════════════════════════════════════════════
function animateCounter(el, target, suffix = '') {
  if (!el) return;
  const duration = 1200;
  const start = performance.now();
  const run = now => {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.floor(target * ease).toLocaleString('en-IN') + suffix;
    if (t < 1) requestAnimationFrame(run);
  };
  requestAnimationFrame(run);
}

function populateHero() {
  // ── Stats ───────────────────────────────────────
  const allProds = [...productCards, ...pages.flatMap(pg => pg.products || [])];
  const totalDeals = allProds.length || productCards.length;
  const totalCategories = pages.length;

  // Compute average discount
  let discSum = 0, discCount = 0;
  allProds.forEach(p => {
    const d = parseInt((p.price_discount || '').replace(/\D/g, '')) || 0;
    if (d > 0) { discSum += d; discCount++; }
  });
  const avgDisc = discCount ? Math.round(discSum / discCount) : 35;

  animateCounter(document.getElementById('heroStatDeals'), totalDeals, '+');
  animateCounter(document.getElementById('heroStatBrands'), totalCategories, '+');
  animateCounter(document.getElementById('heroStatSavings'), avgDisc, '%');

  // ── Floating cards — pick top 3 discounted products ─────
  const sorted = [...allProds]
    .map(p => ({ ...p, _disc: parseInt((p.price_discount || '').replace(/\D/g, '')) || 0 }))
    .filter(p => p._disc > 0)
    .sort((a, b) => b._disc - a._disc)
    .slice(0, 3);

  const tags = ['🔥 Hot Deal', '⚡ Flash Sale', '✅ Verified'];
  sorted.forEach((p, i) => {
    const card = document.getElementById(`heroFloat${i + 1}`);
    if (!card) return;
    const inner = card.querySelector('.float-card-inner');
    if (!inner) return;
    inner.innerHTML = `
      <span class="float-tag">${tags[i]}</span>
      <p class="float-title">${p.title.split(' ').slice(0, 4).join(' ')}</p>
      <p class="float-price">
        <span class="price-new">${p.price_new}</span>
        ${p.price_old ? `<span class="price-old">${p.price_old}</span>` : ''}
      </p>`;
  });
}

function populateTicker() {
  const el = document.getElementById('tickerContent');
  const clone = document.querySelector('.ticker-clone');
  if (!el) return;

  const allProds = [...productCards, ...pages.flatMap(pg => pg.products || [])];
  const picks = allProds
    .filter(p => p.price_discount && p.price_new)
    .sort(() => Math.random() - 0.5)
    .slice(0, 10);

  if (!picks.length) return; // keep hardcoded fallback

  const emojis = ['🔥', '⚡', '💰', '🏷️', '🔔', '✨', '📦', '🎧', '👟', '💎'];
  const formats = [
    p => `${p.title.split(' ').slice(0, 3).join(' ')} dropped to ${p.price_new} — ${p.price_discount}`,
    p => `${p.title.split(' ').slice(0, 3).join(' ')} now ${p.price_new} — Lowest Ever`,
    p => `Flash: ${p.title.split(' ').slice(0, 3).join(' ')} at ${p.price_new}`,
    p => `${p.title.split(' ').slice(0, 3).join(' ')} — Flat ${p.price_discount} ends midnight`,
    p => `${p.category || 'Deal'}: ${p.title.split(' ').slice(0, 3).join(' ')} — ${p.price_discount} savings`,
  ];

  const html = picks.map((p, i) => {
    const emoji = emojis[i % emojis.length];
    const text = formats[i % formats.length](p);
    return `<span class="ticker-item">${emoji} ${text}</span><span class="ticker-sep" aria-hidden="true">◆</span>`;
  }).join('');

  el.innerHTML = html;
  if (clone) clone.innerHTML = html;
}

// ══════════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════════
async function init() {
  document.getElementById('spSearchBtn')?.addEventListener('click', openOverlay);
  document.getElementById('mobileSearchBtn')?.addEventListener('click', openOverlay);
  document.getElementById('mobileSavedBtn')?.addEventListener('click', openWishlist);
  document.getElementById('spSavedBtn')?.addEventListener('click', openWishlist);

  if (!document.getElementById('dealsGrid')) {
    initChatbot(); 
    return;        
  }
  ensureSearchBar(); ensureSortBar(); initWishlistDrawer(); initQuickViewModal(); initChatbot();

  // Account dropdown toggle
  const acToggle = document.getElementById('accountToggle');
  const acDropdown = document.getElementById('accountDropdown');
  if (acToggle && acDropdown) {
    acToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = acDropdown.classList.toggle('open');
      acToggle.setAttribute('aria-expanded', open);
      acDropdown.setAttribute('aria-hidden', !open);
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#headerAccount')) {
        acDropdown.classList.remove('open');
        acToggle.setAttribute('aria-expanded', 'false');
        acDropdown.setAttribute('aria-hidden', 'true');
      }
    });
    const wlLink = document.getElementById('accountWishlist');
    if (wlLink) wlLink.addEventListener('click', (e) => { e.preventDefault(); openWishlist(); acDropdown.classList.remove('open'); });

    // Dynamic user name in header
    const userRaw = localStorage.getItem('tmm_user');
    const isGuest = localStorage.getItem('tmm_guest') === 'true';
    const acLabel = document.getElementById('accountLabel');
    const acAvatar = document.getElementById('accountAvatarIcon');
    const acAuthArea = document.getElementById('accountAuthArea');
    if (userRaw && !isGuest) {
      if (acAuthArea) {
        acAuthArea.innerHTML = `<button class="auth-btn" id="btnLogout" style="width:100%; border:1px solid var(--border); padding:10px; border-radius:var(--radius-sm); font-weight:600;">Sign Out</button>`;
        document.getElementById('btnLogout').addEventListener('click', () => {
          localStorage.removeItem('tmm_user');
          localStorage.removeItem('tmm_session');
          location.reload();
        });
      }
      try {
        const user = JSON.parse(userRaw);
        const meta = user.user_metadata || {};
        const fullName = meta.full_name || meta.name || meta.preferred_username || user.email?.split('@')[0] || 'User';
        const firstName = fullName.split(' ')[0];
        if (acLabel) acLabel.textContent = firstName;
        if (acAvatar) {
          const initials = fullName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
          acAvatar.innerHTML = `<span style="font-size:12px;font-weight:800;font-family:var(--font-display,sans-serif)">${initials}</span>`;
        }
      } catch { }
    } else {
      if (acLabel) acLabel.textContent = 'Guest';
    }
  }
  initNavIndicator();
  showSkeleton();
  try { await fetchAll(); }
  catch (err) { console.warn('Backend offline — fallback data', err); pages = FALLBACK_PAGE_CARDS; productCards = FALLBACK_PRODUCT_CARDS; }

  // Populate hero + ticker with real data
  populateHero();
  populateTicker();

  const urlParams = new URLSearchParams(window.location.search);
  const pageParam = urlParams.get('page') || urlParams.get('cat');
  if (pageParam) {
    activeCategory = pageParam;
    await loadPageProducts(pageParam);
  } else {
    hideSkeleton(); showPages();
  }

  grid().classList.toggle('list-view', viewMode === 'list');
  injectRecentSearches();
}

init();
