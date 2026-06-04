// управление списком симуляций и наполнение выбранной симуляции
let current = null; // {id, name}

async function api(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 1800);
}

// ---- список ----
async function loadSims() {
  const sims = await api('GET', '/api/sims');
  const list = document.getElementById('sim-list');
  list.innerHTML = '';
  if (!sims.length) {
    list.innerHTML = '<div class="empty-hint">Пока нет симуляций. Создай первую выше.</div>';
    return;
  }
  sims.forEach(s => {
    const row = document.createElement('div');
    row.className = 'sim-row';
    row.innerHTML = `
      <span class="sim-name">${s.name}</span>
      <span class="sim-meta">${s.stocks} акций · ${s.miples} миплов · шаг ${s.step}</span>
      <button class="btn btn-accent btn-sm act-edit">Настроить</button>
      <a class="btn btn-ghost btn-sm" href="/sim/${s.id}">Открыть</a>
      <button class="btn btn-sm act-rename" title="Переименовать">✎</button>
      <button class="btn btn-danger btn-sm act-del" title="Удалить">✕</button>`;
    row.querySelector('.act-edit').onclick = () => selectSim(s.id, s.name);
    row.querySelector('.act-del').onclick = async () => {
      await api('DELETE', `/api/sims/${s.id}`);
      if (current && current.id === s.id) hideEditor();
      loadSims();
    };
    row.querySelector('.act-rename').onclick = () => startRename(row, s);
    list.appendChild(row);
  });
}

function startRename(row, s) {
  const name = row.querySelector('.sim-name');
  const input = document.createElement('input');
  input.className = 'rename';
  input.value = s.name;
  name.replaceWith(input);
  input.focus();
  const commit = async () => {
    await api('PUT', `/api/sims/${s.id}`, { name: input.value });
    loadSims();
  };
  input.addEventListener('keydown', e => { if (e.key === 'Enter') commit(); });
  input.addEventListener('blur', commit);
}

// ---- создание ----
document.getElementById('create-sim').onclick = async () => {
  const name = document.getElementById('new-sim-name').value;
  const sim = await api('POST', '/api/sims', { name });
  document.getElementById('new-sim-name').value = '';
  await loadSims();
  selectSim(sim.id, sim.name);
  toast('Симуляция создана — теперь добавь миплов');
};

document.getElementById('create-auto').onclick = async () => {
  const miples = +document.getElementById('auto-miples').value || 4;
  const stocks = +document.getElementById('auto-stocks').value || 5;
  const model = document.getElementById('auto-model').value || null;
  const sim = await api('POST', '/api/sims', { name: 'Авто-симуляция' });
  await api('POST', `/api/sims/${sim.id}/auto`, { stocks, miples, model });
  await loadSims();
  toast('Готово! Запускаю окно симуляции');
  location.href = `/sim/${sim.id}`;
};

// ---- редактор ----
function hideEditor() {
  current = null;
  document.getElementById('editor').style.display = 'none';
}

async function selectSim(id, name) {
  current = { id, name };
  document.getElementById('editor').style.display = '';
  document.getElementById('editor-title').textContent = 'Настройка · ' + name;
  document.getElementById('open-sim').href = `/sim/${id}`;
  document.getElementById('editor').scrollIntoView({ behavior: 'smooth' });
  refreshEditor();
}

async function refreshEditor() {
  if (!current) return;
  const st = await api('GET', `/api/sims/${current.id}/state`);
  renderStocks(st.stocks);
  renderMiples(st.miples);
}

function renderStocks(stocks) {
  const box = document.getElementById('stock-list');
  if (!stocks.length) { box.innerHTML = '<div class="empty-hint">Нет акций</div>'; return; }
  box.innerHTML = stocks.map(s =>
    `<div class="port-row"><span class="pn">${s.name}</span><span class="hold">${s.price} WC</span><span></span></div>`).join('');
}

function renderMiples(miples) {
  const box = document.getElementById('miple-list');
  if (!miples.length) { box.innerHTML = '<div class="empty-hint">Нет миплов</div>'; return; }
  box.innerHTML = '';
  miples.forEach(m => {
    const row = document.createElement('div');
    row.className = 'port-row';
    row.innerHTML = `<span class="pn">${m.name} <span class="hold">${m.model}</span></span>
      <span class="hold">${m.sentiments.join(', ')}</span>
      <button class="btn btn-danger btn-sm">✕</button>`;
    row.querySelector('button').onclick = async () => {
      await api('DELETE', `/api/sims/${current.id}/miples/${m.id}`);
      refreshEditor();
    };
    box.appendChild(row);
  });
}

document.getElementById('add-stock').onclick = async () => {
  if (!current) return toast('Сначала выбери симуляцию');
  const name = document.getElementById('stock-name').value.trim();
  if (!name) return toast('Введи название акции');
  const r = await api('POST', `/api/sims/${current.id}/stocks`, {
    name,
    count: +document.getElementById('stock-count').value || 1000,
    invested: +document.getElementById('stock-invested').value || 4000,
  });
  if (!r.ok) return toast('Такая акция уже есть');
  document.getElementById('stock-name').value = '';
  refreshEditor();
};

document.getElementById('add-stock-random').onclick = async () => {
  if (!current) return toast('Сначала выбери симуляцию');
  await api('POST', `/api/sims/${current.id}/stocks`, { random: true });
  refreshEditor();
};

document.getElementById('add-miple').onclick = async () => {
  if (!current) return toast('Сначала выбери симуляцию');
  await api('POST', `/api/sims/${current.id}/miples`, {
    name: document.getElementById('miple-name').value.trim() || 'Мипл',
    model: window.builder.model,
    traits: [...window.builder.traits],
    expr: window.builder.expr,
  });
  refreshEditor();
  toast('Мипл добавлен');
};

document.getElementById('add-miple-random').onclick = async () => {
  if (!current) return toast('Сначала выбери симуляцию');
  await api('POST', `/api/sims/${current.id}/miples`, { random: true, model: window.builder.model });
  refreshEditor();
  toast('Случайный мипл создан');
};

document.getElementById('auto-fill').onclick = async () => {
  if (!current) return toast('Сначала выбери симуляцию');
  await api('POST', `/api/sims/${current.id}/auto`, { stocks: 4, miples: 4, model: window.builder.model });
  refreshEditor();
  toast('Симуляция заполнена автоматически');
};

loadSims();
