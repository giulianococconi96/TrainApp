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
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad
    except Exception:
        return 0

# ==========================================
# 0. CONSTANTES GLOBALES
# ==========================================
BLOQUES = ["🔥 Entrada en Calor", "⚡ Bloque Principal", "🧘 Bloque Final / Vuelta a la Calma"]

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

# Creación de tablas (Modificada columna edad por fecha_nacimiento)
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
        objetivo TEXT
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
        kilos REAL, 
        rpe REAL, 
        notas TEXT
    )
""")
conn.commit()


# ==========================================
# 2. CONFIGURACIÓN VISUAL GENERAL (UI)
# ==========================================
st.set_page_config(page_title="TrainApp - @pf.giuliano", page_icon="⚡", layout="wide")

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>⚡ TRAINAPP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #84CC16; font-weight: bold; letter-spacing: 1px; margin-top: 0px;'>HIGH PERFORMANCE MANAGEMENT</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 0.9rem;'>By @pf.giuliano</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# 🔑 SISTEMA DE AUTENTICACIÓN (LOGIN)
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""

if not st.session_state["autenticado"]:
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
                if MODO_LOCAL and input_pass == ADMIN_PASS_PLANA:
                    es_admin = True
                elif not MODO_LOCAL and bcrypt.checkpw(input_pass.encode(), ADMIN_PASS_HASH):
                    es_admin = True

            if es_admin:
                st.session_state["autenticado"] = True
                st.session_state["usuario_actual"] = "Prof. Giuliano"
                st.session_state["rol_actual"] = "admin"
                st.rerun()
            else:
                cursor.execute("SELECT nombre_apellido, contrasena FROM alumnos WHERE usuario = ?", (input_user,))
                user_db = cursor.fetchone()
                if user_db and verificar_password(input_pass, user_db[1]):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = user_db[0]
                    st.session_state["rol_actual"] = "atleta"
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()

st.sidebar.markdown(f"👤 Conectado: **{st.session_state['usuario_actual']}**")
if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

cursor.execute("SELECT nombre_apellido FROM alumnos ORDER BY nombre_apellido ASC")
lista_alumnos = [fila[0] for fila in cursor.fetchall()]

# ==========================================
# 🛠️ TRADUCTOR DINÁMICO DE RPE
# ==========================================
def obtener_descripcion_rpe(valor_rpe):
    if valor_rpe >= 10: return "🔴 Esfuerzo Máximo (0 RIR)"
    elif valor_rpe >= 9: return "🟠 Muy Duro (1 RIR)"
    elif valor_rpe >= 8: return "🟡 Pesado / Exigente (2 RIR)"
    elif valor_rpe >= 7: return "🟢 Moderado (3 RIR)"
    return "🔵 Suave / Técnico (+4 RIR)"

# ==========================================
# 🛠️ FUNCIÓN MOTOR: RENDERIZAR INTERFAZ ATLETA
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
        st.info("No hay ejercicios asignados para la sesión de hoy.")
        return
        
    nombre_de_la_rutina = rutina_completa[0][5]
    if not nombre_de_la_rutina:
        nombre_de_la_rutina = "Rutina General"
    
    if es_espejo:
        st.warning(f"👀 MODO ESPEJO: Simulando la pantalla del cliente. Rutina Activa: **{nombre_de_la_rutina}**")
    else:
        st.markdown(f"### 📋 Planificación Activa: <span style='color: #CCFF00;'>{nombre_de_la_rutina}</span>", unsafe_allow_html=True)
        st.caption("Completá tus marcas abajo al finalizar el entrenamiento.")

    entradas_alumno = {}
    
    for key_bloque in BLOQUES:
        ejercicios_del_bloque = [r for r in rutina_completa if r[1] == key_bloque]
        if ejercicios_del_bloque:
            st.markdown(f"<h4 style='color: #CCFF00; margin-top: 15px;'>{key_bloque}</h4>", unsafe_allow_html=True)
            header_cols = st.columns([3, 1, 1, 1.5, 2, 2.5, 2])
            header_cols[0].markdown("**Ejercicio**")
            header_cols[1].markdown("**Series**")
            header_cols[2].markdown("**Reps**")
            header_cols[3].markdown("**Video**")
            header_cols[4].markdown("**Kilos**")
            header_cols[5].markdown("**RPE / Intensidad**")
            header_cols[6].markdown("**Notas**")
            st.markdown("<hr style='margin: 4px 0px;', />", unsafe_allow_html=True)
            
            for idx, ej in enumerate(ejercicios_del_bloque):
                row_cols = st.columns([3, 1, 1, 1.5, 2, 2.5, 2])
                row_cols[0].write(f"💪 **{ej[0]}**")
                row_cols[1].write(f"{ej[2]}")
                row_cols[2].write(f"{ej[3]}")
                
                if ej[4] and "http" in ej[4]:
                    row_cols[3].markdown(f"[🎥 Ver Video]({ej[4]})")
                else:
                    row_cols[3].write("❌ Sin link")
                
                key_id = f"{sufijo}_{nombre_atleta}_{idx}_{ej[0].replace(' ', '_')}"
                
                with row_cols[4]: 
                    kilos_input = st.number_input("Kilos", min_value=0.0, step=0.5, value=0.0, label_visibility="collapsed", key=f"k_{key_id}")
                
                with row_cols[5]: 
                    rpe_input = st.slider("RPE", min_value=1.0, max_value=10.0, step=0.5, value=8.0, label_visibility="collapsed", key=f"r_{key_id}")
                    st.caption(f"**{obtener_descripcion_rpe(rpe_input)}**")
                    
                with row_cols[6]: 
                    notas_input = st.text_input("Notas", placeholder="Sensaciones...", value="", label_visibility="collapsed", key=f"n_{key_id}")
                
                entradas_alumno[(key_bloque, ej[0], idx)] = {
                    "ejercicio": ej[0], "kilos": kilos_input, "rpe": rpe_input, "notes": notas_input
                }
                st.markdown("<hr style='margin: 2px 0px; opacity: 0.3;', />", unsafe_allow_html=True)
    
    st.write("")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 GUARDAR PROGRESO PARCIAL", use_container_width=True, key=f"btn_p_{nombre_atleta}_{sufijo}"):
            st.toast("🔄 ¡Progreso temporal guardado!", icon="💾")
            
    with col_btn2:
        if st.button("🏁 FINALIZAR Y CERRAR SESIÓN", use_container_width=True, type="primary", key=f"btn_c_{nombre_atleta}_{sufijo}"):
            if es_espejo:
                st.info("ℹ️ Guardado deshabilitado: Estás en modo de prueba visual.")
            else:
                fecha_hoy_texto = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("""
                    SELECT COUNT(*) FROM registros_entrenamiento 
                    WHERE alumno = ? AND fecha LIKE ?
                """, (nombre_atleta, f"{fecha_hoy_texto}%"))
                ya_entreno_hoy = cursor.fetchone()[0]
                
                if ya_entreno_hoy > 0:
                    st.error(f"⚠️ ¡Atención! Ya registraste una sesión el día de hoy ({fecha_hoy_texto}).")
                else:
                    datos_validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["notes"].strip() != ""]
                    
                    if not datos_validos:
                        st.warning("⚠️ No se puede crear una sesión vacía. Ingresá marcas antes de finalizar.")
                    else:
                        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                        for datos in datos_validos:
                            cursor.execute("""
                                INSERT INTO registros_entrenamiento (fecha, alumno, nombre_rutina, ejercicio, kilos, rpe, notas) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (fecha_actual, nombre_atleta, nombre_de_la_rutina, datos["ejercicio"], datos["kilos"], datos["rpe"], datos["notes"]))
                        
                        conn.commit()
                        st.success("🚀 ¡Sesión guardada y registrada con éxito!")
                        st.rerun()

# ==========================================
# 🚀 FLUJO DE PANTALLAS SEGÚN EL ROL
# ==========================================

# --- ROL ATLETA ---
if st.session_state["rol_actual"] == "atleta":
    alumno_logueado = st.session_state["usuario_actual"]
    st.markdown(f"### 👋 ¡Hola de nuevo, **{alumno_logueado}**!")
    
    tab_entrenar, tab_progreso = st.tabs(["🏋️‍♂️ Mi Sesión de Hoy", "📈 Mi Historial & Seguridad"])
    with tab_entrenar:
        renderizar_tabla_entrenamiento(alumno_logueado, es_espejo=False)
        
    with tab_progreso:
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            st.markdown("### 📈 Tu Historial de Cargas")
            df_hist_atleta = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, kilos, rpe, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id ASC", conn, params=(alumno_logueado,))
            if df_hist_atleta.empty:
                st.info("Aún no tenés entrenamientos archivados.")
            else:
                ejercicios_registrados = df_hist_atleta["ejercicio"].unique()
                ej_grafico = st.selectbox("Seleccioná el ejercicio:", ejercicios_registrados, key="atleta_ej_select")
                df_filtrado = df_hist_atleta[df_hist_atleta["ejercicio"] == ej_grafico]
                st.line_chart(data=df_filtrado, x="fecha", y="kilos", color="#CCFF00")
                st.dataframe(df_filtrado.sort_values(by="fecha", ascending=False).rename(columns={"nombre_rutina": "Rutina", "fecha": "Fecha", "ejercicio": "Ejercicio", "kilos": "Kilos", "rpe": "RPE", "notas": "Notas"}), use_container_width=True, hide_index=True)
        with col_p2:
            st.markdown("### 🔐 Cambiar Contraseña")
            with st.form("form_cambio_pass"):
                nueva_pass = st.text_input("Nueva Contraseña:", type="password")
                confirmar_pass = st.text_input("Confirmar Nueva Contraseña:", type="password")
                btn_cambio = st.form_submit_button("Actualizar Clave 🔄", use_container_width=True)
            if btn_cambio:
                if nueva_pass == "": st.error("❌ El campo no puede estar vacío.")
                elif nueva_pass != confirmar_pass: st.error("❌ Las contraseñas no coinciden.")
                else:
                    cursor.execute("UPDATE alumnos SET contrasena = ? WHERE nombre_apellido = ?", (hashear_password(nueva_pass), alumno_logueado))
                    conn.commit()
                    st.success("🎉 ¡Contraseña actualizada!")

# --- ROL ADMINISTRADOR (PROFE) ---
elif st.session_state["rol_actual"] == "admin":
    tab_dashboard, tab_rutinas, tab_espejo, tab_fichas, tab_alta, tab_excel = st.tabs([
        "📊 Historial por Sesiones", 
        "📝 Diseñar Sesión", 
        "👀 Espejo: Vista Cliente", 
        "📋 Fichas de Alumnos", 
        "👥 Registrar Alumno", 
        "📚 Base de Ejercicios"
    ])
    
    with tab_dashboard:
        st.markdown("### 🔍 Monitor de Sesiones por Alumno")
        if not lista_alumnos: st.info("No hay alumnos registrados.")
        else:
            alumno_a_revisar = st.selectbox("👤 Seleccionar Atleta para monitorear:", lista_alumnos)
            df_total_alumno = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, kilos, rpe, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_a_revisar,))
            if df_total_alumno.empty: st.warning(f"El atleta {alumno_a_revisar} todavía no guardó ninguna sesión.")
            else:
                sesiones_unicas = df_total_alumno["fecha"].unique()
                st.markdown(f"#### 📅 Sesiones registradas de **{alumno_a_revisar}**")
                
                for fecha_sesion in sesiones_unicas:
                    df_sesion_especifica = df_total_alumno[df_total_alumno["fecha"] == fecha_sesion]
                    r_name = df_sesion_especifica.iloc[0]["nombre_rutina"]
                    if not r_name: r_name = "Rutina General"
                    
                    with st.expander(f"🏋️‍♂️ {r_name} — Finalizada el: {fecha_sesion}"):
                        st.dataframe(df_sesion_especifica[["ejercicio", "kilos", "rpe", "notas"]].rename(columns={"ejercicio": "Ejercicio", "kilos": "Kilos", "rpe": "RPE", "notas": "Notas"}), use_container_width=True, hide_index=True)
                        
                        if st.button("🗑️ Eliminar esta Sesión Definitivamente", key=f"del_{fecha_sesion.replace(' ', '_').replace(':', '_')}"):
                            cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno = ? AND fecha = ?", (alumno_a_revisar, fecha_sesion))
                            conn.commit()
                            st.success(f"❌ Sesión eliminada correctamente.")
                            st.rerun()

    with tab_rutinas:
        st.markdown("### 📝 Diseñar Planificación por Bloques")
        if not lista_alumnos: 
            st.warning("No hay atletas registrados aún. Registrá un alumno en la pestaña de al lado.")
        else:
            alumno_rutina = st.selectbox("Planificar para:", lista_alumnos, key="planif_select")
            
            cursor.execute("SELECT nombre_rutina FROM rutinas_asignadas WHERE alumno = ? LIMIT 1", (alumno_rutina,))
            rutina_existente = cursor.fetchone()
            valor_sugerido_nombre = rutina_existente[0] if (rutina_existente and rutina_existente[0]) else "Rutina: Julio"
            
            nombre_de_la_rutina = st.text_input("🏷️ Nombre de la Planificación / Mes:", value=valor_sugerido_nombre)
            
            cursor.execute("SELECT nombre FROM biblioteca_ejercicios ORDER BY nombre ASC")
            ejercicios_db = [fila[0] for fila in cursor.fetchall()]
            
            st.markdown("#### ⚙️ Inyectar Ejercicio al Plan:")
            if not ejercicios_db:
                st.info("💡 Consejo: Tu biblioteca está vacía. Podés escribir un ejercicio rápido abajo o cargar tu Excel en la pestaña 'Base de Ejercicios'.")
                ejercicio_rutina = st.text_input("Escribí el nombre del Ejercicio manual:")
            else:
                ejercicio_rutina = st.selectbox("Seleccionar Ejercicio de la Biblioteca:", ejercicios_db)
                
            bloque_seleccionado = st.selectbox("Asignar al Bloque / Segmento:", BLOQUES)
            
            col_r1, col_r2 = st.columns(2)
            with col_r1: series_obj = st.number_input("Series objetivo:", min_value=1, max_value=10, value=4)
            with col_r2: reps_obj = st.text_input("Repeticiones objetivo:", value="5")
                
            if st.button("🚀 Inyectar Ejercicio a la Pizarra", use_container_width=True):
                if ejercicio_rutina == "":
                    st.error("Por favor escribí o seleccioná un ejercicio.")
                else:
                    cursor.execute("""
                        INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (alumno_rutina, nombre_de_la_rutina.strip(), ejercicio_rutina, bloque_seleccionado, series_obj, reps_obj, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success(f"💪 ¡Inyectado con éxito!")
                    st.rerun()
                    
            st.divider()
            cursor.execute("SELECT id, ejercicio, bloque, series_objetivo, reps_objetivo, nombre_rutina FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
            ejercicios_actuales = cursor.fetchall()
            if ejercicios_actuales:
                r_label = ejercicios_actuales[0][5] if ejercicios_actuales[0][5] else "Rutina General"
                st.markdown(f"#### 📅 Pizarra de Trabajo Actual: `{r_label}`")
                for b_tit in BLOQUES:
                    items_b = [e for e in ejercicios_actuales if e[2] == b_tit]
                    if items_b:
                        st.markdown(f"**{b_tit}**")
                        for item in items_b: st.write(f" └─ {item[1]} ({item[3]}x{item[4]})")
                if st.button("🗑️ Vaciar Sesión Completa"):
                    cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
                    conn.commit()
                    st.rerun()

    with tab_espejo:
        st.markdown("### 📱 Simulador de Interfaz de Alumno")
        if not lista_alumnos: st.info("No hay alumnos registrados para simular.")
        else:
            alumno_espejo = st.selectbox("Seleccioná un alumno para ver cómo le figura la app en su celu:", lista_alumnos, key="select_espejo")
            st.divider()
            renderizar_tabla_entrenamiento(alumno_espejo, es_espejo=True)

    # =========================================================================
    # 👀 PANEL DE CONSULTA Y EDITOR CON CÁLCULO DINÁMICO DE EDAD
    # =========================================================================
    with tab_fichas:
        st.markdown("### 📋 Fichas Técnicas y Editor de Clientes")
        df_base_alumnos = pd.read_sql_query("SELECT nombre_apellido, usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos ORDER BY nombre_apellido ASC", conn)
        
        if df_base_alumnos.empty: 
            st.info("No hay alumnos registrados.")
        else:
            mes_actual_str = datetime.now().strftime("%Y-%m-%d")[:7]
            
            # Consultas dinámicas para la grilla
            cursor.execute("SELECT alumno, COUNT(DISTINCT SUBSTR(fecha, 1, 10)) FROM registros_entrenamiento WHERE fecha LIKE ? GROUP BY alumno", (f"{mes_actual_str}%",))
            sesiones_por_alumno = dict(cursor.fetchall())
            
            cursor.execute("SELECT alumno, MIN(fecha) FROM registros_entrenamiento GROUP BY alumno")
            primeras_sesiones = dict(cursor.fetchall())
            
            df_base_alumnos["Sesiones Este Mes"] = df_base_alumnos["nombre_apellido"].map(sesiones_por_alumno).fillna(0).astype(int)
            df_base_alumnos["Fecha de Inicio"] = df_base_alumnos["nombre_apellido"].map(primeras_sesiones).fillna("Pendiente (Sin entrenar)")
            
            # Calculamos la edad al vuelo para cada fila de la tabla
            df_base_alumnos["Edad"] = df_base_alumnos["fecha_nacimiento"].apply(calcular_edad)
            
            df_formateado = df_base_alumnos[[
                "nombre_apellido", "Fecha de Inicio", "Sesiones Este Mes", "usuario", "Edad", "fecha_nacimiento", "peso", "altura", "deporte", "objetivo"
            ]].rename(columns={
                "nombre_apellido": "Nombre y Apellido", "usuario": "Usuario Acceso", "fecha_nacimiento": "Fecha Nacimiento", "peso": "Peso (kg)", "altura": "Altura (m)", "deporte": "Especialidad Deportiva", "objetivo": "Foco Planificación"
            })
            st.dataframe(df_formateado, use_container_width=True, hide_index=True)
            
            st.divider()
            
            st.markdown("### 🛠️ Editor Clínico de Fichas")
            alumno_editar = st.selectbox("👤 Seleccionar atleta para editar o remover permanentemente:", lista_alumnos, key="select_editor_atleta")
            
            if alumno_editar:
                cursor.execute("SELECT usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos WHERE nombre_apellido = ?", (alumno_editar,))
                datos_al = cursor.fetchone()
                
                if datos_al:
                    # Parseamos la fecha guardada para que el calendario del editor se posicione en su fecha real
                    try:
                        fecha_nac_default = datetime.strptime(datos_al[1], "%Y-%m-%d").date()
                    except Exception:
                        fecha_nac_default = date(2000, 1, 1)

                    with st.form("form_edicion_alumno", clear_on_submit=False):
                        st.markdown(f"✍️ **Modificando los parámetros de:** `{alumno_editar}` (Edad calculada hoy: **{calcular_edad(datos_al[1])} años**)")
                        col_ed1, col_ed2 = st.columns(2)
                        with col_ed1: ed_user = st.text_input("Usuario Acceso (Login):", value=datos_al[0]).strip().lower()
                        with col_ed2: ed_deporte = st.text_input("Especialidad Deportiva:", value=datos_al[4])
                        
                        col_ed3, col_ed4, col_ed5 = st.columns(3)
                        with col_ed3: ed_nacimiento = st.date_input("Fecha de Nacimiento:", value=fecha_nac_default, min_value=date(1940, 1, 1), max_value=date.today())
                        with col_ed4: ed_peso = st.number_input("Peso (kg):", min_value=0.0, step=0.1, value=float(datos_al[2]))
                        with col_ed5: ed_altura = st.number_input("Altura (m):", min_value=0.0, step=0.01, value=float(datos_al[3]))
                        
                        ed_objetivo = st.text_area("Foco de la Planificación:", value=datos_al[5])
                        
                        col_sub_ed1, col_sub_ed2 = st.columns(2)
                        with col_sub_ed1:
                            btn_guardar_edicion = st.form_submit_button("💾 Guardar Cambios en Ficha", use_container_width=True)
                        with col_sub_ed2:
                            btn_eliminar_alumno = st.form_submit_button("🗑️ ELIMINAR ALUMNO PERMANENTEMENTE", type="primary", use_container_width=True)
                    
                    if btn_guardar_edicion:
                        if ed_user == "":
                            st.error("El usuario de acceso no puede quedar vacío.")
                        else:
                            try:
                                cursor.execute("""
                                    UPDATE alumnos 
                                    SET usuario = ?, fecha_nacimiento = ?, peso = ?, altura = ?, deporte = ?, objetivo = ?
                                    WHERE nombre_apellido = ?
                                """, (ed_user, ed_nacimiento.strftime("%Y-%m-%d"), ed_peso, ed_altura, ed_deporte, ed_objetivo, alumno_editar))
                                conn.commit()
                                st.success(f"🎉 ¡Ficha de {alumno_editar} actualizada correctamente!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("❌ El nombre de usuario ya está asignado a otro alumno.")
                                
                    if btn_eliminar_alumno:
                        cursor.execute("DELETE FROM alumnos WHERE nombre_apellido = ?", (alumno_editar,))
                        cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno = ?", (alumno_editar,))
                        cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno = ?", (alumno_editar,))
                        conn.commit()
                        st.success(f"🔥 El alumno {alumno_editar} fue borrado por completo.")
                        st.rerun()

    # =========================================================================
    # 👀 REGISTRO DE ALUMNO CON CALENDARIO DE NACIMIENTO
    # =========================================================================
    with tab_alta:
        st.markdown("### 👤 Registro y Credenciales de Alumno")
        
        if "mensaje_exito_alta" in st.session_state:
            st.success(st.session_state["mensaje_exito_alta"])
            del st.session_state["mensaje_exito_alta"]
        
        with st.form("alta_alumno", clear_on_submit=True):
            nombre_ap = st.text_input("Nombre y Apellido:")
            col_cred1, col_cred2 = st.columns(2)
            with col_cred1: user_atleta = st.text_input("Nombre de Usuario (Login):").strip().lower()
            with col_cred2: pass_atleta = st.text_input("Contraseña de Acceso:", type="password")
            
            col_a1, col_a2, col_a3 = st.columns(3)
            # Input de tipo Fecha nativo en lugar de número entero
            with col_a1: nacimiento_f = st.date_input("Fecha de Nacimiento:", value=date(2000, 1, 1), min_value=date(1940, 1, 1), max_value=date.today())
            with col_a2: peso_f = st.number_input("Peso (kg):", min_value=0.0, step=0.1, value=70.0)
            with col_a3: altura_f = st.number_input("Altura (m):", min_value=0.0, step=0.01, value=1.75)
            
            deporte = st.text_input("Especialidad Deportiva:")
            objetivo = st.text_area("Foco de la Planificación:")
            btn_alta = st.form_submit_button("Guardar y Crear Cuenta 👤")
            
        if btn_alta:
            if nombre_ap.strip() == "" or user_atleta.strip() == "":
                st.error("❌ Los campos 'Nombre' y 'Usuario' son obligatorios.")
            elif pass_atleta == "":
                st.error("❌ La contraseña no puede estar vacía.")
            else:
                try:
                    # Guardamos la fecha de nacimiento formateada como string estándar de base de datos
                    str_nacimiento = nacimiento_f.strftime("%Y-%m-%d")
                    cursor.execute("""
                        INSERT INTO alumnos (nombre_apellido, usuario, contrasena, fecha_nacimiento, peso, altura, deporte, objetivo) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (nombre_ap.strip(), user_atleta, hashear_password(pass_atleta), str_nacimiento, peso_f, altura_f, deporte, objetivo))
                    conn.commit()
                    
                    st.session_state["mensaje_exito_alta"] = f"🎉 ¡Cuenta creada con éxito para {nombre_ap}! Formulario vaciado."
                    st.rerun()
                    
                except sqlite3.IntegrityError: 
                    st.error("❌ El nombre de usuario o atleta ya existe en el sistema.")

    with tab_excel:
        st.markdown("### 📚 Sincronizar Biblioteca de Ejercicios")
        st.caption("Asegurarse de que su archivo tenga una columna para el nombre del ejercicio, otra para el grupo muscular y opcionalmente una para el link del video.")
        
        archivo_subido = st.file_uploader("Arrastrá tu biblioteca (.xlsx o .csv)", type=["xlsx", "csv"])
        
        if archivo_subido is not None:
            try:
                if archivo_subido.name.endswith('.xlsx'):
                    df_ejercicios = pd.read_excel(archivo_subido)
                else:
                    df_ejercicios = pd.read_csv(archivo_subido)
                
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                
                st.markdown("📝 **Vista previa del archivo cargado:**")
                st.dataframe(df_ejercicios.head(), use_container_width=True)
                
                columnas_actuales = df_ejercicios.columns.tolist()
                
                col_nombre = next((c for c in columnas_actuales if c.lower() in ["nombre", "ejercicio", "ejercicios", "name", "activity"]), None)
                col_grupo = next((c for c in columnas_actuales if c.lower() in ["grupo_muscular", "grupo muscular", "grupo", "músculo", "musculo", "target"]), None)
                col_video = next((c for c in columnas_actuales if c.lower() in ["link_video", "link video", "video", "link", "url"]), None)
                
                if not col_nombre:
                    st.error("❌ No se encontró ninguna columna que represente el nombre del ejercicio.")
                else:
                    if st.button("🚀 Confirmar Sincronización e Importar"):
                        filas_insertadas = 0
                        for _, fila in df_ejercicios.iterrows():
                            nombre_val = str(fila[col_nombre]).strip()
                            if nombre_val == "" or nombre_val.lower() == "nan":
                                continue
                                
                            grupo_val = str(fila[col_grupo]).strip() if col_grupo else "General"
                            video_val = str(fila[col_video]).strip() if col_video else ""
                            
                            if grupo_val.lower() == "nan": grupo_val = "General"
                            if video_val.lower() == "nan": video_val = ""
                            
                            cursor.execute("""
                                INSERT OR IGNORE INTO biblioteca_ejercicios (nombre, grupo_muscular, link_video) 
                                VALUES (?, ?, ?)
                            """, (nombre_val, grupo_val, video_val))
                            filas_insertadas += 1
                            
                        conn.commit()
                        st.success(f"💪 ¡Base sincronizada correctamente! Se procesaron {filas_insertadas} ejercicios.")
                        st.rerun()
                        
            except Exception as e: 
                st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
