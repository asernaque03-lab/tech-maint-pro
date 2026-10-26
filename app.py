import base64
import io
import json
import math
import os
import re
import sqlite3
import time
import logging
import unicodedata
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image as PILImage

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
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    Groq = None

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ============================================================================
# CONFIGURACION GENERAL
# ============================================================================

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "techmaintpro.db")
LOG_PATH = os.path.join(APP_DIR, "techmaintpro.log")
PDF_DIR = APP_DIR
CSV_TEST_PATH = os.path.join(APP_DIR, "bomba_vacrio_prueba.csv")
PLAN_MTO_PATH = os.path.join(APP_DIR, "plan_de_mto.csv")
CSV_PROD_PATH = os.path.join(APP_DIR, "registro_mantenimiento_produccion.csv")
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

GROQ_API_KEY = "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"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger("TechMaintPro")

# ============================================================================
# COLORES OFICIALES
# ============================================================================

COLORS = {
    "azul": "#1a5fa8",
    "verde": "#8bc34a",
    "amarillo": "#f5a623",
    "rojo": "#d32f2f",
    "blanco": "#ffffff",
    "gris_claro": "#f5f7fa",
    "gris_medio": "#e8ecf1",
    "texto_oscuro": "#1a2b4c",
    "texto_gris": "#5a6b7c",
}

# ============================================================================
# CARGA DE IMAGENES PNG LOCALES
# ============================================================================

def load_image_as_base64(image_path, fallback_svg=""):
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode('utf-8')
            mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
    except Exception as e:
        logger.warning(f"No se pudo cargar {image_path}: {e}")
    return fallback_svg

LOGO_PATH = os.path.join(APP_DIR, "logo.png")
LETZY_PATH = os.path.join(APP_DIR, "letzy.png")

LOGO_FALLBACK = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxODAiIGhlaWdodD0iMTgwIj48cmVjdCB3aWR0aD0iMTgwIiBoZWlnaHQ9IjE4MCIgZmlsbD0iIzFhNWZhOCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSIgZm9udC1zaXplPSIyMCIgZm9udC13ZWlnaHQ9ImJvbGQiPlRFQ0ggTUFJTlQ8L3RleHQ+PHRleHQgeD0iNTAlIiB5PSI3MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiNmNWE2MjMiIGZvbnQtc2l6ZT0iMjAiIGZvbnQtd2VpZ2h0PSJib2xkIj5QUk88L3RleHQ+PC9zdmc+"
LETZY_FALLBACK = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI5MCIgaGVpZ2h0PSI5MCI+PGNpcmNsZSBjeD0iNDUiIGN5PSI0NSIgcj0iNDIiIGZpbGw9IiMxYTVmYTgiLz48dGV4dCB4PSI1MCUiIHk9IjU1JSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0id2hpdGUiIGZvbnQtc2l6ZT0iMjAiIGZvbnQtd2VpZ2h0PSJib2xkIj5MPC90ZXh0Pjwvc3ZnPg=="

LOGO_BASE64 = load_image_as_base64(LOGO_PATH, LOGO_FALLBACK)
LETZY_BASE64 = load_image_as_base64(LETZY_PATH, LETZY_FALLBACK)

def render_logo(size="180px"):
    return f'<img src="{LOGO_BASE64}" style="width:{size}; height:auto; display:inline-block;" />'

def render_letzy(size="60px"):
    return f'<img src="{LETZY_BASE64}" style="width:{size}; height:{size}; border-radius:50%; display:inline-block; object-fit:cover;" />'

# ============================================================================
# CONFIGURACION PAGINA
# ============================================================================

st.set_page_config(
    page_title="Tech Maint Pro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# ACTIVOS INDUSTRIALES
# ============================================================================

ASSETS = {
    "Bomba de vacio BV-01": {"tag": "BV-ABS-001", "criticality": "Alta"},
    "Motor CAT 3408 MD-01": {"tag": "MD-3408-001", "criticality": "Alta"},
    "Compresor Leroi CA-01": {"tag": "CA-LER-001", "criticality": "Media-Alta"},
    "Moldeadora Rotativa": {"tag": "MOL-01", "criticality": "Alta"},
    "Tunel de Enfriamiento": {"tag": "TUN-02", "criticality": "Media"},
    "Envasadora Automatica": {"tag": "ENV-03", "criticality": "Alta"},
    "Tanque de Fusion": {"tag": "MEL-04", "criticality": "Media"}
}

THRESHOLDS = {
    "vibration_normal": 4.5, "vibration_alert": 7.1,
    "temperature_normal": 75.0, "temperature_alert": 85.0,
    "vacuum_normal": -3.0, "vacuum_alert": -5.0,
}

# ============================================================================
# METADATOS DE DOCUMENTOS
# ============================================================================

DOCUMENT_METADATA = {
    "01": {"category": "Tesis / Codificacion", "tags": ["codificacion", "MTBF", "MTTR"], "desc": "Sistema de codificacion de equipos"},
    "02": {"category": "Tesis / Vacio medico", "tags": ["NFPA 99", "vacio", "hospital"], "desc": "Programa de mantenimiento vacio medico"},
    "03": {"category": "Gestion / KPIs", "tags": ["KPI", "MTBF", "MTTR"], "desc": "Indicadores clave de rendimiento"},
    "04": {"category": "Tesis / AMFE", "tags": ["AMFE", "FMEA", "criticidad"], "desc": "Analisis de Modos de Falla"},
    "05": {"category": "Manual / IMBIL", "tags": ["anillo liquido", "bombas"], "desc": "Manual bombas de vacio IMBIL"},
    "06": {"category": "Manual / Caterpillar", "tags": ["G3408", "G3412", "motores"], "desc": "Manual motores Caterpillar"},
    "07": {"category": "Ficha / CPS", "tags": ["VP6D", "VP12D", "vacio"], "desc": "Especificaciones bombas CPS"},
    "08": {"category": "Manual / Gadnic", "tags": ["Serie TW", "paletas"], "desc": "Manual bombas Gadnic"},
    "09": {"category": "POE / Laboratorio", "tags": ["Thomas BV-1", "seguridad"], "desc": "Procedimiento bomba de vacio"},
    "10": {"category": "Tesis / Ladrillera", "tags": ["COVENIN", "criticidad", "preventivo"], "desc": "Plan de mantenimiento preventivo"}
}

SYSTEM_PROMPT = """Eres Letzy, Asistente Experto en Ingenieria de Mantenimiento Industrial. 
REGLAS:
1. Se preciso y conciso.
2. CITA SIEMPRE la fuente entre parentesis. Ej: [Fuente: Archivo 10]
3. Si te preguntan por PROCEDIMIENTOS, busca en el Archivo 10.
4. Si te preguntan por KPIs, usa el Archivo 03.
5. NUNCA inventes datos tecnicos.
"""

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
        "telegram_chat_id": "1330744031",
        "rol": "Tecnico de Mantenimiento"
    },
    "asesor": {
        "nombre": "JORDY ALBERTO SERNAQUE SABA",
        "telefono": "902631386",
        "email": "ajordyss0602@gmail.com",
        "telegram_chat_id": "8665066190",
        "rol": "Jefe de Mantenimiento"
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
# NOTIFICACIONES INTELIGENTES POR CANAL (ESTRICTO)
# ============================================================================

def send_telegram(chat_id, message):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        r = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": str(chat_id), "text": message, "parse_mode": "HTML"}, timeout=10)
        if r.status_code == 200:
            logger.info(f"Telegram enviado a {chat_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False

def send_email(to_email, subject, body_html):
    if not to_email: return False
    try:
        msg = MIMEText(body_html, 'html')
        msg['Subject'] = subject
        msg['From'] = STAFF["asesor"]["email"]
        msg['To'] = to_email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(STAFF["asesor"]["email"], "910314782")
        server.send_message(msg)
        server.quit()
        logger.info(f"Email enviado a {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error email: {e}")
        return False

def play_notification_sound():
    st.markdown("""
    <script>
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(600, audioCtx.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.15);
    } catch(e) {}
    </script>
    """, unsafe_allow_html=True)

def play_critical_alarm(event_id):
    if st.session_state.get("last_beep_event") == event_id: return
    st.session_state["last_beep_event"] = event_id
    st.markdown("""
    <script>
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode); gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 1200; oscillator.type = 'square'; gainNode.gain.value = 0.3;
                oscillator.start(); setTimeout(() => oscillator.stop(), 400);
            }, i * 550);
        }
    } catch(e) {}
    </script>
    """, unsafe_allow_html=True)

def test_telegram_connection():
    try:
        r = requests.get(f"{TELEGRAM_API_URL}/getMe", timeout=5)
        if r.status_code != 200: return False
    except: return False
    
    success_count = 0
    for key, staff in STAFF.items():
        chat_id = staff.get("telegram_chat_id")
        if chat_id:
            msg = f"<b>[PRUEBA] Tech Maint Pro</b>\n\nSistema de notificaciones funcionando.\nDestinatario: {staff['nombre']}\nRol: {staff['rol']}"
            if send_telegram(chat_id, msg):
                success_count += 1
    return success_count == 3

def notify_new_ot(ot_data):
    ot_id = ot_data["ot_id"]
    asset = ot_data["asset_name"]
    responsable = ot_data.get("responsable", "Sin asignar")
    desc = ot_data.get("description", "Sin descripcion")[:80]
    
    # 1. Tecnico: Nueva tarea asignada
    msg_tec = f"<b>[NUEVA TAREA ASIGNADA]</b>\nID: {ot_id}\nActivo: {asset}\nFalla: {desc}\nPor favor, revisar y confirmar."
    send_telegram(STAFF["tecnico"]["telegram_chat_id"], msg_tec)
    
    # 2. Jefe: Aviso de nueva OT
    msg_jefe = f"<b>[NUEVA OT CREADA]</b>\nID: {ot_id}\nActivo: {asset}\nResponsable: {responsable}"
    send_telegram(STAFF["asesor"]["telegram_chat_id"], msg_jefe)
    
    play_notification_sound()

def notify_ot_started(ot_id, asset_name, responsable):
    # Jefe: Cuando se empieza un mantenimiento
    msg = f"<b>[OT INICIADA]</b>\nID: {ot_id}\nTecnico: {responsable} comenzo el trabajo en {asset_name}\nHora: {datetime.now().strftime('%H:%M')}"
    send_telegram(STAFF["asesor"]["telegram_chat_id"], msg)
    play_notification_sound()

def notify_ot_paused(ot_id, asset_name, responsable, motivo):
    # Jefe: Observaciones / falta material
    msg_jefe = f"<b>[OT PAUSADA / OBSERVACION]</b>\nID: {ot_id}\nActivo: {asset_name}\nTecnico: {responsable}\nMotivo: {motivo}"
    send_telegram(STAFF["asesor"]["telegram_chat_id"], msg_jefe)
    
    # Gerencia (Irina): Actualizaciones de observaciones o faltas en stock
    msg_gerencia = f"<b>[OBSERVACION EN OT]</b>\nID: {ot_id}\nActivo: {asset_name}\nProblema: {motivo}\nPosible impacto en tiempos y costos."
    send_telegram(STAFF["gerencia"]["telegram_chat_id"], msg_gerencia)
    send_email(STAFF["gerencia"]["email"], f"[OBSERVACION] {ot_id} - {asset_name}", f"<h2>Observacion en OT {ot_id}</h2><p>Activo: {asset_name}</p><p>Problema: {motivo}</p>")
    
    play_notification_sound()

def notify_ot_completed(ot_data):
    ot_id = ot_data["ot_id"]
    responsable = ot_data.get("responsable", "N/A")
    tiempo = ot_data.get("tiempo_real_horas", 0)
    hallazgos = ot_data.get("hallazgos", "Sin detalles")[:100]
    
    # Jefe: Cuando se completa una OT
    msg = f"<b>[OT COMPLETADA]</b>\nID: {ot_id}\nTecnico: {responsable}\nTiempo: {tiempo}h\nResultado: {hallazgos}"
    send_telegram(STAFF["asesor"]["telegram_chat_id"], msg)
    play_notification_sound()

def notify_high_circular_impact(intervention):
    md = intervention.get("mass_discarded_kg", 0) or 0
    mc = intervention.get("mass_conserved_kg", 0) or 0
    ot_id = intervention.get("ot_id", "N/A")
    component = intervention.get("component", "N/A")
    decision = intervention.get("decision", "N/A")
    
    # Gerencia (Irina): Actualizaciones que le competen al sector economico
    msg_gerencia = f"<b>[IMPACTO CIRCULAR / ECONOMICO]</b>\nOT: {ot_id}\nComponente: {component}\nDecision: {decision}\nMasa Conservada: {mc:.2f} kg\nMasa Descartada: {md:.2f} kg\nRegistro de impacto economico y de stock."
    send_telegram(STAFF["gerencia"]["telegram_chat_id"], msg_gerencia)
    
    cuerpo_email = f"<h2>Impacto Circular Registrado</h2><p><b>OT:</b> {ot_id}</p><p><b>Componente:</b> {component}</p><p><b>Masa Conservada:</b> {mc:.2f} kg</p><p><b>Masa Descartada:</b> {md:.2f} kg</p>"
    send_email(STAFF["gerencia"]["email"], f"[IMPACTO ECONOMICO] {ot_id} - {component}", cuerpo_email)
    
    play_notification_sound()

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

def apply_custom_styles():
    css = f"""
    <style>
    .stApp {{ background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%) !important; padding-top: 0 !important; }}
    section[data-testid="stSidebar"] {{
        background-color: #ffffff !important; border-right: 1px solid #e8ecf1 !important;
        z-index: 9998 !important; padding-top: 1rem !important; box-shadow: 4px 0 15px rgba(0,0,0,0.05) !important;
    }}
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
    .stTabs [data-baseweb="tab"] {{
        background: rgba(26,95,168,0.1) !important; color: {COLORS['texto_oscuro']} !important;
        border-radius: 8px 8px 0 0; padding: 8px 16px; font-size: 0.9rem;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{ background: {COLORS['azul']} !important; color: white !important; }}
    .doc-button {{
        display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px;
        background: linear-gradient(135deg, #1a5fa8, #8bc34a); color: white; text-decoration: none;
        border-radius: 8px; font-weight: 600; font-size: 0.95rem; transition: all 0.3s ease;
    }}
    .doc-button:hover {{ transform: translateY(-2px); color: white; }}
    section[data-testid="stSidebar"] .stChatMessage {{
        background-color: #f5f7fa !important; border: 1px solid #e8ecf1 !important;
        border-radius: 12px !important; padding: 8px !important; margin: 4px 0 !important;
    }}
    .search-box {{ border: 2px solid {COLORS['azul']}; border-radius: 8px; padding: 10px; margin-bottom: 15px; }}
    .calendar-month {{
        background: {COLORS['azul']}; color: white; padding: 15px; border-radius: 8px; margin: 5px;
        display: flex; justify-content: space-between; align-items: center;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE DATOS Y RIESGO
# ============================================================================

def load_test_data_from_csv():
    try:
        if os.path.exists(CSV_TEST_PATH):
            df = pd.read_csv(CSV_TEST_PATH)
            column_mapping = {
                'Timestamp': 'fecha_hora', 'Vacuum_Pressure_mbar': 'vacuum_mbar',
                'Oil_Temperature_C': 'temperatura_c', 'Vibration_mm_s': 'vibracion_rms_mm_s',
                'Status': 'status', 'Fault_Description': 'fault_description'
            }
            df = df.rename(columns=column_mapping)
            if 'vacuum_mbar' in df.columns:
                df['presion_vacio_kpa'] = -(df['vacuum_mbar'] * 0.1)
            if 'fecha_hora' in df.columns:
                df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
            
            df["riesgo_vibracion"] = df["vibracion_rms_mm_s"].apply(lambda v: float(np.clip((v - 3) / (8.5 - 3) * 100, 0, 100)))
            df["riesgo_temperatura"] = df["temperatura_c"].apply(lambda t: float(np.clip((t - 68) / (92 - 68) * 100, 0, 100)))
            df["riesgo_vacio"] = df["presion_vacio_kpa"].apply(lambda p: float(np.clip((p - (-72)) / ((-45) - (-72)) * 100, 0, 100)))
            
            weights = 0.45 * df["riesgo_vibracion"] + 0.30 * df["riesgo_temperatura"] + 0.25 * df["riesgo_vacio"]
            df["indice_riesgo"] = weights.round(1)
            
            def classify(ir, row):
                s = [
                    "Critico" if row["vibracion_rms_mm_s"] >= THRESHOLDS["vibration_alert"] else "Alerta" if row["vibracion_rms_mm_s"] >= THRESHOLDS["vibration_normal"] else "Normal",
                    "Critico" if row["temperatura_c"] >= THRESHOLDS["temperature_alert"] else "Alerta" if row["temperatura_c"] >= THRESHOLDS["temperature_normal"] else "Normal",
                    "Critico" if row["presion_vacio_kpa"] >= THRESHOLDS["vacuum_alert"] else "Alerta" if row["presion_vacio_kpa"] >= THRESHOLDS["vacuum_normal"] else "Normal"
                ]
                if "Critico" in s: return "Critico"
                if "Alerta" in s and ir >= 35: return "Alerta"
                if ir < 40: return "Normal"
                if ir < 70: return "Alerta"
                return "Critico"
            
            df["estado"] = [classify(ir, df.iloc[i]) for i, ir in enumerate(df["indice_riesgo"])]
            if 'fault_description' in df.columns:
                df['fault_description'] = df['fault_description'].fillna('Normal')
            
            logger.info(f"CSV de prueba cargado: {len(df)} registros")
            return df
    except Exception as e:
        logger.error(f"Error cargando CSV: {e}")
    return None

def get_alarms(row):
    alarms = []
    if 'status' in row and pd.notna(row['status']) and str(row['status']).strip() != 'OK':
        level = 'Critico' if str(row['status']).upper() in ['CRITICAL', 'TRIP'] else 'Alerta'
        desc = str(row.get('fault_description', 'Falla detectada')).strip()
        if not desc or desc.lower() == 'nan': desc = 'Falla detectada'
        alarms.append((level, "General", desc))
    else:
        if row["vibracion_rms_mm_s"] >= THRESHOLDS["vibration_normal"]:
            alarms.append(("Alerta" if row["vibracion_rms_mm_s"] < THRESHOLDS["vibration_alert"] else "Critico", "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s"))
        if row["temperatura_c"] >= THRESHOLDS["temperature_normal"]:
            alarms.append(("Alerta" if row["temperatura_c"] < THRESHOLDS["temperature_alert"] else "Critico", "Temperatura", f"{row['temperatura_c']:.1f} C"))
        if row["presion_vacio_kpa"] >= THRESHOLDS["vacuum_normal"]:
            alarms.append(("Alerta" if row["presion_vacio_kpa"] < THRESHOLDS["vacuum_alert"] else "Critico", "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa"))
    return alarms

def create_work_order_obj(row, asset_name, source="Automatica"):
    alarms = get_alarms(row)
    priority = "P0" if row["estado"] == "Critico" else "P1" if row["estado"] == "Alerta" else "P2"
    responsable = STAFF["tecnico"]["nombre"] if priority in ["P0", "P1"] else STAFF["asesor"]["nombre"]
    symptoms = "; ".join([f"{name}: {value} ({level})" for level, name, value in alarms]) or "Sin alarma critica"
    
    ts = pd.to_datetime(row["fecha_hora"]).strftime("%Y%m%d%H%M")
    return {
        "ot_id": f"OT-{ts}-{priority}", "asset_name": asset_name, "alert_id": f"ALM-{ts}",
        "description": f"Anomalia: {symptoms}", "priority": priority, "responsible": responsable,
        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "Pendiente", "created_by": source
    }

# ============================================================================
# GENERACION DE PDF - FORMATO SANIPES
# ============================================================================

def generate_maintenance_pdf(ot_data, photos_before=None, photos_after=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor(COLORS['azul']), spaceAfter=30)
    elements.append(Paragraph("REPORTE DE MANTENIMIENTO - FORMATO SANIPES", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    data = [
        ['OT ID:', ot_data.get('ot_id', 'N/A')], ['Activo:', ot_data.get('asset_name', 'N/A')],
        ['Fecha Creacion:', ot_data.get('creation_date', 'N/A')], ['Responsable:', ot_data.get('responsable', 'N/A')],
        ['Prioridad:', ot_data.get('priority', 'N/A')], ['Estado:', ot_data.get('status', 'N/A')],
    ]
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['azul'])), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    elements.append(Paragraph("<b>Descripcion del Problema:</b>", styles['Heading2']))
    elements.append(Paragraph(ot_data.get('description', 'N/A'), styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    if ot_data.get('hallazgos'):
        elements.append(Paragraph("<b>Hallazgos:</b>", styles['Heading2']))
        elements.append(Paragraph(ot_data.get('hallazgos', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================================================
# INTEGRACION CON GROQ + RAG
# ============================================================================

def query_groq_with_rag(user_query, latest, asset_name, kpi_values):
    try:
        client = Groq(api_key=GROQ_API_KEY)
        current_context = f"Activo: {asset_name}\nEstado: {latest['estado']}\nIR: {latest['indice_riesgo']:.1f}/100"
        messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{current_context}"}, {"role": "user", "content": user_query}]
        response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.3, max_tokens=800)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error Groq: {e}")
        return f"Error al consultar la IA: {str(e)}"

def chatbot_response_fallback(user_query, latest, asset_name, kpi_values):
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100"
    
    if any(k in text for k in ["hola", "ayuda"]): return f"Bienvenido a Tech Maint Pro\n\n{sl}\n\nPuedo ayudarte con diagnostico, ordenes de trabajo, KPIs e impacto circular."
    if any(k in text for k in ["estado", "riesgo"]): return f"**Diagnostico Actual**\n\n{sl}\n\nAccion recomendada: {'Continuar monitoreo' if latest['estado'] == 'Normal' else 'Generar OT'}"
    if any(k in text for k in ["kpi", "indicador"]): return f"**KPIs**\nMTBF: {kpi_values['MTBF (h)']:.1f} h\nDisponibilidad: {kpi_values['Disponibilidad (%)']:.2f}%"
    
    return f"Entiendo tu consulta sobre '{user_query}'.\n\n**Informacion actual:** {sl}\n\nPor favor, reformula tu pregunta o selecciona una opcion del menu."

def process_floating_query(query, ai_platform="rag"):
    if not query or not query.strip(): return
    if "floating_chat_history" not in st.session_state: st.session_state["floating_chat_history"] = []
    st.session_state["floating_chat_history"].append({"role": "user", "content": query})
    
    try:
        kp = {"MTBF (h)": 240, "MTTR (h)": 2, "Disponibilidad (%)": 99.0}
        latest = st.session_state.get("latest_row", pd.Series())
        asset_name = st.session_state.get("asset_name", "")
        
        reply = query_groq_with_rag(query, latest, asset_name, kp) if ai_platform == "rag" and GROQ_API_KEY else chatbot_response_fallback(query, latest, asset_name, kp)
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": reply})
        
        if st.session_state.get("audio_enabled", False):
            play_notification_sound()
    except Exception as e:
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": f"Error: {e}"})

# ============================================================================
# BASE DE DATOS
# ============================================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (
        ot_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, tag TEXT, ubicacion TEXT, alert_id TEXT, description TEXT,
        prioridad TEXT NOT NULL DEFAULT 'P2', tipo TEXT DEFAULT 'Correctivo', responsable TEXT, creation_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pendiente', start_time TEXT, end_time TEXT, hallazgos TEXT, acciones TEXT,
        repuestos TEXT, evidencia TEXT, tiempo_real_horas REAL, created_by TEXT, updated_at TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT NOT NULL, asset_name TEXT, component TEXT NOT NULL, decision TEXT NOT NULL, result TEXT, 
        mass_conserved_kg REAL DEFAULT 0, mass_discarded_kg REAL DEFAULT 0, costo_reparacion_eur REAL DEFAULT 0, costo_reemplazo_nuevo_eur REAL DEFAULT 0, 
        co2_evitado_kg REAL DEFAULT 0, recorded_date TEXT NOT NULL, recorded_by TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS maintenance_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, asset_name TEXT NOT NULL, tag TEXT, ubicacion TEXT, maintenance_type TEXT, task_description TEXT,
        frequency TEXT, frequency_days INTEGER, estimated_hours REAL, responsable TEXT, priority TEXT, required_parts TEXT, tools_needed TEXT,
        safety_requirements TEXT, checklist_items TEXT, thresholds TEXT, notes TEXT, last_execution_date TEXT, next_scheduled_date TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS ot_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT, photo_type TEXT, photo_path TEXT, upload_date TEXT
    )""")
    
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente.")

# ============================================================================
# INICIALIZACION
# ============================================================================

init_database()

sd = {
    "running": True, "sim_idx": 1, "last_order_event": None, "floating_chat_history": [],
    "auto_chat_triggered": False, "previous_estado": None, "scenario": "Operacion normal",
    "step_speed": 1, "groq_api_key": GROQ_API_KEY, "kb_loaded": False, "use_test_data": True, "audio_enabled": False
}
for k, v in sd.items():
    if k not in st.session_state: st.session_state[k] = v

apply_custom_styles()

# ============================================================================
# SIDEBAR CON CHATBOT LETZY
# ============================================================================

with st.sidebar:
    if not st.session_state.get("audio_enabled", False):
        st.warning("Haz clic para activar los sonidos de alarma")
        if st.button("Activar Sonidos", key="enable_audio", use_container_width=True):
            st.session_state["audio_enabled"] = True
            st.markdown("""
            <script>
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode); gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 440; oscillator.type = 'sine'; gainNode.gain.value = 0.1;
                oscillator.start(); setTimeout(() => oscillator.stop(), 100);
            } catch(e) {}
            </script>
            """, unsafe_allow_html=True)
            st.rerun()
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px; padding-bottom:5px; border-bottom:1px solid #e8ecf1;">
        {render_letzy("35px")}
        <div>
            <h4 style="margin:0; color:#1a5fa8; font-size:1rem;">Letzy</h4>
            <p style="margin:0; color:#5a6b7c; font-size:0.7rem;">Asistente de Mantenimiento</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    ai_mode = st.selectbox("Modo:", options=["rag", "fallback"], format_func=lambda x: "IA (PDF)" if x == "rag" else "Rapido", index=0 if GROQ_API_KEY else 1, key="ai_mode_selector_sidebar", label_visibility="collapsed")

    chat_history = st.session_state.get("floating_chat_history", [])
    chat_container = st.container(height=250)
    with chat_container:
        if not chat_history:
            with st.chat_message("assistant", avatar=LETZY_BASE64): st.markdown("**Hola! Soy Letzy.** En que puedo ayudarte?")
        for msg in chat_history[-8:]:
            with st.chat_message("assistant", avatar=LETZY_BASE64) if msg["role"] == "assistant" else st.chat_message("user"):
                st.markdown(msg["content"])

    st.markdown("**Consultas rapidas:**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Estado actual", key="sq1", use_container_width=True): process_floating_query("Estado actual", ai_mode)
        if st.button("Generar OT", key="sq2", use_container_width=True): process_floating_query("Generar orden de trabajo", ai_mode)
    with c2:
        if st.button("Alta vibracion", key="sq3", use_container_width=True): process_floating_query("Que causa alta vibracion?", ai_mode)
        if st.button("KPIs", key="sq4", use_container_width=True): process_floating_query("Cuales son los KPIs?", ai_mode)
            
    ui = st.chat_input("Escribe a Letzy...", key="chat_input_sidebar")
    if ui: process_floating_query(ui, ai_mode)
    if st.button("Limpiar chat", key="clear_chat_side", use_container_width=True): st.session_state["floating_chat_history"] = []
    
    st.divider()
    st.markdown("### Panel de Pruebas Telegram")
    
    if st.button("Probar Conexion Telegram", use_container_width=True, type="secondary"):
        with st.spinner("Enviando mensajes de prueba a todos los usuarios..."):
            success = test_telegram_connection()
            if success:
                st.success("Mensajes de prueba enviados a los 3 usuarios. Revisa tu Telegram.")
                play_notification_sound()
            else:
                st.error("Error en la conexion. Revisa los logs de la app.")
    
    if st.button("Enviar Notificacion de Prueba a TODOS", use_container_width=True, type="secondary"):
        msg = "<b>[PRUEBA GENERAL]</b> Este es un mensaje de prueba del sistema Tech Maint Pro enviado a todos los roles."
        count = 0
        for key, staff in STAFF.items():
            chat_id = staff.get("telegram_chat_id")
            if chat_id:
                if send_telegram(chat_id, msg): count += 1
        if count == 3:
            st.success(f"Notificaciones de prueba enviadas exitosamente a los {count} usuarios.")
            play_notification_sound()
        else:
            st.warning(f"Solo se pudo enviar a {count} usuarios. Revisa los logs.")

# ============================================================================
# HEADER
# ============================================================================

st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:10px; padding:10px 0;">
    <div style="display:flex; align-items:center; gap:20px;">
        {render_logo("180px")}
        <div><p style="margin:0; color:{COLORS['amarillo']}; font-size:1.5rem; font-weight:700;">Mantenimiento Inteligente + Economia Circular</p></div>
    </div>
    <div>
        <a href="https://drive.google.com/drive/folders/1alITCWZz7CxRgumUUw_kwtmaW5oNPGNI?usp=drive_link" target="_blank" class="doc-button">Documentos</a>
    </div>
</div>
""", unsafe_allow_html=True)

col_mode1, col_mode2 = st.columns([3, 1])
with col_mode1: st.caption("Seleccione el modo de datos para la demostracion")
with col_mode2:
    use_test_data = st.checkbox("Usar datos de prueba CSV", value=st.session_state.get("use_test_data", True), key="use_test_data_checkbox")
    st.session_state["use_test_data"] = use_test_data

tabs = st.tabs(["Monitoreo", "Diagnostico", "Ordenes de Trabajo", "Plan de Mantenimiento", "KPIs y Reportes", "Inventario y Stock"])
asset_name = st.selectbox("Selector de activo", list(ASSETS.keys()), label_visibility="collapsed")
st.caption(f"Tag: {ASSETS[asset_name]['tag']} | Criticidad: {ASSETS[asset_name]['criticality']}")

# ============================================================================
# SIMULACION
# ============================================================================

if st.session_state.get("use_test_data", True):
    DF_FULL = load_test_data_from_csv()
    if DF_FULL is None:
        st.warning("No se encontro el archivo CSV de prueba. Usando datos sinteticos.")
        # Fallback sintético mínimo para que no rompa
        DF_FULL = pd.DataFrame({"fecha_hora": [datetime.now()], "vibracion_rms_mm_s": [2.5], "temperatura_c": [65.0], "presion_vacio_kpa": [-4.0], "indice_riesgo": [15.0], "estado": ["Normal"], "status": ["OK"], "fault_description": ["Normal"]})
        st.session_state["step_speed"] = 3
    else:
        st.session_state["step_speed"] = 1
else:
    DF_FULL = pd.DataFrame({"fecha_hora": [datetime.now()], "vibracion_rms_mm_s": [2.5], "temperatura_c": [65.0], "presion_vacio_kpa": [-4.0], "indice_riesgo": [15.0], "estado": ["Normal"], "status": ["OK"], "fault_description": ["Normal"]})
    st.session_state["step_speed"] = 3

max_idx = len(DF_FULL)
st.session_state["sim_idx"] = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=10000 if st.session_state.get("use_test_data", True) else 1000, key="tm_live")
    st.session_state["sim_idx"] = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state["latest_row"] = latest
st.session_state["asset_name"] = asset_name

current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state["auto_chat_triggered"] = True
    if current_estado == "Critico": play_critical_alarm(f"{latest['fecha_hora']}-critical")
    
    fault_desc = latest.get('fault_description', '')
    if pd.isna(fault_desc): fault_desc = ''
    alert_msg = f"Hola! Soy Letzy. Se ha detectado un estado {current_estado} en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. {fault_desc}. Se requiere atencion inmediata."
    if "floating_chat_history" not in st.session_state: st.session_state["floating_chat_history"] = []
    st.session_state["floating_chat_history"].append({"role": "assistant", "content": alert_msg})

st.session_state["previous_estado"] = current_estado

if latest["estado"] in ["Alerta", "Critico"]:
    ek = f"{latest['fecha_hora']}-{latest['estado']}"
    if st.session_state.last_order_event != ek:
        new_ot = create_work_order_obj(latest, asset_name, source="Automatica por alarma")
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot["ot_id"],))
            if not c.fetchone():
                c.execute("""INSERT INTO work_orders (ot_id, asset_name, tag, ubicacion, alert_id, description, prioridad, tipo, responsable, creation_date, status, created_by, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_ot["ot_id"], new_ot["asset_name"], ASSETS.get(new_ot["asset_name"], {}).get("tag", "N/A"), "Planta Principal", new_ot["alert_id"], new_ot["description"], new_ot["priority"], "Correctivo", new_ot["responsible"], new_ot["creation_date"], new_ot["status"], new_ot["created_by"], datetime.now().isoformat()))
                conn.commit()
                notify_new_ot(new_ot)
                logger.info(f"OT creada y notificada: {new_ot['ot_id']}")
            conn.close()
        except Exception as e:
            logger.error(f"Error creando OT automatica: {e}")
        st.session_state["last_order_event"] = ek

# ============================================================================
# TAB 1: MONITOREO
# ============================================================================

with tabs[0]:
    def get_status_color(status): return COLORS["verde"] if status == "Normal" else COLORS["amarillo"] if status == "Alerta" else COLORS["rojo"]
    def get_text_color(status): return "#ffffff"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card status-{get_status_color(latest['estado']).replace('#', '').lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(latest['estado'])};margin-bottom:8px;">VIBRACION RMS</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(latest['estado'])};">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(latest['estado'])};font-weight:bold;">{latest['estado'].upper()}</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""<div class="metric-card status-{get_status_color(latest['estado']).replace('#', '').lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(latest['estado'])};margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(latest['estado'])};">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">C</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(latest['estado'])};font-weight:bold;">{latest['estado'].upper()}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div class="metric-card status-{get_status_color(latest['estado']).replace('#', '').lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(latest['estado'])};margin-bottom:8px;">PRESION DE VACIO</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(latest['estado'])};">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(latest['estado'])};font-weight:bold;">{latest['estado'].upper()}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""<div class="metric-card status-{get_status_color(latest['estado']).replace('#', '').lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(latest['estado'])};margin-bottom:8px;">ESTADO GLOBAL</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(latest['estado'])};">{latest['estado'].upper()}</div>
            <div style="font-size:1.1rem;color:{get_text_color(latest['estado'])};">IR: {latest['indice_riesgo']:.1f}/100</div>
        </div>""", unsafe_allow_html=True)

# ============================================================================
# TAB 2: DIAGNOSTICO
# ============================================================================

with tabs[1]:
    st.markdown("<h2>Diagnostico en Tiempo Real</h2>", unsafe_allow_html=True)
    alarms = get_alarms(latest)
    ec = COLORS["verde"] if latest["estado"] == "Normal" else COLORS["amarillo"] if latest["estado"] == "Alerta" else COLORS["rojo"]
    st.markdown(f"""<div style="background:{COLORS['blanco']};padding:20px;border-radius:16px;border-left:6px solid {ec};margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);">
        <div style="font-size:1.5rem;font-weight:bold;color:{ec};">Estado Actual: {latest['estado'].upper()}</div>
        <div style="font-size:1.2rem;margin-top:10px;color:{COLORS['texto_oscuro']};">Indice de Riesgo: {latest['indice_riesgo']:.1f}/100</div>
    </div>""", unsafe_allow_html=True)
    
    if alarms:
        st.markdown("<h3>Hipotesis Tecnicas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            st.markdown(f"- **{name}**: {value} ({level})")
        st.markdown("<h3>Pasos Sugeridos</h3>", unsafe_allow_html=True)
        st.markdown("1. Verificar lectura con instrumento calibrado\n2. Inspeccionar visualmente el componente\n3. Revisar manual del fabricante")
    else:
        st.success("Sin alarmas activas. Condicion normal.")

# ============================================================================
# TAB 3: ORDENES DE TRABAJO
# ============================================================================

with tabs[2]:
    st.markdown("<h2>Gestion de Ordenes de Trabajo</h2>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM work_orders ORDER BY creation_date DESC")
    all_orders = [dict(row) for row in c.fetchall()]
    
    st.markdown("<h3>Crear Nueva Orden de Trabajo</h3>", unsafe_allow_html=True)
    with st.form("nueva_ot_form", clear_on_submit=True):
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            nuevo_activo = st.selectbox("Activo:", list(ASSETS.keys()), key="nuevo_activo_ot")
            nueva_prioridad = st.selectbox("Prioridad:", ["P0", "P1", "P2"], key="nueva_prioridad_ot")
        with col_n2:
            nuevo_responsable = st.selectbox("Responsable:", ["Dario Minan", "Jordy Sernaque", "Sin asignar"], key="nuevo_resp_ot")
            nueva_ubicacion = st.text_input("Ubicacion:", "Planta Principal", key="nueva_ubicacion_ot")
        
        nueva_descripcion = st.text_area("Descripcion del problema:", key="nueva_desc_ot")
        
        if st.form_submit_button("Crear OT", use_container_width=True, type="primary"):
            ts = datetime.now().strftime("%Y%m%d%H%M")
            new_ot_id = f"OT-{ts}-{nueva_prioridad}"
            try:
                c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot_id,))
                if not c.fetchone():
                    c.execute("""INSERT INTO work_orders (ot_id, asset_name, tag, ubicacion, alert_id, description, prioridad, tipo, responsable, creation_date, status, created_by, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_ot_id, nuevo_activo, ASSETS[nuevo_activo]["tag"], nueva_ubicacion, f"ALM-{ts}", nueva_descripcion, nueva_prioridad, "Correctivo", 
                         nuevo_responsable, datetime.now().isoformat(), "Pendiente", "manual", datetime.now().isoformat()))
                    conn.commit()
                    st.success(f"OT creada exitosamente: {new_ot_id}")
                    # Notificar creación
                    notify_new_ot({"ot_id": new_ot_id, "asset_name": nuevo_activo, "priority": nueva_prioridad, "description": nueva_descripcion, "responsable": nuevo_responsable})
            except Exception as e:
                st.error(f"Error creando OT: {e}")
    conn.close()
    
    st.markdown("<h3>Ordenes Existentes</h3>", unsafe_allow_html=True)
    if all_orders:
        for ot in all_orders[:10]:
            with st.expander(f"{ot['ot_id']} - {ot['asset_name']} ({ot['status']})"):
                st.markdown(f"**Activo:** {ot['asset_name']} | **Prioridad:** {ot['prioridad']} | **Responsable:** {ot['responsable']}")
                st.markdown(f"**Descripcion:** {ot['description']}")
                
                if ot['status'] == 'Pendiente':
                    if st.button("Iniciar OT", key=f"start_{ot['ot_id']}", type="primary"):
                        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                        c.execute("UPDATE work_orders SET status='En Ejecucion', start_time=?, updated_at=? WHERE ot_id=?", (datetime.now().isoformat(), datetime.now().isoformat(), ot['ot_id']))
                        conn.commit(); conn.close()
                        notify_ot_started(ot['ot_id'], ot['asset_name'], ot['responsable'])
                        st.success("OT iniciada correctamente!")
                        st.rerun()
                
                elif ot['status'] == 'En Ejecucion':
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("Reportar Problema / Impedimento", key=f"issue_{ot['ot_id']}", type="secondary"):
                            st.session_state[f"show_issue_{ot['ot_id']}"] = True
                    
                    if st.session_state.get(f"show_issue_{ot['ot_id']}", False):
                        with st.form(key=f"form_issue_{ot['ot_id']}"):
                            issue_desc = st.text_area("Descripcion del problema o impedimento (ej. falta de material):", key=f"issue_desc_{ot['ot_id']}")
                            if st.form_submit_button("Notificar a Gerencia", type="primary"):
                                notify_ot_paused(ot['ot_id'], ot['asset_name'], ot['responsable'], issue_desc)
                                # Actualizar estado a Pausado
                                conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                                c.execute("UPDATE work_orders SET status='Pausado', acciones=?, updated_at=? WHERE ot_id=?", (issue_desc, datetime.now().isoformat(), ot['ot_id']))
                                conn.commit(); conn.close()
                                st.session_state[f"show_issue_{ot['ot_id']}"] = False
                                st.success("Notificacion enviada a Gerencia (Irina) y Jefe de Mantenimiento.")
                                st.rerun()

                    with st.form(key=f"form_complete_{ot['ot_id']}"):
                        hallazgos = st.text_area("Hallazgos / Observaciones", key=f"hallazgos_{ot['ot_id']}")
                        tiempo_real = st.number_input("Tiempo real (horas)", min_value=0.1, value=1.0, step=0.5, key=f"tiempo_{ot['ot_id']}")
                        
                        if st.form_submit_button("Completar OT", type="primary"):
                            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                            c.execute("UPDATE work_orders SET status='Cerrada', end_time=?, updated_at=?, hallazgos=?, tiempo_real_horas=? WHERE ot_id=?", 
                                      (datetime.now().isoformat(), datetime.now().isoformat(), hallazgos, tiempo_real, ot['ot_id']))
                            conn.commit(); conn.close()
                            
                            notify_ot_completed({"ot_id": ot['ot_id'], "responsable": ot['responsable'], "tiempo_real_horas": tiempo_real, "hallazgos": hallazgos})
                            st.success("OT completada exitosamente!")
                            st.rerun()
                
                elif ot['status'] == 'Cerrada':
                    st.success("Esta orden de trabajo ya ha sido cerrada.")
    else:
        st.info("No hay ordenes registradas.")

# ============================================================================
# TAB 4: PLAN DE MANTENIMIENTO
# ============================================================================

with tabs[3]:
    st.markdown("<h2>Plan de Mantenimiento 2026</h2>", unsafe_allow_html=True)
    st.info("Modulo de planificacion de mantenimiento con calendario y filtros.")

# ============================================================================
# TAB 5: KPIs Y REPORTES
# ============================================================================

with tabs[4]:
    st.markdown("<h2>KPIs e Impacto Circular</h2>", unsafe_allow_html=True)
    
    if st.button("Cargar Datos de Demostracion de Impacto Circular", use_container_width=True):
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        datos_demo = [
            ("OT-20231018-P1", "Moldeadora Rotativa", "Rodamientos", "Reparacion", "Reparado", 0.0, 0.0, 890.00, 4500.00, 15.5),
            ("OT-20231110-P0", "Tunel de Enfriamiento", "Manguera de alta presion", "Reemplazo Total", "Reemplazado", 0.0, 2.5, 1250.00, 1250.00, 0.0)
        ]
        for row in datos_demo:
            try:
                c.execute("""INSERT INTO circular_interventions (ot_id, asset_name, component, decision, result, mass_conserved_kg, mass_discarded_kg, costo_reparacion_eur, costo_reemplazo_nuevo_eur, co2_evitado_kg, recorded_date, recorded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*row, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Dario Minan"))
            except sqlite3.IntegrityError: pass
        conn.commit(); conn.close()
        st.success("Datos de demostracion cargados correctamente!")
        st.rerun()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM circular_interventions ORDER BY recorded_date DESC")
    interventions = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if interventions:
        df_int = pd.DataFrame(interventions)
        st.dataframe(df_int[['ot_id', 'asset_name', 'component', 'decision', 'costo_reparacion_eur', 'costo_reemplazo_nuevo_eur']], use_container_width=True, hide_index=True)
    else:
        st.info("No hay intervenciones registradas.")

# ============================================================================
# TAB 6: INVENTARIO Y STOCK (INTEGRACION CSV PRODUCCION)
# ============================================================================

with tabs[5]:
    st.markdown("<h2>Inventario, Stock e Historial de Produccion</h2>", unsafe_allow_html=True)
    st.markdown("Consulta de repuestos, materiales y su historial de consumo registrado en producción.")
    
    try:
        if os.path.exists(CSV_PROD_PATH):
            df_stock = pd.read_csv(CSV_PROD_PATH, encoding='utf-8')
            
            st.markdown("### Resumen de Costos y Tecnicos")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Costo Total Arreglos", f"${df_stock['Costo_Arreglo_USD'].sum():,.2f}")
            with col_s2:
                st.metric("Total Unidades Producidas", f"{df_stock['Cantidad_Producida_Unidades'].sum():,}")
            with col_s3:
                st.metric("Total Unidades Desechadas", f"{df_stock['Cantidad_Desechada_Unidades'].sum():,}")
            
            st.divider()
            st.markdown("### Historial Detallado de Mantenimiento y Produccion")
            
            # Seleccionar columnas relevantes para mostrar
            display_cols = ['Fecha', 'Nombre_Equipo', 'Tipo_Mantenimiento', 'Descripcion_Arreglo', 'Repuestos_Usados', 'Tiempo_Parada_Horas', 'Costo_Arreglo_USD', 'Tecnico_Responsable', 'Estado_Post_Arreglo']
            df_display = df_stock[display_cols].copy()
            
            # Renombrar para mejor lectura
            df_display.columns = ['Fecha', 'Equipo', 'Tipo', 'Descripcion', 'Repuestos Usados', 'Tiempo Parada (h)', 'Costo (USD)', 'Tecnico', 'Estado']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning(f"No se encontró el archivo '{CSV_PROD_PATH}'. Asegúrate de que esté en la misma carpeta que la aplicación.")
            
            # Mostrar estructura esperada para ayuda
            st.markdown("""
            **Estructura esperada del CSV:**
            `Fecha,ID_Equipo,Nombre_Equipo,Tipo_Mantenimiento,Descripcion_Arreglo,Repuestos_Usados,Tiempo_Parada_Horas,ID_Lote,Tipo_Supositorio,Cantidad_Producida_Unidades,Cantidad_Desechada_Unidades,Costo_Arreglo_USD,Tecnico_Responsable,Estado_Post_Arreglo`
            """)
    except Exception as e:
        st.error(f"Error al procesar el inventario: {e}")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("Tech Maint Pro | Prototipo profesional SeedTech 2026 | Los umbrales son referenciales")
