// First-party visit analytics. No cookies, nothing personal: a random id that
// lives only in this tab, the page, what was clicked, and how long the page was open.
// Honors Do Not Track and Global Privacy Control, and skips the site owner's own visits.
(() => {
  try {
    if (navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return;
    if (localStorage.getItem('cz-notrack')) return;
  } catch (e) { /* storage blocked: carry on without it */ }
  const id = () => Math.random().toString(36).slice(2, 12).padEnd(10, '0');
  let sid;
  try { sid = sessionStorage.getItem('cz-sid') || id(); sessionStorage.setItem('cz-sid', sid); } catch (e) { sid = id(); }
  const pv = id();
  const path = location.pathname;
  let sent = 0;
  const send = (kind, extra) => {
    if (sent++ > 150) return; // cap per page so a stuck loop can't flood the server
    const body = JSON.stringify(Object.assign({ kind, sid, pv, path, w: window.innerWidth }, extra));
    // Sent as plain text: the most reliable kind of beacon while a page is closing
    if (!(navigator.sendBeacon && navigator.sendBeacon('/t', body))) {
      fetch('/t', { method: 'POST', body, keepalive: true }).catch(() => {});
    }
  };

  let ref = '';
  try { const host = new URL(document.referrer).hostname; if (host && host !== location.hostname) ref = host.replace(/^www\./, ''); } catch (e) { /* no referrer */ }
  send('view', { ref });

  // Clicks on links and buttons, named by what the visitor saw
  document.addEventListener('click', (e) => {
    const el = e.target.closest('a, button, summary');
    if (!el) return;
    const decoded = el.querySelector('[data-text]'); // animated titles: use the real text, not the scramble
    let label = el.dataset.track || el.getAttribute('aria-label') || (decoded ? decoded.dataset.text : el.textContent) || '';
    label = label.replace(/\s+/g, ' ').trim().slice(0, 60);
    if (!label) return;
    const href = el.getAttribute('href') || '';
    if (/^https?:/.test(href)) { try { label += ' → ' + new URL(href).hostname.replace(/^www\./, ''); } catch (err) { /* keep label */ } }
    else if (/\.pdf$/.test(href)) label += ' (PDF)';
    send('click', { label });
  }, true);

  // Home page: which project sections a visitor actually reached
  if ('IntersectionObserver' in window) {
    const seen = new Set();
    const io = new IntersectionObserver((entries) => entries.forEach((entry) => {
      const name = entry.target.dataset.chapter;
      if (entry.isIntersecting && !seen.has(name)) { seen.add(name); send('section', { label: name }); }
    }), { threshold: 0.6 });
    document.querySelectorAll('[data-chapter]').forEach((el) => io.observe(el));
  }

  // Time on page (only while the tab is visible) and how far down they scrolled
  let active = 0, since = document.hidden ? 0 : performance.now(), deepest = 0;
  const measure = () => {
    const room = document.documentElement.scrollHeight - window.innerHeight;
    deepest = Math.max(deepest, room > 0 ? Math.round(100 * window.scrollY / room) : 100);
  };
  addEventListener('scroll', measure, { passive: true });
  measure();
  const leave = () => {
    if (since) { active += performance.now() - since; since = 0; }
    send('leave', { ms: Math.round(active), depth: Math.min(100, deepest) });
  };
  const report = () => {
    const now = since ? active + performance.now() - since : active;
    send('leave', { ms: Math.round(now), depth: Math.min(100, deepest) });
  };
  document.addEventListener('visibilitychange', () => { if (document.hidden) leave(); else since = performance.now(); });
  addEventListener('pagehide', leave);
  // Phones often drop the closing beacon, so also check in at a few points while the page is open
  [3, 10, 30, 60, 120, 300].forEach((s) => setTimeout(() => { if (!document.hidden) report(); }, s * 1000));
})();
