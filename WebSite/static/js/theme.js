// переключение темы
(function () {
  const saved = localStorage.getItem('miple-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);

  function icon() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = dark ? '☀️' : '🌙';
  }

  document.addEventListener('DOMContentLoaded', () => {
    icon();
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      const next = dark ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('miple-theme', next);
      icon();
    });
  });
})();
