'use strict';

/* ══════════════════════════════════════════
   CONSTANTS
══════════════════════════════════════════ */
const PAGE_SIZE = 100;
const TRIGGER_OFFSET = 400;
const TOAST_MS = 3000;
const COMPETITORS = ['강남언니', '여신티켓'];

const ESC_MAP = { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' };
const esc = s => String(s).replace(/[&<>"']/g, c => ESC_MAP[c]);

const CK_LG = `<svg width="11" height="11" viewBox="0 0 13 13" fill="none"><path d="M2 7L5.5 10L11 4.5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ZOOM_SVG = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="5" stroke="white" stroke-width="1.5"/><path d="M11 11L14 14" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>`;

/* ══════════════════════════════════════════
   DATA
══════════════════════════════════════════ */
const PATTERNS = ['필터','리스트','검색','추천/메인','로그인/회원가입','상세정보','리뷰','예약/결제','마이페이지','문의/FAQ','신청/결정','에러/빈화면'];

const FOLDERS = [
  { id:'finance', name:'금융',
    svcs:[
      {l:'토스',bg:'#0064FF',fg:'#fff',ab:'T',n:21},
      {l:'카카오뱅크',bg:'#FFE000',fg:'#333',ab:'K',n:14},
      {l:'네이버페이',bg:'#03C75A',fg:'#fff',ab:'N',n:8},
      {l:'뱅크샐러드',bg:'#845EF7',fg:'#fff',ab:'B',n:6},
    ] },
  { id:'health', name:'건강 및 피트니스',
    svcs:[
      {l:'강남언니',bg:'#FF4E8B',fg:'#fff',ab:'강',n:21, competitor:true},
      {l:'여신티켓',bg:'#FF1493',fg:'#fff',ab:'여',n:15, competitor:true},
      {l:'바비톡',bg:'#FF8C00',fg:'#fff',ab:'바',n:11},
      {l:'눔',bg:'#F04E23',fg:'#fff',ab:'눔',n:5},
    ] },
  { id:'commerce', name:'쇼핑',
    svcs:[
      {l:'쿠팡',bg:'#FF4500',fg:'#fff',ab:'C',n:7},
      {l:'배민',bg:'#2AC1BC',fg:'#fff',ab:'B',n:13},
      {l:'올리브영',bg:'#008000',fg:'#fff',ab:'O',n:5},
      {l:'무신사',bg:'#222',fg:'#fff',ab:'M',n:11},
      {l:'당근마켓',bg:'#FF6F0F',fg:'#fff',ab:'당',n:9},
    ] },
  { id:'lifestyle', name:'라이프스타일',
    svcs:[
      {l:'야놀자',bg:'#FF0081',fg:'#fff',ab:'야',n:6},
      {l:'여기어때',bg:'#E3007C',fg:'#fff',ab:'여',n:4},
      {l:'오늘의집',bg:'#54C1C4',fg:'#fff',ab:'오',n:7},
    ] },
  { id:'social', name:'소셜 네트워킹',
    svcs:[
      {l:'카카오톡',bg:'#FFE000',fg:'#333',ab:'K',n:9},
      {l:'라인',bg:'#00B900',fg:'#fff',ab:'L',n:5},
    ] },
];

const SVC_DATES = {
  '토스':['2026.04','2026.02','2025.12'], '카카오뱅크':['2026.04','2026.01'],
  '네이버페이':['2026.04'], '뱅크샐러드':['2026.03','2025.11'],
  '강남언니':['2026.04','2026.02','2025.12','2025.09'],
  '여신티켓':['2026.03','2026.01','2025.10'],
  '바비톡':['2026.04','2026.02'], '눔':['2026.04'],
  '쿠팡':['2026.04'], '배민':['2026.04','2026.03'], '올리브영':['2026.04'],
  '무신사':['2026.04','2026.01'], '당근마켓':['2026.04'],
  '야놀자':['2026.04','2025.12'], '여기어때':['2026.04'],
  '오늘의집':['2026.04','2026.02'], '카카오톡':['2026.04'], '라인':['2026.04'],
};

/* Derived lookups (모두 init 시 1회 생성) */
const ALL_SVCS = FOLDERS.flatMap(f => f.svcs);
const CAT_MAP = new Map(FOLDERS.map(f => [f.id, f]));
const CAT_SVC_SET = new Map(FOLDERS.map(f => [f.id, new Set(f.svcs.map(s => s.l))]));
const CAT_HAS_COMPETITOR = new Map(
  FOLDERS.map(f => [f.id, f.svcs.some(s => COMPETITORS.includes(s.l))])
);

/* Pre-computed logo HTML (서비스 한 번씩만 생성) */
ALL_SVCS.forEach(s => {
  s._logo   = `<span class="logo" style="background:${s.bg};color:${s.fg};">${s.ab}</span>`;
  s._icLogo = `<span class="ic-logo" style="background:${s.bg};color:${s.fg};">${s.ab}</span>`;
});

const THUMBS = (() => {
  const W = 81, H = 108, fg = '#B0B0B0';
  const wrap = inn =>
    'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
      `<rect width="${W}" height="${H}" fill="#E0E0E0"/>${inn}</svg>`
    );
  return [
    wrap(`<rect x="8" y="8" width="44" height="7" rx="3.5" fill="${fg}" opacity=".7"/>${[28,43,58,73].map(y=>`<circle cx="16" cy="${y+4}" r="5.5" fill="${fg}" opacity=".5"/><rect x="28" y="${y}" width="32" height="5" rx="2.5" fill="${fg}" opacity=".6"/><rect x="28" y="${y+8}" width="20" height="4" rx="2" fill="${fg}" opacity=".4"/>`).join('')}`),
    wrap(`<rect x="8" y="8" width="38" height="7" rx="3.5" fill="${fg}" opacity=".7"/><rect x="8" y="20" width="${W-16}" height="36" rx="6" fill="${fg}" opacity=".4"/><rect x="8" y="62" width="27" height="36" rx="5" fill="${fg}" opacity=".35"/><rect x="46" y="62" width="27" height="36" rx="5" fill="${fg}" opacity=".35"/>`),
    wrap(`<rect x="0" y="0" width="${W}" height="42" fill="${fg}" opacity=".4"/><rect x="8" y="50" width="44" height="7" rx="3.5" fill="${fg}" opacity=".7"/><rect x="8" y="69" width="${W-16}" height="10" rx="5" fill="${fg}" opacity=".3"/><rect x="8" y="83" width="${W-16}" height="12" rx="6" fill="${fg}" opacity=".5"/>`),
    wrap(`<rect x="8" y="8" width="${W-16}" height="10" rx="5" fill="${fg}" opacity=".35"/>${[36,50,64,78].map(y=>`<rect x="8" y="${y}" width="${W-16}" height="10" rx="5" fill="${fg}" opacity=".3"/><rect x="16" y="${y+3}" width="24" height="4" rx="2" fill="${fg}" opacity=".55"/>`).join('')}`),
    wrap(`<circle cx="${W>>1}" cy="22" r="13" fill="${fg}" opacity=".5"/><rect x="${(W>>1)-15}" y="40" width="30" height="6" rx="3" fill="${fg}" opacity=".6"/>${[68,80,92].map(y=>`<rect x="8" y="${y}" width="${W-16}" height="9" rx="4.5" fill="${fg}" opacity=".28"/><rect x="14" y="${y+2}" width="20" height="4" rx="2" fill="${fg}" opacity=".5"/>`).join('')}`),
    wrap(`<rect x="8" y="8" width="36" height="7" rx="3.5" fill="${fg}" opacity=".7"/>${[22,42,62].map(y=>`<rect x="8" y="${y}" width="16" height="4" rx="2" fill="${fg}" opacity=".5"/><rect x="8" y="${y+6}" width="${W-16}" height="11" rx="5.5" fill="${fg}" opacity=".3"/>`).join('')}<rect x="8" y="88" width="${W-16}" height="13" rx="6.5" fill="${fg}" opacity=".55"/>`),
  ];
})();

function buildMasterImages() {
  const all = [];
  let uid = 0;
  for (const s of ALL_SVCS) {
    const dates = SVC_DATES[s.l] || [];
    const latestMonth = dates[0] || '2026.04';
    const isComp = !!s.competitor;
    const monthList = isComp ? dates : [latestMonth];
    for (const month of monthList) {
      const isLatest = (month === latestMonth);
      for (let i = 0; i < s.n; i++, uid++) {
        all.push({
          id: `i${uid}`, svc: s.l, s: s,
          pat: PATTERNS[uid % PATTERNS.length],
          th: THUMBS[uid % 6],
          month, isLatest, isHistory: isComp && !isLatest,
        });
      }
    }
  }
  return all;
}
const MASTER_IMGS = buildMasterImages();
const MASTER_IMGS_MAP = new Map(MASTER_IMGS.map(i => [i.id, i]));

/* ══════════════════════════════════════════
   STATE
══════════════════════════════════════════ */
const S = {
  filters: {
    pat: new Set(),                // 선택된 ui_pattern (Set, 빈 Set = 전체)
    cat: '__all__',                // 활성 카테고리 ('__all__' | folder id)
    svcByCat: new Map(),           // 카테고리별 단일 선택 (Set<string>, max size 1)
  },
  historyOn: false,
  imgSel: new Set(),               // 선택된 이미지 id
  loaded: 0,                       // 현재까지 그리드에 그려진 이미지 수
  filteredIds: [],                 // 현재 필터 결과 id 목록 (순서 보존)
  modal: { open: false, idx: 0 },
};

/* Module-scoped caches (빈번 참조) */
let _filteredImgs = [];            // 현재 필터 결과 (객체 배열)
let _cardMap = new Map();          // img id → 카드 DOM
let _groupMap = new Map();         // pat → { pg, grid, count, total } 그룹 컨테이너 참조
let _toastTmr = null;
let _io = null;
let _loadingNext = false;          // 무한 스크롤 중복 트리거 방지
let _prevFocus = null;             // 모달 열기 전 포커스 복원용

/* ══════════════════════════════════════════
   DOM
══════════════════════════════════════════ */
const $ = id => document.getElementById(id);
const D = {
  plugin: document.body, resizeGrip: $('resize-grip'),
  fc: $('fc'), patAll: $('pat-all'),
  tb: $('tb'),
  sc: $('sc'), svcAll: $('svc-all'), svcRow: $('svc-row'),
  sbCount: $('sb-count'), sbHistory: $('sb-history'), sbSwitch: $('sb-switch'),
  grid: $('grid'), gridContent: $('grid-content'),
  sentinel: $('sentinel'), loadMore: $('load-more'),
  ctaReset: $('cta-reset'), ctaAdd: $('cta-add'),
  modal: $('modal'), mLogo: $('m-logo'), mSvc: $('m-svc'), mPat: $('m-pat'), mMonth: $('m-month'),
  mClose: $('m-close'), mPrev: $('m-prev'), mNext: $('m-next'),
  mImg: $('m-img'), mPos: $('m-pos'), mSelect: $('m-select'),
  toast: $('toast'), toastN: $('toast-n'),
};

/* ══════════════════════════════════════════
   HELPERS
══════════════════════════════════════════ */
const getCatSvc = cid => S.filters.svcByCat.get(cid) || null;

const ensureCatSvc = cid => {
  let set = S.filters.svcByCat.get(cid);
  if (!set) { set = new Set(); S.filters.svcByCat.set(cid, set); }
  return set;
};

/* 활성 탭 기준으로 경쟁사 포함 여부 */
function hasCompetitorInActive() {
  const cat = S.filters.cat;
  if (cat === '__all__') return true;
  const svcs = getCatSvc(cat);
  if (!svcs || !svcs.size) return CAT_HAS_COMPETITOR.get(cat) || false;
  for (const l of svcs) if (COMPETITORS.includes(l)) return true;
  return false;
}

/* ══════════════════════════════════════════
   FILTER
══════════════════════════════════════════ */
function filterImages() {
  const { pat, cat } = S.filters;
  const histOn = S.historyOn;
  const patActive = pat.size > 0;

  let allowed = null;  // null = 서비스 필터 없음
  if (cat !== '__all__') {
    const svcs = getCatSvc(cat);
    allowed = (svcs && svcs.size) ? svcs : CAT_SVC_SET.get(cat);
  }

  const out = [];
  for (let i = 0, n = MASTER_IMGS.length; i < n; i++) {
    const img = MASTER_IMGS[i];
    if (!histOn && img.isHistory) continue;
    if (patActive && !pat.has(img.pat)) continue;
    if (allowed && !allowed.has(img.svc)) continue;
    out.push(img);
  }
  return out;
}

function togglePat(val) {
  const s = S.filters.pat;
  if (val === '__all__') s.clear();
  else s.has(val) ? s.delete(val) : s.add(val);
}

function selectCat(cid) {
  S.filters.cat = cid;
}

function toggleSvc(val) {
  const cid = S.filters.cat;
  if (cid === '__all__') return;
  const svcs = ensureCatSvc(cid);
  if (val === '__all__') svcs.clear();
  else if (svcs.has(val)) svcs.delete(val);
  else { svcs.clear(); svcs.add(val); }
}

function applyFilter(type, val) {
  if (type === 'pat') togglePat(val);
  else if (type === 'cat') selectCat(val);
  else if (type === 'svc') toggleSvc(val);
  renderAllFilters();
  syncHistoryEnabled();
  rebuildGrid();
  if (type === 'cat') scrollActiveTabIntoView();
}

function scrollActiveTabIntoView() {
  const sel = D.tb.querySelector('[aria-selected="true"]');
  if (sel) sel.scrollIntoView({ inline:'center', behavior:'smooth', block:'nearest' });
}

/* ══════════════════════════════════════════
   RENDER FILTERS
══════════════════════════════════════════ */
function renderAllFilters() {
  renderPatFilter();
  renderCatFilter();
  renderSvcFilter();
}

function renderPatFilter() {
  D.patAll.setAttribute('aria-pressed', String(S.filters.pat.size === 0));
  const patSet = S.filters.pat;
  D.fc.innerHTML = PATTERNS.map(p =>
    `<button class="chip txt" aria-pressed="${patSet.has(p)}" data-type="pat" data-v="${esc(p)}">${esc(p)}</button>`
  ).join('');
}

function renderCatFilter() {
  const cat = S.filters.cat;
  let html = `<button class="tab" role="tab" aria-selected="${cat==='__all__'}" data-type="cat" data-v="__all__">전체</button>`;
  for (const f of FOLDERS) {
    html += `<button class="tab" role="tab" aria-selected="${cat===f.id}" data-type="cat" data-v="${esc(f.id)}">${esc(f.name)}</button>`;
  }
  D.tb.innerHTML = html;
}

function renderSvcFilter() {
  const cid = S.filters.cat;
  if (cid === '__all__') { D.svcRow.style.display = 'none'; return; }
  const f = CAT_MAP.get(cid);
  if (!f) { D.svcRow.style.display = 'none'; return; }
  D.svcRow.style.display = 'flex';
  const svcs = getCatSvc(cid);
  const activeLabel = svcs && svcs.size ? [...svcs][0] : null;
  D.svcAll.setAttribute('aria-pressed', String(!activeLabel));
  D.sc.innerHTML = f.svcs.map(s =>
    `<button class="chip" aria-pressed="${s.l === activeLabel}" data-type="svc" data-v="${esc(s.l)}">${s._logo}${esc(s.l)}</button>`
  ).join('');
}

/* ══════════════════════════════════════════
   STATUS BAR
══════════════════════════════════════════ */
function syncHistoryEnabled() {
  const enabled = hasCompetitorInActive();
  D.sbHistory.classList.toggle('disabled', !enabled);
  if (!enabled && S.historyOn) {
    S.historyOn = false;
    D.sbSwitch.classList.remove('on');
    D.sbHistory.setAttribute('aria-checked', 'false');
  }
}

function syncStatus() {
  D.sbCount.innerHTML = `조회화면: <b>${S.filteredIds.length}</b>개`;
  D.sbSwitch.classList.toggle('on', S.historyOn);
  D.sbHistory.setAttribute('aria-checked', String(S.historyOn));
}

function syncCtaAdd() {
  const n = S.imgSel.size;
  D.ctaAdd.disabled = !n;
  D.ctaAdd.textContent = n ? `${n}개 피그마에 추가` : '화면을 선택해 주세요';
}

/* ══════════════════════════════════════════
   CARD HTML
══════════════════════════════════════════ */
function cardHtml(img) {
  const on = S.imgSel.has(img.id);
  const monthBadge = img.isHistory ? `<span class="ic-month">${esc(img.month)}</span>` : '';
  return `<div class="ic${on?' on':''}" data-id="${img.id}" tabindex="0" role="button" aria-pressed="${on}">
    <div class="ic-th">
      <img src="${img.th}" alt="${esc(img.pat)}" loading="lazy">
      ${monthBadge}
      ${img.s._icLogo}
      <button class="ic-zoom" data-action="zoom" data-id="${img.id}" aria-label="확대">${ZOOM_SVG}</button>
      <span class="ic-ck">${CK_LG}</span>
    </div>
  </div>`;
}

/* ══════════════════════════════════════════
   GRID — 그룹 컨테이너 사전 생성 + 증분 append
══════════════════════════════════════════ */
function rebuildGrid() {
  _filteredImgs = filterImages();
  S.filteredIds = _filteredImgs.map(i => i.id);
  S.loaded = 0;
  _cardMap.clear();
  _groupMap.clear();
  D.gridContent.innerHTML = '';

  if (!_filteredImgs.length) {
    renderEmpty();
    D.loadMore.style.display = 'none';
  } else {
    setupGroupContainers();
    appendNextPage();
  }
  syncStatus();
  syncCtaAdd();
}

/* 필터된 이미지들의 pat 집합을 PATTERNS 순서로 정렬해서 빈 그룹 컨테이너 생성 */
function setupGroupContainers() {
  const patternSet = new Set();
  for (const img of _filteredImgs) patternSet.add(img.pat);
  const ordered = PATTERNS.filter(p => patternSet.has(p));

  let html = '';
  for (let i = 0, n = ordered.length; i < n; i++) {
    if (i > 0) html += `<div class="pdiv"></div>`;
    const pat = ordered[i];
    html += `<div class="pg" data-pat="${esc(pat)}">
      <div class="ph"><span class="pt">${esc(pat)}</span><span class="pc">(0)</span></div>
      <div class="pgrid"></div>
    </div>`;
  }
  D.gridContent.innerHTML = html;

  const pgs = D.gridContent.querySelectorAll('.pg[data-pat]');
  for (const pg of pgs) {
    _groupMap.set(pg.dataset.pat, {
      pg,
      grid: pg.querySelector('.pgrid'),
      count: pg.querySelector('.pc'),
      total: 0,
    });
  }
}

/* 다음 페이지 만큼을 기존 그룹에 증분 append */
function appendNextPage() {
  if (_loadingNext) return;
  if (S.loaded >= _filteredImgs.length) {
    D.loadMore.style.display = 'none';
    return;
  }
  _loadingNext = true;

  const start = S.loaded;
  const end = Math.min(start + PAGE_SIZE, _filteredImgs.length);

  // 이번 페이지 범위 내에서 패턴별 그룹핑 (Map은 삽입 순서 보존)
  const byPat = new Map();
  for (let i = start; i < end; i++) {
    const img = _filteredImgs[i];
    const arr = byPat.get(img.pat);
    if (arr) arr.push(img);
    else byPat.set(img.pat, [img]);
  }

  byPat.forEach((imgs, pat) => {
    const g = _groupMap.get(pat);
    if (!g) return;
    const beforeCount = g.grid.children.length;
    g.grid.insertAdjacentHTML('beforeend', imgs.map(cardHtml).join(''));
    // 방금 추가된 카드만 _cardMap에 등록 (O(1) per card)
    for (let i = 0; i < imgs.length; i++) {
      const c = g.grid.children[beforeCount + i];
      _cardMap.set(imgs[i].id, c);
    }
    g.total += imgs.length;
    g.count.textContent = `(${g.total})`;
  });

  S.loaded = end;
  D.loadMore.style.display = S.loaded < _filteredImgs.length ? 'flex' : 'none';
  _loadingNext = false;
}

function renderEmpty() {
  D.gridContent.innerHTML = `<div class="empty">
    <div class="empty-em">🔍</div>
    <p class="empty-t">조건에 맞는 화면이 없어요</p>
    <button class="empty-btn" id="reset-filters">필터 초기화</button>
  </div>`;
}

function setupObserver() {
  if (_io) _io.disconnect();
  _io = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting) return;
    appendNextPage();
  }, { root: D.grid, rootMargin: `${TRIGGER_OFFSET}px 0px` });
  _io.observe(D.sentinel);
}

/* ══════════════════════════════════════════
   SELECTION
══════════════════════════════════════════ */
function toggleCard(id) {
  const nowOn = !S.imgSel.has(id);
  nowOn ? S.imgSel.add(id) : S.imgSel.delete(id);
  const card = _cardMap.get(id);
  if (card) {
    card.classList.add('tap');
    setTimeout(() => card.classList.remove('tap'), 120);
    card.classList.toggle('on', nowOn);
    card.setAttribute('aria-pressed', String(nowOn));
  }
  syncCtaAdd();
}

function doReset() {
  S.filters.pat.clear();
  S.filters.cat = '__all__';
  S.filters.svcByCat.clear();
  S.historyOn = false;
  S.imgSel.clear();
  renderAllFilters();
  syncHistoryEnabled();
  rebuildGrid();
}

function doAdd() {
  const n = S.imgSel.size;
  if (!n) return;
  const ids = [...S.imgSel];
  parent.postMessage({ pluginMessage: { type: 'add-images', payload: { ids } } }, '*');
  S.imgSel.clear();
  _cardMap.forEach(card => {
    card.classList.remove('on');
    card.setAttribute('aria-pressed', 'false');
  });
  showToast(n);
  syncCtaAdd();
}

function showToast(n) {
  const prev = D.toastN.textContent;
  D.toastN.textContent = n;
  D.toast.classList.add('show');
  if (prev !== String(n)) {
    D.toast.classList.remove('pulse');
    // requestAnimationFrame으로 애니메이션 리스타트 (void offsetWidth 대신)
    requestAnimationFrame(() => {
      requestAnimationFrame(() => D.toast.classList.add('pulse'));
    });
  }
  clearTimeout(_toastTmr);
  _toastTmr = setTimeout(() => {
    D.toast.classList.remove('show');
    D.toast.classList.remove('pulse');
  }, TOAST_MS);
}

/* ══════════════════════════════════════════
   MODAL
══════════════════════════════════════════ */
function openModal(id) {
  const idx = S.filteredIds.indexOf(id);
  if (idx < 0) return;
  _prevFocus = document.activeElement;
  S.modal.open = true;
  S.modal.idx = idx;
  renderModal();
  D.modal.classList.add('show');
  // rAF 2회로 display 전환 후 포커스 이동 보장
  requestAnimationFrame(() => requestAnimationFrame(() => D.mClose.focus()));
}

function closeModal() {
  if (!S.modal.open) return;
  S.modal.open = false;
  D.modal.classList.remove('show');
  if (_prevFocus && typeof _prevFocus.focus === 'function') {
    try { _prevFocus.focus(); } catch (_) { /* DOM에서 제거됨 */ }
  }
  _prevFocus = null;
}

function navModal(delta) {
  const next = S.modal.idx + delta;
  if (next < 0 || next >= S.filteredIds.length) return;
  S.modal.idx = next;
  renderModal();
}

function renderModal() {
  const id = S.filteredIds[S.modal.idx];
  const img = MASTER_IMGS_MAP.get(id);
  if (!img) return;

  D.mLogo.innerHTML = img.s._logo;
  D.mSvc.textContent = img.svc;
  D.mPat.textContent = img.pat;
  if (img.isHistory) {
    D.mMonth.textContent = img.month;
    D.mMonth.style.display = 'inline-block';
  } else {
    D.mMonth.style.display = 'none';
  }

  // 이미지 fade 전환
  if (D.mImg.src && D.mImg.getAttribute('src') !== img.th) {
    D.mImg.style.opacity = '0';
    // 다음 프레임에 src 교체 후 opacity 복귀 (더블 rAF로 브라우저 페인트 간격 보장)
    requestAnimationFrame(() => {
      D.mImg.src = img.th;
      D.mImg.alt = img.pat;
      requestAnimationFrame(() => { D.mImg.style.opacity = '1'; });
    });
  } else {
    D.mImg.src = img.th;
    D.mImg.alt = img.pat;
    D.mImg.style.opacity = '1';
  }

  D.mPos.textContent = `${S.modal.idx + 1} / ${S.filteredIds.length}`;
  D.mPrev.disabled = S.modal.idx === 0;
  D.mNext.disabled = S.modal.idx === S.filteredIds.length - 1;
  const selected = S.imgSel.has(id);
  D.mSelect.classList.toggle('on', selected);
  D.mSelect.textContent = selected ? '✓ 선택됨' : '선택';
}

function toggleModalSelect() {
  const id = S.filteredIds[S.modal.idx];
  if (!id) return;
  toggleCard(id);
  renderModal();
}

/* ══════════════════════════════════════════
   EVENTS
══════════════════════════════════════════ */
function handleFilterClick(e) {
  const el = e.target.closest('[data-type][data-v]');
  if (!el) return;
  applyFilter(el.dataset.type, el.dataset.v);
}
D.fc.addEventListener('click', handleFilterClick);
D.tb.addEventListener('click', handleFilterClick);
D.sc.addEventListener('click', handleFilterClick);
D.patAll.addEventListener('click', handleFilterClick);
D.svcAll.addEventListener('click', handleFilterClick);

D.sbHistory.addEventListener('click', () => {
  if (D.sbHistory.classList.contains('disabled')) return;
  S.historyOn = !S.historyOn;
  D.sbSwitch.classList.toggle('on', S.historyOn);
  D.sbHistory.setAttribute('aria-checked', String(S.historyOn));
  rebuildGrid();
});
D.sbHistory.addEventListener('keydown', e => {
  if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault();
    D.sbHistory.click();
  }
});

D.gridContent.addEventListener('click', e => {
  if (e.target.closest('#reset-filters')) { doReset(); return; }
  const zoomBtn = e.target.closest('[data-action="zoom"]');
  if (zoomBtn) {
    e.stopPropagation();
    openModal(zoomBtn.dataset.id);
    return;
  }
  const card = e.target.closest('.ic[data-id]');
  if (card) toggleCard(card.dataset.id);
});

D.ctaReset.addEventListener('click', doReset);
D.ctaAdd.addEventListener('click', doAdd);

D.mClose.addEventListener('click', closeModal);
D.mPrev.addEventListener('click', () => navModal(-1));
D.mNext.addEventListener('click', () => navModal(1));
D.mSelect.addEventListener('click', toggleModalSelect);
D.modal.addEventListener('click', e => { if (e.target === D.modal) closeModal(); });

/* 전역 키보드 */
document.addEventListener('keydown', e => {
  if (S.modal.open) {
    if (e.key === 'Escape') { closeModal(); return; }
    if (e.key === 'ArrowLeft')  { navModal(-1); return; }
    if (e.key === 'ArrowRight') { navModal( 1); return; }
    if (e.key === ' ' || e.key === 'Enter') {
      // 모달 내부 버튼에 포커스되어 있으면 기본 동작
      const a = document.activeElement;
      if (!a || a.tagName !== 'BUTTON') {
        e.preventDefault();
        toggleModalSelect();
      }
      return;
    }
    if (e.key === 'Tab') {
      const focusables = D.modal.querySelectorAll('button:not([disabled])');
      if (!focusables.length) return;
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    return;
  }
  // 모달 외 - 카드 포커스 상태에서 Enter/Space
  const a = document.activeElement;
  if (a && a.classList && a.classList.contains('ic') && a.dataset.id) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleCard(a.dataset.id);
    }
  }
});

/* ══════════════════════════════════════════
   RESIZE GRIP
══════════════════════════════════════════ */
const MIN_H = 400, MAX_H = 700;
D.resizeGrip.addEventListener('mousedown', e => {
  e.preventDefault();
  D.resizeGrip.classList.add('dragging');
  document.body.style.userSelect = 'none';
  document.body.style.cursor = 'ns-resize';
  const startY = e.clientY;
  const startH = window.innerHeight;
  const onMove = ev => {
    const delta = ev.clientY - startY;
    const newH = Math.max(MIN_H, Math.min(MAX_H, startH + delta));
    parent.postMessage({ pluginMessage: { type: 'resize', payload: { height: newH } } }, '*');
  };
  const onUp = () => {
    D.resizeGrip.classList.remove('dragging');
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
});

/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */
renderAllFilters();
syncHistoryEnabled();
rebuildGrid();
setupObserver();
