import csv
import io
import json
import math
import sqlite3
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import requests
from flask import Flask, redirect, render_template, request, send_file, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "aguaviva_local.sqlite3"
PDF_OUTPUT_DIR = BASE_DIR / "output" / "pdf"
APP_ICON_PATH = BASE_DIR / "static" / "icon_COATI.png"
DEVELOPER_CREDIT = "Desenvolvido por: ACT - Soluções para Pessoas"

DEFAULT_FORM_RESPONSE_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScMQCeEV3u5fugZz3I_dFuCtxxSIroKGrHRq-VjXE5vr-35hg/formResponse"
)

DEFAULT_SHEETS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRTFlf173ZaSJs_KjEEckQhJsm6DyLaSrxZcyYw9oASBmrIKvBhinA8sgh_WjRhb69gvLcwo2H6eBku/pub"
    "?gid=2101610767&single=true&output=csv"
)

DEFAULT_FIELD_MAP = {
    "nome": "entry.199097388",
    "lat": "entry.109223030",
    "lon": "entry.1293567946",
    "data": "entry.1209229563",
    "residuos": "entry.2097506040",
    "odor": "entry.1544926180",
    "espumas": "entry.927165480",
    "mata_ciliar": "entry.1265668708",
    "ph": "entry.499498821",
    "nitrito": "entry.1928676244",
    "fosfato": "entry.241410667",
    "turbidez": "entry.658883419",
    "od": "entry.864637607",
    "iqa": "entry.1328257172",
    "classificacao": "entry.298127070",
    "obs": "entry.955505894",
}

FORM_PLACEHOLDERS = {
    "nome": ("{NOME}",),
    "lat": ("{LAT}",),
    "lon": ("{LON}",),
    "data": ("{DATA}", "{9999-12-30}"),
    "residuos": ("{RESIDUOS}",),
    "odor": ("{ODOR}",),
    "espumas": ("{ESPUMAS}",),
    "mata_ciliar": ("{MATA_CILIAR}",),
    "ph": ("{PH}",),
    "nitrito": ("{NITRITO}",),
    "fosfato": ("{FOSFATO}",),
    "turbidez": ("{TURBIDEZ}",),
    "od": ("{OD}",),
    "iqa": ("{IQA}",),
    "classificacao": ("{CLASSIFICACAO}",),
    "obs": ("{OBS}",),
}

DEFAULT_FORM_TEMPLATE_URL = (
    f"{DEFAULT_FORM_RESPONSE_URL}?submit=Submit&usp=pp_url&"
    + "&".join(
        f"{entry}={placeholders[0]}"
        for field, entry in DEFAULT_FIELD_MAP.items()
        for placeholders in [FORM_PLACEHOLDERS[field]]
    )
)

PARAMETROS = [
    {
        "key": "residuos",
        "title": "Lixo e Residuos",
        "group": "sensorial",
        "options": [
            {"value": "1", "label": "Muito lixo (plasticos, pneus, descarte)"},
            {"value": "2", "label": "Pouco lixo ou apenas materiais naturais"},
            {"value": "3", "label": "Nenhum lixo visivel"},
        ],
    },
    {
        "key": "odor",
        "title": "Odor",
        "group": "sensorial",
        "options": [
            {"value": "1", "label": "Cheiro forte de esgoto, quimico ou ovo podre"},
            {"value": "2", "label": "Cheiro leve de mofo ou terra molhada"},
            {"value": "3", "label": "Sem odor perceptivel"},
        ],
    },
    {
        "key": "espumas",
        "title": "Espumas",
        "group": "sensorial",
        "options": [
            {"value": "1", "label": "Espumas brancas, tipo detergente, em flocos"},
            {"value": "2", "label": "Poucas bolhas isoladas"},
            {"value": "3", "label": "Ausencia total de espumas"},
        ],
    },
    {
        "key": "mata_ciliar",
        "title": "Mata Ciliar",
        "group": "sensorial",
        "options": [
            {"value": "1", "label": "Margens desnudas, com pasto ou construcao"},
            {"value": "2", "label": "Vegetacao rasteira ou poucas arvores"},
            {"value": "3", "label": "Mata densa e preservada em ambas as margens"},
        ],
    },
    {
        "key": "ph",
        "title": "pH",
        "group": "fisico_quimico",
        "options": [
            {"value": "1", "label": "Critico: menor que 5.0 ou maior que 9.0"},
            {"value": "2", "label": "Aceitavel: 5.0 a 6.5 ou 8.5 a 9.0"},
            {"value": "3", "label": "Ideal: 7.0 a 8.0"},
        ],
    },
    {
        "key": "nitrito",
        "title": "Nitrito",
        "group": "fisico_quimico",
        "options": [
            {"value": "1", "label": "Presenca nitida, indica carga organica"},
            {"value": "2", "label": "Presenca leve ou tracos"},
            {"value": "3", "label": "Ausente"},
        ],
    },
    {
        "key": "fosfato",
        "title": "Fosfato",
        "group": "fisico_quimico",
        "options": [
            {"value": "1", "label": "Concentracao alta, detergentes ou esgoto"},
            {"value": "2", "label": "Concentracao baixa"},
            {"value": "3", "label": "Ausente"},
        ],
    },
    {
        "key": "turbidez",
        "title": "Turbidez",
        "group": "fisico_quimico",
        "options": [
            {"value": "1", "label": "Agua barrenta ou com particulas em suspensao"},
            {"value": "2", "label": "Agua levemente opaca"},
            {"value": "3", "label": "Agua totalmente cristalina"},
        ],
    },
]

CLASS_ORDER = ["Otima", "Boa", "Razoavel", "Ruim", "Pessima"]
CLASS_LABELS = {
    "Otima": "Ótima",
    "Boa": "Boa",
    "Razoavel": "Razoável",
    "Ruim": "Ruim",
    "Pessima": "Péssima",
}
CLASS_COLORS = {
    "Otima": "#0f766e",
    "Boa": "#22bce0",
    "Razoavel": "#ffe600",
    "Ruim": "#ed1c24",
    "Pessima": "#242424",
}
INDICATOR_LABELS = {
    "Otima": "Ótima",
    "Boa": "Boa",
    "Razoavel": "Regular",
    "Ruim": "Ruim",
    "Pessima": "Péssima",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            create table if not exists cached_records (
                id integer primary key autoincrement,
                row_index integer not null,
                payload text not null,
                synced_at text not null
            );

            create table if not exists pending_submissions (
                id text primary key,
                payload text not null,
                generated_url text not null,
                created_at text not null,
                last_error text,
                synced_at text
            );

            create table if not exists formulas (
                id text primary key,
                name text not null,
                expression text not null,
                created_at text not null
            );

            create table if not exists meta (
                key text primary key,
                value text not null
            );

            create table if not exists city_cache (
                coord_key text primary key,
                latitude real not null,
                longitude real not null,
                cidade text not null,
                raw_payload text,
                updated_at text not null
            );
            """
        )
        count = conn.execute("select count(*) from formulas").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            conn.executemany(
                "insert into formulas (id, name, expression, created_at) values (?, ?, ?, ?)",
                [
                    (str(uuid.uuid4()), "Percentual do score", "{SCORE} / 24 * 100", now),
                    (str(uuid.uuid4()), "IQA ponderado", "{IQA}", now),
                ],
            )


def get_meta_value(key, default=""):
    with get_db() as conn:
        row = conn.execute("select value from meta where key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta_value(key, value):
    with get_db() as conn:
        conn.execute("insert or replace into meta (key, value) values (?, ?)", (key, value))


def current_sheets_csv_url():
    return get_meta_value("sheets_csv_url", DEFAULT_SHEETS_CSV_URL).strip() or DEFAULT_SHEETS_CSV_URL


def current_form_template_url():
    return get_meta_value("google_forms_template_url", DEFAULT_FORM_TEMPLATE_URL).strip() or DEFAULT_FORM_TEMPLATE_URL


def parse_google_forms_template(template_url):
    parsed = urlsplit(template_url.strip())
    action_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    if not parsed.scheme or not parsed.netloc or not parsed.path.endswith("/formResponse"):
        raise ValueError("Informe uma URL valida do Google Forms terminada em /formResponse.")

    field_map = {}
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    for entry_name, entry_value in query_items:
        if not entry_name.startswith("entry."):
            continue
        for local_name, placeholders in FORM_PLACEHOLDERS.items():
            if entry_value.strip() in placeholders:
                field_map[local_name] = entry_name

    missing = [placeholder_group[0] for key, placeholder_group in FORM_PLACEHOLDERS.items() if key not in field_map]
    if missing:
        raise ValueError("A URL modelo esta incompleta. Campos ausentes: " + ", ".join(missing))

    return action_url, field_map


def current_form_settings():
    template_url = current_form_template_url()
    action_url, field_map = parse_google_forms_template(template_url)
    return {"template_url": template_url, "action_url": action_url, "field_map": field_map}


def normalize_key(key):
    cleaned = key.strip().replace("\ufeff", "").replace("\xad", "").replace("�", "i")
    return "".join(
        char for char in unicodedata.normalize("NFKD", cleaned.lower()) if not unicodedata.combining(char)
    )


def pick(row, *names):
    normalized = {normalize_key(key): value for key, value in row.items()}
    for name in names:
        value = normalized.get(normalize_key(name))
        if value is not None:
            return value.strip()
    return ""


def parse_float(value):
    text = str(value or "").strip().replace(",", ".")
    if text.count(".") > 1:
        text = text.replace(".", "", text.count(".") - 1)
    try:
        return float(text)
    except ValueError:
        return None


def parse_coordinate(value, limit):
    coordinate = parse_float(value)
    if coordinate is None or not math.isfinite(coordinate):
        return None
    while abs(coordinate) > limit:
        coordinate = coordinate / 10
    return coordinate


def is_valid_coordinate(latitude, longitude):
    return (
        isinstance(latitude, (int, float))
        and isinstance(longitude, (int, float))
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def coord_cache_key(latitude, longitude):
    return f"{latitude:.5f},{longitude:.5f}"


def cidade_from_address(address):
    return (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or address.get("state_district")
        or "Cidade nao identificada"
    )


def obter_cidade(latitude, longitude):
    if not is_valid_coordinate(latitude, longitude):
        return "Coordenada invalida"

    cache_key = coord_cache_key(latitude, longitude)
    with get_db() as conn:
        cached = conn.execute("select cidade from city_cache where coord_key = ?", (cache_key,)).fetchone()
        if cached:
            return cached["cidade"]

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "jsonv2",
                "lat": latitude,
                "lon": longitude,
                "zoom": 10,
                "addressdetails": 1,
            },
            headers={"User-Agent": "agua-viva-dashboard/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        cidade = cidade_from_address(payload.get("address", {}))
    except (ValueError, requests.RequestException):
        cidade = "Cidade nao identificada"
        payload = {}

    with get_db() as conn:
        conn.execute(
            """
            insert or replace into city_cache
            (coord_key, latitude, longitude, cidade, raw_payload, updated_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                latitude,
                longitude,
                cidade,
                json.dumps(payload, ensure_ascii=False),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
    return cidade


def normalize_classificacao(value):
    key = normalize_key(str(value or ""))
    if key in {"otima", "otimo"}:
        return "Otima"
    if key == "boa":
        return "Boa"
    if key in {"razoavel", "regular", "aceitavel"}:
        return "Razoavel"
    if key == "ruim":
        return "Ruim"
    if key in {"pessima", "pessimo"}:
        return "Pessima"
    return None


def parse_year(record):
    for field in ("data", "timestamp"):
        value = str(record.get(field) or "").strip()
        if not value:
            continue
        for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:19], fmt).year
            except ValueError:
                pass
    return None


def normalize_record(row, row_index):
    return {
        "id": row_index,
        "timestamp": pick(row, "Carimbo de data/hora"),
        "nome": pick(row, "Nome do ponto", "NOME"),
        "lat": parse_coordinate(pick(row, "LAT"), 90),
        "lon": parse_coordinate(pick(row, "LON"), 180),
        "data": pick(row, "Data da Coleta", "Data"),
        "residuos": pick(row, "Lixo e Residuos", "Lixo e Resíduos"),
        "odor": pick(row, "Odor"),
        "espumas": pick(row, "Espumas"),
        "mata_ciliar": pick(row, "Mata Ciliar"),
        "ph": pick(row, "pH", "PH"),
        "nitrito": pick(row, "Nitrito"),
        "fosfato": pick(row, "Fosfato"),
        "turbidez": pick(row, "Turbidez"),
        "od": pick(row, "OD"),
        "iqa": pick(row, "IQA"),
        "classificacao": pick(row, "Classificacao", "Classificação"),
        "obs": pick(row, "Observacoes", "Observações"),
    }


def cache_records(records):
    synced_at = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute("delete from cached_records")
        conn.executemany(
            "insert into cached_records (row_index, payload, synced_at) values (?, ?, ?)",
            [(record["id"], json.dumps(record, ensure_ascii=False), synced_at) for record in records],
        )
        conn.execute("insert or replace into meta (key, value) values (?, ?)", ("last_sheet_sync", synced_at))


def cached_records():
    with get_db() as conn:
        rows = conn.execute("select payload from cached_records order by row_index").fetchall()
        last_sync = conn.execute("select value from meta where key = ?", ("last_sheet_sync",)).fetchone()
    return [json.loads(row["payload"]) for row in rows], last_sync["value"] if last_sync else None


def fetch_sheet_records():
    response = requests.get(current_sheets_csv_url(), timeout=20)
    response.raise_for_status()
    csv_text = response.content.decode("utf-8-sig", errors="replace")
    records = [
        normalize_record(row, index)
        for index, row in enumerate(csv.DictReader(io.StringIO(csv_text)), start=1)
    ]
    cache_records(records)
    return records, datetime.now().isoformat(timespec="seconds"), "online"


def load_records():
    try:
        return fetch_sheet_records()
    except requests.RequestException:
        records, last_sync = cached_records()
        return records, last_sync, "cache"


def build_google_forms_params(form_data):
    field_map = current_form_settings()["field_map"]
    params = {"submit": "Submit", "usp": "pp_url"}
    for local_name, google_entry in field_map.items():
        params[google_entry] = form_data.get(local_name, "").strip()

    for coordinate_name in ("lat", "lon"):
        coordinate = parse_coordinate(form_data.get(coordinate_name, ""), 90 if coordinate_name == "lat" else 180)
        if coordinate is not None:
            params[field_map[coordinate_name]] = f"{coordinate:.6f}".replace(".", ",")

    endereco = form_data.get("endereco", "").strip()
    if endereco:
        observacoes = params[field_map["obs"]]
        params[field_map["obs"]] = (
            f"Endereco: {endereco}\n\n{observacoes}" if observacoes else f"Endereco: {endereco}"
        )
    return params


def generated_form_url(params):
    return requests.Request("GET", current_form_settings()["action_url"], params=params).prepare().url


def save_pending(params, url, error):
    with get_db() as conn:
        conn.execute(
            """
            insert into pending_submissions (id, payload, generated_url, created_at, last_error)
            values (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                json.dumps(params, ensure_ascii=False),
                url,
                datetime.now().isoformat(timespec="seconds"),
                str(error),
            ),
        )


def pending_submissions():
    with get_db() as conn:
        return conn.execute(
            "select * from pending_submissions where synced_at is null order by created_at desc"
        ).fetchall()


def sync_pending_submissions():
    synced = 0
    errors = []
    with get_db() as conn:
        rows = conn.execute("select * from pending_submissions where synced_at is null order by created_at").fetchall()
        for row in rows:
            try:
                response = requests.get(row["generated_url"], timeout=15)
                response.raise_for_status()
                conn.execute(
                    "update pending_submissions set synced_at = ? where id = ?",
                    (datetime.now().isoformat(timespec="seconds"), row["id"]),
                )
                synced += 1
            except requests.RequestException as error:
                conn.execute("update pending_submissions set last_error = ? where id = ?", (str(error), row["id"]))
                errors.append(str(error))
    return synced, errors


def all_formulas():
    with get_db() as conn:
        return conn.execute("select * from formulas order by created_at desc").fetchall()


def stats_for(records):
    counts = {"Otima": 0, "Boa": 0, "Razoavel": 0, "Ruim": 0, "Pessima": 0, "Pendente": 0}
    for record in records:
        klass = normalize_classificacao(record.get("classificacao")) or "Pendente"
        counts[klass] = counts.get(klass, 0) + 1
    return counts


def dashboard_stats(records):
    counts = {key: 0 for key in CLASS_ORDER}
    for record in records:
        klass = normalize_classificacao(record.get("classificacao"))
        if klass:
            counts[klass] += 1

    total = sum(counts.values())
    rows = []
    angle = 0.0
    gradient_parts = []
    for key in CLASS_ORDER:
        quantidade = counts.get(key, 0)
        percentual = (quantidade / total * 100) if total else 0
        sweep = percentual * 3.6
        if sweep > 0:
            gradient_parts.append(f"{CLASS_COLORS[key]} {angle:.4f}deg {angle + sweep:.4f}deg")
        angle += sweep
        rows.append(
            {
                "key": key,
                "label": CLASS_LABELS[key],
                "color": CLASS_COLORS[key],
                "quantidade": quantidade,
                "percentual": percentual,
            }
        )
    return {
        "total": total,
        "rows": rows,
        "gradient": ", ".join(gradient_parts) if gradient_parts else "#d1d5db 0deg 360deg",
        "indicator_rows": [
            {**row, "indicator_label": INDICATOR_LABELS[row["key"]]}
            for row in rows
            if row["key"] in INDICATOR_LABELS
        ],
    }


def dashboard_dataframe(records):
    temporary_rows = []
    for record in records:
        row = dict(record)
        row["cidade"] = obter_cidade(row.get("lat"), row.get("lon"))
        temporary_rows.append(row)
    return temporary_rows


def dashboard_context(cidade=""):
    records, last_sync, source = load_records()
    temporary_rows = dashboard_dataframe(records)
    cidades = sorted(
        {
            row.get("cidade")
            for row in temporary_rows
            if row.get("cidade") and row.get("cidade") != "Coordenada invalida"
        }
    )
    filtered_records = [row for row in temporary_rows if not cidade or row.get("cidade") == cidade]
    return {
        "records": filtered_records,
        "dashboard": dashboard_stats(filtered_records),
        "cidades": cidades,
        "selected_cidade": cidade,
        "total_records": len(records),
        "filtered_records_count": len(filtered_records),
        "last_sync": last_sync,
        "source": source,
    }


def fmt_percent(value):
    return f"{value:.1f}".replace(".", ",") + "%"


class IndicatorCards(Flowable):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.width = 18.3 * cm
        self.height = 3.1 * cm

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def draw(self):
        canvas = self.canv
        card_gap = 0.18 * cm
        card_width = (self.width - (4 * card_gap)) / 5
        card_height = 2.65 * cm
        y = 0.22 * cm

        for index, item in enumerate(self.dashboard["indicator_rows"]):
            x = index * (card_width + card_gap)
            color = colors.HexColor(item["color"])
            canvas.setFillColor(colors.white)
            canvas.setStrokeColor(colors.HexColor("#d7e3ec"))
            canvas.roundRect(x, y, card_width, card_height, 10, stroke=1, fill=1)

            canvas.setFillColor(color)
            canvas.circle(x + 0.33 * cm, y + card_height - 0.42 * cm, 0.09 * cm, stroke=0, fill=1)

            canvas.setFillColor(colors.HexColor("#1f5d86"))
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(x + 0.55 * cm, y + card_height - 0.52 * cm, item["indicator_label"])

            canvas.setFillColor(color)
            canvas.setFont("Helvetica-Bold", 18)
            canvas.drawString(x + 0.28 * cm, y + 1.08 * cm, fmt_percent(item["percentual"]))

            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.setFont("Helvetica-Bold", 6.6)
            canvas.drawString(x + 0.28 * cm, y + 0.42 * cm, f"{item['quantidade']} de {self.dashboard['total']}")
            canvas.drawRightString(x + card_width - 0.28 * cm, y + 0.42 * cm, "classificacoes")


class DonutSummary(Flowable):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.width = 17 * cm
        self.height = 7.4 * cm

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def draw(self):
        canvas = self.canv
        x = 0
        y = 0
        total = self.dashboard["total"]
        cx = x + 3.5 * cm
        cy = y + 3.7 * cm
        radius = 2.7 * cm
        hole = 1.15 * cm
        start = 90

        if total:
            for item in self.dashboard["rows"]:
                extent = -item["percentual"] * 3.6
                if item["quantidade"] > 0:
                    canvas.setFillColor(colors.HexColor(item["color"]))
                    canvas.setStrokeColor(colors.HexColor(item["color"]))
                    canvas.wedge(cx - radius, cy - radius, cx + radius, cy + radius, start, extent, stroke=0, fill=1)
                start += extent
        else:
            canvas.setFillColor(colors.HexColor("#d1d5db"))
            canvas.wedge(cx - radius, cy - radius, cx + radius, cy + radius, 0, 360, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.circle(cx, cy, hole, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#527f9d"))
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(cx, cy + 0.15 * cm, str(total))
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(cx, cy - 0.35 * cm, "classificacoes")

        legend_x = x + 7.5 * cm
        legend_y = y + 6.1 * cm
        canvas.setFont("Helvetica-Bold", 10)
        for index, item in enumerate(self.dashboard["rows"]):
            row_y = legend_y - index * 0.82 * cm
            canvas.setFillColor(colors.HexColor(item["color"]))
            canvas.circle(legend_x, row_y + 0.08 * cm, 0.12 * cm, stroke=0, fill=1)
            canvas.setFillColor(colors.HexColor("#1f5d86"))
            canvas.drawString(legend_x + 0.35 * cm, row_y, item["label"])
            canvas.drawRightString(legend_x + 5.6 * cm, row_y, str(item["quantidade"]))
            canvas.drawRightString(legend_x + 7.2 * cm, row_y, fmt_percent(item["percentual"]))


def draw_pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawCentredString(A4[0] / 2, 0.55 * cm, DEVELOPER_CREDIT)
    canvas.restoreState()


def build_report_pdf(context):
    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PDF_OUTPUT_DIR / "relatorio_dashboard.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    if APP_ICON_PATH.exists():
        logo = Image(str(APP_ICON_PATH), width=1.5 * cm, height=1.5 * cm)
        header = Table(
            [[logo, Paragraph("Agua Viva - Relatorio Dashboard IQA", styles["Title"])]],
            colWidths=[2.0 * cm, 15.2 * cm],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(header)
    else:
        story.append(Paragraph("Agua Viva - Relatorio Dashboard IQA", styles["Title"]))

    subtitle = "Classificacoes consolidadas"
    if context["selected_cidade"]:
        subtitle += f" - {context['selected_cidade']}"
    story.append(Paragraph(subtitle, styles["Heading2"]))
    story.append(
        Paragraph(
            f"Registros exibidos: {context['filtered_records_count']} de {context['total_records']}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(IndicatorCards(context["dashboard"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(DonutSummary(context["dashboard"]))
    story.append(Spacer(1, 0.35 * cm))

    summary_rows = [["IQA", "Quantidade", "Percentual"]]
    for item in context["dashboard"]["rows"]:
        summary_rows.append([item["label"], item["quantidade"], fmt_percent(item["percentual"])])
    summary_rows.append(["Total", context["dashboard"]["total"], "100%" if context["dashboard"]["total"] else "0%"])
    summary_table = Table(summary_rows, colWidths=[8 * cm, 4 * cm, 4 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#527f9d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#d7edf8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#527f9d")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#d7edf8")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#d4dee6")]),
                ("TEXTCOLOR", (0, 1), (-1, -2), colors.HexColor("#1f5d86")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.45 * cm))
    story.append(Paragraph("Dados obtidos do Google Sheets", styles["Heading2"]))

    detail_rows = [["Data", "Ponto", "Cidade", "Classificacao", "IQA", "LAT", "LON"]]
    for record in context["records"]:
        detail_rows.append(
            [
                record.get("data") or record.get("timestamp") or "-",
                Paragraph(str(record.get("nome") or "-"), styles["BodyText"]),
                Paragraph(str(record.get("cidade") or "-"), styles["BodyText"]),
                record.get("classificacao") or "Pendente",
                record.get("iqa") or "-",
                f"{record.get('lat'):.6f}" if isinstance(record.get("lat"), (int, float)) else "-",
                f"{record.get('lon'):.6f}" if isinstance(record.get("lon"), (int, float)) else "-",
            ]
        )

    detail_table = Table(
        detail_rows,
        repeatRows=1,
        colWidths=[2.4 * cm, 3.8 * cm, 3.2 * cm, 2.8 * cm, 1.4 * cm, 2.2 * cm, 2.2 * cm],
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#527f9d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#d7edf8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f6")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1f5d86")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e3ec")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(detail_table)
    doc.build(story, onFirstPage=draw_pdf_footer, onLaterPages=draw_pdf_footer)
    return output_path


@app.context_processor
def inject_globals():
    return {"pending_count": len(pending_submissions())}


@app.get("/")
def index():
    return render_template("index.html", active="registro", today=date.today().isoformat(), parametros=PARAMETROS)


@app.post("/salvar")
def salvar():
    params = build_google_forms_params(request.form)
    final_url = generated_form_url(params)
    try:
        response = requests.get(final_url, timeout=15)
        response.raise_for_status()
        status = "success"
        message = "Registro enviado para o Google Forms com sucesso."
    except requests.RequestException as error:
        save_pending(params, final_url, error)
        status = "warning"
        message = "Sem conexao com o Google Forms. O registro ficou na fila local para sincronizar depois."

    return render_template(
        "resultado.html",
        active="registro",
        generated_url=final_url,
        message=message,
        status=status,
    )


@app.get("/mapa")
def mapa():
    records, last_sync, source = load_records()
    return render_template(
        "mapa.html",
        active="mapa",
        records=records,
        stats=stats_for(records),
        last_sync=last_sync,
        source=source,
    )


@app.get("/dashboard")
def dashboard():
    cidade = request.args.get("cidade", "").strip()
    context = dashboard_context(cidade)
    return render_template(
        "dashboard.html",
        active="dashboard",
        records=context["records"],
        dashboard=context["dashboard"],
        class_order=CLASS_ORDER,
        class_labels=CLASS_LABELS,
        class_colors=CLASS_COLORS,
        cidades=context["cidades"],
        selected_cidade=context["selected_cidade"],
        total_records=context["total_records"],
        filtered_records_count=context["filtered_records_count"],
        last_sync=context["last_sync"],
        source=context["source"],
    )


@app.get("/dashboard/pdf")
def dashboard_pdf():
    cidade = request.args.get("cidade", "").strip()
    context = dashboard_context(cidade)
    output_path = build_report_pdf(context)
    return send_file(output_path, as_attachment=True, download_name=output_path.name)


@app.get("/formulas")
def formulas():
    return render_template("formulas.html", active="formulas", formulas=all_formulas())


@app.post("/formulas")
def salvar_formula():
    name = request.form.get("name", "").strip()
    expression = request.form.get("expression", "").strip()
    if name and expression:
        with get_db() as conn:
            conn.execute(
                "insert into formulas (id, name, expression, created_at) values (?, ?, ?, ?)",
                (str(uuid.uuid4()), name, expression, datetime.now().isoformat(timespec="seconds")),
            )
    return redirect(url_for("formulas"))


@app.post("/formulas/<formula_id>/delete")
def deletar_formula(formula_id):
    with get_db() as conn:
        conn.execute("delete from formulas where id = ?", (formula_id,))
    return redirect(url_for("formulas"))


@app.get("/admin")
def admin():
    records, last_sync, source = load_records()
    form_settings = current_form_settings()
    return render_template(
        "admin.html",
        active="admin",
        records=records,
        stats=stats_for(records),
        formulas_count=len(all_formulas()),
        pending=pending_submissions(),
        last_sync=last_sync,
        source=source,
        forms_template_url=form_settings["template_url"],
        forms_action_url=form_settings["action_url"],
        field_map=form_settings["field_map"],
        sheets_csv_url=current_sheets_csv_url(),
        config_status=request.args.get("config_status", ""),
        config_message=request.args.get("config_message", ""),
    )


@app.post("/admin/configuracoes")
def salvar_configuracoes_admin():
    forms_template_url = request.form.get("forms_template_url", "").strip()
    sheets_csv_url = request.form.get("sheets_csv_url", "").strip()
    try:
        parse_google_forms_template(forms_template_url)
        if not sheets_csv_url.startswith(("http://", "https://")):
            raise ValueError("Informe uma URL CSV valida do Google Sheets.")
    except ValueError as error:
        return redirect(
            url_for("admin", config_status="error", config_message=str(error))
        )

    set_meta_value("google_forms_template_url", forms_template_url)
    set_meta_value("sheets_csv_url", sheets_csv_url)
    return redirect(
        url_for("admin", config_status="success", config_message="Configuracoes salvas com sucesso.")
    )


@app.get("/perfil")
def perfil():
    records, last_sync, source = load_records()
    return render_template(
        "perfil.html",
        active="perfil",
        records=records,
        pending=pending_submissions(),
        last_sync=last_sync,
        source=source,
        sheets_url=current_sheets_csv_url(),
    )


@app.post("/sincronizar")
def sincronizar():
    sync_pending_submissions()
    try:
        fetch_sheet_records()
    except requests.RequestException:
        pass
    return redirect(request.referrer or url_for("perfil"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
