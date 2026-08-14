/* 135er-Grow Central alpha-0.7.5 device extensions */
(() => {
  const byId = (id) => document.getElementById(id);
  const html = (value) => String(value ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
  const cameraDevices = new Map();
  const controlLabels = {
    brightness:"Helligkeit", contrast:"Kontrast", saturation:"Sättigung", sharpness:"Schärfe",
    white_balance_temperature_auto:"Weißabgleich automatisch", white_balance_temperature:"Weißabgleich",
    exposure_auto:"Belichtung automatisch", exposure_absolute:"Belichtungszeit", exposure_auto_priority:"Belichtungspriorität",
    focus_auto:"Autofokus", focus_absolute:"Manueller Fokus", zoom_absolute:"Zoom",
    power_line_frequency:"Netzfrequenz", backlight_compensation:"Gegenlichtausgleich", gain:"Verstärkung",
  };

  // Normal browser writes are authorized by the authenticated Grow Central GUI
  // session. A local API token remains optional for external/test clients and
  // can still be supplied explicitly, but the GUI must never prompt for the
  // factory test token after the mandatory first-boot login is configured.
  writeApi = async function(url, options = {}, providedToken = "") {
    const token = providedToken || sessionStorage.getItem("gcLocalWriteToken") || "";
    if (providedToken) sessionStorage.setItem("gcLocalWriteToken", providedToken);
    const headers = new Headers(options.headers || {});
    if (token) headers.set("X-API-Token", token);
    headers.set("Content-Type", "application/json");
    return api(url, {...options, headers});
  };

  const legacyTapoToken = byId("tapoApiToken");
  if (legacyTapoToken) {
    legacyTapoToken.required = false;
    legacyTapoToken.value = "";
    const label = legacyTapoToken.closest("label");
    if (label) label.style.display = "none";
  }

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

  let fritzPurpose = {purpose:"devices"};
  let fritzConfigured = false;
  function openFritzLogin(detail={purpose:"devices"}) {
    fritzPurpose=detail;
    const labels={devices:"Geräte und Messwerte lesen",automations:"Routinen und Vorlagen lesen",switch:"Steckdose schalten",trigger:"Routine ändern",template:"Vorlage anwenden"};
    byId("fritzLoginPurpose").textContent=`${labels[detail.purpose]||"FRITZ!-Aufruf"}. Nach erfolgreicher Prüfung werden Benutzer und Passwort verschlüsselt auf diesem Grow-Central-Gerät gespeichert und künftig automatisch verwendet.`;
    const dialog=byId("fritzLoginDialog");if(dialog&&!dialog.open)dialog.showModal();
  }

  async function loadFritzCredentialStatus() {
    const card=byId("fritzPresence");
    try {
      const data=await api("/api/v1/smarthome/onboarding/fritz/credentials");
      fritzConfigured=Boolean(data.configured);
      if(card)card.innerHTML=fritzConfigured?`<div class="device-row"><div><strong>FRITZ!Box eingerichtet</strong><span>${html(data.host)} · Benutzer ${html(data.username)}</span></div><span class="badge-online">GESPEICHERT</span></div>`:'<div class="empty-state">FRITZ!Box noch nicht eingerichtet. Die erste erfolgreiche Anmeldung wird sicher gespeichert.</div>';
      const host=byId("fritzHost");if(host&&data.host)host.value=data.host;
      const username=byId("fritzUsername");if(username&&data.username)username.value=data.username;
      const manual=byId("fritzManualBtn");if(manual)manual.textContent=fritzConfigured?"FRITZ! DATEN AKTUALISIEREN":"FRITZ! EINRICHTEN";
      ["fritzChangeBtn","fritzDeleteBtn"].forEach(id=>{const button=byId(id);if(button)button.hidden=!fritzConfigured});
      if(fritzConfigured)await loadFritzDevicesForAutomation();
      return fritzConfigured;
    } catch(error) {
      fritzConfigured=false;
      if(card)card.innerHTML=`<div class="empty-state">FRITZ!-Status fehlgeschlagen: ${html(error.message)}</div>`;
      return false;
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
      card.innerHTML = `<div class="device-row"><div><strong>FRITZ!Box erkannt</strong><span>${html(data.host)} · ${html(data.fingerprint || "AVM")}</span></div><span class="badge-online">BEREIT</span></div>`;
      const host = byId("fritzHost"); if (host) host.value = data.host || "fritz.box";
    } catch (error) {
      card.innerHTML = `<div class="empty-state">FRITZ!-Erkennung fehlgeschlagen: ${html(error.message)}</div>`;
    }
  }

  async function loadRegisteredDevices() {
    const target=byId("registeredDeviceList");if(!target)return;
    try {
      const devices=await api("/api/v1/smarthome/devices");
      target.innerHTML=devices.length?devices.map(row=>`<div class="device-row"><div><strong>${html(row.name)}</strong><span>${html(row.adapter.toUpperCase())} · ${html(row.metadata?.product||row.capability||"Smart Home")} · ID ${html(row.id)}</span></div><span class="${row.approved?"badge-online":"badge-offline"}">${row.approved?"DAUERHAFT":"NICHT FREIGEGEBEN"}</span></div>`).join(""):'<div class="empty-state">Noch kein Smart-Home-Gerät dauerhaft registriert.</div>';
    } catch(error) { target.innerHTML=`<div class="empty-state">Geräteregistrierung konnte nicht gelesen werden: ${html(error.message)}</div>`; }
  }
  window.gcLoadRegisteredDevices=loadRegisteredDevices;

  async function fritzLogin(event) {
    event.preventDefault();
    const status = byId("fritzLoginStatus");
    status.textContent = "FRITZ!Box wird geprüft und die Anmeldung sicher gespeichert…";
    const credentials={host:byId("fritzHost").value.trim()||"fritz.box",username:byId("fritzUsername").value.trim(),password:byId("fritzPassword").value,import_devices:true};
    try {
      const pending=fritzPurpose;
      const data=await writeApi("/api/v1/smarthome/onboarding/fritz/login",{method:"POST",body:JSON.stringify(credentials)});
      window.gcManualFritzDevices=data.imported||[];updateAutomationDevices(data.imported||[]);
      byId("fritzPassword").value = "";
      status.textContent = "Anmeldung geprüft und verschlüsselt gespeichert.";
      byId("fritzLoginDialog")?.close();
      await loadFritzCredentialStatus();await loadRegisteredDevices();await refreshPower();window.gcManualFritzDevices=[];
      if(pending.purpose!=="devices")await executeStoredFritz(pending);
    } catch (error) {
      status.textContent = `FRITZ!-LOGIN FEHLER: ${error.message}`;
    }
  }

  async function executeStoredFritz(detail={purpose:"devices"}) {
    if(detail.purpose==="devices"){
      const data=await writeApi("/api/v1/smarthome/onboarding/fritz/login",{method:"POST",body:JSON.stringify({import_devices:true})});
      window.gcManualFritzDevices=data.imported||[];updateAutomationDevices(data.imported||[]);await loadRegisteredDevices();await refreshPower();window.gcManualFritzDevices=[];return data;
    }
    if(detail.purpose==="automations"){
      const data=await writeApi("/api/v1/smarthome/onboarding/fritz/automations",{method:"POST",body:JSON.stringify({import_devices:false})});renderFritzAutomations(data);return data;
    }
    if(detail.purpose==="switch"){
      const data=await writeApi(`/api/v1/smarthome/devices/${encodeURIComponent(detail.id)}/switch`,{method:"POST",body:JSON.stringify({on:detail.on})});
      await refreshPower(true);return data;
    }
    if(detail.purpose==="trigger"){
      const data=await writeApi("/api/v1/smarthome/onboarding/fritz/automations/trigger",{method:"POST",body:JSON.stringify({import_devices:false,identifier:detail.identifier,active:detail.active})});
      await executeStoredFritz({purpose:"automations"});return data;
    }
    if(detail.purpose==="template")return writeApi("/api/v1/smarthome/onboarding/fritz/automations/template",{method:"POST",body:JSON.stringify({import_devices:false,identifier:detail.identifier})});
  }

  async function useFritz(detail={purpose:"devices"}) {
    if(!fritzConfigured&&!(await loadFritzCredentialStatus())){openFritzLogin(detail);return;}
    try { await executeStoredFritz(detail); }
    catch(error) {
      const target=detail.purpose==="automations"?byId("fritzAutomationList"):byId("fritzPresence");
      if(target)target.innerHTML=`<div class="empty-state">FRITZ!-AUFRUF FEHLER: ${html(error.message)}</div>`;
    }
  }

  function renderFritzAutomations(data){const target=byId("fritzAutomationList");if(!target)return;const triggers=(data.triggers||[]).map(row=>`<article class="automation-card"><small>FRITZ!-ROUTINE</small><strong>${html(row.name)}</strong><span>${row.active?"AKTIV":"INAKTIV"}</span><button class="secondary" data-fritz-trigger="${html(row.identifier)}" data-active="${!row.active}">${row.active?"DEAKTIVIEREN":"AKTIVIEREN"}</button></article>`);const templates=(data.templates||[]).map(row=>`<article class="automation-card"><small>${row.scenario?"FRITZ!-SZENARIO":"FRITZ!-VORLAGE"}</small><strong>${html(row.name)}</strong><span>${html((row.actions||[]).join(" · ")||"Aktion")}</span><button class="secondary" data-fritz-template="${html(row.identifier)}">ANWENDEN</button></article>`);target.innerHTML=[...triggers,...templates].join("")||'<div class="empty-state">Die FRITZ!Box meldet keine Routinen oder sichtbaren Vorlagen.</div>';document.querySelectorAll("[data-fritz-trigger]").forEach(button=>button.addEventListener("click",()=>useFritz({purpose:"trigger",identifier:button.dataset.fritzTrigger,active:button.dataset.active==="true"})));document.querySelectorAll("[data-fritz-template]").forEach(button=>button.addEventListener("click",()=>useFritz({purpose:"template",identifier:button.dataset.fritzTemplate})))}

  function updateAutomationDevices(devices=window.gcManualFritzDevices){const select=byId("automationDevice");if(!select)return;select.innerHTML=devices.length?devices.map(row=>`<option value="${html(row.id)}" data-ain="${html(row.state?.ain||"")}">${html(row.state?.native_name||row.name)}</option>`).join(""):'<option value="">Zuerst FRITZ! einrichten</option>'}
  async function loadFritzDevicesForAutomation(){try{const data=await api("/api/v1/smarthome/overview");updateAutomationDevices((data.devices||[]).filter(row=>row.adapter==="fritz"&&row.state?.ain))}catch{updateAutomationDevices()}}
  async function loadLocalAutomations(){try{const data=await api("/api/v1/automations");const target=byId("localAutomationList");target.innerHTML=data.automations?.length?data.automations.map(row=>`<article class="automation-card"><small>GROW CENTRAL · ${html(row.trigger)}</small><strong>${html(row.name)}</strong><span>${html(row.device_id)} → ${row.on?"EIN":"AUS"}</span><div class="button-row"><button class="secondary" data-run-automation="${html(row.id)}" data-ain="${html(row.ain)}" data-device="${html(row.device_id)}" data-on="${row.on}">MANUELL AUSFÜHREN</button><button class="ghost" data-delete-automation="${html(row.id)}">LÖSCHEN</button></div></article>`).join(""):'<div class="empty-state">Noch keine lokale Automation erstellt.</div>';document.querySelectorAll("[data-run-automation]").forEach(button=>button.addEventListener("click",()=>useFritz({purpose:"switch",id:button.dataset.device,ain:button.dataset.ain,on:button.dataset.on==="true"})));document.querySelectorAll("[data-delete-automation]").forEach(button=>button.addEventListener("click",async()=>{await writeApi(`/api/v1/automations/${encodeURIComponent(button.dataset.deleteAutomation)}`,{method:"DELETE"});await loadLocalAutomations()}))}catch(error){byId("localAutomationList").innerHTML=`<div class="empty-state">${html(error.message)}</div>`}}
  async function createAutomation(event){event.preventDefault();const option=byId("automationDevice").selectedOptions[0];if(!option?.value)return;await writeApi("/api/v1/automations",{method:"POST",body:JSON.stringify({name:byId("automationName").value,trigger:byId("automationTrigger").value,trigger_value:byId("automationTriggerValue").value,device_id:option.value,ain:option.dataset.ain,on:byId("automationAction").value==="on",enabled:true})});event.currentTarget.reset();await loadLocalAutomations()}

  function controlWidget(cameraId, control) {
    const label = controlLabels[control.name] || control.name;
    const manualFocus = control.name === "focus_absolute";
    if (!control.writable && !manualFocus) return `<div class="camera-control readonly"><span>${html(label)}</span><strong>${html(control.value)}</strong><small>read-only/inaktiv</small></div>`;
    if (control.menu?.length) {
      return `<label class="camera-control"><span>${html(label)}</span><select data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}">${control.menu.map((item) => `<option value="${item.value}" ${item.value === control.value ? "selected" : ""}>${html(item.label)}</option>`).join("")}</select></label>`;
    }
    if (control.type === "bool") {
      return `<label class="camera-control ${control.name === "focus_auto" ? "focus-control" : ""}"><span>${html(label)}</span><input type="checkbox" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}" ${control.value ? "checked" : ""}></label>`;
    }
    if (Number.isFinite(control.min) && Number.isFinite(control.max)) {
      return `<label class="camera-control ${manualFocus ? "focus-control" : ""}"><span>${html(label)} <b>${html(control.value)}</b></span><input type="range" min="${control.min}" max="${control.max}" step="${control.step || 1}" value="${control.value}" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}">${manualFocus && !control.writable ? "<small>Autofokus wird beim Verstellen automatisch ausgeschaltet.</small>" : ""}</label>`;
    }
    return `<label class="camera-control"><span>${html(label)}</span><input type="number" value="${html(control.value)}" data-camera-control="${html(control.name)}" data-camera-id="${html(cameraId)}"></label>`;
  }

  async function setCameraControl(element) {
    const value = element.type === "checkbox" ? (element.checked ? 1 : 0) : Number(element.value);
    try {
      const data = await writeApi("/api/v1/camera/controls", {method:"POST", body:JSON.stringify({camera_id:element.dataset.cameraId, control:element.dataset.cameraControl, value})});
      const parent = element.closest(".camera-control"); const label = parent?.querySelector("span b"); if (label) label.textContent = data.control?.value ?? value;
      const action = data.auto_focus_disabled ? "Autofokus deaktiviert · " : "";
      byId("cameraStatusText").textContent = `${action}${controlLabels[element.dataset.cameraControl] || element.dataset.cameraControl} = ${data.control?.value ?? value}`;
      await loadCameraControls(element.dataset.cameraId);
      await refreshCameraSnapshot(element.dataset.cameraId);
    } catch (error) {
      byId("cameraStatusText").textContent = `KAMERA-CONTROL FEHLER: ${error.message}`;
    }
  }

  function bindCameraControls() {
    document.querySelectorAll("[data-camera-control]").forEach((element) => {
      element.addEventListener("change", () => setCameraControl(element));
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

  async function refreshCameraSnapshot(cameraId) {
    const image = byId("cameraSnapshot"); if (!image) return;
    await stopCameraLive(false);
    image.dataset.live = "false";
    if (byId("cameraLiveBtn")) byId("cameraLiveBtn").textContent = "▶";
    image.onerror = () => { byId("cameraStatusText").textContent = "KAMERA-SNAPSHOT FEHLER: Der gewählte Videoknoten liefert kein Bild."; };
    image.src = `/api/v1/camera/snapshot?camera_id=${encodeURIComponent(cameraId)}${cameraModeQuery()}&t=${Date.now()}`;
  }

  async function stopCameraLive(showStatus = false) {
    const image = byId("cameraSnapshot");
    const button = byId("cameraLiveBtn");
    const wasLive = image?.dataset.live === "true";
    if (wasLive) image.src = "";
    if (image) image.dataset.live = "false";
    if (button) { button.textContent = "▶"; button.setAttribute("aria-label", "Livebild starten"); }
    if (wasLive) {
      try {
        await writeApi("/api/v1/camera/stream/stop", {method:"POST", body:"{}"});
      } catch (error) {
        if (showStatus) byId("cameraStatusText").textContent = `LIVEBILD-STOP FEHLER: ${error.message}`;
      }
    }
    return wasLive;
  }

  async function toggleCameraLive() {
    const image = byId("cameraSnapshot");
    const button = byId("cameraLiveBtn");
    const selected = document.querySelector("[data-camera-select].active")?.dataset.cameraSelect;
    if (!image || !button || !selected) return;
    if (image.dataset.live === "true") {
      await stopCameraLive(true);
      await refreshCameraSnapshot(selected);
      byId("cameraStatusText").textContent = "Livebild gestoppt.";
      return;
    }
    await stopCameraLive(false);
    image.dataset.live = "true";
    image.onerror = async () => {
      if (image.dataset.live !== "true") return;
      await stopCameraLive(false);
      byId("cameraStatusText").textContent = "LIVEBILD FEHLER: Der Kamerastream wurde beendet. Bitte erneut starten.";
    };
    image.src = `/api/v1/camera/stream?camera_id=${encodeURIComponent(selected)}${cameraModeQuery()}&t=${Date.now()}`;
    button.textContent = "■";
    button.setAttribute("aria-label", "Livebild stoppen");
    const option = byId("cameraResolutionSelect")?.selectedOptions?.[0];
    byId("cameraStatusText").textContent = `MJPEG-Livebild läuft mit ${option?.textContent || "Kamera-Standard"}.`;
  }

  function cameraModeQuery() {
    const option = byId("cameraResolutionSelect")?.selectedOptions?.[0];
    return option?.dataset.width ? `&width=${encodeURIComponent(option.dataset.width)}&height=${encodeURIComponent(option.dataset.height)}` : "";
  }

  function populateCameraModes(cameraId) {
    const select = byId("cameraResolutionSelect");
    const device = cameraDevices.get(cameraId);
    if (!select) return;
    const modes = device?.mjpeg_modes || [];
    select.innerHTML = modes.map((mode) => `<option data-width="${mode.width}" data-height="${mode.height}" ${mode.width === 640 && mode.height === 480 ? "selected" : ""}>${html(mode.label || `${mode.width} × ${mode.height}`)} · ${html((mode.fps || []).join("/"))} fps</option>`).join("");
    select.disabled = !modes.length;
    if (!modes.length) select.innerHTML = "<option>Keine MJPEG-Auflösung</option>";
  }

  async function loadSystemIdentity() {
    try {
      const data = await api("/api/v1/system/info");
      const set = (id, value) => { const element=byId(id); if(element) element.textContent=value || "Nicht verfügbar"; };
      set("systemHostname", data.hostname); set("systemPiModel", data.model); set("systemBuildVersion", `${data.version} · Build ${data.build}`);
      set("systemDomain", data.domain); set("systemPrimaryIp", data.primary_ipv4); set("systemKernel", `${data.kernel} · ${data.architecture}`);
      set("systemOperatingSystem", data.operating_system); set("systemUptime", data.uptime?.display);
      set("dashboardHostName", data.hostname); set("dashboardPiModel", data.model); set("dashboardBuild", `${data.version} · Build ${data.build}`);
      set("dashboardDomain", data.domain); set("dashboardPrimaryIp", data.primary_ipv4); set("dashboardKernel", `${data.kernel} · ${data.architecture}`);
      set("dashboardOs", data.operating_system); set("dashboardUptime", `UPTIME ${data.uptime?.display || "--"}`);
      const interfaces = (data.interfaces || []).map((row) => `<div class="interface-card"><div><strong>${html(row.name)}</strong><span class="${row.state === "up" ? "badge-online" : "badge-offline"}">${html(row.state.toUpperCase())}</span></div><small>${html(row.mac || "keine MAC")} · MTU ${html(row.mtu)}</small>${row.addresses?.length ? row.addresses.map((address) => `<code>${html(address.family)} · ${html(address.address)}/${html(address.prefix)} · ${html(address.scope)}</code>`).join("") : "<code>Keine IP-Adresse</code>"}</div>`).join("") || '<div class="empty-state">Keine Netzwerkschnittstellen gemeldet.</div>';
      ["dashboardHostInterfaces", "systemInterfaces"].forEach((id) => { const target=byId(id); if(target) target.innerHTML=interfaces; });
    } catch (error) {
      const target = byId("systemPiModel") || byId("dashboardPiModel");
      if (target) target.textContent = `Erkennung fehlgeschlagen: ${error.message}`;
    }
  }

  async function loadCamera() {
    const statusText = byId("cameraStatusText");
    const list = byId("cameraDeviceList");
    if (!statusText || !list) return;
    statusText.textContent = "Kamera wird geprüft…";
    try {
      const data = await api("/api/v1/camera/status?refresh=true");
      cameraDevices.clear(); (data.devices || []).forEach((row) => cameraDevices.set(row.id, row));
      list.innerHTML = data.devices?.length ? data.devices.map((row) => `<button class="camera-device ${row.id === data.selected_camera_id ? "active" : ""}" data-camera-select="${html(row.id)}" title="${html(row.device)}">${row.c920_match?'<img class="camera-model-image" src="/static/device-images/logitech-c920.webp" alt="Logitech C920 Hersteller-Modellbild">':'<span class="webcam-glyph" aria-hidden="true"><i></i></span>'}<strong>${html(row.c920_match ? "C920" : row.name || row.card || row.id)}</strong><small>${row.readable && row.capture_capable ? "BEREIT" : "PRÜFEN"}</small></button>`).join("") : '<div class="empty-state">Keine /dev/video*-Kamera erkannt.</div>';
      statusText.textContent = data.ready ? `${data.selected_is_c920 ? "Logitech C920" : "Kamera"} erkannt und lesbar.` : "Kamera erkannt, aber noch nicht capture-bereit.";
      const selected = data.selected_camera_id;
      document.querySelectorAll("[data-camera-select]").forEach((button) => button.addEventListener("click", async () => { await stopCameraLive(false);document.querySelectorAll("[data-camera-select]").forEach((b)=>b.classList.remove("active"));button.classList.add("active");populateCameraModes(button.dataset.cameraSelect);await loadCameraControls(button.dataset.cameraSelect);await refreshCameraSnapshot(button.dataset.cameraSelect); }));
      if (selected) { populateCameraModes(selected); await loadCameraControls(selected); await refreshCameraSnapshot(selected); }
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
  byId("fritzManualBtn")?.addEventListener("click", async () => { if(fritzConfigured||await loadFritzCredentialStatus())await useFritz({purpose:"devices"});else{await checkFritzPresence();openFritzLogin({purpose:"devices"})} });
  byId("fritzAutomationBtn")?.addEventListener("click", () => useFritz({purpose:"automations"}));
  byId("fritzChangeBtn")?.addEventListener("click", () => openFritzLogin({purpose:"devices"}));
  byId("fritzDeleteBtn")?.addEventListener("click", async () => {if(!confirm("Gespeicherte FRITZ!-Anmeldung wirklich löschen?"))return;await writeApi("/api/v1/smarthome/onboarding/fritz/credentials",{method:"DELETE"});window.gcManualFritzDevices=[];updateAutomationDevices();await loadFritzCredentialStatus();await refreshPower(true)});
  byId("automationCreateForm")?.addEventListener("submit", createAutomation);
  window.addEventListener("gc:fritz-login", event => useFritz(event.detail));
  byId("cameraRefreshBtn")?.addEventListener("click", loadCamera);
  byId("cameraSnapshotBtn")?.addEventListener("click", async () => { const selected=document.querySelector("[data-camera-select].active")?.dataset.cameraSelect; if(selected) await refreshCameraSnapshot(selected); });
  byId("cameraLiveBtn")?.addEventListener("click", toggleCameraLive);
  byId("cameraResolutionSelect")?.addEventListener("change", async () => { const selected=document.querySelector("[data-camera-select].active")?.dataset.cameraSelect; if(selected) await refreshCameraSnapshot(selected); });

  window.addEventListener("gc:view", (event) => {
    if (event.detail.id !== "camera") void stopCameraLive(false);
    if (event.detail.id === "camera") loadCamera();
    if (event.detail.id === "automation") loadLocalAutomations();
    if (event.detail.id === "devices") loadRegisteredDevices();
    if (event.detail.id === "dashboard") loadSystemIdentity();
    if (event.detail.id === "system") { loadSystemIdentity(); loadNetworkStatus(); }
  });

  loadSystemIdentity();
  loadRegisteredDevices();
  loadFritzCredentialStatus();
  loadLocalAutomations();
})();
