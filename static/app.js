const PARAM_KEYS = [
  "residuos",
  "odor",
  "espumas",
  "mata_ciliar",
  "ph",
  "nitrito",
  "fosfato",
  "turbidez",
];

const WEIGHTS = {
  residuos: 0.08,
  odor: 0.10,
  espumas: 0.15,
  mata_ciliar: 0.10,
  ph: 0.12,
  nitrito: 0.10,
  fosfato: 0.10,
  turbidez: 0.08,
  od: 0.17,
};

const NOTE_QUALITY = { 1: 10, 2: 45, 3: 90 };

const CLASS_INFO = {
  Otima: {
    label: "Otima",
    color: "#0f766e",
    description: "Ambiente preservado. Condicoes ideais para a biodiversidade.",
  },
  Boa: {
    label: "Boa",
    color: "#16a34a",
    description: "Agua saudavel. Ecossistema equilibrado e funcional.",
  },
  Razoavel: {
    label: "Razoavel",
    color: "#ca8a04",
    description: "Qualidade razoavel. O rio resiste, mas sofre pressao ambiental.",
  },
  Ruim: {
    label: "Ruim",
    color: "#dc2626",
    description: "Qualidade baixa. Fortes indicios de poluicao e degradacao.",
  },
  Pessima: {
    label: "Pessima",
    color: "#7f1d1d",
    description: "Agua extremamente impactada. Vida aquatica comprometida.",
  },
};

const DRAFT_KEY = "aguaviva2:novo-ponto";
const form = document.querySelector("#agua-form");
const iqaInput = document.querySelector("#iqa");
const classificacaoInput = document.querySelector("#classificacao");
const previewClass = document.querySelector("#preview-class");
const previewDescription = document.querySelector("#preview-description");
const previewScore = document.querySelector("#preview-score");
const previewIqa = document.querySelector("#preview-iqa");
const resultCard = document.querySelector(".result-card");

function selectedScore(key) {
  const selected = form.querySelector(`input[name="${key}"]:checked`);
  return selected ? Number(selected.dataset.score) : null;
}

function qualityFromOd(od) {
  if (od < 2) return 20;
  if (od < 4) return 40;
  if (od < 5) return 70;
  if (od <= 10) return 90;
  if (od <= 14) return 80;
  return 60;
}

function classificarIqa(iqa) {
  if (iqa >= 80) return "Otima";
  if (iqa >= 52) return "Boa";
  if (iqa >= 37) return "Razoavel";
  if (iqa >= 20) return "Ruim";
  return "Pessima";
}

function calcularIqa(scores, od) {
  const entries = PARAM_KEYS.map((key) => ({
    quality: NOTE_QUALITY[scores[key]],
    weight: WEIGHTS[key],
  }));

  if (Number.isFinite(od)) {
    entries.push({ quality: qualityFromOd(od), weight: WEIGHTS.od });
  }

  const valid = entries.filter((entry) => entry.weight > 0 && entry.quality > 0);
  const weightSum = valid.reduce((sum, entry) => sum + entry.weight, 0);
  const product = valid.reduce(
    (current, entry) => current * Math.pow(entry.quality, entry.weight / weightSum),
    1,
  );

  return Math.round(product * 10) / 10;
}

function updatePreview() {
  const scores = {};
  const complete = PARAM_KEYS.every((key) => {
    scores[key] = selectedScore(key);
    return scores[key] != null;
  });

  if (!complete) {
    iqaInput.value = "";
    classificacaoInput.value = "Pendente";
    resultCard.style.setProperty("--class-color", "#b45309");
    previewClass.textContent = "Pendente";
    previewDescription.textContent = "Preencha os 8 parametros para calcular score, IQA e classificacao.";
    previewScore.textContent = "--/24";
    previewIqa.textContent = "--/100";
    return;
  }

  const score = PARAM_KEYS.reduce((sum, key) => sum + scores[key], 0);
  const odText = form.elements.od.value.trim().replace(",", ".");
  const od = odText ? Number(odText) : null;
  const iqa = calcularIqa(scores, Number.isFinite(od) ? od : null);
  const classificacao = classificarIqa(iqa);
  const info = CLASS_INFO[classificacao];

  iqaInput.value = iqa.toFixed(1);
  classificacaoInput.value = info.label;
  resultCard.style.setProperty("--class-color", info.color);
  previewClass.textContent = info.label;
  previewDescription.textContent = info.description;
  previewScore.textContent = `${score}/24`;
  previewIqa.textContent = `${iqa.toFixed(1)}/100`;
}

function saveDraft() {
  const data = new FormData(form);
  const values = {};
  for (const [key, value] of data.entries()) values[key] = value;
  localStorage.setItem(DRAFT_KEY, JSON.stringify(values));
}

function restoreDraft() {
  const raw = localStorage.getItem(DRAFT_KEY);
  if (!raw) return;

  try {
    const values = JSON.parse(raw);
    for (const [key, value] of Object.entries(values)) {
      const field = form.elements[key];
      if (!field) continue;
      if (field instanceof RadioNodeList) {
        const option = [...field].find((item) => item.value === value);
        if (option) option.checked = true;
      } else {
        field.value = value;
      }
    }
  } catch {
    localStorage.removeItem(DRAFT_KEY);
  }
}

function shiftDate(delta) {
  const field = form.elements.data;
  const base = field.value ? new Date(`${field.value}T12:00:00`) : new Date();
  base.setDate(base.getDate() + delta);
  field.value = base.toISOString().slice(0, 10);
  field.dispatchEvent(new Event("input", { bubbles: true }));
}

document.querySelectorAll("[data-date-step]").forEach((button) => {
  button.addEventListener("click", () => shiftDate(Number(button.dataset.dateStep)));
});

document.querySelector("#today-button").addEventListener("click", () => {
  form.elements.data.value = new Date().toISOString().slice(0, 10);
  form.elements.data.dispatchEvent(new Event("input", { bubbles: true }));
});

document.querySelector("#use-location").addEventListener("click", () => {
  const status = document.querySelector("#location-status");
  if (!navigator.geolocation) {
    status.textContent = "Este navegador nao oferece geolocalizacao.";
    return;
  }

  status.textContent = "Obtendo localizacao...";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      form.elements.lat.value = position.coords.latitude.toFixed(6);
      form.elements.lon.value = position.coords.longitude.toFixed(6);
      status.textContent = "Coordenadas preenchidas pelo GPS do navegador.";
      updatePreview();
      saveDraft();
    },
    () => {
      status.textContent = "Nao foi possivel obter a localizacao. Informe manualmente.";
    },
    { enableHighAccuracy: true, timeout: 12000 },
  );
});

document.querySelector("#clear-draft").addEventListener("click", () => {
  localStorage.removeItem(DRAFT_KEY);
  form.reset();
  form.elements.data.value = new Date().toISOString().slice(0, 10);
  updatePreview();
});

form.addEventListener("input", () => {
  updatePreview();
  saveDraft();
});

form.addEventListener("change", () => {
  updatePreview();
  saveDraft();
});

form.addEventListener("submit", () => {
  updatePreview();
  const point = {
    id: `point-${Date.now()}`,
    nome: form.elements.nome.value.trim(),
    endereco: form.elements.endereco.value.trim(),
    lat: Number(form.elements.lat.value),
    lon: Number(form.elements.lon.value),
    iqa: iqaInput.value,
    classificacao: classificacaoInput.value,
    createdAt: new Date().toISOString(),
  };
  if (point.nome && Number.isFinite(point.lat) && Number.isFinite(point.lon)) {
    const key = "aguaviva2:pontos";
    let points = [];
    try {
      points = JSON.parse(localStorage.getItem(key)) || [];
    } catch {
      points = [];
    }
    points.unshift(point);
    localStorage.setItem(key, JSON.stringify(points.slice(0, 200)));
  }
  localStorage.removeItem(DRAFT_KEY);
});

restoreDraft();
const query = new URLSearchParams(location.search);
if (query.has("lat")) form.elements.lat.value = query.get("lat");
if (query.has("lon")) form.elements.lon.value = query.get("lon");
updatePreview();
