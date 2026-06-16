// окно симуляции: шаги, авто-прогон, график и переключатель отображения
const SIM_ID = document.body.dataset.simId;
let state = null;
let chartMode = 'candle';
let view = 'chat';
let selectedStock = null;
let mipleFilter = '';
let autoTimer = null;
let autoRunning = false; // флаг авто-прогона, чтобы стоп срабатывал мгновенно, иначе симуляция продолжится
let chartView = { visible: 80, offset: 0 }; // окно просмотра графика: видимых свечей и сдвиг от конца и тп

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function currentStock() {
  if (!state || !state.stocks.length) return null;
  return state.stocks.find(s => s.name === selectedStock) || state.stocks[0];
}

function visibleCandles(all) {
  const total = all.length;
  if (!total) return [];
  const vis = Math.min(Math.round(chartView.visible), total);
  const end = clamp(total - Math.round(chartView.offset), vis, total);
  return all.slice(end - vis, end);
}

async function api(method, url, body) {
  const r = await fetch(url, {
    method, headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 1800);
}

const DEC = { buy: 'покупка', sell: 'продажа', hold: 'держит' };

function render() {
  if (!state) return;
  document.getElementById('step-badge').innerHTML = '<span class="coin">₩</span>шаг ' + state.step;

  // выбор акции
  const sel = document.getElementById('stock-select');
  if (sel.options.length !== state.stocks.length) {
    sel.innerHTML = state.stocks.map(s => `<option value="${s.name}">${s.name} · ${s.sphere}</option>`).join('');
    if (state.stocks.length) selectedStock = selectedStock || state.stocks[0].name;
    sel.value = selectedStock;
  }

  // фильтр по миплам
  const mf = document.getElementById('miple-filter');
  if (mf.options.length !== state.miples.length + 1) {
    mf.innerHTML = '<option value="">все</option>' +
      state.miples.map(m => `<option value="${m.name}">${m.name}</option>`).join('');
    mf.value = mipleFilter;
  }

  renderChart();
  renderMarket();
  renderFeed();
}

function renderMarket() {
  const m = state.market;
  const sign = v => (v > 0 ? '+' : '') + v + '%';
  const cls = v => (v > 0 ? 'up' : v < 0 ? 'down' : '');
  document.getElementById('market-summary').innerHTML = `
    <div class="market-cell"><div class="v">${m.total_value} WC</div><div class="l">капитализация</div></div>
    <div class="market-cell"><div class="v ${cls(m.avg_change)}" style="color:var(--${m.avg_change>0?'green':m.avg_change<0?'red':'ink'})">${sign(m.avg_change)}</div><div class="l">средний шаг</div></div>
    <div class="market-cell"><div class="v">${m.stocks}</div><div class="l">акций</div></div>
    <div class="market-cell"><div class="v">${m.spheres.length}</div><div class="l">сфер</div></div>`;

  const box = document.getElementById('sphere-list');
  if (!m.spheres.length) { box.innerHTML = '<div class="empty-hint">Нет акций</div>'; return; }
  const maxVal = Math.max(...m.spheres.map(s => s.value)) || 1;
  box.innerHTML = m.spheres.map(s => `
    <div class="sphere-row">
      <span class="sn">${s.sphere} <span class="hold">· ${s.count}</span></span>
      <span class="bar" style="width:${Math.max(8, (s.value / maxVal) * 70)}px"></span>
      <span class="ch ${cls(s.change)}">${sign(s.change)}</span>
    </div>`).join('');
}

function renderChart() {
  const stock = currentStock();
  const canvas = document.getElementById('chart');
  drawChart(canvas, stock ? visibleCandles(stock.candles) : [], chartMode);

  const now = document.getElementById('price-now');
  now.textContent = stock ? `${stock.name}: ${stock.price} WC` : '';

  const tag = document.getElementById('stock-sphere');
  const show = document.getElementById('set-sphere').checked;
  tag.classList.toggle('hidden', !show || !stock);
  if (stock) tag.textContent = 'сфера: ' + stock.sphere;
}

function avatar(expr) {
  const cls = expr && expr !== 'neutral' ? ' ' + expr : '';
  return `<div class="ava"><div class="face${cls}" style="width:100%;height:100%"><span class="eye left"></span><span class="eye right"></span><span class="mouth"></span></div></div>`;
}

function renderFeed() {
  const feed = document.getElementById('feed');
  let html = '';

  if (view === 'chat' || view === 'decisions') {
    let items = state.chat.slice().reverse();
    if (mipleFilter) items = items.filter(c => c.miple === mipleFilter);
    if (!items.length) html = '<div class="empty-hint">Сделай шаг — миплы начнут общаться</div>';
    items.forEach(c => {
      const dec = `<span class="dec ${c.decision}">${DEC[c.decision]}</span>`;
      const body = view === 'chat'
        ? `<div class="txt">${c.text || '…'}</div>
           <div class="meta-line">${dec}<span>· ${c.target}</span></div>`
        : `<div class="txt">по акции <b>${c.target}</b></div>
           <div class="meta-line">${dec}<span>тактика: ${c.tactic}</span></div>`;
      html += `<div class="msg clickable" data-mid="${c.miple_id}">${avatar(c.expr)}<div class="body">
        <div class="who">${c.miple}<span class="badge">${c.model}</span></div>${body}</div></div>`;
    });
  } else if (view === 'assets') {
    let ports = mipleFilter ? state.portfolios.filter(p => p.name === mipleFilter) : state.portfolios;
    if (!ports.length) html = '<div class="empty-hint">Нет миплов</div>';
    ports.forEach(p => {
      const holds = Object.entries(p.holdings).map(([n, c]) => `${n}×${c}`).join(', ') || 'нет позиций';
      html += `<div class="port-row clickable" data-mid="${p.id}"><div><div class="pn">${p.name}</div><div class="hold">${holds}</div></div>
        <span class="hold">${p.balance} WC</span><span class="worth">${p.worth} WC</span></div>`;
    });
  } else if (view === 'events') {
    const items = state.events.slice().reverse();
    if (!items.length) html = '<div class="empty-hint">Событий пока не было</div>';
    items.forEach(e => {
      html += `<div class="event-row ${e.polarity}"><span class="ev-dot"></span>
        <b>шаг ${e.step}:</b> ${e.description} <span class="hold">(${e.stocks.join(', ')})</span></div>`;
    });
  }
  feed.innerHTML = html;
  if (document.getElementById('set-autoscroll').checked) feed.scrollTop = 0;
}

async function load() {
  state = await api('GET', `/api/sims/${SIM_ID}/state`);
  render();
}

async function doStep(n) {
  toast(n > 1 ? `Считаю ${n} шагов…` : 'Шаг…');
  state = await api('POST', `/api/sims/${SIM_ID}/step`, { steps: n });
  render();
  if (state.last_event && document.getElementById('set-toast').checked) {
    toast('Событие: ' + state.last_event.description);
  }
}

// управление шагов симуляции
document.getElementById('step-1').onclick = () => doStep(+document.getElementById('set-steps').value || 1);
document.getElementById('step-5').onclick = () => doStep(5);

function stopAuto(btn) {
  autoRunning = false;
  clearTimeout(autoTimer); autoTimer = null;
  btn.textContent = '⚡ Авто-прогон'; btn.classList.remove('btn-primary'); btn.classList.add('btn-accent');
}

// шаги идут по очереди: следующий ставим только после завершения текущего
async function autoLoop(btn) {
  if (!autoRunning) return;
  await doStep(1);
  if (!autoRunning) return;
  const speed = +document.getElementById('set-speed').value || 1600;
  autoTimer = setTimeout(() => autoLoop(btn), speed);
}

document.getElementById('auto-run').onclick = function () {
  if (autoRunning) { stopAuto(this); return; }
  autoRunning = true;
  this.textContent = '⏸ Остановить'; this.classList.add('btn-primary'); this.classList.remove('btn-accent');
  autoLoop(this);
};

document.getElementById('stock-select').onchange = e => { selectedStock = e.target.value; chartView.offset = 0; renderChart(); };
document.getElementById('miple-filter').onchange = e => { mipleFilter = e.target.value; renderFeed(); };
document.getElementById('set-sphere').onchange = renderChart;

// масштаб и прокрутка графика
const chartCanvas = document.getElementById('chart');
chartCanvas.addEventListener('wheel', e => {
  const stock = currentStock();
  if (!stock || !stock.candles.length) return;
  e.preventDefault();
  const total = stock.candles.length;
  chartView.visible = Math.round(clamp(chartView.visible * (e.deltaY < 0 ? 0.82 : 1.22), 5, total));
  chartView.offset = clamp(chartView.offset, 0, total - Math.min(chartView.visible, total));
  renderChart();
}, { passive: false });

let drag = null;
chartCanvas.addEventListener('pointerdown', e => { drag = e.clientX; chartCanvas.setPointerCapture(e.pointerId); });
chartCanvas.addEventListener('pointermove', e => {
  if (drag === null) return;
  const stock = currentStock();
  if (!stock || !stock.candles.length) return;
  const total = stock.candles.length;
  const vis = Math.min(chartView.visible, total);
  const candleW = chartCanvas.clientWidth / vis;
  chartView.offset = clamp(chartView.offset + (e.clientX - drag) / candleW, 0, total - vis);
  drag = e.clientX;
  renderChart();
});
const endDrag = () => { drag = null; };
chartCanvas.addEventListener('pointerup', endDrag);
chartCanvas.addEventListener('pointerleave', endDrag);

document.querySelectorAll('#chart-mode button').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('#chart-mode button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    chartMode = b.dataset.mode;
    renderChart();
  };
});

document.querySelectorAll('#view-tabs .tab').forEach(t => {
  t.onclick = () => {
    document.querySelectorAll('#view-tabs .tab').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    view = t.dataset.view;
    renderFeed();
  };
});

// кликнув по миплу можно открыть его профиль
document.getElementById('feed').addEventListener('click', e => {
  const row = e.target.closest('[data-mid]');
  if (row) openProfile(row.dataset.mid);
});
document.getElementById('profile-close').onclick = closeProfile;
document.getElementById('profile-modal').addEventListener('click', e => {
  if (e.target.id === 'profile-modal') closeProfile();
});

function openProfile(mid) {
  const p = state.portfolios.find(x => x.id === mid);
  if (!p) return;
  const change = p.wealth.length > 1 ? round2((p.worth - p.wealth[0]) / p.wealth[0] * 100) : 0;
  const cls = change > 0 ? 'green' : change < 0 ? 'red' : 'ink';

  document.getElementById('profile-ava').innerHTML =
    `<div class="face${p.expr && p.expr !== 'neutral' ? ' ' + p.expr : ''}" style="width:100%;height:100%"><span class="eye left"></span><span class="eye right"></span><span class="mouth"></span></div>`;
  document.getElementById('profile-name').textContent = p.name;
  document.getElementById('profile-model').textContent = 'модель: ' + p.model;
  document.getElementById('profile-traits').innerHTML =
    (p.sentiments || []).map(s => `<span class="trait-pill">${s}</span>`).join('');
  document.getElementById('profile-stats').innerHTML = `
    <div class="market-cell"><div class="v">${p.worth} WC</div><div class="l">капитал</div></div>
    <div class="market-cell"><div class="v">${p.balance} WC</div><div class="l">кэш</div></div>
    <div class="market-cell"><div class="v" style="color:var(--${cls})">${change > 0 ? '+' : ''}${change}%</div><div class="l">с начала</div></div>`;

  const holds = Object.entries(p.holdings);
  document.getElementById('profile-holdings').innerHTML = holds.length
    ? holds.map(([n, c]) => `<div class="port-row"><span class="pn">${n}</span><span class="worth">${c} шт</span></div>`).join('')
    : '<div class="empty-hint">Нет открытых позиций</div>';

  document.getElementById('profile-modal').classList.add('show');
  const pseudo = (p.wealth.length ? p.wealth : [p.worth]).map(w => ({ open: w, close: w, high: w, low: w }));
  drawChart(document.getElementById('wealth-chart'), pseudo, 'area');
}

function closeProfile() { document.getElementById('profile-modal').classList.remove('show'); }
function round2(v) { return Math.round(v * 100) / 100; }

window.addEventListener('resize', renderChart);

// клик по планете (не работает как должно)
document.getElementById('planet-card').onclick = () => {
  const side = document.getElementById('col-side');
  const open = side.classList.toggle('planet-expanded');
  document.getElementById('planet-card').title = open ? 'Нажми, чтобы свернуть' : 'Нажми, чтобы развернуть';
};

load();
