const WHEEL_FILL_DEFAULT = '#fffef5';
const WHEEL_FILL_ACTIVE = '#f5e6a3';

const traits = {
  extra: { title: 'Экстра', desc: 'Активно инициирует сделки и диалоги в соцсети.', pill: 'ЭКСТРА' },
  risk: { title: 'Рискованный', desc: 'Высокая волатильность портфеля, быстрые P2P-сделки.', pill: 'рискованный' },
  convinced: { title: 'Убеждённый', desc: 'Держится выбранной стратегии, редко меняет позицию.', pill: 'убеждённый' },
  optimist: { title: 'Оптимист', desc: 'Покупает на просадках, позитивные посты в ленте.', pill: 'Оптимист' },
  introvert: { title: 'Интроверт', desc: 'Реже публикует, выбирает проверенных контрагентов.', pill: 'интроверт' },
  intuitive: { title: 'Интуитивный', desc: 'Решения по паттернам, не только по индикаторам.', pill: 'интуитивный' },
  conservative: { title: 'Консерватор', desc: 'Низкий риск, долгие удержания, стабильные страны.', pill: 'консерватор' },
  systematic: { title: 'Систематичный', desc: 'Алгоритмические правила торговли и фильтры ленты.', pill: 'систематичный' }
};

let selectedTraits = new Set();

function paintWheelSegments() {
  document.querySelectorAll('.wheel-segment').forEach(seg => {
    const active = selectedTraits.has(seg.dataset.trait);
    seg.classList.toggle('active', active);
    seg.setAttribute('fill', active ? WHEEL_FILL_ACTIVE : WHEEL_FILL_DEFAULT);
  });
}

document.querySelectorAll('.wheel-segment').forEach(seg => {
  seg.setAttribute('fill', WHEEL_FILL_DEFAULT);
  seg.addEventListener('click', () => {
    const key = seg.dataset.trait;
    if (selectedTraits.has(key)) selectedTraits.delete(key);
    else selectedTraits.add(key);
    paintWheelSegments();
    updateTraitUI();
  });
});

function updateTraitUI() {
  const pills = document.getElementById('trait-pills');
  const title = document.getElementById('selected-trait-title');
  const desc = document.getElementById('selected-trait-desc');
  if (!pills || !title || !desc) return;
  pills.innerHTML = '';
  if (selectedTraits.size === 0) {
    title.textContent = 'Выбери черту на колесе';
    desc.textContent = 'Каждый сегмент задаёт поведение на рынке и тон постов в соцсети.';
    return;
  }
  const keys = [...selectedTraits];
  keys.forEach(k => {
    const span = document.createElement('span');
    span.className = 'trait-pill';
    span.textContent = traits[k].pill;
    pills.appendChild(span);
  });
  if (keys.length === 1) {
    title.textContent = traits[keys[0]].title;
    desc.textContent = traits[keys[0]].desc;
  } else {
    title.textContent = `Смешанный профиль (${keys.length})`;
    desc.textContent = 'Мипл сочетает несколько черт — поведение на рынке и в соцсети будет гибридным.';
  }
}

document.querySelectorAll('.expr-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.expr-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const expr = btn.dataset.expr;
    const center = document.getElementById('center-face');
    if (center) center.className = 'face' + (expr === 'neutral' ? '' : ' ' + expr);
  });
});

paintWheelSegments();
