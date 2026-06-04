// колесо личности и выбор выражения — общее состояние для конструктора мипла
const traits = {
  extra: { pill: 'ЭКСТРА' }, risk: { pill: 'рискованный' }, convinced: { pill: 'убеждённый' },
  optimist: { pill: 'Оптимист' }, introvert: { pill: 'интроверт' }, intuitive: { pill: 'интуитивный' },
  conservative: { pill: 'консерватор' }, systematic: { pill: 'систематичный' },
};

const builder = { traits: new Set(), expr: 'happy', model: 'mrplip_17M_3' };
window.builder = builder;

function fillColor(active) {
  // читаем актуальные значения темы
  const s = getComputedStyle(document.documentElement);
  return active ? s.getPropertyValue('--yellow').trim() : s.getPropertyValue('--bg-card').trim();
}

function paintWheel() {
  document.querySelectorAll('.wheel-segment').forEach(seg => {
    const active = builder.traits.has(seg.dataset.trait);
    seg.classList.toggle('active', active);
    seg.setAttribute('fill', fillColor(active));
  });
}

function paintPills() {
  const pills = document.getElementById('trait-pills');
  if (!pills) return;
  pills.innerHTML = '';
  [...builder.traits].forEach(k => {
    const span = document.createElement('span');
    span.className = 'trait-pill';
    span.textContent = traits[k].pill;
    pills.appendChild(span);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.wheel-segment').forEach(seg => {
    seg.addEventListener('click', () => {
      const k = seg.dataset.trait;
      builder.traits.has(k) ? builder.traits.delete(k) : builder.traits.add(k);
      paintWheel();
      paintPills();
    });
  });

  document.querySelectorAll('.expr-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.expr-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      builder.expr = btn.dataset.expr;
      const face = document.getElementById('center-face');
      if (face) face.className = 'face' + (builder.expr === 'neutral' ? '' : ' ' + builder.expr);
    });
  });

  document.querySelectorAll('.model-opt').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.model-opt').forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      builder.model = opt.dataset.model;
    });
  });

  const nameIn = document.getElementById('miple-name');
  if (nameIn) nameIn.addEventListener('input', e => {
    document.getElementById('mipple-label').textContent = e.target.value || 'Мипл';
  });

  paintWheel();
});
