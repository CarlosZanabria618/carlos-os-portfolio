// Live demo for the TopSecret page. Same substitution rules as the Java version:
// a key maps each cipher character to a real one, the key must not repeat a
// character, and anything outside the key passes through unchanged.
(() => {
  const root = document.querySelector('[data-cipher]');
  if (!root) return;
  const REAL = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const input = root.querySelector('[data-plain]');
  const coded = root.querySelector('[data-coded]');
  const decoded = root.querySelector('[data-decoded]');
  const keyRow = root.querySelector('[data-key]');
  let cipher = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'; // sample key, made up for this page

  const buildMaps = (real, key) => {
    if (real.length !== key.length) throw new Error('Wrong length');
    const decode = new Map(), encode = new Map();
    for (let i = 0; i < real.length; i += 1) {
      if (decode.has(key[i])) throw new Error('Duplicate key');
      decode.set(key[i], real[i]);
      encode.set(real[i], key[i]);
    }
    return { decode, encode };
  };
  const swap = (text, map) => [...text].map((c) => (map.has(c) ? map.get(c) : c)).join('');

  const render = () => {
    const { decode, encode } = buildMaps(REAL, cipher);
    const secret = swap(input.value, encode);
    coded.textContent = secret || ' ';
    decoded.textContent = swap(secret, decode) || ' ';
    keyRow.textContent = 'a-z becomes ' + cipher.slice(0, 26);
  };
  root.querySelector('[data-shuffle]').addEventListener('click', () => {
    const mix = (s) => { const a = [...s]; for (let i = a.length - 1; i > 0; i -= 1) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.join(''); };
    const lower = mix(REAL.slice(0, 26));
    cipher = lower + lower.toUpperCase();
    render();
  });
  input.addEventListener('input', render);
  root.hidden = false;
  render();
})();
