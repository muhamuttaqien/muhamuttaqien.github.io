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
    │   └── style.css      # Dark theme and responsive layout
    ├── js/
    │   └── main.js        # Modal, edition selection and email request
    └── img/
        └── favicon.svg    # Glossa AI icon
```

## Early-access flow

- **Browser Extension (recommended):** Glossa AI v4.6
- **Ubuntu Desktop:** Glossa AI v1.2

The request button opens an email form; after validation, it prepares a message with a `mailto:` link. The visitor **must manually send** the message using their email application. The site does **not** automatically submit emails, store addresses, or host software installers.

The destination inbox is set in `assets/js/main.js` (the `contact` constant). Change it to your dedicated Glossa support inbox before wide launch.

## Publishing

This directory is served as a subfolder of the existing repository `muhamuttaqien/muhamuttaqien.github.io`. GitHub Pages serves `index.html` at `/glossa/`. Changes to the root research website are not needed.

For local preview, serve the repository folder with a simple HTTP server and open `/glossa/`, or open `index.html` in a browser. Relative CSS, JS and SVG paths are used so the website works on GitHub Pages.

## Privacy and limitations

- There is no website-side collection or database for submitted addresses.
- A `mailto:` link depends on the visitor having an email handler configured.
- Seeing the confirmation text in the modal **does not mean an email was sent**.
- Do not commit API keys, a visitor email list, or early-access installers to this public Pages repository.
