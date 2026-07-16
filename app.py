import streamlit as st
from supabase import create_client, Client
import pandas as pd
import bcrypt
import random
import time
from datetime import datetime, date
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
# ⏰ RELOJ OFICIAL EN ZONA HORARIA DE ARGENTINA
# ==========================================
TZ_ARG = pytz.timezone('America/Argentina/Buenos_Aires')

def obtener_fecha_hora_actual():
    """Retorna el objeto datetime localizado exactamente en Argentina."""
    return datetime.now(TZ_ARG)

# ==========================================
# 🔑 HELPERS DE SEGURIDAD Y CÁLCULOS
# ==========================================
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verificar_password(password_ingresada: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(password_ingresada.encode(), hash_guardado.encode())
    except (ValueError, AttributeError):
        return password_ingresada == hash_guardado

def calcular_e1rm(peso, reps):
    if reps == 0: return 0.0
    if reps == 1: return float(peso)
    return round(peso * (1 + reps / 30.0), 1)

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
# 📸 HELPER PARA STORAGE (SUBIR FOTO)
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
# 0. CONSTANTES Y CONFIGURACIÓN
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
            reg_user = st.text_input("Nombre de Usuario:").strip().lower()
            reg_pass = st.text_input("Contraseña:", type="password")
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
# 🔔 MONITOR EN VIVO (FRAGMENT)
# ==========================================
@st.fragment(run_every=15)
def monitor_en_vivo():
    if st.session_state["rol_actual"] == "admin":
        res_n = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", "giuliano").eq("leido", False).execute()
        if res_n.data:
            for noti in res_n.data:
                st.toast(f"🔔 {noti['mensaje']}", icon="🏃")
                supabase.table("notificaciones").update({"leido": True}).eq("id", noti["id"]).execute()
                time.sleep(0.5)
                st.rerun()
    elif st.session_state["rol_actual"] == "atleta":
        alumno_log = st.session_state["usuario_actual"]
        res_n_at = supabase.table("notificaciones").select("id, mensaje").eq("destinatario", alumno_log).eq("leido", False).execute()
        if res_n_at.data:
            for noti in res_n_at.data:
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
        st.markdown("#### 📊 Evaluación")
        rpe = st.select_slider("RPE Global:", options=list(range(1, 11)), value=7)
        duracion = st.number_input("Minutos:", min_value=1, value=60)
        
        if st.button("🏁 FINALIZAR ENTRENAMIENTO", use_container_width=True, type="primary"):
            fecha_hoy = obtener_fecha_hora_actual().strftime("%Y-%m-%d")
            res_comp = supabase.table("registros_entrenamiento").select("id").eq("alumno", nombre_atleta).like("fecha", f"{fecha_hoy}%").execute()
            if res_comp.data: st.error("⚠️ Ya registraste una sesión hoy.")
            else:
                validos = [d for d in entradas_alumno.values() if d["kilos"] > 0 or d["reps_reales"] > 0]
                if not validos: st.warning("Cargá marcas antes de guardar.")
                else:
                    fh = obtener_fecha_hora_actual().strftime("%Y-%m-%d %H:%M")
                    mes_ano = obtener_fecha_hora_actual().strftime("%m-%Y")
                    for d in validos:
                        supabase.table("registros_entrenamiento").insert({
                            "fecha": fh, "alumno": nombre_atleta, "nombre_rutina": rutina_completa[0]["nombre_rutina"],
                            "ejercicio": d["ejercicio"], "nro_serie": d["serie"], "kilos": d["kilos"],
                            "reps_reales": d["reps_reales"], "notas": d.get("notas", ""), "rpe_global_sesion": rpe, "duracion_minutos": duracion
                        }).execute()
                    
                    supabase.table("asistencia").insert({"fecha": fecha_hoy, "mes_ano": mes_ano, "alumno": nombre_atleta}).execute()
                    supabase.table("notificaciones").insert({"destinatario": "giuliano", "mensaje": f"🏃 {nombre_atleta} finalizó su sesión."}).execute()
                    
                    # Sincronización racha
                    res_tot = supabase.table("asistencia").select("id", count="exact").eq("alumno", nombre_atleta).eq("mes_ano", mes_ano).execute()
                    total = res_tot.count if res_tot.count is not None else 0
                    st.session_state["msj_pop"] = obtener_frase_motivacional(total)
                    st.success("🚀 ¡Sesión enviada!")
                    st.rerun()

if "msj_pop" in st.session_state:
    st.balloons()
    st.toast(st.session_state["msj_pop"], icon="🏆")
    del st.session_state["msj_pop"]

# ==========================================
# 🚀 PANTALLA ATLETA
# ==========================================
if st.session_state["rol_actual"] == "atleta":
    al = st.session_state["usuario_actual"]
    res_at = supabase.table("alumnos").select("foto_perfil, usuario, objetivo, deporte").eq("nombre_apellido", al).execute()
    foto = res_at.data[0]["foto_perfil"] if res_at.data else AVATAR_PREDETERMINADO
    obj = res_at.data[0]["objetivo"] if res_at.data else "Alto Rendimiento"
    dep = res_at.data[0]["deporte"] if res_at.data else "Preparación Física"

    c1, c2 = st.columns([1, 6])
    with c1: st.markdown(f'<img src="{foto}" width="85" height="85" class="profile-pic">', unsafe_allow_html=True)
    with c2:
        st.markdown(f"### 👋 ¡Hola, **{al}**!")
        st.markdown(f"<p style='color: #84CC16; font-weight: bold;'>🎯 Meta: {obj} ({dep})</p>", unsafe_allow_html=True)
    
    t1, t2, t3, t4 = st.tabs(["🏋️‍♂️ Mi Sesión", "📈 Mi Progreso", "💬 Dudas", "⚙️ Perfil"])
    with t1: renderizar_tabla_entrenamiento(al)
    with t2:
        st.markdown("### 📈 Evolución")
        rh = supabase.table("registros_entrenamiento").select("*").eq("alumno", al).execute()
        if rh.data:
            df = pd.DataFrame(rh.data)
            df["e1rm"] = df.apply(lambda r: calcular_e1rm(r["kilos"], r["reps_reales"]), axis=1)
            df["fc"] = df["fecha"].apply(lambda f: f.split(" ")[0])
            ej = st.selectbox("Ejercicio:", sorted(df["ejercicio"].unique()))
            st.line_chart(df[df["ejercicio"]==ej].groupby("fc")["e1rm"].max())
    with t3:
        with st.form("msg"):
            m = st.text_area("Consulta:")
            if st.form_submit_button("Enviar") and m.strip():
                supabase.table("consultas_mensajes").insert({"alumno": al, "mensaje": m.strip()}).execute()
                st.success("Enviado.")
    with t4:
        f_subida = st.file_uploader("📸 Cambiar Foto:", type=["jpg","png","webp"])
        if f_subida and st.button("💾 Guardar Foto"):
            url = subir_foto_perfil(f_subida, st.session_state["usuario_actual"])
            if url:
                supabase.table("alumnos").update({"foto_perfil": url}).eq("nombre_apellido", al).execute()
                st.success("Foto actualizada.")
                st.rerun()

# ==========================================
# 🚀 PANTALLA ADMIN
# ==========================================
elif st.session_state["rol_actual"] == "admin":
    res_ap = supabase.table("alumnos").select("nombre_apellido").eq("estado", "aprobado").order("nombre_apellido").execute()
    list_al = [f["nombre_apellido"] for f in res_ap.data]
    list_al_n = ["- Seleccionar -"] + list_al

    ta1, ta2, ta3, ta4, ta5, ta6 = st.tabs(["📊 Historial", "📝 Planificar", "💬 Mensajes", "👥 Atletas", "✅ Aprobaciones", "📚 Biblioteca"])
    
    with ta1:
        al_r = st.selectbox("Auditar Atleta:", list_al_n)
        if al_r != "- Seleccionar -":
            rt = supabase.table("registros_entrenamiento").select("*").eq("alumno", al_r).order("id", desc=True).execute()
            if rt.data:
                df_t = pd.DataFrame(rt.data)
                for f in df_t["fecha"].unique():
                    with st.expander(f"Session {f}"):
                        st.dataframe(df_t[df_t["fecha"]==f][["ejercicio","nro_serie","kilos","reps_reales","notas"]], hide_index=True)

    with ta2:
        al_p = st.selectbox("Planificar para:", list_al_n)
        if al_p != "- Seleccionar -":
            nom_r = st.text_input("Nombre de la Rutina:")
            c1, c2 = st.columns(2)
            with c1: dia = st.selectbox("Día:", DIAS_PLANIF)
            with c2: blo = st.selectbox("Bloque:", SUB_BLOQUES)
            
            ej_nom = st.text_input("Ejercicio:")
            s_o = st.number_input("Series:", 1, 10, 4)
            r_o = st.text_input("Reps:", "10")
            
            if st.button("➕ Añadir"):
                st.session_state["borrador_rutina"].append({"ejercicio": ej_nom, "bloque": f"{dia}|{blo}", "series": s_o, "reps": r_o})
            
            if st.session_state["borrador_rutina"]:
                st.dataframe(pd.DataFrame(st.session_state["borrador_rutina"]))
                if st.button("💾 PUBLICAR PLAN"):
                    supabase.table("rutinas_asignadas").delete().eq("alumno", al_p).execute()
                    for i in st.session_state["borrador_rutina"]:
                        supabase.table("rutinas_asignadas").insert({"alumno": al_p, "nombre_rutina": nom_r, "ejercicio": i["ejercicio"], "bloque": i["bloque"], "series_objetivo": i["series"], "reps_objetivo": i["reps"]}).execute()
                    st.session_state["borrador_rutina"] = []
                    st.success("Publicado.")

    with ta3:
        al_m = st.selectbox("Chat Privado:", list_al_n)
        if al_m != "- Seleccionar -":
            rm = supabase.table("consultas_mensajes").select("*").eq("alumno", al_m).order("id", desc=True).execute()
            txt_r = st.text_input("Responder:")
            if st.button("Enviar Respuesta") and txt_r.strip():
                supabase.table("consultas_mensajes").insert({"alumno": al_m, "mensaje":"(Profe)", "respuesta": txt_r.strip()}).execute()
                st.rerun()
            for m in rm.data:
                st.markdown(f"**{m['alumno']}**: {m['mensaje']}")
                if m['respuesta']: st.markdown(f"**Giuliano**: {m['respuesta']}")
                st.divider()

    with ta4:
        ra = supabase.table("alumnos").select("*").eq("estado", "aprobado").execute()
        for a in ra.data:
            with st.expander(f"{a['nombre_apellido']} ({a['deporte']})"):
                st.image(a.get("foto_perfil", AVATAR_PREDETERMINADO), width=100)
                st.text(f"Peso: {a['peso']}kg | Altura: {a['altura']}m | Meta: {a['objetivo']}")
                if st.button("🗑️ ELIMINAR", key=f"del_{a['id']}"):
                    supabase.table("alumnos").delete().eq("id", a['id']).execute()
                    st.rerun()

    with ta5:
        rp = supabase.table("alumnos").select("*").eq("estado", "pendiente").execute()
        for p in rp.data:
            st.write(f"Atleta: {p['nombre_apellido']}")
            if st.button("Aprobar", key=f"ap_{p['id']}"):
                supabase.table("alumnos").update({"estado":"aprobado"}).eq("id", p['id']).execute()
                st.rerun()

    with ta6:
        st.markdown("### Biblioteca")
        if st.button("Vaciar Biblioteca"):
            supabase.table("biblioteca_ejercicios").delete().neq("id", 0).execute()
        f_xl = st.file_uploader("Subir Excel:", type=["xlsx", "csv"])
        if f_xl and st.button("Cargar Lote"):
            df = pd.read_excel(f_xl) if f_xl.name.endswith(".xlsx") else pd.read_csv(f_xl)
            lote = []
            for _, r in df.iterrows():
                lote.append({"nombre": str(r.iloc[0]), "grupo_muscular": str(r.iloc[1]) if len(r)>1 else "General"})
            supabase.table("biblioteca_ejercicios").insert(lote).execute()
            st.success("Cargado.")
