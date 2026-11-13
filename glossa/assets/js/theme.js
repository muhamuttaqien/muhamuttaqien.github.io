(() => {
  'use strict';
  // Apply a stored preference before the stylesheet is rendered.
  let selected = 'dark';
  try {
    if (localStorage.getItem('glossa-theme') === 'light') selected = 'light';
  } catch (_) {
    // Storage might be disabled; keep the default theme working.
  }
  document.documentElement.setAttribute('data-theme', selected);
})();
