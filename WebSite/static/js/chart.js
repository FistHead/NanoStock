// отрисовка графиков
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function drawChart(canvas, candles, mode) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const green = cssVar('--green'), red = cssVar('--red');
  const ink = cssVar('--ink-light'), grid = cssVar('--border');
  const pad = { l: 8, r: 56, t: 14, b: 18 };

  if (!candles || !candles.length) {
    ctx.fillStyle = ink;
    ctx.font = '13px DM Sans, sans-serif';
    ctx.fillText('Нет данных — сделай шаг симуляции', pad.l + 10, h / 2);
    return;
  }

  const highs = candles.map(c => c.high), lows = candles.map(c => c.low);
  let max = Math.max(...highs), min = Math.min(...lows);
  if (max === min) { max += 1; min -= 1; }
  const range = max - min;
  max += range * 0.08; min -= range * 0.08;

  const plotW = w - pad.l - pad.r, plotH = h - pad.t - pad.b;
  const x = i => pad.l + (plotW * (candles.length === 1 ? 0.5 : i / (candles.length - 1)));
  const y = p => pad.t + plotH * (1 - (p - min) / (max - min));

  // сетка и подписи цены
  ctx.strokeStyle = grid; ctx.fillStyle = ink;
  ctx.font = '10px DM Sans, sans-serif'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const gy = pad.t + (plotH * i) / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(w - pad.r, gy); ctx.stroke();
    const price = (max - ((max - min) * i) / 4);
    ctx.fillText(price.toFixed(2), w - pad.r + 6, gy + 3);
  }

  if (mode === 'line' || mode === 'area') {
    const accent = cssVar('--yellow-accent');
    ctx.beginPath();
    candles.forEach((c, i) => { const px = x(i), py = y(c.close); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
    if (mode === 'area') {
      const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + plotH);
      grad.addColorStop(0, cssVar('--yellow-deep')); grad.addColorStop(1, 'transparent');
      ctx.lineTo(x(candles.length - 1), pad.t + plotH); ctx.lineTo(x(0), pad.t + plotH); ctx.closePath();
      ctx.fillStyle = grad; ctx.globalAlpha = 0.5; ctx.fill(); ctx.globalAlpha = 1;
      ctx.beginPath();
      candles.forEach((c, i) => { const px = x(i), py = y(c.close); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
    }
    ctx.strokeStyle = accent; ctx.lineWidth = 2; ctx.stroke();
    return;
  }

  // свечи
  const slot = plotW / candles.length;
  const bw = Math.max(2, Math.min(16, slot * 0.62));
  candles.forEach((c, i) => {
    const px = candles.length === 1 ? pad.l + plotW / 2 : pad.l + slot * (i + 0.5);
    const up = c.close >= c.open;
    const col = up ? green : red;
    ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(px, y(c.high)); ctx.lineTo(px, y(c.low)); ctx.stroke();
    const yo = y(c.open), yc = y(c.close);
    const top = Math.min(yo, yc), bh = Math.max(2, Math.abs(yc - yo));
    ctx.fillRect(px - bw / 2, top, bw, bh);
  });
}
window.drawChart = drawChart;
