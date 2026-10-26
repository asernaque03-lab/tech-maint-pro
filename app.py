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
# CARGA DE IMAGENES PNG LOCALES
# ============================================================================

def load_image_as_base64(image_path, fallback_svg=""):
    """Carga una imagen PNG local y la convierte a base64 para uso inline."""
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

# SVG fallback minimalista para el logo
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
# METADATOS DE DOCUMENTOS
# ============================================================================

DOCUMENT_METADATA = {
    "01_Mantenimiento_Prev": {"id": 1, "category": "Tesis / Codificacion", "tags": ["Eternit Pacifico", "codificacion", "MTBF", "MTTR", "software SM"], "desc": "Sistema de codificacion de equipos industriales"},
    "02_Mantenimiento_Vacio": {"id": 2, "category": "Tesis / Vacio medico", "tags": ["NFPA 99", "vacio grado medico", "bombas rotativas", "hospital"], "desc": "Programa de mantenimiento para sistemas de vacio medico"},
    "03_Gestion_KPIs": {"id": 3, "category": "Gestion / KPIs", "tags": ["KPI", "MTBF", "MTTR", "disponibilidad", "indicadores"], "desc": "Guia de indicadores clave de rendimiento"},
    "04_Mantenimiento_Casa": {"id": 4, "category": "Tesis / AMFE", "tags": ["AMFE", "FMEA", "criticidad", "casa de maquinas", "hospital"], "desc": "Analisis de Modos de Falla y Efectos"},
    "05_Manual_IMBIL": {"id": 5, "category": "Manual tecnico / IMBIL", "tags": ["anillo liquido", "instalacion", "desmontaje", "lubricacion"], "desc": "Manual completo de bombas de vacio IMBIL serie BVI"},
    "06_Manual_Caterpillar": {"id": 6, "category": "Manual OEM / Caterpillar", "tags": ["G3408", "G3412", "motores a gas", "intervalos de mantenimiento"], "desc": "Manual oficial de operacion y mantenimiento de motores Caterpillar"},
    "07_Ficha_CPS": {"id": 7, "category": "Ficha tecnica / CPS", "tags": ["VP6D", "VP12D", "doble etapa", "10 micrones", "ensayo Rice"], "desc": "Especificaciones tecnicas de bombas de vacio CPS"},
    "08_Manual_Gadnic": {"id": 8, "category": "Manual de usuario / Gadnic", "tags": ["Serie TW", "paletas rotativas", "cambio de aceite", "solucion de problemas"], "desc": "Manual de usuario de bombas Gadnic compactas"},
    "09_Procedimiento_Lab": {"id": 9, "category": "POE / Laboratorio", "tags": ["Thomas BV-1", "diafragma", "trampas", "silica gel", "seguridad"], "desc": "Procedimiento operativo para uso seguro de bomba de vacio"},
    "10_Tesis_Plan": {"id": 10, "category": "Tesis / Ladrillera", "tags": ["Arcillas de Colombia", "COVENIN 2500-93", "criticidad", "programacion anual"], "desc": "Plan completo de mantenimiento preventivo para empresa ladrillera"}
}

# ============================================================================
# SYSTEM PROMPT PARA LETZY
# ============================================================================

SYSTEM_PROMPT = """Eres Letzy, Asistente Experto en Ingenieria de Mantenimiento Industrial, Operacion de Equipos y Gestion de Calidad. Tu base de conocimiento contiene 10 documentos tecnicos especializados.

REGLAS DE RESPUESTA OBLIGATORIAS:
1. Se preciso, tecnico y conciso. Ve directo al dato solicitado.
2. CITA SIEMPRE la fuente entre parentesis al final, usando el numero del archivo. Ejemplo: [Fuente: Archivo 10 - Tesis Arcillas de Colombia]
3. Si te preguntan por PROCEDIMIENTOS o INSTRUCCIONES TECNICAS de equipos especificos, busca primero en el Archivo 10.
4. Si te preguntan por COMO CALCULAR MTBF, MTTR o Disponibilidad, usa el Archivo 03.
5. Si te preguntan por BOMBAS DE VACIO, diferencia segun el contexto:
   - Laboratorio/acidos -> Archivo 09 (Thomas BV-1 con trampas)
   - Industrial/anillo liquido -> Archivo 05 (IMBIL)
   - Compacta/HVAC -> Archivo 08 (Gadnic)
   - Especificaciones tecnicas -> Archivo 07 (CPS)
   - Grado medico -> Archivo 02 (NFPA 99)
6. Si te preguntan por MOTORES Caterpillar G3408/G3412 -> Archivo 06
7. Si te preguntan por ANALISIS DE CRITICIDAD o AMFE -> Archivo 04 o Archivo 10
8. Si te preguntan por SISTEMAS DE CODIFICACION de equipos -> Archivo 01 o Archivo 10
9. Si la informacion NO esta en los documentos, indica claramente que no la encuentras.
10. NUNCA inventes datos tecnicos, valores de torque, frecuencias de mantenimiento o especificaciones que no esten en los documentos.

FORMATO DE RESPUESTA PREFERIDO:
- Usa vinetas y tablas cuando sea posible
- Incluye valores numericos exactos
- Menciona el responsable (mecanico, electricista, operario) cuando aplique
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
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

def apply_custom_styles():
    css = f"""
    <style>
    .stApp {{ 
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%) !important; 
        padding-top: 0 !important;
    }}
    
    .block-container {{
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }}
    
    .main-header {{
        padding: 10px 0;
        margin-bottom: 8px;
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
    .badge-normal-text {{ color: #ffffff; font-weight: bold; }}
    
    .status-alerta {{ background: {COLORS['amarillo']} !important; }}
    .badge-alerta-text {{ color: #ffffff; font-weight: bold; }}
    
    .status-critico {{ background: {COLORS['rojo']} !important; }}
    .badge-critico-text {{ color: #ffffff; font-weight: bold; }}
    
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
    
    div[data-testid="stDialog"] {{
        background: #f5f7fa !important;
        color: #1a2b4c !important;
    }}
    div[data-testid="stDialog"] * {{
        color: #1a2b4c !important;
    }}
    div[data-testid="stDialog"] h3 {{
        color: #1a5fa8 !important;
    }}
    div[data-testid="stDialog"] input {{
        background: #ffffff !important;
        color: #1a2b4c !important;
        border: 1px solid #e8ecf1 !important;
    }}
    div[data-testid="stChatMessage"] {{
        background: #ffffff !important;
        border: 1px solid #e8ecf1 !important;
    }}
    div[data-testid="stChatMessage"] p {{
        color: #1a2b4c !important;
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
    
    @media (max-width: 768px) {{
        .metric-value {{ font-size: 1.5rem !important; }}
        .main-header {{ padding: 8px 0; }}
        h1 {{ font-size: 1.6rem !important; }}
        h2 {{ font-size: 1.3rem !important; }}
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

def load_test_data_from_csv():
    """Carga datos de prueba desde el archivo CSV con conversion de unidades"""
    try:
        if os.path.exists(CSV_TEST_PATH):
            df = pd.read_csv(CSV_TEST_PATH)
            
            # Mapeo de columnas del CSV
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
            
            # Convertir presion de vacio de mbar a kPa e invertir signo
            if 'vacuum_mbar' in df.columns:
                df['presion_vacio_kpa'] = -(df['vacuum_mbar'] * 0.1)
            
            # Convertir Timestamp a datetime
            if 'fecha_hora' in df.columns:
                df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
                if df['fecha_hora'].isna().any():
                    start_date = datetime.now() - timedelta(minutes=len(df))
                    df['fecha_hora'] = [start_date + timedelta(minutes=i) for i in range(len(df))]
            
            # Enriquecer datos con estado y riesgo
            df = enrich_data(df)
            
            # Agregar columna de descripcion de falla si existe
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
    """Obtiene alarmas basadas en umbrales o en el status del CSV"""
    alarms = []
    
    # Si el CSV tiene columna Status, usarla directamente
    if 'status' in row and row['status'] in ['ALARM', 'CRITICAL', 'TRIP', 'WARNING']:
        fault_desc = row.get('fault_description', 'Falla detectada')
        if pd.isna(fault_desc):
            fault_desc = 'Falla detectada'
        level = 'Critico' if row['status'] in ['CRITICAL', 'TRIP'] else 'Alerta'
        
        # Clasificar por tipo de falla
        fault_lower = fault_desc.lower()
        if 'vibracion' in fault_lower or 'vibration' in fault_lower:
            alarms.append((level, "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s - {fault_desc}"))
        elif 'vacio' in fault_lower or 'vacuum' in fault_lower:
            alarms.append((level, "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa - {fault_desc}"))
        elif 'temperatura' in fault_lower or 'sobrecalentamiento' in fault_lower or 'aceite' in fault_lower:
            alarms.append((level, "Temperatura", f"{row['temperatura_c']:.1f} C - {fault_desc}"))
        elif 'sobrecarga' in fault_lower or 'corriente' in fault_lower or 'electrica' in fault_lower:
            if 'motor_current_a' in row:
                alarms.append((level, "Corriente del motor", f"{row['motor_current_a']:.2f} A - {fault_desc}"))
            else:
                alarms.append((level, "Sobrecarga", fault_desc))
        elif 'lubricacion' in fault_lower or 'termica' in fault_lower:
            alarms.append((level, "Temperatura", f"{row['temperatura_c']:.1f} C - {fault_desc}"))
        elif 'mecanica' in fault_lower or 'multiple' in fault_lower:
            alarms.append((level, "Vibracion", f"{row['vibracion_rms_mm_s']:.2f} mm/s - {fault_desc}"))
            alarms.append((level, "Presion de vacio", f"{row['presion_vacio_kpa']:.1f} kPa - {fault_desc}"))
        else:
            alarms.append((level, "General", fault_desc))
    else:
        # Fallback: usar umbrales tradicionales
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
            if key.lower() in pdf_file.lower():
                meta_key = key
                break
        
        meta = DOCUMENT_METADATA.get(meta_key, {"id": 0, "category": "General", "tags": [], "desc": ""})
        
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        text = extract_text_from_pdf(pdf_path)
        
        if text.strip():
            chunks = chunk_text(text, chunk_size=400, overlap=80)
            for idx, chunk in enumerate(chunks):
                kb.append({
                    "doc_id": meta["id"],
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
Tag: {ASSETS[asset_name]['tag']}
Criticidad: {ASSETS[asset_name]['criticality']}
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

INSTRUCCION FINAL: Responde la pregunta del usuario basandote EXCLUSIVAMENTE en la informacion proporcionada arriba. Cita siempre la fuente. Si no encuentras la respuesta en los documentos, indicalo claramente."""
        
        client = Groq(api_key=api_key)
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        response = client.chat.completions.create(
            model="llama3-8b-8192",
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
    st.session_state.floating_chat_history.append({"role": "user", "content": q})
    
    try:
        kp = calculate_kpis(720, 3, 18, 18, 20, 40, 80, st.session_state.get("production_rate", 85.5))
        latest = st.session_state.get("latest_row", pd.Series())
        asset_name = st.session_state.get("asset_name", "")
        
        if ai_platform == "rag" and st.session_state.get("groq_api_key", ""):
            reply = query_groq_with_rag(q, latest, asset_name, kp)
        else:
            reply = chatbot_response_fallback(q, latest, asset_name, kp)
        
        st.session_state.floating_chat_history.append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state.floating_chat_history.append({"role": "assistant", "content": f"Error: {e}"})

@st.dialog("Asistente Tech Maint Pro - Letzy", width="large")
def floating_chat_dialog():
    st.markdown(f"""
    <style>
    div[data-testid="stDialog"] {{ background: #f5f7fa !important; color: #1a2b4c !important; }}
    div[data-testid="stDialog"] * {{ color: #1a2b4c !important; }}
    div[data-testid="stDialog"] h3 {{ color: #1a5fa8 !important; }}
    div[data-testid="stDialog"] input {{ background: #ffffff !important; color: #1a2b4c !important; border: 1px solid #e8ecf1 !important; }}
    div[data-testid="stChatMessage"] {{ background: #ffffff !important; border: 1px solid #e8ecf1 !important; }}
    div[data-testid="stChatMessage"] p {{ color: #1a2b4c !important; }}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px; margin-bottom:10px;">
        {render_letzy("60px")}
        <div>
            <h3 style="margin:0; color:#1a5fa8; font-size:1.5rem;">Hola, soy Letzy</h3>
            <p style="margin:5px 0 0 0; color:#5a6b7c; font-size:0.95rem;">Tu asistente de Tech Maint Pro</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    ai_mode = st.selectbox(
        "Modo de respuesta:",
        options=["rag", "fallback"],
        format_func=lambda x: "IA con Base de Conocimiento PDF (Groq)" if x == "rag" else "Respuestas rapidas (local)",
        index=0 if st.session_state.get("groq_api_key", "") else 1,
        key="ai_mode_selector",
        disabled=not st.session_state.get("kb_loaded", False)
    )
    
    if ai_mode == "rag":
        if not st.session_state.get("groq_api_key", ""):
            st.warning("Ingresa tu API Key de Groq para usar la IA con documentos PDF")
            st.session_state["groq_api_key"] = st.text_input("API Key de Groq", type="password", key="groq_key_rag", help="Obten tu clave gratis en console.groq.com")
        else:
            st.success(f"Base de conocimiento activa: {len(st.session_state.get('knowledge_base', []))} chunks cargados")
    
    st.caption("Respuestas basadas en 10 documentos tecnicos especializados")
    st.divider()
    
    if not st.session_state.floating_chat_history:
        with st.chat_message("assistant", avatar=LETZY_BASE64):
            st.markdown("**HOLA, SOY LETZY TU ASISTENTE DE TECH MAINT PRO**\n\nEn que puedo ayudarte hoy? Tengo acceso a manuales tecnicos, procedimientos de mantenimiento, fichas de equipos y guias de KPIs.")
    
    for msg in st.session_state.floating_chat_history[-10:]:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar=LETZY_BASE64):
                st.markdown(msg["content"])
        else:
            with st.chat_message("user"):
                st.markdown(msg["content"])
    
    st.divider()
    st.markdown("#### Consultas sugeridas:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Estado actual", key="qr1", use_container_width=True):
            process_floating_query("Estado actual", ai_mode)
        if st.button("Alta vibracion", key="qr2", use_container_width=True):
            process_floating_query("Que causa alta vibracion?", ai_mode)
        if st.button("KPIs", key="qr3", use_container_width=True):
            process_floating_query("Cuales son los KPIs?", ai_mode)
    with c2:
        if st.button("Caída de vacio", key="qr4", use_container_width=True):
            process_floating_query("Que revisar si cae el vacio?", ai_mode)
        if st.button("Generar OT", key="qr5", use_container_width=True):
            process_floating_query("Generar orden de trabajo", ai_mode)
        if st.button("Impacto circular", key="qr6", use_container_width=True):
            process_floating_query("Que es impacto circular?", ai_mode)
    with c3:
        if st.button("Modos de falla", key="qr7", use_container_width=True):
            process_floating_query("Modos de falla AMEF", ai_mode)
        if st.button("Temperatura", key="qr8", use_container_width=True):
            process_floating_query("Analiza la temperatura actual", ai_mode)
        if st.button("Limpiar", key="qr9", use_container_width=True):
            st.session_state.floating_chat_history = []
    
    st.divider()
    ui = st.chat_input("Escribe tu consulta a Letzy...", key="fci")
    if ui:
        process_floating_query(ui, ai_mode)
    
    if st.button("Cerrar chat", key="fcc", use_container_width=True):
        st.session_state.floating_chat_open = False
        st.session_state.auto_chat_triggered = False

# ============================================================================
# BOTON FLOTANTE DE LETZY - HTML FIJO EN EL DOM
# ============================================================================

st.markdown(f"""
<a href="?open_letzy=1" style="position: fixed; bottom: 30px; right: 30px; z-index: 9999; width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #1a5fa8, #8bc34a); border: 3px solid #f5a623; box-shadow: 0 4px 20px rgba(0,0,0,0.3); cursor: pointer; overflow: hidden; display: flex; align-items: center; justify-content: center; transition: transform 0.3s ease; text-decoration: none;">
    <img src="{LETZY_BASE64}" style="width: 84px; height: 84px; border-radius: 50%; object-fit: cover;" alt="Letzy">
</a>
""", unsafe_allow_html=True)

if "open_letzy" in st.query_params:
    st.session_state.floating_chat_open = True
    st.query_params.clear()

if st.session_state.get("floating_chat_open", False):
    floating_chat_dialog()

if st.session_state.get("auto_chat_triggered", False) and not st.session_state.get("floating_chat_open", False):
    st.session_state.floating_chat_open = True

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
    c.execute("""CREATE TABLE IF NOT EXISTS work_orders (ot_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, alert_id TEXT, description TEXT, priority TEXT NOT NULL, responsible TEXT, creation_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendiente', created_by TEXT, updated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS circular_interventions (id INTEGER PRIMARY KEY AUTOINCREMENT, ot_id TEXT NOT NULL, component TEXT NOT NULL, decision TEXT NOT NULL, result TEXT, mass_conserved_kg REAL DEFAULT 0, mass_discarded_kg REAL DEFAULT 0, evidence TEXT, recorded_date TEXT NOT NULL, recorded_by TEXT, FOREIGN KEY (ot_id) REFERENCES work_orders(ot_id))""")
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

# Cargar base de conocimiento al inicio
if not st.session_state.get("kb_loaded", False):
    with st.spinner("Cargando base de conocimiento PDF..."):
        load_knowledge_base()

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

# Selector de modo de datos
col_mode1, col_mode2 = st.columns([3, 1])
with col_mode1:
    st.caption("Seleccione el modo de datos para la demostracion")
with col_mode2:
    use_test_data = st.checkbox("Usar datos de prueba CSV", value=st.session_state.get("use_test_data", True), key="use_test_data_checkbox")
    st.session_state.use_test_data = use_test_data

tabs = st.tabs(["Monitoreo", "Diagnostico", "Ordenes de Trabajo", "Impacto Circular", "KPIs"])

asset_name = st.selectbox("Selector de activo", list(ASSETS.keys()), label_visibility="collapsed")
st.caption(f"Tag: {ASSETS[asset_name]['tag']} | Criticidad: {ASSETS[asset_name]['criticality']}")

# Mostrar modo y velocidad
if st.session_state.use_test_data:
    st.info(f" Modo: Datos CSV | Velocidad: 1 registro cada 10 segundos | Total: {len(DF_FULL) if 'DF_FULL' in locals() else 0} registros")
else:
    st.info(f" Modo: Datos Sintéticos | Velocidad: 3 registros por segundo")

# ============================================================================
# SIMULACION
# ============================================================================

# Cargar datos de prueba o generar datos sinteticos
if st.session_state.use_test_data:
    DF_FULL = load_test_data_from_csv()
    if DF_FULL is None:
        st.warning("No se encontro el archivo CSV de prueba. Usando datos sinteticos.")
        DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
        st.session_state.step_speed = 3  # Datos sintéticos: más rápido
else:
    DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
    st.session_state.step_speed = 3  # Datos sintéticos: más rápido

# AJUSTAR VELOCIDAD SEGÚN MODO
if st.session_state.use_test_data and DF_FULL is not None:
    st.session_state.step_speed = 1  # CSV: 1 registro cada actualización (10 segundos reales)
    
max_idx = len(DF_FULL)
st.session_state.sim_idx = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    # Ajustar intervalo según modo: 10000ms para CSV, 1000ms para sintético
    refresh_interval = 10000 if st.session_state.use_test_data else 1000
    
    if HAS_AUTOREFRESH: 
        st_autorefresh(interval=refresh_interval, key="tm_live")
    
    st.session_state.sim_idx = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)
elif st.session_state.sim_idx >= max_idx:
    st.session_state.sim_idx = 1

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state.latest_row = latest
st.session_state.asset_name = asset_name

current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state.auto_chat_triggered = True
    if current_estado == "Critico": play_critical_alarm(f"{latest['fecha_hora']}-critical")
    else: play_observation_alarm(f"{latest['fecha_hora']}-alert")
    
    fault_desc = latest.get('fault_description', '')
    if pd.isna(fault_desc):
        fault_desc = ''
    alert_msg = f"Hola! Soy Letzy. Se ha detectado un estado {current_estado} en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. {fault_desc}. Se requiere atencion inmediata. En que puedo ayudarte?"
    st.session_state.floating_chat_history.append({"role": "assistant", "content": alert_msg})

st.session_state.previous_estado = current_estado

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
                    if new_status == "Cerrada": notify_ot_completion(ot)
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
                        notify_economic_impact({"ot_id": ot.get("ot_id", ""), "component": comp, "decision": dec, "result": res, "mass_conserved_kg": mc, "mass_discarded_kg": md})
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
    with c1: st.metric("Intervenciones", total)
    with c2: st.metric("Reparados/Reutilizados", repaired)
    with c3: st.metric("Masa Conservada (kg)", f"{conserved:.2f}")
    with c4: st.metric("Masa Descartada (kg)", f"{discarded:.2f}")
    
    if interventions:
        st.dataframe(pd.DataFrame(interventions), use_container_width=True, hide_index=True)

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
