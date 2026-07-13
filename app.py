import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
import random
from datetime import datetime, date

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
# 🛠️ HELPERS: CÁLCULO DE EDAD Y MOTIVACIÓN
# ==========================================
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
    frases_inicio = [
        "¡Excelente primer paso! El camino a la alta competencia empieza hoy. 🚀",
        "¡Buen comienzo! La constancia es el secreto del rendimiento. 💪"
    ]
    frases_racha_baja = [
        f"¡Suma y sigue! Ya van {dias_acumulados} entrenamientos este mes. ¡Buen ritmo! ⚡",
        f"¡Cuerpo e intención enfocados! Llevás {dias_acumulados} sesiones. No aflojes. 🔥"
    ]
    frases_racha_media = [
        f"¡Tremenda disciplina! {dias_acumulados} días adentro. Te estás volviendo imparable. 👑",
        f"El esfuerzo de hoy es el rendimiento del mañana. ¡{dias_acumulados} sesiones acumuladas! 🏆"
    ]
    frases_elite = [
        f"¡Nivel Élite! 🔥 {dias_acumulados} entrenamientos en el mes. Sos un ejemplo de consistencia. 🦅",
        f"¡Impresionante! {dias_acumulados} días dándolo todo. La preparación vence al talento. 🥇"
    ]
    
    if dias_acumulados <= 1:
        return random.choice(frases_inicio)
    elif dias_acumulados <= 5:
        return random.choice(frases_racha_baja)
    elif dias_acumulados <= 12:
        return random.choice(frases_racha_media)
    else:
        return random.choice(frases_elite)

# ==========================================
# 0. CONSTANTES GLOBALES Y SESIÓN BORRADOR
# ==========================================
DIAS_PLANIF = ["📅 Día 1", "📅 Día 2", "🏃 Día Aeróbico"]
SUB_BLOQUES = ["🔥 Entrada en Calor", "⚡ Bloque Principal", "🧘 Bloque Final / Vuelta a la Calma"]

if "borrador_rutina" not in st.session_state:
    st.session_state["borrador_rutina"] = []

try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS_HASH = st.secrets["admin_pass_hash"].encode()
    MODO_LOCAL = False
except Exception:
    ADMIN_USER = "giuliano"
    ADMIN_PASS_PLANA = "magpower2026"
    MODO_LOCAL = True

# ==========================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS
# ==========================================
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("gimnasio.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS alumnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_apellido TEXT UNIQUE,
        usuario TEXT UNIQUE,
        contrasena TEXT,
        fecha_nacimiento TEXT,
        peso REAL,
        altura REAL,
        deporte TEXT,
        objetivo TEXT,
        estado TEXT DEFAULT 'pendiente'
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS biblioteca_ejercicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT UNIQUE, 
        grupo_muscular TEXT, 
        link_video TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS rutinas_asignadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        alumno TEXT, 
        nombre_rutina TEXT,
        ejercicio TEXT, 
        bloque TEXT, 
        series_objetivo INTEGER, 
        reps_objetivo TEXT, 
        fecha_asignacion TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS registros_entrenamiento (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        fecha TEXT, 
        alumno TEXT, 
        nombre_rutina TEXT,
        ejercicio TEXT, 
        nro_serie INTEGER,
        kilos REAL, 
        reps_reales INTEGER,
        rpe_serie REAL, 
        notas TEXT,
        rpe_global_sesion REAL,
        duracion_minutos INTEGER
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        mes_ano TEXT,
        alumno TEXT
    )
""")
conn.commit()

# ==========================================
# 2. CONFIGURACIÓN VISUAL GENERAL (UI)
# ==========================================
st.set_page_config(page_title="TrainApp - Prof. Giuliano Cocconi", page_icon="⚡", layout="wide")

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
                es_admin = False
                if input_user == ADMIN_USER:
                    if MODO_LOCAL and input_pass == ADMIN_PASS_PLANA: es_admin = True
                    elif not MODO_LOCAL and bcrypt.checkpw(input_pass.encode(), ADMIN_PASS_HASH): es_admin = True

                if es_admin:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = "Prof. Giuliano"
                    st.session_state["rol_actual"] = "admin"
                    st.rerun()
                else:
                    cursor.execute("SELECT nombre_apellido, contrasena, estado FROM alumnos WHERE usuario = ?", (input_user,))
                    user_db = cursor.fetchone()
                    if user_db and verificar_password(input_pass, user_db[1]):
                        if user_db[2] == "pendiente":
                            st.warning("⏳ Tu cuenta está pendiente de aprobación por el Prof. Giuliano.")
                        else:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = user_db[0]
                            st.session_state["rol_actual"] = "atleta"
                            st.rerun()
                    else: st.error("❌ Usuario o contraseña incorrectos.")
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
                        cursor.execute("""
                            INSERT INTO alumnos (nombre_apellido, usuario, contrasena, fecha_nacimiento, peso, altura, deporte, objetivo, estado) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente')
                        """, (reg_nombre.strip(), reg_user, hashear_password(reg_pass), reg_nacimiento.strftime("%Y-%m-%d"), reg_peso, reg_altura, reg_deporte, reg_obj))
                        conn.commit()
                        st.success(f"🎉 ¡Registro enviado, {reg_nombre}! Quedó pendiente de aprobación.")
                    except sqlite3.IntegrityError: st.error("❌ El usuario o nombre ya se encuentran registrados.")
    st.stop()

st.sidebar.markdown(f"👤 Coach: **{st.session_state['usuario_actual']}**")

if st.session_state["rol_actual"] == "atleta":
    mes_actual_str = datetime.now().strftime("%m-%Y")
    cursor.execute("SELECT COUNT(*) FROM asistencia WHERE alumno = ? AND mes_ano = ?", (st.session_state["usuario_actual"], mes_actual_str))
    racha_act = cursor.fetchone()[0]
    st.sidebar.markdown(f"📆 Asistencias este mes: **{racha_act}**")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["borrador_rutina"] = []
    st.rerun()

cursor.execute("SELECT nombre_apellido FROM alumnos WHERE estado = 'aprobado' ORDER BY nombre_apellido ASC")
lista_alumnos = [fila[0] for fila in cursor.fetchall()]
lista_alumnos_con_neutro = ["- Seleccionar Atleta -"] + lista_alumnos

# ==========================================
# 📱 INTERFAZ ATLETA CON ASISTENCIA Y MOTIVACIÓN
# ==========================================
def renderizar_tabla_entrenamiento(nombre_atleta, es_espejo=False):
    sufijo = "esp" if es_espejo else "atl"
    
    cursor.execute("""
        SELECT r.ejercicio, r.bloque, r.series_objetivo, r.reps_objetivo, b.link_video, r.nombre_rutina 
        FROM rutinas_asignadas r
        LEFT JOIN biblioteca_ejercicios b ON r.ejercicio = b.nombre
        WHERE r.alumno = ?
    """, (nombre_atleta,))
    rutina_completa = cursor.fetchall()
    
    if not rutina_completa:
        st.info("No tenés ninguna rutina asignada para este mes todavía.")
        return
        
    nombre_de_la_rutina = rutina_completa[0][5] or "Planificación Mensual"
    if es_espejo: st.warning(f"👀 MODO ESPEJO. Planificación: **{nombre_de_la_rutina}**")
    else: st.markdown(f"### 📋 Plan Mensual: <span style='color: #CCFF00;'>{nombre_de_la_rutina}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    dia_a_entrenar = st.selectbox("📆 ¿Qué día te toca entrenar hoy?", options=DIAS_PLANIF, key=f"sb_dia_atleta_{sufijo}")
    st.markdown("---")

    entradas_alumno = {}
    ejercicios_visibles_en_pantalla = False
    
    for sub_b in SUB_BLOQUES:
        llave_busqueda = f"{dia_a_entrenar}|{sub_b}"
        ejercicios_del_bloque = [r for r in rutina_completa if r[1] == llave_busqueda]
        
        if ejercicios_del_bloque:
            ejercicios_visibles_en_pantalla = True
            st.markdown(f"<h4 style='color: #CCFF00; margin-top: 20px; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{sub_b}</h4>", unsafe_allow_html=True)
            
            for idx, ej in enumerate(ejercicios_del_bloque):
                nombre_ejercicio = ej[0]
                series_prescritas = int(ej[2])
                reps_prescritas = ej[3]
                link_video = ej[4]
                
                with st.container():
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1: st.markdown(f"💪 **{nombre_ejercicio}** | `{series_prescritas}S x {reps_prescritas}R`")
                    with col_t2: 
                        if link_video and "http" in link_video: st.markdown(f"[🎥 Video]({link_video})")
                    
                    for s in range(1, series_prescritas + 1):
                        key_id = f"{sufijo}_{nombre_atleta}_{idx}_{nombre_ejercicio.replace(' ', '_')}_s{s}"
                        col_s1, col_s2, col_s3 = st.columns([1, 2, 2])
                        with col_s1: st.markdown(f"<p style='margin-top: 30px; font-weight: bold; color: #94A3B8;'>S{s}</p>", unsafe_allow_html=True)
                        with col_s2:
                            try: default_reps = int(reps_prescritas)
                            except: default_reps = 5
                            reps_reales = st.number_input("Reps:", min_value=0, max_value=100, value=default_reps, key=f"rep_{key_id}")
                        with col_s3: kilos_input = st.number_input("Kilos:", min_value=0.0, step=0.5, value=0.0, key=f"k_{key_id}")
                        
                        entradas_alumno[(nombre_ejercicio, s)] = {
                            "ejercicio": nombre_ejercicio, "serie": s, "kilos": kilos_input, "reps_reales": reps_reales
                        }
                    
                    notas_ejercicio = st.text_input("Comentarios:", placeholder="Ej: Liviano, molestia...", key=f"not_{sufijo}_{nombre_atleta}_{idx}_{dia_a_entrenar.replace(' ', '_')}")
                    for s in range(1, series_prescritas + 1): entradas_alumno[(nombre_ejercicio, s)]["notas"] = notas_ejercicio
                    st.markdown("<hr style='margin: 12px 0px; opacity: 0.15;'/>", unsafe_allow_html=True)
                    
    if not ejercicios_visibles_en_pantalla:
        st.info(f"No tenés ejercicios cargados en el sistema para el día: **{dia_a_entrenar}**.")
        return
        
    st.markdown("<h4 style='color: #84CC16; margin-top: 30px;'>📊 Evaluación General de la Sesión</h4>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1: rpe_global = st.select_slider("¿Qué tan dura estuvo la sesión hoy? (RPE Global):", options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], value=7)
    with col_g2: duracion_min = st.number_input("⏱️ ¿Cuántos minutos duró el entrenamiento?", min_value=1, max_value=300, value=60, step=5)

    if st.button("🏁 FINALIZAR ENTRENAMIENTO Y ENVIAR AL PROFE", use_container_width=True, type="primary", key=f"btn_finalizar_{sufijo}"):
        if es_espejo: st.info("ℹ️ Modo espejo de visualización.")
        else:
            fecha_hoy_texto = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM registros_entrenamiento WHERE alumno = ? AND fecha LIKE ?", (nombre_atleta, f"{fecha_hoy_texto}%"))
            if cursor.fetchone()[0] > 0: st.error(f"⚠️ Ya registraste una sesión hoy.")
            else:
                datos_validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                if not datos_validos: st.warning("⚠️ Completá marcas antes de guardar.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    mes_ano_actual = datetime.now().strftime("%m-%Y")
                    nombre_reporte_dia = f"{nombre_de_la_rutina} ({dia_a_entrenar})"
                    
                    for datos in datos_validos:
                        cursor.execute("""
                            INSERT INTO registros_entrenamiento 
                            (fecha, alumno, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, rpe_serie, notas, rpe_global_sesion, duracion_minutos) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?)
                        """, (fecha_actual, nombre_atleta, nombre_reporte_dia, datos["ejercicio"], datos["serie"], datos["kilos"], datos["reps_reales"], datos["notas"], rpe_global, duracion_min))
                    
                    cursor.execute("INSERT INTO asistencia (fecha, mes_ano, alumno) VALUES (?, ?, ?)", (fecha_hoy_texto, mes_ano_actual, nombre_atleta))
                    conn.commit()
                    
                    cursor.execute("SELECT COUNT(*) FROM asistencia WHERE alumno = ? AND mes_ano = ?", (nombre_atleta, mes_ano_actual))
                    total_dias = cursor.fetchone()[0]
                    
                    st.session_state["mensaje_motivacional_pop"] = obtener_frase_motivacional(total_dias)
                    st.success("🚀 ¡Entrenamiento enviado correctamente al Profe Giuliano!")
                    st.rerun()

if "mensaje_motivacional_pop" in st.session_state:
    st.balloons()
    st.toast(st.session_state["mensaje_motivacional_pop"], icon="🏆")
    st.markdown(f"<div style='background-color: #1E293B; border-left: 5px solid #84CC16; padding: 15px; border-radius: 4px; margin-bottom: 20px;'><strong>🏅 TU MENSAJE DE HOY:</strong><br/>{st.session_state['mensaje_motivacional_pop']}</div>", unsafe_allow_html=True)
    del st.session_state["mensaje_motivacional_pop"]

# ==========================================
# 🚀 MONITOR ADMINISTRADOR (PROFE GIULIANO)
# ==========================================
if st.session_state["rol_actual"] == "atleta":
    alumno_logueado = st.session_state["usuario_actual"]
    st.markdown(f"### 👋 ¡Hola, **{alumno_logueado}**!")
    tab_entrenar, tab_progreso = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Mi Historial"])
    with tab_entrenar: renderizar_tabla_entrenamiento(alumno_logueado, es_espejo=False)
    with tab_progreso:
        df_hist_atleta = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_logueado,))
        if df_hist_atleta.empty: st.info("Aún no registrás entrenamientos.")
        else: st.dataframe(df_hist_atleta.rename(columns={"nombre_rutina": "Plan / Día", "fecha":"Fecha", "ejercicio":"Ejercicio", "nro_serie":"Serie", "kilos":"Kilos", "reps_reales":"Reps", "notas":"Notas"}), use_container_width=True, hide_index=True)

elif st.session_state["rol_actual"] == "admin":
    tab_dashboard, tab_rutinas, tab_clonar, tab_fichas, tab_aprobaciones, tab_excel = st.tabs([
        "📊 Historial", "📝 Diseñar Plan", "👥 Clonar Pizarra", "📋 Fichas Clínicas", "👥 Aprobar Atletas", "📚 Biblioteca"
    ])
    
    with tab_dashboard:
        st.markdown("### 🔍 Monitor General y Control de Asistencia")
        
        mes_ano_actual = datetime.now().strftime("%m-%Y")
        st.markdown(f"#### 📅 Control de Asistencia Mensual ({mes_ano_actual})")
        df_asist_resumen = pd.read_sql_query("""
            SELECT alumno as 'Atleta', COUNT(*) as 'Días Entrenados' 
            FROM asistencia 
            WHERE mes_ano = ? 
            GROUP BY alumno 
            ORDER BY COUNT(*) DESC
        """, conn, params=(mes_ano_actual,))
        
        if df_asist_resumen.empty:
            st.info("Ningún atleta registró asistencia todavía este mes.")
        else:
            st.dataframe(df_asist_resumen, use_container_width=True, hide_index=True)
        st.divider()
        
        fecha_actual_hoy = datetime.now().strftime("%Y-%m-%d")
        df_alertas = pd.read_sql_query("SELECT alumno, ejercicio, notas FROM registros_entrenamiento WHERE fecha LIKE ? AND (notas LIKE '%dolor%' OR notas LIKE '%molestia%' OR notas LIKE '%tiron%' OR notas LIKE '%molesto%')", conn, params=(f"{fecha_actual_hoy}%",))
        if not df_alertas.empty:
            st.markdown("#### ⚠️ SEMÁFORO DE ALERTAS CLÍNICAS (HOY)")
            for _, al_row in df_alertas.iterrows():
                st.warning(f"🚨 **{al_row['alumno']}** reportó problemas en **{al_row['ejercicio']}**: *\"{al_row['notas']}\"*")
            st.divider()

        alumno_a_revisar = st.selectbox("👤 Seleccionar Atleta para auditar series:", lista_alumnos_con_neutro, key="sb_hist_admin")
        if alumno_a_revisar == "- Seleccionar Atleta -":
            st.info("💡 Elegí un atleta para revisar el desglose específico de sus cargas.")
        else:
            df_total_alumno = pd.read_sql_query("SELECT id, fecha, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, notas, rpe_global_sesion, duracion_minutos FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_a_revisar,))
            if df_total_alumno.empty: st.warning(f"Sin entrenamientos guardados para {alumno_a_revisar}.")
            else:
                for fecha_sesion in df_total_alumno["fecha"].unique():
                    df_sesion_especifica = df_total_alumno[df_total_alumno["fecha"] == fecha_sesion]
                    r_name = df_sesion_especifica.iloc[0]["nombre_rutina"] or "Plan General"
                    rpe_g = df_sesion_especifica.iloc[0]["rpe_global_sesion"] or 7
                    dur_m = df_sesion_especifica.iloc[0]["duracion_minutos"] or 60
                    
                    with st.expander(f"🏋️‍♂️ {r_name} — {fecha_sesion} | 📊 sRPE Carga: {int(rpe_g)*int(dur_m)} (RPE {rpe_g} x {dur_m} min)"):
                        st.dataframe(df_sesion_especifica[["ejercicio", "nro_serie", "kilos", "reps_reales", "notas"]].rename(columns={"ejercicio": "Ejercicio", "nro_serie": "Serie", "kilos": "Kilos", "reps_reales": "Reps Reales", "notas": "Notas Atleta"}), use_container_width=True, hide_index=True)
                        if st.button("🗑️ Eliminar Sesión", key=f"del_{fecha_sesion.replace(' ', '_').replace(':', '_')}"):
                            solo_fecha_dia = fecha_sesion.split(" ")[0]
                            cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno = ? AND fecha = ?", (alumno_a_revisar, fecha_sesion))
                            cursor.execute("DELETE FROM asistencia WHERE alumno = ? AND fecha = ?", (alumno_a_revisar, solo_fecha_dia))
                            conn.commit()
                            st.rerun()

    # PESTAÑA DISEÑAR PLAN CON BORRADOR Y ENTRADA MANUAL CORREGIDA
    with tab_rutinas:
        st.markdown("### 📝 Pizarra de Planificación")
        alumno_rutina = st.selectbox("Planificar para:", lista_alumnos_con_neutro, key="planif_select_admin")
        
        if alumno_rutina == "- Seleccionar Atleta -": 
            st.info("💡 Elegí un atleta de la lista para empezar a construir la sesión.")
            st.session_state["borrador_rutina"] = []
        else:
            cursor.execute("SELECT nombre_rutina FROM rutinas_asignadas WHERE alumno = ? LIMIT 1", (alumno_rutina,))
            rutina_existente = cursor.fetchone()
            valor_sugerido_nombre = rutina_existente[0] if (rutina_existente and rutina_existente[0]) else ""
            nombre_de_la_rutina = st.text_input("🏷️ Bloque / Nombre del Mesociclo (Ej: Planificación Julio - Fuerza):", value=valor_sugerido_nombre)
            
            st.divider()
            
            col_p1, col_p2 = st.columns(2)
            with col_p1: dia_seleccionado = st.selectbox("1. ¿Qué día de la estructura semanal?:", options=DIAS_PLANIF)
            with col_p2: sub_bloque_seleccionado = st.selectbox("2. ¿En qué bloque de la sesión va?:", options=SUB_BLOQUES)
            
            llave_bloque_combinada = f"{dia_seleccionado}|{sub_bloque_seleccionado}"

            st.markdown("##### 🏋️‍♂️ Configuración del Ejercicio")
            tipo_carga = st.radio("Modo de selección de ejercicio:", ["🔍 Buscar en Biblioteca por Patrón", "✍️ Escribir Ejercicio Manualmente (Libre / Aeróbico)"], horizontal=True)
            
            ejercicio_final = ""
            if tipo_carga == "🔍 Buscar en Biblioteca por Patrón":
                cursor.execute("SELECT DISTINCT grupo_muscular FROM biblioteca_ejercicios WHERE grupo_muscular IS NOT NULL AND grupo_muscular != '' ORDER BY grupo_muscular ASC")
                patrones_disponibles = [p[0] for p in cursor.fetchall()]
                
                if patrones_disponibles:
                    patron_seleccionado = st.selectbox("Filtrar por patrón de movimiento:", ["- Todos los patrones -"] + patrones_disponibles)
                    if patron_seleccionado == "- Todos los patrones -":
                        cursor.execute("SELECT nombre FROM biblioteca_ejercicios ORDER BY nombre ASC")
                    else:
                        cursor.execute("SELECT nombre FROM biblioteca_ejercicios WHERE grupo_muscular = ? ORDER BY nombre ASC", (patron_seleccionado,))
                else:
                    st.info("💡 Tu biblioteca está vacía. Podés usar el ingreso manual o cargar el Excel en la pestaña 'Biblioteca'.")
                    cursor.execute("SELECT nombre FROM biblioteca_ejercicios ORDER BY nombre ASC")
                    
                ejercicios_filtrados = [fila[0] for fila in cursor.fetchall()]
                if ejercicios_filtrados:
                    ejercicio_final = st.selectbox("Seleccionar Ejercicio:", ejercicios_filtrados)
                else:
                    ejercicio_final = st.text_input("No hay ejercicios en este patrón. Escribilo acá:")
            else:
                ejercicio_final = st.text_input("Escribí el ejercicio o trabajo aeróbico/libre:", placeholder="Ej: Pasadas 400m / Intervalado intermitente / Sentadilla Libre")

            col_r1, col_r2 = st.columns(2)
            with col_r1: series_obj = st.number_input("Series prescritas:", min_value=1, max_value=20, value=4)
            with col_r2: reps_obj = st.text_input("Repeticiones objetivo:", value="5")
                
            if st.button("➕ Inyectar Ejercicio al Borrador", use_container_width=True):
                if ejercicio_final.strip() == "" or nombre_de_la_rutina.strip() == "": 
                    st.error("❌ Por favor completa el nombre de la rutina y el ejercicio.")
                else:
                    st.session_state["borrador_rutina"].append({
                        "ejercicio": ejercicio_final.strip(),
                        "bloque": llave_bloque_combinada,
                        "series": int(series_obj),
                        "reps": str(reps_obj)
                    })
                    st.toast(f"✅ Añadido al borrador: {ejercicio_final}")
            
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
                        cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
                        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                        for item in st.session_state["borrador_rutina"]:
                            cursor.execute("""
                                INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (alumno_rutina, nombre_de_la_rutina.strip(), item["ejercicio"], item["bloque"], item["series"], item["reps"], fecha_hoy))
                        
                        conn.commit()
                        st.session_state["borrador_rutina"] = []
                        st.success(f"🎉 ¡Planificación publicada con éxito! El atleta **{alumno_rutina}** ya puede visualizarla.")
                        st.rerun()
            
            st.divider()
            
            cursor.execute("SELECT id, ejercicio, bloque, series_objetivo, reps_objetivo FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
            ejercicios_actuales = cursor.fetchall()
            if ejercicios_actuales:
                st.markdown(f"#### 📅 Planificación activa en el celular del Atleta")
                for d_op in DIAS_PLANIF:
                    ejercicios_del_dia = [e for e in ejercicios_actuales if e[2].startswith(d_op)]
                    if ejercicios_del_dia:
                        st.markdown(f"<h5 style='color: #84CC16; margin-top: 10px;'>{d_op}</h5>", unsafe_allow_html=True)
                        for sb_op in SUB_BLOQUES:
                            llave_comp = f"{d_op}|{sb_op}"
                            items_b = [e for e in ejercicios_del_dia if e[2] == llave_comp]
                            if items_b:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**{sb_op}**")
                                for item in items_b: st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└─ {item[1]} ({item[3]}x{item[4]})")
                if st.button("🗑️ Desactivar / Borrar Plan de la base de datos"):
                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
                    conn.commit()
                    st.rerun()

    # PESTAÑA CLONAR
    with tab_clonar:
        st.markdown("### 👥 Clonación Semanal de Pizarras")
        col_c1, col_c2 = st.columns(2)
        with col_c1: atleta_origen = st.selectbox("Atleta Origen:", lista_alumnos_con_neutro, key="at_origen")
        with col_c2: atleta_destino = st.selectbox("Atleta Destino:", lista_alumnos_con_neutro, key="at_destino")
        if st.button("⚡ CLONAR RUTINA COMPLETA", use_container_width=True, type="primary"):
            if atleta_origen == "- Seleccionar Atleta -" or atleta_destino == "- Seleccionar Atleta -": st.error("Seleccioná ambos.")
            else:
                cursor.execute("SELECT nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo FROM rutinas_asignadas WHERE alumno = ?", (atleta_origen,))
                origen_datos = cursor.fetchall()
                if origen_datos:
                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (atleta_destino,))
                    for f_rut in origen_datos:
                        cursor.execute("INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) VALUES (?, ?, ?, ?, ?, ?, ?)", (atleta_destino, f_rut[0], f_rut[1], f_rut[2], f_rut[3], f_rut[4], datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("🎉 ¡Pizarra copiada completa!")
                    st.rerun()

    # PESTAÑA FICHAS CLÍNICAS
    with tab_fichas:
        st.markdown("### 📋 Fichas Clínicas")
        cursor.execute("SELECT nombre_apellido, usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos WHERE estado = 'aprobado' ORDER BY nombre_apellido ASC")
        for al_fila in cursor.fetchall():
            n_c, u_a, f_n, p_k, a_m, d_e, o_f = al_fila
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
                            cursor.execute("UPDATE alumnos SET usuario=?, peso=?, altura=?, deporte=?, objetivo=? WHERE nombre_apellido=?", (nuevo_user, nuevo_peso, nuevo_alt, nuevo_dep, nuevo_obj, n_c))
                            conn.commit()
                            st.rerun()

    # PESTAÑA SOLICITUDES
    with tab_aprobaciones:
        st.markdown("### 👥 Solicitudes de Autoregistro Pendientes")
        cursor.execute("SELECT id, nombre_apellido, usuario, deporte, objetivo FROM alumnos WHERE estado = 'pendiente' ORDER BY id ASC")
        pendientes = cursor.fetchall()
        if not pendientes: st.info("No hay solicitudes pendientes.")
        else:
            for p_atleta in pendientes:
                p_id, p_nom, p_user, p_dep, p_obj = p_atleta
                with st.container():
                    st.markdown(f"**👤 Atleta:** `{p_nom}` | **Usuario:** `{p_user}`")
                    col_ap1, col_ap2, _ = st.columns([1, 1, 3])
                    with col_ap1:
                        if st.button("✅ APROBAR", key=f"ap_{p_id}"):
                            cursor.execute("UPDATE alumnos SET estado = 'aprobado' WHERE id = ?", (p_id,))
                            conn.commit()
                            st.rerun()
                    with col_ap2:
                        if st.button("❌ RECHAZAR", key=f"re_{p_id}", type="primary"):
                            cursor.execute("DELETE FROM alumnos WHERE id = ?", (p_id,))
                            conn.commit()
                            st.rerun()

    # PESTAÑA EXCEL (CORREGIDA CON grupo_muscular)
    with tab_excel:
        st.markdown("### 📚 Importar Biblioteca de Ejercicios (.xlsx / .csv)")
        archivo_subido = st.file_uploader("Arrastrá tu archivo excel o csv con los ejercicios:", type=["xlsx", "csv"])
        
        if archivo_subido is not None:
            try:
                df_ejercicios = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido)
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                columnas_actuales = df_ejercicios.columns.tolist()
                
                col_nombre = next((c for c in columnas_actuales if c.lower() in ["nombre", "ejercicio", "name"]), None)
                col_grupo = next((c for c in columnas_actuales if c.lower() in ["grupo", "grupo muscular", "grupo_muscular", "musculo", "target", "patron"]), None)
                col_video = next((c for c in columnas_actuales if c.lower() in ["video", "link", "url", "link_video"]), None)
                
                if not col_nombre:
                    st.error("❌ El archivo debe tener al menos una columna llamada 'nombre' o 'ejercicio'.")
                else:
                    st.success(f"📋 Archivo detectado con éxito. Se encontraron {len(df_ejercicios)} filas.")
                    st.dataframe(df_ejercicios.head(10), use_container_width=True)
                    
                    if st.button("📥 CONFIRMAR E INYECTAR A LA BIBLIOTECA", use_container_width=True, type="primary"):
                        contador_insertados = 0
                        for _, fila in df_ejercicios.iterrows():
                            n_val = str(fila[col_nombre]).strip()
                            if n_val == "" or n_val.lower() == "nan": 
                                continue
                            g_val = str(fila[col_grupo]).strip() if (col_grupo and str(fila[col_grupo]).strip().lower() != "nan") else "General"
                            v_val = str(fila[col_video]).strip() if (col_video and str(fila[col_video]).strip().lower() != "nan") else ""
                            
                            cursor.execute("""
                                INSERT OR IGNORE INTO biblioteca_ejercicios (nombre, grupo_muscular, link_video) 
                                VALUES (?, ?, ?)
                            """, (n_val, g_val, v_val))
                            contador_insertados += 1
                            
                        conn.commit()
                        st.success(f"🎉 ¡Biblioteca actualizada! Se procesaron {contador_insertados} ejercicios correctamente.")
                        st.rerun()
                        
            except Exception as e: 
                st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
