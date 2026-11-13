(() => {
  'use strict';

  const root = document.getElementById('glossa-preview');
  const stage = document.getElementById('pv-display');
  const sourceTabs = Array.from(document.querySelectorAll('[data-pv-mode]'));
  const exampleTabs = Array.from(document.querySelectorAll('[data-pv-sample]'));
  const exampleChooser = document.getElementById('pv-ocr-switch');
  const replayButton = document.getElementById('pv-replay');
  const announcer = document.getElementById('pv-live');
  if (!root || !stage || !replayButton || !exampleChooser) return;

  let mode = 'writing';
  let sample = 'naruto';
  let scheduled = [];
  let runNumber = 0;

  const escapeText = value => String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);

  function clearAnimation() {
    scheduled.forEach(timer => clearTimeout(timer));
    scheduled = [];
    runNumber += 1;
  }

  function panelHeading(title, chip, brand = false) {
    return '<div class="pv-panel-head"><span class="pv-head-label">' +
      (brand ? '<span class="pv-mini">G.</span>' : '') +
      escapeText(title) + '</span><span class="pv-chip">' + escapeText(chip) + '</span></div>';
  }
  function vocab(rows) {
    return '<div class="pv-vocab">' + rows.map(row =>
      '<div class="pv-word"><span class="pv-term">' + escapeText(row[0]) +
      '<small>' + escapeText(row[1]) + '</small></span><span class="pv-meaning">' +
      escapeText(row[2]) + '</span></div>'
    ).join('') + '</div>';
  }
  function resultWrap(chip, content) {
    return '<div class="pv-result">' + panelHeading('GLOSSA AI', chip, true) +
      '<div class="pv-result-card"><div class="pv-result-inner pv-promise">' + content +
      '</div></div></div>';
  }
  function sourceWrap(title, chip, source, description) {
    return '<div class="pv-source">' + panelHeading(title, chip) + source +
      '<p class="pv-panel-caption">' + description + '</p></div>';
  }
  function title(text) {
    return '<div class="pv-label">' + escapeText(text) + '</div>';
  }
  function writingPreview() {
    const doc = '<div class="pv-editor"><div class="pv-editor-meta"><span>Message to a colleague</span><span>EN</span></div>' +
      '<p>Hi Alex,</p><p>I wanted to follow up on our meeting. <mark class="pv-highlight">' +
      'She don\'t know why the schedule changed.</mark> Could you share the latest version?</p>' +
      '<p>Thanks!</p><span class="pv-selection-hint"><span class="pv-mini">G.</span> Fix grammar</span></div>';
    const result = '<div class="pv-actions"><span class="active">Fix Grammar</span><span>Natural</span><span>Professional</span></div>' +
      title('SUGGESTED CORRECTION') + '<p class="pv-primary-answer">She <strong>doesn\'t</strong> know why the schedule changed.</p>' +
      '<div class="pv-explain"><strong>What changed?</strong><p>With “she”, use “doesn\'t” rather than “don\'t”. Keep the main verb in its base form.</p></div>' +
      title('WHY IT HELPS') + '<p class="pv-panel-caption">Understand your mistakes, not just the correction.</p>';
    return sourceWrap('ORIGINAL WRITING','On a webpage',doc,'Select text and use Glossa to improve grammar without losing your meaning.') +
      resultWrap('Writing',result);
  }
  function readingPreview() {
    const doc = '<div class="pv-editor"><div class="pv-editor-meta"><span>Reading a Japanese article</span><span>JA</span></div>' +
      '<p class="pv-article-title" lang="ja">読むことの楽しさ</p>' +
      '<p class="pv-jp" lang="ja">毎日の小さな発見が、人生を豊かにする。</p>' +
      '<p class="pv-jp" lang="ja"><mark class="pv-highlight">読書は、新しい世界への扉を開く。</mark></p>' +
      '<span class="pv-selection-hint"><span class="pv-mini">G.</span> Understand text</span></div>';
    const result = title('MEANING') +
      '<p class="pv-primary-answer">“Reading opens the door to new worlds.”</p>' +
      '<div class="pv-explain"><strong>BEYOND THE WORDS</strong><p>“Opens the door” is a metaphor for discovering new perspectives, not a literal door.</p></div>' +
      title('VOCABULARY') +
      vocab([['読書','どくしょ / Dokusho','Reading books'], ['世界','せかい / Sekai','World'], ['扉','とびら / Tobira','Door']]);
    return sourceWrap('HIGHLIGHTED TEXT','Japanese article',doc,'Read the translation, cultural nuance, and vocabulary directly from a selected sentence.') +
      resultWrap('Reading',result);
  }
  function ocrPreview(which) {
    const isArabic = which === 'arabic';
    const img = isArabic ? 'ocr-arabic.svg' : 'ocr-naruto.webp';
    const label = isArabic ? 'Arabic book · close-up' : 'Naruto manga · user-provided page';
    const alt = isArabic
      ? 'Close-up of a white Arabic book page with Arabic text without vowel marks.'
      : 'User-provided Naruto manga page, with an OCR selection over the speech bubble in the upper right.';
    const source = '<div class="pv-image ' + (isArabic ? 'pv-arabic-image' : 'pv-manga-image') + '">' +
      '<img src="assets/img/' + img + '" alt="' + alt + '" width="960" height="660" loading="lazy">' +
      (!isArabic ? '<span class="pv-ocr-active" aria-hidden="true"><i></i>OCR ACTIVE</span>' : '') +
      '<div class="pv-scanning" aria-hidden="true"></div></div>';
    const arabicRows = [['العلم','Al-ʿilm','Knowledge'], ['الفهم','Al-fahm','Understanding'], ['الحكمة','Al-ḥikmah','Wisdom']];
    const japaneseRows = [['懐かしい','なつかしい / Natsukashii','Nostalgic']];
    const recognized = isArabic
      ? '<div class="pv-ocr-text" lang="ar" dir="rtl">العلم نور، والفهم مفتاح الحكمة.</div>'
      : '<div class="pv-ocr-text" lang="ja">なっつかしーっ!!</div>';
    const translated = isArabic
      ? '“Knowledge is light, and understanding is the key to wisdom.”'
      : '“So nostalgic!”';
    const explanation = isArabic
      ? 'The sentence uses “light” and “key” as metaphors for learning and understanding.'
      : 'An excited, casual form of 懐かしい (natsukashii), expressing nostalgia at seeing a familiar place again.';
    const result = title('RECOGNIZED TEXT') + recognized + title('TRANSLATION') +
      '<p class="pv-primary-answer">' + translated + '</p>' +
      '<div class="pv-explain"><strong>MEANING &amp; CONTEXT</strong><p>' + explanation + '</p></div>' +
      title('VOCABULARY') + vocab(isArabic ? arabicRows : japaneseRows);
    const desc = isArabic
      ? 'Select a sentence from a white book page to reveal its meaning, transliteration, and key words.'
      : 'Select dialogue from the provided Naruto manga page to understand the wording and tone.';
    return sourceWrap('SOURCE IMAGE',label,source,desc) + resultWrap('OCR · ' + (isArabic ? 'AR → EN' : 'JA → EN'),result);
  }

  function draw() {
    stage.innerHTML = '<div class="pv-scene">' +
      (mode === 'writing' ? writingPreview() : mode === 'reading' ? readingPreview() : ocrPreview(sample)) +
      '</div>';
    stage.setAttribute('aria-labelledby', 'pv-tab-' + mode);
    exampleChooser.hidden = mode !== 'ocr';
    sourceTabs.forEach(tab => {
      const selected = tab.dataset.pvMode === mode;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    exampleTabs.forEach(tab => {
      const selected = tab.dataset.pvSample === sample;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
  }

  function setStage(next) {
    root.dataset.stage = next;
    const order = ['select', 'analyze', 'done'];
    root.querySelectorAll('[data-pv-step]').forEach(item => {
      const step = item.dataset.pvStep;
      item.classList.toggle('is-active',step === next);
      item.classList.toggle('is-complete', order.indexOf(step) < order.indexOf(next));
    });
  }

  function replay() {
    clearAnimation();
    // Respect visitors who prefer less animation and avoid unnecessary waits.
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setStage('done');
      announcer.textContent = 'Preview result ready';
      return;
    }
    const currentRun = runNumber;
    setStage('select');
    announcer.textContent = 'Selected content is ready for Glossa';
    scheduled.push(setTimeout(() => {
      if (runNumber !== currentRun) return;
      setStage('analyze');
      announcer.textContent = 'Analyzing selected text';
    }, 850));
    scheduled.push(setTimeout(() => {
      if (runNumber !== currentRun) return;
      setStage('done');
      announcer.textContent = 'Preview result ready';
    }, 1850));
  }

  function selectMode(next, focus = false) {
    if (!['writing','reading','ocr'].includes(next)) return;
    mode = next;
    draw();
    replay();
    if (focus) document.getElementById('pv-tab-' + mode)?.focus();
  }

  function selectSample(next, focus = false) {
    if (!['arabic', 'naruto'].includes(next)) return;
    sample = next;
    draw();
    replay();
    if (focus) document.getElementById('pv-sample-' + sample)?.focus();
  }

  function wireTabs(tabs, attribute, choose) {
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => choose(tab.dataset[attribute]));
      tab.addEventListener('keydown', event => {
        if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
        event.preventDefault();
        let nextIndex = index;
        if (event.key === 'Home') nextIndex = 0;
        if (event.key === 'End') nextIndex = tabs.length - 1;
        if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
        choose(tabs[nextIndex].dataset[attribute], true);
      });
    });
  }

  wireTabs(sourceTabs, 'pvMode', selectMode);
  wireTabs(exampleTabs, 'pvSample', selectSample);
  replayButton.addEventListener('click', replay);
  draw();
  setStage('done');

  // Do not start auto-playing animations until visitors explicitly switch tabs
  // or press Replay; a static result is the default for reduced motion.
})();
