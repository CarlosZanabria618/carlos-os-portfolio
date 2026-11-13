/* Progressive enhancement: the complete site works without motion or JavaScript. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const small = window.matchMedia('(max-width: 720px)');
  const reveals = [...document.querySelectorAll('[data-reveal]')];
  const hero = document.querySelector('[data-hero-scene]');
  const story = document.querySelector('[data-scroll-story]');
  const steps = story ? [...story.querySelectorAll('[data-story-step]')] : [];
  let observer;
  let frame = 0;
  let storyIndex = -1;
  const clamp = (n, min = 0, max = 1) => Math.max(min, Math.min(max, n));

  function setupReveals() {
    observer?.disconnect();
    root.classList.remove('reveal-ready');
    if (reduced.matches || !('IntersectionObserver' in window)) {
      reveals.forEach(el => el.classList.add('is-visible'));
      return;
    }
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -32px 0px', threshold: 0.08 });
    reveals.forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight - 32 && rect.bottom > 0) el.classList.add('is-visible');
      if (!el.classList.contains('is-visible')) observer.observe(el);
    });
    root.classList.add('reveal-ready');
  }

  function update() {
    frame = 0;
    root.classList.toggle('has-scrolled', window.scrollY > 24);
    if (reduced.matches) {
      hero?.style.removeProperty('--hero-progress');
      story?.style.removeProperty('--story-progress');
      story?.classList.remove('story-ready');
      return;
    }
    if (hero) {
      const rect = hero.getBoundingClientRect();
      const progress = clamp((window.innerHeight - rect.top) / (window.innerHeight + rect.height));
      hero.style.setProperty('--hero-progress', progress.toFixed(4));
    }
    if (story && steps.length) {
      story.classList.toggle('story-ready', !small.matches);
      const rect = story.getBoundingClientRect();
      const progress = clamp((window.innerHeight * 0.5 - rect.top) / Math.max(1, rect.height - window.innerHeight * 0.25));
      story.style.setProperty('--story-progress', progress.toFixed(4));
      let nearest = 0;
      let distance = Infinity;
      steps.forEach((step, i) => {
        const position = step.getBoundingClientRect();
        const current = Math.abs(position.top + position.height / 2 - window.innerHeight / 2);
        if (current < distance) { distance = current; nearest = i; }
      });
      if (nearest !== storyIndex) {
        storyIndex = nearest;
        story.dataset.step = String(nearest);
        steps.forEach((step, i) => step.classList.toggle('is-active', i === nearest));
      }
    }
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(update); }
  setupReveals();
  update();
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('pageshow', () => { setupReveals(); schedule(); });
  reduced.addEventListener('change', () => { setupReveals(); schedule(); });
  small.addEventListener('change', schedule);
})();
