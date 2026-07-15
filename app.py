import streamlit as st
from supabase import create_client, Client
import pandas as pd
import bcrypt
import random
from datetime import datetime, date

# ==========================================
# 🔑 CONEXIÓN A SUPABASE (DESDE SECRETS)
# ==========================================
try:
    SUPABASE_URL = st.secrets["supabase_url"]
    SUPABASE_KEY = st.secrets["supabase_key"]
except Exception:
    # Fallback local o por si no lee los secrets temporalmente
    SUPABASE_URL = "https://ogaoizovgrfabvmxyuee.supabase.co"
    SUPABASE_KEY = "sb_publishable_SwDaoOYxxdl2oCm_c04S3w_Wf09EGl2"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==========================================
# 🔑 HELPERS DE CONTRASEÑAS (BCRYPT)
# ==========================================
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verificar_password(password_ingresada: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(password_ingresada.encode(), hash_guardado.encode())
    except (ValueError, AttributeError):
        return password_ingresada == hash_guardado

# ==========================================
# 📈 CALCULADORA DE 1RM ESTIMADO (EPLEY)
# ==========================================
def calcular_e1rm(peso, reps):
    if reps == 0: return 0.0
    if reps == 1: return float(peso)
    return round(peso * (1 + reps / 30.0), 1)

def calcular_edad(fecha_nac_str):
    try:
        if not fecha_nac_str or fecha_nac_str == "None":
            return 0
        fecha_nac = datetime.strptime(fecha_nac_str, "%Y-%m-%d").date()
        hoy = date.today()
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
# 0. CONSTANTES GLOBALES Y SESIÓN BORRADOR
# ==========================================
DIAS_PLANIF = ["📅 Día 1", "📅 Día 2", "🏃 Día Aeróbico"]
SUB_BLOQUES = ["🔥 Entrada en Calor", "⚡ Bloque Principal", "🧘 Bloque Final / Vuelta a la Calma"]

if "borrador_rutina" not in st.session_state:
    st.session_state["borrador_rutina"] = []

# ==========================================
# 🔑 ACCESO DIRECTO DE ADMINISTRADOR (FUERZA BRUTA)
# ==========================================
ADMIN_USER = "giuliano"
ADMIN_PASS_PLANA = "magpower2026"

# ==========================================
# 2. CONFIGURACIÓN VISUAL GENERAL (UI)
# ==========================================
st.set_page_config(page_title="TrainApp - Prof. Giuliano Cocconi", page_icon="⚡", layout="wide")

# Estilos CSS específicos para compactar la visualización móvil horizontal
st.markdown("""
<style>
    div[data-testid="column"] {
        padding: 1px !important;
    }
    input {
        text-align: center !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>⚡ TRAINAPP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #84CC16; font-weight: bold; letter-spacing: 1px; margin-top: 0px;'>PROF. GIULIANO COCCONI - PREPARACIÓN FÍSICA PERSONALIZADA</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# 🔑 LOGIN Y AUTOREGISTRO
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
                # Verificación directa de administrador (Fuerza Bruta)
                if input_user == ADMIN_USER and input_pass == ADMIN_PASS_PLANA:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = "Prof. Giuliano"
                    st.session_state["rol_actual"] = "admin"
                    st.rerun()
                else:
                    # Si no es admin, busca en Supabase si es un atleta
                    res = supabase.table("alumnos").select("nombre_apellido, contrasena, estado").eq("usuario", input_user).execute()
                    user_db = res.data
                    if user_db and verificar_password(input_pass, user_db[0]["contrasena"]):
                        if user_db[0]["estado"] == "pendiente":
                            st.warning("⏳ Tu cuenta está pendiente de aprobación por el Prof. Giuliano.")
                        else:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = user_db[0]["nombre_apellido"]
                            st.session_state["rol_actual"] = "atleta"
                            st.rerun()
                    else: 
                        st.error("❌ Usuario o contraseña incorrectos.")
    else:
        st.markdown("<h3 style='text-align: center;'>📝 Registro de Atleta</h3>", unsafe_allow_html=True)
        col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
        with col_r2:
            with st.form("autoregistro_alumno", clear_on_submit=True):
                reg_nombre = st.text_input("Nombre y Apellido completo:")
                reg_user = st.text_input("Nombre de Usuario (para ingresar):").strip().lower()
                reg_pass = st.text_input("Contraseña de Acceso:", type="password")
                reg_nacimiento = st.date_input("Fecha de Nacimiento:", value=date(2000, 1, 1))
                reg_peso = st.number_input("Peso Actual (kg):", min_value=1.0, value=70.0)
                reg_altura = st.number_input("Altura Actual (m):", min_value=0.5, value=1.75)
                reg_deporte = st.text_input("Deporte / Disciplina:")
                reg_obj = st.text_area("Objetivo principal:")
                btn_reg_submit = st.form_submit_button("Enviar Registro 👤", use_container_width=True)
                
            if btn_reg_submit:
                if reg_nombre.strip() == "" or reg_user.strip() == "" or reg_pass == "":
                    st.error("❌ Todos los campos obligatorios deben estar completos.")
                else:
                    try:
                        supabase.table("alumnos").insert({
                            "nombre_apellido": reg_nombre.strip(), "usuario": reg_user,
                            "contrasena": hashear_password(reg_pass), "fecha_nacimiento": reg_nacimiento.strftime("%Y-%m-%d"),
                            "peso": reg_peso, "altura": reg_altura, "deporte": reg_deporte, "objetivo": reg_obj, "estado": "pendiente"
                        }).execute()
                        st.success(f"🎉 ¡Registro enviado, {reg_nombre}! Quedó pendiente de aprobación.")
                    except Exception: st.error("❌ El usuario o nombre ya se encuentran registrados.")
    st.stop()

st.sidebar.markdown(f"👤 Coach: **{st.session_state['usuario_actual']}**")

if st.session_state["rol_actual"] == "atleta":
    mes_actual_str = datetime.now().strftime("%m-%Y")
    res_asist = supabase.table("asistencia").select("id", count="exact").eq("alumno", st.session_state["usuario_actual"]).eq("mes_ano", mes_actual_str).execute()
    racha_act = res_asist.count if res_asist.count is not None else len(res_asist.data)
    st.sidebar.markdown(f"📆 Asistencias este mes: **{racha_act}**")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["borrador_rutina"] = []
    st.rerun()

res_aprob = supabase.table("alumnos").select("nombre_apellido").eq("estado", "aprobado").order("nombre_apellido").execute()
lista_alumnos = [f["nombre_apellido"] for f in res_aprob.data]
lista_alumnos_con_neutro = ["- Seleccionar Atleta -"] + lista_alumnos

# ==========================================
# 📱 INTERFAZ ATLETA CON CARGA HORIZONTAL Y HISTORIAL
# ==========================================
def renderizar_tabla_entrenamiento(nombre_atleta, es_espejo=False):
    sufijo = "esp" if es_espejo else "atl"
    
    res_rut = supabase.table("rutinas_asignadas").select("*").eq("alumno", nombre_atleta).execute()
    rutina_completa = res_rut.data
    
    if not rutina_completa:
        st.info("No tenés ninguna rutina asignada para este mes todavía.")
        return
        
    nombre_de_la_rutina = rutina_completa[0]["nombre_rutina"] or "Planificación Mensual"
    if es_espejo: st.warning(f"👀 MODO ESPEJO. Planificación: **{nombre_de_la_rutina}**")
    else: st.markdown(f"### 📋 Plan Mensual: <span style='color: #CCFF00;'>{nombre_de_la_rutina}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    dia_a_entrenar = st.selectbox("📆 ¿Qué día te toca entrenar hoy?", options=DIAS_PLANIF, key=f"sb_dia_atleta_{sufijo}")
    st.markdown("---")

    entradas_alumno = {}
    ejercicios_visibles_en_pantalla = False
    
    for sub_b in SUB_BLOQUES:
        llave_busqueda = f"{dia_a_entrenar}|{sub_b}"
        ejercicios_del_bloque = [r for r in rutina_completa if r["bloque"] == llave_busqueda]
        
        if ejercicios_del_bloque:
            ejercicios_visibles_en_pantalla = True
            st.markdown(f"<h4 style='color: #CCFF00; margin-top: 15px; margin-bottom: 10px; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{sub_b}</h4>", unsafe_allow_html=True)
            
            for idx, ej in enumerate(ejercicios_del_bloque):
                nombre_ejercicio = ej["ejercicio"]
                series_prescritas = int(ej["series_objetivo"])
                reps_prescritas = ej["reps_objetivo"]
                
                res_v = supabase.table("biblioteca_ejercicios").select("link_video").eq("nombre", nombre_ejercicio).execute()
                link_video = res_v.data[0]["link_video"] if res_v.data else ""
                
                # --- OBTENER HISTORIAL DE CARGA ANTERIOR ---
                res_hist_prev = supabase.table("registros_entrenamiento").select("kilos, reps_reales, fecha").eq("alumno", nombre_atleta).eq("ejercicio", nombre_ejercicio).order("id", desc=True).limit(series_prescritas).execute()
                texto_historial = ""
                if res_hist_prev.data:
                    hist_data = res_hist_prev.data
                    detalles = ", ".join([f"{h['reps_reales']}R x {h['kilos']}kg" for h in reversed(hist_data)])
                    texto_historial = f"⏮️ Última sesión ({hist_data[0]['fecha'].split(' ')[0]}): {detalles}"
                else:
                    texto_historial = "⏮️ Sin cargas anteriores registradas para este ejercicio."
                
                with st.container():
                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1: 
                        st.markdown(f"🏋️‍♂️ **{nombre_ejercicio}** | `{series_prescritas}S x {reps_prescritas}R` Prescritas")
                    with col_h2:
                        if link_video and "http" in link_video: st.markdown(f"[🎥 Video]({link_video})")
                    
                    st.markdown(f"<p style='font-size: 0.85rem; color: #94A3B8; margin-top: -8px; margin-bottom: 8px;'>{texto_historial}</p>", unsafe_allow_html=True)
                    
                    # Carga Horizontal Adaptada al celular
                    columnas_visuales = st.columns(series_prescritas)
                    
                    for s in range(1, series_prescritas + 1):
                        with columnas_visuales[s-1]:
                            st.markdown(f"<p style='text-align: center; margin-bottom: 1px; font-weight: bold; color: #CCFF00;'>S{s}</p>", unsafe_allow_html=True)
                            key_id = f"{sufijo}_{nombre_atleta}_{idx}_{nombre_ejercicio.replace(' ', '_')}_s{s}"
                            
                            kilos_input = st.number_input(
                                "kg", min_value=0.0, step=0.5, value=0.0, 
                                key=f"k_{key_id}", label_visibility="collapsed"
                            )
                            
                            try: default_reps = int(reps_prescritas)
                            except: default_reps = 5
                            
                            reps_reales = st.number_input(
                                "R", min_value=0, max_value=100, value=default_reps, 
                                key=f"rep_{key_id}", label_visibility="collapsed"
                            )
                            
                            entradas_alumno[(nombre_ejercicio, s)] = {
                                "ejercicio": nombre_ejercicio, "serie": s, "kilos": kilos_input, "reps_reales": reps_reales
                            }
                    
                    nombre_ej_limpio = nombre_ejercicio.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "")
                    dia_limpio = dia_a_entrenar.replace(" ", "_").replace("📅", "").replace("🏃", "")
                    sub_b_limpio = sub_b.replace(" ", "_").replace("🔥", "").replace("⚡", "").replace("🧘", "")
                    
                    notas_ejercicio = st.text_input(
                        "Anotaciones:", placeholder="Molestia, velocidad percibida...", 
                        key=f"not_{sufijo}_{idx}_{nombre_ej_limpio}_{dia_limpio}_{sub_b_limpio}"
                    )
                    for s in range(1, series_prescritas + 1): entradas_alumno[(nombre_ejercicio, s)]["notes_field"] = notas_ejercicio
                    
                    st.markdown("<hr style='margin: 15px 0px; opacity: 0.15;'/>", unsafe_allow_html=True)
                    
    if not ejercicios_visibles_en_pantalla:
        st.info(f"No tenés ejercicios cargados en el sistema para el día: **{dia_a_entrenar}**.")
        return
        
    st.markdown("<h4 style='color: #84CC16; margin-top: 25px;'>📊 Evaluación General de la Sesión</h4>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1: rpe_global = st.select_slider("¿Qué tan dura estuvo la sesión hoy? (RPE Global):", options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], value=7)
    with col_g2: duracion_min = st.number_input("⏱️ ¿Cuántos minutos duró el entrenamiento?", min_value=1, max_value=300, value=60, step=5)

    if st.button("🏁 FINALIZAR ENTRENAMIENTO Y ENVIAR AL PROFE", use_container_width=True, type="primary", key=f"btn_finalizar_{sufijo}"):
        if es_espejo: st.info("ℹ️ Modo espejo de visualización.")
        else:
            fecha_hoy_texto = datetime.now().strftime("%Y-%m-%d")
            res_comp = supabase.table("registros_entrenamiento").select("id").eq("alumno", nombre_atleta).like("fecha", f"{fecha_hoy_texto}%").execute()
            if res_comp.data: st.error(f"⚠️ Ya registraste una sesión hoy.")
            else:
                datos_validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                if not datos_validos: st.warning("⚠️ Completá marcas antes de guardar.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    mes_ano_actual = datetime.now().strftime("%m-%Y")
                    nombre_reporte_dia = f"{nombre_de_la_rutina} ({dia_a_entrenar})"
                    
                    max_e1rm = 0.0
                    mejor_ej_e1rm = ""
                    
                    for datos in datos_validos:
                        supabase.table("registros_entrenamiento").insert({
                            "fecha": fecha_actual, "alumno": nombre_atleta, "nombre_rutina": nombre_reporte_dia,
                            "ejercicio": datos["ejercicio"], "nro_serie": datos["serie"], "kilos": datos["kilos"],
                            "reps_reales": datos["reps_reales"], "rpe_serie": 0.0, "notas": datos["notes_field"],
                            "rpe_global_sesion": rpe_global, "duracion_minutos": duracion_min
                        }).execute()
                        
                        e1rm_calc = calcular_e1rm(datos["kilos"], datos["reps_reales"])
                        if e1rm_calc > max_e1rm:
                            max_e1rm = e1rm_calc
                            mejor_ej_e1rm = datos["ejercicio"]
                    
                    supabase.table("asistencia").insert({
                        "fecha": fecha_hoy_texto, "mes_ano": mes_ano_actual, "alumno": nombre_atleta
                    }).execute()
                    
                    supabase.table("notificaciones").insert({
                        "destinatario": "giuliano",
                        "mensaje": f"🏃 {nombre_atleta} finalizó su entrenamiento: {nombre_reporte_dia}."
                    }).execute()
                    
                    res_tot = supabase.table("asistencia").select("id", count="exact").eq("alumno", nombre_atleta).eq("mes_ano", mes_ano_actual).execute()
                    total_dias = res_tot.count if res_tot.count is not None else len(res_tot.data)
                    
                    msg_motivacional = obtener_frase_motivacional(total_dias)
                    if max_e1rm > 0:
                        msg_motivacional += f"\n\n🔥 **Hito de Fuerza hoy:** Tu 1RM estimado en *{mejor_ej_e1rm}* llegó a **{max_e1rm} kg**. ¡Excelente!"
                    
                    st.session_state["mensaje_motivacional_pop"] = msg_motivacional
                    st.success("🚀 ¡Entrenamiento enviado correctamente al Profe!")
                    st.rerun()

if "mensaje_motivacional_pop" in st.session_state:
    st.balloons()
    st.toast(st.session_state["mensaje_motivacional_pop"], icon="🏆")
    st.markdown(f"<div style='background-color: #1E293B; border-left: 5px solid #84CC16; padding: 15px; border-radius: 4px; margin-bottom: 20px;'><strong>🏅 DESEMPEÑO DEL DÍA:</strong><br/>{st.session_state['mensaje_motivacional_pop']}</div>", unsafe_allow_html=True)
    del st.session_state["mensaje_motivacional_pop"]

# ==========================================
# 🚀 PANTALLAS SEGÚN ROL (ATLETA)
# ==========================================
if st.session_state["rol_actual"] == "atleta":
    alumno_logueado = st.session_state["usuario_actual"]
    
    # 🔔 NOTIFICACIONES DEL ATLETA
    res_notif = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", alumno_logueado).eq("leido", False).execute()
    if res_notif.data:
        for noti in res_notif.data:
            st.warning(f"🔔 **Notificación:** {noti['mensaje']}")
            if st.button("Entendido / Descartar", key=f"desc_{noti['id']}"):
                supabase.table("notificaciones").update({"leido": True}).eq("id", noti["id"]).execute()
                st.rerun()

    st.markdown(f"### 👋 ¡Hola, **{alumno_logueado}**!")
    
    tab_entrenar, tab_progreso, tab_consultas = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Mi Progreso", "💬 Dudas al Profe"])
    
    with tab_entrenar: 
        renderizar_tabla_entrenamiento(alumno_logueado, es_espejo=False)
        
    with tab_progreso:
        st.markdown("### 📈 Tu Evolución Deportiva")
        res_hist = supabase.table("registros_entrenamiento").select("fecha, ejercicio, kilos, reps_reales, rpe_global_sesion, duracion_minutos").eq("alumno", alumno_logueado).execute()
        if not res_hist.data:
            st.info("Aún no registrás entrenamientos en la base de datos para armar tus gráficos.")
        else:
            df_hist_at = pd.DataFrame(res_hist.data)
            df_hist_at["e1rm"] = df_hist_at.apply(lambda r: calcular_e1rm(r["kilos"], r["reps_reales"]), axis=1)
            df_hist_at["fecha_corta"] = df_hist_at["fecha"].apply(lambda f: f.split(" ")[0])
            
            st.markdown("#### 💪 Evolución del 1RM Estimado por Ejercicio")
            lista_ejs_hist = sorted(df_hist_at["ejercicio"].unique())
            ej_grafica = st.selectbox("Elegí el ejercicio para ver tu fuerza histórica:", lista_ejs_hist)
            
            df_ej_filtrado = df_hist_at[df_hist_at["ejercicio"] == ej_grafica].groupby("fecha_corta")["e1rm"].max().reset_index()
            st.line_chart(df_ej_filtrado.set_index("fecha_corta")["e1rm"])
            
            st.markdown("#### ⏱️ Fatiga Interna Semanal (sRPE)")
            df_sesiones_unique = df_hist_at.drop_duplicates(subset=["fecha_corta"]).copy()
            df_sesiones_unique["carga_srpe"] = df_sesiones_unique["rpe_global_sesion"] * df_sesiones_unique["duracion_minutos"]
            st.line_chart(df_sesiones_unique.set_index("fecha_corta")["carga_srpe"])
            
    with tab_consultas:
        st.markdown("### 💬 Canal de Dudas al Profe")
        with st.form("form_mensaje_alumno", clear_on_submit=True):
            nuevo_msg = st.text_area("Escribí tu consulta técnica (recorrido, molestias, fatiga):")
            btn_env_msg = st.form_submit_button("Enviar Consulta 🚀")
            
        if btn_env_msg and nuevo_msg.strip() != "":
            supabase.table("consultas_mensajes").insert({
                "alumno": alumno_logueado, "mensaje": nuevo_msg.strip()
            }).execute()
            st.success("📩 ¡Mensaje enviado al Profe Giuliano!")
            st.rerun()
            
        st.divider()
        st.markdown("#### 📬 Historial de Respuestas")
        res_msgs = supabase.table("consultas_mensajes").select("*").eq("alumno", alumno_logueado).order("id", desc=True).execute()
        for msg in res_msgs.data:
            with st.container():
                st.markdown(f"**Tú ({msg['fecha'].split('T')[0]}):** *{msg['mensaje']}*")
                if msg["respuesta"]:
                    st.markdown(f"<p style='color: #84CC16;'><strong>Profe Giuliano:</strong> {msg['respuesta']}</p>", unsafe_allow_html=True)
                else:
                    st.markdown("⏳ *Esperando respuesta...*")
                st.markdown("---")

# ==========================================
# 🚀 PANTALLAS SEGÚN ROL (COACH/ADMIN)
# ==========================================
elif st.session_state["rol_actual"] == "admin":
    res_notif_ad = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", "giuliano").eq("leido", False).execute()
    if res_notif_ad.data:
        for noti in res_notif_ad.data:
            st.toast(noti["mensaje"], icon="🏃")
            if st.button("Marcar como leído", key=f"desc_ad_{noti['id']}"):
                supabase.table("notificaciones").update({"leido": True}).eq("id", noti["id"]).execute()
                st.rerun()

    tab_dashboard, tab_rutinas, tab_clonar, tab_consultas_profe, tab_fichas, tab_aprobaciones, tab_excel = st.tabs([
        "📊 Historial", "📝 Diseñar Plan", "👥 Clonar Pizarra", "💬 Mensajes Recibidos", "📋 Fichas Clínicas", "👥 Aprobar Atletas", "📚 Biblioteca"
    ])
    
    with tab_dashboard:
        st.markdown("### 🔍 Monitor General y Control de Asistencia")
        
        mes_ano_actual = datetime.now().strftime("%m-%Y")
        st.markdown(f"#### 📅 Control de Asistencia Mensual ({mes_ano_actual})")
        res_asist_m = supabase.table("asistencia").select("alumno").eq("mes_ano", mes_ano_actual).execute()
        if not res_asist_m.data:
            st.info("Ningún atleta registró asistencia todavía este mes.")
        else:
            df_asist_resumen = pd.DataFrame(res_asist_m.data)["alumno"].value_counts().reset_index()
            df_asist_resumen.columns = ["Atleta", "Días Entrenados"]
            st.dataframe(df_asist_resumen, use_container_width=True, hide_index=True)
        st.divider()
        
        fecha_actual_hoy = datetime.now().strftime("%Y-%m-%d")
        res_alertas = supabase.table("registros_entrenamiento").select("alumno, ejercicio, notas").like("fecha", f"{fecha_actual_hoy}%").execute()
        df_alertas_list = [r for r in res_alertas.data if any(p in str(r["notas"]).lower() for p in ["dolor", "molestia", "tiron", "molesto"])]
        if df_alertas_list:
            st.markdown("#### ⚠️ SEMÁFORO DE ALERTAS CLÍNICAS (HOY)")
            for al_row in df_alertas_list:
                st.warning(f"🚨 **{al_row['alumno']}** reportó problemas en **{al_row['ejercicio']}**: *\"{al_row['notas']}\"*")
            st.divider()

        alumno_a_revisar = st.selectbox("👤 Seleccionar Atleta para auditar series:", lista_alumnos_con_neutro, key="sb_hist_admin")
        if alumno_a_revisar == "- Seleccionar Atleta -":
            st.info("💡 Elegí un atleta para revisar el desglose específico de sus cargas.")
        else:
            res_total_al = supabase.table("registros_entrenamiento").select("*").eq("alumno", alumno_a_revisar).order("id", desc=True).execute()
            if not res_total_al.data: st.warning(f"Sin entrenamientos guardados para {alumno_a_revisar}.")
            else:
                df_total_alumno = pd.DataFrame(res_total_al.data)
                for fecha_sesion in df_total_alumno["fecha"].unique():
                    df_sesion_especifica = df_total_alumno[df_total_alumno["fecha"] == fecha_sesion]
                    r_name = df_sesion_especifica.iloc[0]["nombre_rutina"] or "Plan General"
                    rpe_g = df_sesion_especifica.iloc[0]["rpe_global_sesion"] or 7
                    dur_m = df_sesion_especifica.iloc[0]["duracion_minutos"] or 60
                    
                    with st.expander(f"🏋️‍♂️ {r_name} — {fecha_sesion} | 📊 sRPE Carga: {int(rpe_g)*int(dur_m)} (RPE {rpe_g} x {dur_m} min)"):
                        st.dataframe(df_sesion_especifica[["ejercicio", "nro_serie", "kilos", "reps_reales", "notas"]].rename(columns={
                            "ejercicio": "Ejercicio", "nro_serie": "Serie", "kilos": "Kilos", "reps_reales": "Reps Reales", "notas": "Notas Atleta"
                        }), use_container_width=True, hide_index=True)
                        
                        if st.button("🗑️ Eliminar Sesión", key=f"del_{fecha_sesion.replace(' ', '_').replace(':', '_')}"):
                            solo_fecha_dia = fecha_sesion.split(" ")[0]
                            supabase.table("registros_entrenamiento").delete().eq("alumno", alumno_a_revisar).eq("fecha", fecha_sesion).execute()
                            supabase.table("asistencia").delete().eq("alumno", alumno_a_revisar).eq("fecha", solo_fecha_dia).execute()
                            st.rerun()

    with tab_rutinas:
        st.markdown("### 📝 Pizarra de Planificación")
        alumno_rutina = st.selectbox("Planificar para:", lista_alumnos_con_neutro, key="planif_select_admin")
        
        if alumno_rutina == "- Seleccionar Atleta -": 
            st.info("💡 Elegí un atleta de la lista para empezar a construir la sesión.")
            st.session_state["borrador_rutina"] = []
        else:
            res_nom = supabase.table("rutinas_asignadas").select("nombre_rutina").eq("alumno", alumno_rutina).limit(1).execute()
            valor_sugerido_nombre = res_nom.data[0]["nombre_rutina"] if res_nom.data else ""
            nombre_de_la_rutina = st.text_input("🏷️ Bloque / Nombre del Mesociclo:", value=valor_sugerido_nombre)
            
            st.divider()
            col_p1, col_p2 = st.columns(2)
            with col_p1: dia_seleccionado = st.selectbox("1. ¿Qué día de la estructura semanal?:", options=DIAS_PLANIF)
            with col_p2: sub_bloque_seleccionado = st.selectbox("2. ¿En qué bloque de la sesión va?:", options=SUB_BLOQUES)
            
            llave_bloque_combinada = f"{dia_seleccionado}|{sub_bloque_seleccionado}"

            st.markdown("##### 🏋️‍♂️ Configuración del Ejercicio")
            tipo_carga = st.radio("Modo de selección de ejercicio:", ["🔍 Buscar en Biblioteca por Patrón", "✍️ Escribir Ejercicio Manualmente (Libre / Aeróbico)"], horizontal=True)
            
            ejercicio_final = ""
            if tipo_carga == "🔍 Buscar en Biblioteca por Patrón":
                res_pat = supabase.table("biblioteca_ejercicios").select("grupo_muscular").execute()
                patrones_disponibles = sorted(list(set([p["grupo_muscular"] for p in res_pat.data if p["grupo_muscular"]])))
                
                if patrones_disponibles:
                    patron_seleccionado = st.selectbox("Filtrar por patrón de movimiento:", ["- Todos los patrones -"] + patrones_disponibles)
                    if patron_seleccionado == "- Todos los patrones -":
                        res_ejs = supabase.table("biblioteca_ejercicios").select("nombre").order("nombre").execute()
                    else:
                        res_ejs = supabase.table("biblioteca_ejercicios").select("nombre").eq("grupo_muscular", patron_seleccionado).order("nombre").execute()
                else:
                    st.info("💡 Tu biblioteca está vacía.")
                    res_ejs = supabase.table("biblioteca_ejercicios").select("nombre").order("nombre").execute()
                    
                ejercicios_filtrados = [fila["nombre"] for fila in res_ejs.data]
                if ejercicios_filtrados: ejercicio_final = st.selectbox("Seleccionar Ejercicio:", ejercicios_filtrados)
                else: ejercicio_final = st.text_input("No hay ejercicios. Escribilo acá:")
            else:
                ejercicio_final = st.text_input("Escribí el ejercicio o trabajo aeróbico/libre:", placeholder="Ej: Pasadas 400m")

            col_r1, col_r2 = st.columns(2)
            with col_r1: series_obj = st.number_input("Series prescritas:", min_value=1, max_value=20, value=4)
            with col_r2: reps_obj = st.text_input("Repeticiones objetivo:", value="5")
                
            if st.button("➕ Inyectar Ejercicio al Borrador", use_container_width=True):
                if ejercicio_final.strip() == "" or nombre_de_la_rutina.strip() == "": st.error("❌ Completa los campos obligatorios.")
                else:
                    st.session_state["borrador_rutina"].append({
                        "ejercicio": ejercicio_final.strip(), "bloque": llave_bloque_combinada, "series": int(series_obj), "reps": str(reps_obj)
                    })
                    st.toast(f"✅ Añadido: {ejercicio_final}")
            
            if st.session_state["borrador_rutina"]:
                st.markdown("### 📋 Pizarra Borrador (No Guardado Aún)")
                df_borrador = pd.DataFrame(st.session_state["borrador_rutina"])
                st.dataframe(df_borrador.rename(columns={"ejercicio":"Ejercicio","bloque":"Día | Bloque","series":"Series","reps":"Reps"}), use_container_width=True)
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🗑️ Vaciar Borrador Actual", use_container_width=True, type="secondary"):
                        st.session_state["borrador_rutina"] = []
                        st.rerun()
                with col_b2:
                    if st.button("💾 PUBLICAR Y ENVIAR PLANIFICACIÓN AL ATLETA", use_container_width=True, type="primary"):
                        supabase.table("rutinas_asignadas").delete().eq("alumno", alumno_rutina).execute()
                        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                        for item in st.session_state["borrador_rutina"]:
                            supabase.table("rutinas_asignadas").insert({
                                "alumno": alumno_rutina, "nombre_rutina": nombre_de_la_rutina.strip(),
                                "ejercicio": item["ejercicio"], "bloque": item["bloque"],
                                "series_objetivo": item["series"], "reps_objetivo": item["reps"], "fecha_asignacion": fecha_hoy
                            }).execute()
                        
                        supabase.table("notificaciones").insert({
                            "destinatario": alumno_rutina,
                            "mensaje": f"🏋️‍♂️ El Profe Giuliano actualizó tu planificación mensual: {nombre_de_la_rutina.strip()}."
                        }).execute()
                        
                        st.session_state["borrador_rutina"] = []
                        st.success(f"🎉 ¡Planificación publicada con éxito para **{alumno_rutina}**!")
                        st.rerun()
            
            st.divider()
            res_act = supabase.table("rutinas_asignadas").select("id, ejercicio, bloque, series_objetivo, reps_objetivo").eq("alumno", alumno_rutina).execute()
            ejercicios_actuales = res_act.data
            if ejercicios_actuales:
                st.markdown(f"#### 📅 Planificación activa en el celular del Atleta")
                for d_op in DIAS_PLANIF:
                    ejercicios_del_dia = [e for e in ejercicios_actuales if e["bloque"].startswith(d_op)]
                    if ejercicios_del_dia:
                        st.markdown(f"<h5 style='color: #84CC16; margin-top: 10px;'>{d_op}</h5>", unsafe_allow_html=True)
                        for sb_op in SUB_BLOQUES:
                            llave_comp = f"{d_op}|{sb_op}"
                            items_b = [e for e in ejercicios_del_dia if e["bloque"] == llave_comp]
                            if items_b:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**{sb_op}**")
                                for item in items_b: st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└─ {item['ejercicio']} ({item['series_objetivo']}x{item['reps_objetivo']})")
                if st.button("🗑️ Desactivar / Borrar Plan de la base de datos"):
                    supabase.table("rutinas_asignadas").delete().eq("alumno", alumno_rutina).execute()
                    st.rerun()

    with tab_clonar:
        st.markdown("### 👥 Clonación Semanal de Pizarras")
        col_c1, col_c2 = st.columns(2)
        with col_c1: atleta_origen = st.selectbox("Atleta Origen:", lista_alumnos_con_neutro, key="at_origen")
        with col_c2: atleta_destino = st.selectbox("Atleta Destino:", lista_alumnos_con_neutro, key="at_destino")
        if st.button("⚡ CLONAR RUTINA COMPLETA", use_container_width=True, type="primary"):
            if atleta_origen == "- Seleccionar Atleta -" or atleta_destino == "- Seleccionar Atleta -": st.error("Seleccioná ambos.")
            else:
                res_orig = supabase.table("rutinas_asignadas").select("*").eq("alumno", atleta_origen).execute()
                origen_datos = res_orig.data
                if origen_datos:
                    supabase.table("rutinas_asignadas").delete().eq("alumno", atleta_destino).execute()
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    for f_rut in origen_datos:
                        supabase.table("rutinas_asignadas").insert({
                            "alumno": atleta_destino, "nombre_rutina": f_rut["nombre_rutina"],
                            "ejercicio": f_rut["ejercicio"], "bloque": f_rut["bloque"],
                            "series_objetivo": f_rut["series_objetivo"], "reps_objetivo": f_rut["reps_objetivo"], "fecha_asignacion": fecha_hoy
                        }).execute()
                    
                    supabase.table("notificaciones").insert({
                        "destinatario": atleta_destino,
                        "mensaje": f"🏋️‍♂️ El Profe Giuliano actualizó tu planificación mensual clonando una pizarra activa."
                    }).execute()
                    
                    st.success("🎉 ¡Pizarra copiada completa!")
                    st.rerun()

    with tab_consultas_profe:
        st.markdown("### 📬 Mensajes y Consultas de Atletas")
        res_cli_msg = supabase.table("consultas_mensajes").select("*").order("id", desc=True).execute()
        if not res_cli_msg.data:
            st.info("No hay mensajes o consultas de atletas todavía.")
        else:
            for c_msg in res_cli_msg.data:
                with st.container():
                    st.markdown(f"👤 **{c_msg['alumno']}** ({c_msg['fecha'].split('T')[0]}): *\"{c_msg['mensaje']}\"*")
                    if c_msg["respuesta"]:
                        st.markdown(f"✅ Respondido: *{c_msg['respuesta']}*")
                    else:
                        with st.form(f"resp_f_{c_msg['id']}", clear_on_submit=True):
                            txt_resp = st.text_input("Escribí tu respuesta técnica:")
                            btn_resp = st.form_submit_button("Responder Consulta 📤")
                        if btn_resp and txt_resp.strip() != "":
                            supabase.table("consultas_mensajes").update({"respuesta": txt_resp.strip()}).eq("id", c_msg["id"]).execute()
                            st.rerun()
                st.markdown("---")

    with tab_fichas:
        st.markdown("### 📋 Fichas Clínicas")
        res_cli = supabase.table("alumnos").select("*").eq("estado", "aprobado").order("nombre_apellido").execute()
        for al_fila in res_cli.data:
            n_c = al_fila["nombre_apellido"]
            u_a = al_fila["usuario"]
            f_n = al_fila["fecha_nacimiento"]
            p_k = al_fila["peso"]
            a_m = al_fila["altura"]
            d_e = al_fila["deporte"]
            o_f = al_fila["objetivo"]
            
            with st.expander(f"👤 {n_c} | Deporte: {d_e} | Edad: {calcular_edad(f_n)} años"):
                st.text(f"• Usuario: {u_a}  • Peso: {p_k} kg  • Altura: {a_m} m\n• Foco: {o_f}")
                if st.checkbox("✍️ Editar Ficha", key=f"chk_{n_c.replace(' ','_')}"):
                    with st.form(f"f_inline_{n_c.replace(' ','_')}"):
                        nuevo_user = st.text_input("Usuario:", value=u_a)
                        nuevo_dep = st.text_input("Deporte:", value=d_e)
                        nuevo_peso = st.number_input("Peso:", value=float(p_k))
                        nuevo_alt = st.number_input("Altura:", value=float(a_m))
                        nuevo_obj = st.text_area("Objetivo:", value=o_f)
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table("alumnos").update({
                                "usuario": nuevo_user, "peso": nuevo_peso, "altura": nuevo_alt,
                                "deporte": nuevo_dep, "objetivo": nuevo_obj
                            }).eq("nombre_apellido", n_c).execute()
                            st.rerun()

    with tab_aprobaciones:
        st.markdown("### 👥 Solicitudes de Autoregistro Pendientes")
        res_pend = supabase.table("alumnos").select("id, nombre_apellido, usuario, deporte, objetivo").eq("estado", "pendiente").order("id").execute()
        pendientes = res_pend.data
        if not pendientes: st.info("No hay solicitudes pendientes.")
        else:
            for p_atleta in pendientes:
                p_id = p_atleta["id"]
                p_nom = p_atleta["nombre_apellido"]
                p_user = p_atleta["usuario"]
                with st.container():
                    st.markdown(f"**👤 Atleta:** `{p_nom}` | **Usuario:** `{p_user}`")
                    col_ap1, col_ap2, _ = st.columns([1, 1, 3])
                    with col_ap1:
                        if st.button("✅ APROBAR", key=f"ap_{p_id}"):
                            supabase.table("alumnos").update({"estado": "aprobado"}).eq("id", p_id).execute()
                            st.rerun()
                    with col_ap2:
                        if st.button("❌ RECHAZAR", key=f"re_{p_id}", type="primary"):
                            supabase.table("alumnos").delete().eq("id", p_id).execute()
                            st.rerun()

    with tab_excel:
        st.markdown("### 📚 Importar Biblioteca de Ejercicios (.xlsx / .csv)")
        
        st.warning("⚠️ Si querés reiniciar de cero tu biblioteca actual en la nube de Supabase antes de cargar el archivo, tocá el botón rojo de abajo:")
        if st.button("🗑️ VACIAR BIBLIOTECA EN SUPABASE", use_container_width=True, type="secondary"):
            supabase.table("biblioteca_ejercicios").delete().neq("id", 0).execute()
            st.success("✨ ¡Biblioteca vaciada con éxito!")
            st.rerun()
            
        st.divider()
        archivo_subido = st.file_uploader("Arrastrá tu archivo excel o csv con los ejercicios:", type=["xlsx", "csv"])
        
        if archivo_subido is not None:
            try:
                df_ejercicios = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido)
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                columnas_actuales = df_ejercicios.columns.tolist()
                
                col_nombre = next((c for c in columnas_actuales if c.lower() in ["nombre", "ejercicio", "name"]), None)
                col_grupo = next((c for c in columnas_actuales if c.lower() in ["grupo", "grupo muscular", "grupo_muscular", "musculo", "target", "patron"]), None)
                col_video = next((c for c in columnas_actuales if c.lower() in ["video", "link", "url", "link_video"]), None)
                
                if not col_nombre: st.error("❌ El archivo debe tener una columna llamada 'nombre' o 'ejercicio'.")
                else:
                    st.success(f"📋 Archivo detectado. Filas: {len(df_ejercicios)}")
                    st.dataframe(df_ejercicios.head(10), use_container_width=True)
                    
                    if st.button("📥 CONFIRMAR E INYECTAR A LA BIBLIOTECA", use_container_width=True, type="primary"):
                        contador_insertados = 0
                        for _, fila in df_ejercicios.iterrows():
                            n_val = str(fila[col_nombre]).strip()
                            if n_val == "" or n_val.lower() == "nan": continue
                            g_val = str(fila[col_grupo]).strip() if (col_grupo and str(fila[col_grupo]).strip().lower() != "nan") else "General"
                            v_val = str(fila[col_video]).strip() if (col_video and str(fila[col_video]).strip().lower() != "nan") else ""
                            
                            res_dup = supabase.table("biblioteca_ejercicios").select("id").eq("nombre", n_val).execute()
                            if not res_dup.data:
                                supabase.table("biblioteca_ejercicios").insert({
                                    "nombre": n_val, "grupo_muscular": g_val, "link_video": v_val
                                }).execute()
                                contador_insertados += 1
                        st.success(f"🎉 ¡Procesados {contador_insertados} ejercicios correctamente!")
                        st.rerun()
            except Exception as e: st.error(f"❌ Error al procesar archivo: {e}")
