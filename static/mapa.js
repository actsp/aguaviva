const mapElement = document.querySelector("#map");
const emptyElement = document.querySelector("#map-empty");

function colorFor(classificacao) {
  return {
    Otima: "#0f766e",
    Boa: "#16a34a",
    Razoavel: "#ca8a04",
    Regular: "#ca8a04",
    Ruim: "#dc2626",
    Pessima: "#7f1d1d",
  }[classificacao] || "#64748b";
}

function markerIcon(color) {
  return L.divIcon({
    className: "av-marker",
    html: `<span style="background:${color}"></span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function initMap() {
  if (!window.L || !mapElement) {
    if (emptyElement) emptyElement.textContent = "Mapa indisponivel sem internet. A tabela abaixo continua disponivel.";
    return;
  }

  const points = JSON.parse(mapElement.dataset.points || "[]").filter((point) => (
    Number.isFinite(point.lat)
    && Number.isFinite(point.lon)
    && point.lat >= -90
    && point.lat <= 90
    && point.lon >= -180
    && point.lon <= 180
  ));

  const map = L.map("map", { scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  if (points.length === 0) {
    map.setView([-15.78, -47.93], 4);
    if (emptyElement) emptyElement.textContent = "Nenhum ponto com coordenadas validas.";
    return;
  }

  const bounds = [];
  points.forEach((point) => {
    const color = colorFor(point.classificacao);
    bounds.push([point.lat, point.lon]);
    L.marker([point.lat, point.lon], { icon: markerIcon(color) })
      .addTo(map)
      .bindPopup(`
        <strong>${escapeHtml(point.nome || "Ponto sem nome")}</strong><br>
        ${escapeHtml(point.data)}<br>
        Classificacao: ${escapeHtml(point.classificacao || "Pendente")}<br>
        IQA: ${escapeHtml(point.iqa || "-")}<br>
        ${escapeHtml(point.obs)}
      `);
  });

  map.fitBounds(bounds, { padding: [28, 28], maxZoom: 15 });
  if (emptyElement) emptyElement.remove();
}

window.addEventListener("load", initMap);
