(() => {
  'use strict';

  // This early-access site is intentionally static: no installers, databases,
  // analytics, or third-party data collection are hosted by this page.
  // FormSubmit forwards the request after the owner activates the form.
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
  const submitButton = document.getElementById('request-submit');
  const honeypot = document.getElementById('request-website');
  let submitting = false;
  document.getElementById('current-year').textContent = String(new Date().getFullYear());

  function openRequest(type) {
    editionInput.value = Object.hasOwn(editions, type) ? type : 'browser';
    feedback.hidden = true;
    feedback.textContent = '';
    feedback.classList.remove('is-error', 'is-success');
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

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitting) return;

    const email = emailInput.value.trim();
    emailInput.value = email;
    if (!emailInput.checkValidity()) {
      emailInput.reportValidity();
      return;
    }
    const edition = editions[editionInput.value];
    if (!edition) return;
    if (honeypot.value.trim()) return;

    submitting = true;
    submitButton.disabled = true;
    submitButton.textContent = 'Sending request…';
    form.setAttribute('aria-busy', 'true');
    feedback.classList.remove('is-error', 'is-success');
    feedback.hidden = true;
    manual.hidden = true;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 18000);
    try {
      const response = await fetch('https://formsubmit.co/ajax/' + contact, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({
          name: 'Glossa AI Early Access',
          email,
          edition: edition.label,
          version: edition.version,
          message: 'I would like early access to Glossa AI ' + edition.label + ' (' + edition.version + '). Please reply to ' + email + ' when access is available.',
          _subject: 'Glossa AI Early Access Request - ' + edition.label,
          _replyto: email,
          _captcha: 'false',
          _template: 'table'
        }),
        signal: controller.signal
      });
      const result = await response.json();
      if (!response.ok || (result.success !== true && result.success !== 'true')) {
        throw new Error('Submission was not accepted');
      }
      feedback.textContent = 'Request submitted successfully. Thank you! We will contact you by email when access is available.';
      feedback.classList.add('is-success');
      feedback.hidden = false;
      form.reset();
      editionInput.value = Object.keys(editions).find(key => editions[key] === edition) || 'browser';
    } catch (error) {
      feedback.textContent = error && error.name === 'AbortError'
        ? 'Request timed out. Please try again or contact us using the address below.'
        : 'Unable to confirm your submission. Please retry or contact us using the address below.';
      feedback.classList.add('is-error');
      feedback.hidden = false;
      manual.hidden = false;
      contactAddress.textContent = contact;
    } finally {
      clearTimeout(timeout);
      submitting = false;
      submitButton.disabled = false;
      submitButton.textContent = 'Send access request';
      form.removeAttribute('aria-busy');
    }
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
