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

# API KEY DE GROQ INTEGRADA
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
# CARGA DE IMAGENES
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
LETZY_BASE64 = load_image_as_base64(LETZY_PATH, "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI5MCIgaGVpZ2h0PSI5MCI+PGNpcmNsZSBjeD0iNDUiIGN5PSI0NSIgcj0iNDIiIGZpbGw9IiMxYTVmYTgiLz48dGV4dCB4PSI1MCUiIHk9IjU1JSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0id2hpdGUiIGZvbnQtc2l6ZT0iMjAiIGZvbnQtd2VpZ2h0PSJib2xkIj5MPC90ZXh0Pjwvc3ZnPg==")

def render_logo(size="180px"):
    return f'<img src="{LOGO_BASE64}" style="width:{size}; height:auto; display:inline-block;" />'
# Agrega esto después de LETZY_BASE64 y antes de render_letzy

LOGO_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxODAiIGhlaWdodD0iMTgwIj48cmVjdCB3aWR0aD0iMTgwIiBoZWlnaHQ9IjE4MCIgZmlsbD0iIzFhNWZhOCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSIgZm9udC1zaXplPSIyMCIgZm9udC13ZWlnaHQ9ImJvbGQiPlRFQ0ggTUFJTlQ8L3RleHQ+PHRleHQgeD0iNTAlIiB5PSI3MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiNmNWE2MjMiIGZvbnQtc2l6ZT0iMjAiIGZvbnQtd2VpZ2h0PSJib2xkIj5QUk88L3RleHQ+PC9zdmc+"

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
# ALARMAS SONORAS VIA JAVASCRIPT
# ============================================================================

def play_critical_alarm(event_id):
    if st.session_state.get("last_beep_event") == event_id:
        return
    st.session_state["last_beep_event"] = event_id
    
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
    
    .stSelectbox {{ margin-bottom: 8px; }}
    .stDataFrame {{ margin: 0 auto; }}
    
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
                'Timestamp': 'fecha_hora', 'Time_Seconds': 'time_seconds',
                'Vacuum_Pressure_mbar': 'vacuum_mbar', 'Oil_Temperature_C': 'temperatura_c',
                'Vibration_mm_s': 'vibracion_rms_mm_s', 'Motor_Current_A': 'motor_current_a',
                'Status': 'status', 'Fault_Description': 'fault_description'
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
        vibration += np.linspace(0, 4.1, n); temperature += np.linspace(0, 16, n); vacuum += np.linspace(0, 18, n)
    elif scenario == "Condicion critica":
        vibration += np.linspace(1.5, 6, n) + 0.45 * np.sin(t / 3.5)
        temperature += np.linspace(8, 24, n) + 0.9 * np.sin(t / 5)
        vacuum += np.linspace(10, 28, n)
    elif scenario == "Fuga subito":
        step = int(n * 0.55)
        vibration += np.linspace(0, 1.2, n); temperature += np.linspace(0, 5.5, n)
        vacuum[step:] += 18.5; vacuum[step + 12:] += 6
    elif scenario == "Rodamiento degradado":
        vibration += np.linspace(0.4, 5.2, n) + 0.8 * np.maximum(0, np.sin(t / 4))
        temperature += np.linspace(1, 13, n); vacuum += np.linspace(0, 7, n)
    
    df = pd.DataFrame({"fecha_hora": dates, "vibracion_rms_mm_s": np.round(vibration, 3), "temperatura_c": np.round(temperature, 2), "presion_vacio_kpa": np.round(vacuum, 2)})
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
    if 'status' in row and pd.notna(row['status']) and str(row['status']).strip() != 'OK':
        level = 'Critico' if str(row['status']).upper() in ['CRITICAL', 'TRIP'] else 'Alerta'
        desc = str(row.get('fault_description', 'Falla detectada')).strip()
        if not desc or desc.lower() == 'nan': desc = 'Falla detectada'
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
        if s["Vibracion"] != "Normal": alarms.append((s["Vibracion"], "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s"))
        if s["Temperatura"] != "Normal": alarms.append((s["Temperatura"], "Temperatura", f"{row['temperatura_c']:.1f} C"))
        if s["Presion de vacio"] != "Normal": alarms.append((s["Presion de vacio"], "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa"))
    return alarms

def create_work_order_obj(row, asset_name, source="Automatica"):
    alarms = get_alarms(row)
    priority = "P0" if row["estado"] == "Critico" else "P1" if row["estado"] == "Alerta" else "P2"
    responsable = STAFF["tecnico"]["nombre"] if priority in ["P0", "P1"] else STAFF["asesor"]["nombre"]
    symptoms = "; ".join([f"{name}: {value} ({level})" for level, name, value in alarms]) or "Sin alarma critica"
    tasks = []
    if any(a[1] == "Vibracion" for a in alarms): tasks += ["Medir vibracion", "Verificar alineacion"]
    if any(a[1] == "Temperatura" for a in alarms): tasks += ["Revisar lubricacion", "Verificar friccion"]
    if any(a[1] == "Presion de vacio" for a in alarms): tasks += ["Prueba de fugas", "Inspeccionar sellos"]
    if any(a[1] == "Corriente del motor" for a in alarms): tasks += ["Medir corriente", "Revisar devanado", "Verificar carga"]
    if not tasks: tasks = ["Inspeccion rutinaria"]
    
    ts = pd.to_datetime(row["fecha_hora"]).strftime("%Y%m%d%H%M")
    return {
        "ot_id": f"OT-{ts}-{priority}", "asset_name": asset_name, "alert_id": f"ALM-{ts}",
        "description": f"Anomalia: {symptoms}", "priority": priority, "responsible": responsable,
        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "Pendiente", "created_by": source,
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
    return {"MTBF (h)": mtbf, "MTTR (h)": mttr, "Disponibilidad (%)": avail * 100, "Confiabilidad 24h (%)": rel24 * 100, "Cumplimiento PM (%)": pmc * 100, "Backlog (semanas)": bl, "Perdida productiva (t)": pl}

# ============================================================================
# SISTEMA RAG - BASE DE CONOCIMIENTO PDF
# ============================================================================

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        if HAS_FITZ:
            doc = fitz.open(pdf_path)
            for page in doc: text += page.get_text() + "\n"
            doc.close()
        elif HAS_PDF:
            reader = PdfReader(pdf_path)
            for page in reader.pages: text += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
    return text

def chunk_text(text, chunk_size=500, overlap=100):
    chunks, words = [], text.split()
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i+chunk_size]))
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
        text = extract_text_from_pdf(os.path.join(PDF_DIR, pdf_file))
        if text.strip():
            chunks = chunk_text(text, chunk_size=400, overlap=80)
            for idx, chunk in enumerate(chunks):
                kb.append({"doc_id": meta_key or "00", "filename": pdf_file, "category": meta["category"], "tags": meta["tags"], "chunk_idx": idx, "content": chunk, "total_chunks": len(chunks)})
    st.session_state.knowledge_base = kb
    st.session_state.kb_loaded = True
    logger.info(f"Base de conocimiento cargada: {len(kb)} chunks de {len(pdf_files)} documentos")

def search_knowledge_base(query, top_k=5):
    if not st.session_state.get("kb_loaded", False): return []
    kb = st.session_state.knowledge_base
    query_words = set(re.findall(r'\w+', query.lower()))
    scores = []
    for item in kb:
        content_words = set(re.findall(r'\w+', item["content"].lower()))
        tag_words = set(item["tags"])
        score = len(query_words & content_words) + len(query_words & tag_words) * 3
        if score > 0: scores.append((score, item))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scores[:top_k]]

def format_context_for_llm(search_results):
    context_parts, seen_docs = [], set()
    for result in search_results:
        if result["doc_id"] not in seen_docs:
            seen_docs.add(result["doc_id"])
            context_parts.append(f"=== ARCHIVO {result['doc_id']}: {result['filename']} ===\nCategoria: {result['category']}\nTags: {', '.join(result['tags'])}\nContenido:\n{result['content']}")
    return "\n".join(context_parts)

# ============================================================================
# INTEGRACION CON GROQ + RAG
# ============================================================================

def query_groq_with_rag(user_query, latest, asset_name, kpi_values):
    try:
        api_key = GROQ_API_KEY  # Usar la API Key integrada
        
        alarms = get_alarms(latest)
        at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas activas"
        current_context = f"=== ESTADO ACTUAL ===\nActivo: {asset_name}\nEstado: {latest['estado']}\nIR: {latest['indice_riesgo']:.1f}/100\nVibracion: {latest['vibracion_rms_mm_s']:.2f} mm/s\nTemperatura: {latest['temperatura_c']:.1f} C\nVacio: {latest['presion_vacio_kpa']:.1f} kPa\nAlarmas: {at}\n\nKPIs: MTBF: {kpi_values['MTBF (h)']:.1f} h, MTTR: {kpi_values['MTTR (h)']:.1f} h, Disponibilidad: {kpi_values['Disponibilidad (%)']:.2f}%"
        
        search_results = search_knowledge_base(user_query, top_k=8)
        kb_context = format_context_for_llm(search_results)
        full_system_prompt = f"{SYSTEM_PROMPT}\n\n{current_context}\n\n{kb_context}\n\nINSTRUCCION FINAL: Responde basandote EXCLUSIVAMENTE en la informacion proporcionada. Cita siempre la fuente."
        
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
        return f"Error al consultar la IA: {str(e)}"

def chatbot_response_fallback(user_query, latest, asset_name, kpi_values):
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100 | Vibracion {latest['vibracion_rms_mm_s']:.2f} mm/s | Temp {latest['temperatura_c']:.1f} C | Vacio {latest['presion_vacio_kpa']:.1f} kPa"
    alarms = get_alarms(latest)
    at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas"
    
    if any(k in text for k in ["hola", "ayuda", "quiero", "necesito"]):
        return f"Bienvenido a Tech Maint Pro\n\n{sl}\n\nPuedo ayudarte con diagnostico, ordenes de trabajo, AMEF, KPIs e impacto circular."
    if any(k in text for k in ["estado", "riesgo", "condicion", "diagnostico"]):
        na = [a[1] for a in alarms]
        hip = "Posible desgaste de rodamientos o desalineacion." if "Vibracion" in na and "Temperatura" in na else "Posible fuga en linea o deterioro de sellos." if "Presion de vacio" in na else "Posible desalineacion o desgaste de rodamiento." if "Vibracion" in na else "Posible friccion interna o lubricacion deficiente." if "Temperatura" in na else "Condicion normal."
        acc = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT prioritaria"
        return f"Diagnostico\n\n{sl}\n\nAlarmas: {at}\n\nHipotesis: {hip}\n\nAccion: {acc}"
    if any(k in text for k in ["orden", "trabajo", "ot", "generar"]):
        pri = "P0" if latest["estado"] == "Critico" else "P1" if latest["estado"] == "Alerta" else "P2"
        sint = "; ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) or "Sin alarma critica"
        tareas = ["Medir vibracion", "Verificar alineacion"] if any(a[1] == "Vibracion" for a in alarms) else []
        tareas += ["Revisar lubricacion", "Verificar friccion"] if any(a[1] == "Temperatura" for a in alarms) else []
        tareas += ["Prueba de fugas", "Inspeccionar sellos"] if any(a[1] == "Presion de vacio" for a in alarms) else []
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
    if not query or not query.strip(): return
    q = query.strip()
    if "floating_chat_history" not in st.session_state: st.session_state["floating_chat_history"] = []
    st.session_state["floating_chat_history"].append({"role": "user", "content": q})
    
    try:
        kp = calculate_kpis(720, 3, 18, 18, 20, 40, 80, st.session_state.get("production_rate", 85.5))
        latest = st.session_state.get("latest_row", pd.Series())
        asset_name = st.session_state.get("asset_name", "")
        
        if ai_platform == "rag":
            reply = query_groq_with_rag(q, latest, asset_name, kp)
        else:
            reply = chatbot_response_fallback(q, latest, asset_name, kp)
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": f"Error: {e}"})

# ============================================================================
# BASE DE DATOS EXPANDIDA
# ============================================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabla work_orders EXPANDIDA con campos para impacto circular
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
        updated_at TEXT,
        -- CAMPOS NUEVOS PARA IMPACTO CIRCULAR
        componente_afectado TEXT,
        tipo_falla TEXT,
        decision_tecnica TEXT,
        masa_conservada_kg REAL DEFAULT 0,
        masa_descartada_kg REAL DEFAULT 0,
        costo_reparacion REAL DEFAULT 0,
        costo_reemplazo_nuevo REAL DEFAULT 0,
        co2_evitado_kg REAL DEFAULT 0,
        vida_util_extendida_horas REAL DEFAULT 0,
        disponibilidad_post_reparacion_pct REAL DEFAULT 0
    )""")
    
    # Agregar columnas nuevas si no existen
    c.execute("PRAGMA table_info(work_orders)")
    existing_columns = [row[1] for row in c.fetchall()]
    
    new_columns = {
        'componente_afectado': 'TEXT',
        'tipo_falla': 'TEXT',
        'decision_tecnica': 'TEXT',
        'masa_conservada_kg': 'REAL DEFAULT 0',
        'masa_descartada_kg': 'REAL DEFAULT 0',
        'costo_reparacion': 'REAL DEFAULT 0',
        'costo_reemplazo_nuevo': 'REAL DEFAULT 0',
        'co2_evitado_kg': 'REAL DEFAULT 0',
        'vida_util_extendida_horas': 'REAL DEFAULT 0',
        'disponibilidad_post_reparacion_pct': 'REAL DEFAULT 0'
    }
    
    for col_name, col_type in new_columns.items():
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

sd = {"running": True, "sim_idx": 1, "orders": [], "last_order_event": None, "chat_history": [], "theme_mode": "default", "kb_docs": [], "kb_chunks": [], "kb_ready": False, "last_beep_event": None, "floating_chat_open": False, "floating_chat_history": [], "auto_chat_triggered": False, "previous_estado": None, "scenario": "Operacion normal", "seed": 42, "n_hours": 168, "step_speed": 1, "production_rate": 85.5, "groq_api_key": GROQ_API_KEY, "knowledge_base": [], "kb_loaded": False, "use_test_data": True, "audio_enabled": False}
for k, v in sd.items():
    if k not in st.session_state: st.session_state[k] = v

apply_custom_styles()
if not st.session_state.get("kb_loaded", False):
    with st.spinner("Cargando base de conocimiento PDF..."): load_knowledge_base()

# ============================================================================
# SIDEBAR CON CHATBOT LETZY
# ============================================================================

with st.sidebar:
    # Botón para activar audio
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
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 440;
                oscillator.type = 'sine';
                gainNode.gain.value = 0.1;
                oscillator.start();
                setTimeout(() => oscillator.stop(), 100);
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

    ai_mode = st.selectbox("Modo:", options=["rag", "fallback"], format_func=lambda x: "IA (PDF)" if x == "rag" else "Rapido", index=0 if GROQ_API_KEY else 1, key="ai_mode_selector_sidebar", disabled=not st.session_state.get("kb_loaded", False), label_visibility="collapsed")

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
    if st.session_state.get("audio_enabled", False):
        if current_estado == "Critico": play_critical_alarm(f"{latest['fecha_hora']}-critical")
        else: play_observation_alarm(f"{latest['fecha_hora']}-alert")
    
    fault_desc = latest.get('fault_description', '')
    if pd.isna(fault_desc): fault_desc = ''
    alert_msg = f"Hola! Soy Letzy. Se ha detectado un estado {current_estado} en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. {fault_desc}. Se requiere atencion inmediata. En que puedo ayudarte?"
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
                c.execute("""INSERT INTO work_orders (ot_id, asset_name, tag, ubicacion, alert_id, description, prioridad, tipo, responsable, creation_date, estimated_hours, status, created_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_ot["ot_id"], new_ot["asset_name"], ASSETS.get(new_ot["asset_name"], {}).get("tag", "N/A"), "Planta Principal", new_ot["alert_id"], new_ot["description"], new_ot["priority"], "Correctivo", new_ot["responsible"], new_ot["creation_date"], 2.0, new_ot["status"], new_ot["created_by"], datetime.now().isoformat()))
                conn.commit()
                if new_ot["priority"] == "P0":
                    alarms_list = get_alarms(latest)
                    if alarms_list:
                        level, param, valor = alarms_list[0]
                        threshold = THRESHOLDS.get("vibration_alert", 7.1)
                        notify_critical_alarm(asset_name=asset_name, parameter=param, value=valor, threshold=threshold, ir=latest['indice_riesgo'], ot_id=new_ot["ot_id"], responsable=new_ot["responsible"])
                notify_new_ot(new_ot)
                logger.info(f"OT creada y notificada: {new_ot['ot_id']}")
            conn.close()
        except Exception as e:
            logger.error(f"Error creando OT automatica: {e}")
        st.session_state["last_order_event"] = ek

# El resto del código (tabs de monitoreo, diagnóstico, OT, impacto circular, KPIs) permanece igual...
