/* Guided setup for a sensor attached to the Raspberry Pi, never the browser PC. */
(() => {
  const panel = document.getElementById('sensorPairing');
  if (!panel) return;
  const make = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  const section = make('section', null, 'usb-onboarding');
  section.append(make('h4', 'USB-Sensor am Raspberry Pi einrichten'));
  const intro = make('p', 'Sensor per Daten-USB-Kabel direkt an den Pi anschließen. GC führt dich durch Firmware, WLAN und Raumzuweisung.');
  section.append(intro);
  const list = make('div', null, 'usb-device-list'); section.append(list); panel.prepend(section);
  const status = make('p', '', 'pairing-feedback'); status.setAttribute('role', 'status'); section.append(status);
  const labels = {DETECTED:'USB erkannt', CHECKING:'Firmware prüfen', NEEDS_FIRMWARE:'Firmware benötigt', FLASHING:'Firmware installieren', NETWORK:'WLAN einrichten', PROVISIONING:'Zugang einrichten', CONNECTING:'Verbindung prüfen', ASSIGN:'Name und Raum', READY:'Bereit', BLOCKED:'Entscheidung prüfen', ERROR:'Einrichtung prüfen'};
  const stage = state => ({DETECTED:0, CHECKING:1, NEEDS_FIRMWARE:1, FLASHING:1, NETWORK:2, PROVISIONING:2, CONNECTING:2, ASSIGN:3, READY:4, ERROR:0}[state] ?? 0);
  const dialog = document.createElement('dialog'); dialog.className = 'pairing-dialog usb-dialog';
  dialog.innerHTML = '<h2>USB-Sensor einrichten</h2><ol class="usb-steps"><li>USB</li><li>Firmware</li><li>WLAN</li><li>Raum</li><li>Bereit</li></ol><p class="usb-current" role="status"></p><div class="usb-content"></div><p class="usb-error" role="alert"></p><button type="button" class="usb-close">Schließen</button>';
  document.body.append(dialog);
  dialog.querySelector('.usb-close').onclick = () => dialog.close();
  let devices = [], selected = null, renderedState = '', firmwareReady = false, activeRequest = false, polling = false;
  const content = dialog.querySelector('.usb-content');
  const error = dialog.querySelector('.usb-error');
  async function api(path, options = {}) {
    const response = await fetch('/api/devices/usb' + path, {credentials:'same-origin', cache:'no-store', ...options, headers:{'Content-Type':'application/json', ...options.headers}});
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Anfrage fehlgeschlagen.');
    return body;
  }
  async function action(path, body) {
    if (activeRequest) return;
    activeRequest = true; error.textContent = '';
    content.querySelectorAll('button').forEach(button => { button.disabled = true; });
    try {
      await api('/' + encodeURIComponent(selected.id) + path, {method:'POST', ...(body ? {body:JSON.stringify(body)} : {})});
      renderedState = ''; await refresh();
    } catch (e) { error.textContent = e.message; renderedState = ''; renderDialog(); }
    finally { activeRequest = false; }
  }
  function button(text, handler) { const b = make('button', text); b.type = 'button'; b.onclick = handler; return b; }
  function field(form, title, name, type = 'text') {
    const label = make('label', title); const input = document.createElement('input');
    input.name = name; input.type = type; input.required = true; label.append(input); form.append(label); return input;
  }
  function open(device) {
    selected = device; renderedState = ''; error.textContent = ''; renderDialog(); dialog.showModal();
  }
  function renderDialog() {
    if (!selected) return;
    dialog.querySelector('.usb-current').textContent = selected.message;
    [...dialog.querySelectorAll('.usb-steps li')].forEach((li, index) => {
      li.classList.toggle('done', index < stage(selected.state));
      li.classList.toggle('current', index === stage(selected.state));
      if (index === stage(selected.state)) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    dialog.querySelector('.usb-close').textContent = selected.busy ? 'Im Hintergrund fortsetzen' : 'Schließen';
    const key = selected.state + ':' + selected.busy;
    if (renderedState === key) return;
    renderedState = key; content.replaceChildren();
    if (selected.busy) { content.append(make('p', 'Der Schritt läuft weiter, wenn du den Dialog schließt. Beim Flashen das USB-Kabel angeschlossen lassen.')); return; }
    if (['DETECTED','NEEDS_FIRMWARE'].includes(selected.state) || (selected.state === 'ERROR' && selected.resume !== 'NETWORK')) {
      content.append(button('Angeschlossenen Sensor prüfen', () => action('/inspect')));
      const form = document.createElement('form');
      const label = make('label', 'Sensor-Board'); const select = document.createElement('select');
      const option = make('option', 'Seeed XIAO ESP32-C3 · GC Soil / HW-390'); option.value = 'seeed_xiao_esp32c3'; select.append(option); label.append(select); form.append(label);
      const confirmation = make('label', null, 'usb-confirmation'); const check = document.createElement('input'); check.type = 'checkbox'; check.required = true;
      confirmation.append(check, make('span', 'Dieses USB-Gerät ist mein XIAO ESP32-C3. GC darf die Sensor-Firmware installieren; Identität und Kalibrierung bleiben erhalten.')); form.append(confirmation);
      form.append(make('p', firmwareReady ? 'GC nutzt ausschließlich das geprüfte Firmware-Paket dieses Images. Kein vollständiges Löschen des Flash-Speichers.' : 'Das Firmware-Paket fehlt. Installiere das aktuelle USB-Test-Image.'));
      const install = make('button', 'Firmware installieren'); install.type = 'submit'; install.disabled = !firmwareReady; form.append(install);
      form.onsubmit = e => { e.preventDefault(); action('/flash', {board:select.value, confirmed:check.checked}); };
      content.append(form);
      if (selected.device_id) content.append(button('Vorhandene Verbindung erneut prüfen', () => action('/connection')));
    }
    if (selected.state === 'NETWORK' || (selected.state === 'ERROR' && selected.resume === 'NETWORK')) renderNetwork();
    if (selected.state === 'BLOCKED') content.append(make('p', 'Die frühere Sperre bleibt bestehen. Prüfe die Sensorliste unterhalb des USB-Bereichs; anschließend kannst du hier erneut prüfen.'), button('USB-Identität erneut prüfen', () => action('/inspect')));
    if (selected.state === 'ASSIGN') renderAssignment();
    if (selected.state === 'READY') {
      content.append(make('h3', selected.name || 'Sensor bereit'), make('p', 'Aufnahme und Raumzuweisung sind gespeichert. Messwerte im zugewiesenen Raum prüfen.'), button('Zu den Räumen', () => {
        dialog.close(); (document.querySelector('#mainNav [data-view="rooms"]') || document.querySelector('.bottom-nav [data-tab="rooms"]') || document.querySelector('[data-view="rooms"]'))?.click();
        window.dispatchEvent(new Event('gc:refresh'));
      }));
    }
    if (selected.fingerprint) {
      const details = document.createElement('details'); details.append(make('summary', 'Geprüfte USB-Identität'), make('code', selected.device_id + '\n' + selected.fingerprint)); content.append(details);
    }
  }
  async function renderNetwork() {
    const identity = selected.id; const form = document.createElement('form');
    const ssid = field(form, 'WLAN des Sensors', 'ssid'); ssid.maxLength = 32; ssid.autocomplete = 'off';
    const password = field(form, 'WLAN-Kennwort', 'password', 'password'); password.minLength = 8; password.maxLength = 63; password.autocomplete = 'new-password';
    const label = make('label', 'Dieser Pi als MQTT-Broker'); const host = document.createElement('select'); host.required = true; label.append(host); form.append(label);
    form.append(make('p', 'GC erstellt das lokale Zertifikat und einen individuellen Sensorzugang und überträgt sie direkt per USB.'));
    const submit = make('button', 'WLAN und Sensorzugang einrichten'); submit.type = 'submit'; submit.disabled = true; form.append(submit); content.append(form);
    content.append(button('Sensor hat bereits eine Verbindung – prüfen', () => action('/connection')));
    form.onsubmit = e => {
      e.preventDefault(); const body = {ssid:ssid.value, password:password.value, broker_host:host.value}; password.value = ''; action('/network', body);
    };
    try {
      const result = await api('/broker');
      if (selected?.id !== identity || !form.isConnected) return;
      for (const name of result.hosts || []) { const o = make('option', name); o.value = name; host.append(o); }
      if ([...host.options].some(option => option.value === location.hostname)) host.value = location.hostname;
      submit.disabled = !result.ready || !host.options.length;
      if (!result.ready) error.textContent = result.message;
    } catch (e) { error.textContent = e.message; }
  }
  async function renderAssignment() {
    const identity = selected.id; const form = document.createElement('form');
    const name = field(form, 'Sensorname', 'name'); name.maxLength = 120; name.value = selected.name || 'Bodenfeuchte';
    const label = make('label', 'Raum / Growbox'); const rooms = document.createElement('select'); rooms.required = true; label.append(rooms); form.append(label);
    const details = document.createElement('details'); details.append(make('summary', 'Neuen Raum anlegen'));
    const roomName = document.createElement('input'); roomName.placeholder = 'Raumname'; roomName.maxLength = 80; roomName.setAttribute('aria-label', 'Neuer Raumname'); details.append(roomName);
    const create = button('Raum anlegen', async () => {
      if (!roomName.value.trim()) return;
      create.disabled = true;
      try {
        const response = await fetch('/api/v1/rooms', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:roomName.value.trim()})});
        if (!response.ok) throw new Error('Raum konnte nicht angelegt werden.');
        const room = await response.json(); const option = make('option', room.name); option.value = room.id; rooms.append(option); rooms.value = room.id; submit.disabled = false; details.open = false;
      } catch (e) { error.textContent = e.message; } finally { create.disabled = false; }
    }); details.append(create); form.append(details);
    form.append(make('p', 'GC gleicht die USB-Identität mit der aktuellen Netzwerk-Identität ab. Erst deine Aufnahme erlaubt produktive Raumdaten.'));
    const submit = make('button', 'Sensor aufnehmen und zuweisen'); submit.type = 'submit'; submit.disabled = true; form.append(submit); content.append(form);
    form.onsubmit = async e => {
      e.preventDefault(); await action('/assign', {name:name.value, room_id:rooms.value}); window.dispatchEvent(new Event('gc:refresh'));
    };
    try {
      const response = await fetch('/api/v1/rooms', {credentials:'same-origin', cache:'no-store'});
      if (!response.ok) throw new Error('Räume konnten nicht geladen werden.');
      const result = await response.json();
      if (selected?.id !== identity || !form.isConnected) return;
      for (const room of result.rooms || []) { const option = make('option', room.name); option.value = room.id; rooms.append(option); }
      submit.disabled = !rooms.options.length; details.open = !rooms.options.length;
    } catch (e) { error.textContent = e.message; }
  }
  async function refresh() {
    if (polling) return;
    polling = true;
    try {
      const result = await api(''); devices = result.devices || []; firmwareReady = result.firmware_ready;
      list.replaceChildren();
      for (const device of devices) {
        const row = make('article', null, 'pairing-card'); const info = make('div');
        info.append(make('strong', device.name || device.label), make('small', device.port + ' · ' + (device.firmware || 'Firmware noch nicht geprüft')), make('span', labels[device.state], 'pairing-status'));
        row.append(info, button(device.state === 'READY' ? 'Anzeigen' : device.busy ? 'Fortschritt anzeigen' : 'Einrichten', () => open(device))); list.append(row);
      }
      if (!devices.length) list.append(make('p', 'Noch kein unterstützter USB-Kandidat am Pi. Datenkabel verwenden; reine Ladekabel werden nicht erkannt.'));
      status.textContent = '';
      if (selected && dialog.open) {
        const current = devices.find(device => device.id === selected.id);
        if (current) { selected = current; renderDialog(); }
        else { const session=(result.sessions||[]).find(item=>item.id===selected.id);if(session){selected={...selected,...session};renderDialog();}error.textContent='USB-Gerät wurde getrennt. Wieder an den Pi anschließen.';content.querySelectorAll('button').forEach(b=>{b.disabled=true;});renderedState=''; }
      }
      window.dispatchEvent(new CustomEvent('gc:usb-sessions', {detail:devices}));
    } catch (e) { status.textContent = e.message; }
    finally { polling = false; }
  }
  window.addEventListener('gc:refresh', refresh); refresh(); setInterval(refresh, 3000);
})();
