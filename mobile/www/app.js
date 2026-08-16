(() => {
  const input = document.getElementById('endpoint');
  const form = document.getElementById('connect-form');
  const setup = document.getElementById('setup');
  const status = document.getElementById('status');
  const saved = localStorage.getItem('gc.endpoint');
  if (saved) input.value = saved;

  function normalize(value) {
    let raw = value.trim();
    if (!raw) throw new Error('Bitte eine Adresse eingeben.');
    if (!/^https?:\/\//i.test(raw)) raw = `http://${raw}`;
    const url = new URL(raw);
    if (url.username || url.password) throw new Error('Zugangsdaten gehören nicht in die URL.');
    const host = url.hostname.toLowerCase();
    const local = host.endsWith('.local') || host === '10.42.0.1' || /^10\./.test(host) || /^192\.168\./.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host);
    if (!local && url.protocol !== 'https:') throw new Error('Remote-Adressen müssen HTTPS verwenden.');
    url.hash = '';
    return url.toString();
  }

  function connect(value) {
    try {
      const endpoint = normalize(value);
      localStorage.setItem('gc.endpoint', endpoint);
      status.textContent = 'Verbindung wird geöffnet …';
      window.location.assign(endpoint);
    } catch (error) {
      status.textContent = error.message || 'Ungültige Adresse.';
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
