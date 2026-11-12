/* ============================================================
   《全英雄使用指南》交互脚本
   依赖：window.GUIDE_DATA（guide/data/heroes.js）
   功能：双主题 / 网格-清单双视图 / 交叉筛选 / 详情抽屉 / 打印
   ============================================================ */
(function () {
  'use strict';

  var GUIDE = window.GUIDE_DATA || [];
  if (!GUIDE.length) return;

  var GUIDE_BY_NAME = {};
  GUIDE.forEach(function (g) { GUIDE_BY_NAME[g.n] = g; });

  /* ---------- 主题 ---------- */
  var THEME_KEY = 'hok.theme';
  var VIEW_KEY = 'hok.view';
  var THEME_DARK = 'dark';
  var THEME_LIGHT = 'light';

  function getTheme() {
    try { return localStorage.getItem(THEME_KEY) || THEME_DARK; } catch (e) { return THEME_DARK; }
  }
  function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
    var b = document.getElementById('theme-toggle');
    if (b) {
      b.textContent = t === THEME_LIGHT ? '🌙 深色' : '☀️ 浅色';
      b.setAttribute('aria-label', t === THEME_LIGHT ? '切换到深色主题' : '切换到浅色主题');
      b.title = t === THEME_LIGHT ? '切换到深色国风主题' : '切换到浅色资料手册主题';
    }
  }
  function toggleTheme() {
    setTheme(getTheme() === THEME_LIGHT ? THEME_DARK : THEME_LIGHT);
  }

  /* ---------- 筛选状态 ---------- */
  var state = {
    view: 'grid',
    role: '',
    diff: '',
    tag: '',
    lane: 'all',
    q: ''
  };
  try { state.view = localStorage.getItem(VIEW_KEY) || 'grid'; } catch (e) {}

  /* ---------- 工具条 ---------- */
  function buildToolbar() {
    var host = document.getElementById('guide-toolbar');
    if (!host) return;
    var roles = [];
    var diffs = [];
    var tags = [];
    GUIDE.forEach(function (g) {
      if (roles.indexOf(g.role) < 0) roles.push(g.role);
      if (diffs.indexOf(g.diff) < 0) diffs.push(g.diff);
      (g.tags || []).forEach(function (t) { if (tags.indexOf(t) < 0) tags.push(t); });
    });
    roles.sort();
    var order = { '易': 0, '中': 1, '难': 2, '极难': 3 };
    diffs.sort(function (a, b) { return order[a] - order[b]; });
    tags.sort();

    function opts(list, cur, label) {
      var h = '<option value="">' + label + '</option>';
      list.forEach(function (v) {
        h += '<option value="' + v + '"' + (v === cur ? ' selected' : '') + '>' + v + '</option>';
      });
      return h;
    }

    host.innerHTML =
      '<div class="gt-group">' +
      '<select id="gt-role" class="gt-select" aria-label="按职业筛选">' + opts(roles, state.role, '全部职业') + '</select>' +
      '<select id="gt-diff" class="gt-select" aria-label="按难度筛选">' + opts(diffs, state.diff, '全部难度') + '</select>' +
      '<select id="gt-tag" class="gt-select" aria-label="按标签筛选">' + opts(tags, state.tag, '全部标签') + '</select>' +
      '</div>' +
      '<div class="gt-group">' +
      '<span class="gt-count">匹配 <b id="gt-count">0</b> 位英雄</span>' +
      '<span class="gt-sep"></span>' +
      '<button id="gt-view-grid" class="gt-btn' + (state.view === 'grid' ? ' active' : '') + '">▦ 网格</button>' +
      '<button id="gt-view-list" class="gt-btn' + (state.view === 'list' ? ' active' : '') + '">☰ 清单</button>' +
      '<button id="gt-reset" class="gt-btn ghost">重置</button>' +
      '<button id="theme-toggle" class="gt-btn ghost">☀️ 浅色</button>' +
      '<button id="gt-print" class="gt-btn ghost">🖨 打印</button>' +
      '</div>';

    host.querySelector('#gt-role').onchange = function () { state.role = this.value; applyFilter(); };
    host.querySelector('#gt-diff').onchange = function () { state.diff = this.value; applyFilter(); };
    host.querySelector('#gt-tag').onchange = function () { state.tag = this.value; applyFilter(); };
    host.querySelector('#gt-view-grid').onclick = function () { setView('grid'); };
    host.querySelector('#gt-view-list').onclick = function () { setView('list'); };
    host.querySelector('#gt-reset').onclick = function () {
      state.role = ''; state.diff = ''; state.tag = ''; state.q = '';
      var s = document.getElementById('search'); if (s) { s.value = ''; }
      var lb = document.querySelector('.nav-btn.active');
      state.lane = lb ? lb.dataset.lane : 'all';
      buildToolbar();
      applyFilter();
    };
    host.querySelector('#theme-toggle').onclick = toggleTheme;
    host.querySelector('#gt-print').onclick = function () { window.print(); };

    setTheme(getTheme());
  }

  /* ---------- 视图切换 ---------- */
  function setView(v) {
    state.view = v;
    try { localStorage.setItem(VIEW_KEY, v); } catch (e) {}
    var g = document.getElementById('gt-view-grid');
    var l = document.getElementById('gt-view-list');
    if (g) g.classList.toggle('active', v === 'grid');
    if (l) l.classList.toggle('active', v === 'list');
    document.body.setAttribute('data-gt-view', v);
    renderView();
  }

  /* ---------- 过滤 ---------- */
  function match(g) {
    if (state.lane && state.lane !== 'all' && g.lane !== state.lane) return false;
    if (state.role && g.role !== state.role) return false;
    if (state.diff && g.diff !== state.diff) return false;
    if (state.tag && (g.tags || []).indexOf(state.tag) < 0) return false;
    if (state.q) {
      var q = state.q;
      if (g.n.toLowerCase().indexOf(q) < 0 &&
          (g.feat || '').toLowerCase().indexOf(q) < 0 &&
          (g.tags || []).join(' ').toLowerCase().indexOf(q) < 0) return false;
    }
    return true;
  }

  function applyFilter() {
    var list = GUIDE.filter(match);
    if (state.view === 'list') {
      var c = document.getElementById('gt-count');
      if (c) c.textContent = list.length;
      renderList(list);
      renderEmptyHint(list.length);
    } else {
      var shown = filterGridCards(list);
      var c2 = document.getElementById('gt-count');
      if (c2) c2.textContent = shown;
      renderEmptyHint(shown);
    }
  }

  /* 筛选结果为空时给出明确提示，避免出现空白页 */
  function renderEmptyHint(n) {
    var main = document.getElementById('main');
    if (!main) return;
    var hint = document.getElementById('gt-empty-hint');
    if (n > 0) {
      if (hint) hint.remove();
      return;
    }
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'gt-empty-hint';
      hint.className = 'no-results';
      main.appendChild(hint);
    }
    hint.textContent = '没有符合当前筛选条件的英雄，请放宽职业/难度/标签筛选或点击「重置」。';
  }

  function renderView() {
    var main = document.getElementById('main');
    var listHost = document.getElementById('gt-list');
    if (main) main.style.display = state.view === 'list' ? 'none' : '';
    if (listHost) listHost.style.display = state.view === 'list' ? '' : 'none';
    applyFilter();
  }

  /* ---------- 网格视图：给现有卡片挂指南区块 + 隐藏不匹配卡片 ---------- */
  function filterGridCards(list) {
    var keep = {};
    list.forEach(function (g) { keep[g.n] = true; });
    var cards = document.querySelectorAll('#main .hero-card');
    var shown = 0;
    cards.forEach(function (card) {
      var nameEl = card.querySelector('.hero-name');
      var name = nameEl ? nameEl.textContent.trim() : '';
      var g = GUIDE_BY_NAME[name];
      if (!g) return;
      if (keep[name]) {
        card.style.display = '';
        shown++;
        injectGuide(card, g);
      } else {
        card.style.display = 'none';
      }
    });
    // 分路标题在整路被过滤掉时隐藏
    document.querySelectorAll('#main .lane-section').forEach(function (sec) {
      var visible = sec.querySelectorAll('.hero-card:not([style*="display: none"])').length;
      sec.style.display = visible ? '' : 'none';
    });
    return shown;
  }

  var GUIDE_FIELDS = [
    ['特点', 'feat'],
    ['优势', 'pros'],
    ['弱点', 'cons'],
    ['打法', 'play'],
    ['克制', 'counter'],
    ['被克制', 'weakto']
  ];

  /* ---------- 13 节完整攻略直达链接 ---------- */
  function fullLink(name, inline) {
    var m = (typeof FULL_GUIDES !== 'undefined') ? FULL_GUIDES[name] : null;
    if (!m) return '';
    var cls = inline ? 'hp-full' : 'gb-full';
    return '<a class="' + cls + '" href="guide/full/' + m.file + '" target="_blank" rel="noopener"' +
      (inline ? '' : ' onclick="event.stopPropagation()"') + '>📚 13 节完整攻略</a>';
  }

  function esc(s) {
    return s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function injectGuide(card, g) {
    var body = card.querySelector('.hero-body');
    if (!body) return;
    var old = body.querySelector('.guide-block');
    if (old) old.remove();

    var badges =
      '<span class="gb-badge b-role">' + esc(g.role) + '</span>' +
      '<span class="gb-badge b-diff b-diff-' + esc(g.diff) + '">难度 ' + esc(g.diff) + '</span>' +
      '<span class="gb-badge b-alt">副分路 ' + esc(g.alt) + '</span>';

    var fields = GUIDE_FIELDS.map(function (f) {
      return '<div class="gb-field"><div class="gb-label">' + f[0] + '</div>' +
             '<div class="gb-text">' + esc(g[f[1]]) + '</div></div>';
    }).join('');
    var fieldsHtml = '<div class="gb-fields">' + fields + '</div>';

    var tags = '<div class="gb-tags">' + (g.tags || []).map(function (t) {
      return '<span class="gb-tag">' + esc(t) + '</span>';
    }).join('') + '</div>';

    var html =
      '<div class="guide-block">' +
      '<div class="gb-title">📖 全英雄使用指南<span class="gb-line"></span></div>' +
      '<div class="gb-badges">' + badges + '</div>' +
      fieldsHtml +
      tags +
      '<button class="gb-more" data-guide-more="' + esc(g.n) + '">完整详情</button>' +
      fullLink(g.n) +
      '</div>';

    // 指南放在卡片正文最前面：展开卡片第一眼就是「怎么玩」，而不是滚完技能才看到
    body.insertAdjacentHTML('afterbegin', html);
    var btn = body.querySelector('.gb-more');
    if (btn) {
      btn.onclick = function (e) {
        e.stopPropagation();
        openDrawer(g);
      };
    }
    injectHeadPreview(card, g);
  }

  /* 折叠态在卡片头部显示一句话摘要 + 一键打开完整攻略 */
  function injectHeadPreview(card, g) {
    var head = card.querySelector('.hero-head');
    if (!head) return;
    var old = head.querySelector('.hero-preview');
    if (old) old.remove();
    var preview = document.createElement('div');
    preview.className = 'hero-preview';
    preview.innerHTML =
      '<div class="hp-line"><span class="hp-feat">' + esc(g.feat) + '</span></div>' +
      '<div class="hp-tags">' + (g.tags || []).slice(0, 4).map(function (t) {
        return '<span class="hp-tag">' + esc(t) + '</span>';
      }).join('') +
      '<button class="hp-open" data-guide-open="' + esc(g.n) + '">📖 完整详情</button>' +
      fullLink(g.n, true) + '</div>';
    head.appendChild(preview);
    var btn = preview.querySelector('.hp-open');
    if (btn) {
      btn.onclick = function (e) {
        e.stopPropagation();
        openDrawer(g);
      };
    }
  }

  /* ---------- 清单视图 ---------- */
  function renderList(list) {
    var host = document.getElementById('gt-list');
    if (!host) return;
    if (!list.length) {
      host.innerHTML = '<div class="gt-empty">没有符合当前筛选条件的英雄</div>';
      return;
    }
    var rows = list.map(function (g) {
      return '<tr data-guide-row="' + esc(g.n) + '">' +
        '<td class="c-name">' + esc(g.n) + '</td>' +
        '<td class="c-mini">' + esc(g.lane) + '</td>' +
        '<td class="c-mini">' + esc(g.role) + '</td>' +
        '<td class="c-mini">' + esc(g.diff) + '</td>' +
        '<td class="c-feat">' + esc(g.feat) + '</td>' +
        '<td>' + esc(g.pros) + '</td>' +
        '<td>' + esc(g.cons) + '</td>' +
        '<td>' + esc(g.counter) + ' / ' + esc(g.weakto) + '</td>' +
        '<td class="c-mini">' + (g.tags || []).map(function (t) {
          return '<span class="g-mini-tag">' + esc(t) + '</span>';
        }).join('') + '</td>' +
        '</tr>';
    }).join('');

    host.innerHTML =
      '<div class="gt-table-wrap"><table class="gt-table"><thead><tr>' +
      '<th>英雄</th><th>分路</th><th>职业</th><th>难度</th><th>特点</th>' +
      '<th>优势</th><th>弱点</th><th>克制 / 被克</th><th>标签</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';

    host.querySelectorAll('tr[data-guide-row]').forEach(function (tr) {
      tr.style.cursor = 'pointer';
      tr.onclick = function () { openDrawer(GUIDE_BY_NAME[tr.dataset.guideRow]); };
    });
  }

  /* ---------- 详情抽屉 ---------- */
  function ensureDrawer() {
    if (document.getElementById('gt-drawer')) return;
    var mask = document.createElement('div');
    mask.className = 'gt-drawer-mask';
    mask.id = 'gt-drawer-mask';
    var dr = document.createElement('div');
    dr.className = 'gt-drawer';
    dr.id = 'gt-drawer';
    dr.setAttribute('role', 'dialog');
    dr.setAttribute('aria-modal', 'true');
    dr.innerHTML =
      '<div class="gt-drawer-head">' +
      '<div class="gt-drawer-avatar" id="gt-d-avatar"></div>' +
      '<div><div class="gt-drawer-name" id="gt-d-name"></div>' +
      '<div class="gt-drawer-sub" id="gt-d-sub"></div></div>' +
      '<button class="gt-drawer-close" id="gt-d-close" aria-label="关闭">✕</button>' +
      '</div>' +
      '<div class="gt-drawer-body" id="gt-d-body"></div>';
    document.body.appendChild(mask);
    document.body.appendChild(dr);
    mask.onclick = closeDrawer;
    document.getElementById('gt-d-close').onclick = closeDrawer;
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrawer();
    });
  }

  function openDrawer(g) {
    if (!g) return;
    ensureDrawer();
    var hero = null;
    var all = (typeof HEROES !== 'undefined') ? HEROES : [];
    all.forEach(function (h) { if (h.cname === g.n) hero = h; });

    var av = document.getElementById('gt-d-avatar');
    if (hero && hero.eid) {
      av.innerHTML = '<span class="av-fallback">' + esc(g.n[0]) + '</span>' +
        '<img src="https://game.gtimg.cn/images/yxzj/img201606/heroimg/' +
        hero.eid + '/' + hero.eid + '.jpg" alt="' + esc(g.n) + '" onerror="this.style.display=\'none\'">';
    } else {
      av.innerHTML = '<span class="av-fallback">' + esc(g.n[0]) + '</span>';
    }
    document.getElementById('gt-d-name').textContent = g.n;
    document.getElementById('gt-d-sub').textContent =
      g.lane + ' · ' + g.role + ' · 难度 ' + g.diff + ' · 副分路 ' + g.alt;

    var body = document.getElementById('gt-d-body');
    // 指南六项平铺进一个网格区块，一眼看完，不用逐段下滑
    var f = '<div class="section"><div class="sec-title">使用指南</div>' +
      '<div class="gb-fields">' +
      GUIDE_FIELDS.map(function (x) {
        return '<div class="gb-field"><div class="gb-label">' + x[0] + '</div>' +
          '<div class="gb-text">' + esc(g[x[1]]) + '</div></div>';
      }).join('') +
      '</div></div>';

    var extra = '';
    if (hero) {
      var skills = (hero.skills || []).map(function (s, i) {
        return '<div class="skill-row"><div class="skill-badge skill-' + i + '">' +
          '<span style="font-size:11px;font-weight:700">' + (i === 0 ? '被动' : i + '技能') + '</span></div>' +
          '<div class="skill-info"><div class="skill-name">' + esc(s.name) + '</div>' +
          '<div class="skill-desc">' + esc(s.desc) + '</div></div></div>';
      }).join('');
      var combos = (hero.combos || []).map(function (c) {
        if (typeof c === 'object') {
          return '<div class="combo-item"><span class="combo-name">' + esc(c.name) + '</span>' +
            (c.desc ? '<div class="combo-desc">' + esc(c.desc) + '</div>' : '') + '</div>';
        }
        return '<div class="combo-item"><span class="combo-seq">' + esc(c) + '</span></div>';
      }).join('');
      var counters = (hero.counters || []).map(function (x) {
        return '<span class="tag tag-counter">' + esc(x) + '</span>';
      }).join('');
      var countered = (hero.countered_by || []).map(function (x) {
        return '<span class="tag tag-countered">' + esc(x) + '</span>';
      }).join('');
      extra =
        '<div class="section"><div class="sec-title">技能详解</div>' + skills + '</div>' +
        '<div class="section"><div class="sec-title">铭文推荐</div><div class="tips-text">' +
          esc(hero.inscriptions || '宿命×10、虚空×10、调和×10') + '</div></div>' +
        '<div class="section"><div class="sec-title">出装推荐</div>' +
          (hero.equips || []).map(function (e, i) {
            return '<div class="equip-row"><span class="equip-label">方案' + (i + 1) + '</span>' +
              '<span class="equip-items">' + e.map(function (x) {
                return '<span class="equip-tag">' + esc(x) + '</span>';
              }).join('') + '</span></div>';
          }).join('') + '</div>' +
        '<div class="section"><div class="sec-title">连招技巧</div>' + combos + '</div>' +
        '<div class="section"><div class="sec-title">对位关系</div>' +
          '<div class="counter-group"><div class="counter-label">克制:</div>' + (counters || '无') + '</div>' +
          '<div class="counter-group"><div class="counter-label">被克:</div>' + (countered || '无') + '</div></div>' +
        '<div class="section"><div class="sec-title">进阶技巧</div>' +
          (hero.pro_tips || []).map(function (t) {
            return '<div class="pro-tip">' + esc(t) + '</div>';
          }).join('') + '</div>';
    }

    body.innerHTML = f + '<div class="section"><div class="sec-title">13 节完整攻略</div>' +
      fullLink(g.n) + '<div class="tips-text">该英雄的独立单文件深度攻略：13 节固定骨架，含' +
      '机制拆解、出装铭文替换表、开局路线、连招库、节奏锚点、团战与三种局势。</div></div>' +
      '<div class="section"><div class="sec-title">标签</div><div class="gb-tags">' +
      (g.tags || []).map(function (t) { return '<span class="gb-tag">' + esc(t) + '</span>'; }).join('') +
      '</div></div>' + extra;

    document.getElementById('gt-drawer').classList.add('open');
    document.getElementById('gt-drawer-mask').classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    var dr = document.getElementById('gt-drawer');
    var mk = document.getElementById('gt-drawer-mask');
    if (dr) dr.classList.remove('open');
    if (mk) mk.classList.remove('open');
    document.body.style.overflow = '';
  }

  /* ---------- 与原页面联动的钩子 ---------- */
  var _origRender = window.render;
  window.render = function () {
    if (typeof _origRender === 'function') {
      try { _origRender(); } catch (e) { console.error(e); }
    }
    var s = document.getElementById('search');
    state.q = s ? s.value.trim().toLowerCase() : '';
    var lb = document.querySelector('.nav-btn.active');
    state.lane = lb ? lb.dataset.lane : 'all';
    var matched = GUIDE.filter(match);
    var c = document.getElementById('gt-count');
    if (state.view === 'list') {
      if (c) c.textContent = matched.length;
      renderList(matched);
      renderEmptyHint(matched.length);
    } else {
      var shown = filterGridCards(matched);
      if (c) c.textContent = shown;
      renderEmptyHint(shown);
    }
  };

  function syncLane() {
    var lb = document.querySelector('.nav-btn.active');
    state.lane = lb ? lb.dataset.lane : 'all';
    applyFilter();
  }

  /* ---------- 启动 ---------- */
  function boot() {
    setTheme(getTheme());
    buildToolbar();

    var main = document.getElementById('main');
    if (main && !document.getElementById('gt-list')) {
      var listHost = document.createElement('div');
      listHost.id = 'gt-list';
      listHost.style.display = 'none';
      main.parentNode.insertBefore(listHost, main.nextSibling);
    }

    // 分路切换后同步筛选
    document.querySelectorAll('.nav-btn').forEach(function (b) {
      var orig = b.onclick;
      b.onclick = function () {
        if (typeof orig === 'function') orig();
        setTimeout(syncLane, 0);
      };
    });

    setView(state.view);
    window.render();

    // 打印前展开所有指南区块
    window.addEventListener('beforeprint', function () {
      document.querySelectorAll('#main .hero-card').forEach(function (card) {
        card.classList.add('expanded');
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // 暴露给其它脚本
  window.HOK_GUIDE = {
    data: GUIDE,
    open: openDrawer,
    close: closeDrawer,
    setTheme: setTheme,
    toggleTheme: toggleTheme
  };
})();
