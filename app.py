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
    if valor_rpe >= 10: return "🔴 Máximo"
    elif valor_rpe >= 9: return "🟠 Muy Duro"
    elif valor_rpe >= 8: return "🟡 Exigente"
    elif valor_rpe >= 7: return "🟢 Moderado"
    return "🔵 Suave"

# ==========================================
# 📱 REFORMADO: DISEÑO MOBILE INTEGRAL PARA ATLETA
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
        
    nombre_de_la_rutina = rutina_completa[0][5] or "Rutina General"
    
    if es_espejo:
        st.warning(f"👀 MODO ESPEJO: Vista celular. Plan: **{nombre_de_la_rutina}**")
    else:
        st.markdown(f"### 📋 Plan Activo: <span style='color: #CCFF00;'>{nombre_de_la_rutina}</span>", unsafe_allow_html=True)
        st.caption("Ingresá tus marcas al terminar las series de cada ejercicio.")

    entradas_alumno = {}
    
    for key_bloque in BLOQUES:
        ejercicios_del_bloque = [r for r in rutina_completa if r[1] == key_bloque]
        if ejercicios_del_bloque:
            st.markdown(f"<h4 style='color: #CCFF00; margin-top: 20px; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{key_bloque}</h4>", unsafe_allow_html=True)
            
            for idx, ej in enumerate(ejercicios_del_bloque):
                # Contenedor visual tipo tarjeta móvil para cada ejercicio
                with st.container():
                    # Línea 1: Título y link
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.markdown(f"💪 **{ej[0]}** — `{ej[2]}x{ej[3]}`")
                    with col_t2:
                        if ej[4] and "http" in ej[4]:
                            st.markdown(f"[🎥 Video]({ej[4]})")
                        else:
                            st.caption("❌ Link")
                    
                    # Línea 2: Casillas de entrada ordenadas en 3 columnas perfectas para celular
                    key_id = f"{sufijo}_{nombre_atleta}_{idx}_{ej[0].replace(' ', '_')}"
                    col_in1, col_in2, col_in3 = st.columns(3)
                    
                    with col_in1:
                        kilos_input = st.number_input("Kilos:", min_value=0.0, step=0.5, value=0.0, key=f"k_{key_id}")
                    
                    with col_in2:
                        # Reemplazamos slider por un selectbox indexado numérico ideal para dedos en pantalla táctil
                        rpe_input = st.selectbox("RPE / RIR:", options=[10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.0, 5.0], index=4, key=f"r_{key_id}")
                        st.caption(f"{obtener_descripcion_rpe(rpe_input)}")
                        
                    with col_in3:
                        notas_input = st.text_input("Notas:", placeholder="Reps reales...", value="", key=f"n_{key_id}")
                    
                    entradas_alumno[(key_bloque, ej[0], idx)] = {
                        "ejercicio": ej[0], "kilos": kilos_input, "rpe": rpe_input, "notes": notas_input
                    }
                    st.markdown("<hr style='margin: 8px 0px; opacity: 0.2;'/>", unsafe_allow_html=True)
    
    st.write("")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 GUARDAR AVANCE PARCIAL", use_container_width=True, key=f"btn_p_{nombre_atleta}_{sufijo}"):
            st.toast("🔄 ¡Progreso temporal guardado!", icon="💾")
            
    with col_btn2:
        if st.button("🏁 FINALIZAR ENTRENAMIENTO", use_container_width=True, type="primary", key=f"btn_c_{nombre_atleta}_{sufijo}"):
            if es_espejo:
                st.info("ℹ️ Modo de prueba: Datos no guardados.")
            else:
                fecha_hoy_texto = datetime.now().strftime("%Y-%m-%d")
                cursor.execute("SELECT COUNT(*) FROM registros_entrenamiento WHERE alumno = ? AND fecha LIKE ?", (nombre_atleta, f"{fecha_hoy_texto}%"))
                if cursor.fetchone()[0] > 0:
                    st.error(f"⚠️ Ya guardaste un entrenamiento hoy ({fecha_hoy_texto}).")
                else:
                    datos_validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["notes"].strip() != ""]
                    if not datos_validos:
                        st.warning("⚠️ Cargá marcas o notas antes de finalizar.")
                    else:
                        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                        for datos in datos_validos:
                            cursor.execute("""
                                INSERT INTO registros_entrenamiento (fecha, alumno, nombre_rutina, ejercicio, kilos, rpe, notas) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (fecha_actual, nombre_atleta, nombre_de_la_rutina, datos["ejercicio"], datos["kilos"], datos["rpe"], datos["notes"]))
                        conn.commit()
                        st.success("🚀 ¡Sesión registrada con éxito!")
                        st.rerun()

# ==========================================
# 🚀 FLUJO DE PANTALLAS SEGÚN EL ROL
# ==========================================

# --- ROL ATLETA ---
if st.session_state["rol_actual"] == "atleta":
    alumno_logueado = st.session_state["usuario_actual"]
    st.markdown(f"### 👋 ¡Hola, **{alumno_logueado}**!")
    
    tab_entrenar, tab_progreso = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Historial"])
    with tab_entrenar:
        renderizar_tabla_entrenamiento(alumno_logueado, es_espejo=False)
        
    with tab_progreso:
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            st.markdown("### 📈 Historial de Cargas")
            df_hist_atleta = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, kilos, rpe, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id ASC", conn, params=(alumno_logueado,))
            if df_hist_atleta.empty:
                st.info("Aún no tenés registros.")
            else:
                ejercicios_registrados = df_hist_atleta["ejercicio"].unique()
                ej_grafico = st.selectbox("Ejercicio:", ejercicios_registrados, key="atleta_ej_select")
                df_filtrado = df_hist_atleta[df_hist_atleta["ejercicio"] == ej_grafico]
                st.line_chart(data=df_filtrado, x="fecha", y="kilos", color="#CCFF00")
                st.dataframe(df_filtrado.sort_values(by="fecha", ascending=False).rename(columns={"nombre_rutina": "Rutina", "fecha": "Fecha", "ejercicio": "Ejercicio", "kilos": "Kilos", "rpe": "RPE", "notes": "Notas"}), use_container_width=True, hide_index=True)
        with col_p2:
            st.markdown("### 🔐 Seguridad")
            with st.form("form_cambio_pass"):
                nueva_pass = st.text_input("Nueva Contraseña:", type="password")
                confirmar_pass = st.text_input("Confirmar Contraseña:", type="password")
                btn_cambio = st.form_submit_button("Actualizar 🔄", use_container_width=True)
            if btn_cambio:
                if nueva_pass == "": st.error("❌ No puede estar vacío.")
                elif nueva_pass != confirmar_pass: st.error("❌ No coinciden.")
                else:
                    cursor.execute("UPDATE alumnos SET contrasena = ? WHERE nombre_apellido = ?", (hashear_password(nueva_pass), alumno_logueado))
                    conn.commit()
                    st.success("🎉 ¡Actualizada!")

# --- ROL ADMINISTRADOR (PROFE) ---
elif st.session_state["rol_actual"] == "admin":
    tab_dashboard, tab_rutinas, tab_espejo, tab_fichas, tab_alta, tab_excel = st.tabs([
        "📊 Historial", "📝 Diseñar", "👀 Vista Celu", "📋 Fichas", "👥 Registrar", "📚 Biblioteca"
    ])
    
    with tab_dashboard:
        st.markdown("### 🔍 Monitor de Sesiones")
        if not lista_alumnos: st.info("No hay alumnos.")
        else:
            alumno_a_revisar = st.selectbox("👤 Seleccionar Atleta:", lista_alumnos)
            df_total_alumno = pd.read_sql_query("SELECT fecha, nombre_rutina, ejercicio, kilos, rpe, notas FROM registros_entrenamiento WHERE alumno = ? ORDER BY id DESC", conn, params=(alumno_a_revisar,))
            if df_total_alumno.empty: st.warning(f"Sin entrenamientos guardados.")
            else:
                sesiones_unicas = df_total_alumno["fecha"].unique()
                for fecha_sesion in sesiones_unicas:
                    df_sesion_especifica = df_total_alumno[df_total_alumno["fecha"] == fecha_sesion]
                    r_name = df_sesion_especifica.iloc[0]["nombre_rutina"] or "Rutina General"
                    with st.expander(f"🏋️‍♂️ {r_name} — {fecha_sesion}"):
                        st.dataframe(df_sesion_especifica[["ejercicio", "kilos", "rpe", "notas"]].rename(columns={"ejercicio": "Ejercicio", "kilos": "Kilos", "rpe": "RPE", "notas": "Notas"}), use_container_width=True, hide_index=True)
                        if st.button("🗑️ Eliminar Sesión", key=f"del_{fecha_sesion.replace(' ', '_').replace(':', '_')}"):
                            cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno = ? AND fecha = ?", (alumno_a_revisar, fecha_sesion))
                            conn.commit()
                            st.success(f"❌ Eliminada.")
                            st.rerun()

    with tab_rutinas:
        st.markdown("### 📝 Diseñar Planificación")
        if not lista_alumnos: st.warning("No hay atletas registrados.")
        else:
            alumno_rutina = st.selectbox("Planificar para:", lista_alumnos, key="planif_select")
            cursor.execute("SELECT nombre_rutina FROM rutinas_asignadas WHERE alumno = ? LIMIT 1", (alumno_rutina,))
            rutina_existente = cursor.fetchone()
            valor_sugerido_nombre = rutina_existente[0] if (rutina_existente and rutina_existente[0]) else "Rutina: Julio"
            nombre_de_la_rutina = st.text_input("🏷️ Nombre de la Planificación:", value=valor_sugerido_nombre)
            
            cursor.execute("SELECT nombre FROM biblioteca_ejercicios ORDER BY nombre ASC")
            ejercicios_db = [fila[0] for fila in cursor.fetchall()]
            
            if not ejercicios_db:
                ejercicio_rutina = st.text_input("Escribí el Ejercicio manual:")
            else:
                ejercicio_rutina = st.selectbox("Seleccionar Ejercicio:", ejercicios_db)
                
            bloque_seleccionado = st.selectbox("Asignar al Bloque:", BLOQUES)
            col_r1, col_r2 = st.columns(2)
            with col_r1: series_obj = st.number_input("Series:", min_value=1, max_value=10, value=4)
            with col_r2: reps_obj = st.text_input("Repeticiones:", value="5")
                
            if st.button("🚀 Inyectar Ejercicio", use_container_width=True):
                if ejercicio_rutina == "": st.error("Completá el ejercicio.")
                else:
                    cursor.execute("""
                        INSERT INTO rutinas_asignadas (alumno, nombre_rutina, ejercicio, bloque, series_objetivo, reps_objetivo, fecha_asignacion) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (alumno_rutina, nombre_de_la_rutina.strip(), ejercicio_rutina, bloque_seleccionado, series_obj, reps_obj, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success(f"💪 ¡Inyectado!")
                    st.rerun()
                    
            st.divider()
            cursor.execute("SELECT id, ejercicio, bloque, series_objetivo, reps_objetivo, nombre_rutina FROM rutinas_asignadas WHERE alumno = ?", (alumno_rutina,))
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

    with tab_espejo:
        st.markdown("### 📱 Simulador Móvil")
        if not lista_alumnos: st.info("No hay alumnos.")
        else:
            alumno_espejo = st.selectbox("Ver celular de:", lista_alumnos, key="select_espejo")
            st.divider()
            renderizar_tabla_entrenamiento(alumno_espejo, es_espejo=True)

    with tab_fichas:
        st.markdown("### 📋 Fichas Clínicas")
        df_base_alumnos = pd.read_sql_query("SELECT nombre_apellido, usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos ORDER BY nombre_apellido ASC", conn)
        if df_base_alumnos.empty: st.info("No hay alumnos.")
        else:
            mes_actual_str = datetime.now().strftime("%Y-%m-%d")[:7]
            cursor.execute("SELECT alumno, COUNT(DISTINCT SUBSTR(fecha, 1, 10)) FROM registros_entrenamiento WHERE fecha LIKE ? GROUP BY alumno", (f"{mes_actual_str}%",))
            sesiones_por_alumno = dict(cursor.fetchall())
            cursor.execute("SELECT alumno, MIN(fecha) FROM registros_entrenamiento GROUP BY alumno")
            primeras_sesiones = dict(cursor.fetchall())
            
            df_base_alumnos["Sesiones Este Mes"] = df_base_alumnos["nombre_apellido"].map(sesiones_por_alumno).fillna(0).astype(int)
            df_base_alumnos["Fecha de Inicio"] = df_base_alumnos["nombre_apellido"].map(primeras_sesiones).fillna("Pendiente")
            df_base_alumnos["Edad"] = df_base_alumnos["fecha_nacimiento"].apply(calcular_edad)
            
            st.dataframe(df_base_alumnos.rename(columns={"nombre_apellido": "Nombre", "usuario": "Usuario", "peso": "Peso", "altura": "Altura", "deporte": "Deporte"}), use_container_width=True, hide_index=True)
            
            st.divider()
            alumno_editar = st.selectbox("👤 Editar atleta:", lista_alumnos, key="select_editor_atleta")
            if alumno_editar:
                cursor.execute("SELECT usuario, fecha_nacimiento, peso, altura, deporte, objetivo FROM alumnos WHERE nombre_apellido = ?", (alumno_editar,))
                datos_al = cursor.fetchone()
                if datos_al:
                    try: fecha_nac_default = datetime.strptime(datos_al[1], "%Y-%m-%d").date()
                    except: fecha_nac_default = date(2000, 1, 1)

                    with st.form("form_edicion_alumno"):
                        ed_user = st.text_input("Usuario Acceso:", value=datos_al[0]).strip().lower()
                        ed_deporte = st.text_input("Deporte:", value=datos_al[4])
                        ed_nacimiento = st.date_input("Nacimiento:", value=fecha_nac_default)
                        ed_peso = st.number_input("Peso (kg):", value=float(datos_al[2]))
                        ed_altura = st.number_input("Altura (m):", value=float(datos_al[3]))
                        ed_objetivo = st.text_area("Objetivo:", value=datos_al[5])
                        
                        c_ed1, c_ed2 = st.columns(2)
                        with c_ed1: btn_guardar_edicion = st.form_submit_button("💾 Guardar")
                        with c_ed2: btn_eliminar_alumno = st.form_submit_button("🗑️ ELIMINAR", type="primary")
                    
                    if btn_guardar_edicion:
                        cursor.execute("UPDATE alumnos SET usuario=?, fecha_nacimiento=?, peso=?, altura=?, deporte=?, objetivo=? WHERE nombre_apellido=?", (ed_user, ed_nacimiento.strftime("%Y-%m-%d"), ed_peso, ed_altura, ed_deporte, ed_objetivo, alumno_editar))
                        conn.commit()
                        st.success("Ficha actualizada.")
                        st.rerun()
                    if btn_eliminar_alumno:
                        cursor.execute("DELETE FROM alumnos WHERE nombre_apellido=?", (alumno_editar,))
                        cursor.execute("DELETE FROM rutinas_asignadas WHERE alumno=?", (alumno_editar,))
                        cursor.execute("DELETE FROM registros_entrenamiento WHERE alumno=?", (alumno_editar,))
                        conn.commit()
                        st.rerun()

    with tab_alta:
        st.markdown("### 👤 Registrar Nuevo Alumno")
        if "mensaje_exito_alta" in st.session_state:
            st.success(st.session_state["mensaje_exito_alta"])
            del st.session_state["mensaje_exito_alta"]
            
        with st.form("alta_alumno", clear_on_submit=True):
            nombre_ap = st.text_input("Nombre y Apellido:")
            user_atleta = st.text_input("Nombre de Usuario:").strip().lower()
            pass_atleta = st.text_input("Contraseña:", type="password")
            nacimiento_f = st.date_input("Fecha de Nacimiento:", value=date(2000, 1, 1))
            peso_f = st.number_input("Peso (kg):", value=70.0)
            altura_f = st.number_input("Altura (m):", value=1.75)
            deporte = st.text_input("Especialidad Deportiva:")
            objetivo = st.text_area("Foco / Objetivo:")
            btn_alta = st.form_submit_button("Crear Cuenta 👤")
            
        if btn_alta:
            if nombre_ap.strip() == "" or user_atleta.strip() == "": st.error("Campos obligatorios vacíos.")
            else:
                try:
                    cursor.execute("INSERT INTO alumnos (nombre_apellido, usuario, contrasena, fecha_nacimiento, peso, altura, deporte, objetivo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (nombre_ap.strip(), user_atleta, hashear_password(pass_atleta), nacimiento_f.strftime("%Y-%m-%d"), peso_f, altura_f, deporte, objetivo))
                    conn.commit()
                    st.session_state["mensaje_exito_alta"] = "🎉 ¡Alumno creado con éxito!"
                    st.rerun()
                except sqlite3.IntegrityError: st.error("El usuario ya existe.")

    with tab_excel:
        st.markdown("### 📚 Importar Biblioteca (.xlsx / .csv)")
        archivo_subido = st.file_uploader("Arrastrá tu archivo", type=["xlsx", "csv"])
        if archivo_subido is not None:
            try:
                df_ejercicios = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido)
                df_ejercicios.columns = df_ejercicios.columns.astype(str).str.strip()
                st.dataframe(df_ejercicios.head(), use_container_width=True)
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
                    st.success("¡Base importada!")
                    st.rerun()
            except Exception as e: st.error(f"Error: {e}")
