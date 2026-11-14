# Glossa AI — Early Access Landing Page (Browser Extension v5.7)

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
    │   └── preview.js     # Writing/Reading/OCR/Transcribe interactive demo
    └── img/
        ├── favicon.svg    # Glossa AI icon
        ├── ocr-arabic.svg  # Zoomed white page with unvowelled Arabic
        └── ocr-naruto.webp # User-provided Naruto manga excerpt
```

## Interactive browser-extension preview

The **See Glossa in Action** section is a standalone visual walkthrough for **Glossa AI Chrome Extension v5.7**. Visitors can switch between **Writing, Reading, OCR and Live Transcribe**. OCR provides two scenarios: a white Arabic book page and a user-provided Naruto manga excerpt. Transcribe shows a simulated Japanese lesson, example live captions, GPT-6 Luna translations, and G. analysis after Pause.

The preview is **illustrative only**: it never captures tab audio, calls the OpenAI API, runs Whisper, or analyzes uploaded documents. Mock transcript text and translations are prewritten. It is intentionally separate from the real early-access form.

- `assets/css/preview.css` — responsive presentation, stage animation and mobile layouts
- `assets/js/preview.js` — accessible tabs, keyboard navigation, switchable OCR samples and replay
- `assets/img/ocr-arabic.svg` — enlarged white Arabic page with unvowelled text
- `assets/img/ocr-naruto.webp` — compressed version of the Naruto manga image supplied for this preview. Rights remain with their respective owners.

Only the browser extension is previewed. The Ubuntu app remains available to request in the Early Access section.

## What's new in Glossa AI v5.7

The Chrome extension now offers a fourth mode, **Live Transcribe**:

- Share a Chrome video tab with **Share tab audio** enabled, then see partial and finalized transcripts in the Glossa side panel.
- Default speech recognition: **GPT Live Transcribe (OpenAI Cloud)**. Optional: **Whisper Large-v3-Turbo** using a separately started local Python backend.
- **GPT-6 Luna** automatically translates completed transcript passages to the chosen Transcribe translation language (fresh-install default: Indonesian). The Cloud/Local STT selection is independent of translation.
- Pause or Stop to right-click a completed transcript entry for **Explain Grammar**, **Vocabulary**, or **Meaning & Context**. The G. analysis has **Ask a follow-up** and a separate Luna/Terra/Sol model preference, defaulting to Luna.
- A user-provided OpenAI API key is required for Cloud STT and translation. Local Whisper does not send the captured audio to OpenAI for STT, but completed transcript text is still sent to OpenAI for Luna translation. All features may incur service costs where applicable.
- Some protected videos may block audio capture. The site does not promise compatibility with every video provider.

This information is grounded in the uploaded `Glossa-AI-v5.7.zip`. The landing page does not run these functions; it only presents a simulated tour.

## Early-access flow

- **Browser Extension (recommended):** Glossa AI v5.7
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
