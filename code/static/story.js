/* Scroll story engine for the home page.
   Each [data-chapter] is a tall section with a pinned stage. Scroll progress (0 to 1)
   picks the active beat, drives the device animations, and tints the page. */
(() => {
  'use strict';
  const root = document.documentElement;
  const body = document.body;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const clamp = (n, a = 0, b = 1) => Math.min(b, Math.max(a, n));

  const chapters = [...document.querySelectorAll('[data-chapter]')].map(el => ({
    el,
    name: el.dataset.chapter,
    steps: Number(el.dataset.steps || 1),
    beats: [...el.querySelectorAll('[data-beat]')],
    step: -1,
  }));
  const tinted = [...document.querySelectorAll('[data-bg]')];
  const marquees = [...document.querySelectorAll('[data-marquee]')];

  /* HokieWallet pieces */
  const wallet = document.querySelector('.ch-wallet');
  const screens = wallet ? [...wallet.querySelectorAll('[data-screen]')] : [];
  const navs = wallet ? [...wallet.querySelectorAll('[data-screen-link]')] : [];
  const counters = wallet ? [...wallet.querySelectorAll('[data-count]')] : [];
  const langGreet = document.querySelector('[data-lang-greet]');
  const langName = document.querySelector('[data-lang-name]');
  const langDots = document.querySelector('[data-lang-dots]');
  const toggles = wallet ? [...wallet.querySelectorAll('[data-toggle]')] : [];
  const preview = document.querySelector('[data-preview]');
  const greetings = [
    ['English', 'Good to see you, Hokie.', 'ltr'],
    ['Español', 'Qué bueno verte, Hokie.', 'ltr'],
    ['Français', 'Content de te voir, Hokie.', 'ltr'],
    ['Português', 'Que bom te ver, Hokie.', 'ltr'],
    ['Deutsch', 'Schön, dich zu sehen, Hokie.', 'ltr'],
    ['Italiano', 'Che bello vederti, Hokie.', 'ltr'],
    ['Tiếng Việt', 'Rất vui được gặp bạn, Hokie.', 'ltr'],
    ['한국어', '만나서 반가워요, Hokie.', 'ltr'],
    ['日本語', '会えてうれしいです、Hokie。', 'ltr'],
    ['中文', '很高兴见到你，Hokie。', 'ltr'],
    ['हिन्दी', 'आपसे मिलकर खुशी हुई, Hokie।', 'ltr'],
    ['العربية', 'سعيد برؤيتك يا Hokie.', 'rtl'],
  ];
  if (langDots) langDots.innerHTML = greetings.map(() => '<i></i>').join('');
  let langIndex = -1;

  /* Game pieces */
  const shots = [...document.querySelectorAll('.ch-game [data-shot]')];

  /* TopSecret pieces */
  const consoleEl = document.querySelector('.console');
  const roleEl = document.querySelector('[data-role]');
  const msgEl = document.querySelector('[data-msg]');

  /* Intro: split the headline into letters (screen readers keep the aria-label) */
  const title = document.querySelector('[data-split]');
  let letters = [];
  if (title) {
    let i = 0;
    const html = title.innerHTML.split(/<br\s*\/?>/i).map(line =>
      line.trim().split(/\s+/).map(word =>
        '<span class="w" aria-hidden="true">' + [...word].map(c => {
          const fy = (Math.sin(i * 12.9898) * 43758.5453 % 1) * 160 - 40;
          const fr = (Math.cos(i * 4.1414) * 9631.17 % 1) * 24;
          return '<span class="ch" style="--i:' + (i++) + ';--fy:' + fy.toFixed(1) + ';--fr:' + fr.toFixed(1) + '">' + c + '</span>';
        }).join('') + '</span>'
      ).join(' ')
    ).join('<br>');
    title.innerHTML = html;
    letters = [...title.querySelectorAll('.ch')];
    // Letters near the pointer lift toward it
    let raf = 0, px = -1e4, py = -1e4;
    const lift = () => {
      raf = 0;
      for (const l of letters) {
        const r = l.getBoundingClientRect();
        const d = Math.hypot(r.left + r.width / 2 - px, r.top + r.height / 2 - py);
        l.style.setProperty('--lift', Math.max(0, 1 - d / 220) * 26);
      }
    };
    const intro = title.closest('section');
    intro.addEventListener('pointermove', e => {
      if (reduced.matches || e.pointerType !== 'mouse') return;
      px = e.clientX; py = e.clientY;
      if (!raf) raf = requestAnimationFrame(lift);
    });
    intro.addEventListener('pointerleave', () => { px = py = -1e4; if (!raf) raf = requestAnimationFrame(lift); });
  }

  /* Game: 3D turntable drawn from a 24-frame image sequence */
  const tt = document.querySelector('[data-turntable]');
  const tt_canvas = tt ? tt.querySelector('canvas') : null;
  const tt_ctx = tt_canvas ? tt_canvas.getContext('2d') : null;
  const tt_n = tt ? Number(tt.dataset.frames) : 0;
  const tt_frames = [];
  let tt_loaded = false, tt_drag = 0, tt_scroll = 0, tt_shown = -1;
  function ttLoad() {
    if (tt_loaded || !tt) return;
    tt_loaded = true;
    for (let k = 0; k < tt_n; k++) {
      const img = new Image();
      img.decoding = 'async';
      img.src = tt.dataset.src + String(k).padStart(2, '0') + '.webp';
      img.onload = () => { if (tt_shown < 0 || k === ttIndex()) ttDraw(true); };
      tt_frames[k] = img;
    }
  }
  const ttIndex = () => (((17 + Math.round(tt_scroll * tt_n + tt_drag)) % tt_n) + tt_n) % tt_n;
  function ttDraw(force) {
    const k = ttIndex();
    const img = tt_frames[k];
    if (!img || !img.complete || !img.naturalWidth || (k === tt_shown && !force)) return;
    tt_shown = k;
    tt_ctx.clearRect(0, 0, tt_canvas.width, tt_canvas.height);
    tt_ctx.drawImage(img, 0, 0, tt_canvas.width, tt_canvas.height);
  }
  if (tt_canvas) {
    let startX = 0, startDrag = 0, dragging = false;
    tt_canvas.addEventListener('pointerdown', e => { dragging = true; startX = e.clientX; startDrag = tt_drag; tt_canvas.setPointerCapture(e.pointerId); });
    tt_canvas.addEventListener('pointermove', e => { if (!dragging) return; tt_drag = startDrag + (e.clientX - startX) / 18; ttDraw(); });
    const end = () => { dragging = false; };
    tt_canvas.addEventListener('pointerup', end);
    tt_canvas.addEventListener('pointercancel', end);
    tt_canvas.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { tt_drag += e.key === 'ArrowRight' ? 1 : -1; ttDraw(); e.preventDefault(); }
    });
  }

  /* TopSecret: decode text one character at a time */
  const glyphs = '!<>-_\\/[]{}=+*^?#ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
  function scramble(el, text) {
    if (!el || el.dataset.text === text) return;
    el.dataset.text = text;
    if (reduced.matches) { el.textContent = text; return; }
    const from = el.textContent;
    const len = Math.max(from.length, text.length);
    const plan = [];
    for (let k = 0; k < len; k++) {
      const s0 = Math.floor(Math.random() * 12), e0 = s0 + 8 + Math.floor(Math.random() * 16);
      plan.push([from[k] || '', text[k] || '', s0, e0]);
    }
    let f = 0;
    cancelAnimationFrame(el._scr);
    const tick = () => {
      let out = '', done = 0;
      for (const [a, b, s0, e0] of plan) {
        if (f >= e0) { out += b; done++; }
        else if (f >= s0) out += glyphs[Math.floor(Math.random() * glyphs.length)];
        else out += a;
      }
      el.textContent = out;
      if (done < plan.length) { f++; el._scr = requestAnimationFrame(tick); }
    };
    tick();
  }

  /* This site: horizontal track */
  const trackView = document.querySelector('.track-view');
  const track = document.querySelector('.track');
  const wins = track ? [...track.children] : [];
  const typed = document.querySelector('[data-typed]');
  const results = [...document.querySelectorAll('.retro-results li')];
  const checks = [...document.querySelectorAll('[data-checks] li')];
  const testsBar = document.querySelector('.retro-tests');

  const money = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function progressOf(el) {
    const r = el.getBoundingClientRect();
    const travel = r.height - window.innerHeight;
    if (travel <= 0) return clamp(-r.top / Math.max(1, r.height));
    return clamp(-r.top / travel);
  }

  function setStep(ch, step) {
    if (step === ch.step) return;
    ch.step = step;
    ch.beats.forEach(b => b.classList.toggle('is-on', Number(b.dataset.beat) === step));
    ch.el.dataset.step = String(step);
    ch.el.classList.remove(...[...ch.el.classList].filter(c => c.startsWith('step-')));
    ch.el.classList.add('step-' + step);
  }

  function updateWallet(p, step, local) {
    const screen = clamp(step, 1, 4);
    screens.forEach(s => s.classList.toggle('is-on', Number(s.dataset.screen) === screen));
    navs.forEach(n => n.classList.toggle('is-on', Number(n.dataset.screenLink) === screen));
    // Count balances up as the first screen arrives
    const grow = step >= 1 ? 1 : clamp(local * 1.4);
    counters.forEach(c => { c.textContent = money(Number(c.dataset.count) * (reduced.matches ? 1 : grow)); });
    // Languages: walk through every greeting during beat 3
    if (step === 3 && langGreet) {
      const i = Math.min(greetings.length - 1, Math.floor(local * greetings.length));
      if (i !== langIndex) {
        langIndex = i;
        const [name, text, dir] = greetings[i];
        langGreet.textContent = text;
        langGreet.dir = dir;
        langName.textContent = name;
        [...langDots.children].forEach((d, k) => d.classList.toggle('is-on', k === i));
      }
    }
    // Accessibility: flip toggles one after another during beat 4
    if (toggles.length) {
      const on = step > 4 ? 3 : step === 4 ? Math.min(3, Math.floor(local * 4)) : 0;
      toggles.forEach((t, k) => t.classList.toggle('is-on', k < on));
      if (preview) {
        preview.classList.toggle('big', on >= 1);
        preview.classList.toggle('contrast', on >= 2);
      }
    }
  }

  function updateGame(step, local, near) {
    const map = [0, 1, 2, 1, 3];
    const on = map[Math.min(step, map.length - 1)];
    shots.forEach(img => img.classList.toggle('is-on', Number(img.dataset.shot) === on));
    if (!tt) return;
    if (near) ttLoad();
    // During "You become the animal" the cow turns once as you scroll
    if (step === 3 && !reduced.matches) tt_scroll = local;
    else if (step < 3) tt_scroll = 0;
    else if (step > 3) tt_scroll = 1;
    tt_canvas.tabIndex = step === 3 ? 0 : -1;
    ttDraw();
  }

  function updateSecret(step) {
    if (!consoleEl) return;
    const admin = step >= 2;
    consoleEl.classList.toggle('is-admin', step >= 2);
    consoleEl.classList.toggle('show-users', step >= 3);
    consoleEl.classList.toggle('lock-self', step >= 4);
    scramble(roleEl, admin ? 'Signed in as carlos, Admin' : 'Signed in as alex, Standard');
    scramble(msgEl, step === 1 ? 'Two options hidden for this role.'
      : step === 2 ? 'First account registered. You are the administrator.'
      : step === 3 ? 'Choose a user to promote or demote.'
      : step >= 4 ? 'You can’t demote your own account.' : '');
  }

  function tint() {
    // The section crossing the middle of the screen sets the page color
    const mid = window.innerHeight * 0.12;
    let pick = tinted[0];
    for (const el of tinted) {
      const r = el.getBoundingClientRect();
      if (r.top <= mid && r.bottom > mid) { pick = el; break; }
    }
    if (!pick) return;
    const bg = pick.dataset.bg;
    if (root.style.getPropertyValue('--page-bg') !== bg) {
      root.style.setProperty('--page-bg', bg);
      body.classList.toggle('ink-dark', pick.dataset.ink === 'dark');
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', bg);
    }
  }

  function updateOS(p) {
    if (!track) return;
    // Hold each window during its beat and slide between them at the beat boundaries
    const smooth = t => t * t * (3 - 2 * t);
    let pos = 0;
    for (let k = 1; k < wins.length; k++) pos += smooth(clamp((p * wins.length - k + .35) / .7));
    const stride = wins[1].offsetLeft - wins[0].offsetLeft;
    track.style.setProperty('--hx', (-pos * stride).toFixed(1) + 'px');
    wins.forEach((w, k) => { const d = k - pos; w.style.setProperty('--d', d.toFixed(3)); w.style.setProperty('--ad', Math.min(1, Math.abs(d)).toFixed(3)); });
    // Type the search as window 2 arrives, then tick the tests as window 3 arrives
    const word = 'wallet';
    const beat = p * wins.length;
    const n = Math.round(clamp((beat - .95) / .6) * word.length);
    if (typed) typed.textContent = word.slice(0, n);
    results.forEach((li, k) => li.classList.toggle('dim', n > 0 && n < word.length ? false : n === word.length && k > 0));
    const c = Math.floor(clamp((beat - 1.95) / .7) * (checks.length + 1));
    checks.forEach((li, k) => li.classList.toggle('ok', k < c));
    if (testsBar) testsBar.classList.toggle('ok', c > checks.length);
  }

  /* Contact buttons lean toward the pointer */
  document.querySelectorAll('.contact .btn').forEach(b => {
    b.addEventListener('pointermove', e => {
      if (reduced.matches || e.pointerType !== 'mouse') return;
      const r = b.getBoundingClientRect();
      b.style.transform = 'translate(' + ((e.clientX - r.left - r.width / 2) * .25).toFixed(1) + 'px,' + ((e.clientY - r.top - r.height / 2) * .35).toFixed(1) + 'px)';
    });
    b.addEventListener('pointerleave', () => { b.style.transform = ''; });
  });

  let frame = 0;
  function update() {
    frame = 0;
    for (const ch of chapters) {
      const p = progressOf(ch.el);
      ch.el.style.setProperty('--p', p.toFixed(4));
      if (ch.name === 'intro') continue;
      const raw = p * ch.steps;
      const step = Math.min(ch.steps - 1, Math.floor(raw));
      const local = raw - step;
      // Device rises in during the first part of the chapter
      const r = ch.el.getBoundingClientRect();
      const enter = clamp(1 - (r.top / window.innerHeight));
      ch.el.style.setProperty('--enter', reduced.matches ? 1 : enter.toFixed(4));
      if (ch.name === 'secret') {
        ch.el.style.setProperty('--crtX', reduced.matches ? 1 : clamp((enter - .5) / .2).toFixed(4));
        ch.el.style.setProperty('--crtY', reduced.matches ? 1 : clamp((enter - .72) / .26).toFixed(4));
      }
      setStep(ch, step);
      if (ch.name === 'wallet') updateWallet(p, step, local);
      else if (ch.name === 'game') updateGame(step, local, r.top < window.innerHeight * 2.5);
      else if (ch.name === 'secret') updateSecret(step);
      else if (ch.name === 'os') updateOS(p);
    }
    if (!reduced.matches) {
      for (const m of marquees) {
        const r = m.getBoundingClientRect();
        const t = (window.innerHeight - r.top) / (window.innerHeight + r.height);
        const dir = Number(m.dataset.marquee);
        m.style.setProperty('--mx', ((dir > 0 ? -1 : 0) * 0.35 * m.scrollWidth + dir * t * 0.25 * m.scrollWidth).toFixed(1) + 'px');
      }
    }
    tint();
  }
  const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule, { passive: true });
  reduced.addEventListener('change', schedule);
  update();
})();
