/* 135er-Grow Central alpha-0.7.5 device extensions */
(() => {
  const byId = (id) => document.getElementById(id);
  const html = (value) => String(value ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));

  async function loadNetworkStatus() {
    const target = byId("networkStatus");
    if (!target) return;
    try {
      const data = await api("/api/v1/network/status");
      const rows = data.interfaces || [];
      target.innerHTML = rows.length ? rows.map((row) => `<div class="device-row"><div><strong>${html(row.device)}</strong><span>${html(row.type)} · ${html(row.connection || "keine Verbindung")}</span></div><span class="${["connected","verbunden"].includes(row.state) ? "badge-online" : "badge-offline"}">${html(row.state)}</span></div>`).join("") : '<div class="empty-state">Keine Netzwerkschnittstellen gemeldet.</div>';
    } catch (error) {
      target.innerHTML = `<div class="empty-state">Netzwerkstatus fehlgeschlagen: ${html(error.message)}</div>`;
    }
  }

  async function scanWifi() {
    const button = byId("wifiScanBtn");
    const status = byId("wifiScanStatus");
    const list = byId("wifiList");
    if (!button || !status || !list) return;
    button.disabled = true;
    status.textContent = "WLAN-SCAN LÄUFT…";
    try {
      const data = await api("/api/v1/network/wifi");
      if (!data.ok) throw new Error(data.message || "WLAN-Scan fehlgeschlagen");
      status.textContent = data.count ? `${data.count} WLAN-Netzwerk(e) gefunden.` : "Keine WLAN-Netzwerke gefunden.";
      list.innerHTML = data.networks?.length ? data.networks.map((row) => `<label class="wifi-row"><input type="radio" name="guiWifiSsid" value="${html(row.ssid)}"><span><strong>${html(row.ssid)}</strong><small>${html(row.security)} · ${row.signal}%${row.connected ? " · VERBUNDEN" : ""}</small></span></label>`).join("") : '<div class="empty-state">Keine Netze gefunden.</div>';
    } catch (error) {
      status.textContent = `WLAN-SCAN FEHLER: ${error.message}`;
      list.innerHTML = '<div class="empty-state">Erneut scannen oder Netzwerkverbindung prüfen.</div>';
    } finally {
      button.disabled = false;
    }
  }

  async function joinWifi(event) {
    event.preventDefault();
    const status = byId("wifiScanStatus");
    const selected = document.querySelector('input[name="guiWifiSsid"]:checked');
    const manual = byId("wifiManualSsid")?.value.trim();
    const ssid = manual || selected?.value || "";
    const password = byId("wifiJoinPassword")?.value || "";
    if (!ssid) { status.textContent = "Bitte ein WLAN auswählen oder die SSID eingeben."; return; }
    status.textContent = `Verbinde mit ${ssid}…`;
    try {
      await writeApi("/api/v1/network/wifi/join", {method:"POST", body:JSON.stringify({ssid,password})});
      status.textContent = `WLAN ${ssid} verbunden. Die aktuelle Browser-Verbindung kann kurz unterbrochen werden.`;
      if (byId("wifiJoinPassword")) byId("wifiJoinPassword").value = "";
      setTimeout(loadNetworkStatus, 1800);
    } catch (error) {
      status.textContent = `WLAN-VERBINDUNG FEHLER: ${error.message}`;
    }
  }

  async function checkFritzPresence() {
    const card = byId("fritzPresence");
    if (!card) return;
    try {
      const data = await api("/api/v1/smarthome/onboarding/fritz/presence");
      if (!data.detected) {
        card.innerHTML = '<div class="empty-state">Keine FRITZ!Box eindeutig erkannt.</div>';
        return;
      }
      card.innerHTML = `<div class="device-row"><div><strong>FRITZ!Box erkannt</strong><span>${html(data.host)} · ${html(data.fingerprint || "AVM")}</span></div><span class="badge-online">LOGIN NÖTIG</span></div>`;
      const host = byId("fritzHost"); if (host) host.value = data.host || "fritz.box";
      const dialog = byId("fritzLoginDialog"); if (dialog && typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
    } catch (error) {
      card.innerHTML = `<div class="empty-state">FRITZ!-Erkennung fehlgeschlagen: ${html(error.message)}</div>`;
    }
  }

  async function fritzLogin(event) {
    event.preventDefault();
    const status = byId("fritzLoginStatus");
    status.textContent = "FRITZ!Box wird angemeldet und Smart-Home-Geräte werden gelesen…";
    try {
      const data = await writeApi("/api/v1/smarthome/onboarding/fritz/login", {method:"POST", body:JSON.stringify({host:byId("fritzHost").value.trim() || "fritz.box",username:byId("fritzUsername").value.trim(),password:byId("fritzPassword").value,import_devices:true})});
      byId("fritzPassword").value = "";
      status.textContent = `${data.devices_found} FRITZ!-Gerät(e) gefunden, ${data.imported?.length || 0} importiert.`;
      byId("fritzLoginDialog")?.close();
      await refreshPower();
      checkFritzPresence();
    } catch (error) {
      status.textContent = `FRITZ!-LOGIN FEHLER: ${error.message}`;
    }
  }

  function controlWidget(cameraId, control) {
    if (!control.writable) return `<div class="camera-control readonly"><span>${html(control.name)}</span><strong>${html(control.value)}</strong><small>read-only/inaktiv</small></div>`;
    if (control.menu?.length) {
      return `<label class="camera-control"><span>${html(control.name)}</span><select data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}">${control.menu.map((item) => `<option value="${item.value}" ${item.value === control.value ? "selected" : ""}>${html(item.label)}</option>`).join("")}</select></label>`;
    }
    if (control.type === "bool") {
      return `<label class="camera-control"><span>${html(control.name)}</span><input type="checkbox" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}" ${control.value ? "checked" : ""}></label>`;
    }
    if (Number.isFinite(control.min) && Number.isFinite(control.max)) {
      return `<label class="camera-control"><span>${html(control.name)} <b>${html(control.value)}</b></span><input type="range" min="${control.min}" max="${control.max}" step="${control.step || 1}" value="${control.value}" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}"></label>`;
    }
    return `<label class="camera-control"><span>${html(control.name)}</span><input type="number" value="${html(control.value)}" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}"></label>`;
  }

  async function setCameraControl(element) {
    let value = element.type === "checkbox" ? (element.checked ? 1 : 0) : Number(element.value);
    try {
      const data = await writeApi("/api/v1/camera/controls", {method:"POST", body:JSON.stringify({camera_id:element.dataset.cameraId, control:element.dataset.cameraControl, value})});
      const parent = element.closest(".camera-control"); const label = parent?.querySelector("span b"); if (label) label.textContent = data.control?.value ?? value;
      byId("cameraStatusText").textContent = `${element.dataset.cameraControl} = ${data.control?.value ?? value}`;
      refreshCameraSnapshot(element.dataset.cameraId);
    } catch (error) {
      byId("cameraStatusText").textContent = `KAMERA-CONTROL FEHLER: ${error.message}`;
    }
  }

  function bindCameraControls() {
    document.querySelectorAll("[data-camera-control]").forEach((element) => {
      const eventName = element.type === "range" ? "change" : "change";
      element.addEventListener(eventName, () => setCameraControl(element));
      if (element.type === "range") element.addEventListener("input", () => { const b=element.closest(".camera-control")?.querySelector("span b"); if(b)b.textContent=element.value; });
    });
  }

  async function loadCameraControls(cameraId) {
    const target = byId("cameraControls");
    target.innerHTML = '<div class="empty-state">Kamerafunktionen werden gelesen…</div>';
    try {
      const data = await api(`/api/v1/camera/controls?camera_id=${encodeURIComponent(cameraId)}`);
      target.innerHTML = data.controls?.length ? data.controls.map((control) => controlWidget(cameraId, control)).join("") : '<div class="empty-state">Diese Kamera meldet keine einstellbaren V4L2-Regler.</div>';
      bindCameraControls();
    } catch (error) {
      target.innerHTML = `<div class="empty-state">Kamerafunktionen konnten nicht gelesen werden: ${html(error.message)}</div>`;
    }
  }

  function refreshCameraSnapshot(cameraId) {
    const image = byId("cameraSnapshot"); if (!image) return;
    image.src = `/api/v1/camera/snapshot?camera_id=${encodeURIComponent(cameraId)}&t=${Date.now()}`;
  }

  async function loadCamera() {
    const statusText = byId("cameraStatusText");
    const list = byId("cameraDeviceList");
    if (!statusText || !list) return;
    statusText.textContent = "Kamera wird geprüft…";
    try {
      const data = await api("/api/v1/camera/status");
      list.innerHTML = data.devices?.length ? data.devices.map((row) => `<button class="camera-device ${row.id === data.selected_camera_id ? "active" : ""}" data-camera-select="${html(row.id)}"><strong>${html(row.name || row.card || row.id)}</strong><span>${html(row.device)} · ${row.c920_match ? "Logitech C920" : html(row.driver || "UVC/V4L2")}</span><small>${row.readable ? "READ OK" : "NO READ"} · ${row.capture_capable ? "CAPTURE" : "NO CAPTURE"}</small></button>`).join("") : '<div class="empty-state">Keine /dev/video*-Kamera erkannt.</div>';
      statusText.textContent = data.ready ? `${data.selected_is_c920 ? "Logitech C920" : "Kamera"} erkannt und lesbar.` : "Kamera erkannt, aber noch nicht capture-bereit.";
      const selected = data.selected_camera_id;
      document.querySelectorAll("[data-camera-select]").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll("[data-camera-select]").forEach((b)=>b.classList.remove("active"));button.classList.add("active");loadCameraControls(button.dataset.cameraSelect);refreshCameraSnapshot(button.dataset.cameraSelect); }));
      if (selected) { await loadCameraControls(selected); refreshCameraSnapshot(selected); }
    } catch (error) {
      statusText.textContent = `KAMERA FEHLER: ${error.message}`;
      list.innerHTML = '<div class="empty-state">Kamera-API nicht verfügbar.</div>';
    }
  }

  byId("wifiScanBtn")?.addEventListener("click", scanWifi);
  byId("wifiJoinForm")?.addEventListener("submit", joinWifi);
  byId("networkRefreshBtn")?.addEventListener("click", loadNetworkStatus);
  byId("fritzLoginForm")?.addEventListener("submit", fritzLogin);
  byId("fritzCancelBtn")?.addEventListener("click", () => byId("fritzLoginDialog")?.close());
  byId("cameraRefreshBtn")?.addEventListener("click", loadCamera);
  byId("cameraSnapshotBtn")?.addEventListener("click", () => { const selected=document.querySelector("[data-camera-select].active")?.dataset.cameraSelect; if(selected) refreshCameraSnapshot(selected); });

  loadNetworkStatus();
  checkFritzPresence();
  loadCamera();
})();
