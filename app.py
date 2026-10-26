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
from collections import Counter
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
    "01": {"category": "Tesis / Codificacion de equipos", "tags": ["Eternit Pacifico", "codificacion", "MTBF", "MTTR", "software SM"], "desc": "Sistema de codificacion de equipos industriales y uso del software SM Real World"},
    "02": {"category": "Tesis / Vacio medico", "tags": ["NFPA 99", "vacio grado medico", "bombas rotativas", "hospital"], "desc": "Programa de mantenimiento para sistemas de vacio medico segun norma NFPA 99"},
    "03": {"category": "Gestion / KPIs", "tags": ["KPI", "MTBF", "MTTR", "disponibilidad", "indicadores"], "desc": "Guia de indicadores clave de rendimiento con formulas y ejemplos"},
    "04": {"category": "Tesis / AMFE", "tags": ["AMFE", "FMEA", "criticidad", "casa de maquinas", "hospital"], "desc": "Analisis de Modos de Falla y Efectos aplicado a casa de maquinas hospitalaria"},
    "05": {"category": "Manual tecnico / IMBIL", "tags": ["anillo liquido", "instalacion", "desmontaje", "lubricacion"], "desc": "Manual completo de bombas de vacio IMBIL serie BVI"},
    "06": {"category": "Manual OEM / Caterpillar", "tags": ["G3408", "G3412", "motores a gas", "intervalos de mantenimiento"], "desc": "Manual oficial de operacion y mantenimiento de motores Caterpillar"},
    "07": {"category": "Ficha tecnica / CPS", "tags": ["VP6D", "VP12D", "doble etapa", "10 micrones", "ensayo Rice"], "desc": "Especificaciones tecnicas de bombas de vacio CPS para laboratorio"},
    "08": {"category": "Manual de usuario / Gadnic", "tags": ["Serie TW", "paletas rotativas", "cambio de aceite", "solucion de problemas"], "desc": "Manual de usuario y troubleshooting de bombas Gadnic compactas"},
    "09": {"category": "POE / Laboratorio", "tags": ["Thomas BV-1", "diafragma", "trampas", "silica gel", "seguridad"], "desc": "Procedimiento operativo para uso seguro de bomba de vacio en laboratorio"},
    "10": {"category": "Tesis / Ladrillera", "tags": ["Arcillas de Colombia", "COVENIN 2500-93", "criticidad", "programacion anual"], "desc": "Plan completo de mantenimiento preventivo para empresa ladrillera con 37 equipos"}
}

# ============================================================================
# SYSTEM PROMPT PARA LETZY
# ============================================================================

SYSTEM_PROMPT = """Eres Letzy, Asistente Experto en Ingenieria de Mantenimiento Industrial, Operacion de Equipos y Gestion de Calidad. Tu base de conocimiento contiene 10 documentos tecnicos especializados.

REGLAS DE RESPUESTA:
1. Se preciso, tecnico y conciso. Ve directo al dato solicitado.
2. CITA SIEMPRE la fuente entre parentesis al final, usando el numero del archivo. Ejemplo: [Fuente: Archivo 10 - Tesis Arcillas de Colombia]
3. Si te preguntan por PROCEDIMIENTOS o INSTRUCCIONES TECNICAS de equipos especificos, busca primero en el Archivo 10.
4. Si te preguntan por COMO CALCULAR MTBF, MTTR o Disponibilidad, usa el Archivo 03.
5. Si te preguntan por BOMBAS DE VACIO, diferencia segun el contexto:
   - Laboratorio/acidos -> Archivo 09
   - Industrial/anillo liquido -> Archivo 05
   - Compacta/HVAC -> Archivo 08
   - Especificaciones tecnicas -> Archivo 07
   - Grado medico -> Archivo 02
6. Si te preguntan por MOTORES Caterpillar G3408/G3412 -> Archivo 06
7. Si te preguntan por ANALISIS DE CRITICIDAD o AMFE -> Archivo 04 o Archivo 10
8. Si te preguntan por SISTEMAS DE CODIFICACION de equipos -> Archivo 01 o Archivo 10
9. Si la informacion NO esta en los documentos, indicalo claramente.
10. NUNCA inventes datos tecnicos.

FORMATO DE RESPUESTA PREFERIDO:
- Usa vinetas y tablas cuando sea posible
- Incluye valores numericos exactos
- Menciona el responsable cuando aplique
- Indica si la actividad es rutinaria (R) o programada (P)"""

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
# NOTIFICACIONES INTELIGENTES POR CANAL
# ============================================================================

def send_telegram(chat_id, message):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning(f"Telegram no configurado para chat_id={chat_id}")
        return False
    try:
        r = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        if r.status_code == 200:
            logger.info(f"Telegram enviado a {chat_id}")
            return True
        else:
            logger.error(f"Error Telegram {r.status_code}: {r.text}")
            return False
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False

def send_email(to_email, subject, body_html):
    if not to_email:
        logger.warning(f"Email no configurado para {to_email}")
        return False
    try:
        msg = MIMEText(body_html, 'html')
        msg['Subject'] = subject
        msg['From'] = STAFF["asesor"]["email"]
        msg['To'] = to_email
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(STAFF["asesor"]["email"], "")
        server.send_message(msg)
        server.quit()
        logger.info(f"Email enviado a {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {e}")
        return False

def notify_critical_alarm(asset_name, parameter, value, threshold, ir, ot_id, responsable):
    mensaje_telegram = (
        f"<b>[ALERTA CRITICA DETECTADA]</b>\n\n"
        f"<b>Activo:</b> {asset_name}\n"
        f"<b>Parametro:</b> {parameter}: {value} (Umbral: {threshold})\n"
        f"<b>Riesgo:</b> Alto (IR: {ir}/100)\n"
        f"<b>Accion:</b> Se ha generado la {ot_id} automaticamente.\n\n"
        f"@{responsable}, por favor verificar de inmediato."
    )
    
    for key in ["tecnico", "asesor", "gerencia"]:
        staff = STAFF[key]
        if staff.get("telegram_chat_id"):
            send_telegram(staff["telegram_chat_id"], mensaje_telegram)
    
    cuerpo_email = f"""
    <h2>[ALERTA CRITICA] {asset_name}</h2>
    <p><b>Parametro:</b> {parameter}: {value} (Umbral: {threshold})</p>
    <p><b>Riesgo:</b> Alto (IR: {ir}/100)</p>
    <p><b>OT Generada:</b> {ot_id}</p>
    <p><b>Responsable asignado:</b> {responsable}</p>
    <hr>
    <p>Este es un correo de respaldo. La notificacion principal fue enviada por Telegram.</p>
    """
    for key in ["asesor", "gerencia"]:
        send_email(STAFF[key]["email"], f"[CRITICO] {ot_id} - {asset_name}", cuerpo_email)

def notify_new_ot(ot_data):
    responsable = ot_data.get("responsable", "Sin asignar")
    ot_id = ot_data["ot_id"]
    asset = ot_data["asset_name"]
    prio = ot_data["priority"]
    desc = ot_data.get("description", "Sin descripcion")[:80]
    
    mensaje_telegram = (
        f"<b>[NUEVA ORDEN DE TRABAJO ASIGNADA]</b>\n\n"
        f"<b>ID:</b> {ot_id} | <b>Prioridad:</b> {prio}\n"
        f"<b>Activo:</b> {asset}\n"
        f"<b>Falla reportada:</b> {desc}\n"
        f"<b>Responsable:</b> {responsable}\n\n"
        f"Responde a este chat con 'OK' para confirmar recepcion."
    )
    
    if prio in ["P0", "P1"]:
        send_telegram(STAFF["tecnico"]["telegram_chat_id"], mensaje_telegram)
        send_telegram(STAFF["asesor"]["telegram_chat_id"], mensaje_telegram)
    else:
        cuerpo_email = f"""
        <h2>Nueva Orden de Trabajo - {ot_id}</h2>
        <p><b>Prioridad:</b> {prio}</p>
        <p><b>Activo:</b> {asset}</p>
        <p><b>Descripcion:</b> {desc}</p>
        <p><b>Responsable:</b> {responsable}</p>
        """
        send_email(STAFF["tecnico"]["email"], f"Nueva OT {ot_id} ({prio})", cuerpo_email)

def notify_ot_started(ot_id, asset_name, responsable):
    hora = datetime.now().strftime("%H:%M")
    mensaje = (
        f"<b>[OT INICIADA]</b>\n\n"
        f"<b>ID:</b> {ot_id}\n"
        f"<b>Tecnico:</b> {responsable} comenzo el trabajo en {asset_name}\n"
        f"<b>Hora:</b> {hora}"
    )
    send_telegram(STAFF["asesor"]["telegram_chat_id"], mensaje)

def notify_ot_paused(ot_id, asset_name, responsable, motivo):
    ot_data = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT prioridad FROM work_orders WHERE ot_id=?", (ot_id,))
        row = c.fetchone()
        conn.close()
        ot_data = row
    except:
        pass
    
    prio = ot_data[0] if ot_data else "P2"
    
    mensaje_telegram = (
        f"<b>[OT PAUSADA - BLOQUEADA]</b>\n\n"
        f"<b>ID:</b> {ot_id}\n"
        f"<b>Activo:</b> {asset_name}\n"
        f"<b>Tecnico:</b> {responsable}\n"
        f"<b>Motivo:</b> {motivo}"
    )
    send_telegram(STAFF["asesor"]["telegram_chat_id"], mensaje_telegram)
    
    if prio == "P0":
        cuerpo_email = f"""
        <h2>[BLOQUEO EN OT] {ot_id} - Requiere aprobacion</h2>
        <p><b>Activo:</b> {asset_name}</p>
        <p><b>Tecnico:</b> {responsable}</p>
        <p><b>Motivo:</b> {motivo}</p>
        <p>Se solicita aprobacion urgente para evitar parada de linea.</p>
        """
        send_email(STAFF["gerencia"]["email"], f"[BLOQUEO] {ot_id} - {asset_name}", cuerpo_email)

def notify_ot_completed(ot_data):
    ot_id = ot_data["ot_id"]
    responsable = ot_data.get("responsable", "N/A")
    tiempo = ot_data.get("tiempo_real_horas", 0)
    hallazgos = ot_data.get("hallazgos", "Sin detalles")
    
    mensaje = (
        f"<b>[OT COMPLETADA]</b>\n\n"
        f"<b>ID:</b> {ot_id}\n"
        f"<b>Tecnico:</b> {responsable}\n"
        f"<b>Tiempo total:</b> {tiempo}h\n"
        f"<b>Resultado:</b> {hallazgos[:100]}"
    )
    send_telegram(STAFF["asesor"]["telegram_chat_id"], mensaje)

def notify_high_circular_impact(intervention):
    md = intervention.get("mass_discarded_kg", 0) or 0
    mc = intervention.get("mass_conserved_kg", 0) or 0
    
    if md <= 5 and mc <= 2:
        return
    
    ot_id = intervention.get("ot_id", "N/A")
    component = intervention.get("component", "N/A")
    decision = intervention.get("decision", "N/A")
    
    msg_telegram = (
        f"<b>[IMPACTO CIRCULAR REGISTRADO]</b>\n\n"
        f"<b>OT:</b> {ot_id}\n"
        f"<b>Componente:</b> {component}\n"
        f"<b>Decision:</b> {decision}\n"
        f"<b>Masa Conservada:</b> {mc:.2f} kg\n"
        f"<b>Masa Descartada:</b> {md:.2f} kg\n\n"
        f"Excelente trabajo del equipo de mantenimiento."
    )
    send_telegram(STAFF["gerencia"]["telegram_chat_id"], msg_telegram)
    
    cuerpo_email = f"""
    <h2>Impacto Circular Registrado</h2>
    <p><b>OT:</b> {ot_id}</p>
    <p><b>Componente:</b> {component}</p>
    <p><b>Decision:</b> {decision}</p>
    <p><b>Masa Conservada:</b> {mc:.2f} kg</p>
    <p><b>Masa Descartada:</b> {md:.2f} kg</p>
    <hr>
    <p>Este registro contribuye a los objetivos de economia circular de la empresa.</p>
    """
    for key in ["gerencia", "asesor"]:
        send_email(STAFF[key]["email"], f"[Circular] {ot_id} - {component}", cuerpo_email)

# ============================================================================
# ALARMAS SONORAS VIA JAVASCRIPT (FUNCIONA EN STREAMLIT CLOUD)
# ============================================================================

def play_critical_alarm(event_id):
    """Alarma critica con sonido via JavaScript (funciona en navegador)"""
    if st.session_state.get("last_beep_event") == event_id:
        return
    st.session_state["last_beep_event"] = event_id
    
    # Inyectar JavaScript para reproducir sonido en el navegador
    st.markdown("""
    <script>
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 1200;
                oscillator.type = 'square';
                gainNode.gain.value = 0.3;
                oscillator.start();
                setTimeout(() => oscillator.stop(), 400);
            }, i * 550);
        }
    } catch(e) {
        console.log('Audio no disponible:', e);
    }
    </script>
    """, unsafe_allow_html=True)
    
    logger.info(f"[ALARMA CRITICA] {event_id}")

def play_observation_alarm(event_id):
    """Alarma de advertencia con sonido via JavaScript"""
    if st.session_state.get("last_observation_event") == event_id:
        return
    st.session_state["last_observation_event"] = event_id
    
    st.markdown("""
    <script>
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        for (let i = 0; i < 2; i++) {
            setTimeout(() => {
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 600;
                oscillator.type = 'sine';
                gainNode.gain.value = 0.2;
                oscillator.start();
                setTimeout(() => oscillator.stop(), 200);
            }, i * 500);
        }
    } catch(e) {
        console.log('Audio no disponible:', e);
    }
    </script>
    """, unsafe_allow_html=True)
    
    logger.info(f"[ALARMA OBSERVACION] {event_id}")

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

def apply_custom_styles():
    css = f"""
    <style>
    .stApp {{ 
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%) !important; 
        padding-top: 0 !important;
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: #ffffff !important;
        border-right: 1px solid #e8ecf1 !important;
        z-index: 9998 !important;
        padding-top: 1rem !important;
        box-shadow: 4px 0 15px rgba(0,0,0,0.05) !important;
    }}
    
    .block-container {{
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }}
    
    .metric-card {{
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        text-align: center;
        border: none;
    }}
    .metric-card:hover {{ 
        transform: translateY(-5px); 
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}
    
    .status-normal {{ background: {COLORS['verde']} !important; }}
    .status-alerta {{ background: {COLORS['amarillo']} !important; }}
    .status-critico {{ background: {COLORS['rojo']} !important; }}
    
    .alarm-banner {{
        background: linear-gradient(90deg, rgba(245,166,35,0.15), rgba(245,166,35,0.05));
        border-left: 5px solid {COLORS['amarillo']};
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(245,166,35,0.3);
    }}
    .alarm-critical {{
        background: linear-gradient(90deg, rgba(211,47,47,0.15), rgba(211,47,47,0.05));
        border-left: 5px solid {COLORS['rojo']};
        border: 1px solid rgba(211,47,47,0.3);
    }}
    
    h1, h2, h3, p, label, span, div {{ 
        color: {COLORS['texto_oscuro']} !important; 
    }}
    .stMarkdown p {{ color: {COLORS['texto_oscuro']} !important; }}
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ 
        color: {COLORS['azul']} !important; 
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        margin-bottom: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(26,95,168,0.1) !important;
        color: {COLORS['texto_oscuro']} !important;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        font-size: 0.9rem;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: {COLORS['azul']} !important;
        color: white !important;
    }}
    
    .stSelectbox {{
        margin-bottom: 8px;
    }}
    
    .stDataFrame {{
        margin: 0 auto;
    }}
    
    .doc-button {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        background: linear-gradient(135deg, #1a5fa8, #8bc34a);
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }}
    .doc-button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        color: white;
    }}

    section[data-testid="stSidebar"] .stChatMessage {{
        background-color: #f5f7fa !important;
        border: 1px solid #e8ecf1 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        margin: 4px 0 !important;
    }}
    
    section[data-testid="stSidebar"] .stChatMessage p {{
        font-size: 0.85rem !important;
        margin: 0 !important;
    }}
    
    .quick-btn {{
        font-size: 0.75rem !important;
        padding: 4px 8px !important;
        min-height: 32px !important;
    }}
    
    @media (max-width: 768px) {{
        .metric-value {{ font-size: 1.5rem !important; }}
        section[data-testid="stSidebar"] {{
            width: 100% !important;
            min-width: 100% !important;
        }}
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
                'Timestamp': 'fecha_hora',
                'Time_Seconds': 'time_seconds',
                'Vacuum_Pressure_mbar': 'vacuum_mbar',
                'Oil_Temperature_C': 'temperatura_c',
                'Vibration_mm_s': 'vibracion_rms_mm_s',
                'Motor_Current_A': 'motor_current_a',
                'Status': 'status',
                'Fault_Description': 'fault_description'
            }
            
            df = df.rename(columns=column_mapping)
            
            if 'vacuum_mbar' in df.columns:
                df['presion_vacio_kpa'] = -(df['vacuum_mbar'] * 0.1)
            
            if 'fecha_hora' in df.columns:
                df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
                if df['fecha_hora'].isna().any():
                    start_date = datetime.now() - timedelta(minutes=len(df))
                    df['fecha_hora'] = [start_date + timedelta(minutes=i) for i in range(len(df))]
            
            df = enrich_data(df)
            
            if 'fault_description' in df.columns:
                df['fault_description'] = df['fault_description'].fillna('Normal')
            
            logger.info(f"CSV de prueba cargado: {len(df)} registros")
            return df
        else:
            logger.warning(f"Archivo CSV de prueba no encontrado: {CSV_TEST_PATH}")
            return None
    except Exception as e:
        logger.error(f"Error cargando CSV de prueba: {e}")
        return None

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
    if 'status' in row and pd.notna(row['status']) and str(row['status']).strip() != 'OK':
        level = 'Critico' if str(row['status']).upper() in ['CRITICAL', 'TRIP'] else 'Alerta'
        desc = str(row.get('fault_description', 'Falla detectada')).strip()
        if not desc or desc.lower() == 'nan':
            desc = 'Falla detectada'

        desc_lower = desc.lower()
        if 'vibracion' in desc_lower or 'vibration' in desc_lower:
            alarms.append((level, "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s - {desc}"))
        elif 'vacio' in desc_lower or 'vacuum' in desc_lower:
            alarms.append((level, "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa - {desc}"))
        elif 'temperatura' in desc_lower or 'sobrecalentamiento' in desc_lower or 'aceite' in desc_lower:
            alarms.append((level, "Temperatura", f"{row['temperatura_c']:.1f} C - {desc}"))
        elif 'sobrecarga' in desc_lower or 'corriente' in desc_lower or 'electrica' in desc_lower:
            alarms.append((level, "Corriente del motor", f"{row['motor_current_a']:.2f} A - {desc}"))
        else:
            alarms.append((level, "General", desc))
    else:
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
    
    if priority in ["P0", "P1"]:
        responsable = STAFF["tecnico"]["nombre"]
    else:
        responsable = STAFF["asesor"]["nombre"]
    
    symptoms = "; ".join([f"{name}: {value} ({level})" for level, name, value in alarms]) or "Sin alarma critica"
    
    tasks = []
    if any(a[1] == "Vibracion" for a in alarms):
        tasks += ["Medir vibracion", "Verificar alineacion"]
    if any(a[1] == "Temperatura" for a in alarms):
        tasks += ["Revisar lubricacion", "Verificar friccion"]
    if any(a[1] == "Presion de vacio" for a in alarms):
        tasks += ["Prueba de fugas", "Inspeccionar sellos"]
    if any(a[1] == "Corriente del motor" for a in alarms):
        tasks += ["Medir corriente", "Revisar devanado", "Verificar carga"]
    if not tasks:
        tasks = ["Inspeccion rutinaria"]
    
    ts = pd.to_datetime(row["fecha_hora"]).strftime("%Y%m%d%H%M")
    return {
        "ot_id": f"OT-{ts}-{priority}",
        "asset_name": asset_name,
        "alert_id": f"ALM-{ts}",
        "description": f"Anomalia: {symptoms}",
        "priority": priority,
        "responsible": responsable,
        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Pendiente",
        "created_by": source,
        "tasks": "\n".join([f"- {t}" for t in tasks])
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
# SISTEMA RAG - BASE DE CONOCIMIENTO PDF
# ============================================================================

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        if HAS_FITZ:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        elif HAS_PDF:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
    return text

def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    words = text.split()
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def load_knowledge_base():
    kb = []
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        meta_key = None
        for key in DOCUMENT_METADATA.keys():
            if key in pdf_file:
                meta_key = key
                break
        
        meta = DOCUMENT_METADATA.get(meta_key, {"category": "General", "tags": [], "desc": ""})
        
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        text = extract_text_from_pdf(pdf_path)
        
        if text.strip():
            chunks = chunk_text(text, chunk_size=400, overlap=80)
            for idx, chunk in enumerate(chunks):
                kb.append({
                    "doc_id": meta_key or "00",
                    "filename": pdf_file,
                    "category": meta["category"],
                    "tags": meta["tags"],
                    "chunk_idx": idx,
                    "content": chunk,
                    "total_chunks": len(chunks)
                })
    
    st.session_state.knowledge_base = kb
    st.session_state.kb_loaded = True
    logger.info(f"Base de conocimiento cargada: {len(kb)} chunks de {len(pdf_files)} documentos")

def search_knowledge_base(query, top_k=5):
    if not st.session_state.get("kb_loaded", False):
        return []
    
    kb = st.session_state.knowledge_base
    query_words = set(re.findall(r'\w+', query.lower()))
    
    scores = []
    for item in kb:
        content_words = set(re.findall(r'\w+', item["content"].lower()))
        tag_words = set(item["tags"])
        
        word_overlap = len(query_words & content_words)
        tag_match = len(query_words & tag_words) * 3
        
        score = word_overlap + tag_match
        
        if score > 0:
            scores.append((score, item))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    
    return [item for _, item in scores[:top_k]]

def format_context_for_llm(search_results):
    context_parts = []
    seen_docs = set()
    
    for result in search_results:
        doc_id = result["doc_id"]
        if doc_id not in seen_docs:
            seen_docs.add(doc_id)
            context_parts.append(f"""
=== ARCHIVO {doc_id}: {result['filename']} ===
Categoria: {result['category']}
Tags: {', '.join(result['tags'])}
Contenido:
{result['content']}
""")
    
    return "\n".join(context_parts)

# ============================================================================
# INTEGRACION CON GROQ + RAG
# ============================================================================

def query_groq_with_rag(user_query, latest, asset_name, kpi_values):
    try:
        api_key = st.session_state.get("groq_api_key", "")
        if not api_key:
            return "Por favor, ingresa tu API Key gratuita de Groq en la configuracion del chatbot."
        
        alarms = get_alarms(latest)
        at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas activas"
        
        current_context = f"""
=== ESTADO ACTUAL DEL EQUIPO ===
Activo: {asset_name}
Estado: {latest['estado']}
IR: {latest['indice_riesgo']:.1f}/100
Vibracion: {latest['vibracion_rms_mm_s']:.2f} mm/s
Temperatura: {latest['temperatura_c']:.1f} C
Vacio: {latest['presion_vacio_kpa']:.1f} kPa
Alarmas: {at}

KPIs Actuales:
- MTBF: {kpi_values['MTBF (h)']:.1f} h
- MTTR: {kpi_values['MTTR (h)']:.1f} h
- Disponibilidad: {kpi_values['Disponibilidad (%)']:.2f}%
"""
        
        search_results = search_knowledge_base(user_query, top_k=8)
        kb_context = format_context_for_llm(search_results)
        
        full_system_prompt = f"""{SYSTEM_PROMPT}

{current_context}

{kb_context}

INSTRUCCION FINAL: Responde la pregunta del usuario basandote EXCLUSIVAMENTE en la informacion proporcionada arriba. Cita siempre la fuente."""
        
        client = Groq(api_key=api_key)
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        response = client.chat.completions.create(
    model="llama-3.1-8b-instant",  
    messages=messages,
    temperature=0.3,
    max_tokens=800
)
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error en Groq RAG: {e}")
        return f"Error al consultar la IA: {str(e)}. Verifica tu API Key de Groq."

def chatbot_response_fallback(user_query, latest, asset_name, kpi_values):
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100 | Vibracion {latest['vibracion_rms_mm_s']:.2f} mm/s | Temp {latest['temperatura_c']:.1f} C | Vacio {latest['presion_vacio_kpa']:.1f} kPa"
    alarms = get_alarms(latest)
    at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas"
    
    if any(k in text for k in ["hola", "ayuda", "quiero", "necesito"]):
        return f"Bienvenido a Tech Maint Pro\n\n{sl}\n\nPuedo ayudarte con diagnostico, ordenes de trabajo, AMEF, KPIs e impacto circular."
    
    if any(k in text for k in ["estado", "riesgo", "condicion", "diagnostico"]):
        na = [a[1] for a in alarms]
        if "Vibracion" in na and "Temperatura" in na: hip = "Posible desgaste de rodamientos o desalineacion."
        elif "Presion de vacio" in na: hip = "Posible fuga en linea o deterioro de sellos."
        elif "Vibracion" in na: hip = "Posible desalineacion o desgaste de rodamiento."
        elif "Temperatura" in na: hip = "Posible friccion interna o lubricacion deficiente."
        else: hip = "Condicion normal."
        acc = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT prioritaria"
        return f"Diagnostico\n\n{sl}\n\nAlarmas: {at}\n\nHipotesis: {hip}\n\nAccion: {acc}"
    
    if any(k in text for k in ["orden", "trabajo", "ot", "generar"]):
        pri = "P0" if latest["estado"] == "Critico" else "P1" if latest["estado"] == "Alerta" else "P2"
        sint = "; ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) or "Sin alarma critica"
        tareas = []
        if any(a[1] == "Vibracion" for a in alarms): tareas += ["Medir vibracion", "Verificar alineacion"]
        if any(a[1] == "Temperatura" for a in alarms): tareas += ["Revisar lubricacion", "Verificar friccion"]
        if any(a[1] == "Presion de vacio" for a in alarms): tareas += ["Prueba de fugas", "Inspeccionar sellos"]
        if not tareas: tareas = ["Inspeccion rutinaria"]
        return f"OT Sugerida\n\nPrioridad: {pri}\nActivo: {asset_name}\nSintomas: {sint}\n\nTareas:\n" + "\n".join(["- " + t for t in tareas])
    
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
    
    return f"En que puedo ayudarte?\n\n{sl}\n\nConsultas sugeridas:\n1. Diagnostico: estado actual\n2. Variables: vibracion, temperatura, vacio\n3. Ordenes: generar OT\n4. AMEF: modos de falla\n5. KPIs: indicadores\n6. Circular: impacto"

# ============================================================================
# CHATBOT FLOTANTE CON LETZY Y RAG
# ============================================================================

def process_floating_query(query, ai_platform="rag"):
    if not query or not query.strip():
        return
    q = query.strip()
    
    if "floating_chat_history" not in st.session_state:
        st.session_state["floating_chat_history"] = []
        
    st.session_state["floating_chat_history"].append({"role": "user", "content": q})
    
    try:
        kp = calculate_kpis(720, 3, 18, 18, 20, 40, 80, st.session_state.get("production_rate", 85.5))
        latest = st.session_state.get("latest_row", pd.Series())
        asset_name = st.session_state.get("asset_name", "")
        
        if ai_platform == "rag" and st.session_state.get("groq_api_key", ""):
            reply = query_groq_with_rag(q, latest, asset_name, kp)
        else:
            reply = chatbot_response_fallback(q, latest, asset_name, kp)
        
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": f"Error: {e}"})

# ============================================================================
# FUNCION AUXILIAR PARA MOSTRAR DETALLE DE OT
# ============================================================================

def mostrar_detalle_ot(ot, conn):
    prioridad_color = "#d32f2f" if ot["prioridad"] == "P0" else "#f5a623" if ot["prioridad"] == "P1" else "#8bc34a"
    prioridad_text = "URGENTE" if ot["prioridad"] == "P0" else "ALTA" if ot["prioridad"] == "P1" else "NORMAL"
    
    st.markdown(f"""
    <div style="background:{prioridad_color}; color:white; padding:15px; border-radius:12px; margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="margin:0; color:white;">{ot['ot_id']} - {prioridad_text}</h3>
            <span style="background:white; color:{prioridad_color}; padding:5px 15px; border-radius:20px; font-weight:bold;">{ot['status']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"**Activo:** {ot['asset_name']}")
        st.markdown(f"**Tag:** {ot.get('tag', 'N/A')}")
        st.markdown(f"**Ubicacion:** {ot.get('ubicacion', 'N/A')}")
        st.markdown(f"**Tipo:** {ot.get('tipo', 'N/A')}")
    
    with col_info2:
        st.markdown(f"**Responsable:** {ot.get('responsable', 'Sin asignar')}")
        st.markdown(f"**Creada:** {ot['creation_date'][:16] if ot.get('creation_date') else 'N/A'}")
        st.markdown(f"**Horas estimadas:** {ot.get('estimated_hours', 2.0)}h")
        if ot.get('start_time'):
            st.markdown(f"**Inicio:** {ot['start_time'][:16]}")
        if ot.get('end_time'):
            st.markdown(f"**Fin:** {ot['end_time'][:16]}")
    
    st.divider()
    
    if ot.get('description'):
        st.markdown("<h4>Problema Reportado</h4>", unsafe_allow_html=True)
        st.info(ot['description'])
    
    st.markdown("<h4>Tareas a Realizar</h4>", unsafe_allow_html=True)
    
    tareas_text = ot.get('acciones', '')
    if tareas_text:
        tareas_lista = tareas_text.split('\n')
        for i, tarea in enumerate(tareas_lista):
            if tarea.strip():
                st.checkbox(tarea.strip(), key=f"tarea_{ot['ot_id']}_{i}")
    else:
        st.markdown("- Medir vibracion en 3 puntos (horizontal/vertical/axial)")
        st.markdown("- Verificar alineacion")
        st.markdown("- Revisar nivel de aceite")
        st.markdown("- Inspeccionar componente")
        st.markdown("- Tomar fotos del estado actual")
    
    st.divider()
    
    st.markdown("<h4>Recursos Necesarios</h4>", unsafe_allow_html=True)
    
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.markdown("**Herramientas:**")
        st.markdown("- Analizador de vibraciones")
        st.markdown("- Llave dinamometrica")
        st.markdown("- Multimetro")
    
    with col_rec2:
        st.markdown("**Seguridad:**")
        st.markdown("- Bloqueo/etiquetado LOTO")
        st.markdown("- EPP completo")
        st.markdown("- Permiso de trabajo")
    
    st.divider()
    
    st.markdown("<h4>Registro de Trabajo</h4>", unsafe_allow_html=True)
    
    with st.form(f"registro_{ot['ot_id']}"):
        col_reg1, col_reg2 = st.columns(2)
        
        with col_reg1:
            nuevo_estado = st.selectbox(
                "Estado:",
                options=["Pendiente", "En Ejecucion", "Completado", "Pausado", "No realizado"],
                index=["Pendiente", "En Ejecucion", "Completado", "Pausado", "No realizado"].index(ot["status"]) if ot["status"] in ["Pendiente", "En Ejecucion", "Completado", "Pausado", "No realizado"] else 0,
                key=f"estado_{ot['ot_id']}"
            )
        
        with col_reg2:
            tiempo_real = st.number_input(
                "Tiempo real (horas):",
                min_value=0.0,
                max_value=24.0,
                value=ot.get('tiempo_real_horas', 0.0),
                step=0.5,
                key=f"tiempo_{ot['ot_id']}"
            )
        
        hallazgos = st.text_area(
            "Hallazgos (que encontro?):",
            value=ot.get('hallazgos', ''),
            height=100,
            key=f"hallazgos_{ot['ot_id']}"
        )
        
        acciones_realizadas = st.text_area(
            "Acciones realizadas:",
            value=ot.get('acciones', ''),
            height=100,
            key=f"acciones_{ot['ot_id']}"
        )
        
        repuestos = st.text_input(
            "Repuestos utilizados:",
            value=ot.get('repuestos', ''),
            key=f"repuestos_{ot['ot_id']}"
        )
        
        submitted_registro = st.form_submit_button("Guardar Cambios", use_container_width=True, type="primary")
        
        if submitted_registro:
            c = conn.cursor()
            
            update_fields = [
                "status = ?",
                "tiempo_real_horas = ?",
                "hallazgos = ?",
                "acciones = ?",
                "repuestos = ?",
                "updated_at = ?"
            ]
            update_values = [
                nuevo_estado,
                tiempo_real,
                hallazgos,
                acciones_realizadas,
                repuestos,
                datetime.now().isoformat()
            ]
            
            if nuevo_estado == "En Ejecucion" and not ot.get('start_time'):
                update_fields.append("start_time = ?")
                update_values.append(datetime.now().isoformat())
            
            if nuevo_estado == "Completado" and not ot.get('end_time'):
                update_fields.append("end_time = ?")
                update_values.append(datetime.now().isoformat())
            
            update_values.append(ot['ot_id'])
            
            c.execute(f"""UPDATE work_orders SET {', '.join(update_fields)} WHERE ot_id = ?""", update_values)
            conn.commit()
            
            responsable = ot.get('responsable', 'Sin asignar')
            asset = ot.get('asset_name', 'N/A')
            
            if nuevo_estado == "En Ejecucion" and ot["status"] != "En Ejecucion":
                notify_ot_started(ot['ot_id'], asset, responsable)
            elif nuevo_estado == "Pausado" and ot["status"] != "Pausado":
                notify_ot_paused(ot['ot_id'], asset, responsable, hallazgos or "Sin motivo especificado")
            elif nuevo_estado == "Completado" and ot["status"] != "Completado":
                notify_ot_completed({
                    "ot_id": ot['ot_id'],
                    "responsable": responsable,
                    "tiempo_real_horas": tiempo_real,
                    "hallazgos": hallazgos
                })
            
            st.success(f"OT {ot['ot_id']} actualizada a '{nuevo_estado}'")
            st.rerun()
    
    st.divider()
    st.markdown("<h4>Acciones Rapidas</h4>", unsafe_allow_html=True)
    
    col_acc1, col_acc2, col_acc3 = st.columns(3)
    
    with col_acc1:
        if st.button("Iniciar Trabajo", key=f"iniciar_{ot['ot_id']}", use_container_width=True):
            c = conn.cursor()
            c.execute("""UPDATE work_orders SET status = 'En Ejecucion', start_time = ?, updated_at = ? WHERE ot_id = ?""",
                     (datetime.now().isoformat(), datetime.now().isoformat(), ot['ot_id']))
            conn.commit()
            st.success(f"OT {ot['ot_id']} iniciada")
            st.rerun()
    
    with col_acc2:
        if st.button("Completar", key=f"completar_{ot['ot_id']}", use_container_width=True):
            c = conn.cursor()
            c.execute("""UPDATE work_orders SET status = 'Completado', end_time = ?, updated_at = ? WHERE ot_id = ?""",
                     (datetime.now().isoformat(), datetime.now().isoformat(), ot['ot_id']))
            conn.commit()
            st.success(f"OT {ot['ot_id']} completada")
            st.rerun()
    
    with col_acc3:
        if st.button("Pausar", key=f"pausar_{ot['ot_id']}", use_container_width=True):
            c = conn.cursor()
            c.execute("""UPDATE work_orders SET status = 'Pausado', updated_at = ? WHERE ot_id = ?""",
                     (datetime.now().isoformat(), ot['ot_id']))
            conn.commit()
            st.success(f"OT {ot['ot_id']} pausada")
            st.rerun()

# ============================================================================
# VISUALIZACION - GRAFICAS
# ============================================================================

def create_sensor_chart(df, column, title, y_title, color, threshold_normal=None, threshold_alert=None, reverse=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df[column], mode="lines+markers", name=title, line=dict(color=color, width=3), marker=dict(size=4), fill="tozeroy" if not reverse else None, fillcolor="rgba(26,95,168,0.08)" if not reverse else None))
    if threshold_normal is not None:
        fig.add_hline(y=threshold_normal, line_dash="dash", line_color=COLORS["amarillo"], line_width=2, annotation_text="Alerta", annotation_position="top right", annotation_font_color=COLORS["amarillo"], annotation_font_size=11)
    if threshold_alert is not None:
        fig.add_hline(y=threshold_alert, line_dash="dash", line_color=COLORS["rojo"], line_width=2, annotation_text="Critico", annotation_position="top right", annotation_font_color=COLORS["rojo"], annotation_font_size=11)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")),
        template="plotly_white", paper_bgcolor="rgba(255,255,255,0.95)", plot_bgcolor="rgba(255,255,255,0.95)", margin=dict(l=20, r=20, t=78, b=30),
        xaxis=dict(title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)), showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10), tickangle=-45),
        yaxis=dict(title=dict(text=y_title, font=dict(color=COLORS["texto_oscuro"], size=12)), autorange="reversed" if reverse else True, showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10)),
        hovermode="x unified", showlegend=False, height=280, font=dict(color=COLORS["texto_oscuro"], family="Arial", size=12)
    )
    return fig

def create_vibration_chart(df): return create_sensor_chart(df, "vibracion_rms_mm_s", "Vibracion RMS", "mm/s", COLORS["azul"], THRESHOLDS["vibration_normal"], THRESHOLDS["vibration_alert"])
def create_temperature_chart(df): return create_sensor_chart(df, "temperatura_c", "Temperatura", "C", COLORS["amarillo"], THRESHOLDS["temperature_normal"], THRESHOLDS["temperature_alert"])
def create_vacuum_chart(df): return create_sensor_chart(df, "presion_vacio_kpa", "Presion de vacio", "kPa", COLORS["verde"], THRESHOLDS["vacuum_normal"], THRESHOLDS["vacuum_alert"], reverse=True)

def create_risk_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["indice_riesgo"], mode="lines+markers", name="IR", line=dict(color=COLORS["amarillo"], width=3), fill="tozeroy", fillcolor="rgba(245,166,35,0.10)", marker=dict(size=4)))
    fig.add_hline(y=40, line_dash="dash", line_color=COLORS["amarillo"], line_width=2, annotation_text="Alerta", annotation_position="top right", annotation_font_color=COLORS["amarillo"], annotation_font_size=11)
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["rojo"], line_width=2, annotation_text="Critico", annotation_position="top right", annotation_font_color=COLORS["rojo"], annotation_font_size=11)
    fig.update_layout(
        title=dict(text="Indice de riesgo", font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")),
        template="plotly_white", paper_bgcolor="rgba(255,255,255,0.95)", plot_bgcolor="rgba(255,255,255,0.95)", margin=dict(l=20, r=20, t=52, b=20),
        xaxis=dict(title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)), showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10), tickangle=-45),
        yaxis=dict(title=dict(text="IR", font=dict(color=COLORS["texto_oscuro"], size=12)), range=[0, 100], showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10)),
        hovermode="x unified", height=280, font=dict(color=COLORS["texto_oscuro"], family="Arial", size=12)
    )
    return fig

# ============================================================================
# BASE DE DATOS
# ============================================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (
        ot_id TEXT PRIMARY KEY,
        asset_name TEXT NOT NULL,
        tag TEXT,
        ubicacion TEXT,
        alert_id TEXT,
        description TEXT,
        prioridad TEXT NOT NULL DEFAULT 'P2',
        tipo TEXT DEFAULT 'Correctivo',
        responsable TEXT,
        creation_date TEXT NOT NULL,
        due_date TEXT,
        estimated_hours REAL DEFAULT 2.0,
        status TEXT NOT NULL DEFAULT 'Pendiente',
        start_time TEXT,
        end_time TEXT,
        hallazgos TEXT,
        acciones TEXT,
        repuestos TEXT,
        evidencia TEXT,
        firma_operario TEXT,
        firma_supervisor TEXT,
        tiempo_real_horas REAL,
        created_by TEXT,
        updated_at TEXT
    )""")
    
    c.execute("PRAGMA table_info(work_orders)")
    existing_columns = [row[1] for row in c.fetchall()]
    
    columns_to_add = {
        'tag': 'TEXT',
        'ubicacion': 'TEXT',
        'prioridad': "TEXT NOT NULL DEFAULT 'P2'",
        'tipo': "TEXT DEFAULT 'Correctivo'",
        'responsable': 'TEXT',
        'due_date': 'TEXT',
        'estimated_hours': 'REAL DEFAULT 2.0',
        'start_time': 'TEXT',
        'end_time': 'TEXT',
        'hallazgos': 'TEXT',
        'acciones': 'TEXT',
        'repuestos': 'TEXT',
        'evidencia': 'TEXT',
        'firma_operario': 'TEXT',
        'firma_supervisor': 'TEXT',
        'tiempo_real_horas': 'REAL',
        'created_by': 'TEXT',
        'updated_at': 'TEXT'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                c.execute(f"ALTER TABLE work_orders ADD COLUMN {col_name} {col_type}")
                logger.info(f"Agregada columna {col_name} a work_orders")
            except Exception as e:
                logger.error(f"Error agregando columna {col_name}: {e}")
    
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ot_id TEXT NOT NULL,
        asset_name TEXT,
        component TEXT NOT NULL,
        decision TEXT NOT NULL,
        result TEXT,
        mass_conserved_kg REAL DEFAULT 0,
        mass_discarded_kg REAL DEFAULT 0,
        costo_reparacion_eur REAL DEFAULT 0,
        costo_reemplazo_nuevo_eur REAL DEFAULT 0,
        vida_util_extendida_horas REAL DEFAULT 0,
        co2_evitado_kg REAL DEFAULT 0,
        disponibilidad_post_reparacion_pct REAL DEFAULT 0,
        tiempo_entre_fallas_reparado_horas REAL DEFAULT 0,
        nivel_reparacion INTEGER DEFAULT 0,
        fabricante_original TEXT,
        garantia_reparacion_meses INTEGER DEFAULT 0,
        recorded_date TEXT NOT NULL,
        recorded_by TEXT,
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
    "step_speed": 1, "production_rate": 85.5, "groq_api_key": "",
    "knowledge_base": [], "kb_loaded": False, "use_test_data": True
}
for k, v in sd.items():
    if k not in st.session_state:
        st.session_state[k] = v

apply_custom_styles()

if not st.session_state.get("kb_loaded", False):
    with st.spinner("Cargando base de conocimiento PDF..."):
        load_knowledge_base()

# ============================================================================
# SIDEBAR CON CHATBOT LETZY COMPACTO
# ============================================================================

with st.sidebar:
    # Header compacto
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:5px; padding-bottom:5px; border-bottom:1px solid #e8ecf1;">
        {render_letzy("35px")}
        <div>
            <h4 style="margin:0; color:#1a5fa8; font-size:1rem;">Letzy</h4>
            <p style="margin:0; color:#5a6b7c; font-size:0.7rem;">Asistente de Mantenimiento</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Modo IA compacto
    ai_mode = st.selectbox(
        "Modo:",
        options=["rag", "fallback"],
        format_func=lambda x: "IA (PDF)" if x == "rag" else "Rapido",
        index=0 if st.session_state.get("groq_api_key", "") else 1,
        key="ai_mode_selector_sidebar",
        disabled=not st.session_state.get("kb_loaded", False),
        label_visibility="collapsed"
    )
    
    if ai_mode == "rag" and not st.session_state.get("groq_api_key", ""):
        st.session_state["groq_api_key"] = st.text_input("API Key Groq", type="password", key="groq_key_side", placeholder="API Key aqui")

    # Contenedor de chat con altura REDUCIDA
    chat_history = st.session_state.get("floating_chat_history", [])
    
    chat_container = st.container(height=250)  # Reducido de 400 a 250
    with chat_container:
        if not chat_history:
            with st.chat_message("assistant", avatar=LETZY_BASE64):
                st.markdown("**Hola! Soy Letzy.** En que puedo ayudarte?")
        
        for msg in chat_history[-8:]:  # Solo últimos 8 mensajes
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar=LETZY_BASE64):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user"):
                    st.markdown(msg["content"])

    # Botones rápidos en 2 columnas compactas
    st.markdown("**Consultas rapidas:**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Estado actual", key="sq1", use_container_width=True):
            process_floating_query("Estado actual", ai_mode)
        if st.button("Generar OT", key="sq2", use_container_width=True):
            process_floating_query("Generar orden de trabajo", ai_mode)
    with c2:
        if st.button("Alta vibracion", key="sq3", use_container_width=True):
            process_floating_query("Que causa alta vibracion?", ai_mode)
        if st.button("KPIs", key="sq4", use_container_width=True):
            process_floating_query("Cuales son los KPIs?", ai_mode)
            
    # Input de chat (sin divider antes)
    ui = st.chat_input("Escribe a Letzy...", key="chat_input_sidebar")
    if ui:
        process_floating_query(ui, ai_mode)
        
    if st.button("Limpiar chat", key="clear_chat_side", use_container_width=True):
        st.session_state["floating_chat_history"] = []

# ============================================================================
# HEADER CON BOTON DE DOCUMENTOS
# ============================================================================

st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:10px; padding:10px 0;">
    <div style="display:flex; align-items:center; gap:20px;">
        {render_logo("180px")}
        <div>
            <p style="margin:0; color:{COLORS['amarillo']}; font-size:1.5rem; font-weight:700;">Mantenimiento Inteligente + Economia Circular</p>
        </div>
    </div>
    <div>
        <a href="https://drive.google.com/drive/folders/1alITCWZz7CxRgumUUw_kwtmaW5oNPGNI?usp=drive_link" target="_blank" class="doc-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            Documentos
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

col_mode1, col_mode2 = st.columns([3, 1])
with col_mode1:
    st.caption("Seleccione el modo de datos para la demostracion")
with col_mode2:
    use_test_data = st.checkbox("Usar datos de prueba CSV", value=st.session_state.get("use_test_data", True), key="use_test_data_checkbox")
    st.session_state["use_test_data"] = use_test_data

tabs = st.tabs(["Monitoreo", "Diagnostico", "Ordenes de Trabajo", "Impacto Circular", "KPIs"])

asset_name = st.selectbox("Selector de activo", list(ASSETS.keys()), label_visibility="collapsed")
st.caption(f"Tag: {ASSETS[asset_name]['tag']} | Criticidad: {ASSETS[asset_name]['criticality']}")

# ============================================================================
# SIMULACION
# ============================================================================

if st.session_state.get("use_test_data", True):
    DF_FULL = load_test_data_from_csv()
    if DF_FULL is None:
        st.warning("No se encontro el archivo CSV de prueba. Usando datos sinteticos.")
        DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
        st.session_state["step_speed"] = 3
        st.info("Modo: Datos Sinteticos | Velocidad: 3 registros por segundo")
    else:
        st.session_state["step_speed"] = 1
        st.info(f"Modo: Datos CSV | Velocidad: 1 registro cada 10 segundos | Total: {len(DF_FULL)} registros")
else:
    DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
    st.session_state["step_speed"] = 3
    st.info("Modo: Datos Sinteticos | Velocidad: 3 registros por segundo")

max_idx = len(DF_FULL)
st.session_state["sim_idx"] = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    if HAS_AUTOREFRESH:
        refresh_interval = 10000 if st.session_state.get("use_test_data", True) else 1000
        st_autorefresh(interval=refresh_interval, key="tm_live")
    st.session_state["sim_idx"] = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)
elif st.session_state.sim_idx >= max_idx:
    st.session_state["sim_idx"] = 1

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state["latest_row"] = latest
st.session_state["asset_name"] = asset_name

current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state["auto_chat_triggered"] = True
    if current_estado == "Critico":
        play_critical_alarm(f"{latest['fecha_hora']}-critical")
    else:
        play_observation_alarm(f"{latest['fecha_hora']}-alert")
    
    fault_desc = latest.get('fault_description', '')
    if pd.isna(fault_desc):
        fault_desc = ''
    alert_msg = f"Hola! Soy Letzy. Se ha detectado un estado {current_estado} en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. {fault_desc}. Se requiere atencion inmediata. En que puedo ayudarte?"
    
    if "floating_chat_history" not in st.session_state:
        st.session_state["floating_chat_history"] = []
    st.session_state["floating_chat_history"].append({"role": "assistant", "content": alert_msg})

st.session_state["previous_estado"] = current_estado

if latest["estado"] in ["Alerta", "Critico"]:
    ek = f"{latest['fecha_hora']}-{latest['estado']}"
    if st.session_state.last_order_event != ek:
        new_ot = create_work_order_obj(latest, asset_name, source="Automatica por alarma")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot["ot_id"],))
        if not c.fetchone():
            c.execute("""INSERT INTO work_orders 
                (ot_id, asset_name, tag, ubicacion, alert_id, description, prioridad, 
                 tipo, responsable, creation_date, estimated_hours, status, created_by, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_ot["ot_id"], new_ot["asset_name"], 
                 ASSETS.get(new_ot["asset_name"], {}).get("tag", "N/A"),
                 "Planta Principal",
                 new_ot["alert_id"], new_ot["description"], new_ot["priority"],
                 "Correctivo", new_ot["responsible"], new_ot["creation_date"],
                 2.0, new_ot["status"], new_ot["created_by"], datetime.now().isoformat()))
            conn.commit()
            
            # === NOTIFICACIONES ===
            if new_ot["priority"] == "P0":
                alarms_list = get_alarms(latest)
                if alarms_list:
                    level, param, valor = alarms_list[0]
                    threshold = THRESHOLDS.get("vibration_alert", 7.1)
                    notify_critical_alarm(
                        asset_name=asset_name,
                        parameter=param,
                        value=valor,
                        threshold=threshold,
                        ir=latest['indice_riesgo'],
                        ot_id=new_ot["ot_id"],
                        responsable=new_ot["responsible"]
                    )
            
            notify_new_ot(new_ot)
            logger.info(f"OT creada y notificada: {new_ot['ot_id']}")
        
        conn.close()
        st.session_state["last_order_event"] = ek

# ============================================================================
# TAB 1: MONITOREO
# ============================================================================

with tabs[0]:
    statuses = variable_status(latest)
    def get_status_color(status): return COLORS["verde"] if status == "Normal" else COLORS["amarillo"] if status == "Alerta" else COLORS["rojo"]
    def get_text_color(status): return "#ffffff"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sc = get_status_color(statuses["Vibracion"])
        st.markdown(f"""<div class="metric-card status-{statuses['Vibracion'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Vibracion'])};margin-bottom:8px;">VIBRACION RMS</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Vibracion'])};">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Vibracion'])};font-weight:bold;">{statuses['Vibracion'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Vibracion'])};margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['vibration_normal']} / {THRESHOLDS['vibration_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vibration_chart(DF), use_container_width=True)
    
    with col2:
        sc = get_status_color(statuses["Temperatura"])
        st.markdown(f"""<div class="metric-card status-{statuses['Temperatura'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Temperatura'])};margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Temperatura'])};">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">C</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Temperatura'])};font-weight:bold;">{statuses['Temperatura'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Temperatura'])};margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['temperature_normal']} / {THRESHOLDS['temperature_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_temperature_chart(DF), use_container_width=True)
    
    with col3:
        sc = get_status_color(statuses["Presion de vacio"])
        st.markdown(f"""<div class="metric-card status-{statuses['Presion de vacio'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Presion de vacio'])};margin-bottom:8px;">PRESION DE VACIO</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Presion de vacio'])};">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Presion de vacio'])};font-weight:bold;">{statuses['Presion de vacio'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Presion de vacio'])};margin-top:8px;opacity:0.9;">Mas negativo = mejor</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vacuum_chart(DF), use_container_width=True)
    
    with col4:
        ec = get_status_color(latest["estado"])
        st.markdown(f"""<div class="metric-card status-{latest['estado'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(latest['estado'])};margin-bottom:8px;">ESTADO GLOBAL</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(latest['estado'])};">{latest['estado'].upper()}</div>
            <div style="font-size:1.1rem;color:{get_text_color(latest['estado'])};">IR: {latest['indice_riesgo']:.1f}/100</div>
            <div style="font-size:0.8rem;color:{get_text_color(latest['estado'])};margin-top:8px;opacity:0.9;">Avance: {st.session_state.sim_idx}/{max_idx}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_risk_chart(DF), use_container_width=True)
    
    alarms = get_alarms(latest)
    if alarms:
        st.markdown(f"<h3 style='margin-top:20px;color:{COLORS['texto_oscuro']};'>Alarmas Activas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            ac = "alarm-critical" if level == "Critico" else ""
            icon = "[!]" if level == "Critico" else "[*]"
            color = COLORS["rojo"] if level == "Critico" else COLORS["amarillo"]
            st.markdown(f"""<div class="alarm-banner {ac}">
                <div style="font-weight:bold;font-size:1.1rem;color:{color};">{icon} {level}: {name}</div>
                <div style="margin-top:5px;">{name} fuera de rango: <strong>{value}</strong></div>
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
            if name == "Vibracion": st.markdown("- **Posible desgaste de rodamientos**, desalineacion o lubricacion deficiente.")
            elif name == "Temperatura": st.markdown("- **Posible friccion interna**, lubricacion deficiente o sobrecarga.")
            elif name == "Presion de vacio": st.markdown("- **Posible fuga en linea**, deterioro de sellos o restriccion en succion.")
            elif name == "Corriente del motor": st.markdown("- **Sobrecarga electrica**, posible falla en devanado o bloqueo mecanico.")
            else: st.markdown(f"- **Falla detectada**: {value}")
        st.markdown("<h3>Pasos Sugeridos</h3>", unsafe_allow_html=True)
        st.markdown("1. Verificar lectura con instrumento calibrado\n2. Inspeccionar visualmente el componente\n3. Revisar manual del fabricante\n4. Comprobar operacion segura\n5. Evaluar necesidad de repuesto")
        accion = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT Prioridad 0"
        st.markdown(f"<div style='background:{COLORS['blanco']};padding:15px;border-radius:12px;margin-top:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);'><strong>Accion Inmediata:</strong> {accion}</div>", unsafe_allow_html=True)
    else:
        st.success("Sin alarmas activas. Condicion normal.")
    
    if st.button("Generar Orden de Trabajo", use_container_width=True, type="primary"):
        ot = create_work_order_obj(latest, asset_name, source="Manual desde diagnostico")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (ot["ot_id"],))
        if not c.fetchone():
            c.execute("""INSERT INTO work_orders (ot_id, asset_name, tag, ubicacion, alert_id, description, prioridad, tipo, responsable, creation_date, estimated_hours, status, created_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ot["ot_id"], ot["asset_name"], ASSETS.get(ot["asset_name"], {}).get("tag", "N/A"), "Planta Principal", ot["alert_id"], ot["description"], ot["priority"], "Correctivo", ot["responsible"], ot["creation_date"], 2.0, ot["status"], ot["created_by"], datetime.now().isoformat()))
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
    all_orders = [dict(row) for row in c.fetchall()]
    
    st.markdown("<h3>Crear Nueva Orden de Trabajo</h3>", unsafe_allow_html=True)
    
    with st.form("nueva_ot_form", clear_on_submit=True):
        col_n1, col_n2 = st.columns(2)
        
        with col_n1:
            nuevo_activo = st.selectbox("Activo:", list(ASSETS.keys()), key="nuevo_activo_ot")
            nueva_prioridad = st.selectbox("Prioridad:", ["P0", "P1", "P2"], key="nueva_prioridad_ot")
            nuevo_tipo = st.selectbox("Tipo:", ["Correctivo", "Preventivo", "Predictivo"], key="nuevo_tipo_ot")
        
        with col_n2:
            nuevo_responsable = st.selectbox("Responsable:", ["Dario Minan", "Jordy Sernaque", "Sin asignar"], key="nuevo_resp_ot")
            nueva_ubicacion = st.text_input("Ubicacion:", "Planta Principal", key="nueva_ubicacion_ot")
            horas_estimadas = st.number_input("Horas estimadas:", min_value=0.5, max_value=24.0, value=2.0, step=0.5, key="nueva_horas_ot")
        
        nueva_descripcion = st.text_area("Descripcion del problema:", key="nueva_desc_ot")
        nuevas_tareas = st.text_area("Tareas a realizar (una por linea):", key="nueva_tareas_ot")
        
        submitted = st.form_submit_button("Crear OT", use_container_width=True, type="primary")
        
        if submitted:
    ts = datetime.now().strftime("%Y%m%d%H%M")
    new_ot_id = f"OT-{ts}-{nueva_prioridad}"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Verificar si la OT ya existe
        c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot_id,))
        if c.fetchone():
            st.info(f"La OT {new_ot_id} ya existe")
        else:
           if latest["estado"] in ["Alerta", "Critico"]:
    ek = f"{latest['fecha_hora']}-{latest['estado']}"
    if st.session_state.last_order_event != ek:
        new_ot = create_work_order_obj(latest, asset_name, source="Automatica por alarma")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot["ot_id"],))
            if not c.fetchone():
                # Insertar solo columnas básicas
                c.execute("""INSERT INTO work_orders 
                    (ot_id, asset_name, description, prioridad, responsable, 
                     creation_date, status, created_by, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_ot["ot_id"], new_ot["asset_name"], new_ot["description"], 
                     new_ot["priority"], new_ot["responsible"], new_ot["creation_date"],
                     new_ot["status"], new_ot["created_by"], datetime.now().isoformat()))
                conn.commit()
                
                # Notificaciones
                if new_ot["priority"] == "P0":
                    alarms_list = get_alarms(latest)
                    if alarms_list:
                        level, param, valor = alarms_list[0]
                        threshold = THRESHOLDS.get("vibration_alert", 7.1)
                        notify_critical_alarm(
                            asset_name=asset_name,
                            parameter=param,
                            value=valor,
                            threshold=threshold,
                            ir=latest['indice_riesgo'],
                            ot_id=new_ot["ot_id"],
                            responsable=new_ot["responsible"]
                        )
                
                notify_new_ot(new_ot)
                logger.info(f"OT creada y notificada: {new_ot['ot_id']}")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error creando OT automática: {e}")
            if 'conn' in locals():
                conn.close()
        
        st.session_state["last_order_event"] = ek

# ============================================================================
# TAB 4: IMPACTO CIRCULAR
# ============================================================================

with tabs[3]:
    st.markdown("<h2>Panel de Impacto Circular</h2>", unsafe_allow_html=True)
    st.markdown("Registro de decisiones de mantenimiento y su impacto en la conservacion de recursos")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""SELECT * FROM circular_interventions 
                 ORDER BY recorded_date DESC""")
    interventions = [dict(row) for row in c.fetchall()]
    conn.close()
    
    if interventions:
        df_interventions = pd.DataFrame(interventions)
        
        total_intervenciones = len(df_interventions)
        masa_total = df_interventions['mass_conserved_kg'].sum() + df_interventions['mass_discarded_kg'].sum()
        masa_conservada = df_interventions['mass_conserved_kg'].sum()
        masa_descartada = df_interventions['mass_discarded_kg'].sum()
        
        tasa_circularidad = (masa_conservada / masa_total * 100) if masa_total > 0 else 0
        
        reparados = len(df_interventions[df_interventions['result'].isin(['Reparado', 'Reutilizado'])])
        tasa_reparacion = (reparados / total_intervenciones * 100) if total_intervenciones > 0 else 0
        
        costo_total_reparacion = df_interventions['costo_reparacion_eur'].sum()
        costo_total_reemplazo = df_interventions['costo_reemplazo_nuevo_eur'].sum()
        ahorro_total = costo_total_reemplazo - costo_total_reparacion
        roi_circular = ((ahorro_total - costo_total_reparacion) / costo_total_reparacion * 100) if costo_total_reparacion > 0 else 0
        
        co2_total_evitado = df_interventions['co2_evitado_kg'].sum()
        arboles_equivalentes = co2_total_evitado / 22
        autos_retirados = co2_total_evitado / 4600
        
        vida_util_total = df_interventions['vida_util_extendida_horas'].sum()
        
        if 'disponibilidad_post_reparacion_pct' in df_interventions.columns:
            avg_disponibilidad = df_interventions['disponibilidad_post_reparacion_pct'].mean()
        else:
            avg_disponibilidad = 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Tasa de Circularidad",
                value=f"{tasa_circularidad:.1f}%",
                delta=f"{masa_conservada:.0f} kg conservados",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                label="CO2 Evitado",
                value=f"{co2_total_evitado:.0f} kg",
                delta=f"Equivalente a {arboles_equivalentes:.0f} arboles/año",
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                label="Ahorro Total",
                value=f"EUR {ahorro_total:,.0f}",
                delta=f"ROI: {roi_circular:.0f}%",
                delta_color="normal" if ahorro_total > 0 else "inverse"
            )
        
        with col4:
            st.metric(
                label="Tasa de Exito Reparaciones",
                value=f"{avg_disponibilidad:.1f}%" if avg_disponibilidad > 0 else "N/A",
                delta=f"{reparados} reparaciones",
                delta_color="normal"
            )
        
        st.divider()
        
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        
        with col_f1:
            asset_filter = st.selectbox(
                "Filtrar por activo:",
                options=["Todos"] + list(ASSETS.keys()),
                key="circular_asset_filter"
            )
        
        with col_f2:
            date_filter = st.selectbox(
                "Periodo:",
                options=["Todos", "Ultimos 30 dias", "Ultimos 90 dias", "Ultimo año"],
                key="circular_date_filter"
            )
        
        with col_f3:
            decision_filter = st.multiselect(
                "Tipo de decision:",
                options=["Inspeccion", "Reparacion", "Reemplazo Parcial", "Reemplazo Total"],
                default=["Inspeccion", "Reparacion", "Reemplazo Parcial", "Reemplazo Total"],
                key="circular_decision_filter"
            )
        
        df_filtered = df_interventions.copy()
        
        if asset_filter != "Todos":
            df_filtered = df_filtered[df_filtered['asset_name'] == asset_filter]
        
        if decision_filter:
            df_filtered = df_filtered[df_filtered['decision'].isin(decision_filter)]
        
        if date_filter != "Todos":
            df_filtered['recorded_date'] = pd.to_datetime(df_filtered['recorded_date'])
            today = datetime.now()
            if date_filter == "Ultimos 30 dias":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=30)]
            elif date_filter == "Ultimos 90 dias":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=90)]
            elif date_filter == "Ultimo año":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=365)]
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Tendencia Mensual")
            
            if not df_filtered.empty:
                df_filtered['mes'] = pd.to_datetime(df_filtered['recorded_date']).dt.to_period('M')
                df_mensual = df_filtered.groupby('mes').agg({
                    'mass_conserved_kg': 'sum',
                    'mass_discarded_kg': 'sum',
                    'costo_reparacion_eur': 'sum',
                    'costo_reemplazo_nuevo_eur': 'sum'
                }).reset_index()
                
                fig_tendencia = go.Figure()
                fig_tendencia.add_trace(go.Scatter(
                    x=[str(m) for m in df_mensual['mes']],
                    y=df_mensual['mass_conserved_kg'],
                    mode='lines+markers',
                    name='Masa Conservada',
                    line=dict(color='#8bc34a', width=3),
                    fill='tozeroy'
                ))
                fig_tendencia.add_trace(go.Scatter(
                    x=[str(m) for m in df_mensual['mes']],
                    y=df_mensual['mass_discarded_kg'],
                    mode='lines+markers',
                    name='Masa Descartada',
                    line=dict(color='#d32f2f', width=3),
                    fill='tozeroy'
                ))
                fig_tendencia.update_layout(
                    height=350,
                    xaxis_title="Mes",
                    yaxis_title="Masa (kg)",
                    hovermode='x unified',
                    showlegend=True
                )
                st.plotly_chart(fig_tendencia, use_container_width=True)
        
        with col_g2:
            st.subheader("Distribucion por Decision")
            
            if not df_filtered.empty:
                decision_counts = df_filtered['decision'].value_counts()
                
                colors = ['#1a5fa8', '#8bc34a', '#f5a623', '#d32f2f']
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=decision_counts.index,
                    values=decision_counts.values,
                    hole=.3,
                    marker=dict(colors=colors)
                )])
                fig_pie.update_layout(
                    height=350,
                    showlegend=True,
                    annotations=[dict(
                        text=f'Total:<br>{len(df_filtered)}',
                        x=0.5, y=0.5,
                        font_size=20,
                        showarrow=False
                    )]
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        col_g3, col_g4 = st.columns(2)
        
        with col_g3:
            st.subheader("Top 5 Componentes Mas Circulares")
            
            if not df_filtered.empty:
                df_componentes = df_filtered.groupby('component').agg({
                    'mass_conserved_kg': 'sum',
                    'id': 'count'
                }).reset_index()
                df_componentes.columns = ['Componente', 'Masa Conservada (kg)', 'Intervenciones']
                df_top5 = df_componentes.nlargest(5, 'Masa Conservada (kg)')
                
                fig_barras = go.Figure()
                fig_barras.add_trace(go.Bar(
                    x=df_top5['Masa Conservada (kg)'],
                    y=df_top5['Componente'],
                    orientation='h',
                    marker=dict(color='#1a5fa8'),
                    text=df_top5['Intervenciones'],
                    textposition='outside',
                    hovertemplate='%{y}<br>Masa: %{x:.1f} kg<br>Intervenciones: %{text}<extra></extra>'
                ))
                fig_barras.update_layout(
                    height=350,
                    xaxis_title="Masa Conservada (kg)",
                    showlegend=False
                )
                st.plotly_chart(fig_barras, use_container_width=True)
        
        with col_g4:
            st.subheader("Ahorro Acumulado")
            
            if not df_filtered.empty and 'costo_reemplazo_nuevo_eur' in df_filtered.columns:
                df_filtered_sorted = df_filtered.sort_values('recorded_date')
                df_filtered_sorted['ahorro_acumulado'] = (
                    df_filtered_sorted['costo_reemplazo_nuevo_eur'].cumsum() - 
                    df_filtered_sorted['costo_reparacion_eur'].cumsum()
                )
                
                fig_area = go.Figure()
                fig_area.add_trace(go.Scatter(
                    x=df_filtered_sorted['recorded_date'],
                    y=df_filtered_sorted['ahorro_acumulado'],
                    mode='lines',
                    fill='tozeroy',
                    line=dict(color='#8bc34a', width=3),
                    name='Ahorro Acumulado'
                ))
                fig_area.update_layout(
                    height=350,
                    xaxis_title="Fecha",
                    yaxis_title="Ahorro (EUR)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_area, use_container_width=True)
        
        st.divider()
        
        st.subheader("Insights y Recomendaciones")
        
        if not df_filtered.empty:
            for componente in df_filtered['component'].unique():
                df_comp = df_filtered[df_filtered['component'] == componente]
                
                tasa_exito = len(df_comp[df_comp['result'].isin(['Reparado', 'Reutilizado'])]) / len(df_comp) * 100
                
                if tasa_exito >= 80:
                    st.success(f"**{componente}**: {tasa_exito:.0f}% tasa de reparacion exitosa - **Recomendacion**: Priorizar reparacion sobre reemplazo")
                elif tasa_exito <= 40:
                    st.warning(f"**{componente}**: Solo {tasa_exito:.0f}% de exito en reparacion - **Recomendacion**: Evaluar cambio de tecnologia o mantener stock de repuestos")
                
                if 'costo_reparacion_eur' in df_comp.columns and 'costo_reemplazo_nuevo_eur' in df_comp.columns:
                    costo_rep = df_comp['costo_reparacion_eur'].sum()
                    costo_rep_new = df_comp['costo_reemplazo_nuevo_eur'].sum()
                    ahorro = costo_rep_new - costo_rep
                    pct_ahorro = (ahorro / costo_rep_new * 100) if costo_rep_new > 0 else 0
                    
                    if ahorro > 0:
                        st.info(f"**{componente}**: Inversion reparacion EUR {costo_rep:,.0f} vs Reemplazo EUR {costo_rep_new:,.0f} = **Ahorro EUR {ahorro:,.0f} ({pct_ahorro:.0f}%)**")
        
        st.divider()
        st.subheader("Benchmarks de Desempeño")
        
        col_b1, col_b2, col_b3 = st.columns(3)
        
        with col_b1:
            st.metric(
                label="Tu Tasa de Circularidad",
                value=f"{tasa_circularidad:.1f}%",
                delta="Meta: >70% (Industria clase mundial)",
                delta_color="normal" if tasa_circularidad >= 70 else "inverse"
            )
        
        with col_b2:
            st.metric(
                label="CO2 Evitado vs Meta",
                value=f"{co2_total_evitado:.0f} kg",
                delta=f"Equivalente a {arboles_equivalentes:.0f} arboles",
                delta_color="normal"
            )
        
        with col_b3:
            st.metric(
                label="Alineacion SDG 12",
                value="Produccion Responsable",
                delta="Objetivo: Reduccion 30% residuos",
                delta_color="normal"
            )
        
        st.divider()
        st.subheader("Registro Detallado de Intervenciones")
        
        cols_to_show = [
            'recorded_date', 'ot_id', 'asset_name', 'component', 'decision', 
            'result', 'mass_conserved_kg', 'mass_discarded_kg'
        ]
        
        if 'costo_reparacion_eur' in df_filtered.columns:
            cols_to_show.append('costo_reparacion_eur')
        if 'costo_reemplazo_nuevo_eur' in df_filtered.columns:
            cols_to_show.append('costo_reemplazo_nuevo_eur')
        if 'co2_evitado_kg' in df_filtered.columns:
            cols_to_show.append('co2_evitado_kg')
        
        df_display = df_filtered[cols_to_show].copy()
        
        column_names = {
            'recorded_date': 'Fecha',
            'ot_id': 'OT ID',
            'asset_name': 'Activo',
            'component': 'Componente',
            'decision': 'Decision',
            'result': 'Resultado',
            'mass_conserved_kg': 'Masa Conservada (kg)',
            'mass_discarded_kg': 'Masa Descartada (kg)',
            'costo_reparacion_eur': 'Costo Reparacion (EUR)',
            'costo_reemplazo_nuevo_eur': 'Costo Reemplazo (EUR)',
            'co2_evitado_kg': 'CO2 Evitado (kg)'
        }
        df_display = df_display.rename(columns=column_names)
        
        st.dataframe(
            df_display.sort_values('Fecha', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        csv = df_display.to_csv(index=False, sep=';').encode('utf-8')
        st.download_button(
            label="Exportar a CSV",
            data=csv,
            file_name=f"impacto_circular_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    else:
        st.info("No hay intervenciones registradas. Complete ordenes de trabajo para registrar el impacto circular.")
        
        st.markdown("""
        ### Como registrar intervenciones?
        
        1. **Complete una Orden de Trabajo** en el modulo correspondiente
        2. **Al cerrar la OT**, seleccione:
           - Componente intervenido
           - Decision tomada (Inspeccion/Reparacion/Reemplazo)
           - Masa conservada y descartada
           - Costos asociados
           - Vida util extendida
        3. **El sistema calculara automaticamente**:
           - Tasa de circularidad
           - CO2 evitado
           - Ahorro economico
           - ROI de la economia circular
        """)

# ============================================================================
# TAB 5: KPIs
# ============================================================================

with tabs[4]:
    st.markdown("<h2 style='text-align:center;'>KPIs e Indicadores</h2>", unsafe_allow_html=True)
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
    
    col_center1, col_center2, col_center3 = st.columns([1, 3, 1])
    with col_center2:
        st.dataframe(pd.DataFrame({"KPI": list(kpis.keys()), "Valor": list(kpis.values())}), use_container_width=True, hide_index=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("Tech Maint Pro | Prototipo profesional SeedTech 2026 | Los umbrales son referenciales")
