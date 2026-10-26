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
# CARGA DE IMAGENES DESDE ARCHIVOS PNG
# ============================================================================

def load_image(image_path):
    """Carga una imagen desde un archivo PNG"""
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                return image_file.read()
        return None
    except Exception as e:
        logger.error(f"Error cargando imagen {image_path}: {e}")
        return None

# Cargar imágenes
LOGO_IMAGE = load_image(os.path.join(APP_DIR, "logo.png"))
LETZY_IMAGE = load_image(os.path.join(APP_DIR, "letzy.png"))

def render_logo(size="180px"):
    """Renderiza el logo desde archivo o base64"""
    if LOGO_IMAGE:
        return f'<img src="data:image/png;base64,{base64.b64encode(LOGO_IMAGE).decode()}" style="width:{size}; height:auto; display:inline-block;" />'
    return '<div style="width:{size}; height:60px; background:#1a5fa8; display:inline-block; border-radius:8px;"></div>'

def render_letzy(size="60px"):
    """Renderiza Letzy desde archivo o base64"""
    if LETZY_IMAGE:
        return f'<img src="data:image/png;base64,{base64.b64encode(LETZY_IMAGE).decode()}" style="width:{size}; height:{size}; border-radius:50%; display:inline-block; object-fit:cover;" />'
    return f'<div style="width:{size}; height:{size}; background:linear-gradient(135deg, #1a5fa8, #8bc34a); border-radius:50%; display:inline-block;"></div>'

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
# COLORES Y CONSTANTES
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

DOCUMENT_METADATA = {
    "01": {"category": "Tesis / Codificacion de equipos", "tags": ["Eternit Pacifico", "codificacion", "MTBF", "MTTR", "software SM"], "desc": "Sistema de codificación de equipos industriales y uso del software SM Real World"},
    "02": {"category": "Tesis / Vacío médico", "tags": ["NFPA 99", "vacío grado médico", "bombas rotativas", "hospital"], "desc": "Programa de mantenimiento para sistemas de vacío médico según norma NFPA 99"},
    "03": {"category": "Gestión / KPIs", "tags": ["KPI", "MTBF", "MTTR", "disponibilidad", "indicadores"], "desc": "Guía de indicadores clave de rendimiento con fórmulas y ejemplos"},
    "04": {"category": "Tesis / AMFE", "tags": ["AMFE", "FMEA", "criticidad", "casa de máquinas", "hospital"], "desc": "Análisis de Modos de Falla y Efectos aplicado a casa de máquinas hospitalaria"},
    "05": {"category": "Manual técnico / IMBIL", "tags": ["anillo líquido", "instalación", "desmontaje", "lubricación"], "desc": "Manual completo de bombas de vacío IMBIL serie BVI"},
    "06": {"category": "Manual OEM / Caterpillar", "tags": ["G3408", "G3412", "motores a gas", "intervalos de mantenimiento"], "desc": "Manual oficial de operación y mantenimiento de motores Caterpillar"},
    "07": {"category": "Ficha técnica / CPS", "tags": ["VP6D", "VP12D", "doble etapa", "10 micrones", "ensayo Rice"], "desc": "Especificaciones técnicas de bombas de vacío CPS para laboratorio"},
    "08": {"category": "Manual de usuario / Gadnic", "tags": ["Serie TW", "paletas rotativas", "cambio de aceite", "solución de problemas"], "desc": "Manual de usuario y troubleshooting de bombas Gadnic compactas"},
    "09": {"category": "POE / Laboratorio", "tags": ["Thomas BV-1", "diafragma", "trampas", "sílica gel", "seguridad"], "desc": "Procedimiento operativo para uso seguro de bomba de vacío en laboratorio"},
    "10": {"category": "Tesis / Ladrillera", "tags": ["Arcillas de Colombia", "COVENIN 2500-93", "criticidad", "programación anual"], "desc": "Plan completo de mantenimiento preventivo para empresa ladrillera con 37 equipos"}
}

SYSTEM_PROMPT = """Eres Letzy, Asistente Experto en Ingeniería de Mantenimiento Industrial, Operación de Equipos y Gestión de Calidad. Tu base de conocimiento contiene 10 documentos técnicos especializados.

REGLAS DE RESPUESTA:
1. Sé preciso, técnico y conciso. Ve directo al dato solicitado.
2. CITA SIEMPRE la fuente entre paréntesis al final, usando el número del archivo. Ejemplo: [Fuente: Archivo 10 - Tesis Arcillas de Colombia]
3. Si te preguntan por PROCEDIMIENTOS o INSTRUCCIONES TÉCNICAS de equipos específicos (extrusora, molino, banda transportadora), busca primero en el Archivo 10 (Arcillas de Colombia) que contiene los anexos detallados.
4. Si te preguntan por CÓMO CALCULAR MTBF, MTTR o Disponibilidad, usa el Archivo 03 (KPIs) para las fórmulas y el Archivo 10 para ejemplos aplicados.
5. Si te preguntan por BOMBAS DE VACÍO, diferencia según el contexto:
   - Laboratorio/ácidos → Archivo 09 (Thomas BV-1 con trampas)
   - Industrial/anillo líquido → Archivo 05 (IMBIL)
   - Compacta/HVAC → Archivo 08 (Gadnic)
   - Especificaciones técnicas → Archivo 07 (CPS)
   - Grado médico → Archivo 02 (NFPA 99)
6. Si te preguntan por MOTORES Caterpillar G3408/G3412 → Archivo 06
7. Si te preguntan por ANÁLISIS DE CRITICIDAD o AMFE → Archivo 04 o Archivo 10
8. Si te preguntan por SISTEMAS DE CODIFICACIÓN de equipos → Archivo 01 o Archivo 10
9. Si la información NO está en los documentos, di: "No encuentro esa información específica en los documentos proporcionados. ¿Puedes reformular tu pregunta o indicarme qué equipo/sistema te interesa?"
10. NUNCA inventes datos técnicos, valores de torque, frecuencias de mantenimiento o especificaciones que no estén en los documentos.

FORMATO DE RESPUESTA PREFERIDO:
- Usa viñetas y tablas cuando sea posible
- Incluye valores numéricos exactos (torques, frecuencias, tiempos)
- Menciona el responsable (mecánico, electricista, operario) cuando aplique
- Indica si la actividad es rutinaria (R) o programada (P)"""

# ============================================================================
# ESTILOS CSS
# ============================================================================

def apply_custom_styles():
    css = f"""
    <style>
    .stApp {{ 
        background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%) !important; 
        padding-top: 0 !important;
    }}
    
    section[data-testid="stSidebar"] {{
        left: auto !important;
        right: 0 !important;
        width: 400px !important;
        min-width: 400px !important;
        background-color: #ffffff !important;
        border-left: 1px solid #e8ecf1 !important;
        z-index: 9998 !important;
        padding-top: 1.5rem !important;
        box-shadow: -4px 0 15px rgba(0,0,0,0.05) !important;
    }}
    
    .stApp > div[data-testid="stAppViewBlockContainer"] {{
        margin-right: 400px !important;
    }}

    div[data-testid="stSidebarCollapsedControl"] {{
        position: fixed !important;
        top: -100px !important; 
        z-index: -1 !important;
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
    }}
    section[data-testid="stSidebar"] .stChatInputContainer {{
        position: sticky;
        bottom: 0;
        background-color: #ffffff;
        padding-top: 10px;
        border-top: 1px solid #e8ecf1;
        z-index: 10;
    }}
    
    .quick-question-btn {{
        width: 100%;
        margin: 5px 0;
        padding: 8px 12px;
        background: rgba(26,95,168,0.1);
        border: 1px solid rgba(26,95,168,0.2);
        border-radius: 8px;
        cursor: pointer;
        text-align: left;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }}
    .quick-question-btn:hover {{
        background: rgba(26,95,168,0.2);
        border-color: rgba(26,95,168,0.4);
    }}
    
    @media (max-width: 768px) {{
        section[data-testid="stSidebar"] {{
            width: 100% !important;
            min-width: 100% !important;
        }}
        .stApp > div[data-testid="stAppViewBlockContainer"] {{
            margin-right: 0 !important;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE CHATBOT
# ============================================================================

def chatbot_response(user_query, latest, asset_name, kpi_values):
    """Genera respuesta del chatbot"""
    text = unicodedata.normalize('NFKD', user_query.lower().strip()).encode('ascii', 'ignore').decode('utf-8')
    sl = f"Estado: {latest['estado']} | IR {latest['indice_riesgo']:.1f}/100 | Vibracion {latest['vibracion_rms_mm_s']:.2f} mm/s | Temp {latest['temperatura_c']:.1f} C | Vacio {latest['presion_vacio_kpa']:.1f} kPa"
    
    if any(k in text for k in ["hola", "ayuda", "quiero", "necesito"]):
        return f"¡Hola! Soy Letzy, tu asistente de mantenimiento.\n\n{sl}\n\nPuedo ayudarte con:\n- Diagnóstico de equipos\n- Órdenes de trabajo\n- AMEF y RCM\n- KPIs de mantenimiento\n- Impacto circular\n\n¿En qué puedo ayudarte?"
    
    if any(k in text for k in ["estado", "riesgo", "condicion", "diagnostico"]):
        return f"**Diagnóstico Actual**\n\n{sl}\n\n**Hipótesis:** {'Condición normal' if latest['estado'] == 'Normal' else 'Se requiere atención inmediata' if latest['estado'] == 'Critico' else 'Programar inspección'}\n\n**Acción recomendada:** {'Continuar monitoreo' if latest['estado'] == 'Normal' else 'Generar OT prioritaria' if latest['estado'] == 'Critico' else 'Programar inspección'}"
    
    if any(k in text for k in ["orden", "trabajo", "ot", "generar"]):
        return f"**Orden de Trabajo Sugerida**\n\nPrioridad: {'P0' if latest['estado'] == 'Critico' else 'P1' if latest['estado'] == 'Alerta' else 'P2'}\nActivo: {asset_name}\n\n**Tareas sugeridas:**\n- Medir vibración\n- Verificar alineación\n- Revisar lubricación\n- Inspeccionar sellos"
    
    if any(k in text for k in ["vibracion", "vibra"]):
        v = latest["vibracion_rms_mm_s"]
        return f"**Vibración RMS**\n\nLectura: {v:.2f} mm/s\nEstado: {'Crítico' if v >= THRESHOLDS['vibration_alert'] else 'Alerta' if v >= THRESHOLDS['vibration_normal'] else 'Normal'}\n\n**Causas posibles:** Desgaste rodamientos, desalineación, desbalance\n\n**Acciones:** Medir vibración, verificar alineación, revisar lubricante"
    
    if any(k in text for k in ["temperatura", "temp", "calor"]):
        t = latest["temperatura_c"]
        return f"**Temperatura**\n\nLectura: {t:.1f} °C\nEstado: {'Crítico' if t >= THRESHOLDS['temperature_alert'] else 'Alerta' if t >= THRESHOLDS['temperature_normal'] else 'Normal'}\n\n**Causas:** Fricción interna, lubricación deficiente, sobrecarga\n\n**Acciones:** Revisar lubricante, inspeccionar enfriamiento"
    
    if any(k in text for k in ["vacio", "presion"]):
        p = latest["presion_vacio_kpa"]
        return f"**Presión de Vacío**\n\nLectura: {p:.1f} kPa\nEstado: {'Crítico' if p >= THRESHOLDS['vacuum_alert'] else 'Alerta' if p >= THRESHOLDS['vacuum_normal'] else 'Normal'}\n*Mas negativo es mejor*\n\n**Causas:** Fuga en línea, deterioro de sellos\n\n**Acciones:** Prueba de fugas, inspeccionar sellos"
    
    if any(k in text for k in ["kpi", "indicador"]):
        return f"**KPIs Actuales**\n\nMTBF: {kpi_values['MTBF (h)']:.1f} h\nMTTR: {kpi_values['MTTR (h)']:.1f} h\nDisponibilidad: {kpi_values['Disponibilidad (%)']:.2f}%\nConfiabilidad 24h: {kpi_values['Confiabilidad 24h (%)']:.2f}%"
    
    if any(k in text for k in ["amef", "rcm", "falla"]):
        return "**AMEF/RCM**\n\n**Modos de falla:**\n1. Vibración alta - Desgaste rodamientos/desalineación\n2. Temperatura alta - Fricción/lubricación deficiente\n3. Pérdida de vacío - Fuga/deterioro sellos"
    
    if any(k in text for k in ["circular", "impacto", "residuo"]):
        return "**Impacto Circular**\n\nRegistro de decisiones que permiten conservar componentes y minimizar residuos.\n\n**Cómo registrar:** Cierra una OT → Selecciona decisión → Registra masa conservada/descartada"
    
    return f"¿En qué puedo ayudarte?\n\n{sl}\n\n**Consultas sugeridas:**\n1. Estado actual del equipo\n2. Variables: vibración, temperatura, vacío\n3. Generar orden de trabajo\n4. AMEF: modos de falla\n5. KPIs: indicadores\n6. Impacto circular"

def process_chat_query(query):
    """Procesa la consulta del chat"""
    if not query or not query.strip():
        return
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    st.session_state["chat_history"].append({"role": "user", "content": query})
    
    try:
        kp = calculate_kpis(720, 3, 18, 18, 20, 40, 80, st.session_state.get("production_rate", 85.5))
        latest = st.session_state.get("latest_row", pd.Series())
        asset_name = st.session_state.get("asset_name", "")
        
        reply = chatbot_response(query, latest, asset_name, kp)
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
    except Exception as e:
        st.session_state["chat_history"].append({"role": "assistant", "content": f"Error: {e}"})

# ============================================================================
# FUNCIONES DE DATOS
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
# GRAFICAS
# ============================================================================

def create_sensor_chart(df, column, title, y_title, color, threshold_normal=None, threshold_alert=None, reverse=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df[column], mode="lines+markers", name=title, line=dict(color=color, width=3), marker=dict(size=4)))
    if threshold_normal is not None:
        fig.add_hline(y=threshold_normal, line_dash="dash", line_color=COLORS["amarillo"], line_width=2, annotation_text="Alerta")
    if threshold_alert is not None:
        fig.add_hline(y=threshold_alert, line_dash="dash", line_color=COLORS["rojo"], line_width=2, annotation_text="Critico")
    fig.update_layout(
        title=dict(text=title, font=dict(color=COLORS["texto_oscuro"], size=14)),
        template="plotly_white", 
        margin=dict(l=20, r=20, t=50, b=30),
        xaxis=dict(title="Fecha/hora", showgrid=True, tickangle=-45),
        yaxis=dict(title=y_title, autorange="reversed" if reverse else True, showgrid=True),
        height=280, showlegend=False
    )
    return fig

def create_vibration_chart(df): 
    return create_sensor_chart(df, "vibracion_rms_mm_s", "Vibracion RMS", "mm/s", COLORS["azul"], THRESHOLDS["vibration_normal"], THRESHOLDS["vibration_alert"])

def create_temperature_chart(df): 
    return create_sensor_chart(df, "temperatura_c", "Temperatura", "C", COLORS["amarillo"], THRESHOLDS["temperature_normal"], THRESHOLDS["temperature_alert"])

def create_vacuum_chart(df): 
    return create_sensor_chart(df, "presion_vacio_kpa", "Presion de vacio", "kPa", COLORS["verde"], THRESHOLDS["vacuum_normal"], THRESHOLDS["vacuum_alert"], reverse=True)

def create_risk_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["indice_riesgo"], mode="lines+markers", name="IR", line=dict(color=COLORS["amarillo"], width=3)))
    fig.add_hline(y=40, line_dash="dash", line_color=COLORS["amarillo"], line_width=2, annotation_text="Alerta")
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["rojo"], line_width=2, annotation_text="Critico")
    fig.update_layout(
        title=dict(text="Indice de riesgo", font=dict(color=COLORS["texto_oscuro"], size=14)),
        template="plotly_white", 
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title="Fecha/hora", showgrid=True, tickangle=-45),
        yaxis=dict(title="IR", range=[0, 100], showgrid=True),
        height=280, showlegend=False
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
    "floating_chat_open": False, "auto_chat_triggered": False, "previous_estado": None,
    "scenario": "Operacion normal", "seed": 42, "n_hours": 168,
    "step_speed": 1, "production_rate": 85.5, "groq_api_key": "",
    "knowledge_base": [], "kb_loaded": False, "use_test_data": True
}
for k, v in sd.items():
    if k not in st.session_state:
        st.session_state[k] = v

apply_custom_styles()

# ============================================================================
# SIDEBAR - CHATBOT LETZY
# ============================================================================

with st.sidebar:
    # Header del chatbot
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px; padding-bottom:15px; border-bottom:2px solid #e8ecf1;">
        {render_letzy("50px")}
        <div>
            <h3 style="margin:0; color:#1a5fa8; font-size:1.3rem;">Letzy</h3>
            <p style="margin:0; color:#5a6b7c; font-size:0.9rem;">Asistente de Mantenimiento</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Modo de IA
    ai_mode = st.selectbox(
        "Modo de respuesta:",
        options=["rapido", "IA (PDF)"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Preguntas rápidas
    st.markdown("** Preguntas rápidas:**")
    
    quick_questions = [
        "¿Cuál es el estado actual?",
        "¿Generar orden de trabajo?",
        "¿Niveles de vibración?",
        "¿KPIs de mantenimiento?",
        "¿AMEF del equipo?",
        "¿Impacto circular?"
    ]
    
    for question in quick_questions:
        if st.button(question, key=f"qq_{question}", use_container_width=True, type="secondary"):
            process_chat_query(question)
    
    st.divider()
    
    # Historial de chat
    chat_history = st.session_state.get("chat_history", [])
    
    if chat_history:
        st.markdown("** Conversación:**")
        chat_container = st.container(height=300)
        with chat_container:
            for msg in chat_history[-10:]:
                if msg["role"] == "assistant":
                    st.markdown(f" **Letzy:** {msg['content']}")
                else:
                    st.markdown(f" **Tú:** {msg['content']}")
                st.markdown("---")
    
    st.divider()
    
    # Input de texto
    user_input = st.chat_input("Escribe tu pregunta a Letzy...", key="chat_input")
    if user_input:
        process_chat_query(user_input)
        st.rerun()
    
    # Botón limpiar chat
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()

# ============================================================================
# HEADER
# ============================================================================

st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; gap:20px; margin-bottom:20px; padding:15px 0;">
    <div style="display:flex; align-items:center; gap:20px;">
        {render_logo("200px")}
        <div>
            <h1 style="margin:0; color:{COLORS['amarillo']}; font-size:1.8rem; font-weight:700;">Mantenimiento Inteligente + Economia Circular</h1>
        </div>
    </div>
    <div>
        <a href="https://drive.google.com/drive/folders/1alITCWZz7CxRgumUUw_kwtmaW5oNPGNI?usp=drive_link" target="_blank" class="doc-button">
            📄 Documentos
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
    else:
        st.session_state["step_speed"] = 1
else:
    DF_FULL = generate_synthetic_data(st.session_state.scenario, n=st.session_state.n_hours, seed=int(st.session_state.seed))
    st.session_state["step_speed"] = 3

max_idx = len(DF_FULL)
st.session_state["sim_idx"] = min(max(1, st.session_state.sim_idx), max_idx)

if st.session_state.running and st.session_state.sim_idx < max_idx:
    if HAS_AUTOREFRESH:
        refresh_interval = 10000 if st.session_state.get("use_test_data", True) else 1000
        st_autorefresh(interval=refresh_interval, key="tm_live")
    st.session_state["sim_idx"] = min(max_idx, st.session_state.sim_idx + st.session_state.step_speed)

DF = DF_FULL.iloc[:st.session_state.sim_idx].copy()
latest = DF.iloc[-1]
st.session_state["latest_row"] = latest
st.session_state["asset_name"] = asset_name

current_estado = latest["estado"]
if current_estado in ["Alerta", "Critico"] and st.session_state.previous_estado != current_estado:
    st.session_state["auto_chat_triggered"] = True
    alert_msg = f"¡Alerta! Se ha detectado un estado {current_estado} en {asset_name}. IR: {latest['indice_riesgo']:.1f}/100. Se requiere atención inmediata."
    st.session_state["chat_history"].append({"role": "assistant", "content": alert_msg})

st.session_state["previous_estado"] = current_estado

# ============================================================================
# TAB 1: MONITOREO
# ============================================================================

with tabs[0]:
    statuses = variable_status(latest)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_class = "status-normal" if statuses["Vibracion"] == "Normal" else "status-alerta" if statuses["Vibracion"] == "Alerta" else "status-critico"
        st.markdown(f"""<div class="metric-card {status_class}">
            <div style="font-size:1.1rem;font-weight:800;color:white;margin-bottom:8px;">VIBRACION RMS</div>
            <div style="font-size:2.5rem;font-weight:800;margin:10px 0;color:white;">{latest['vibracion_rms_mm_s']:.2f} <span style="font-size:1rem;">mm/s</span></div>
            <div style="font-size:1.2rem;color:white;font-weight:bold;">{statuses['Vibracion'].upper()}</div>
            <div style="font-size:0.8rem;color:white;margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['vibration_normal']} / {THRESHOLDS['vibration_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vibration_chart(DF), use_container_width=True)
    
    with col2:
        status_class = "status-normal" if statuses["Temperatura"] == "Normal" else "status-alerta" if statuses["Temperatura"] == "Alerta" else "status-critico"
        st.markdown(f"""<div class="metric-card {status_class}">
            <div style="font-size:1.1rem;font-weight:800;color:white;margin-bottom:8px;">TEMPERATURA</div>
            <div style="font-size:2.5rem;font-weight:800;margin:10px 0;color:white;">{latest['temperatura_c']:.1f} <span style="font-size:1rem;">°C</span></div>
            <div style="font-size:1.2rem;color:white;font-weight:bold;">{statuses['Temperatura'].upper()}</div>
            <div style="font-size:0.8rem;color:white;margin-top:8px;opacity:0.9;">Ref: {THRESHOLDS['temperature_normal']} / {THRESHOLDS['temperature_alert']}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_temperature_chart(DF), use_container_width=True)
    
    with col3:
        status_class = "status-normal" if statuses["Presion de vacio"] == "Normal" else "status-alerta" if statuses["Presion de vacio"] == "Alerta" else "status-critico"
        st.markdown(f"""<div class="metric-card {status_class}">
            <div style="font-size:1.1rem;font-weight:800;color:white;margin-bottom:8px;">PRESION DE VACIO</div>
            <div style="font-size:2.5rem;font-weight:800;margin:10px 0;color:white;">{latest['presion_vacio_kpa']:.1f} <span style="font-size:1rem;">kPa</span></div>
            <div style="font-size:1.2rem;color:white;font-weight:bold;">{statuses['Presion de vacio'].upper()}</div>
            <div style="font-size:0.8rem;color:white;margin-top:8px;opacity:0.9;">Mas negativo = mejor</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_vacuum_chart(DF), use_container_width=True)
    
    with col4:
        status_class = "status-normal" if latest["estado"] == "Normal" else "status-alerta" if latest["estado"] == "Alerta" else "status-critico"
        st.markdown(f"""<div class="metric-card {status_class}">
            <div style="font-size:1.1rem;font-weight:800;color:white;margin-bottom:8px;">ESTADO GLOBAL</div>
            <div style="font-size:2.5rem;font-weight:800;margin:10px 0;color:white;">{latest['estado'].upper()}</div>
            <div style="font-size:1.2rem;color:white;">IR: {latest['indice_riesgo']:.1f}/100</div>
            <div style="font-size:0.8rem;color:white;margin-top:8px;opacity:0.9;">Avance: {st.session_state.sim_idx}/{max_idx}</div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(create_risk_chart(DF), use_container_width=True)
    
    alarms = get_alarms(latest)
    if alarms:
        st.markdown(f"<h3 style='margin-top:30px;color:{COLORS['texto_oscuro']};'>🚨 Alarmas Activas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            ac = "alarm-critical" if level == "Critico" else ""
            icon = "🔴" if level == "Critico" else "🟡"
            color = COLORS["rojo"] if level == "Critico" else COLORS["amarillo"]
            st.markdown(f"""<div class="alarm-banner {ac}">
                <div style="font-weight:bold;font-size:1.1rem;color:{color};">{icon} {level}: {name}</div>
                <div style="margin-top:5px;">{name} fuera de rango: <strong>{value}</strong></div>
            </div>""", unsafe_allow_html=True)

# ============================================================================
# TAB 2: DIAGNOSTICO
# ============================================================================

with tabs[1]:
    st.markdown("<h2> Diagnostico en Tiempo Real</h2>", unsafe_allow_html=True)
    alarms = get_alarms(latest)
    ec = COLORS["verde"] if latest["estado"] == "Normal" else COLORS["amarillo"] if latest["estado"] == "Alerta" else COLORS["rojo"]
    st.markdown(f"""<div style="background:{COLORS['blanco']};padding:20px;border-radius:16px;border-left:6px solid {ec};margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);">
        <div style="font-size:1.5rem;font-weight:bold;color:{ec};">Estado Actual: {latest['estado'].upper()}</div>
        <div style="font-size:1.2rem;margin-top:10px;color:{COLORS['texto_oscuro']};">Indice de Riesgo: {latest['indice_riesgo']:.1f}/100</div>
    </div>""", unsafe_allow_html=True)
    
    if alarms:
        st.markdown("<h3>🔧 Hipotesis Tecnicas</h3>", unsafe_allow_html=True)
        for level, name, value in alarms:
            if name == "Vibracion": st.markdown("- **Posible desgaste de rodamientos**, desalineacion o lubricacion deficiente.")
            elif name == "Temperatura": st.markdown("- **Posible friccion interna**, lubricacion deficiente o sobrecarga.")
            elif name == "Presion de vacio": st.markdown("- **Posible fuga en linea**, deterioro de sellos o restriccion en succion.")
            else: st.markdown(f"- **Falla detectada**: {value}")
        
        st.markdown("<h3>📋 Pasos Sugeridos</h3>", unsafe_allow_html=True)
        st.markdown("1. Verificar lectura con instrumento calibrado\n2. Inspeccionar visualmente el componente\n3. Revisar manual del fabricante\n4. Comprobar operacion segura\n5. Evaluar necesidad de repuesto")
        
        accion = "Continuar monitoreo" if latest["estado"] == "Normal" else "Programar inspeccion" if latest["estado"] == "Alerta" else "Generar OT Prioridad 0"
        st.markdown(f"<div style='background:{COLORS['blanco']};padding:15px;border-radius:12px;margin-top:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);'><strong>✅ Accion Inmediata:</strong> {accion}</div>", unsafe_allow_html=True)
    else:
        st.success("✅ Sin alarmas activas. Condicion normal.")

# ============================================================================
# TAB 3: ORDENES DE TRABAJO
# ============================================================================

with tabs[2]:
    st.markdown("<h2> Gestion de Ordenes de Trabajo</h2>", unsafe_allow_html=True)
    st.info("Módulo de gestión de órdenes de trabajo - Próximamente")

# ============================================================================
# TAB 4: IMPACTO CIRCULAR - VERSIÓN COMPLETA
# ============================================================================

with tabs[3]:
    st.markdown("<h2>♻️ Panel de Impacto Circular</h2>", unsafe_allow_html=True)
    st.markdown("Registro de decisiones de mantenimiento y su impacto en la conservación de recursos")
    
    # Conexión a base de datos
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Crear tabla mejorada si no existe
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
    
    # Cargar intervenciones
    c.execute("""SELECT * FROM circular_interventions 
                 ORDER BY recorded_date DESC""")
    interventions = [dict(row) for row in c.fetchall()]
    conn.close()
    
    # ========================================================================
    # CÁLCULO DE KPIs AVANZADOS
    # ========================================================================
    
    if interventions:
        df_interventions = pd.DataFrame(interventions)
        
        # KPIs básicos
        total_intervenciones = len(df_interventions)
        masa_total = df_interventions['mass_conserved_kg'].sum() + df_interventions['mass_discarded_kg'].sum()
        masa_conservada = df_interventions['mass_conserved_kg'].sum()
        masa_descartada = df_interventions['mass_discarded_kg'].sum()
        
        # Tasa de circularidad
        tasa_circularidad = (masa_conservada / masa_total * 100) if masa_total > 0 else 0
        
        # Reparados vs reemplazados
        reparados = len(df_interventions[df_interventions['result'].isin(['Reparado', 'Reutilizado'])])
        tasa_reparacion = (reparados / total_intervenciones * 100) if total_intervenciones > 0 else 0
        
        # Indicadores económicos
        costo_total_reparacion = df_interventions['costo_reparacion_eur'].sum()
        costo_total_reemplazo = df_interventions['costo_reemplazo_nuevo_eur'].sum()
        ahorro_total = costo_total_reemplazo - costo_total_reparacion
        roi_circular = ((ahorro_total - costo_total_reparacion) / costo_total_reparacion * 100) if costo_total_reparacion > 0 else 0
        
        # Indicadores ambientales
        co2_total_evitado = df_interventions['co2_evitado_kg'].sum()
        # Equivalencias
        arboles_equivalentes = co2_total_evitado / 22  # 1 árbol absorbe ~22 kg CO2/año
        autos_retirados = co2_total_evitado / 4600  # 1 auto emite ~4600 kg CO2/año
        
        # Vida útil extendida
        vida_util_total = df_interventions['vida_util_extendida_horas'].sum()
        
        # Tasa de éxito de reparaciones
        if 'disponibilidad_post_reparacion_pct' in df_interventions.columns:
            avg_disponibilidad = df_interventions['disponibilidad_post_reparacion_pct'].mean()
        else:
            avg_disponibilidad = 0
        
        # ====================================================================
        # TARJETAS DE KPI PRINCIPALES
        # ====================================================================
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🔄 Tasa de Circularidad",
                value=f"{tasa_circularidad:.1f}%",
                delta=f"{masa_conservada:.0f} kg conservados",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                label="🌍 CO₂ Evitado",
                value=f"{co2_total_evitado:.0f} kg",
                delta=f"≈ {arboles_equivalentes:.0f} árboles/año",
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                label="💰 Ahorro Total",
                value=f"€ {ahorro_total:,.0f}",
                delta=f"ROI: {roi_circular:.0f}%",
                delta_color="normal" if ahorro_total > 0 else "inverse"
            )
        
        with col4:
            st.metric(
                label="✅ Tasa de Éxito Reparaciones",
                value=f"{avg_disponibilidad:.1f}%" if avg_disponibilidad > 0 else "N/A",
                delta=f"{reparados} reparaciones",
                delta_color="normal"
            )
        
        st.divider()
        
        # ====================================================================
        # FILTROS Y SELECCIÓN DE ACTIVO
        # ====================================================================
        
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        
        with col_f1:
            asset_filter = st.selectbox(
                "Filtrar por activo:",
                options=["Todos"] + list(ASSETS.keys()),
                key="circular_asset_filter"
            )
        
        with col_f2:
            date_filter = st.selectbox(
                "Período:",
                options=["Todos", "Últimos 30 días", "Últimos 90 días", "Último año"],
                key="circular_date_filter"
            )
        
        with col_f3:
            decision_filter = st.multiselect(
                "Tipo de decisión:",
                options=["Inspección", "Reparación", "Reemplazo Parcial", "Reemplazo Total"],
                default=["Inspección", "Reparación", "Reemplazo Parcial", "Reemplazo Total"],
                key="circular_decision_filter"
            )
        
        # Aplicar filtros
        df_filtered = df_interventions.copy()
        
        if asset_filter != "Todos":
            df_filtered = df_filtered[df_filtered['asset_name'] == asset_filter]
        
        if decision_filter:
            df_filtered = df_filtered[df_filtered['decision'].isin(decision_filter)]
        
        if date_filter != "Todos":
            df_filtered['recorded_date'] = pd.to_datetime(df_filtered['recorded_date'])
            today = datetime.now()
            if date_filter == "Últimos 30 días":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=30)]
            elif date_filter == "Últimos 90 días":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=90)]
            elif date_filter == "Último año":
                df_filtered = df_filtered[df_filtered['recorded_date'] >= today - timedelta(days=365)]
        
        # ====================================================================
        # GRÁFICOS Y VISUALIZACIONES
        # ====================================================================
        
        # Fila 1: Gráficos principales
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("📊 Tendencia Mensual")
            
            # Agrupar por mes
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
            st.subheader(" Distribución por Decisión")
            
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
        
        # Fila 2: Más gráficos
        col_g3, col_g4 = st.columns(2)
        
        with col_g3:
            st.subheader("🏆 Top 5 Componentes Más Circulares")
            
            if not df_filtered.empty:
                df_componentes = df_filtered.groupby('component').agg({
                    'mass_conserved_kg': 'sum',
                    'id': 'count'
                }).reset_index()
                df_componentes.columns = ['Componente', 'Masa Conservada (kg)', 'Intervenciones']
                df_componentes['Tasa Circularidad'] = (
                    df_componentes['Masa Conservada (kg)'] / 
                    (df_componentes['Masa Conservada (kg)'] + 1) * 100
                )
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
            st.subheader("💰 Ahorro Acumulado")
            
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
                    yaxis_title="Ahorro (€)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_area, use_container_width=True)
        
        st.divider()
        
        # ====================================================================
        # INSIGHTS Y RECOMENDACIONES AUTOMÁTICAS
        # ====================================================================
        
        st.subheader(" Insights y Recomendaciones")
        
        if not df_filtered.empty:
            # Análisis por componente
            for componente in df_filtered['component'].unique():
                df_comp = df_filtered[df_filtered['component'] == componente]
                
                tasa_exito = len(df_comp[df_comp['result'].isin(['Reparado', 'Reutilizado'])]) / len(df_comp) * 100
                
                if tasa_exito >= 80:
                    st.success(f"✅ **{componente}**: {tasa_exito:.0f}% tasa de reparación exitosa - **Recomendación**: Priorizar reparación sobre reemplazo")
                elif tasa_exito <= 40:
                    st.warning(f"⚠️ **{componente}**: Solo {tasa_exito:.0f}% de éxito en reparación - **Recomendación**: Evaluar cambio de tecnología o mantener stock de repuestos")
                
                # Análisis económico
                if 'costo_reparacion_eur' in df_comp.columns and 'costo_reemplazo_nuevo_eur' in df_comp.columns:
                    costo_rep = df_comp['costo_reparacion_eur'].sum()
                    costo_rep_new = df_comp['costo_reemplazo_nuevo_eur'].sum()
                    ahorro = costo_rep_new - costo_rep
                    pct_ahorro = (ahorro / costo_rep_new * 100) if costo_rep_new > 0 else 0
                    
                    if ahorro > 0:
                        st.info(f"💰 **{componente}**: Inversión reparación €{costo_rep:,.0f} vs Reemplazo €{costo_rep_new:,.0f} = **Ahorro €{ahorro:,.0f} ({pct_ahorro:.0f}%)**")
        
        # ====================================================================
        # BENCHMARKS
        # ====================================================================
        
        st.divider()
        st.subheader("📈 Benchmarks de Desempeño")
        
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
                label="CO₂ Evitado vs Meta",
                value=f"{co2_total_evitado:.0f} kg",
                delta=f"Equivalente a {arboles_equivalentes:.0f} árboles",
                delta_color="normal"
            )
        
        with col_b3:
            st.metric(
                label="Alineación SDG 12",
                value="Producción Responsable",
                delta="Objetivo: Reducción 30% residuos",
                delta_color="normal"
            )
        
        # ====================================================================
        # TABLA DETALLADA
        # ====================================================================
        
        st.divider()
        st.subheader(" Registro Detallado de Intervenciones")
        
        # Columnas a mostrar
        cols_to_show = [
            'recorded_date', 'ot_id', 'asset_name', 'component', 'decision', 
            'result', 'mass_conserved_kg', 'mass_discarded_kg'
        ]
        
        # Agregar columnas económicas si existen
        if 'costo_reparacion_eur' in df_filtered.columns:
            cols_to_show.append('costo_reparacion_eur')
        if 'costo_reemplazo_nuevo_eur' in df_filtered.columns:
            cols_to_show.append('costo_reemplazo_nuevo_eur')
        if 'co2_evitado_kg' in df_filtered.columns:
            cols_to_show.append('co2_evitado_kg')
        
        df_display = df_filtered[cols_to_show].copy()
        
        # Formatear nombres de columnas
        column_names = {
            'recorded_date': 'Fecha',
            'ot_id': 'OT ID',
            'asset_name': 'Activo',
            'component': 'Componente',
            'decision': 'Decisión',
            'result': 'Resultado',
            'mass_conserved_kg': 'Masa Conservada (kg)',
            'mass_discarded_kg': 'Masa Descartada (kg)',
            'costo_reparacion_eur': 'Costo Reparación (€)',
            'costo_reemplazo_nuevo_eur': 'Costo Reemplazo (€)',
            'co2_evitado_kg': 'CO₂ Evitado (kg)'
        }
        df_display = df_display.rename(columns=column_names)
        
        st.dataframe(
            df_display.sort_values('Fecha', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Botón de exportación
        csv = df_display.to_csv(index=False, sep=';').encode('utf-8')
        st.download_button(
            label=" Exportar a CSV",
            data=csv,
            file_name=f"impacto_circular_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
    else:
        st.info(" No hay intervenciones registradas. Complete órdenes de trabajo para registrar el impacto circular.")
        
        # Ejemplo de cómo registrar
        st.markdown("""
        ### ¿Cómo registrar intervenciones?
        
        1. **Complete una Orden de Trabajo** en el módulo correspondiente
        2. **Al cerrar la OT**, seleccione:
           - Componente intervenido
           - Decisión tomada (Inspección/Reparación/Reemplazo)
           - Masa conservada y descartada
           - Costos asociados
           - Vida útil extendida
        3. **El sistema calculará automáticamente**:
           - Tasa de circularidad
           - CO₂ evitado
           - Ahorro económico
           - ROI de la economía circular
        """)

# ============================================================================
# TAB 5: KPIs
# ============================================================================

with tabs[4]:
    st.markdown("<h2 style='text-align:center;'> KPIs e Indicadores</h2>", unsafe_allow_html=True)
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
