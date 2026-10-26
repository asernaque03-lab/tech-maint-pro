import base64
import hashlib
import io
import json
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
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import wave
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Dict, List, Tuple
from collections import Counter
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import base64
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
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")

# Crear directorio de uploads si no existe
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

LOGO_BASE64 = load_image_as_base64(LOGO_PATH)
LETZY_BASE64 = load_image_as_base64(LETZY_PATH)

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
# SYSTEM PROMPT PARA LETZY (ACTUALIZADO)
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
9. Si te preguntan por PLAN DE MANTENIMIENTO, indica que el sistema tiene un modulo completo con calendario, filtros y seguimiento
10. Si te preguntan por IMPACTO CIRCULAR, explica que se registra al cerrar OTs con masa conservada/descartada
11. Si la informacion NO esta en los documentos, indicalo claramente.
12. NUNCA inventes datos tecnicos.

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
        server.login(STAFF["asesor"]["email"], "910314782")
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

def notify_maintenance_reminder(plan_task):
    """Enviar recordatorio de mantenimiento programado"""
    asset_name = plan_task.get('asset_name', 'N/A')
    task_desc = plan_task.get('task_description', '')
    scheduled_date = plan_task.get('scheduled_date', '')
    responsable = plan_task.get('responsable', '')
    
    mensaje_telegram = (
        f"<b>[RECORDATORIO DE MANTENIMIENTO]</b>\n\n"
        f"<b>Activo:</b> {asset_name}\n"
        f"<b>Tarea:</b> {task_desc}\n"
        f"<b>Fecha programada:</b> {scheduled_date}\n"
        f"<b>Responsable:</b> {responsable}\n\n"
        f"Por favor confirmar ejecucion."
    )
    
    # Enviar a tecnico y asesor
    send_telegram(STAFF["tecnico"]["telegram_chat_id"], mensaje_telegram)
    send_telegram(STAFF["asesor"]["telegram_chat_id"], mensaje_telegram)

def notify_maintenance_issue(asset_name, issue_description, reporter):
    """Notificar problema o impedimento en mantenimiento a Irina"""
    mensaje_telegram = (
        f"<b>[PROBLEMA/IMPEDIMENTO DE MANTENIMIENTO]</b>\n\n"
        f"<b>Activo:</b> {asset_name}\n"
        f"<b>Reportado por:</b> {reporter}\n"
        f"<b>Descripcion:</b> {issue_description}\n\n"
        f"Se requiere atencion inmediata."
    )
    
    send_telegram(STAFF["gerencia"]["telegram_chat_id"], mensaje_telegram)
    
    cuerpo_email = f"""
    <h2>Problema/Impedimento de Mantenimiento</h2>
    <p><b>Activo:</b> {asset_name}</p>
    <p><b>Reportado por:</b> {reporter}</p>
    <p><b>Descripcion:</b> {issue_description}</p>
    <p>Se requiere atencion inmediata.</p>
    """
    send_email(STAFF["gerencia"]["email"], f"[PROBLEMA] {asset_name} - {issue_description[:50]}", cuerpo_email)

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

def play_notification_sound():
    """Sonido de notificacion suave"""
    st.markdown("""
    <script>
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.frequency.value = 880;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.15;
        oscillator.start();
        setTimeout(() => oscillator.stop(), 150);
    } catch(e) {}
    </script>
    """, unsafe_allow_html=True)

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
    
    .search-box {{
        border: 2px solid {COLORS['azul']};
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 15px;
    }}
    
    .calendar-month {{
        background: {COLORS['azul']};
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
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

def load_maintenance_plan():
    """Cargar plan de mantenimiento desde CSV"""
    try:
        if os.path.exists(PLAN_MTO_PATH):
            df = pd.read_csv(PLAN_MTO_PATH)
            logger.info(f"Plan de mantenimiento cargado: {len(df)} tareas")
            return df
        else:
            logger.warning(f"Archivo plan_de_mto.csv no encontrado: {PLAN_MTO_PATH}")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error cargando plan de mantenimiento: {e}")
        return pd.DataFrame()

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
# GENERACION DE PDF - FORMATO SANIPES
# ============================================================================

def generate_maintenance_pdf(ot_data, photos_before=None, photos_after=None):
    """Generar reporte PDF en formato SANIPES"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor(COLORS['azul']),
        spaceAfter=30
    )
    
    # Header
    elements.append(Paragraph("REPORTE DE MANTENIMIENTO - FORMATO SANIPES", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Informacion general
    data = [
        ['OT ID:', ot_data.get('ot_id', 'N/A')],
        ['Activo:', ot_data.get('asset_name', 'N/A')],
        ['Tag:', ot_data.get('tag', 'N/A')],
        ['Ubicacion:', ot_data.get('ubicacion', 'N/A')],
        ['Fecha Creacion:', ot_data.get('creation_date', 'N/A')],
        ['Responsable:', ot_data.get('responsable', 'N/A')],
        ['Prioridad:', ot_data.get('prioridad', 'N/A')],
        ['Estado:', ot_data.get('status', 'N/A')],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['azul'])),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Descripcion
    elements.append(Paragraph("<b>Descripcion del Problema:</b>", styles['Heading2']))
    elements.append(Paragraph(ot_data.get('description', 'N/A'), styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Acciones realizadas
    if ot_data.get('acciones'):
        elements.append(Paragraph("<b>Acciones Realizadas:</b>", styles['Heading2']))
        elements.append(Paragraph(ot_data.get('acciones', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
    
    # Hallazgos
    if ot_data.get('hallazgos'):
        elements.append(Paragraph("<b>Hallazgos:</b>", styles['Heading2']))
        elements.append(Paragraph(ot_data.get('hallazgos', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
    
    # Impacto Circular
    if ot_data.get('masa_conservada_kg') or ot_data.get('masa_descartada_kg'):
        elements.append(Paragraph("<b>Impacto Circular:</b>", styles['Heading2']))
        circular_data = [
            ['Masa Conservada:', f"{ot_data.get('masa_conservada_kg', 0):.2f} kg"],
            ['Masa Descartada:', f"{ot_data.get('masa_descartada_kg', 0):.2f} kg"],
            ['CO2 Evitado:', f"{ot_data.get('co2_evitado_kg', 0):.2f} kg"],
            ['Costo Reparacion:', f"EUR {ot_data.get('costo_reparacion', 0):.2f}"],
        ]
        circular_table = Table(circular_data, colWidths=[3*inch, 3*inch])
        circular_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLORS['verde'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(circular_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Fotos
    if photos_before or photos_after:
        elements.append(Paragraph("<b>Registro Fotografico:</b>", styles['Heading2']))
        
        if photos_before:
            elements.append(Paragraph("<b>Antes del Mantenimiento:</b>", styles['Heading3']))
            for photo_path in photos_before:
                if os.path.exists(photo_path):
                    try:
                        img = Image(photo_path, width=3*inch, height=2*inch)
                        elements.append(img)
                        elements.append(Spacer(1, 0.1*inch))
                    except:
                        pass
        
        if photos_after:
            elements.append(Paragraph("<b>Despues del Mantenimiento:</b>", styles['Heading3']))
            for photo_path in photos_after:
                if os.path.exists(photo_path):
                    try:
                        img = Image(photo_path, width=3*inch, height=2*inch)
                        elements.append(img)
                        elements.append(Spacer(1, 0.1*inch))
                    except:
                        pass
    
    # Firmas
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("<b>Firmas:</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*inch))
    
    signature_data = [
        ['_________________________', '_________________________'],
        ['Tecnico de Mantenimiento', 'Jefe de Mantenimiento'],
        [f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ''],
    ]
    sig_table = Table(signature_data, colWidths=[3*inch, 3*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
    ]))
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

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
    cache_file = os.path.join(APP_DIR, "kb_cache.json")
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    
    use_cache = False
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            if len(cache_data.get('pdf_files', [])) == len(pdf_files) and len(cache_data.get('kb', [])) > 0:
                use_cache = True
                st.session_state.knowledge_base = cache_data['kb']
                st.session_state.kb_loaded = True
                logger.info("Base de conocimiento cargada desde cache.")
                return
        except Exception:
            pass

    kb = []
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
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({'pdf_files': pdf_files, 'kb': kb}, f)
    except Exception as e:
        logger.warning(f"No se pudo guardar cache: {e}")
        
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
        api_key = GROQ_API_KEY
        
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
        return chatbot_response_fallback(user_query, latest, asset_name, kpi_values)

def chatbot_response_fallback(user_query, latest, asset_name, kpi_values):
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100 | Vibracion {latest['vibracion_rms_mm_s']:.2f} mm/s | Temp {latest['temperatura_c']:.1f} C | Vacio {latest['presion_vacio_kpa']:.1f} kPa"
    alarms = get_alarms(latest)
    at = ", ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) if alarms else "Sin alarmas"
    
    if any(k in text for k in ["hola", "ayuda", "quiero", "necesito", "buenas", "hey"]):
        return f"Bienvenido a Tech Maint Pro\n\n{sl}\n\nPuedo ayudarte con:\n- Diagnostico del equipo\n- Generacion de ordenes de trabajo\n- Analisis AMEF y modos de falla\n- Consulta de KPIs (MTBF, MTTR, Disponibilidad)\n- Impacto circular y sostenibilidad\n- Procedimientos de mantenimiento\n- Plan de mantenimiento y calendario\n\nEscribe tu consulta o usa los botones rapidos."
    
    if any(k in text for k in ["estado", "riesgo", "condicion", "diagnostico", "como esta", "situacion"]):
        na = [a[1] for a in alarms]
        if "Vibracion" in na and "Temperatura" in na: 
            hip = "Posible desgaste de rodamientos o desalineacion del eje. Se recomienda verificar alineacion laser y estado de rodamientos."
        elif "Presion de vacio" in na: 
            hip = "Posible fuga en linea de vacio o deterioro de sellos mecanicos. Realizar prueba de fugas con helio."
        elif "Vibracion" in na: 
            hip = "Posible desalineacion, desbalance o desgaste de rodamiento. Medir vibracion en 3 ejes."
        elif "Temperatura" in na: 
            hip = "Posible friccion interna, lubricacion deficiente o sobrecarga del motor. Verificar nivel y calidad del aceite."
        elif "Corriente del motor" in na:
            hip = "Posible sobrecarga electrica o falla en devanado del motor. Medir corriente en las 3 fases."
        else: 
            hip = "Condicion normal del equipo. Todos los parametros dentro de rangos operativos."
        acc = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT Prioridad 0 - Atencion inmediata requerida"
        return f"**Diagnostico Actual**\n\n{sl}\n\n**Alarmas activas:** {at if at != 'Sin alarmas' else 'Ninguna'}\n\n**Hipotesis tecnica:** {hip}\n\n**Accion recomendada:** {acc}\n\n[Fuente: Archivo 03 - Gestion KPIs]"
    
    if any(k in text for k in ["plan", "mantenimiento", "calendario", "programa"]):
        return "**Plan de Mantenimiento**\n\nEl sistema cuenta con un modulo completo de planificacion de mantenimiento que incluye:\n\n- Calendario anual de mantenimiento 2026\n- Filtrado por frecuencia (3, 4, 6, 12 meses)\n- Buscador por fecha o palabra clave\n- Descarga de reportes en PDF formato SANIPES\n- Recordatorios automaticos via Telegram\n- Seguimiento de ejecucion\n\n**Activos programados:**\n- Bomba de vacio BV-01\n- Motor CAT 3408 MD-01\n- Compresor Leroi CA-01\n\n[Fuente: Sistema Tech Maint Pro - Modulo Plan de Mantenimiento]"
    
    if any(k in text for k in ["orden", "trabajo", "ot", "generar", "crear ot", "nueva ot"]):
        pri = "P0" if latest["estado"] == "Critico" else "P1" if latest["estado"] == "Alerta" else "P2"
        sint = "; ".join([f"{n}: {v} ({l})" for l, n, v in alarms]) or "Mantenimiento preventivo programado"
        tareas = []
        if any(a[1] == "Vibracion" for a in alarms): tareas += ["Medir vibracion en 3 puntos (H/V/A)", "Verificar alineacion laser", "Inspeccionar rodamientos"]
        if any(a[1] == "Temperatura" for a in alarms): tareas += ["Revisar nivel de lubricante", "Verificar sistema de enfriamiento", "Inspeccionar sobrecarga"]
        if any(a[1] == "Presion de vacio" for a in alarms): tareas += ["Prueba de fugas", "Inspeccionar sellos mecanicos", "Revisar tuberias y conexiones"]
        if any(a[1] == "Corriente del motor" for a in alarms): tareas += ["Medir corriente en 3 fases", "Inspeccionar devanado", "Verificar carga del motor"]
        if not tareas: tareas = ["Inspeccion visual general", "Verificacion de parametros operativos", "Limpieza de componentes"]
        return f"**OT Sugerida**\n\n**Prioridad:** {pri}\n**Activo:** {asset_name}\n**Sintomas:** {sint}\n\n**Tareas sugeridas:**\n" + "\n".join([f"- {t}" for t in tareas]) + f"\n\n**Responsable asignado:** {STAFF['tecnico']['nombre'] if pri in ['P0','P1'] else STAFF['asesor']['nombre']}\n\n[Fuente: Archivo 10 - Tesis Ladrillera]"
    
    if any(k in text for k in ["vibracion", "vibra", "oscilacion", "rms"]):
        v = latest["vibracion_rms_mm_s"]
        vs = "Critico" if v >= THRESHOLDS["vibration_alert"] else "Alerta" if v >= THRESHOLDS["vibration_normal"] else "Normal"
        return f"**Analisis de Vibracion RMS**\n\n**Lectura actual:** {v:.2f} mm/s\n**Estado:** {vs}\n**Umbral Alerta:** {THRESHOLDS['vibration_normal']} mm/s\n**Umbral Critico:** {THRESHOLDS['vibration_alert']} mm/s\n\n**Causas posibles:**\n- Desgaste de rodamientos\n- Desalineacion del eje\n- Desbalance de rotor\n- Holgura mecanica\n- Resonancia estructural\n\n**Acciones recomendadas:**\n1. Medir vibracion en 3 ejes (horizontal, vertical, axial)\n2. Analizar espectro de frecuencias\n3. Verificar alineacion laser\n4. Inspeccionar estado de rodamientos\n5. Revisar lubricacion\n\n[Fuente: Archivo 05 - Manual IMBIL]"
    
    if any(k in text for k in ["temperatura", "temp", "calor", "sobrecalentamiento", "aceite"]):
        t = latest["temperatura_c"]
        ts = "Critico" if t >= THRESHOLDS["temperature_alert"] else "Alerta" if t >= THRESHOLDS["temperature_normal"] else "Normal"
        return f"**Analisis de Temperatura**\n\n**Lectura actual:** {t:.1f} C\n**Estado:** {ts}\n**Umbral Alerta:** {THRESHOLDS['temperature_normal']} C\n**Umbral Critico:** {THRESHOLDS['temperature_alert']} C\n\n**Causas posibles:**\n- Friccion interna excesiva\n- Lubricacion deficiente o aceite degradado\n- Sobrecarga del motor\n- Falla en sistema de enfriamiento\n- Obstruccion de flujo\n\n**Acciones recomendadas:**\n1. Verificar nivel y calidad del aceite\n2. Inspeccionar sistema de enfriamiento\n3. Medir corriente del motor\n4. Revisar carga operativa\n5. Limpiar filtros y intercambiadores\n\n[Fuente: Archivo 06 - Manual Caterpillar]"
    
    if any(k in text for k in ["vacio", "presion", "succcion", "mbar", "kpa"]):
        p = latest["presion_vacio_kpa"]
        ps = "Critico" if p >= THRESHOLDS["vacuum_alert"] else "Alerta" if p >= THRESHOLDS["vacuum_normal"] else "Normal"
        return f"**Analisis de Presion de Vacio**\n\n**Lectura actual:** {p:.1f} kPa\n**Estado:** {ps}\n**Umbral Alerta:** {THRESHOLDS['vacuum_normal']} kPa\n**Umbral Critico:** {THRESHOLDS['vacuum_alert']} kPa\n\n*Nota: Valores mas negativos indican mejor vacio*\n\n**Causas posibles de perdida de vacio:**\n- Fuga en linea de succion\n- Deterioro de sellos mecanicos\n- Obstruccion en filtros\n- Falla en bomba de vacio\n- Entrada de aire no deseada\n\n**Acciones recomendadas:**\n1. Realizar prueba de fugas con helio\n2. Inspeccionar sellos y juntas\n3. Revisar tuberias y conexiones\n4. Verificar estado de filtros\n5. Medir caudal de succion\n\n[Fuente: Archivo 09 - POE Laboratorio]"
    
    if any(k in text for k in ["kpi", "indicador", "metrica", "mtbf", "mttr", "disponibilidad", "rendimiento"]):
        return f"**KPIs de Mantenimiento**\n\n**MTBF (Tiempo Medio Entre Fallas):** {kpi_values['MTBF (h)']:.1f} horas\n**MTTR (Tiempo Medio de Reparacion):** {kpi_values['MTTR (h)']:.1f} horas\n**Disponibilidad:** {kpi_values['Disponibilidad (%)']:.2f}%\n**Confiabilidad a 24h:** {kpi_values['Confiabilidad 24h (%)']:.2f}%\n**Cumplimiento PM:** {kpi_values['Cumplimiento PM (%)']:.1f}%\n**Backlog:** {kpi_values['Backlog (semanas)']:.1f} semanas\n**Perdida productiva:** {kpi_values['Perdida productiva (t)']:.1f} toneladas\n\n**Interpretacion:**\n- MTBF alto = Equipo confiable\n- MTTR bajo = Reparaciones rapidas\n- Disponibilidad > 95% = Excelente\n- Cumplimiento PM > 90% = Buen programa preventivo\n\n[Fuente: Archivo 03 - Gestion KPIs]"
    
    if any(k in text for k in ["circular", "impacto", "residuo", "sostenibilidad", "economia circular", "reciclaje"]):
        return f"**Panel de Impacto Circular**\n\nEl modulo de economia circular registra las decisiones de mantenimiento que permiten conservar componentes y minimizar residuos.\n\n**Como registrar una intervencion circular:**\n1. Cerrar una Orden de Trabajo\n2. Seleccionar decision tomada:\n   - Inspeccion (sin cambio de componente)\n   - Reparacion (componente reparado in-situ)\n   - Reemplazo Parcial (solo piezas danadas)\n   - Reemplazo Total (componente completo)\n3. Registrar masa conservada (kg)\n4. Registrar masa descartada (kg)\n5. El sistema calcula automaticamente:\n   - Tasa de circularidad\n   - CO2 evitado\n   - Ahorro economico\n   - ROI de economia circular\n**Meta:** Tasa de circularidad > 70% (industria clase mundial)\n\n[Fuente: Archivo 10 - Tesis Ladrillera]"
    
    return f"Entiendo tu consulta sobre '{user_query}'.\n\n**Informacion actual del equipo:**\n{sl}\n\n**Puedo ayudarte con:**\n1. Estado actual y diagnostico\n2. Analisis de vibracion, temperatura o vacio\n3. Generacion de ordenes de trabajo\n4. Consulta de KPIs (MTBF, MTTR, Disponibilidad)\n5. Modos de falla (AMEF/RCM)\n6. Procedimientos de mantenimiento\n7. Gestion de repuestos\n8. Protocolos de seguridad\n9. Analisis de costos\n10. Impacto circular\n11. Plan de mantenimiento y calendario\n\nPor favor, reformula tu pregunta o selecciona una de las opciones anteriores.\n\n[Fuente: Sistema Tech Maint Pro]"

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
        
        if st.session_state.get("audio_enabled", False):
            play_notification_sound()
    except Exception as e:
        st.session_state["floating_chat_history"].append({"role": "assistant", "content": f"Error: {e}"})

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
    fig.update_layout(title=dict(text=title, font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")), template="plotly_white", paper_bgcolor="rgba(255,255,255,0.95)", plot_bgcolor="rgba(255,255,255,0.95)", margin=dict(l=20, r=20, t=78, b=30), xaxis=dict(title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)), showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10), tickangle=-45), yaxis=dict(title=dict(text=y_title, font=dict(color=COLORS["texto_oscuro"], size=12)), autorange="reversed" if reverse else True, showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10)), hovermode="x unified", showlegend=False, height=280, font=dict(color=COLORS["texto_oscuro"], family="Arial", size=12))
    return fig

def create_vibration_chart(df): return create_sensor_chart(df, "vibracion_rms_mm_s", "Vibracion RMS", "mm/s", COLORS["azul"], THRESHOLDS["vibration_normal"], THRESHOLDS["vibration_alert"])
def create_temperature_chart(df): return create_sensor_chart(df, "temperatura_c", "Temperatura", "C", COLORS["amarillo"], THRESHOLDS["temperature_normal"], THRESHOLDS["temperature_alert"])
def create_vacuum_chart(df): return create_sensor_chart(df, "presion_vacio_kpa", "Presion de vacio", "kPa", COLORS["verde"], THRESHOLDS["vacuum_normal"], THRESHOLDS["vacuum_alert"], reverse=True)

def create_risk_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["indice_riesgo"], mode="lines+markers", name="IR", line=dict(color=COLORS["amarillo"], width=3), fill="tozeroy", fillcolor="rgba(245,166,35,0.10)", marker=dict(size=4)))
    fig.add_hline(y=40, line_dash="dash", line_color=COLORS["amarillo"], line_width=2, annotation_text="Alerta", annotation_position="top right", annotation_font_color=COLORS["amarillo"], annotation_font_size=11)
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["rojo"], line_width=2, annotation_text="Critico", annotation_position="top right", annotation_font_color=COLORS["rojo"], annotation_font_size=11)
    fig.update_layout(title=dict(text="Indice de riesgo", font=dict(color=COLORS["texto_oscuro"], size=14, family="Arial")), template="plotly_white", paper_bgcolor="rgba(255,255,255,0.95)", plot_bgcolor="rgba(255,255,255,0.95)", margin=dict(l=20, r=20, t=52, b=20), xaxis=dict(title=dict(text="Fecha/hora", font=dict(color=COLORS["texto_oscuro"], size=12)), showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10), tickangle=-45), yaxis=dict(title=dict(text="IR", font=dict(color=COLORS["texto_oscuro"], size=12)), range=[0, 100], showgrid=True, gridcolor="rgba(0,0,0,0.08)", tickfont=dict(color=COLORS["texto_oscuro"], size=10)), hovermode="x unified", height=280, font=dict(color=COLORS["texto_oscuro"], family="Arial", size=12))
    return fig

# ============================================================================
# BASE DE DATOS
# ============================================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Usamos IF NOT EXISTS para no borrar los datos que subimos desde GitHub
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (
        ot_id TEXT PRIMARY KEY,
        asset_name TEXT NOT NULL,
        tag TEXT, ubicacion TEXT, alert_id TEXT, description TEXT,
        prioridad TEXT NOT NULL DEFAULT 'P2', tipo TEXT DEFAULT 'Correctivo',
        responsable TEXT, creation_date TEXT NOT NULL, due_date TEXT,
        estimated_hours REAL DEFAULT 2.0, status TEXT NOT NULL DEFAULT 'Pendiente',
        start_time TEXT, end_time TEXT, hallazgos TEXT, acciones TEXT,
        repuestos TEXT, evidencia TEXT, firma_operario TEXT, firma_supervisor TEXT,
        tiempo_real_horas REAL, created_by TEXT, updated_at TEXT,
        componente_afectado TEXT, tipo_falla TEXT, decision_tecnica TEXT,
        masa_conservada_kg REAL DEFAULT 0, masa_descartada_kg REAL DEFAULT 0,
        costo_reparacion REAL DEFAULT 0, costo_reemplazo_nuevo REAL DEFAULT 0,
        co2_evitado_kg REAL DEFAULT 0, vida_util_extendida_horas REAL DEFAULT 0,
        disponibilidad_post_reparacion_pct REAL DEFAULT 0
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ot_id TEXT NOT NULL, asset_name TEXT, component TEXT NOT NULL,
        decision TEXT NOT NULL, result TEXT, mass_conserved_kg REAL DEFAULT 0,
        mass_discarded_kg REAL DEFAULT 0, costo_reparacion_eur REAL DEFAULT 0,
        costo_reemplazo_nuevo_eur REAL DEFAULT 0, vida_util_extendida_horas REAL DEFAULT 0,
        co2_evitado_kg REAL DEFAULT 0, disponibilidad_post_reparacion_pct REAL DEFAULT 0,
        tiempo_entre_fallas_reparado_horas REAL DEFAULT 0, nivel_reparacion INTEGER DEFAULT 0,
        fabricante_original TEXT, garantia_reparacion_meses INTEGER DEFAULT 0,
        recorded_date TEXT NOT NULL, recorded_by TEXT,
        FOREIGN KEY (ot_id) REFERENCES work_orders(ot_id)
    )""")
    
    # Crear tabla maintenance_plan si no existe
    c.execute("""CREATE TABLE IF NOT EXISTS maintenance_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT NOT NULL,
        tag TEXT,
        ubicacion TEXT,
        maintenance_type TEXT,
        task_description TEXT,
        frequency TEXT,
        frequency_days INTEGER,
        estimated_hours REAL,
        responsable TEXT,
        priority TEXT,
        required_parts TEXT,
        tools_needed TEXT,
        safety_requirements TEXT,
        checklist_items TEXT,
        thresholds TEXT,
        notes TEXT,
        last_execution_date TEXT,
        next_scheduled_date TEXT
    )""")
    
    # Crear tabla maintenance_execution si no existe
    c.execute("""CREATE TABLE IF NOT EXISTS maintenance_execution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        asset_name TEXT,
        scheduled_date TEXT,
        execution_date TEXT,
        executed_by TEXT,
        status TEXT DEFAULT 'Pendiente',
        observations TEXT,
        photos_before TEXT,
        photos_after TEXT,
        circular_impact_registered INTEGER DEFAULT 0,
        FOREIGN KEY (plan_id) REFERENCES maintenance_plan(id)
    )""")
    
    # Crear tabla ot_photos si no existe
    c.execute("""CREATE TABLE IF NOT EXISTS ot_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ot_id TEXT,
        photo_type TEXT,
        photo_path TEXT,
        upload_date TEXT,
        FOREIGN KEY (ot_id) REFERENCES work_orders(ot_id)
    )""")
    
    # Cargar plan de mantenimiento desde CSV (ANTES del commit)
    df_plan = load_maintenance_plan()
    if not df_plan.empty:
        logger.info(f"Cargando {len(df_plan)} tareas de mantenimiento desde CSV...")
        for _, row in df_plan.iterrows():
            try:
                c.execute("""INSERT INTO maintenance_plan 
                    (asset_name, tag, ubicacion, maintenance_type, task_description, 
                     frequency, frequency_days, estimated_hours, responsable, priority,
                     required_parts, tools_needed, safety_requirements, checklist_items, 
                     thresholds, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row.get('asset_name', ''), row.get('tag', ''), row.get('ubicacion', ''),
                     row.get('maintenance_type', ''), row.get('task_description', ''),
                     row.get('frequency', ''), row.get('frequency_days', 0),
                     row.get('estimated_hours', 0), row.get('responsable', ''),
                     row.get('priority', ''), row.get('required_parts', ''),
                     row.get('tools_needed', ''), row.get('safety_requirements', ''),
                     row.get('checklist_items', ''), row.get('thresholds', ''),
                     row.get('notes', '')))
            except sqlite3.IntegrityError:
                # Si ya existe, ignorar (esto pasa si ya se cargó antes)
                pass
            except Exception as e:
                logger.error(f"Error insertando tarea de mantenimiento: {e}")
    
    # AHORA sí hacemos commit y cerramos
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente.")

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
    "step_speed": 1, "production_rate": 85.5, "groq_api_key": GROQ_API_KEY,
    "knowledge_base": [], "kb_loaded": False, "use_test_data": True,
    "audio_enabled": False, "maintenance_plan_df": None
}
for k, v in sd.items():
    if k not in st.session_state: st.session_state[k] = v

apply_custom_styles()
if not st.session_state.get("kb_loaded", False):
    with st.spinner("Cargando base de conocimiento PDF..."): load_knowledge_base()

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
# HEADER CON BOTON DE DOCUMENTOS
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

# Tabs principales - Impacto Circular ahora dentro de KPIs
tabs = st.tabs(["Monitoreo", "Diagnostico", "Ordenes de Trabajo", "Plan de Mantenimiento", "KPIs y Reportes"])
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

# ============================================================================
# TAB 1: MONITOREO
# ============================================================================

with tabs[0]:
    statuses = variable_status(latest)
    def get_status_color(status): return COLORS["verde"] if status == "Normal" else COLORS["amarillo"] if status == "Alerta" else COLORS["rojo"]
    def get_text_color(status): return "#ffffff"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card status-{statuses['Vibracion'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Vibracion'])};margin-bottom:8px;">VIBRACION RMS</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Vibracion'])};">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Vibracion'])};font-weight:bold;">{statuses['Vibracion'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Vibracion'])};margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['vibration_normal']} / {THRESHOLDS['vibration_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vibration_chart(DF), use_container_width=True)
    
    with col2:
        st.markdown(f"""<div class="metric-card status-{statuses['Temperatura'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Temperatura'])};margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Temperatura'])};">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">C</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Temperatura'])};font-weight:bold;">{statuses['Temperatura'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Temperatura'])};margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['temperature_normal']} / {THRESHOLDS['temperature_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_temperature_chart(DF), use_container_width=True)
    
    with col3:
        st.markdown(f"""<div class="metric-card status-{statuses['Presion de vacio'].lower()}">
            <div style="font-size:1.1rem;font-weight:800;color:{get_text_color(statuses['Presion de vacio'])};margin-bottom:8px;">PRESION DE VACIO</div>
            <div style="font-size:2.2rem;font-weight:800;margin:10px 0;color:{get_text_color(statuses['Presion de vacio'])};">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div style="font-size:1.1rem;color:{get_text_color(statuses['Presion de vacio'])};font-weight:bold;">{statuses['Presion de vacio'].upper()}</div>
            <div style="font-size:0.8rem;color:{get_text_color(statuses['Presion de vacio'])};margin-top:8px;opacity:0.9;">Mas negativo = mejor</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vacuum_chart(DF), use_container_width=True)
    
    with col4:
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
# TAB 3: ORDENES DE TRABAJO (CON FOTOS)
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
        
        # Upload de fotos
        st.markdown("**Fotos del antes y despues:**")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            photos_before = st.file_uploader("Fotos ANTES (multiple)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="ot_before")
        with col_f2:
            photos_after = st.file_uploader("Fotos DESPUES (multiple)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="ot_after")
        
        submitted = st.form_submit_button("Crear OT", use_container_width=True, type="primary")
        if submitted:
            ts = datetime.now().strftime("%Y%m%d%H%M")
            new_ot_id = f"OT-{ts}-{nueva_prioridad}"
            try:
                c.execute("SELECT ot_id FROM work_orders WHERE ot_id=?", (new_ot_id,))
                if c.fetchone():
                    st.info(f"La OT {new_ot_id} ya existe")
                else:
                    c.execute("""INSERT INTO work_orders 
                        (ot_id, asset_name, tag, ubicacion, alert_id, description, 
                         prioridad, tipo, responsable, creation_date, estimated_hours, 
                         status, created_by, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_ot_id, nuevo_activo, ASSETS[nuevo_activo]["tag"], nueva_ubicacion,
                         f"ALM-{ts}", nueva_descripcion, nueva_prioridad, nuevo_tipo, 
                         nuevo_responsable, datetime.now().isoformat(), horas_estimadas,
                         "Pendiente", "manual", datetime.now().isoformat()))
                    
                    # Guardar fotos
                    if photos_before or photos_after:
                        for photo in photos_before:
                            photo_path = os.path.join(UPLOAD_DIR, f"{new_ot_id}_before_{photo.name}")
                            with open(photo_path, "wb") as f:
                                f.write(photo.getbuffer())
                            c.execute("INSERT INTO ot_photos (ot_id, photo_type, photo_path, upload_date) VALUES (?, ?, ?, ?)",
                                    (new_ot_id, 'before', photo_path, datetime.now().isoformat()))
                        
                        for photo in photos_after:
                            photo_path = os.path.join(UPLOAD_DIR, f"{new_ot_id}_after_{photo.name}")
                            with open(photo_path, "wb") as f:
                                f.write(photo.getbuffer())
                            c.execute("INSERT INTO ot_photos (ot_id, photo_type, photo_path, upload_date) VALUES (?, ?, ?, ?)",
                                    (new_ot_id, 'after', photo_path, datetime.now().isoformat()))
                    
                    conn.commit()
                    st.success(f"OT creada exitosamente: {new_ot_id}")
            except Exception as e:
                st.error(f"Error creando OT: {e}")
    conn.close()
    
    st.markdown("<h3>Ordenes Existentes</h3>", unsafe_allow_html=True)
    if all_orders:
        for ot in all_orders[:10]:
            with st.expander(f"{ot['ot_id']} - {ot['asset_name']} ({ot['status']})"):
                st.markdown(f"**Activo:** {ot['asset_name']} | **Prioridad:** {ot['prioridad']}")
                st.markdown(f"**Descripcion:** {ot['description']}")
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    if st.button("Iniciar", key=f"ini_{ot['ot_id']}"):
                        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                        c.execute("UPDATE work_orders SET status='En Ejecucion', start_time=?, updated_at=? WHERE ot_id=?", (datetime.now().isoformat(), datetime.now().isoformat(), ot['ot_id']))
                        conn.commit(); conn.close()
                        notify_ot_started(ot['ot_id'], ot['asset_name'], ot['responsable'])
                        st.rerun()
                with col_a2:
                    if st.button("Pausar", key=f"pau_{ot['ot_id']}"):
                        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                        c.execute("UPDATE work_orders SET status='Pausado', updated_at=? WHERE ot_id=?", (datetime.now().isoformat(), ot['ot_id']))
                        conn.commit(); conn.close()
                        st.rerun()
                with col_a3:
                    if st.button("Completar", key=f"com_{ot['ot_id']}"):
                        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
                        c.execute("UPDATE work_orders SET status='Cerrada', end_time=?, updated_at=? WHERE ot_id=?", (datetime.now().isoformat(), datetime.now().isoformat(), ot['ot_id']))
                        conn.commit(); conn.close()
                        notify_ot_completed({"ot_id": ot['ot_id'], "responsable": ot['responsable'], "tiempo_real_horas": 0, "hallazgos": "Completado"})
                        st.rerun()
    else:
        st.info("No hay ordenes registradas.")

# ============================================================================
# TAB 4: PLAN DE MANTENIMIENTO (NUEVO)
# ============================================================================

with tabs[3]:
    st.markdown("<h2>Plan de Mantenimiento 2026</h2>", unsafe_allow_html=True)
    
    # Buscador/Filtro
    st.markdown('<div class="search-box">', unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_query = st.text_input("Buscar por fecha o palabra clave:", placeholder="Ej: Bomba, Enero, Preventivo...")
    with col_s2:
        filter_freq = st.selectbox("Filtrar por frecuencia:", ["Todas", "3 meses", "4 meses", "6 meses", "12 meses", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Cargar plan de mantenimiento
    conn = sqlite3.connect(DB_PATH)
    df_plan = pd.read_sql_query("SELECT * FROM maintenance_plan", conn)
    conn.close()
    
    if not df_plan.empty:
        # Aplicar filtros
        if search_query:
            mask = df_plan.apply(lambda row: row.astype(str).str.lower().str.contains(search_query.lower()).any(), axis=1)
            df_plan = df_plan[mask]
        
        if filter_freq != "Todas":
            df_plan = df_plan[df_plan['frequency'].str.lower() == filter_freq.lower()]
        
        # Mostrar calendario
        st.markdown("<h3>Calendario Anual de Mantenimiento 2026</h3>", unsafe_allow_html=True)
        
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
        cols = st.columns(4)
        for i, mes in enumerate(meses):
            with cols[i % 4]:
                tareas_mes = len(df_plan)  # Simplificado - en produccion se filtraria por mes
                st.markdown(f"""
                <div class="calendar-month">
                    <span>{mes} 2026</span>
                    <span style="background:rgba(255,255,255,0.2); padding:5px 10px; border-radius:15px;">{tareas_mes} tareas</span>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Tabla de tareas
        st.markdown("<h3>Tareas Programadas</h3>", unsafe_allow_html=True)
        
        display_cols = ['asset_name', 'maintenance_type', 'task_description', 'frequency', 'responsable', 'priority']
        df_display = df_plan[display_cols].copy()
        df_display.columns = ['Activo', 'Tipo', 'Tarea', 'Frecuencia', 'Responsable', 'Prioridad']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Boton de descarga PDF
        if st.button("Descargar Reporte PDF (Formato SANIPES)", use_container_width=True):
            # Generar PDF con todas las tareas
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph("PLAN DE MANTENIMIENTO 2026 - FORMATO SANIPES", styles['Title']))
            elements.append(Spacer(1, 0.3*inch))
            
            for _, row in df_plan.iterrows():
                elements.append(Paragraph(f"<b>{row['asset_name']}</b>", styles['Heading2']))
                elements.append(Paragraph(f"<b>Tarea:</b> {row['task_description']}", styles['Normal']))
                elements.append(Paragraph(f"<b>Frecuencia:</b> {row['frequency']} | <b>Responsable:</b> {row['responsable']}", styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
            
            doc.build(elements)
            buffer.seek(0)
            
            st.download_button(
                label="Descargar PDF",
                data=buffer,
                file_name=f"Plan_Mantenimiento_2026_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        # Registro de ejecucion
        st.markdown("<h3>Registrar Ejecucion de Mantenimiento</h3>", unsafe_allow_html=True)
        
        with st.form("registro_ejecucion"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                ejec_activo = st.selectbox("Activo:", list(ASSETS.keys()), key="ejec_activo")
                ejec_fecha = st.date_input("Fecha de ejecucion:", datetime.now())
            with col_e2:
                ejec_tecnico = st.selectbox("Tecnico:", ["Dario Minan", "Jordy Sernaque"], key="ejec_tecnico")
                ejec_status = st.selectbox("Estado:", ["Completado", "Pendiente", "Pausado", "No realizado"], key="ejec_status")
            
            ejec_obs = st.text_area("Observaciones:", key="ejec_obs")
            
            # Fotos
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                ejec_photos_before = st.file_uploader("Fotos ANTES", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="ejec_before")
            with col_f2:
                ejec_photos_after = st.file_uploader("Fotos DESPUES", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="ejec_after")
            
            # Checkbox de impacto circular
            circular_check = st.checkbox("Registrar impacto circular", key="circular_check")
            
            submitted_ejec = st.form_submit_button("Registrar Ejecucion", use_container_width=True, type="primary")
            if submitted_ejec:
                # Guardar en base de datos
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                # Buscar tarea correspondiente
                c.execute("SELECT id FROM maintenance_plan WHERE asset_name=? LIMIT 1", (ejec_activo,))
                result = c.fetchone()
                plan_id = result[0] if result else None
                
                c.execute("""INSERT INTO maintenance_execution 
                    (plan_id, asset_name, scheduled_date, execution_date, executed_by, status, observations)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (plan_id, ejec_activo, datetime.now().isoformat(), ejec_fecha.isoformat(), 
                     ejec_tecnico, ejec_status, ejec_obs))
                
                exec_id = c.lastrowid
                
                # Guardar fotos
                if ejec_photos_before or ejec_photos_after:
                    for photo in ejec_photos_before:
                        photo_path = os.path.join(UPLOAD_DIR, f"exec_{exec_id}_before_{photo.name}")
                        with open(photo_path, "wb") as f:
                            f.write(photo.getbuffer())
                    
                    for photo in ejec_photos_after:
                        photo_path = os.path.join(UPLOAD_DIR, f"exec_{exec_id}_after_{photo.name}")
                        with open(photo_path, "wb") as f:
                            f.write(photo.getbuffer())
                
                conn.commit()
                conn.close()
                
                st.success(f"Ejecucion registrada correctamente")
                
                # Notificar
                if ejec_status == "Completado":
                    play_notification_sound()
                    st.balloons()
    
    else:
        st.info("No hay tareas de mantenimiento programadas. Cargue el archivo plan_de_mto.csv")

# ============================================================================
# TAB 5: KPIs Y REPORTES (CON IMPACTO CIRCULAR)
# ============================================================================

with tabs[4]:
    # Sub-tabs para KPIs e Impacto Circular
    sub_tabs = st.tabs(["KPIs", "Impacto Circular", "Reportes"])
    
    with sub_tabs[0]:
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
    
    with sub_tabs[1]:
        st.markdown("<h2>Panel de Impacto Circular</h2>", unsafe_allow_html=True)
        st.markdown("Registro de decisiones de mantenimiento y su impacto en la conservacion de recursos")
        # BOTÓN PARA CARGAR DATOS DE DEMOSTRACIÓN
if st.button(" Cargar Datos de Demostración", use_container_width=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Datos de demostración
    datos_demo = [
        ("OT-20261020-P1", "Bomba de vacio BV-01", "Rodamiento SKF 6205", "Reparacion", "Reparado", 8.5, 0.3, 250, 1500, 12.5, 2000, 95.0),
        ("OT-20261018-P2", "Motor CAT 3408 MD-01", "Filtro de aceite", "Reemplazo Parcial", "Reutilizado", 2.1, 0.8, 80, 450, 3.2, 500, 98.0),
        ("OT-20261015-P1", "Compresor Leroi CA-01", "Correa de transmision", "Reparacion", "Reparado", 5.2, 0.1, 180, 800, 8.7, 1500, 92.0),
        ("OT-20261012-P0", "Bomba de vacio BV-01", "Sello mecanico", "Reemplazo Total", "Reemplazado", 0.0, 3.5, 0, 2200, 0.0, 0, 100.0),
        ("OT-20261010-P1", "Motor CAT 3408 MD-01", "Inyector de combustible", "Reparacion", "Reparado", 12.8, 0.5, 450, 3200, 18.3, 3000, 96.0),
        ("OT-20261008-P2", "Compresor Leroi CA-01", "Filtro de aire", "Reemplazo Parcial", "Reutilizado", 1.5, 0.4, 60, 320, 2.1, 400, 97.0),
        ("OT-20261005-P1", "Bomba de vacio BV-01", "Eje principal", "Reparacion", "Reparado", 15.3, 0.2, 680, 4500, 22.5, 4000, 94.0),
        ("OT-20261002-P0", "Motor CAT 3408 MD-01", "Turbo compresor", "Reemplazo Total", "Reemplazado", 0.0, 18.5, 0, 8500, 0.0, 0, 100.0),
    ]
    
    for row in datos_demo:
        try:
            c.execute("""INSERT INTO circular_interventions 
                (ot_id, asset_name, component, decision, result, 
                 mass_conserved_kg, mass_discarded_kg, 
                 costo_reparacion_eur, costo_reemplazo_nuevo_eur, 
                 co2_evitado_kg, vida_util_extendida_horas, 
                 disponibilidad_post_reparacion_pct, recorded_date, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*row, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Dario Minan"))
        except sqlite3.IntegrityError:
            pass  # Si ya existe, ignorar
    
    conn.commit()
    conn.close()
    st.success("Datos de demostración cargados correctamente!")
    st.rerun()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM circular_interventions ORDER BY recorded_date DESC")
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
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Tasa de Circularidad", f"{tasa_circularidad:.1f}%", delta=f"{masa_conservada:.0f} kg conservados")
            with col2: st.metric("CO2 Evitado", f"{co2_total_evitado:.0f} kg", delta=f"Equivalente a {arboles_equivalentes:.0f} arboles/año")
            with col3: st.metric("Ahorro Total", f"EUR {ahorro_total:,.0f}", delta=f"ROI: {roi_circular:.0f}%", delta_color="normal" if ahorro_total > 0 else "inverse")
            with col4: st.metric("Tasa de Exito Reparaciones", f"{tasa_reparacion:.1f}%", delta=f"{reparados} reparaciones")
            
            st.divider()
            cols_to_show = ['recorded_date', 'ot_id', 'asset_name', 'component', 'decision', 'result', 'mass_conserved_kg', 'mass_discarded_kg']
            if 'costo_reparacion_eur' in df_interventions.columns: cols_to_show.append('costo_reparacion_eur')
            if 'costo_reemplazo_nuevo_eur' in df_interventions.columns: cols_to_show.append('costo_reemplazo_nuevo_eur')
            if 'co2_evitado_kg' in df_interventions.columns: cols_to_show.append('co2_evitado_kg')
            
            df_display = df_interventions[cols_to_show].copy()
            column_names = {'recorded_date': 'Fecha', 'ot_id': 'OT ID', 'asset_name': 'Activo', 'component': 'Componente', 'decision': 'Decision', 'result': 'Resultado', 'mass_conserved_kg': 'Masa Conservada (kg)', 'mass_discarded_kg': 'Masa Descartada (kg)', 'costo_reparacion_eur': 'Costo Reparacion (EUR)', 'costo_reemplazo_nuevo_eur': 'Costo Reemplazo (EUR)', 'co2_evitado_kg': 'CO2 Evitado (kg)'}
            st.dataframe(df_display.rename(columns=column_names).sort_values('Fecha', ascending=False), use_container_width=True, hide_index=True)
            
            csv = df_display.to_csv(index=False, sep=';').encode('utf-8')
            st.download_button(label="Exportar a CSV", data=csv, file_name=f"impacto_circular_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        else:
            st.info("No hay intervenciones registradas. Complete ordenes de trabajo para registrar el impacto circular.")
    
    with sub_tabs[2]:
        st.markdown("<h2>Reportes y Descargas</h2>")
        
        st.markdown("### Generar Reporte de Mantenimiento")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM work_orders WHERE status='Cerrada' ORDER BY creation_date DESC LIMIT 10")
        closed_orders = [dict(row) for row in c.fetchall()]
        conn.close()
        
        if closed_orders:
            selected_ot = st.selectbox("Seleccionar OT para generar reporte:", 
                                       [f"{ot['ot_id']} - {ot['asset_name']}" for ot in closed_orders])
            
            if selected_ot:
                ot_id = selected_ot.split(" - ")[0]
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT * FROM work_orders WHERE ot_id=?", (ot_id,))
                ot_data = dict(c.fetchone())
                
                # Obtener fotos
                c.execute("SELECT photo_path FROM ot_photos WHERE ot_id=? AND photo_type='before'", (ot_id,))
                photos_before = [row[0] for row in c.fetchall()]
                c.execute("SELECT photo_path FROM ot_photos WHERE ot_id=? AND photo_type='after'", (ot_id,))
                photos_after = [row[0] for row in c.fetchall()]
                conn.close()
                
                if st.button("Generar PDF Reporte", use_container_width=True):
                    pdf_buffer = generate_maintenance_pdf(ot_data, photos_before, photos_after)
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_buffer,
                        file_name=f"Reporte_{ot_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.info("No hay OTs cerradas para generar reportes")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("Tech Maint Pro | Prototipo profesional SeedTech 2026 | Los umbrales son referenciales")
