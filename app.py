"""
app.py
------
Interfaz de usuario de la aplicación NBA Shot Chart.

Modos:
    Un jugador  → scatter maps, hexbin, animación por partidos
    Comparar    → mapa lado a lado, hexbin lado a lado, tabla de stats

Temas: "light" (Editorial Paper) y "dark" (Midnight Court).
El tema se guarda en st.session_state.tema y persiste durante la sesión.
"""

import os
import time
import tempfile
from datetime import datetime

import streamlit as st
from nba_api.stats.static import players

from nba.api    import obtener_tiros, obtener_tiros_carrera, obtener_stats_panel
from nba.stats  import calcular_stats, calcular_ts
from nba.styles import aplicar_estilos, stat_table_html
from nba.charts import (
    generar_imagenes, generar_video, generar_hexbin,
    generar_comparacion_mapa, generar_comparacion_hexbin,
)


# ── Constantes ────────────────────────────────────────────────────────────────

OPCION_CARRERA     = "📅 Toda la carrera"
OPCION_CARRERA_API = "Toda la carrera"
TIPOS              = ["Regular Season", "Playoffs", "Ambos"]


# ── Configuración de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="NBA Shot Chart",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializar tema en session_state
if "tema" not in st.session_state:
    st.session_state.tema = "light"

# Aplicar estilos del tema activo
aplicar_estilos(st.session_state.tema)


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.dialog("Mapa de tiros", width="large")
def ver_imagen_grande(ruta: str, titulo: str, nombre: str, temporada: str) -> None:
    st.markdown(f"#### {titulo} — {nombre} {temporada}")
    st.image(ruta, use_container_width=True)
    with open(ruta, "rb") as f:
        st.download_button("⬇ Descargar", data=f,
                           file_name=f"{nombre}_{temporada}_{titulo}.png",
                           mime="image/png", use_container_width=True)


def id_de_nombre(nombre: str, lista: list) -> int:
    return next(j["id"] for j in lista if j["full_name"] == nombre)


def api_temporada(temporada_ui: str) -> str:
    return OPCION_CARRERA_API if temporada_ui == OPCION_CARRERA else temporada_ui


def label_temporada(temporada: str, tipo: str) -> str:
    sufijo = {"Playoffs": " PO", "Ambos": " RS+PO"}.get(tipo, "")
    if temporada == OPCION_CARRERA:
        return f"Carrera{sufijo}"
    return f"{temporada}{sufijo}"


def selector_jugador(label: str, key_prefix: str, nombres: list,
                     temporadas_list: list, default: str = "Stephen Curry") -> tuple:
    jugador   = st.selectbox(label, nombres,
                              index=nombres.index(default), key=f"{key_prefix}_j")
    temporada = st.selectbox("Temporada", temporadas_list, key=f"{key_prefix}_t")
    tipo      = st.selectbox("Tipo",      TIPOS,           key=f"{key_prefix}_tp")
    quiere_slider = False
    if temporada == OPCION_CARRERA:
        quiere_slider = st.checkbox("Ver temporada por temporada",
                                    key=f"{key_prefix}_slider",
                                    help="Filtrá por temporada después de generar.")
    return jugador, temporada, tipo, quiere_slider


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:

    # Logo
    st.markdown("""
    <div style="padding-bottom:16px;border-bottom:1px solid #2a2a2a;margin-bottom:8px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:0.22em;text-transform:uppercase;color:#444;
                    margin-bottom:2px;">NBA Analytics</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:26px;
                    letter-spacing:0.05em;color:#f2ede3;line-height:1;">
            Shot<span style="color:#c8a850;">.</span>Chart
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Toggle de tema
    tema_label = "☀️ Modo claro" if st.session_state.tema == "dark" else "🌙 Modo oscuro"
    if st.button(tema_label, use_container_width=True, key="tema_btn"):
        st.session_state.tema = "dark" if st.session_state.tema == "light" else "light"
        st.rerun()

    st.markdown('<div class="sidebar-section">Modo</div>', unsafe_allow_html=True)
    modo     = st.radio("", ["👤 Un jugador", "⚔️ Comparar"], horizontal=True,
                        label_visibility="collapsed")
    comparar = modo == "⚔️ Comparar"

    st.markdown('<div class="sidebar-section">Jugador</div>', unsafe_allow_html=True)

    todos   = players.get_players()
    nombres = sorted([j["full_name"] for j in todos])

    hoy             = datetime.now()
    año_actual      = hoy.year if hoy.month >= 9 else hoy.year - 1
    temporadas_list = [OPCION_CARRERA] + [
        f"{y}-{str(y+1)[2:]}" for y in range(año_actual, 1995, -1)
    ]

    if not comparar:
        jugador1, temporada1, tipo1, slider1 = selector_jugador(
            "", "j1", nombres, temporadas_list, "Stephen Curry")
        jugador2 = temporada2 = tipo2 = slider2 = None

        st.markdown('<div class="sidebar-section">Visualizaciones</div>',
                    unsafe_allow_html=True)
        quiere_video  = st.checkbox("🎬  Animación", value=False,
                                    help="~20 seg. Solo para una temporada.")
        quiere_mapa   = st.checkbox("📍  Mapa de tiros", value=True)
        quiere_hexbin = st.checkbox("🔥  Hexbin", value=False)

        if temporada1 == OPCION_CARRERA and quiere_video:
            st.warning("La animación no está disponible para carrera completa.")
            quiere_video = False

        alguno = quiere_video or quiere_mapa or quiere_hexbin
        if not alguno:
            st.warning("Elegí al menos una visualización.")
    else:
        st.markdown("**Jugador 1**")
        jugador1, temporada1, tipo1, slider1 = selector_jugador(
            "", "j1", nombres, temporadas_list, "Stephen Curry")
        st.markdown("**Jugador 2**")
        jugador2, temporada2, tipo2, slider2 = selector_jugador(
            "", "j2", nombres, temporadas_list, "Klay Thompson")
        alguno = True

    st.markdown("")
    buscar = st.button("Generar →", use_container_width=True,
                       disabled=not alguno if not comparar else False)


# ── Título principal ──────────────────────────────────────────────────────────

tema = st.session_state.tema
acento = "#c8a850"

if comparar:
    lbl1 = label_temporada(temporada1, tipo1)
    lbl2 = label_temporada(temporada2, tipo2)
    st.markdown(
        f"# {jugador1} "
        f"<span class='season-tag'>{lbl1}</span>"
        f"<span style='font-family:\"Bebas Neue\",sans-serif;color:#555;margin:0 8px;'>vs</span>"
        f"{jugador2} "
        f"<span class='season-tag'>{lbl2}</span>",
        unsafe_allow_html=True
    )
else:
    lbl = label_temporada(temporada1, tipo1)
    st.markdown(
        f"# {jugador1} "
        f"<span class='season-tag'>{lbl}</span>",
        unsafe_allow_html=True
    )


# ── Obtención de datos ────────────────────────────────────────────────────────

if buscar:
    pid1 = id_de_nombre(jugador1, todos)
    pid2 = id_de_nombre(jugador2, todos) if comparar else None

    with st.spinner("Obteniendo datos..."):
        try:
            if temporada1 == OPCION_CARRERA:
                tiros1, temps_carrera1 = obtener_tiros_carrera(pid1, tipo1)
            else:
                tiros1, temps_carrera1 = obtener_tiros(pid1, temporada1, tipo1), None

            stats1 = calcular_stats(tiros1)
            panel1 = obtener_stats_panel(pid1, api_temporada(temporada1), tipo1)

            tiros2 = temps_carrera2 = stats2 = panel2 = None
            if comparar:
                if temporada2 == OPCION_CARRERA:
                    tiros2, temps_carrera2 = obtener_tiros_carrera(pid2, tipo2)
                else:
                    tiros2, temps_carrera2 = obtener_tiros(pid2, temporada2, tipo2), None
                stats2 = calcular_stats(tiros2)
                panel2 = obtener_stats_panel(pid2, api_temporada(temporada2), tipo2)

        except ValueError as e:
            st.warning(f"⚠️ {e}")
            st.info("Probá con otra temporada o tipo.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error inesperado: {type(e).__name__}: {e}")
            st.stop()

    resultados = {}
    lbl1 = label_temporada(temporada1, tipo1)

    if comparar:
        with st.spinner("Generando comparación..."):
            lbl2        = label_temporada(temporada2, tipo2)
            titulo_comp = f"{jugador1} ({lbl1})  vs  {jugador2} ({lbl2})"
            resultados["comp_mapa"]   = generar_comparacion_mapa(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
            resultados["comp_hexbin"] = generar_comparacion_hexbin(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
    else:
        if quiere_video:
            with st.spinner("🎬 Generando animación (~20 seg)..."):
                ruta_mp4       = os.path.join(tempfile.gettempdir(), "shot_chart.mp4")
                duracion_video = generar_video(tiros1, jugador1, ruta_mp4)
                rutas_post     = generar_imagenes(tiros1, jugador1, lbl1)
                resultados["video"] = {"ruta": ruta_mp4, "duracion": duracion_video,
                                       "rutas_charts": rutas_post}
        if quiere_mapa:
            with st.spinner("📍 Generando mapa de tiros..."):
                rutas = (resultados["video"]["rutas_charts"] if "video" in resultados
                         else generar_imagenes(tiros1, jugador1, lbl1))
                resultados["mapa"] = rutas
        if quiere_hexbin:
            with st.spinner("🔥 Generando hexbin..."):
                resultados["hexbin"] = {"ruta": generar_hexbin(tiros1, jugador1, lbl1)}

    st.session_state.update({
        "resultados"    : resultados,
        "comparar"      : comparar,
        "stats1"        : stats1,
        "panel1"        : panel1,
        "stats2"        : stats2,
        "panel2"        : panel2,
        "jugador1"      : jugador1,
        "jugador2"      : jugador2,
        "temporada1"    : temporada1,
        "temporada2"    : temporada2,
        "tipo1"         : tipo1,
        "tipo2"         : tipo2,
        "tiros1"        : tiros1,
        "tiros2"        : tiros2,
        "temps_carrera1": temps_carrera1,
        "temps_carrera2": temps_carrera2,
        "slider1"       : slider1,
        "slider2"       : slider2 if comparar else False,
        "video_mostrado": False,
    })


# ── Renderizado ───────────────────────────────────────────────────────────────

if "resultados" not in st.session_state or not st.session_state.resultados:
    color_txt = "#888" if tema == "dark" else "#999"
    st.markdown(
        f"<p style='font-family:\"IBM Plex Mono\",monospace;font-size:11px;"
        f"letter-spacing:0.1em;color:{color_txt};margin-top:2rem;'>"
        f"Elegí un jugador y presioná Generar →</p>",
        unsafe_allow_html=True
    )
    st.stop()

resultados  = st.session_state.resultados
es_comparar = st.session_state.comparar


def render_slider_y_charts(key_prefix, tiros_full, temps_carrera,
                            jugador, temporada, tipo, pid, quiere_slider):
    if quiere_slider and temps_carrera:
        opciones = [OPCION_CARRERA] + temps_carrera
        sel = st.select_slider(
            f"Temporada — {jugador}",
            options=opciones,
            value=OPCION_CARRERA,
            key=f"{key_prefix}_sel_slider",
        )
        num = next(c for c in key_prefix if c in ("1", "2"))
        if sel == OPCION_CARRERA:
            return tiros_full, label_temporada(temporada, tipo), st.session_state[f"panel{num}"]
        else:
            df_f = tiros_full[tiros_full["TEMPORADA"] == sel]
            return df_f, label_temporada(sel, tipo), obtener_stats_panel(pid, sel, tipo)
    else:
        num = next(c for c in key_prefix if c in ("1", "2"))
        return tiros_full, label_temporada(temporada, tipo), st.session_state[f"panel{num}"]


# ── MODO COMPARACIÓN ──────────────────────────────────────────────────────────

if es_comparar:
    tab_mapa, tab_hexbin, tab_stats = st.tabs(
        ["📍  Mapa de tiros", "🔥  Hexbin", "📊  Estadísticas"])

    with tab_mapa:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            df1_u, lbl1_u, p1_u = render_slider_y_charts(
                "j1", st.session_state.tiros1, st.session_state.temps_carrera1,
                st.session_state.jugador1, st.session_state.temporada1,
                st.session_state.tipo1, id_de_nombre(st.session_state.jugador1, todos),
                st.session_state.slider1)
        with col_s2:
            df2_u, lbl2_u, p2_u = render_slider_y_charts(
                "j2", st.session_state.tiros2, st.session_state.temps_carrera2,
                st.session_state.jugador2, st.session_state.temporada2,
                st.session_state.tipo2, id_de_nombre(st.session_state.jugador2, todos),
                st.session_state.slider2)

        titulo = (f"{st.session_state.jugador1} ({lbl1_u})  "
                  f"vs  {st.session_state.jugador2} ({lbl2_u})")
        with st.spinner("Actualizando..."):
            ruta_m = generar_comparacion_mapa(df1_u, df2_u,
                st.session_state.jugador1, st.session_state.jugador2, titulo)
        st.image(ruta_m, use_container_width=True)
        with open(ruta_m, "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_mapa.png", mime="image/png")

    with tab_hexbin:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            df1_u, lbl1_u, p1_u = render_slider_y_charts(
                "j1h", st.session_state.tiros1, st.session_state.temps_carrera1,
                st.session_state.jugador1, st.session_state.temporada1,
                st.session_state.tipo1, id_de_nombre(st.session_state.jugador1, todos),
                st.session_state.slider1)
        with col_s2:
            df2_u, lbl2_u, p2_u = render_slider_y_charts(
                "j2h", st.session_state.tiros2, st.session_state.temps_carrera2,
                st.session_state.jugador2, st.session_state.temporada2,
                st.session_state.tipo2, id_de_nombre(st.session_state.jugador2, todos),
                st.session_state.slider2)

        titulo = (f"{st.session_state.jugador1} ({lbl1_u})  "
                  f"vs  {st.session_state.jugador2} ({lbl2_u})")
        with st.spinner("Actualizando..."):
            ruta_h = generar_comparacion_hexbin(df1_u, df2_u,
                st.session_state.jugador1, st.session_state.jugador2, titulo)
        st.image(ruta_h, use_container_width=True)
        st.caption("Escala de tamaño y color unificada entre jugadores.")
        with open(ruta_h, "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_hexbin.png", mime="image/png")

    with tab_stats:
        st.markdown("<br>", unsafe_allow_html=True)
        html = stat_table_html(
            st.session_state.stats1, st.session_state.stats2,
            st.session_state.panel1, st.session_state.panel2,
            st.session_state.jugador1, st.session_state.jugador2,
            st.session_state.temporada1, st.session_state.temporada2,
            st.session_state.tipo1, st.session_state.tipo2,
            tema=tema,
        )
        st.markdown(html, unsafe_allow_html=True)


# ── MODO UN JUGADOR ───────────────────────────────────────────────────────────

else:
    col_grafico, col_stats = st.columns([3, 1], gap="large")

    with col_grafico:
        df1_u, lbl1_u, panel1_u = render_slider_y_charts(
            "j1", st.session_state.tiros1, st.session_state.temps_carrera1,
            st.session_state.jugador1, st.session_state.temporada1,
            st.session_state.tipo1, id_de_nombre(st.session_state.jugador1, todos),
            st.session_state.slider1)

        charts_din = (st.session_state.get("slider1") and
                      st.session_state.temps_carrera1 is not None)
        if charts_din:
            with st.spinner("Regenerando..."):
                rutas_din  = generar_imagenes(df1_u, st.session_state.jugador1, lbl1_u)
                hexbin_din = generar_hexbin(df1_u, st.session_state.jugador1, lbl1_u)
            res = {**resultados, "mapa": rutas_din, "hexbin": {"ruta": hexbin_din}}
        else:
            res = resultados

        labels  = []
        if "video"  in res: labels.append("🎬  Animación")
        if "mapa"   in res: labels.append("📍  Mapa de tiros")
        if "hexbin" in res: labels.append("🔥  Hexbin")

        tabs    = st.tabs(labels)
        tab_idx = 0

        # Tab: Animación
        if "video" in res:
            with tabs[tab_idx]:
                vd = res["video"]
                if not st.session_state.get("video_mostrado", False):
                    with open(vd["ruta"], "rb") as f:
                        st.video(f.read(), autoplay=True)
                    time.sleep(vd["duracion"])
                    st.session_state.video_mostrado = True
                    st.rerun()
                else:
                    col_r, _ = st.columns([1, 3])
                    with col_r:
                        if st.button("🎬 Ver de nuevo", use_container_width=True):
                            st.session_state.video_mostrado = False
                            st.rerun()
                    st.markdown("---")
                    rutas = vd["rutas_charts"]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                        st.caption("Tiros convertidos")
                        if st.button("Ver en grande", key="btn_vc", use_container_width=True):
                            ver_imagen_grande(rutas["convertidos"]["ruta"],
                                              rutas["convertidos"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
                    with c2:
                        st.image(rutas["fallados"]["ruta"], use_container_width=True)
                        st.caption("Tiros fallados")
                        if st.button("Ver en grande", key="btn_vf", use_container_width=True):
                            ver_imagen_grande(rutas["fallados"]["ruta"],
                                              rutas["fallados"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
                    _, cc, _ = st.columns([1, 2, 1])
                    with cc:
                        st.image(rutas["completo"]["ruta"], use_container_width=True)
                        st.caption("Vista completa")
                        if st.button("Ver en grande", key="btn_vco", use_container_width=True):
                            ver_imagen_grande(rutas["completo"]["ruta"],
                                              rutas["completo"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
            tab_idx += 1

        # Tab: Mapa de tiros
        if "mapa" in res:
            with tabs[tab_idx]:
                rutas = res["mapa"]
                c1, c2 = st.columns(2)
                with c1:
                    st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                    st.caption("Tiros convertidos")
                    if st.button("Ver en grande", key="btn_convertidos", use_container_width=True):
                        ver_imagen_grande(rutas["convertidos"]["ruta"],
                                          rutas["convertidos"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
                with c2:
                    st.image(rutas["fallados"]["ruta"], use_container_width=True)
                    st.caption("Tiros fallados")
                    if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                        ver_imagen_grande(rutas["fallados"]["ruta"],
                                          rutas["fallados"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
                _, cc, _ = st.columns([1, 2, 1])
                with cc:
                    st.image(rutas["completo"]["ruta"], use_container_width=True)
                    st.caption("Vista completa")
                    if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                        ver_imagen_grande(rutas["completo"]["ruta"],
                                          rutas["completo"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
            tab_idx += 1

        # Tab: Hexbin
        if "hexbin" in res:
            with tabs[tab_idx]:
                ruta_hb = res["hexbin"]["ruta"]
                st.image(ruta_hb, use_container_width=True)
                st.caption("Tamaño = volumen de tiros · Color = FG% (azul frío → rojo caliente)")
                with open(ruta_hb, "rb") as f:
                    st.download_button("⬇ Descargar hexbin", data=f,
                                       file_name=f"hexbin_{st.session_state.jugador1}.png",
                                       mime="image/png", use_container_width=True)

    # ── Panel de stats ────────────────────────────────────────────────────────
    with col_stats:
        st.markdown("#### Estadísticas")
        p  = panel1_u
        s  = calcular_stats(df1_u)
        ts = calcular_ts(p["pts"], p["fga"], p["fta"])
        pm = p["plus_minus"]

        st.metric("FG%", f"{s['fg_pct']}%",
                  f"#{p['rank_fg']} / {p['total_fg']}" if p["rank_fg"] else "No aplica")
        st.metric("3PT%", f"{s['fg3_pct']}%",
                  f"#{p['rank_fg3']} / {p['total_fg3']}" if p["rank_fg3"] else "No aplica")
        st.metric("TS%", f"{ts*100:.1f}%" if ts else "N/A",
                  help="True Shooting %: PTS / (2 × (FGA + 0.44 × FTA)). Liga ~56%.")
        st.metric("Partidos",  p["gp"])
        st.metric("Min / partido", p["min_pg"])
        st.metric("+/−", str(pm) if pm is not None else "N/A",
                  help="N/A para carrera completa.")
        st.metric("Intentos",  s["intentos"])
        st.metric("Convertidos", s["metidos"])