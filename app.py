import base64
import hashlib
import io
import math
import os
import re
import sqlite3
import struct
import time
import logging
import unicodedata
import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor, as_completed
import wave
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

try:
    import streamlit as st
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    requests = None
    HAS_REQUESTS = False

try:
    from PyPDF2 import PdfReader
    HAS_PDF = True
except Exception:
    PdfReader = None
    HAS_PDF = False

try:
    import fitz
    HAS_FITZ = True
except Exception:
    fitz = None
    HAS_FITZ = False

try:
    from docx import Document
    HAS_DOCX = True
except Exception:
    Document = None
    HAS_DOCX = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ============================================================================
# CONFIGURACION
# ============================================================================

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "techmaintpro.db")
LOG_PATH = os.path.join(APP_DIR, "techmaintpro.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger("TechMaintPro")

# ============================================================================
# CONFIGURACION TELEGRAM
# ============================================================================

TELEGRAM_BOT_TOKEN = "8944581569:AAFw2rfEn3zU5iOpdNrtIzYHLTs30xg_cIA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

STAFF = {
    "tecnico": {
        "nombre": "DARIO MINAN ESPINOZA",
        "telefono": "958000191",
        "email": "dario.minanespinoza@gmail.com",
        "telegram_chat_id": "",
        "rol": "Tecnico de Mantenimiento"
    },
    "asesor": {
        "nombre": "JORDY ALBERTO SERNAQUE SABA",
        "telefono": "902631386",
        "email": "ajordyss0602@gmail.com",
        "telegram_chat_id": "",
        "rol": "Asesor de Mantenimiento"
    },
    "gerencia": {
        "nombre": "Irina Nicole Castillo Coronado",
        "telefono": "966153839",
        "email": "nicolecastc@gmail.com",
        "telegram_chat_id": "",
        "rol": "Gerencia"
    }
}

# ============================================================================
# LOGO OFICIAL BASE64
# ============================================================================

LOGO_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAZABkADASIAAhEBAxEB/8QAHQABAAEEAwEAAAAAAAAAAAAAAAgBAgcJAwUGBP/EAF4QAAIBAwIDBQQFCAYGBQkDDQABAgMEEQUGByExCBJBUWETInGBCRQykaEVI0JSYoKxwRYzcpKi8CQ0Q7LC0SVTk7PSF2NzdHWDo+HxNTY3RFTDGCY4VpQnhKTT4v/EABwBAQACAwEBAQAAAAAAAAAAAAAGBwEEBQMCCP/EAEERAQABAwIDBAkCBAUCBwEBAQABAgMEBREGITESE0FRFCIyYXGBkaGxwdEVI0LhM1JicvAkNBYlNUOSovFEU4L/2gAMAwEAAhEDEQA/ANqYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA......"

def render_logo(size="80px"):
    return f'<img src="{LOGO_BASE64}" style="width:{size}; height:auto; display:inline-block;" />'

# ============================================================================
# CONFIGURACION PAGINA
# ============================================================================

st.set_page_config(
    page_title="Tech Maint Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.stApp > header { background-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# COLORES OFICIALES DEL LOGO
# ============================================================================

COLORS = {
    "azul": "#1a5fa8",
    "verde": "#7cb342",
    "amarillo": "#f5a623",
    "rojo": "#d32f2f",
    "blanco": "#ffffff",
    "gris_claro": "#f5f7fa",
    "gris_medio": "#e8ecf1",
    "texto_oscuro": "#1a2b4c",
    "texto_gris": "#5a6b7c",
}

# ============================================================================
# ACTIVOS INDUSTRIALES
# ============================================================================

ASSETS = {
    "Bomba de vacio BV-01": {"tag": "BV-ABS-001", "criticality": "Alta"},
    "Motor CAT 3408 MD-01": {"tag": "MD-3408-001", "criticality": "Alta"},
    "Compresor Leroi CA-01": {"tag": "CA-LER-001", "criticality": "Media-Alta"},
}

THRESHOLDS = {
    "vibration_normal": 4.5, "vibration_alert": 7.1,
    "temperature_normal": 75.0, "temperature_alert": 85.0,
    "vacuum_normal": -65.0, "vacuum_alert": -55.0,
}

FMECA_KNOWLEDGE = [
    {
        "symptom": "vibracion alta",
        "failure_mode": "Desgaste de rodamientos o desalineacion",
        "effect": "Aumento de vibracion y temperatura",
        "criticality": "Alta",
        "tasks": ["Medir vibracion en rodamientos", "Verificar alineacion", "Revisar lubricacion"]
    },
    {
        "symptom": "temperatura alta",
        "failure_mode": "Friccion interna o lubricacion deficiente",
        "effect": "Degradacion acelerada de componentes",
        "criticality": "Media-Alta",
        "tasks": ["Revisar nivel de lubricante", "Inspeccionar enfriamiento", "Verificar sobrecarga"]
    },
    {
        "symptom": "perdida de vacio",
        "failure_mode": "Fuga en linea o deterioro de sellos",
        "effect": "Reduccion de succion y parada del muelle",
        "criticality": "Alta",
        "tasks": ["Prueba de fugas", "Inspeccionar sellos", "Revisar tuberias y filtros"]
    },
]

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

def apply_custom_styles():
    css = f"""
    <style>
    /* Fondo claro general */
    .stApp {{ 
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%) !important; 
    }}
    
    /* Header con colores del logo */
    .main-header {{
        background: linear-gradient(90deg, {COLORS['azul']} 0%, #2a7bc8 100%);
        padding: 20px 30px;
        border-radius: 0 0 24px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(26,95,168,0.2);
    }}
    
    /* Tarjetas metricas con semafaro */
    .metric-card {{
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        border-left: 6px solid;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-top: 1px solid #e8ecf1;
        text-align: center;
    }}
    .metric-card:hover {{ 
        transform: translateY(-5px); 
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}
    
    /* Semafaro verde */
    .status-normal {{ border-left-color: {COLORS['verde']} !important; }}
    .badge-normal {{ color: {COLORS['verde']}; font-weight: bold; }}
    
    /* Semafaro amarillo */
    .status-alerta {{ border-left-color: {COLORS['amarillo']} !important; }}
    .badge-alerta {{ color: {COLORS['amarillo']}; font-weight: bold; }}
    
    /* Semafaro rojo */
    .status-critico {{ border-left-color: {COLORS['rojo']} !important; }}
    .badge-critico {{ color: {COLORS['rojo']}; font-weight: bold; }}
    
    /* Alarmas */
    .alarm-banner {{
        background: linear-gradient(90deg, rgba(245,166,35,0.15), rgba(245,166,35,0.05));
        border-left: 5px solid {COLORS['amarillo']};
        border-radius: 12px;
        padding: 15px 20px;
        margin-bottom: 15px;
        border: 1px solid rgba(245,166,35,0.3);
    }}
    .alarm-critical {{
        background: linear-gradient(90deg, rgba(211,47,47,0.15), rgba(211,47,47,0.05));
        border-left: 5px solid {COLORS['rojo']};
        border: 1px solid rgba(211,47,47,0.3);
    }}
    
    /* Texto oscuro para fondo claro */
    h1, h2, h3, p, label, span, div {{ 
        color: {COLORS['texto_oscuro']} !important; 
    }}
    .stMarkdown p {{ color: {COLORS['texto_oscuro']} !important; }}
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ 
        color: {COLORS['azul']} !important; 
    }}
    
    /* Chatbot flotante - tema claro */
    .stChatMessage {{
        background: #ffffff !important;
        border: 1px solid #e8ecf1 !important;
    }}
    
    /* Botones */
    .stButton > button {{
        background: {COLORS['azul']} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    .stButton > button:hover {{
        background: #2a7bc8 !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(26,95,168,0.1) !important;
        color: {COLORS['texto_oscuro']} !important;
        border-radius: 12px 12px 0 0;
        padding: 10px 18px;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: {COLORS['azul']} !important;
        color: white !important;
    }}
    
    /* Selectbox y inputs */
    .stSelectbox > div > div {{
        background: #ffffff !important;
        color: {COLORS['texto_oscuro']} !important;
    }}
    
    @media (max-width: 768px) {{
        .metric-value {{ font-size: 1.5rem !important; }}
        .main-header {{ padding: 15px 20px; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# NOTIFICACIONES TELEGRAM
# ============================================================================

def send_telegram(chat_id, message):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Telegram no configurado correctamente")
        return False
    try:
        r = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False

def notify_ot_creation(ot_data):
    resp = ot_data.get("responsable", "").lower()
    prio = ot_data.get("prioridad", "P2")
    if any(x in resp for x in ["dario", "minan"]):
        staff = STAFF["tecnico"]
        next_level = STAFF["asesor"]
    elif any(x in resp for x in ["jordy", "sernaque"]):
        staff = STAFF["asesor"]
        next_level = STAFF["gerencia"]
    else:
        staff = STAFF["tecnico"]
        next_level = STAFF["asesor"]
    
    msg = f"NUEVA ORDEN DE TRABAJO\n\nID: {ot_data['ot_id']}\nActivo: {ot_data['activo']}\nPrioridad: {prio}\nResponsable: {ot_data.get('responsable', 'No asignado')}\nSintomas: {ot_data.get('sintomas', '')[:100]}...\nFecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    if staff.get("telegram_chat_id"):
        send_telegram(staff["telegram_chat_id"], msg)
    if prio in ["P0", "P1"] and next_level.get("telegram_chat_id"):
        esc_msg = f"OT ESCALADA - {prio}\n{ot_data['ot_id']}: {ot_data['activo']}"
        send_telegram(next_level["telegram_chat_id"], esc_msg)

def notify_ot_completion(ot_data):
    if STAFF["asesor"].get("telegram_chat_id"):
        msg = f"OT COMPLETADA\n\nID: {ot_data['ot_id']}\nTecnico: {ot_data.get('responsable', 'N/A')}\nEstado: {ot_data.get('estado', 'Cerrada')}"
        send_telegram(STAFF["asesor"]["telegram_chat_id"], msg)

def notify_economic_impact(intervention):
    md = intervention.get("mass_discarded_kg", 0) or 0
    mc = intervention.get("mass_conserved_kg", 0) or 0
    if md > 5 or mc > 10:
        body = f"<h2>Impacto Circular</h2><ul><li>OT: {intervention['ot_id']}</li><li>Componente: {intervention['component']}</li><li>Masa conservada: {mc:.2f} kg</li><li>Masa descartada: {md:.2f} kg</li></ul>"
        for key in ["asesor", "gerencia"]:
            try:
                msg = MIMEText(body, 'html')
                msg['Subject'] = f"Impacto Economico - OT {intervention['ot_id']}"
                msg['From'] = STAFF[key]["email"]
                msg['To'] = STAFF[key]["email"]
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(STAFF[key]["email"], "")
                server.send_message(msg)
                server.quit()
            except Exception:
                pass

# ============================================================================
# ALARMAS SONORAS
# ============================================================================

def play_critical_alarm(event_id):
    if st.session_state.get("last_beep_event") == event_id:
        return
    st.session_state.last_beep_event = event_id
    if HAS_WINSOUND:
        for _ in range(3):
            winsound.Beep(1000, 300)
            time.sleep(0.1)

def play_observation_alarm(event_id):
    if st.session_state.get("last_observation_event") == event_id:
        return
    st.session_state.last_observation_event = event_id
    if HAS_WINSOUND:
        for _ in range(2):
            winsound.Beep(600, 200)
            time.sleep(0.1)

# ============================================================================
# FUNCIONES DE DATOS Y RIESGO
# ============================================================================

def generate_synthetic_data(scenario, n=240, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    start = datetime.now() - timedelta(hours=n)
    dates = [start + timedelta(hours=int(i)) for i in t]
    vibration = 2.8 + 0.28 * rng.normal(size=n) + 0.12 * np.sin(t / 9)
    temperature = 66 + 1.6 * rng.normal(size=n) + 0.5 * np.sin(t / 12)
    vacuum = -72 + 1.2 * rng.normal(size=n) + 0.7 * np.sin(t / 10)
    
    if scenario == "Degradacion progresiva":
        vibration += np.linspace(0, 4.1, n)
        temperature += np.linspace(0, 16, n)
        vacuum += np.linspace(0, 18, n)
    elif scenario == "Condicion critica":
        vibration += np.linspace(1.5, 6, n) + 0.45 * np.sin(t / 3.5)
        temperature += np.linspace(8, 24, n) + 0.9 * np.sin(t / 5)
        vacuum += np.linspace(10, 28, n)
    elif scenario == "Fuga subito":
        step = int(n * 0.55)
        vibration += np.linspace(0, 1.2, n)
        temperature += np.linspace(0, 5.5, n)
        vacuum[step:] += 18.5
        vacuum[step + 12:] += 6
    elif scenario == "Rodamiento degradado":
        vibration += np.linspace(0.4, 5.2, n) + 0.8 * np.maximum(0, np.sin(t / 4))
        temperature += np.linspace(1, 13, n)
        vacuum += np.linspace(0, 7, n)
    
    df = pd.DataFrame({
        "fecha_hora": dates,
        "vibracion_rms_mm_s": np.round(vibration, 3),
        "temperatura_c": np.round(temperature, 2),
        "presion_vacio_kpa": np.round(vacuum, 2)
    })
    return enrich_data(df)

def risk_vibration(v):
    return float(np.clip((v - 3) / (8.5 - 3) * 100, 0, 100))

def risk_temperature(t):
    return float(np.clip((t - 68) / (92 - 68) * 100, 0, 100))

def risk_vacuum(p):
    return float(np.clip((p - (-72)) / ((-45) - (-72)) * 100, 0, 100))

def variable_status(row):
    v = row["vibracion_rms_mm_s"]
    t = row["temperatura_c"]
    p = row["presion_vacio_kpa"]
    return {
        "Vibracion": "Critico" if v >= THRESHOLDS["vibration_alert"] else "Alerta" if v >= THRESHOLDS["vibration_normal"] else "Normal",
        "Temperatura": "Critico" if t >= THRESHOLDS["temperature_alert"] else "Alerta" if t >= THRESHOLDS["temperature_normal"] else "Normal",
        "Presion de vacio": "Critico" if p >= THRESHOLDS["vacuum_alert"] else "Alerta" if p >= THRESHOLDS["vacuum_normal"] else "Normal",
    }

def classify_risk(ir, row=None):
    if row is not None:
        s = variable_status(row).values()
        if "Critico" in s:
            return "Critico"
        if "Alerta" in s and ir >= 35:
            return "Alerta"
    if ir < 40:
        return "Normal"
    if ir < 70:
        return "Alerta"
    return "Critico"

def enrich_data(df):
    df = df.copy()
    df["riesgo_vibracion"] = df["vibracion_rms_mm_s"].apply(risk_vibration)
    df["riesgo_temperatura"] = df["temperatura_c"].apply(risk_temperature)
    df["riesgo_vacio"] = df["presion_vacio_kpa"].apply(risk_vacuum)
    weights = 0.45 * df["riesgo_vibracion"] + 0.30 * df["riesgo_temperatura"] + 0.25 * df["riesgo_vacio"]
    df["indice_riesgo"] = weights.round(1)
    df["estado"] = [classify_risk(ir, df.iloc[i]) for i, ir in enumerate(df["indice_riesgo"])]
    return df

def get_alarms(row):
    alarms = []
    s = variable_status(row)
    if s["Vibracion"] != "Normal":
        alarms.append((s["Vibracion"], "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s"))
    if s["Temperatura"] != "Normal":
        alarms.append((s["Temperatura"], "Temperatura", f"{row['temperatura_c']:.1f} C"))
    if s["Presion de vacio"] != "Normal":
        alarms.append((s["Presion de vacio"], "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa"))
    return alarms

def create_work_order_obj(row, asset_name, source="Automatica"):
    alarms = get_alarms(row)
    priority = "P0" if row["estado"] == "Critico" else "P1" if row["estado"] == "Alerta" else "P2"
    symptoms = "; ".join([f"{name}: {value} ({level})" for level, name, value in alarms]) or "Sin alarma critica"
    tasks = []
    if any(a[1] == "Vibracion" for a in alarms):
        tasks += ["Medir vibracion", "Verificar alineacion"]
    if any(a[1] == "Temperatura" for a in alarms):
        tasks += ["Revisar lubricacion", "Verificar friccion"]
    if any(a[1] == "Presion de vacio" for a in alarms):
        tasks += ["Prueba de fugas", "Inspeccionar sellos"]
    if not tasks:
        tasks = ["Inspeccion rutinaria"]
    ts = pd.to_datetime(row["fecha_hora"]).strftime("%Y%m%d%H%M")
    return {
        "ot_id": f"OT-{ts}-{priority}",
        "asset_name": asset_name,
        "alert_id": f"ALM-{ts}",
        "description": f"Anomalia: {symptoms}",
        "priority": priority,
        "responsible": "",
        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Pendiente",
        "created_by": "sistema"
    }

def calculate_kpis(oh, failures, dh, pmd, pmp, ph, ahw, pr):
    mtbf = oh / failures if failures else float("inf")
    mttr = dh / failures if failures else 0
    avail = mtbf / (mtbf + mttr) if math.isfinite(mtbf) and (mtbf + mttr) else 1
    rel24 = math.exp(-24 / mtbf) if math.isfinite(mtbf) and mtbf > 0 else 1
    pmc = pmd / pmp if pmp else 0
    bl = ph / ahw if ahw else 0
    pl = dh * pr
    return {
        "MTBF (h)": mtbf,
        "MTTR (h)": mttr,
        "Disponibilidad (%)": avail * 100,
        "Confiabilidad 24h (%)": rel24 * 100,
        "Cumplimiento PM (%)": pmc * 100,
        "Backlog (semanas)": bl,
        "Perdida productiva (t)": pl
    }

# ============================================================================
# ASISTENTE IA
# ============================================================================

def chatbot_response(user_text, latest, kpi_values, asset_name, use_generative_ai=False):
    text = unicodedata.normalize('NFKD', user_text.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100 | Vibracion {latest['vibracion_rms_mm_s']:.2f} mm/s | Temp {latest['temperatura_c']:.1f} C | Vacio {latest['presion_vacio_kpa']:.1f} kPa"
    alarms = get_alarms(latest)
    at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas"
    
    if any(k in text for k in ["hola", "ayuda", "quiero", "necesito"]):
        return f"Bienvenido a Tech Maint Pro\n\n{sl}\n\nPuedo ayudarte con diagnostico, ordenes de trabajo, AMEF, KPIs e impacto circular."
    
    if any(k in text for k in ["estado", "riesgo", "condicion", "diagnostico"]):
        na = [a[1] for a in alarms]
        if "Vibracion" in na and "Temperatura" in na:
            hip = "Posible desgaste de rodamientos o desalineacion."
        elif "Presion de vacio" in na:
            hip = "Posible fuga en linea o deterioro de sellos."
        elif "Vibracion" in na:
            hip = "Posible desalineacion o desgaste de rodamiento."
        elif "Temperatura" in na:
            hip = "Posible friccion interna o lubricacion deficiente."
        else:
            hip = "Condicion normal."
        acc = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT prioritaria"
        return f"Diagnostico\n\n{sl}\n\nAlarmas: {at}\n\nHipotesis: {hip}\n\nAccion: {acc}"
    
    if any(k in text for k in ["orden", "trabajo", "ot", "generar"]):
        pri = "P0" if latest["estado"] == "Critico" else "P1" if latest["estado"] == "Alerta" else "P2"
        sint = "; ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) or "Sin alarma critica"
        tareas = []
        if any(a[1] == "Vibracion" for a in alarms):
            tareas += ["Medir vibracion", "Verificar alineacion"]
        if any(a[1] == "Temperatura" for a in alarms):
            tareas += ["Revisar lubricacion", "Verificar friccion"]
        if any(a[1] == "Presion de vacio" for a in alarms):
            tareas += ["Prueba de fugas", "Inspeccionar sellos"]
        if not tareas:
            tareas = ["Inspeccion rutinaria"]
        tareas_str = "\n".join(["- " + t for t in tareas])
        return f"OT Sugerida\n\nPrioridad: {pri}\nActivo: {asset_name}\nSintomas: {sint}\n\nTareas:\n{tareas_str}"
    
    if any(k in text for k in ["vibracion", "vibra"]):
        v = latest["vibracion_rms_mm_s"]
        vs = "Critico" if v >= THRESHOLDS["vibration_alert"] else "Alerta" if v >= THRESHOLDS["vibration_normal"] else "Normal"
        return f"Vibracion\n\nLectura: {v:.2f} mm/s\nEstado: {vs}\n\nCausas: Desgaste rodamientos, desalineacion, desbalance.\n\nAcciones: Medir vibracion, verificar alineacion, revisar lubricante."
    
    if any(k in text for k in ["temperatura", "temp", "calor"]):
        t = latest["temperatura_c"]
        ts = "Critico" if t >= THRESHOLDS["temperature_alert"] else "Alerta" if t >= THRESHOLDS["temperature_normal"] else "Normal"
        return f"Temperatura\n\nLectura: {t:.1f} C\nEstado: {ts}\n\nCausas: Friccion interna, lubricacion deficiente, sobrecarga.\n\nAcciones: Revisar lubricante, inspeccionar enfriamiento."
    
    if any(k in text for k in ["vacio", "presion"]):
        p = latest["presion_vacio_kpa"]
        ps = "Critico" if p >= THRESHOLDS["vacuum_alert"] else "Alerta" if p >= THRESHOLDS["vacuum_normal"] else "Normal"
        return f"Presion de Vacio\n\nLectura: {p:.1f} kPa\nEstado: {ps}\n*Mas negativo es mejor*\n\nCausas: Fuga en linea, deterioro de sellos.\n\nAcciones: Prueba de fugas, inspeccionar sellos."
    
    if any(k in text for k in ["kpi", "indicador"]):
        return f"KPIs\n\nMTBF: {kpi_values['MTBF (h)']:.1f} h\nMTTR: {kpi_values['MTTR (h)']:.1f} h\nDisponibilidad: {kpi_values['Disponibilidad (%)']:.2f}%\nConfiabilidad 24h: {kpi_values['Confiabilidad 24h (%)']:.2f}%"
    
    if any(k in text for k in ["amef", "rcm", "falla"]):
        return "AMEF/RCM\n\nModos de falla:\n1. Vibracion alta - Desgaste rodamientos/desalineacion\n2. Temperatura alta - Friccion/lubricacion deficiente\n3. Perdida de vacio - Fuga/deterioro sellos"
    
    if any(k in text for k in ["circular", "impacto", "residuo"]):
        return "Impacto Circular\n\nRegistro de decisiones que permiten conservar componentes y minimizar residuos.\n\nComo registrar: Cierra una OT -> Selecciona decision -> Registra masa conservada/descartada."
# ============================================================================
# CHATBOT FLOTANTE AUTOMATICO - VERSION CORREGIDA
# ============================================================================

def process_floating_query(query):
    if not query or not query.strip():
        return
    q = query.strip()
    st.session_state.floating_chat_history.append({"role": "user", "content": q})
    try:
        kp = calculate_kpis(720, 3, 18, 18, 20, 40, 80, st.session_state.get("production_rate", 85.5))
        reply = chatbot_response(q, st.session_state.get("latest_row", pd.Series()), kp, st.session_state.get("asset_name", ""), use_generative_ai=False)
        st.session_state.floating_chat_history.append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state.floating_chat_history.append({"role": "assistant", "content": f"Error: {e}"})

@st.dialog("Asistente Tech Maint Pro", width="large")
def floating_chat_dialog():
    st.markdown("### Asistente tecnico de mantenimiento")
    st.caption("Respuestas instantaneas basadas en datos reales")
    st.divider()
    
    if st.session_state.floating_chat_history:
        for msg in st.session_state.floating_chat_history[-10:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown("Hola! Soy Tech Maint Pro AI. En que puedo ayudarte?")
    
    st.divider()
    st.markdown("#### Consultas rapidas:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Estado actual", key="qr1", use_container_width=True):
            process_floating_query("Estado actual")
        if st.button("Alta vibracion", key="qr2", use_container_width=True):
            process_floating_query("Que causa alta vibracion?")
        if st.button("KPIs", key="qr3", use_container_width=True):
            process_floating_query("Cuales son los KPIs?")
    with c2:
        if st.button("Caída de vacio", key="qr4", use_container_width=True):
            process_floating_query("Que revisar si cae el vacio?")
        if st.button("Generar OT", key="qr5", use_container_width=True):
            process_floating_query("Generar orden de trabajo")
        if st.button("Impacto circular", key="qr6", use_container_width=True):
            process_floating_query("Que es impacto circular?")
    with c3:
        if st.button("Modos de falla", key="qr7", use_container_width=True):
            process_floating_query("Modos de falla AMEF")
        if st.button("Temperatura", key="qr8", use_container_width=True):
            process_floating_query("Analiza la temperatura actual")
        if st.button("Limpiar", key="qr9", use_container_width=True):
            st.session_state.floating_chat_history = []
    
    st.divider()
    ui = st.chat_input("Escribe tu consulta...", key="fci")
    if ui:
        process_floating_query(ui)
    
    if st.button("Cerrar chat", key="fcc", use_container_width=True):
        st.session_state.floating_chat_open = False
        st.session_state.auto_chat_triggered = False

# Boton flotante
btn_html = f"""
<div style="position:fixed;bottom:30px;right:30px;z-index:9999;">
<button onclick="document.getElementById('fc_toggle').click()" style="width:65px;height:65px;background:linear-gradient(135deg,{COLORS['azul']},{COLORS['verde']});border-radius:50%;border:3px solid {COLORS['amarillo']};cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,0.2);">
{render_logo("50px")}
</button>
</div>
<div style="display:none;">
"""
st.markdown(btn_html, unsafe_allow_html=True)

if st.button("Abrir asistente", key="fc_toggle", help="Abrir asistente"):
    st.session_state.floating_chat_open = not st.session_state.floating_chat_open

st.markdown("</div>", unsafe_allow_html=True)

# Mostrar el dialogo si esta abierto
if st.session_state.get("floating_chat_open", False):
    floating_chat_dialog()

# Abrir chat automaticamente en alertas
if st.session_state.get("auto_chat_triggered", False) and not st.session_state.get("floating_chat_open", False):
    st.session_state.floating_chat_open = True
    
# ============================================================================
# VISUALIZACION - GRAFICAS CORREGIDAS (sin titlefont)
# ============================================================================

def create_sensor_chart(df, column, title, y_title, color, threshold_normal=None, threshold_alert=None, reverse=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha_hora"],
        y=df[column],
        mode="lines+markers",
        name=title,
        line=dict(color=color, width=3),
        marker=dict(size=4),
        fill="tozeroy" if not reverse else None,
        fillcolor="rgba(26,95,168,0.08)" if not reverse else None
    ))
    if threshold_normal is not None:
        fig.add_hline(
            y=threshold_normal,
            line_dash="dash",
            line_color=COLORS["amarillo"],
            line_width=2,
            annotation_text="Alerta",
            annotation_position="top right",
            annotation_font_color=COLORS["amarillo"],
            annotation_font_size=11
        )
    if threshold_alert is not None:
        fig.add_hline(
            y=threshold_alert,
            line_dash="dash",
            line_color=COLORS["rojo"],
            line_width=2,
            annotation_text="Critico",
            annotation_position="top right",
            annotation_font_color=COLORS["rojo"],
            annotation_font_size=11
        )
    
    fig.update_layout(
        title=dict(text=title, font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")),
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0.9)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        margin=dict(l=20, r=20, t=78, b=30),
        xaxis=dict(
            title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)),
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            tickfont=dict(color=COLORS["texto_oscuro"], size=10)
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color=COLORS["texto_oscuro"], size=12)),
            autorange="reversed" if reverse else True,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            tickfont=dict(color=COLORS["texto_oscuro"], size=10)
        ),
        hovermode="x unified",
        showlegend=False,
        height=280
    )
    return fig

def create_vibration_chart(df):
    return create_sensor_chart(
        df, "vibracion_rms_mm_s", "Vibracion RMS", "mm/s",
        COLORS["azul"], THRESHOLDS["vibration_normal"], THRESHOLDS["vibration_alert"]
    )

def create_temperature_chart(df):
    return create_sensor_chart(
        df, "temperatura_c", "Temperatura", "C",
        COLORS["amarillo"], THRESHOLDS["temperature_normal"], THRESHOLDS["temperature_alert"]
    )

def create_vacuum_chart(df):
    return create_sensor_chart(
        df, "presion_vacio_kpa", "Presion de vacio", "kPa",
        COLORS["verde"], THRESHOLDS["vacuum_normal"], THRESHOLDS["vacuum_alert"],
        reverse=True
    )

def create_risk_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha_hora"],
        y=df["indice_riesgo"],
        mode="lines+markers",
        name="IR",
        line=dict(color=COLORS["amarillo"], width=3),
        fill="tozeroy",
        fillcolor="rgba(245,166,35,0.10)",
        marker=dict(size=4)
    ))
    fig.add_hline(
        y=40, line_dash="dash", line_color=COLORS["amarillo"], line_width=2,
        annotation_text="Alerta", annotation_position="top right",
        annotation_font_color=COLORS["amarillo"], annotation_font_size=11
    )
    fig.add_hline(
        y=70, line_dash="dash", line_color=COLORS["rojo"], line_width=2,
        annotation_text="Critico", annotation_position="top right",
        annotation_font_color=COLORS["rojo"], annotation_font_size=11
    )
    fig.update_layout(
        title=dict(text="Indice de riesgo", font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")),
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0.9)",
        plot_bgcolor="rgba(255,255,255,0.9)",
        margin=dict(l=20, r=20, t=52, b=20),
        xaxis=dict(
            title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)),
            showgrid=True, gridcolor="rgba(0,0,0,0.08)",
            tickfont=dict(color=COLORS["texto_oscuro"], size=10)
        ),
        yaxis=dict(
            title=dict(text="IR", font=dict(color=COLORS["texto_oscuro"], size=12)),
            range=[0, 100], showgrid=True, gridcolor="rgba(0,0,0,0.08)",
            tickfont=dict(color=COLORS["texto_oscuro"], size=10)
        ),
        hovermode="x unified",
        height=280
    )
    return fig

# ============================================================================
# BASE DE DATOS
# ============================================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (
        ot_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, alert_id TEXT,
        description TEXT, priority TEXT NOT NULL, responsible TEXT,
        creation_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendiente',
        created_by TEXT, updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT NOT NULL,
        component TEXT NOT NULL, decision TEXT NOT NULL, result TEXT,
        mass_conserved_kg REAL DEFAULT 0, mass_discarded_kg REAL DEFAULT 0,
        evidence TEXT, recorded_date TEXT NOT NULL, recorded_by TEXT,
        FOREIGN KEY (ot_id) REFERENCES work_orders(ot_id)
    )""")
    conn.commit()
    conn.close()

# ============================================================================
# INICIALIZACION
# ============================================================================

init_database()

sd = {
    "running": True, "sim_idx": 1, "orders": [], "last_order_event": None,
    "chat_history": [], "theme_mode": "default", "kb_docs": [],
    "kb_chunks": [], "kb_ready": False, "last_beep_event": None,
    "floating_chat_open": False, "floating_chat_history": [],
    "auto_chat_triggered": False, "previous_estado": None,
    "scenario": "Operacion normal", "seed": 42, "n_hours": 168,
    "step_speed": 3, "production_rate": 85.5
}
for k, v in sd.items():
    if k not in st.session_state:
        st.session_state[k] = v

apply_custom_styles()

# ============================================================================
# HEADER CON TITULO ARRIBA Y NAVEGACION HORIZONTAL
# ============================================================================

col_logo, col_title = st.columns([1, 9])
with col_logo:
    st.markdown(render_logo("70px"), unsafe_allow_html=True)
with col_title:
    st.markdown("<h1 style='margin:0;color:white;font-size:2.5rem;'>Tech Maint Pro</h1>", unsafe_allow_html=True)
    tagline = f"<p style='margin:5px 0 0 0;color:{COLORS['amarillo']};font-size:1.1rem;font-weight:600;'>Mantenimiento Inteligente + Economia Circular</p>"
    st.markdown(tagline, unsafe_allow_html=True)

# Tabs de navegacion horizontal
tabs = st.tabs(["Monitoreo", "Diagnostico", "Ordenes de Trabajo", "Impacto Circular", "KPIs"])

# Selector de activo debajo de los tabs
asset_name = st.selectbox("Selector de activo", list(ASSETS.keys()), label_visibility="collapsed")
st.caption(f"Tag: {ASSETS[asset_name]['tag']} | Criticidad: {ASSETS[asset_name]['criticality']}")

# ============================================================================
# SIMULACION CONTINUA AUTOMATICA
# ============================================================================

DF_FULL = generate_synthetic_data(
    st.session_state.scenario,
    n=st.session_state.n_hours,
    seed=int(st.session_state.seed)
)
max_idx = len(DF_FULL)
st.session_state.sim_idx = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=1000, key="tm_live")
    st.session_state.sim_idx = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)
elif st.session_state.sim_idx >= max_idx:
    st.session_state.sim_idx = 1

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state.latest_row = latest
st.session_state.asset_name = asset_name

# Detectar cambio de estado para abrir chatbot automatico
current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state.auto_chat_triggered = True
    if current_estado == "Critico":
        play_critical_alarm(f"{latest['fecha_hora']}-critical")
    else:
        play_observation_alarm(f"{latest['fecha_hora']}-alert")
    
    alert_msg = f"ALERTA AUTOMATICA: Estado {current_estado} detectado en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. Se requiere atencion inmediata."
    st.session_state.floating_chat_history.append({"role": "assistant", "content": alert_msg})

st.session_state.previous_estado = current_estado

# Generar OT automatica
if latest["estado"] in ["Alerta", "Critico"]:
    ek = f"{latest['fecha_hora']}-{latest['estado']}"
    if st.session_state.last_order_event != ek:
        new_ot = create_work_order_obj(latest, asset_name, source="Automatica por alarma")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot["ot_id"],))
        if not c.fetchone():
            c.execute("""INSERT INTO work_orders (ot_id, asset_name, alert_id, description, priority, responsible, creation_date, status, created_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_ot["ot_id"], new_ot["asset_name"], new_ot["alert_id"], new_ot["description"], new_ot["priority"], new_ot["responsible"], new_ot["creation_date"], new_ot["status"], new_ot["created_by"], datetime.now().isoformat()))
            conn.commit()
        conn.close()
        st.session_state.last_order_event = ek

# ============================================================================
# TAB 1: MONITOREO EN VIVO - 4 INDICADORES EN FILA CON GRAFICAS DEBAJO
# ============================================================================

with tabs[0]:
    statuses = variable_status(latest)
    
    # Función auxiliar para obtener color del estado
    def get_status_color(status):
        if status == "Normal":
            return COLORS["verde"]
        elif status == "Alerta":
            return COLORS["amarillo"]
        else:
            return COLORS["rojo"]
    
    # 4 columnas: cada una con métrica + gráfica debajo
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sc = get_status_color(statuses["Vibracion"])
        bc = f"badge-{statuses['Vibracion'].lower()}"
        card_html = f"""
        <div class="metric-card status-{statuses['Vibracion'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{sc};margin-bottom:8px;">VIBRACION RMS</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{COLORS['texto_oscuro']};">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div class="{bc}" style="font-size:1.1rem;">{statuses['Vibracion'].upper()}</div>
            <div style="font-size:0.8rem;color:{COLORS['texto_gris']};margin-top:8px;">Ref: {THRESHOLDS['vibration_normal']} / {THRESHOLDS['vibration_alert']}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        st.plotly_chart(create_vibration_chart(DF), use_container_width=True)
    
    with col2:
        sc = get_status_color(statuses["Temperatura"])
        bc = f"badge-{statuses['Temperatura'].lower()}"
        card_html = f"""
        <div class="metric-card status-{statuses['Temperatura'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{sc};margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{COLORS['texto_oscuro']};">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">C</span></div>
            <div class="{bc}" style="font-size:1.1rem;">{statuses['Temperatura'].upper()}</div>
            <div style="font-size:0.8rem;color:{COLORS['texto_gris']};margin-top:8px;">Ref: {THRESHOLDS['temperature_normal']} / {THRESHOLDS['temperature_alert']}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        st.plotly_chart(create_temperature_chart(DF), use_container_width=True)
    
    with col3:
        sc = get_status_color(statuses["Presion de vacio"])
        bc = f"badge-{statuses['Presion de vacio'].lower()}"
        card_html = f"""
        <div class="metric-card status-{statuses['Presion de vacio'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{sc};margin-bottom:8px;">PRESION DE VACIO</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{COLORS['texto_oscuro']};">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div class="{bc}" style="font-size:1.1rem;">{statuses['Presion de vacio'].upper()}</div>
            <div style="font-size:0.8rem;color:{COLORS['texto_gris']};margin-top:8px;">Mas negativo = mejor</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        st.plotly_chart(create_vacuum_chart(DF), use_container_width=True)
    
    with col4:
        ec = get_status_color(latest["estado"])
        card_html = f"""
        <div class="metric-card" style="border-left-color:{ec};">
            <div style="font-size:1.1rem;font-weight:800;color:{ec};margin-bottom:8px;">ESTADO GLOBAL</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{ec};">{latest['estado'].upper()}</div>
            <div style="font-size:1.1rem;color:{COLORS['texto_gris']};">IR: {latest['indice_riesgo']:.1f}/100</div>
            <div style="font-size:0.8rem;color:{COLORS['texto_gris']};margin-top:8px;">Avance: {st.session_state.sim_idx}/{max_idx}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        st.plotly_chart(create_risk_chart(DF), use_container_width=True)
    
    # Alarmas activas
    alarms = get_alarms(latest)
    if alarms:
        st.markdown(f"<h3 style='margin-top:30px;color:{COLORS['texto_oscuro']};'>Alarmas Activas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            ac = "alarm-critical" if level == "Critico" else ""
            icon = "[!]" if level == "Critico" else "[*]"
            color = COLORS["rojo"] if level == "Critico" else COLORS["amarillo"]
            banner_html = f"""
            <div class="alarm-banner {ac}">
                <div style="font-weight:bold;font-size:1.1rem;color:{color};">{icon} {level}: {name}</div>
                <div style="margin-top:5px;">{name} fuera de rango: <strong>{value}</strong></div>
            </div>
            """
            st.markdown(banner_html, unsafe_allow_html=True)

# ============================================================================
# TAB 2: DIAGNOSTICO
# ============================================================================

with tabs[1]:
    st.markdown("<h2>Diagnostico en Tiempo Real</h2>", unsafe_allow_html=True)
    
    alarms = get_alarms(latest)
    ec = COLORS["verde"] if latest["estado"] == "Normal" else COLORS["amarillo"] if latest["estado"] == "Alerta" else COLORS["rojo"]
    
    diag_html = f"""
    <div style="background:{COLORS['blanco']};padding:20px;border-radius:16px;border-left:6px solid {ec};margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);">
        <div style="font-size:1.5rem;font-weight:bold;color:{ec};">Estado Actual: {latest['estado'].upper()}</div>
        <div style="font-size:1.2rem;margin-top:10px;color:{COLORS['texto_oscuro']};">Indice de Riesgo: {latest['indice_riesgo']:.1f}/100</div>
    </div>
    """
    st.markdown(diag_html, unsafe_allow_html=True)
    
    if alarms:
        st.markdown("<h3>Hipotesis Tecnicas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            if name == "Vibracion":
                st.markdown("- **Posible desgaste de rodamientos**, desalineacion o lubricacion deficiente.")
            elif name == "Temperatura":
                st.markdown("- **Posible friccion interna**, lubricacion deficiente o sobrecarga.")
            elif name == "Presion de vacio":
                st.markdown("- **Posible fuga en linea**, deterioro de sellos o restriccion en succion.")
        
        st.markdown("<h3>Pasos Sugeridos</h3>", unsafe_allow_html=True)
        pasos = "1. Verificar lectura con instrumento calibrado\n2. Inspeccionar visualmente el componente\n3. Revisar manual del fabricante\n4. Comprobar operacion segura\n5. Evaluar necesidad de repuesto"
        st.markdown(pasos)
        
        accion = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT Prioridad 0"
        acc_html = f"<div style='background:{COLORS['blanco']};padding:15px;border-radius:12px;margin-top:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);'><strong>Accion Inmediata:</strong> {accion}</div>"
        st.markdown(acc_html, unsafe_allow_html=True)
    else:
        st.success("Sin alarmas activas. Condicion normal.")
    
    if st.button("Generar Orden de Trabajo", use_container_width=True, type="primary"):
        ot = create_work_order_obj(latest, asset_name, source="Manual desde diagnostico")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (ot["ot_id"],))
        if not c.fetchone():
            c.execute("""INSERT INTO work_orders (ot_id, asset_name, alert_id, description, priority, responsible, creation_date, status, created_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ot["ot_id"], ot["asset_name"], ot["alert_id"], ot["description"], ot["priority"], ot["responsible"], ot["creation_date"], ot["status"], ot["created_by"], datetime.now().isoformat()))
            conn.commit()
            st.success(f"OT creada: {ot['ot_id']}")
        else:
            st.info(f"OT ya existe: {ot['ot_id']}")
        conn.close()

# ============================================================================
# TAB 3: ORDENES DE TRABAJO
# ============================================================================

with tabs[2]:
    st.markdown("<h2>Gestion de Ordenes de Trabajo</h2>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM work_orders ORDER BY creation_date DESC")
    orders = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if orders:
        filter_status = st.multiselect("Filtrar por estado", ["Pendiente", "En Ejecucion", "Cerrada"], default=["Pendiente", "En Ejecucion", "Cerrada"])
        filtered = [o for o in orders if o["status"] in filter_status]
        
        for ot in filtered[:10]:
            with st.expander(f"{ot['ot_id']} - {ot['asset_name'][:40]}... ({ot['status']})"):
                st.markdown(f"**ID:** {ot['ot_id']} | **Activo:** {ot['asset_name']} | **Prioridad:** {ot['priority']}")
                st.markdown(f"**Descripcion:** {ot['description']} | **Responsable:** {ot['responsible'] or 'No asignado'}")
                st.markdown("---")
                
                new_status = st.selectbox("Nuevo estado", ["Pendiente", "En Ejecucion", "Cerrada"], key=f"ns_{ot['ot_id']}")
                if st.button("Actualizar", key=f"up_{ot['ot_id']}"):
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("UPDATE work_orders SET status=?, updated_at=? WHERE ot_id=?", (new_status, datetime.now().isoformat(), ot['ot_id']))
                    conn.commit()
                    if new_status == "Cerrada":
                        notify_ot_completion(ot)
                    conn.close()
                    st.success("Estado actualizado")
                    st.rerun()
                
                if ot["status"] == "Cerrada":
                    st.markdown("**Registrar intervencion circular:**")
                    comp = st.text_input("Componente", key=f"comp_{ot['ot_id']}")
                    dec = st.selectbox("Decision", ["Inspeccion", "Reparacion", "Reemplazo Parcial", "Reemplazo Total"], key=f"dec_{ot['ot_id']}")
                    res = st.selectbox("Resultado", ["Reparado", "Reutilizado", "Reemplazado", "Descartado"], key=f"res_{ot['ot_id']}")
                    mc = st.number_input("Masa conservada (kg)", min_value=0.0, value=0.0, key=f"mc_{ot['ot_id']}")
                    md = st.number_input("Masa descartada (kg)", min_value=0.0, value=0.0, key=f"md_{ot['ot_id']}")
                    if st.button("Registrar", key=f"sub_{ot['ot_id']}"):
                        notify_economic_impact({
                            "ot_id": ot.get("ot_id", ""),
                            "component": comp,
                            "decision": dec,
                            "result": res,
                            "mass_conserved_kg": mc,
                            "mass_discarded_kg": md
                        })
                        st.success("Intervencion registrada")
    else:
        st.info("No hay ordenes registradas.")

# ============================================================================
# TAB 4: IMPACTO CIRCULAR
# ============================================================================

with tabs[3]:
    st.markdown("<h2>Panel de Impacto Circular</h2>", unsafe_allow_html=True)
    st.write("Registro de decisiones de mantenimiento y su impacto en la conservacion de recursos.")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM circular_interventions ORDER BY recorded_date DESC")
    interventions = [dict(row) for row in c.fetchall()]
    conn.close()
    
    total = len(interventions)
    repaired = sum(1 for i in interventions if i["decision"] in ["Reparado", "Reutilizado"])
    conserved = sum(i["mass_conserved_kg"] or 0 for i in interventions)
    discarded = sum(i["mass_discarded_kg"] or 0 for i in interventions)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Intervenciones", total)
    with c2:
        st.metric("Reparados/Reutilizados", repaired)
    with c3:
        st.metric("Masa Conservada (kg)", f"{conserved:.2f}")
    with c4:
        st.metric("Masa Descartada (kg)", f"{discarded:.2f}")
    
    if interventions:
        st.dataframe(pd.DataFrame(interventions), use_container_width=True, hide_index=True)

# ============================================================================
# TAB 5: KPIs
# ============================================================================

with tabs[4]:
    st.markdown("<h2>KPIs e Indicadores</h2>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    oh = c1.number_input("Horas operativas", value=720.0, min_value=0.0)
    fl = c1.number_input("Numero de fallas", value=3, min_value=0)
    dh = c2.number_input("Horas de parada", value=18.0, min_value=0.0)
    pmd = c2.number_input("PM ejecutados", value=18, min_value=0)
    pmp = c3.number_input("PM programados", value=20, min_value=0)
    ph = c3.number_input("HH pendientes", value=40.0, min_value=0.0)
    ahw = st.number_input("HH disponibles/semana", value=80.0, min_value=1.0)
    
    kpis = calculate_kpis(oh, fl, dh, pmd, pmp, ph, ahw, st.session_state.production_rate)
    
    kk1, kk2, kk3, kk4 = st.columns(4)
    kk1.metric("MTBF", f"{kpis['MTBF (h)']:.1f} h")
    kk2.metric("MTTR", f"{kpis['MTTR (h)']:.1f} h")
    kk3.metric("Disponibilidad", f"{kpis['Disponibilidad (%)']:.2f}%")
    kk4.metric("Perdida productiva", f"{kpis['Perdida productiva (t)']:.1f} t")
    
    st.dataframe(pd.DataFrame({"KPI": list(kpis.keys()), "Valor": list(kpis.values())}), use_container_width=True, hide_index=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("Tech Maint Pro | Prototipo profesional SeedTech 2026 | Los umbrales son referenciales")
