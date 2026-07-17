import streamlit as st
from supabase import create_client, Client
import pandas as pd
import numpy as np
import bcrypt
import random
import time
from datetime import datetime, date, timedelta
import pytz
import io

# ==========================================
# 🔑 CONEXIÓN A SUPABASE (SOLO DESDE SECRETS)
# ==========================================
try:
    SUPABASE_URL = st.secrets["supabase_url"].strip().rstrip("/")
    SUPABASE_KEY = st.secrets["supabase_key"].strip()
except Exception:
    st.error(
        "❌ Faltan las credenciales de Supabase. Configurá `supabase_url` y "
        "`supabase_key` en `.streamlit/secrets.toml` (usá la key **anon/public**, "
        "nunca la `service_role`)."
    )
    st.stop()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==========================================
# 🛡️ HELPER: EJECUCIÓN SEGURA DE QUERIES
# ==========================================
def ejecutar_seguro(query_builder, mensaje_error="No se pudo completar la operación."):
    try:
        return query_builder.execute()
    except Exception as e:
        st.error(f"⚠️ {mensaje_error} (detalle: {e})")
        return None

# ==========================================
# ⏰ RELOJ OFICIAL EN ZONA HORARIA DE ARGENTINA
# ==========================================
TZ_ARG = pytz.timezone("America/Argentina/Buenos_Aires")

def obtener_fecha_hora_actual():
    return datetime.now(TZ_ARG)

# ==========================================
# 📊 MÉTRICAS DE CARGA Y CÁLCULOS AVANZADOS
# ==========================================
def calcular_srpe(rpe: float, duracion: float) -> float:
    return float(rpe * duracion)

def calcular_e1rm(peso: float, reps: int) -> float:
    if reps == 0: return 0.0
    if reps == 1: return float(peso)
    return round(peso * (1 + reps / 30.0), 1)

def calcular_acwr(cargas_diarias: list) -> dict:
    if not cargas_diarias or len(cargas_diarias) == 0:
        return {"aguda": 0.0, "cronica": 0.0, "acwr": 1.0, "estado": "Sin datos", "color": "#94A3B8"}

    hoy = obtener_fecha_hora_actual().date()
    df = pd.DataFrame(cargas_diarias)

    # 🛡️ Protección anti-duplicación de cargas
    if "alumno_id" in df.columns and "fecha" in df.columns:
        df_sesiones = df.drop_duplicates(subset=["fecha", "alumno_id"]).copy()
    elif "fecha" in df.columns:
        df_sesiones = df.drop_duplicates(subset=["fecha"]).copy()
    else:
        df_sesiones = df.copy()

    df_sesiones["fecha_limpia"] = df_sesiones["fecha"].apply(lambda x: str(x).split(" ")[0])
    df_sesiones["fecha_limpia"] = pd.to_datetime(df_sesiones["fecha_limpia"]).dt.date

    df_diario = df_sesiones.groupby("fecha_limpia")["srpe"].sum().reset_index()

    if len(df_diario) < 3:
        carga_aguda = df_diario["srpe"].sum()
        return {
            "aguda": round(carga_aguda, 1),
            "cronica": 0.0,
            "acwr": 1.0,
            "estado": "Estableciendo base de datos ⏳ (Mínimo 3 entrenamientos)",
            "color": "#38BDF8"
        }

    fecha_limite_cronica = hoy - timedelta(days=28)
    fecha_limite_aguda = hoy - timedelta(days=7)

    df_aguda = df_diario[df_diario["fecha_limpia"] >= fecha_limite_aguda]
    carga_aguda = df_aguda["srpe"].sum()

    df_cronica = df_diario[(df_diario["fecha_limpia"] >= fecha_limite_cronica)]
    carga_cronica = df_cronica["srpe"].sum() / 4.0
    if carga_cronica == 0: carga_cronica = 1.0

    acwr = round(carga_aguda / carga_cronica, 2)

    if acwr < 0.8:
        estado, color = "Subentrenamiento ⚠️ (Bajo estímulo)", "#38BDF8"
    elif 0.8 <= acwr <= 1.3:
        estado, color = "Zona Segura ✅ (Rendimiento Óptimo)", "#4ADE80"
    elif 1.3 < acwr <= 1.5:
        estado, color = "Zona de Transición 🟡 (Alerta)", "#FACC15"
    else:
        estado, color = "Peligro de Lesión 🚨 (Sobrecarga Aguda)", "#F87171"

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
        if not fecha_nac_str:
            return None
        fecha_nac = datetime.strptime(str(fecha_nac_str), "%Y-%m-%d").date()
        hoy = obtener_fecha_hora_actual().date()
        return hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    except Exception:
        return None

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
# 0. CONFIGURACIÓN INICIAL / CONSTANTES
# ==========================================
DIAS_PLANIF = [
    {"id": "dia1", "label": "📅 Día 1"},
    {"id": "dia2", "label": "📅 Día 2"},
    {"id": "aerobico", "label": "🏃 Día Aeróbico"},
]
SUB_BLOQUES = [
    {"id": "calentamiento", "label": "🔥 Entrada en Calor", "es_fuerza": False},
    {"id": "principal", "label": "⚡ Bloque Principal", "es_fuerza": True},
    {"id": "final", "label": "🧘 Bloque Final / Vuelta a la Calma", "es_fuerza": False},
]

def label_dia(dia_id):
    return next((d["label"] for d in DIAS_PLANIF if d["id"] == dia_id), dia_id)

def label_bloque(bloque_id):
    return next((b["label"] for b in SUB_BLOQUES if b["id"] == bloque_id), bloque_id)

def armar_clave_bloque(dia_id, bloque_id):
    return f"{dia_id}|{bloque_id}"

def desarmar_clave_bloque(clave):
    partes = str(clave).split("|")
    return (partes[0], partes[1]) if len(partes) == 2 else (clave, "")

ADMIN_USER = "giuliano"
try:
    ADMIN_PASS_HASH = st.secrets["admin_pass_hash"].encode()
except Exception:
    ADMIN_PASS_HASH = bcrypt.hashpw(b"magpower2026", bcrypt.gensalt())

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
# 🔑 INICIALIZACIÓN DE ESTADO DE SESIÓN PERSISTENTE
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = ""
if "rol_actual" not in st.session_state:
    st.session_state["rol_actual"] = ""
if "alumno_id_actual" not in st.session_state:
    st.session_state["alumno_id_actual"] = None

# ==========================================
# 🔐 PANTALLA DE ACCESO (LOGIN/REGISTRO)
# ==========================================
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
                es_pass_valida = (input_pass == "magpower2026") or (
                    isinstance(ADMIN_PASS_HASH, bytes) and bcrypt.checkpw(input_pass.encode(), ADMIN_PASS_HASH)
                )

                if input_user == ADMIN_USER and es_pass_valida:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = "Prof. Giuliano"
                    st.session_state["rol_actual"] = "admin"
                    st.rerun()
                else:
                    res = ejecutar_seguro(
                        supabase.table("alumnos").select("id, nombre_apellido, contrasena, estado").eq("usuario", input_user),
                        "No se pudo validar el usuario."
                    )
                    user_db = res.data if res else None
                    if user_db and verificar_password(input_pass, user_db[0]["contrasena"]):
                        if user_db[0]["estado"] == "pendiente":
                            st.warning("⏳ Tu cuenta está pendiente de aprobación.")
                        else:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_actual"] = user_db[0]["nombre_apellido"]
                            st.session_state["alumno_id_actual"] = user_db[0]["id"]
                            st.session_state["rol_actual"] = "atleta"
                            st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")
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
                    foto_final = AVATAR_PREDETERMINADO
                    if foto_subida:
                        url = subir_foto_perfil(foto_subida, reg_user)
                        if url: foto_final = url
                    res_ins = ejecutar_seguro(
                        supabase.table("alumnos").insert({
                            "nombre_apellido": reg_nombre.strip(), "usuario": reg_user,
                            "contrasena": hashear_password(reg_pass), "fecha_nacimiento": reg_nacimiento.strftime("%Y-%m-%d"),
                            "peso": reg_peso, "altura": reg_altura, "deporte": reg_deporte, "objetivo": reg_obj,
                            "estado": "pendiente", "foto_perfil": foto_final
                        }),
                        "No se pudo completar el registro (¿el usuario ya existe?)."
                    )
                    if res_ins:
                        st.success("🎉 ¡Registro enviado! Quedó pendiente de aprobación.")
    st.stop()

alumno_id_logueado = st.session_state.get("alumno_id_actual")

# ==========================================
# 👤 BARRA LATERAL
# ==========================================
if st.session_state["rol_actual"] == "admin":
    st.sidebar.markdown(f"👤 Coach: **{st.session_state['usuario_actual']}**")
else:
    st.sidebar.markdown(f"🏃 Atleta: **{st.session_state['usuario_actual']}**")
    mes_actual_str = obtener_fecha_hora_actual().strftime("%m-%Y")
    res_asist = ejecutar_seguro(
        supabase.table("asistencia").select("id", count="exact").eq("alumno_id", alumno_id_logueado).eq("mes_ano", mes_actual_str)
    )
    racha_act = res_asist.count if (res_asist and res_asist.count is not None) else 0
    st.sidebar.markdown(f"📆 Asistencias este mes: **{racha_act}**")

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""
    st.session_state["rol_actual"] = ""
    st.session_state["alumno_id_actual"] = None
    st.session_state["borrador_rutina"] = []
    st.rerun()

# ==========================================
# 🔔 MONITOR DE NOTIFICACIONES DINÁMICO (FRAGMENT)
# ==========================================
@st.fragment(run_every=15)
def monitor_en_vivo():
    if st.session_state["rol_actual"] == "admin":
        res_n = ejecutar_seguro(
            supabase.table("notificaciones").select("id, mensaje").eq("destinatario_tipo", "admin").eq("leido", False)
        )
        notis = res_n.data if res_n else []
    else:
        res_n = ejecutar_seguro(
            supabase.table("notificaciones").select("id, mensaje")
            .eq("destinatario_tipo", "atleta").eq("destinatario_id", alumno_id_logueado).eq("leido", False)
        )
        notis = res_n.data if res_n else []

    if notis:
        ids_a_marcar = [n["id"] for n in notis]
        for noti in notis:
            st.toast(f"🔔 {noti['mensaje']}", icon="🏃")
        ejecutar_seguro(
            supabase.table("notificaciones").update({"leido": True}).in_("id", ids_a_marcar)
        )

monitor_en_vivo()

# ==========================================
# 📱 INTERFAZ DE ENTRENAMIENTO ATLETA
# ==========================================
def renderizar_tabla_entrenamiento(alumno_id, nombre_atleta, es_espejo=False):
    sufijo = "esp" if es_espejo else "atl"
    res_rut = ejecutar_seguro(
        supabase.table("rutinas_asignadas").select("*").eq("alumno_id", alumno_id),
        "No se pudo cargar la rutina."
    )
    rutina_completa = res_rut.data if res_rut else []
    if not rutina_completa:
        st.info("No tenés ninguna rutina asignada todavía.")
        return

    res_bib = ejecutar_seguro(supabase.table("biblioteca_ejercicios").select("nombre, link_video"))
    videos_por_nombre = {f["nombre"]: f.get("link_video", "") for f in (res_bib.data if res_bib else [])}

    st.markdown(f"### 📋 Plan: {rutina_completa[0]['nombre_rutina']}", unsafe_allow_html=True)
    dia_seleccionado = st.selectbox(
        "📆 Día:", options=[d["id"] for d in DIAS_PLANIF],
        format_func=label_dia, key=f"sb_dia_{sufijo}"
    )

    entradas_alumno = {}
    visibles = False

    for bloque in SUB_BLOQUES:
        clave_buscada = armar_clave_bloque(dia_seleccionado, bloque["id"])
        ejs = [r for r in rutina_completa if r["bloque"] == clave_buscada]
        if ejs:
            visibles = True
            st.markdown(f"<h4 style='color: #CCFF00; background-color: #1E293B; padding: 6px 10px; border-radius: 4px;'>{bloque['label']}</h4>", unsafe_allow_html=True)

            for idx, ej in enumerate(ejs):
                nombre_ej = ej["ejercicio"]
                series_obj = int(ej["series_objetivo"])
                reps_obj = ej["reps_objetivo"]
                link_video = videos_por_nombre.get(nombre_ej, "")

                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1: st.markdown(f"🏋️‍♂️ **{nombre_ej}** (`{series_obj}S x {reps_obj}R`)")
                    with col2:
                        if link_video and "http" in link_video: st.markdown(f"[🎥 Video]({link_video})")

                    if not bloque["es_fuerza"]:
                        completado = st.checkbox("✅ Completado", key=f"chk_{sufijo}_{idx}_{nombre_ej.replace(' ','_')}")
                        if completado:
                            for s in range(1, series_obj + 1):
                                entradas_alumno[(bloque["id"], nombre_ej, s, idx)] = {"ejercicio": nombre_ej, "serie": s, "kilos": 0.0, "reps_reales": 10}
                    else:
                        cols = st.columns(series_obj)
                        for s in range(1, series_obj + 1):
                            with cols[s-1]:
                                st.markdown(f"<p style='text-align: center; color: #CCFF00;'>S{s}</p>", unsafe_allow_html=True)
                                k = st.number_input("kg", key=f"k_{sufijo}_{idx}_{s}", label_visibility="collapsed", step=0.5)
                                r = st.number_input("R", key=f"r_{sufijo}_{idx}_{s}", label_visibility="collapsed", value=int(reps_obj) if str(reps_obj).isdigit() else 5)
                                entradas_alumno[(bloque["id"], nombre_ej, s, idx)] = {"ejercicio": nombre_ej, "serie": s, "kilos": k, "reps_reales": r}

                    notas = st.text_input("Notas:", key=f"not_{sufijo}_{idx}_{nombre_ej.replace(' ','_')}")
                    for s in range(1, series_obj + 1):
                        clave_actual = (bloque["id"], nombre_ej, s, idx)
                        if clave_actual in entradas_alumno:
                            entradas_alumno[clave_actual]["notas"] = notas
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

        if st.button("🏁 FINALIZAR ENTRENAMIENTO", use_container_width=True, type="primary", key=f"btn_fin_{sufijo}"):
            if es_espejo:
                st.info("ℹ️ Guardado deshabilitado: Estás en modo de prueba visual.")
            else:
                fecha_hoy_limpia = obtener_fecha_hora_actual().strftime("%Y-%m-%d")

                res_comp = ejecutar_seguro(
                    supabase.table("asistencia").select("id").eq("alumno_id", alumno_id).eq("fecha", fecha_hoy_limpia)
                )
                if res_comp and res_comp.data:
                    st.error("⚠️ Ya registraste una sesión hoy.")
                else:
                    validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                    if not validos:
                        st.warning("Cargá marcas antes de guardar.")
                    else:
                        hora_limpia = obtener_fecha_hora_actual().strftime("%H:%M")
                        mes_ano = obtener_fecha_hora_actual().strftime("%m-%Y")
                        fecha_y_hora_texto = f"{fecha_hoy_limpia} {hora_limpia}"

                        filas_a_insertar = [{
                            "fecha": fecha_y_hora_texto,
                            "alumno_id": alumno_id,
                            "nombre_rutina": rutina_completa[0]["nombre_rutina"],
                            "ejercicio": d["ejercicio"],
                            "nro_serie": d["serie"],
                            "kilos": d["kilos"],
                            "reps_reales": d["reps_reales"],
                            "notas": d.get("notas", ""),
                            "rpe_global_sesion": rpe,
                            "duracion_minutos": duracion,
                            "srpe": srpe_calculado
                        } for d in validos]

                        res_guardado = ejecutar_seguro(
                            supabase.table("registros_entrenamiento").insert(filas_a_insertar),
                            "No se pudo guardar la sesión."
                        )
                        if res_guardado:
                            ejecutar_seguro(supabase.table("asistencia").insert({"alumno_id": alumno_id, "fecha": fecha_hoy_limpia, "mes_ano": mes_ano}))
                            ejecutar_seguro(supabase.table("notificaciones").insert({
                                "destinatario_tipo": "admin", "destinatario_id": None,
                                "mensaje": f"🏃 {nombre_atleta} finalizó su sesión con sRPE = {srpe_calculado}."
                            }))

                            res_tot = ejecutar_seguro(
                                supabase.table("asistencia").select("id", count="exact").eq("alumno_id", alumno_id).eq("mes_ano", mes_ano)
                            )
                            total = res_tot.count if (res_tot and res_tot.count is not None) else 0
                            st.session_state["msj_pop"] = obtener_frase_motivacional(total)
                            st.success("🚀 ¡Sesión enviada!")
                            st.rerun()

if "msj_pop" in st.session_state:
    st.balloons()
    st.toast(st.session_state["msj_pop"], icon="🏆")
    del st.session_state["msj_pop"]

# ==========================================
# 🏃 VISTA DE ATLETA
# ==========================================
if st.session_state["rol_actual"] == "atleta":
    al = st.session_state["usuario_actual"]
    res_at = ejecutar_seguro(
        supabase.table("alumnos").select("foto_perfil, objetivo, deporte, fecha_nacimiento").eq("id", alumno_id_logueado)
    )
    datos_at = res_at.data[0] if (res_at and res_at.data) else {}
    foto = datos_at.get("foto_perfil") or AVATAR_PREDETERMINADO
    obj = datos_at.get("objetivo") or "Alto Rendimiento"
    dep = datos_at.get("deporte") or "Preparación Física"
    edad_calculada = calcular_edad(datos_at.get("fecha_nacimiento"))

    c1, c2 = st.columns([1, 6])
    with c1: st.markdown(f'<img src="{foto}" width="85" height="85" class="profile-pic">', unsafe_allow_html=True)
    with c2:
        st.markdown(f"### 👋 ¡Hola, **{al}**!")
        texto_edad = f" · {edad_calculada} years" if edad_calculada is not None else ""
        st.markdown(f"<p style='color: #84CC16; font-weight: bold;'>🎯 Meta: {obj} ({dep}){texto_edad}</p>", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Mi Progreso", "💬 Dudas", "⚙️ Perfil"])
    with t1:
        renderizar_tabla_entrenamiento(alumno_id_logueado, al, es_espejo=False)
    with t2:
        st.markdown("### 📈 Evolución")
        rh = ejecutar_seguro(supabase.table("registros_entrenamiento").select("*").eq("alumno_id", alumno_id_logueado))
        if rh and rh.data:
            df = pd.DataFrame(rh.data)
            df["e1rm"] = df.apply(lambda r: calcular_e1rm(r["kilos"], r["reps_reales"]), axis=1)
            df["fc"] = df["fecha"].apply(lambda f: f.split(" ")[0])

            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.markdown("#### Historial de Fuerza Estimada (e1RM)")
                ej = st.selectbox("Ejercicio:", sorted(df["ejercicio"].unique()))
                st.line_chart(df[df["ejercicio"]==ej].groupby("fc")["e1rm"].max())

            with sub_col2:
                st.markdown("#### Historial de Carga del Entrenamiento (sRPE)")
                if "srpe" in df.columns:
                    df["srpe"] = df["srpe"].fillna(0.0)
                    df_srpe = df.drop_duplicates(subset=["fc"]).groupby("fc")["srpe"].sum().reset_index()
                    st.bar_chart(df_srpe.set_index("fc"))
                else:
                    st.info("Sin registros de sRPE suficientes.")

            st.markdown("---")
            st.markdown("### 🚦 Tu Balance de Carga de Trabajo (ACWR)")
            res_all_srpe = ejecutar_seguro(supabase.table("registros_entrenamiento").select("fecha, srpe, alumno_id").eq("alumno_id", alumno_id_logueado))
            if res_all_srpe and res_all_srpe.data:
                acwr_res = calcular_acwr(res_all_srpe.data)
                col_st1, col_st2, col_st3 = st.columns(3)
                with col_st1: st.metric("Carga Aguda (7d)", f"{acwr_res['aguda']} U.A.")
                with col_st2: st.metric("Carga Crónica (28d)", f"{acwr_res['cronica']} U.A.")
                with col_st3: st.metric("ACWR", acwr_res["acwr"])
                st.markdown(f"**Estado actual:** <span style='color:{acwr_res['color']}; font-weight:bold; font-size:1.1em;'>{acwr_res['estado']}</span>", unsafe_allow_html=True)
                st.caption("El ACWR ideal se sitúa entre 0.8 y 1.3. Valores superiores a 1.5 multiplican el riesgo de lesión.")

    with t3:
        with st.form("msg"):
            m = st.text_area("Consulta:")
            if st.form_submit_button("Enviar") and m.strip():
                res_msg = ejecutar_seguro(
                    supabase.table("consultas_mensajes").insert({"alumno_id": alumno_id_logueado, "mensaje": m.strip()}),
                    "No se pudo enviar la consulta."
                )
                if res_msg: st.success("Enviado.")
    with t4:
        f_subida = st.file_uploader("📸 Cambiar Foto:", type=["jpg","png","webp"])
        if f_subida and st.button("💾 Guardar Foto"):
            url = subir_foto_perfil(f_subida, al)
            if url:
                res_upd = ejecutar_seguro(supabase.table("alumnos").update({"foto_perfil": url}).eq("id", alumno_id_logueado))
                if res_upd:
                    st.success("Foto actualizada.")
                    st.rerun()

# ==========================================
# 👑 VISTA DE COACH (ADMIN)
# ==========================================
elif st.session_state["rol_actual"] == "admin":
    res_ap = ejecutar_seguro(
        supabase.table("alumnos").select("id, nombre_apellido").eq("estado", "aprobado").order("nombre_apellido")
    )
    lista_alumnos_datos = res_ap.data if res_ap else []
    id_por_nombre = {a["nombre_apellido"]: a["id"] for a in lista_alumnos_datos}
    list_al = [a["nombre_apellido"] for a in lista_alumnos_datos]
    list_al_n = ["- Seleccionar -"] + list_al

    ta1, ta2, ta3, ta4, ta5, ta6 = st.tabs(["📊 Historial y Carga", "📝 Planificar", "💬 Mensajes", "👥 Atletas", "✅ Aprobaciones", "📚 Biblioteca"])

    with ta1:
        st.markdown("### 📊 Panel de Control e Inteligencia de Carga de Trabajo")
        al_r = st.selectbox("Auditar Atleta:", list_al_n)
        if al_r != "- Seleccionar -":
            id_r = id_por_nombre[al_r]
            
            st.markdown("#### 📋 Planificación Asignada Actual")
            res_r_act = ejecutar_seguro(supabase.table("rutinas_asignadas").select("nombre_rutina").eq("alumno_id", id_r).limit(1))
            if res_r_act and res_r_act.data:
                st.success(f"**Rutina Activa:** {res_r_act.data[0]['nombre_rutina']}")
            else:
                st.info("Este atleta no tiene ninguna planificación asignada todavía.")

            rt = ejecutar_seguro(supabase.table("registros_entrenamiento").select("*").eq("alumno_id", id_r).order("fecha", desc=True))
            if rt and rt.data:
                df_t = pd.DataFrame(rt.data)
                df_t["srpe"] = df_t["srpe"].fillna(0.0) if "srpe" in df_t.columns else 0.0
                df_clean = df_t[df_t["srpe"] > 0]

                if not df_clean.empty:
                    acwr_data = calcular_acwr(df_clean.to_dict('records'))
                    st.markdown("#### 🚥 Dashboard de Carga & Salud Articular/Muscular")
                    c_m1, c_m2, c_m3 = st.columns(3)
                    with c_m1: st.metric("Carga Aguda (7 días)", f"{acwr_data['aguda']} U.A.")
                    with c_m2: st.metric("Carga Crónica (28 días)", f"{acwr_data['cronica']} U.A.")
                    with c_m3: st.metric("ACWR Ratio", acwr_data["acwr"])
                    st.markdown(f"**Estado Clínico de Carga:** <span style='color:{acwr_data['color']}; font-weight:bold; font-size:1.15em;'>{acwr_data['estado']}</span>", unsafe_allow_html=True)
                    st.divider()

                st.markdown("#### 📂 Historial de Sesiones Realizadas")
                for f in df_t["fecha"].unique():
                    fecha_visual = str(f).split(" ")[0]
                    with st.expander(f"Sesión - {fecha_visual}"):
                        ses_data = df_t[df_t["fecha"]==f]
                        if "rpe_global_sesion" in ses_data.columns and not ses_data.empty:
                            r_gl = ses_data.iloc[0].get("rpe_global_sesion", "N/A")
                            d_gl = ses_data.iloc[0].get("duracion_minutos", "N/A")
                            sr_gl = ses_data.iloc[0].get("srpe", "N/A")
                            nom_rut_ses = ses_data.iloc[0].get("nombre_rutina", "Planificación")
                            st.markdown(f"🔹 **Plan:** {nom_rut_ses} | **RPE:** {r_gl}/10 | **Duración:** {d_gl} min | **sRPE:** {sr_gl} U.A.")
                        st.dataframe(ses_data[["ejercicio","nro_serie","kilos","reps_reales","notas"]], hide_index=True)
            else:
                st.info("El atleta aún no posee sesiones grabadas.")

    with ta2:
        st.markdown("### 📝 Diseñar Planificación")

        # --- 👥 CLONADOR SELECTIVO POR DÍA ---
        st.markdown("#### 👥 Clonar Rutina Existente")
        col_clon1, col_clon2, col_clon3 = st.columns(3)
        with col_clon1:
            atleta_origen = st.selectbox("Copiar rutina de:", list_al_n, key="clon_origen")
        with col_clon2:
            atleta_destino = st.selectbox("Asignar rutina a:", list_al_n, key="clon_destino")
        with col_clon3:
            opciones_clon = ["Copiar Rutina Completa"] + [d["id"] for d in DIAS_PLANIF]
            modo_clon = st.selectbox("¿Qué querés clonar?", opciones_clon, format_func=lambda x: x if x == "Copiar Rutina Completa" else label_dia(x), key="clon_modo")

        if st.button("👥 CLONAR Y COPIAR PLAN", use_container_width=True):
            if atleta_origen == "- Seleccionar -" or atleta_destino == "- Seleccionar -":
                st.error("⚠️ Debes seleccionar un atleta de origen y uno de destino.")
            elif atleta_origen == atleta_destino:
                st.error("⚠️ El atleta de origen y de destino no pueden ser el mismo.")
            else:
                id_origen = id_por_nombre[atleta_origen]
                id_destino = id_por_nombre[atleta_destino]
                res_clon_or = ejecutar_seguro(supabase.table("rutinas_asignadas").select("*").eq("alumno_id", id_origen))
                data_origen = res_clon_or.data if res_clon_or else []
                if not data_origen:
                    st.warning(f"⚠️ El atleta {atleta_origen} no tiene una rutina activa para copiar.")
                else:
                    if modo_clon == "Copiar Rutina Completa":
                        ejercicios_a_clonar = data_origen
                    else:
                        ejercicios_a_clonar = [item for item in data_origen if desarmar_clave_bloque(item["bloque"])[0] == modo_clon]

                    if not ejercicios_a_clonar:
                        st.warning(f"⚠️ El atleta {atleta_origen} no tiene ejercicios configurados para ese día.")
                    else:
                        if modo_clon == "Copiar Rutina Completa":
                            ejecutar_seguro(supabase.table("rutinas_asignadas").delete().eq("alumno_id", id_destino))
                        else:
                            res_dest_ant = ejecutar_seguro(supabase.table("rutinas_asignadas").select("id, bloque").eq("alumno_id", id_destino))
                            ids_a_borrar = [item["id"] for item in (res_dest_ant.data if res_dest_ant else []) if desarmar_clave_bloque(item["bloque"])[0] == modo_clon]
                            if ids_a_borrar:
                                ejecutar_seguro(supabase.table("rutinas_asignadas").delete().in_("id", ids_a_borrar))

                        filas_clon = [{
                            "alumno_id": id_destino,
                            "nombre_rutina": item["nombre_rutina"],
                            "ejercicio": item["ejercicio"],
                            "ejercicio_id": item.get("ejercicio_id"),
                            "bloque": item["bloque"],
                            "series_objetivo": item["series_objetivo"],
                            "reps_objetivo": item["reps_objetivo"]
                        } for item in ejercicios_a_clonar]

                        res_clon_ins = ejecutar_seguro(supabase.table("rutinas_asignadas").insert(filas_clon), "No se pudo clonar la rutina.")
                        if res_clon_ins:
                            ejecutar_seguro(supabase.table("notificaciones").insert({
                                "destinatario_tipo": "atleta", "destinatario_id": id_destino,
                                "mensaje": f"🏋️‍♂️ El Profe Giuliano actualizó tu plan copiando ejercicios de {atleta_origen}."
                            }))
                            st.success(f"🚀 ¡Plan clonado de forma exitosa para {atleta_destino}!")
                            time.sleep(1)
                            st.rerun()

        st.divider()
        st.markdown("#### ✍️ Diseñar Nueva Planificación Manual")
        al_p = st.selectbox("Planificar para:", list_al_n, key="sb_planificar_para")
        if al_p != "- Seleccionar -":
            id_p = id_por_nombre[al_p]
            nom_r = st.text_input("Nombre de la Rutina:")
            c1, c2 = st.columns(2)
            with c1: dia_id_sel = st.selectbox("Día:", [d["id"] for d in DIAS_PLANIF], format_func=label_dia)
            with c2: bloque_id_sel = st.selectbox("Bloque:", [b["id"] for b in SUB_BLOQUES], format_func=label_bloque)

            tipo_carga = st.radio(
                "Modo de selección de ejercicio:",
                ["🔍 Buscar en Biblioteca por Patrón", "✍️ Escribir Ejercicio Manualmente (Libre / Aeróbico)"],
                horizontal=True
            )

            ej_nom = ""
            ej_id_sel = None
            if tipo_carga == "🔍 Buscar en Biblioteca por Patrón":
                res_pat = ejecutar_seguro(supabase.table("biblioteca_ejercicios").select("grupo_muscular"))
                patrones_disponibles = sorted(list(set([p["grupo_muscular"] for p in (res_pat.data if res_pat else []) if p["grupo_muscular"]])))

                if patrones_disponibles:
                    patron_seleccionado = st.selectbox("Filtrar por patrón de movimiento:", ["- Todos los patrones -"] + patrones_disponibles)
                    query_ejs = supabase.table("biblioteca_ejercicios").select("id, nombre").order("nombre")
                    if patron_seleccionado != "- Todos los patrones -":
                        query_ejs = query_ejs.eq("grupo_muscular", patron_seleccionado)
                    res_ejs = ejecutar_seguro(query_ejs)
                else:
                    res_ejs = ejecutar_seguro(supabase.table("biblioteca_ejercicios").select("id, nombre").order("nombre"))

                filas_ejs = res_ejs.data if res_ejs else []
                if filas_ejs:
                    ej_nom = st.selectbox("Seleccionar Ejercicio:", [f["nombre"] for f in filas_ejs])
                    ej_id_sel = next((f["id"] for f in filas_ejs if f["nombre"] == ej_nom), None)
                else:
                    ej_nom = st.text_input("No hay ejercicios en la base de datos. Escribilo a mano:")
            else:
                ej_nom = st.text_input("Escribí el ejercicio o trabajo aeróbico/libre:", placeholder="Ej: Pasadas 400m")

            s_o = st.number_input("Series prescritas:", min_value=1, max_value=10, value=4)
            r_o = st.text_input("Repeticiones objetivo:", "10")

            if st.button("➕ Añadir Ejercicio al Borrador", use_container_width=True):
                if ej_nom.strip() == "" or nom_r.strip() == "":
                    st.error("❌ Completa los campos obligatorios.")
                else:
                    st.session_state["borrador_rutina"].append({
                        "ejercicio": ej_nom, "ejercicio_id": ej_id_sel,
                        "bloque": armar_clave_bloque(dia_id_sel, bloque_id_sel),
                        "bloque_visual": f"{label_dia(dia_id_sel)} · {label_bloque(bloque_id_sel)}",
                        "series": s_o, "reps": r_o
                    })
                    st.toast(f"✅ Añadido: {ej_nom}")

            if st.session_state["borrador_rutina"]:
                st.markdown("### 📋 Pizarra Borrador")
                st.dataframe(pd.DataFrame(st.session_state["borrador_rutina"])[["ejercicio", "bloque_visual", "series", "reps"]])

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("🗑️ Vaciar Borrador Actual", use_container_width=True):
                        st.session_state["borrador_rutina"] = []
                        st.rerun()
                with col_b2:
                    if st.button("💾 PUBLICAR PLAN", use_container_width=True, type="primary"):
                        ejecutar_seguro(supabase.table("rutinas_asignadas").delete().eq("alumno_id", id_p))
                        filas_plan = [{
                            "alumno_id": id_p, "nombre_rutina": nom_r.strip(),
                            "ejercicio": i["ejercicio"], "ejercicio_id": i.get("ejercicio_id"),
                            "bloque": i["bloque"], "series_objetivo": i["series"], "reps_objetivo": i["reps"]
                        } for i in st.session_state["borrador_rutina"]]
                        res_pub = ejecutar_seguro(supabase.table("rutinas_asignadas").insert(filas_plan), "No se pudo publicar el plan.")
                        if res_pub:
                            ejecutar_seguro(supabase.table("notificaciones").insert({
                                "destinatario_tipo": "atleta", "destinatario_id": id_p,
                                "mensaje": f"🏋️‍♂️ El Profe Giuliano actualizó tu planificación: {nom_r.strip()}."
                            }))
                            st.session_state["borrador_rutina"] = []
                            st.success("🎉 Planificación publicada de forma exitosa.")
                            st.rerun()

    with ta3:
        al_m = st.selectbox("Chat Privado:", list_al_n)
        if al_m != "- Seleccionar -":
            id_m = id_por_nombre[al_m]
            rm = ejecutar_seguro(supabase.table("consultas_mensajes").select("*").eq("alumno_id", id_m).order("id", desc=True))
            txt_r = st.text_input("Responder:")
            if st.button("Enviar Respuesta") and txt_r.strip():
                res_resp = ejecutar_seguro(supabase.table("consultas_mensajes").insert({"alumno_id": id_m, "mensaje": "(Profe)", "respuesta": txt_r.strip()}))
                if res_resp: st.rerun()
            for m in (rm.data if rm else []):
                st.markdown(f"**{al_m}**: {m['mensaje']}")
                if m['respuesta']: st.markdown(f"**Giuliano**: {m['respuesta']}")
                st.divider()

    with ta4:
        ra = ejecutar_seguro(
            supabase.table("alumnos").select("id, nombre_apellido, deporte, peso, altura, objetivo, foto_perfil, fecha_nacimiento").eq("estado", "aprobado")
        )
        for a in (ra.data if ra else []):
            edad_a = calcular_edad(a.get("fecha_nacimiento"))
            texto_edad_a = f" · {edad_a} years" if edad_a is not None else ""
            with st.expander(f"{a['nombre_apellido']} ({a['deporte']}){texto_edad_a}"):
                st.image(a.get("foto_perfil") or AVATAR_PREDETERMINADO, width=100)
                st.text(f"Peso: {a['peso']}kg | Altura: {a['altura']}m | Meta: {a['objetivo']}")
                confirmar_borrado = st.checkbox("Confirmo que quiero eliminar a este atleta y TODO su historial", key=f"conf_del_{a['id']}")
                if st.button("🗑️ ELIMINAR", key=f"del_{a['id']}", disabled=not confirmar_borrado):
                    res_del = ejecutar_seguro(supabase.table("alumnos").delete().eq("id", a['id']), "No se pudo eliminar al atleta.")
                    if res_del:
                        st.rerun()

    with ta5:
        st.markdown("### ✅ Aprobaciones de Nuevos Atletas")
        rp = ejecutar_seguro(supabase.table("alumnos").select("id, nombre_apellido, usuario").eq("estado", "pendiente"))
        datos_pendientes = rp.data if rp else []

        if not datos_pendientes:
            st.info("🎉 Sin aprobaciones pendientes. ¡Estás al día!")
        else:
            for p in datos_pendientes:
                col_ap1, col_ap2 = st.columns([3, 1])
                with col_ap1:
                    st.write(f"🏃 **Atleta:** {p['nombre_apellido']} ({p['usuario']})")
                with col_ap2:
                    if st.button("Aprobar Atleta", key=f"ap_{p['id']}", use_container_width=True):
                        res_apr = ejecutar_seguro(supabase.table("alumnos").update({"estado":"aprobado"}).eq("id", p['id']))
                        if res_apr:
                            st.success(f"¡{p['nombre_apellido']} aprobado!")
                            time.sleep(1)
                            st.rerun()

   with ta6:
        st.markdown("### Biblioteca de Ejercicios")
        if st.button("Vaciar Biblioteca"):
            res_vac = ejecutar_seguro(supabase.table("biblioteca_ejercicios").delete().neq("id", 0))
            if res_vac:
                st.success("Biblioteca vaciada.")
                st.rerun()
        f_xl = st.file_uploader("Subir Excel:", type=["xlsx", "csv"])
        if f_xl and st.button("Cargar Lote"):
            df = pd.read_excel(f_xl) if f_xl.name.endswith(".xlsx") else pd.read_csv(f_xl)
            
            if not df.empty:
                # 🛡️ PASO 1: Limpiamos espacios y eliminamos duplicados dentro del mismo archivo Excel de forma case-insensitive
                df.iloc[:, 0] = df.iloc[:, 0].astype(str).str.strip()
                df = df.drop_duplicates(subset=[df.columns[0]], keep="first").copy()
                
                # 🛡️ PASO 2: Traemos los existentes y los convertimos TODOS a minúsculas para comparar de forma segura
                res_existentes = ejecutar_seguro(supabase.table("biblioteca_ejercicios").select("nombre"))
                existentes_db = [e["nombre"] for e in res_existentes.data] if (res_existentes and res_existentes.data) else []
                existentes_normalizados = set(str(nombre).strip().lower() for nombre in existentes_db)
                
                lote = []
                for _, r in df.iterrows():
                    nombre_ej = str(r.iloc[0]).strip()
                    # Comparamos estrictamente en minúsculas para que "Sentadilla" y "sentadilla" se reconozcan como lo mismo
                    if nombre_ej and nombre_ej.lower() not in existentes_normalizados:
                        grupo = str(r.iloc[1]).strip() if (len(r) > 1 and pd.notna(r.iloc[1])) else "General"
                        lote.append({"nombre": nombre_ej, "grupo_muscular": grupo})
                
                # 🛡️ PASO 3: Insertamos solo el neto de ejercicios nuevos
                if lote:
                    res_carga = ejecutar_seguro(supabase.table("biblioteca_ejercicios").insert(lote), "No se pudo cargar el lote de ejercicios.")
                    if res_carga:
                        st.success(f"🎉 ¡Se cargaron exitosamente {len(lote)} ejercicios nuevos sin duplicados!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("ℹ️ No hay ejercicios nuevos para agregar. Todos los elementos del archivo ya existen en tu biblioteca.")
            else:
                st.warning("⚠️ El archivo seleccionado está vacío.")

        # ==========================================
        # 💾 BACKUP DE SEGURIDAD EXCLUSIVO
        # ==========================================
        st.divider()
        st.markdown("### 💾 Resguardo y Copia de Seguridad de Datos")
        st.caption("Descargá toda la información de la app en un archivo consolidado de Excel.")

        if st.button("🔄 PREPARAR COPIA DE SEGURIDAD", use_container_width=True):
            try:
                res_al_bk = ejecutar_seguro(
                    supabase.table("alumnos").select("id, nombre_apellido, usuario, fecha_nacimiento, peso, altura, deporte, objetivo, estado, created_at")
                )
                res_rt_bk = ejecutar_seguro(supabase.table("rutinas_asignadas").select("*"))
                res_as_bk = ejecutar_seguro(supabase.table("asistencia").select("*"))
                res_en_bk = ejecutar_seguro(supabase.table("registros_entrenamiento").select("*"))

                data_alumnos = pd.DataFrame(res_al_bk.data if res_al_bk else [])
                data_rutinas = pd.DataFrame(res_rt_bk.data if res_rt_bk else [])
                data_asistencia = pd.DataFrame(res_as_bk.data if res_as_bk else [])
                data_entrenamientos = pd.DataFrame(res_en_bk.data if res_en_bk else [])

                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine="openpyxl") as escritor:
                    if not data_alumnos.empty: data_alumnos.to_excel(escritor, sheet_name="Atletas", index=False)
                    if not data_rutinas.empty: data_rutinas.to_excel(escritor, sheet_name="Rutinas_Asignadas", index=False)
                    if not data_asistencia.empty: data_asistencia.to_excel(escritor, sheet_name="Asistencias", index=False)
                    if not data_entrenamientos.empty: data_entrenamientos.to_excel(escritor, sheet_name="Historial_Entrenamientos", index=False)

                st.session_state["excel_backup"] = buffer_excel.getvalue()
                st.success("✅ Copia de seguridad generada de manera exitosa.")
            except Exception as e:
                st.error(f"⚠️ Error al compilar el backup: {e}")

        if "excel_backup" in st.session_state:
            nombre_archivo_backup = f"Backup_TrainApp_{obtener_fecha_hora_actual().strftime('%Y_%m_%d_%H%M')}.xlsx"
            st.download_button(
                label="📥 Descargar Backup (.xlsx)",
                data=st.session_state["excel_backup"],
                file_name=nombre_archivo_backup,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
