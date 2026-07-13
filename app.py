import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
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
# 🛠️ HELPER: CÁLCULO DINÁMICO DE EDAD
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

# ==========================================
# 0. CONSTANTES GLOBALES
# ==========================================
BLOQUES = [
    "🔥 Entrada en Calor", 
    "⚡ Bloque Principal", 
    "🧘 Bloque Final / Vuelta a la Calma",
    "📅 Día 1",
    "📅 Día 2",
    "🏃 Día Aeróbico"
]

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

# Tabla de alumnos con columna 'estado' para aprobación
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
conn.commit()

# ==========================================
# 2. CONFIGURACIÓN VISUAL GENERAL (UI)
# ==========================================
st.set_page_config(page_title="TrainApp - @pf.giuliano", page_icon="⚡", layout="wide")

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>⚡ TRAINAPP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #84CC16; font-weight: bold; letter-spacing: 1px; margin-top: 0px;'>HIGH PERFORMANCE MANAGEMENT</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# 🔑 AUTENTICACIÓN Y AUTOREGISTRO CON FILTRO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""

if not st.session_state["autenticado"]:
    login_mode = st.radio("Seleccioná una opción:", ["🔑 Iniciar Sesión", "👥 ¿Sos nuevo? Registrate acá 👤"], horizontal=True, label_visibility="collapsed")
    
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
                            st.warning("⏳ Tu cuenta fue registrada pero aún está pendiente de aprobación por el Prof. Giuliano. Te avisamos apenas se habilite.")
                        else:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = user_db[0]
                            st.session_state["rol_actual"] = "atleta"
                            st.rerun()
                    else: st.error("❌ Usuario o contraseña incorrectos.")
    else:
        st.markdown("<h3 style='text-align: center;'>📝 Registro Atleta - Mag Power</h3>", unsafe_allow_html=True)
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
                        st.success(f"🎉 ¡Registro enviado, {reg_nombre}! Quedó pendiente de aprobación por el Profe.")
                    except sqlite3.IntegrityError:
                        st.error("❌ El usuario o nombre ya se encuentran registrados.")
    st.stop()

st.sidebar.markdown(f"👤 Conectado: **{st.session_state['usuario_actual']}**")
if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# Filtrar solo aprobados para el uso regular
cursor.execute("SELECT nombre_apellido FROM alumnos WHERE estado = 'aprobado' ORDER BY nombre_apellido ASC")
lista_alumnos = [fila[0] for fila in cursor.fetchall()]
lista_alumnos_con_neutro = ["- Seleccionar Atleta -"] + lista_alumnos

# ==========================================
# 📱 INTERFAZ ATLETA EN TRINCHERA (SIN RPE INDIVIDUAL)
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
        st.info("No hay ejercicios asignados para hoy.")
        return
        
    nombre_de_la_rutina = rutina_completa[0][5] or "Rutina General"
    if es_espejo: st.warning(f"👀 MODO ESPEJO. Plan: **{nombre_de_la_rutina}**")
    else: st.markdown(f"### 📋 Plan Activo: <span style='color: #CCFF00;'>{nombre_de_la_rutina}</span>", unsafe_allow_html=True)

    entradas_alumno = {}
    
    for key_bloque in BLOQUES:
        ejercicios_del_bloque = [r for r in rutina_completa if r[1] == key_bloque]
        if ejercicios_del_bloque:
            st.markdown(f"<h4 style='color: #CCFF00; margin-top: 20px; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{key_bloque}</h4>", unsafe_allow_html=True)
            
            for idx, ej in enumerate(ejercicios_del_bloque):
                nombre_ejercicio = ej[0]
                series_prescritas = int(ej[2])
                reps_prescritas = ej[3]
                link_video = ej[4]
                
                with st.container():
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.markdown(f"💪 **{nombre_ejercicio}** | `{series_prescritas}S x {reps_prescritas}R`")
                    with col_t2:
                        if link_video and "http" in link_video: st.markdown(f"[🎥 Video]({link_video})")
                    
                    # Carga limpia: Reps y Kilos únicamente (Kilos arrancan en 0.0)
                    for s in range(1, series_prescritas + 1):
                        key_id = f"{sufijo}_{nombre_atleta}_{idx}_{nombre_ejercicio.replace(' ', '_')}_s{s}"
                        col_s1, col_s2, col_s3 = st.columns([1, 2, 2])
                        with col_s1: st.markdown(f"<p style='margin-top: 30px; font-weight: bold; color: #94A3B8;'>S{s}</p>", unsafe_allow_html=True)
                        with col_s2:
                            try: default_reps = int(reps_prescritas)
                            except: default_reps = 5
                            reps_reales = st.number_input("Reps logradas:", min_value=0, max_value=100, value=default_reps, key=f"rep_{key_id}")
                        with col_s3: 
                            kilos_input = st.number_input("Kilos usados:", min_value=0.0, step=0.5, value=0.0, key=f"k_{key_id}")
                        
                        entradas_alumno[(nombre_ejercicio, s)] = {
                            "ejercicio": nombre_ejercicio, "serie": s, "kilos": kilos_input, "reps_reales": reps_reales, "rpe_serie": 0.0
                        }
                    
                    notas_ejercicio = st.text_input("Sensaciones del ejercicio:", placeholder="Ej: Molestia leve, volé, etc.", key=f"not_{sufijo}_{nombre_atleta}_{idx}")
                    for s in range(1, series_prescritas + 1): entradas_alumno[(nombre_ejercicio, s)]["notas"] = notas_ejercicio
                    st.markdown("<hr style='margin: 12px 0px; opacity: 0.15;'/>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: #84CC16; margin-top: 30px;'>📊 Evaluación General de la Sesión</h4>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1: rpe_global = st.select_slider("¿Qué tan dura estuvo la sesión hoy? (RPE Global):", options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], value=7)
    with col_g2: duracion_min = st.number_input("⏱️ ¿Cuántos minutos duró el entrenamiento?", min_value=1, max_value=300, value=60, step=5)

    if st.button("🏁 FINALIZAR ENTRENAMIENTO Y ENVIAR", use_container_width=True, type="primary", key=f"btn_finalizar_{sufijo}"):
        if es_espejo: st.info("ℹ️ Modo espejo de visualización.")
        else:
            fecha_hoy_texto = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM registros_entrenamiento WHERE alumno = ? AND fecha LIKE ?", (nombre_atleta, f"{fecha_hoy_texto}%"))
            if cursor.fetchone()[0] > 0: st.error(f"⚠️ Ya registraste tu sesión de hoy.")
            else:
                datos_validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                if not datos_validos: st.warning("⚠️ Completá las marcas antes de finalizar.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                    for datos in datos_validos:
                        cursor.execute("""
                            INSERT INTO registros_entrenamiento 
                            (fecha, alumno, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, rpe_serie, notas, rpe_global_sesion, duracion_minutos) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fecha_actual, nombre_atleta, nombre_de_la_rutina, datos["ejercicio"], datos["serie"], datos["kilos"], datos["reps_reales"], datos["rpe_serie"], datos["notas"], rpe_global, duracion_min))
                    conn.commit()
                    st.success("🚀 ¡Entrenamiento enviado con éxito!")
                    st.rerun()

# ==========================================
# 🚀 PANTALLAS SEGÚN ROL
# ==========================================
if st.session_state["rol_actual"] == "atleta":
    alumno_logueado = st.session_state["usuario_actual"]
    st.markdown(f"### 👋 ¡Hola, **{alumno_logueado}**!")
    tab_entrenar, tab_progreso = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Mi Historial"])
    with tab_entrenar: renderizar_tabla_entrenamiento(alumno_logueado, es_espejo=False)
    with tab_progreso:
        df_hist_atleta = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_logueado,))
        if df_hist_atleta.empty: st.info("Aún no registrás entrenamientos.")
        else: st.dataframe(df_hist_atleta.rename(columns={"nombre_rutina": "Plan", "fecha":"Fecha", "ejercicio":"Ejercicio", "nro_serie":"Serie", "kilos":"Kilos", "reps_reales":"Reps", "notas":"Notas"}), use_container_width=True, hide_index=True)

elif st.session_state["rol_actual"] == "admin":
    tab_dashboard, tab_rutinas, tab_clonar, tab_fichas, tab_aprobaciones, tab_excel = st.tabs([
        "📊 Historial", "📝 Diseñar Plan", "👥 Clonar Pizarra", "📋 Fichas Clínicas", "👥 Aprobar Atletas", "📚 Biblioteca"
    ])
    
    # 📊 MONITOR INTELIGENTE (CON SEMÁFORO DE ALERTAS CLÍNICAS)
    with tab_dashboard:
        st.markdown("### 🔍 Monitor General de Rendimiento")
        
        # Sistema de escaneo preventivo automático de palabras clave de dolor
        fecha_actual_hoy = datetime.now().strftime("%Y-%m-%d")
        df_alertas = pd.read_sql_query("SELECT alumno, ejercicio, notas FROM registros_entrenamiento WHERE fecha LIKE ? AND (notas LIKE '%dolor%' OR notas LIKE '%molestia%' OR notas LIKE '%tiron%' OR notas LIKE '%molesto%')", conn, params=(f"{fecha_actual_hoy}%",))
        
        if not df_alertas.empty:
            st.markdown("#### ⚠️ SEMÁFORO DE ALERTAS CLÍNICAS (HOY)")
            for _, al_row in df_alertas.iterrows():
                st.warning(f"🚨 **{al_row['alumno']}** reportó problemas en **{al_row['ejercicio']}**: *\"{al_row['notas']}\"*")
            st.divider()

        alumno_a_revisar = st.selectbox("👤 Seleccionar Atleta para auditar:", lista_alumnos_con_neutro, key="sb_hist_admin")
        if alumno_a_revisar == "- Seleccionar Atleta -":
            st.info("💡 Elegí un atleta para auditar el desglose de sus series reales.")
        else:
            df_total_alumno = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, nro_serie, kilos, reps_reales, notas, rpe_global_sesion, duracion_minutos FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_a_revisar,))
            if df_total_alumno.empty: st.warning(f"Sin entrenamientos guardados para {alumno_a_revisar}.")
            else:
                for fecha_sesion in df_total_alumno["fecha"].unique():
                    df_sesion_especifica = df_total_alumno[df_total_alumno["fecha"] == fecha_sesion]
                    r_name = df_sesion_especifica.iloc[0]["nombre_rutina"] or "Plan General"
                    rpe_g = df_sesion_especifica.iloc[0]["rpe_global_sesion"] or 7
                    dur_m = df_sesion_especifica.iloc[0]["duracion_minutos"] or 60
                    
                    with st.expander(f"🏋️‍♂️ {r_name} — {fecha_sesion} | 📊 sRPE Carga: {int(rpe_g)*int(dur_m)} (RPE {rpe_g} x {dur_m} min)"):
                        st.dataframe(df_sesion_especifica[["ejercicio", "nro_serie", "kilos", "reps_reales", "notas"]].rename(columns={"ejercicio": "Ejercicio", "nro_serie": "Serie", "kilos": "Kilos Anotados", "reps_reales": "Reps Reales", "notas": "Notas Atleta"}), use_container_width=True, hide_index=True)
                        if st.button("🗑️ Eliminar Sesión", key=f"del_{fecha_sesion.replace(' ', '_').replace(':', '_')}"):
                            cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno = ? AND fecha = ?", (alumno_a_revisar, fecha_sesion))
                            conn.commit()
                            st.rerun()

    # 📝 DISEÑAR PLAN CON VALIDACIÓN DE DUPLICADOS
    with tab_rutinas:
        st.markdown("### 📝 Diseñar Planificación Semanal")
        alumno_rutina = st.selectbox("Planificar para:", lista_alumnos_con_neutro, key="planif_select_admin")
        
        if alumno_rutina == "- Seleccionar Atleta -": st.info("Elegí un atleta para configurar su pizarra.")
        else:
            cursor.execute("SELECT nombre_rutina FROM rutinas_asignadas WHERE alumno = ? LIMIT 1", (alumno_rutina,))
            rutina_existente = cursor.fetchone()
            valor_sugerido_nombre = rutina_existente[0] if (rutina_existente and rutina_existente[0]) else ""
            nombre_de_la_rutina = st.text_input("🏷️ Nombre de la Planificación (Único):", value=valor_sugerido_nombre)
            
            nombre_duplicado = False
            if nombre_de_la_rutina.strip() != "":
                cursor.execute("SELECT COUNT(*) FROM rutinas_asignadas WHERE nombre_rutina = ? AND alumno != ?", (nombre_de_la_rutina.strip(), alumno_rutina))
                if cursor.fetchone()[0] > 0:
                    st.error("⚠️ Nombre en uso por otro atleta. Modificalo para evitar solapamientos.")
                    nombre_duplicado = True

            cursor.execute("SELECT nombre FROM biblioteca_ejercicios ORDER BY nombre ASC")
            ejercicios_db = [fila[0] for fila in cursor.fetchall()]
            ejercicio_rutina = st.selectbox("Seleccionar Ejercicio:", ejercicios_db) if ejercicios_db else st.text_input("Ejercicio manual:")
            bloque_seleccionado = st.selectbox("Asignar al Bloque o Día:", BLOQUES)
            
            col_r1, col_r2 = st.columns(2)
            with col_r1: series_obj = st.number_input("Series:", min_value=1, max_value=20, value=4)
            with col_r2: reps_obj = st.text_input("Repeticiones sugeridas:", value="5")
                
            if st.button("🚀 Inyectar Ejercicio a la Pizarra", use_container_width=True, disabled=nombre_duplicado):
                if ejercicio_rutina == "" or nombre_de_la_rutina.strip() == "": st.error("Faltan campos obligatorios.")
                else:
                    cursor.execute("INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) VALUES (?, ?, ?, ?, ?, ?, ?)", (alumno_rutina, nombre_de_la_rutina.strip(), ejercicio_rutina, bloque_seleccionado, int(series_obj), reps_obj, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.rerun()
                    
            st.divider()
            cursor.execute("SELECT id, ejercicio, bloque, series_objetivo, reps_objetivo FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
            ejercicios_actuales = cursor.fetchall()
            if ejercicios_actuales:
                for b_tit in BLOQUES:
                    items_b = [e for e in ejercicios_actuales if e[2] == b_tit]
                    if items_b:
                        st.markdown(f"**{b_tit}**")
                        for item in items_b: st.write(f" └─ {item[1]} ({item[3]}x{item[4]})")
                if st.button("🗑️ Vaciar Plan"):
                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
                    conn.commit()
                    st.rerun()

    # 👥 NUEVO MÓDULO: CLONACIÓN EN UN SOLO CLIC
    with tab_clonar:
        st.markdown("### 👥 Clonación y Copia de Pizarras Semanales")
        st.caption("Copia la rutina base completa de un atleta a otro de forma directa para ahorrar tiempo de tipeo.")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1: atleta_origen = st.selectbox("Atleta Origen (Copiar desde aquí):", lista_alumnos_con_neutro, key="at_origen")
        with col_c2: atleta_destino = st.selectbox("Atleta Destino (Pegar rutina aquí):", lista_alumnos_con_neutro, key="at_destino")
            
        if st.button("⚡ CLONAR RUTINA COMPLETA", use_container_width=True, type="primary"):
            if atleta_origen == "- Seleccionar Atleta -" or atleta_destino == "- Seleccionar Atleta -":
                st.error("❌ Debes seleccionar tanto el atleta de origen como el de destino.")
            elif atleta_origen == atleta_destino:
                st.error("❌ El atleta origen y destino no pueden ser el mismo.")
            else:
                cursor.execute("SELECT nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo FROM rutinas_asignadas WHERE alumno = ?", (atleta_origen,))
                rutina_origen_datos = cursor.fetchall()
                if not rutina_origen_datos:
                    st.warning(f"El atleta {atleta_origen} no tiene ejercicios en su pizarra para copiar.")
                else:
                    # Limpiar destino antes de pegar la nueva
                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (atleta_destino,))
                    for f_rut in rutina_origen_datos:
                        cursor.execute("INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) VALUES (?, ?, ?, ?, ?, ?, ?)", (atleta_destino, f_rut[0], f_rut[1], f_rut[2], f_rut[3], f_rut[4], datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success(f"🎉 ¡Pizarra clonada con éxito! {len(rutina_origen_datos)} ejercicios transferidos a {atleta_destino}.")
                    st.rerun()

    # 📋 FICHAS INTEGRADAS INLINE EN CADA EXPANSIBLE
    with tab_fichas:
        st.markdown("### 📋 Fichas Clínicas")
        cursor.execute("SELECT nombre_apellido, usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos WHERE estado = 'aprobado' ORDER BY nombre_apellido ASC")
        todos_al = cursor.fetchall()
        
        if not todos_al: st.info("No hay alumnos aprobados.")
        else:
            for al_fila in todos_al:
                n_c, u_a, f_n, p_k, a_m, d_e, o_f = al_fila
                with st.expander(f"👤 {n_c} | Deporte: {d_e} | Edad: {calcular_edad(f_n)} años"):
                    st.text(f"• Usuario: {u_a}  • Peso: {p_k} kg  • Altura: {a_m} m\n• Foco: {o_f}")
                    
                    if st.checkbox("✍️ Editar Atleta", key=f"chk_{n_c.replace(' ','_')}"):
                        with st.form(f"f_inline_{n_c.replace(' ','_')}"):
                            nuevo_user = st.text_input("Usuario:", value=u_a)
                            nuevo_dep = st.text_input("Deporte:", value=d_e)
                            nuevo_peso = st.number_input("Peso:", value=float(p_k))
                            nuevo_alt = st.number_input("Altura:", value=float(a_m))
                            nuevo_obj = st.text_area("Objetivo:", value=o_f)
                            
                            c_b1, c_b2 = st.columns(2)
                            with c_b1: 
                                if st.form_submit_button("💾 Guardar"):
                                    cursor.execute("UPDATE alumnos SET usuario=?, peso=?, altura=?, deporte=?, objetivo=? WHERE nombre_apellido=?", (nuevo_user, nuevo_peso, nuevo_alt, nuevo_dep, nuevo_obj, n_c))
                                    conn.commit()
                                    st.rerun()
                            with c_b2:
                                if st.form_submit_button("🗑️ ELIMINAR ACÁ", type="primary"):
                                    cursor.execute("DELETE FROM alumnos WHERE nombre_apellido=?", (n_c,))
                                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno=?", (n_c,))
                                    cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno=?", (n_c,))
                                    conn.commit()
                                    st.rerun()

    # 👥 NUEVO PANEL: MODERADOR Y APROBADOR DE MATRÍCULAS
    with tab_aprobaciones:
        st.markdown("### 👥 Solicitudes de Autoregistro Pendientes")
        cursor.execute("SELECT id, nombre_apellido, usuario, deporte, objetivo FROM alumnos WHERE estado = 'pendiente' ORDER BY id ASC")
        pendientes = cursor.fetchall()
        
        if not pendientes:
            st.info("No hay solicitudes pendientes en este momento. El sistema está al día.")
        else:
            for p_atleta in pendientes:
                p_id, p_nom, p_user, p_dep, p_obj = p_atleta
                with st.container():
                    st.markdown(f"**👤 Atleta:** `{p_nom}` | **Usuario propuesto:** `{p_user}`")
                    st.text(f"• Disciplina: {p_dep}\n• Meta declarada: {p_obj}")
                    
                    col_ap1, col_ap2, _ = st.columns([1, 1, 3])
                    with col_ap1:
                        if st.button("✅ APROBAR ACCESO", key=f"ap_{p_id}"):
                            cursor.execute("UPDATE alumnos SET estado = 'aprobado' WHERE id = ?", (p_id,))
                            conn.commit()
                            st.success(f"¡{p_nom} aprobado!")
                            st.rerun()
                    with col_ap2:
                        if st.button("❌ RECHAZAR", key=f"re_{p_id}", type="primary"):
                            cursor.execute("DELETE FROM alumnos WHERE id = ?", (p_id,))
                            conn.commit()
                            st.rerun()
                    st.markdown("<hr style='margin:10px 0px; opacity:0.1;'/>", unsafe_allow_html=True)

    with tab_excel:
        st.markdown("### 📚 Importar Biblioteca (.xlsx / .csv)")
        archivo_subido = st.file_uploader("Arrastrá tu archivo", type=["xlsx", "csv"])
        if archivo_subido is not None:
            try:
                df_ejercicios = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido)
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                columnas_actuales = df_ejercicios.columns.tolist()
                col_nombre = next((c for c in columnas_actuales if c.lower() in ["nombre", "ejercicio", "name"]), None)
                col_grupo = next((c for c in columnas_actuales if c.lower() in ["grupo", "musculo", "target"]), None)
                col_video = next((c for c in columnas_actuales if c.lower() in ["video", "link", "url"]), None)
                
                if col_nombre and st.button("Confirmar Importación"):
                    for _, fila in df_ejercicios.iterrows():
                        n_val = str(fila[col_nombre]).strip()
                        if n_val == "" or n_val.lower() == "nan": continue
                        g_val = str(fila[col_grupo]).strip() if col_grupo else "General"
                        v_val = str(fila[col_video]).strip() if col_video else ""
                        cursor.execute("INSERT OR IGNORE INTO biblioteca_ejercicios (nombre, grupo_muscular, link_video) VALUES (?, ?, ?)", (n_val, g_val, v_val))
                    conn.commit()
                    st.success("¡Base importada con éxito!")
                    st.rerun()
            except Exception as e: st.error(f"Error: {e}")
