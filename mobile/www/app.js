(() => {
  const input = document.getElementById('endpoint');
  const form = document.getElementById('connect-form');
  const setup = document.getElementById('setup');
  const status = document.getElementById('status');
  const platformLabel = document.getElementById('platformLabel');
  const saved = localStorage.getItem('gc.endpoint');

  const ua = navigator.userAgent || '';
  if (/iPhone|iPad|iPod/i.test(ua)) platformLabel.textContent = 'IOS · SIDELOAD CLIENT';
  else if (/Android/i.test(ua)) platformLabel.textContent = 'ANDROID · APK CLIENT';

  if (saved) input.value = saved;

  function setStatus(message, type = '') {
    status.textContent = message;
    status.className = `status ${type}`.trim();
  }

  function isPrivateHost(host) {
    return host.endsWith('.local') || host === '10.42.0.1' || /^10\./.test(host) || /^192\.168\./.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host);
  }

  function normalize(value) {
    let raw = value.trim();
    if (!raw) throw new Error('Bitte eine Grow-Central-Adresse eingeben.');
    if (!/^https?:\/\//i.test(raw)) raw = `http://${raw}`;
    const url = new URL(raw);
    if (url.username || url.password) throw new Error('Zugangsdaten gehören nicht in die URL.');
    const host = url.hostname.toLowerCase();
    if (!isPrivateHost(host) && url.protocol !== 'https:') throw new Error('Remote-Adressen müssen HTTPS verwenden.');
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Nur HTTP oder HTTPS ist erlaubt.');
    url.hash = '';
    url.search = '';
    url.pathname = '/';
    return url.toString();
  }

  function mobileUrl(endpoint) {
    const url = new URL(endpoint);
    url.pathname = '/mobile';
    url.search = '';
    url.hash = '';
    return url.toString();
  }

  function connect(value) {
    try {
      const endpoint = normalize(value);
      localStorage.setItem('gc.endpoint', endpoint);
      setStatus('Mobile Grow Central wird geöffnet …', 'success');
      window.location.assign(mobileUrl(endpoint));
    } catch (error) {
      setStatus(error.message || 'Ungültige Adresse.', 'error');
    }
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    connect(input.value);
  });

  setup.addEventListener('click', () => {
    input.value = 'http://10.42.0.1/';
    connect(input.value);
  });
})();
