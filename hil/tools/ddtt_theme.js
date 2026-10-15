// Тема хранится отдельно от результатов: переключение не меняет свидетельства.
(() => {
  const root = document.documentElement, button = document.getElementById('theme');
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  const key = 'bluepill-ddtt-theme';
  const modes = ['dark', 'light', 'auto'];
  let mode = 'dark';
  try { const saved = localStorage.getItem(key); if (modes.includes(saved)) mode = saved; } catch (_) {}
  function render() {
    const classes = document.body.classList;
    const vscodeDark = classes.contains('vscode-dark') || classes.contains('vscode-high-contrast');
    const vscodeLight = classes.contains('vscode-light') || classes.contains('vscode-high-contrast-light');
    const automatic = vscodeDark ? 'dark' : vscodeLight ? 'light' : media.matches ? 'dark' : 'light';
    root.dataset.theme = mode === 'auto' ? automatic : mode;
    button.textContent = {dark: '☾', light: '☀', auto: '◐'}[mode];
    const label = {dark: 'Тёмная', light: 'Светлая', auto: 'Авто'}[mode];
    button.title = 'Тема: ' + label + '. Переключить: тёмная / светлая / авто';
    button.setAttribute('aria-label', button.title);
    button.dataset.mode = mode;
  }
  button.addEventListener('click', () => {
    mode = modes[(modes.indexOf(mode) + 1) % modes.length];
    try { localStorage.setItem(key, mode); } catch (_) {}
    render();
  });
  media.addEventListener('change', render);
  new MutationObserver(render).observe(document.body, {attributes: true, attributeFilter: ['class']});
  render();
})();
