import streamlit as st
from supabase import create_client, Client
import pandas as pd
import numpy as np
import bcrypt
import random
import time
from datetime import datetime, date, timedelta
import pytz

# ==========================================
# 🔑 CONEXIÓN A SUPABASE (DESDE SECRETS)
# ==========================================
try:
    SUPABASE_URL = st.secrets["supabase_url"]
    SUPABASE_KEY = st.secrets["supabase_key"]
except Exception:
    SUPABASE_URL = "https://ogaoizovgrfabvmxyuee.supabase.co"
    SUPABASE_KEY = "sb_publishable_SwDaoOYxxdl2oCm_c04S3w_Wf09EGl2"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==========================================
# ⏰ RELOJ OFICIAL EN ZONA HORARIA DE ARGENTINA (CONSOLIDADOR)
# ==========================================
TZ_ARG = pytz.timezone("America/Argentina/Buenos_Aires")

def obtener_fecha_hora_actual():
    """Retorna el objeto datetime localizado exactamente en Argentina."""
    return datetime.now(TZ_ARG)

def obtener_fecha_iso_argentina():
    """Retorna la fecha y hora formateada de forma segura para base de datos (con timezone offset)."""
    return obtener_fecha_hora_actual().strftime("%Y-%m-%d %H:%M:%S-03:00")

# ==========================================
# 📊 METRICAS DE CARGA Y CÁLCULOS AVANZADOS
# ==========================================
def calcular_srpe(rpe: float, duracion: float) -> float:
    """Calcula el Session RPE (Carga de la Sesión)."""
    return float(rpe * duracion)

def calcular_e1rm(peso: float, reps: int) -> float:
    """Estimación de 1RM por Epley (Brzycki Modificado)."""
    if reps == 0: return 0.0
    if reps == 1: return float(peso)
    return round(peso * (1 + reps / 30.0), 1)

def calcular_acwr(cargas_diarias: list) -> dict:
    """
    Calcula el Acute:Chronic Workload Ratio (ACWR).
    - Carga Aguda: Suma de sRPE de los últimos 7 días.
    - Carga Crónica: Promedio semanal de los últimos 28 días.
    """
    if not cargas_diarias or len(cargas_diarias) == 0:
        return {"aguda": 0.0, "cronica": 0.0, "acwr": 1.0, "estado": "Sin datos", "color": "#94A3B8"}
    
    hoy = obtener_fecha_hora_actual().date()
    df = pd.DataFrame(cargas_diarias)
    df["fecha_limpia"] = df["fecha"].apply(lambda x: str(x).split(" ")[0])
    df["fecha_limpia"] = pd.to_datetime(df["fecha_limpia"]).dt.date
    
    # Rango de fechas
    fecha_limite_cronica = hoy - timedelta(days=28)
    fecha_limite_aguda = hoy - timedelta(days=7)
    
    df_diario = df.groupby("fecha_limpia")["srpe"].sum().reset_index()
    
    # Carga Aguda (7 días)
    df_aguda = df_diario[df_diario["fecha_limpia"] >= fecha_limite_aguda]
    carga_aguda = df_aguda["srpe"].sum()
    
    # Carga Crónica (4 semanas)
    df_cronica = df_diario[(df_diario["fecha_limpia"] >= fecha_limite_cronica)]
    carga_cronica = df_cronica["srpe"].sum() / 4.0 if not df_cronica.empty else 1.0
    if carga_cronica == 0: carga_cronica = 1.0
    
    acwr = round(carga_aguda / carga_cronica, 2)
    
    # Clasificación por semáforo de lesión
    if acwr < 0.8:
        estado = "Subentrenamiento ⚠️ (Bajo estímulo)"
        color = "#38BDF8"
    elif 0.8 <= acwr <= 1.3:
        estado = "Zona Segura ✅ (Rendimiento Óptimo)"
        color = "#4ADE80"
    elif 1.3 < acwr <= 1.5:
        estado = "Zona de Transición 🟡 (Alerta)"
        color = "#FACC15"
    else:
        estado = "Peligro de Lesión 🚨 (Sobrecarga Aguda)"
        color = "#F87171"
        
    return {"aguda": round(carga_aguda, 1), "cronica": round(carga_cronica, 1), "acwr": acwr, "estado": estado, "color": color}

# ==========================================
# 🔑 SEGURIDAD, UTILS Y EDAD
# ==========================================
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verificar_password(password_ingresada: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(password_ingresada.encode(), hash_guardado.encode())
    except (ValueError, AttributeError):
        return password_ingresada == hash_guardado

def calcular_edad(fecha_nac_str):
    try:
        if not fecha_nac_str or fecha_nac_str == "None":
            return 0
        fecha_nac = datetime.strptime(fecha_nac_str, "%Y-%m-%d").date()
        hoy = obtener_fecha_hora_actual().date()
        return hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    except Exception:
        return 0

def obtener_frase_motivacional(dias_acumulados):
    frases = [
        "¡Excelente primer paso! El camino a la alta competencia empieza hoy. 🚀",
        "¡Buen comienzo! La constancia es el secreto del rendimiento. 💪",
        f"¡Suma y sigue! Ya van {dias_acumulados} entrenamientos este mes. ¡Buen ritmo! ⚡",
        f"¡Cuerpo e intención enfocados! Llevás {dias_acumulados} sesiones. No aflojes. 🔥",
        f"¡Tremenda disciplina! {dias_acumulados} días dándolo todo. Te estás volviendo imparable. 👑",
        f"El esfuerzo de hoy es el rendimiento del mañana. ¡{dias_acumulados} sesiones acumuladas! 🏆",
        f"¡Nivel Élite! 🔥 {dias_acumulados} entrenamientos en el mes. Sos un ejemplo de consistencia. 🦅"
    ]
    return random.choice(frases)

# ==========================================
# 📸 STORAGE (SUBIR FOTO DE PERFIL)
# ==========================================
def subir_foto_perfil(archivo_imagen, usuario_slug) -> str:
    try:
        usuario_limpio = str(usuario_slug).replace(" ", "_").lower()
        extension = archivo_imagen.name.split(".")[-1]
        nombre_archivo = f"{usuario_limpio}_{int(time.time())}.{extension}"
        bytes_datos = archivo_imagen.getvalue()
        
        supabase.storage.from_("fotos_perfil").upload(
            path=nombre_archivo,
            file=bytes_datos,
            file_options={"content-type": f"image/{extension}"}
        )
        return supabase.storage.from_("fotos_perfil").get_public_url(nombre_archivo)
    except Exception as e:
        st.error(f"⚠️ Error al procesar o subir la foto: {e}")
        return None

# ==========================================
# 0. CONFIGURACIÓN INICIAL
# ==========================================
DIAS_PLANIF = ["📅 Día 1", "📅 Día 2", "🏃 Día Aeróbico"]
SUB_BLOQUES = ["🔥 Entrada en Calor", "⚡ Bloque Principal", "🧘 Bloque Final / Vuelta a la Calma"]
ADMIN_USER = "giuliano"
ADMIN_PASS_PLANA = "magpower2026"
AVATAR_PREDETERMINADO = "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&q=80&w=200&h=200"

if "borrador_rutina" not in st.session_state:
    st.session_state["borrador_rutina"] = []

st.set_page_config(page_title="TrainApp - Prof. Giuliano Cocconi", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    div[data-testid="column"] { padding: 1px !important; }
    input { text-align: center !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }
    .profile-pic { border-radius: 50%; object-fit: cover; border: 3px solid #84CC16; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>⚡ TRAINAPP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #84CC16; font-weight: bold; letter-spacing: 1px; margin-top: 0px;'>PROF. GIULIANO COCCONI - PREPARACIÓN FÍSICA PERSONALIZADA</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# 🔑 LOGIN Y REGISTRO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""

if not st.session_state["autenticado"]:
    login_mode = st.radio("Opción:", ["🔑 Iniciar Sesión", "👥 ¿Sos nuevo? Registrate acá 👤"], horizontal=True, label_visibility="collapsed")
    
    if login_mode == "🔑 Iniciar Sesión":
        st.markdown("<h3 style='text-align: center;'>🔐 Iniciar Sesión</h3>", unsafe_allow_html=True)
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            with st.form("form_login"):
                input_user = st.text_input("Usuario:").strip().lower()
                input_pass = st.text_input("Contraseña:", type="password")
                btn_login = st.form_submit_button("Entrar al Sistema 🚀", use_container_width=True)
            if btn_login:
                if input_user == ADMIN_USER and input_pass == ADMIN_PASS_PLANA:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = "Prof. Giuliano"
                    st.session_state["rol_actual"] = "admin"
                    st.rerun()
                else:
                    res = supabase.table("alumnos").select("nombre_apellido, contrasena, estado").eq("usuario", input_user).execute()
                    user_db = res.data
                    if user_db and verificar_password(input_pass, user_db[0]["contrasena"]):
                        if user_db[0]["estado"] == "pendiente":
                            st.warning("⏳ Tu cuenta está pendiente de aprobación.")
                        else:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = user_db[0]["nombre_apellido"]
                            st.session_state["rol_actual"] = "atleta"
                            st.rerun()
                    else: st.error("❌ Usuario o contraseña incorrectos.")
    else:
        st.markdown("<h3 style='text-align: center;'>📝 Registro de Atleta</h3>", unsafe_allow_html=True)
        col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
        with col_r2:
            reg_nombre = st.text_input("Nombre y Apellido completo:")
            reg_user = st.text_input("Nombre de Usuario (para ingresar):").strip().lower()
            reg_pass = st.text_input("Contraseña de Acceso:", type="password")
            reg_nacimiento = st.date_input("Fecha de Nacimiento:", value=date(2000, 1, 1))
            reg_peso = st.number_input("Peso Actual (kg):", min_value=1.0, value=70.0)
            reg_altura = st.number_input("Altura Actual (m):", min_value=0.5, value=1.75)
            reg_deporte = st.text_input("Deporte / Disciplina:")
            reg_obj = st.text_area("Objetivo principal:")
            foto_subida = st.file_uploader("📸 Subí tu Foto de Perfil (Opcional):", type=["jpg", "jpeg", "png", "webp"])
            
            btn_reg_submit = st.button("Enviar Registro 👤", use_container_width=True, type="primary")
            if btn_reg_submit:
                if reg_nombre.strip() == "" or reg_user.strip() == "" or reg_pass == "":
                    st.error("❌ Nombre, Usuario y Contraseña son obligatorios.")
                else:
                    try:
                        foto_final = AVATAR_PREDETERMINADO
                        if foto_subida:
                            url = subir_foto_perfil(foto_subida, reg_user)
                            if url: foto_final = url
                        supabase.table("alumnos").insert({
                            "nombre_apellido": reg_nombre.strip(), "usuario": reg_user,
                            "contrasena": hashear_password(reg_pass), "fecha_nacimiento": reg_nacimiento.strftime("%Y-%m-%d"),
                            "peso": reg_peso, "altura": reg_altura, "deporte": reg_deporte, "objetivo": reg_obj, 
                            "estado": "pendiente", "foto_perfil": foto_final
                        }).execute()
                        st.success("🎉 ¡Registro enviado! Quedó pendiente de aprobación.")
                    except Exception as e: st.error(f"❌ Error: {e}")
    st.stop()

# ==========================================
# 👤 BARRA LATERAL (ZONA HORARIA SYNC)
# ==========================================
if st.session_state["rol_actual"] == "admin":
    st.sidebar.markdown(f"👤 Coach: **{st.session_state['usuario_actual']}**")
else:
    st.sidebar.markdown(f"🏃 Atleta: **{st.session_state['usuario_actual']}**")
    mes_actual_str = obtener_fecha_hora_actual().strftime("%m-%Y")
    res_asist = supabase.table("asistencia").select("id", count="exact").eq("alumno", st.session_state["usuario_actual"]).eq("mes_ano", mes_actual_str).execute()
    racha_act = res_asist.count if res_asist.count is not None else 0
    st.sidebar.markdown(f"📆 Asistencias este mes: **{racha_act}**")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["borrador_rutina"] = []
    st.rerun()

# ==========================================
# 🔔 MONITOR EN VIVO Y ACTUALIZACIÓN AUTOMÁTICA (FRAGMENT)
# ==========================================
# Se mantiene activo el auto-refresh cada 15 segundos para mantener notificaciones y datos al día
@st.fragment(run_every=15)
def monitor_en_vivo():
    if st.session_state["rol_actual"] == "admin":
        res_n = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", "giuliano").eq("leido", False).execute()
        if res_n.data:
            for noti in res_n.data:
                # 🔔 Notificación Toast/Push-up en pantalla
                st.toast(f"🔔 {noti['mensaje']}", icon="🏃")
                supabase.table("notificaciones").update({"leido": True}).eq("id", noti["id"]).execute()
                time.sleep(0.5)
                st.rerun()
    elif st.session_state["rol_actual"] == "atleta":
        alumno_log = st.session_state["usuario_actual"]
        res_n_at = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", alumno_log).eq("leido", False).execute()
        if res_n_at.data:
            for noti in res_n_at.data:
                # 🔔 Notificación Toast/Push-up en pantalla
                st.toast(f"🔔 {noti['mensaje']}", icon="🏋️‍♂️")
                supabase.table("notificaciones").update({"leido": True}).eq("id", noti["id"]).execute()
                time.sleep(0.5)
                st.rerun()

monitor_en_vivo()

# ==========================================
# 📱 INTERFAZ DE ENTRENAMIENTO (POR BLOQUES)
# ==========================================
def renderizar_tabla_entrenamiento(nombre_atleta, es_espejo=False):
    sufijo = "esp" if es_espejo else "atl"
    res_rut = supabase.table("rutinas_asignadas").select("*").eq("alumno", nombre_atleta).execute()
    rutina_completa = res_rut.data
    if not rutina_completa:
        st.info("No tenés ninguna rutina asignada todavía.")
        return
    
    st.markdown(f"### 📋 Plan: {rutina_completa[0]['nombre_rutina']}", unsafe_allow_html=True)
    dia_a_entrenar = st.selectbox("📆 Día:", options=DIAS_PLANIF, key=f"sb_dia_{sufijo}")
    
    entradas_alumno = {}
    visibles = False
    
    for sub_b in SUB_BLOQUES:
        llave = f"{dia_a_entrenar}|{sub_b}"
        ejs = [r for r in rutina_completa if r["bloque"] == llave]
        if ejs:
            visibles = True
            st.markdown(f"<h4 style='color: #CCFF00; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{sub_b}</h4>", unsafe_allow_html=True)
            es_secundario = "Principal" not in sub_b
            
            for idx, ej in enumerate(ejs):
                nombre_ej = ej["ejercicio"]
                series_obj = int(ej["series_objetivo"])
                reps_obj = ej["reps_objetivo"]
                
                res_v = supabase.table("biblioteca_ejercicios").select("link_video").eq("nombre", nombre_ej).execute()
                link_video = res_v.data[0]["link_video"] if res_v.data else ""
                
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1: st.markdown(f"🏋️‍♂️ **{nombre_ej}** (`{series_obj}S x {reps_obj}R`)")
                    with col2:
                        if link_video and "http" in link_video: st.markdown(f"[🎥 Video]({link_video})")
                    
                    if es_secundario:
                        completado = st.checkbox("✅ Completado", key=f"chk_{sufijo}_{idx}_{nombre_ej.replace(' ','_')}")
                        if completado:
                            for s in range(1, series_obj + 1):
                                entradas_alumno[(nombre_ej, s)] = {"ejercicio": nombre_ej, "serie": s, "kilos": 0.0, "reps_reales": 10}
                    else:
                        cols = st.columns(series_obj)
                        for s in range(1, series_obj + 1):
                            with cols[s-1]:
                                st.markdown(f"<p style='text-align: center; color: #CCFF00;'>S{s}</p>", unsafe_allow_html=True)
                                k = st.number_input("kg", key=f"k_{sufijo}_{idx}_{s}", label_visibility="collapsed", step=0.5)
                                r = st.number_input("R", key=f"r_{sufijo}_{idx}_{s}", label_visibility="collapsed", value=int(reps_obj) if reps_obj.isdigit() else 5)
                                entradas_alumno[(nombre_ej, s)] = {"ejercicio": nombre_ej, "serie": s, "kilos": k, "reps_reales": r}
                    
                    notas = st.text_input("Notas:", key=f"not_{sufijo}_{idx}_{nombre_ej.replace(' ','_')}")
                    for s in range(1, series_obj + 1):
                        if (nombre_ej, s) in entradas_alumno: entradas_alumno[(nombre_ej, s)]["notas"] = notas
                    st.divider()

    if visibles:
        st.markdown("#### 📊 Evaluación de la Carga de Trabajo")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
            rpe = st.select_slider("RPE Global de la Sesión (Esfuerzo Percibido 1-10):", options=list(range(1, 11)), value=7)
        with col_ev2:
            duracion = st.number_input("Duración de la Sesión (minutos):", min_value=1, value=60)
            
        srpe_calculado = calcular_srpe(rpe, duracion)
        st.info(f"💡 Carga de entrenamiento calculada (sRPE): **{srpe_calculado}** unidades arbitrarias (RPE {rpe} x {duracion} min).")
        
        if st.button("🏁 FINALIZAR ENTRENAMIENTO", use_container_width=True, type="primary"):
            fecha_hoy_limpia = obtener_fecha_hora_actual().strftime("%Y-%m-%d")
            
            # Verificamos contra la tabla Asistencia que solo guarda la fecha limpia para evitar duplicados
            res_comp = supabase.table("asistencia").select("id").eq("alumno", nombre_atleta).eq("fecha", fecha_hoy_limpia).execute()
            
            if res_comp.data: 
                st.error("⚠️ Ya registraste una sesión hoy.")
            else:
                validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                if not validos: 
                    st.warning("Cargá marcas antes de guardar.")
                else:
                    hora_limpia = obtener_fecha_hora_actual().strftime("%H:%M")
                    mes_ano = obtener_fecha_hora_actual().strftime("%m-%Y")
                    
                    for d in validos:
                        fecha_y_hora_texto = f"{fecha_hoy_limpia} {hora_limpia}"
                        
                        supabase.table("registros_entrenamiento").insert({
                            "fecha": fecha_y_hora_texto, 
                            "alumno": nombre_atleta, 
                            "nombre_rutina": rutina_completa[0]["nombre_rutina"],
                            "ejercicio": d["ejercicio"], 
                            "nro_serie": d["serie"], 
                            "kilos": d["kilos"],
                            "reps_reales": d["reps_reales"], 
                            "notas": d.get("notas", ""), 
                            "rpe_global_sesion": rpe, 
                            "duracion_minutos": duracion, 
                            "srpe": srpe_calculado
                        }).execute()
                    
                    # Guardamos asistencia con fecha limpia
             