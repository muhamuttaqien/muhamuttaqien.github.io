(() => {
  'use strict';

  // This early-access site is intentionally static: no installers, databases,
  // analytics, or third-party data collection are hosted by this page.
  // Email requests remain user-sent via their own mail application.
  const contact = 'muha.muttaqien@gmail.com';
  const editions = {
    browser: { label: 'Browser Extension', version: 'v4.6' },
    desktop: { label: 'Ubuntu Desktop', version: 'v1.2' },
  };

  const themeToggle = document.getElementById('theme-toggle');
  function updateThemeButton() {
    const light = document.documentElement.dataset.theme === 'light';
    themeToggle.setAttribute('aria-pressed', String(light));
    themeToggle.setAttribute('aria-label', light ? 'Switch to dark mode' : 'Switch to light mode');
    themeToggle.title = light ? 'Switch to dark mode' : 'Switch to light mode';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', light ? '#fafbfc' : '#080808');
  }
  updateThemeButton();
  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('glossa-theme', next); } catch (_) {}
    updateThemeButton();
  });

  const dialog = document.getElementById('request-dialog');
  const form = document.getElementById('request-form');
  const editionInput = document.getElementById('request-edition');
  const emailInput = document.getElementById('request-email');
  const feedback = document.getElementById('request-feedback');
  const manual = document.getElementById('manual-contact');
  const contactAddress = document.getElementById('contact-address');
  document.getElementById('current-year').textContent = String(new Date().getFullYear());

  function openRequest(type) {
    editionInput.value = Object.hasOwn(editions, type) ? type : 'browser';
    feedback.hidden = true;
    feedback.textContent = '';
    manual.hidden = true;
    form.reset();
    editionInput.value = Object.hasOwn(editions, type) ? type : 'browser';
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    emailInput.focus();
  }

  document.querySelectorAll('.request-button').forEach(button => {
    button.addEventListener('click', () => openRequest(button.dataset.edition));
  });

  document.getElementById('dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    // Clicking the native dialog backdrop closes the modal.
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    feedback.hidden = true;
    manual.hidden = true;
  });

  form.addEventListener('submit', event => {
    event.preventDefault();
    const email = emailInput.value.trim();
    emailInput.value = email;
    if (!emailInput.checkValidity()) {
      emailInput.reportValidity();
      return;
    }
    const edition = editions[editionInput.value];
    if (!edition) return;

    const subject = `Glossa AI Early Access Request — ${edition.label}`;
    const body = [
      'Hello Glossa AI team,',
      '',
      `I would like to request early access to Glossa AI ${edition.label} (${edition.version}).`,
      '',
      `My contact email: ${email}`,
      '',
      'Please let me know when access is available and how to install it.',
      '',
      'Thank you!'
    ].join('\n');

    contactAddress.textContent = contact;
    manual.hidden = false;
    feedback.textContent = 'Your email app should open with a ready-to-send request. Please press Send there to complete it. This site has not sent an email on your behalf.';
    feedback.hidden = false;

    // Do not claim submission here: mailto only opens a local email composer.
    window.location.href = `mailto:${contact}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  document.getElementById('copy-contact').addEventListener('click', async event => {
    try {
      await navigator.clipboard.writeText(contact);
      event.currentTarget.textContent = 'Copied';
      setTimeout(() => { event.currentTarget.textContent = 'Copy'; }, 1800);
    } catch (_) {
      // Email address remains visible, so users can copy it manually.
      event.currentTarget.textContent = 'Select the address';
    }
  });

  const params = new URLSearchParams(window.location.search);
  const preselect = params.get('request');
  if (preselect && Object.hasOwn(editions, preselect)) openRequest(preselect);
})();
