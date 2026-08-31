const STORE = {
  points: "aguaviva2:pontos",
  formulas: "aguaviva2:formulas",
  groups: "aguaviva2:groups",
  users: "aguaviva2:users",
  invites: "aguaviva2:invites",
  profile: "aguaviva2:profile",
  theme: "aguaviva2:theme",
};

function readStore(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}

function writeStore(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function uid(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function applyTheme() {
  const dark = localStorage.getItem(STORE.theme) === "dark";
  document.documentElement.classList.toggle("dark", dark);
}

function initMap() {
  const mapEl = document.querySelector("#map");
  if (!mapEl || typeof L === "undefined") return;

  const params = new URLSearchParams(location.search);
  const startLat = Number(params.get("lat"));
  const startLon = Number(params.get("lon"));
  const hasStart = Number.isFinite(startLat) && Number.isFinite(startLon);
  const map = L.map(mapEl).setView(hasStart ? [startLat, startLon] : [-15.78, -47.93], hasStart ? 14 : 4);
  const pointsLayer = L.layerGroup().addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  function renderPoints() {
    const points = readStore(STORE.points, []);
    pointsLayer.clearLayers();
    const list = document.querySelector("#map-points-list");
    list.innerHTML = "";

    if (!points.length) {
      list.innerHTML = '<p class="empty-text">Nenhum ponto local ainda.</p>';
      return;
    }

    points.forEach((point) => {
      L.marker([point.lat, point.lon])
        .bindPopup(`<strong>${point.nome}</strong><br>IQA: ${point.iqa || "pendente"}<br>${point.classificacao || "Pendente"}`)
        .addTo(pointsLayer);

      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `<strong>${point.nome}</strong><span>${Number(point.lat).toFixed(6)}, ${Number(point.lon).toFixed(6)}</span><span>${point.classificacao || "Pendente"} ${point.iqa ? `- IQA ${point.iqa}` : ""}</span>`;
      row.addEventListener("click", () => map.setView([point.lat, point.lon], 15));
      list.append(row);
    });
  }

  map.on("click", (event) => {
    const url = `/?lat=${event.latlng.lat.toFixed(6)}&lon=${event.latlng.lng.toFixed(6)}`;
    L.popup()
      .setLatLng(event.latlng)
      .setContent(`<a href="${url}">Cadastrar ponto aqui</a>`)
      .openOn(map);
  });

  document.querySelector("#map-use-location").addEventListener("click", () => {
    navigator.geolocation?.getCurrentPosition((position) => {
      map.setView([position.coords.latitude, position.coords.longitude], 15);
    });
  });

  document.querySelector("#clear-map-points").addEventListener("click", () => {
    if (!confirm("Limpar pontos salvos localmente neste navegador?")) return;
    writeStore(STORE.points, []);
    renderPoints();
  });

  renderPoints();
}

function formulaDefaults() {
  return [
    { id: uid("formula"), name: "Percentual do score", expression: "{SCORE} / 24 * 100" },
    { id: uid("formula"), name: "IQA ajustado por OD", expression: "({IQA} * 0.8) + ({OD} * 2)" },
  ];
}

function getFormulaContext() {
  const values = {};
  document.querySelectorAll("[data-sim]").forEach((input) => {
    values[input.dataset.sim] = Number(input.value || 0);
  });
  values.SCORE = ["LIXO", "ODOR", "ESPUMAS", "MATA_CILIAR", "PH", "NITRITO", "FOSFATO", "TURBIDEZ"]
    .reduce((sum, key) => sum + Number(values[key] || 0), 0);
  return values;
}

function evaluateExpression(expression, context) {
  const normalized = expression.replace(/\{([A-Z_]+)\}/gi, (_, key) => {
    const value = context[key.toUpperCase()];
    if (value == null || Number.isNaN(Number(value))) throw new Error(`Variavel sem valor: ${key}`);
    return String(value);
  });

  if (!/^[0-9+\-*/%().,\s]+$/.test(normalized)) {
    throw new Error("Expressao contem caracteres nao permitidos.");
  }

  const value = Function(`"use strict"; return (${normalized.replaceAll(",", ".")});`)();
  if (!Number.isFinite(value)) throw new Error("Resultado invalido.");
  return Math.round(value * 1000) / 1000;
}

function initFormulas() {
  const list = document.querySelector("#formulas-list");
  if (!list) return;

  let editingId = null;
  let formulas = readStore(STORE.formulas, null);
  if (!formulas) {
    formulas = formulaDefaults();
    writeStore(STORE.formulas, formulas);
  }

  const editor = document.querySelector(".formula-editor");
  const name = document.querySelector("#formula-name");
  const expression = document.querySelector("#formula-expression");

  function render() {
    const ctx = getFormulaContext();
    list.innerHTML = "";
    formulas.forEach((formula) => {
      let result;
      try {
        result = evaluateExpression(formula.expression, ctx);
      } catch (error) {
        result = error.message;
      }
      const item = document.createElement("div");
      item.className = "list-item formula-item";
      item.innerHTML = `<div><strong>${formula.name}</strong><code>${formula.expression}</code><span>Resultado: ${result}</span></div><div class="mini-actions"><button type="button" data-edit="${formula.id}" class="ghost-button">Editar</button><button type="button" data-delete="${formula.id}" class="danger-button">Excluir</button></div>`;
      list.append(item);
    });
  }

  document.querySelector("#add-formula").addEventListener("click", () => {
    editingId = null;
    name.value = "";
    expression.value = "";
    editor.hidden = false;
    name.focus();
  });

  document.querySelector("#cancel-formula").addEventListener("click", () => {
    editor.hidden = true;
  });

  document.querySelector("#save-formula").addEventListener("click", () => {
    if (!name.value.trim() || !expression.value.trim()) return;
    if (editingId) {
      formulas = formulas.map((item) => item.id === editingId ? { ...item, name: name.value.trim(), expression: expression.value.trim() } : item);
    } else {
      formulas.push({ id: uid("formula"), name: name.value.trim(), expression: expression.value.trim() });
    }
    writeStore(STORE.formulas, formulas);
    editor.hidden = true;
    render();
  });

  list.addEventListener("click", (event) => {
    const editId = event.target.dataset.edit;
    const deleteId = event.target.dataset.delete;
    if (editId) {
      const formula = formulas.find((item) => item.id === editId);
      if (!formula) return;
      editingId = editId;
      name.value = formula.name;
      expression.value = formula.expression;
      editor.hidden = false;
    }
    if (deleteId) {
      formulas = formulas.filter((item) => item.id !== deleteId);
      writeStore(STORE.formulas, formulas);
      render();
    }
  });

  document.querySelectorAll("[data-sim]").forEach((input) => input.addEventListener("input", render));
  render();
}

function initAdmin() {
  const groupsList = document.querySelector("#groups-list");
  if (!groupsList) return;

  let groups = readStore(STORE.groups, [{ id: "geral", name: "Geral", description: "Grupo padrao" }]);
  let users = readStore(STORE.users, [{ id: "admin", name: "Administrador", email: "admin@aguaviva.local", group: "Geral", role: "admin" }]);
  let invites = readStore(STORE.invites, []);

  function persist() {
    writeStore(STORE.groups, groups);
    writeStore(STORE.users, users);
    writeStore(STORE.invites, invites);
  }

  function render() {
    groupsList.innerHTML = groups.map((group) => `<div class="list-item"><strong>${group.name}</strong><span>${group.description || "Sem descricao"}</span></div>`).join("");
    document.querySelector("#users-list").innerHTML = users.map((user) => `<div class="list-item"><strong>${user.name}</strong><span>${user.email}</span><span>${user.role || "usuario"} - ${user.group || "Geral"}</span></div>`).join("");
    document.querySelector("#invites-list").innerHTML = invites.length
      ? invites.map((invite) => `<div class="list-item"><strong>${invite.code}</strong><span>${invite.group}</span><span>${invite.createdAt}</span></div>`).join("")
      : '<p class="empty-text">Nenhum convite gerado.</p>';
  }

  document.querySelector("#add-group").addEventListener("click", () => {
    const name = document.querySelector("#group-name").value.trim();
    const description = document.querySelector("#group-desc").value.trim();
    if (!name) return;
    groups.push({ id: uid("group"), name, description });
    persist();
    render();
  });

  document.querySelector("#add-user").addEventListener("click", () => {
    const name = document.querySelector("#user-name").value.trim();
    const email = document.querySelector("#user-email").value.trim();
    if (!name || !email) return;
    users.push({ id: uid("user"), name, email, group: groups[0]?.name || "Geral", role: "usuario" });
    persist();
    render();
  });

  document.querySelector("#generate-invite").addEventListener("click", () => {
    invites.unshift({
      id: uid("invite"),
      code: Math.random().toString(36).slice(2, 8).toUpperCase(),
      group: groups[0]?.name || "Geral",
      createdAt: new Date().toLocaleString("pt-BR"),
    });
    persist();
    render();
  });

  document.querySelector("#clear-local-data").addEventListener("click", () => {
    if (!confirm("Limpar todos os dados locais deste navegador?")) return;
    Object.values(STORE).forEach((key) => localStorage.removeItem(key));
    location.reload();
  });

  persist();
  render();
}

function initPerfil() {
  const name = document.querySelector("#profile-name");
  if (!name) return;

  const email = document.querySelector("#profile-email");
  const avatar = document.querySelector("#profile-avatar");
  const dark = document.querySelector("#dark-mode");
  const profile = readStore(STORE.profile, { name: "Agua Viva", email: "coleta@aguaviva.local" });

  function updateStats() {
    document.querySelector("#stat-draft").textContent = localStorage.getItem("aguaviva2:novo-ponto") ? "1" : "0";
    document.querySelector("#stat-formulas").textContent = readStore(STORE.formulas, []).length;
    document.querySelector("#stat-points").textContent = readStore(STORE.points, []).length;
    document.querySelector("#stat-invites").textContent = readStore(STORE.invites, []).length;
  }

  function paintProfile() {
    avatar.textContent = (name.value || "A").trim().charAt(0).toUpperCase();
  }

  name.value = profile.name;
  email.value = profile.email;
  dark.checked = localStorage.getItem(STORE.theme) === "dark";
  paintProfile();
  updateStats();

  name.addEventListener("input", paintProfile);
  document.querySelector("#save-profile").addEventListener("click", () => {
    writeStore(STORE.profile, { name: name.value.trim(), email: email.value.trim() });
    paintProfile();
  });
  dark.addEventListener("change", () => {
    localStorage.setItem(STORE.theme, dark.checked ? "dark" : "light");
    applyTheme();
  });
}

applyTheme();
initMap();
initFormulas();
initAdmin();
initPerfil();
