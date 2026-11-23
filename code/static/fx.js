// Small interaction effects for the inner pages, written in plain JavaScript.
// Ideas adapted from React Bits (Decrypted Text, Tilted Card, Glare Hover,
// Count Up, Spotlight Card). Everything is skipped when the visitor asks for
// reduced motion, and pointer effects only run with a real mouse.
(() => {
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const seen = (el, fn, threshold = 0.4) => {
    if (!('IntersectionObserver' in window)) return fn();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { io.disconnect(); fn(); } });
    }, { threshold });
    io.observe(el);
  };

  // Decrypted text: letters cycle through random glyphs, then settle left to right.
  const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#$%&*+<>?';
  const decrypt = (el) => {
    if (el.dataset.busy) return;
    const target = el.dataset.text;
    el.dataset.busy = '1';
    let frame = 0;
    const total = target.length * 3 + 12;
    const tick = () => {
      frame += 1;
      const settled = Math.max(0, Math.floor((frame - 12) / 3));
      let out = '';
      for (let i = 0; i < target.length; i += 1) {
        const ch = target[i];
        out += i < settled || ch === ' ' ? ch : GLYPHS[(Math.random() * GLYPHS.length) | 0];
      }
      el.lastChild.textContent = out;
      if (frame < total) setTimeout(tick, 45);
      else { el.lastChild.textContent = target; delete el.dataset.busy; }
    };
    tick();
  };
  document.querySelectorAll('[data-decrypt]').forEach((el) => {
    const text = el.textContent.trim();
    el.dataset.text = text;
    el.textContent = '';
    // Screen readers get the real text once; the scrambling copy is hidden from them
    const real = document.createElement('span');
    real.className = 'sr-only';
    real.textContent = text;
    const span = document.createElement('span');
    span.setAttribute('aria-hidden', 'true');
    span.textContent = text;
    el.appendChild(real);
    el.appendChild(span);
    if (still) return;
    // On the home page the title sits in a story beat that fades in; decode
    // each time that beat turns on. Elsewhere, decode when it scrolls into view.
    const beat = el.closest('.beat');
    if (beat && 'MutationObserver' in window) {
      let on = beat.classList.contains('is-on');
      if (on) decrypt(el);
      new MutationObserver(() => {
        const now = beat.classList.contains('is-on');
        if (now && !on) decrypt(el);
        on = now;
      }).observe(beat, { attributes: true, attributeFilter: ['class'] });
    } else {
      seen(el, () => decrypt(el));
    }
    const trigger = el.closest('.project-card') || el;
    trigger.addEventListener('mouseenter', () => decrypt(el));
    trigger.addEventListener('focusin', () => decrypt(el));
  });

  // Count up: numbers ease up from zero the first time they scroll into view.
  document.querySelectorAll('[data-count]').forEach((el) => {
    const end = Number(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    if (still) { el.textContent = end + suffix; return; }
    el.textContent = '0' + suffix;
    seen(el, () => {
      const start = performance.now();
      const ms = 1100 + Math.min(end, 400) * 2;
      const step = (now) => {
        const t = Math.min(1, (now - start) / ms);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(end * eased) + suffix;
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, 0.6);
  });

  if (still || !fine) return;

  // Tilt and glare on project covers: the screenshot leans toward the cursor
  // and a soft light streak follows it.
  document.querySelectorAll('.project-cover').forEach((cover) => {
    let raf = 0;
    const move = (e) => {
      const r = cover.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        cover.style.setProperty('--ry', ((x - 0.5) * 12).toFixed(2) + 'deg');
        cover.style.setProperty('--rx', ((0.5 - y) * 9).toFixed(2) + 'deg');
        cover.style.setProperty('--gx', (x * 100).toFixed(1) + '%');
        cover.style.setProperty('--gy', (y * 100).toFixed(1) + '%');
      });
    };
    cover.addEventListener('pointerenter', () => cover.classList.add('is-tilting'));
    cover.addEventListener('pointermove', move);
    cover.addEventListener('pointerleave', () => {
      cancelAnimationFrame(raf);
      cover.classList.remove('is-tilting');
      ['--rx', '--ry'].forEach((p) => cover.style.setProperty(p, '0deg'));
    });
  });

  // Spotlight cards: a soft light follows the pointer across the card.
  document.querySelectorAll('[data-spotlight]').forEach((card) => {
    card.addEventListener('pointermove', (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  });
})();
