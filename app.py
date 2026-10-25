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
from datetime import datetime, timedelta
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
    HAS_REQUESTS = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ============================================================================
# CONFIGURACIÓN Y LOGGING
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
# CONFIGURACIÓN TELEGRAM
# ============================================================================
TELEGRAM_BOT_TOKEN = "8944581569:AAFw2rfEn3zU5iOpdNrtIzYHLTs30xg_cIA"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

STAFF = {
    "tecnico": {
        "nombre": "DARIO MINAN ESPINOZA",
        "telefono": "958000191",
        "email": "dario.minanespinoza@gmail.com",
        "telegram_chat_id": "1330744031",
        "rol": "Tecnico de Mantenimiento"
    },
    "asesor": {
        "nombre": "JORDY ALBERTO SERNAQUE SABA",
        "telefono": "902631386",
        "email": "ajordyss0602@gmail.com",
        "telegram_chat_id": "8665066190",
        "rol": "Asesor de Mantenimiento"
    },
    "gerencia": {
        "nombre": "Irina Nicole Castillo Coronado",
        "telefono": "966153839",
        "email": "nicolecastc@gmail.com",
        "telegram_chat_id": "8533612747",
        "rol": "Gerencia"
    }
}

# ============================================================================
# LOGOS BASE64
# ============================================================================
LOGO_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAKlBB4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9U6KKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAK......" # (Truncado por brevedad, usa el completo de tu archivo)

LETZY_BASE64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAZABkADASIAAhEBAxEB/8QAHQABAAEEAwEAAAAAAAAAAAAAAAgBAgcJAwUGBP/EAF4QAAIBAwIDBQQFCAYGBQkDDQABAgMEEQUGByExCBJBUWETInGBCRQykaEVI0JSYoKxwRYzcpKi8CQ0Q7LC0SVTk7PSF2NzdHWDo+HxNTY3RFTDGCY4VpQnhKTT4v/EABwBAQACAwEBAQAAAAAAAAAAAAAGBwEEBQMCCP/EAEERAQABAwIDBAkCBAUCBwEBAQABAgMEBREGITESE0FRFCIyYXGBkaGxwdEVI0LhM1JicvAkNBYlNUOSovFEU4L/2gAMAwEAAhEDEQA/ANqYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA......"

def render_logo(size="180px"):
    return f'<img src="{LOGO_BASE64}" style="width:{size}; height:auto; display:inline-block;" />'

def render_letzy(size="84px"):
    return f'<img src="{LETZY_BASE64}" style="width:{size}; height:{size}; border-radius:50%; display:block; object-fit:cover;" />'

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Tech Maint Pro",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Ocultar sidebar completamente
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.stApp > header { background-color: transparent; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PALETA DE COLORES OFICIAL
# ============================================================================
COLORS = {
    "azul": "#1a5fa8",
    "verde": "#8bc34a",    # Verde más claro y vibrante
    "amarillo": "#f5a623",
    "rojo": "#d32f2f",
    "blanco": "#ffffff",
    "gris_claro": "#f5f7fa",
    "gris_medio": "#e8ecf1",
    "texto_oscuro": "#1a2b4c",
    "texto_gris": "#5a6b7c",
}

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================
def apply_custom_styles():
    css = f"""
    <style>
    .stApp {{ background: linear-gradient(135deg, {COLORS['gris_claro']} 0%, #ffffff 100%) !important; padding-top: 0 !important; }}
    .block-container {{ padding-top: 0.5rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }}
    
    .metric-card {{
        border-radius: 16px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease; text-align: center; border: none;
    }}
    .metric-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.12); }}
    
    .status-normal {{ background: {COLORS['verde']} !important; }}
    .status-alerta {{ background: {COLORS['amarillo']} !important; }}
    .status-critico {{ background: {COLORS['rojo']} !important; }}
    
    .alarm-banner {{
        background: linear-gradient(90deg, rgba(245,166,35,0.15), rgba(245,166,35,0.05));
        border-left: 5px solid {COLORS['amarillo']}; border-radius: 12px; padding: 12px 16px; margin-bottom: 12px;
    }}
    .alarm-critical {{
        background: linear-gradient(90deg, rgba(211,47,47,0.15), rgba(211,47,47,0.05));
        border-left: 5px solid {COLORS['rojo']};
    }}
    
    h1, h2, h3, p, label, span, div {{ color: {COLORS['texto_oscuro']} !important; }}
    .stMarkdown p {{ color: {COLORS['texto_oscuro']} !important; }}
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: {COLORS['azul']} !important; }}
    
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; margin-bottom: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(26,95,168,0.1) !important; color: {COLORS['texto_oscuro']} !important;
        border-radius: 8px 8px 0 0; padding: 8px 16px; font-size: 0.9rem;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ background: {COLORS['azul']} !important; color: white !important; }}
    
    /* Chatbot Dialog Styles */
    div[data-testid="stDialog"] {{ background: #f5f7fa !important; color: #1a2b4c !important; }}
    div[data-testid="stDialog"] * {{ color: #1a2b4c !important; }}
    div[data-testid="stDialog"] h3 {{ color: #1a5fa8 !important; }}
    div[data-testid="stDialog"] .stButton > button {{
        background: #1a5fa8 !important; color: #ffffff !important; border: none !important;
        border-radius: 8px !important; font-weight: 600 !important;
    }}
    div[data-testid="stChatMessage"] {{ background: #ffffff !important; border: 1px solid #e8ecf1 !important; }}
    div[data-testid="stChatMessage"] p {{ color: #1a2b4c !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE DATOS Y RIESGO
# ============================================================================
THRESHOLDS = {
    "vibration_normal": 4.5, "vibration_alert": 7.1,
    "temperature_normal": 75.0, "temperature_alert": 85.0,
    "vacuum_normal": -65.0, "vacuum_alert": -55.0,
}

def generate_synthetic_data(scenario, n=240, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    start = datetime.now() - timedelta(hours=n)
    dates = [start + timedelta(hours=int(i)) for i in t]
    
    vibration = 2.8 + 0.28 * rng.normal(size=n) + 0.12 * np.sin(t / 9)
    temperature = 66 + 1.6 * rng.normal(size=n) + 0.5 * np.sin(t / 12)
    vacuum = -72 + 1.2 * rng.normal(size=n) + 0.7 * np.sin(t / 10)
    
    if scenario == "Degradacion progresiva":
        vibration += np.linspace(0, 4.1, n); temperature += np.linspace(0, 16, n); vacuum += np.linspace(0, 18, n)
    elif scenario == "Condicion critica":
        vibration += np.linspace(1.5, 6, n) + 0.45 * np.sin(t / 3.5)
        temperature += np.linspace(8, 24, n) + 0.9 * np.sin(t / 5)
        vacuum += np.linspace(10, 28, n)
    elif scenario == "Fuga subito":
        step = int(n * 0.55)
        vibration += np.linspace(0, 1.2, n); temperature += np.linspace(0, 5.5, n)
        vacuum[step:] += 18.5; vacuum[step + 12:] += 6
        
    df = pd.DataFrame({
        "fecha_hora": dates,
        "vibracion_rms_mm_s": np.round(vibration, 3),
        "temperatura_c": np.round(temperature, 2),
        "presion_vacio_kpa": np.round(vacuum, 2)
    })
    return enrich_data(df)

def risk_vibration(v): return float(np.clip((v - 3) / (8.5 - 3) * 100, 0, 100))
def risk_temperature(t): return float(np.clip((t - 68) / (92 - 68) * 100, 0, 100))
def risk_vacuum(p): return float(np.clip((p - (-72)) / ((-45) - (-72)) * 100, 0, 100))

def variable_status(row):
    v, t, p = row["vibracion_rms_mm_s"], row["temperatura_c"], row["presion_vacio_kpa"]
    return {
        "Vibracion": "Critico" if v >= THRESHOLDS["vibration_alert"] else "Alerta" if v >= THRESHOLDS["vibration_normal"] else "Normal",
        "Temperatura": "Critico" if t >= THRESHOLDS["temperature_alert"] else "Alerta" if t >= THRESHOLDS["temperature_normal"] else "Normal",
        "Presion de vacio": "Critico" if p >= THRESHOLDS["vacuum_alert"] else "Alerta" if p >= THRESHOLDS["vacuum_normal"] else "Normal",
    }

def classify_risk(ir, row=None):
    if row is not None:
        s = variable_status(row).values()
        if "Critico" in s: return "Critico"
        if "Alerta" in s and ir >= 35: return "Alerta"
    if ir < 40: return "Normal"
    if ir < 70: return "Alerta"
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
    if s["Vibracion"] != "Normal": alarms.append((s["Vibracion"], "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s"))
    if s["Temperatura"] != "Normal": alarms.append((s["Temperatura"], "Temperatura", f"{row['temperatura_c']:.1f} C"))
    if s["Presion de vacio"] != "Normal": alarms.append((s["Presion de vacio"], "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa"))
    return alarms

def calculate_kpis(oh, failures, dh, pmd, pmp, ph, ahw, pr):
    mtbf = oh / failures if failures else float("inf")
    mttr = dh / failures if failures else 0
    avail = mtbf / (mtbf + mttr) if math.isfinite(mtbf) and (mtbf + mttr) else 1
    rel24 = math.exp(-24 / mtbf) if math.isfinite(mtbf) and mtbf > 0 else 1
    pmc = pmd / pmp if pmp else 0
    bl = ph / ahw if ahw else 0
    pl = dh * pr
    return {
        "MTBF (h)": mtbf, "MTTR (h)": mttr, "Disponibilidad (%)": avail * 100,
        "Confiabilidad 24h (%)": rel24 * 100, "Cumplimiento PM (%)": pmc * 100,
        "Backlog (semanas)": bl, "Perdida productiva (t)": pl
    }

# ============================================================================
# CHATBOT LETZY
# ============================================================================
def chatbot_response(user_query, latest, asset_name):
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100"
    alarms = get_alarms(latest)
    at = ", ".join([f"{n}: {v}" for _, n, v in alarms]) if alarms else "Sin alarmas"
    
    if any(k in text for k in ["hola", "ayuda", "quiero"]):
        return f"¡Hola! Soy Letzy. {sl}. Puedo ayudarte con diagnóstico, órdenes de trabajo, KPIs e impacto circular."
    if any(k in text for k in ["estado", "riesgo", "diagnostico"]):
        return f"Diagnóstico: {sl}. Alarmas: {at}. Acción: {'Generar OT' if latest['estado'] != 'Normal' else 'Continuar monitoreo'}."
    if any(k in text for k in ["vibracion", "vibra"]):
        return f"Vibración: {latest['vibracion_rms_mm_s']:.2f} mm/s. Estado: {variable_status(latest)['Vibracion']}. Causas probables: Desgaste o desalineación."
    if any(k in text for k in ["temperatura", "temp"]):
        return f"Temperatura: {latest['temperatura_c']:.1f} C. Estado: {variable_status(latest)['Temperatura']}. Causas: Fricción o lubricación deficiente."
    if any(k in text for k in ["vacio", "presion"]):
        return f"Vacío: {latest['presion_vacio_kpa']:.1f} kPa. Estado: {variable_status(latest)['Presion de vacio']}. Causas: Fuga o deterioro de sellos."
    if any(k in text for k in ["kpi", "indicador"]):
        kpis = calculate_kpis(720, 3, 18, 18, 20, 40, 80, 85.5)
        return f"KPIs: MTBF {kpis['MTBF (h)']:.1f}h, Disponibilidad {kpis['Disponibilidad (%)']:.1f}%."
    
    return f"¿En qué puedo ayudarte? Estado actual: {sl}. Consultas sugeridas: 'diagnóstico', 'vibración', 'KPIs'."

def process_floating_query(query):
    if not query or not query.strip(): return
    st.session_state.floating_chat_history.append({"role": "user", "content": query.strip()})
    try:
        latest = st.session_state.get("latest_row", pd.Series({"estado": "Normal", "indice_riesgo": 0, "vibracion_rms_mm_s": 0, "temperatura_c": 0, "presion_vacio_kpa": 0}))
        asset_name = st.session_state.get("asset_name", "Activo")
        reply = chatbot_response(query.strip(), latest, asset_name)
        st.session_state.floating_chat_history.append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state.floating_chat_history.append({"role": "assistant", "content": f"Error: {str(e)}"})

@st.dialog("Asistente Tech Maint Pro - Letzy", width="large")
def floating_chat_dialog():
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
        {render_letzy("60px")}
        <div>
            <h3 style="margin:0; color:#1a5fa8; font-size:1.5rem;">Hola, soy Letzy</h3>
            <p style="margin:5px 0 0 0; color:#5a6b7c; font-size:0.95rem;">Tu asistente de mantenimiento inteligente</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.floating_chat_history:
        with st.chat_message("assistant", avatar=LETZY_BASE64):
            st.markdown("**¡HOLA! SOY LETZY, TU ASISTENTE DE TECH MAINT PRO.**\n\n¿En qué puedo ayudarte hoy? Puedo asistirte con diagnóstico, órdenes de trabajo, KPIs, modos de falla e impacto circular.")
    
    for msg in st.session_state.floating_chat_history[-10:]:
        avatar = LETZY_BASE64 if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            
    st.markdown("#### Consultas rápidas:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Estado actual", key="qr1", use_container_width=True): process_floating_query("Estado actual")
        if st.button("Alta vibración", key="qr2", use_container_width=True): process_floating_query("¿Qué causa alta vibración?")
    with c2:
        if st.button("Caída de vacío", key="qr3", use_container_width=True): process_floating_query("¿Qué revisar si cae el vacío?")
        if st.button("KPIs", key="qr4", use_container_width=True): process_floating_query("¿Cuáles son los KPIs?")
    with c3:
        if st.button("Modos de falla", key="qr5", use_container_width=True): process_floating_query("Modos de falla AMEF")
        if st.button("Limpiar chat", key="qr6", use_container_width=True): 
            st.session_state.floating_chat_history = []
            
    st.divider()
    ui = st.chat_input("Escribe tu consulta a Letzy...", key="fci")
    if ui:
        process_floating_query(ui)
        
    if st.button("Cerrar chat", key="fcc", use_container_width=True):
        st.session_state.floating_chat_open = False
        st.session_state.auto_chat_triggered = False

# Botón flotante robusto
st.markdown("""
<style>
.floating-btn-container { position: fixed; bottom: 30px; right: 30px; z-index: 9999; }
.floating-btn-container button {
    width: 90px !important; height: 90px !important; border-radius: 50% !important;
    background: linear-gradient(135deg, #1a5fa8, #8bc34a) !important;
    border: 3px solid #f5a623 !important; padding: 0 !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important; transition: transform 0.2s !important;
}
.floating-btn-container button:hover { transform: scale(1.1) !important; }
</style>
<div class="floating-btn-container">
    <button onclick="document.getElementById('hidden_chat_btn').click()">
        <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:50%;">
            <img src="""" + LETZY_BASE64 + """" style="width:84px;height:84px;object-fit:cover;">
        </div>
    </button>
</div>
""", unsafe_allow_html=True)

if st.button("Abrir asistente", key="hidden_chat_btn", help="Abrir asistente Letzy"):
    st.session_state.floating_chat_open = True

if st.session_state.get("floating_chat_open", False):
    floating_chat_dialog()

# ============================================================================
# INICIALIZACIÓN Y SIMULACIÓN
# ============================================================================
@st.cache_resource
def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (
        ot_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, description TEXT, 
        priority TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendiente', created_by TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT NOT NULL, component TEXT NOT NULL, 
        decision TEXT NOT NULL, mass_conserved_kg REAL DEFAULT 0, mass_discarded_kg REAL DEFAULT 0)""")
    conn.commit()
    conn.close()

init_database()

# Inicializar estado
for k, v in {
    "running": True, "sim_idx": 1, "last_order_event": None,
    "floating_chat_open": False, "floating_chat_history": [],
    "auto_chat_triggered": False, "previous_estado": None,
    "scenario": "Operacion normal", "seed": 42, "n_hours": 168, "step_speed": 3
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

apply_custom_styles()

# Header
st.markdown(f"""
<div style="display:flex; align-items:center; gap:20px; margin-bottom:10px; padding:10px 0;">
    {render_logo("180px")}
    <div style="flex:1;">
        <p style="margin:0; color:{COLORS['amarillo']}; font-size:1.5rem; font-weight:700;">Mantenimiento Inteligente + Economía Circular</p>
    </div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["Monitoreo", "Diagnóstico", "Órdenes de Trabajo", "Impacto Circular", "KPIs"])
asset_name = st.selectbox("Selector de activo", ["Bomba de vacio BV-01", "Motor CAT 3408 MD-01", "Compresor Leroi CA-01"], label_visibility="collapsed")
st.caption(f"Tag: BV-ABS-001 | Criticidad: Alta")

# Lógica de simulación
DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
max_idx = len(DF_FULL)
st.session_state.sim_idx = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    if HAS_AUTOREFRESH: st_autorefresh(interval=1000, key="tm_live")
    st.session_state.sim_idx = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)
elif st.session_state.sim_idx >= max_idx:
    st.session_state.sim_idx = 1

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state.latest_row = latest
st.session_state.asset_name = asset_name

# Detección de alertas
current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state.auto_chat_triggered = True
    alert_msg = f"¡Hola! Soy Letzy. Se ha detectado un estado **{current_estado}** en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. Se requiere atención inmediata."
    st.session_state.floating_chat_history.append({"role": "assistant", "content": alert_msg})
st.session_state.previous_estado = current_estado

# ============================================================================
# TAB 1: MONITOREO (4 Indicadores + Gráficas debajo)
# ============================================================================
with tabs[0]:
    statuses = variable_status(latest)
    
    def get_status_color(status):
        return COLORS["verde"] if status == "Normal" else COLORS["amarillo"] if status == "Alerta" else COLORS["rojo"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Columna 1: Vibración
    with col1:
        sc = get_status_color(statuses["Vibracion"])
        st.markdown(f"""<div class="metric-card status-{statuses['Vibracion'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:#ffffff;margin-bottom:8px;">VIBRACIÓN RMS</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:#ffffff;">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div style="font-size:1.1rem;color:#ffffff;font-weight:bold;">{statuses['Vibracion'].upper()}</div>
        </div>""", unsafe_allow_html=True)
        # Gráfica simplificada para evitar errores de layout
        fig_vib = go.Figure()
        fig_vib.add_trace(go.Scatter(x=DF["fecha_hora"], y=DF["vibracion_rms_mm_s"], mode="lines", line=dict(color=COLORS["azul"], width=2)))
        fig_vib.update_layout(height=200, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_vib, use_container_width=True, key="chart_vib")

    # Columna 2: Temperatura
    with col2:
        sc = get_status_color(statuses["Temperatura"])
        st.markdown(f"""<div class="metric-card status-{statuses['Temperatura'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:#ffffff;margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:#ffffff;">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">°C</span></div>
            <div style="font-size:1.1rem;color:#ffffff;font-weight:bold;">{statuses['Temperatura'].upper()}</div>
        </div>""", unsafe_allow_html=True)
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=DF["fecha_hora"], y=DF["temperatura_c"], mode="lines", line=dict(color=COLORS["amarillo"], width=2)))
        fig_temp.update_layout(height=200, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_temp, use_container_width=True, key="chart_temp")

    # Columna 3: Vacío
    with col3:
        sc = get_status_color(statuses["Presion de vacio"])
        st.markdown(f"""<div class="metric-card status-{statuses['Presion de vacio'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:#ffffff;margin-bottom:8px;">PRESIÓN DE VACÍO</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:#ffffff;">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div style="font-size:1.1rem;color:#ffffff;font-weight:bold;">{statuses['Presion de vacio'].upper()}</div>
        </div>""", unsafe_allow_html=True)
        fig_vac = go.Figure()
        fig_vac.add_trace(go.Scatter(x=DF["fecha_hora"], y=DF["presion_vacio_kpa"], mode="lines", line=dict(color=COLORS["verde"], width=2)))
        fig_vac.update_layout(height=200, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_vac, use_container_width=True, key="chart_vac")

    # Columna 4: Estado Global
    with col4:
        ec = get_status_color(latest["estado"])
        st.markdown(f"""<div class="metric-card status-{latest['estado'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:#ffffff;margin-bottom:8px;">ESTADO GLOBAL</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:#ffffff;">{latest['estado'].upper()}</div>
            <div style="font-size:1.1rem;color:#ffffff;">IR: {latest['indice_riesgo']:.1f}/100</div>
        </div>""", unsafe_allow_html=True)
        fig_ir = go.Figure()
        fig_ir.add_trace(go.Scatter(x=DF["fecha_hora"], y=DF["indice_riesgo"], mode="lines", line=dict(color=COLORS["rojo"], width=2)))
        fig_ir.update_layout(height=200, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False, showticklabels=False), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_ir, use_container_width=True, key="chart_ir")

    # Alarmas
    alarms = get_alarms(latest)
    if alarms:
        st.markdown(f"<h3 style='margin-top:20px;color:{COLORS['texto_oscuro']};'>Alarmas Activas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            ac = "alarm-critical" if level == "Critico" else ""
            icon = "🚨" if level == "Critico" else "⚠️"
            color = COLORS["rojo"] if level == "Critico" else COLORS["amarillo"]
            st.markdown(f"""<div class="alarm-banner {ac}">
                <div style="font-weight:bold;font-size:1.1rem;color:{color};">{icon} {level}: {name}</div>
                <div style="margin-top:5px;">{name} fuera de rango: <strong>{value}</strong></div>
            </div>""", unsafe_allow_html=True)

# ============================================================================
# TABS 2-5 (Simplificados para robustez)
# ============================================================================
with tabs[1]:
    st.markdown("<h2>Diagnóstico en Tiempo Real</h2>", unsafe_allow_html=True)
    ec = get_status_color(latest["estado"])
    st.markdown(f"""<div style="background:{COLORS['blanco']};padding:20px;border-radius:16px;border-left:6px solid {ec};margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);">
        <div style="font-size:1.5rem;font-weight:bold;color:{ec};">Estado Actual: {latest['estado'].upper()}</div>
        <div style="font-size:1.2rem;margin-top:10px;">Índice de Riesgo: {latest['indice_riesgo']:.1f}/100</div>
    </div>""", unsafe_allow_html=True)
    if alarms:
        st.markdown("<h3>Hipótesis Técnicas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            st.markdown(f"- **{name}**: Posible falla mecánica o de lubricación. Acción: {'Generar OT' if level == 'Critico' else 'Inspeccionar'}.")

with tabs[2]:
    st.markdown("<h2>Gestión de Órdenes de Trabajo</h2>", unsafe_allow_html=True)
    if st.button("Generar Orden de Trabajo Automática", type="primary"):
        st.success(f"OT generada para {asset_name} por estado {latest['estado']}")

with tabs[3]:
    st.markdown("<h2>Panel de Impacto Circular</h2>", unsafe_allow_html=True)
    st.info("Registra aquí las decisiones de mantenimiento para conservar componentes y minimizar residuos.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Intervenciones", 0)
    c2.metric("Reparados/Reutilizados", 0)
    c3.metric("Masa Conservada (kg)", "0.00")
    c4.metric("Masa Descartada (kg)", "0.00")

with tabs[4]:
    st.markdown("<h2 style='text-align:center;'>KPIs e Indicadores</h2>", unsafe_allow_html=True)
    kpis = calculate_kpis(720, 3, 18, 18, 20, 40, 80, 85.5)
    kk1, kk2, kk3, kk4 = st.columns(4)
    kk1.metric("MTBF", f"{kpis['MTBF (h)']:.1f} h")
    kk2.metric("MTTR", f"{kpis['MTTR (h)']:.1f} h")
    kk3.metric("Disponibilidad", f"{kpis['Disponibilidad (%)']:.1f}%")
    kk4.metric("Pérdida productiva", f"{kpis['Perdida productiva (t)']:.1f} t")
    
    col_center1, col_center2, col_center3 = st.columns([1, 3, 1])
    with col_center2:
        st.dataframe(pd.DataFrame({"KPI": list(kpis.keys()), "Valor": list(kpis.values())}), use_container_width=True, hide_index=True)

# Footer
st.divider()
st.caption("Tech Maint Pro | Prototipo profesional SeedTech 2026 | Los umbrales son referenciales")
