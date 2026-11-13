# Glossa AI — Early Access Landing Page

**Don't Just Translate. Understand.**

Your AI companion for learning languages.

This directory hosts the static Glossa AI early-access website on GitHub Pages.

**Live URL:** https://muhamuttaqien.github.io/glossa/

## Project structure

```text
glossa/
├── index.html             # Website markup and accessible request modal
├── README.md              # This file
└── assets/
    ├── css/
    │   ├── style.css      # Dark and light themes
    │   └── preview.css    # Extension walkthrough
    ├── js/
    │   ├── main.js        # Theme toggle, modal and email request
    │   ├── theme.js       # Restores saved theme before stylesheet loads
    │   └── preview.js     # Writing/Reading/OCR interactive demo
    └── img/
        ├── favicon.svg    # Glossa AI icon
        ├── ocr-arabic.svg  # Arabic book OCR sample
        └── ocr-naruto.svg  # Fan-made ninja manga example
```

## Interactive browser-extension preview

The **See Glossa in Action** section is a standalone visual walkthrough for **Glossa AI Chrome Extension v4.6**. Visitors can switch between Writing, Reading and OCR; OCR provides two scenarios: an illustrative Arabic book page and a fan-created ninja manga example labelled Naruto Manga.

The preview does **not** call an AI API or process uploaded documents. Its mock results are clearly labelled as illustrative. It is intentionally separate from the real early-access form.

- `assets/css/preview.css` — responsive presentation, stage animation and mobile layouts
- `assets/js/preview.js` — accessible tabs, keyboard navigation, switchable OCR samples and replay
- `assets/img/ocr-arabic.svg` — original Arabic-language book illustration
- `assets/img/ocr-naruto.svg` — original fan-style ninja manga illustration (not an official manga scan)

Only the browser extension is previewed. The Ubuntu app remains available to request in the Early Access section.

## Early-access flow

- **Browser Extension (recommended):** Glossa AI v4.6
- **Ubuntu Desktop:** Glossa AI v1.2

Visitors select an edition and enter an email address, then press **Send access request**. The page sends the request directly using the [FormSubmit AJAX endpoint](https://formsubmit.co/ajax-documentation). No email client is needed, and no installation files are hosted on this site.

The destination inbox is `muha.muttaqien@gmail.com` and is configured in `assets/js/main.js`.

### Required first-time FormSubmit activation

1. Submit one test request using the live landing page.
2. Check `muha.muttaqien@gmail.com`, including spam, for FormSubmit's activation email.
3. Confirm/activate the form from that email.
4. Submit a second test and verify that the notification arrives.

The website can show a request as accepted before the mailbox has been activated; **acceptance is not proof of email delivery**. Do not assume emails arrive until the activation and a second test are complete.

## Dark and light mode

Use the theme toggle at the top right to switch between Dark and Light. The selection is saved locally in the browser under `glossa-theme`. Dark is the default. Light mode uses a muted slate-gray palette rather than bright white, with darker section surfaces and comfortable text contrast. This preference is never sent to a server.

## Publishing

This directory is served as a subfolder of the existing repository `muhamuttaqien/muhamuttaqien.github.io`. GitHub Pages serves `index.html` at `/glossa/`. Changes to the root research website are not needed.

For local preview, serve the repository folder with a simple HTTP server and open `/glossa/`, or open `index.html` in a browser. Relative CSS, JS and SVG paths are used so the website works on GitHub Pages.

## Privacy and limitations

- GitHub Pages itself stores no submission database, but the form processor FormSubmit receives user email addresses, edition choices, and submitted message text. Its [privacy policy](https://formsubmit.co/privacy.pdf) applies.
- AJAX submission requires JavaScript and a network connection to FormSubmit. Client confirmation means FormSubmit accepted the request, not guaranteed delivery to the inbox.
- The form includes a simple honeypot to discourage automated spam.
- Do not commit API keys, a visitor email list, or early-access installers to this public Pages repository.
