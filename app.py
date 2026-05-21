"""
app.py
------
Interfaz de usuario de la aplicación NBA Shot Chart.

Modos:
    Un jugador  → scatter maps, hexbin, animación por partidos
    Comparar    → mapa lado a lado, hexbin lado a lado, tabla de stats

Opciones de temporada: cualquier temporada desde 1996-97, "📅 Toda la carrera"
Opciones de tipo: Regular Season, Playoffs, Ambos

Estructura del proyecto:
    app.py          ← estás acá
    nba/
        api.py      → comunicación con la NBA Stats API
        stats.py    → cálculos sobre los datos
        charts.py   → visualizaciones
"""

import os
import time
import tempfile
from datetime import datetime

import streamlit as st
from nba_api.stats.static import players

from nba.api    import obtener_tiros, obtener_tiros_carrera, obtener_stats_panel
from nba.stats  import calcular_stats, calcular_ts
from nba.charts import (
    generar_imagenes, generar_video, generar_hexbin,
    generar_comparacion_mapa, generar_comparacion_hexbin,
)


# ── Constantes UI ─────────────────────────────────────────────────────────────

OPCION_CARRERA     = "📅 Toda la carrera"
OPCION_CARRERA_API = "Toda la carrera"   # Sin emoji, para la API
TIPOS              = ["Regular Season", "Playoffs", "Ambos"]


# ── Configuración de la página ────────────────────────────────────────────────

st.set_page_config(page_title="Mapa de tiros NBA", page_icon="🏀", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stApp { background-color: #0a0a0a; }
    h1, h2, h3, h4 { color: white; }
    video { border-radius: 8px; }
    .stat-table { width:100%; border-collapse:collapse; color:white; font-size:14px; }
    .stat-table th { background:#1a1a2e; padding:8px 12px; text-align:center; }
    .stat-table td { padding:7px 12px; text-align:center; border-bottom:1px solid #222; }
    .stat-table tr:hover td { background:#111122; }
    .mejor { color:#00ff88; font-weight:bold; }
    .peor  { color:#ff3333; }
</style>
""", unsafe_allow_html=True)


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
    """Convierte la opción UI a string que entiende la API."""
    return OPCION_CARRERA_API if temporada_ui == OPCION_CARRERA else temporada_ui


def label_temporada(temporada: str, tipo: str) -> str:
    """Etiqueta corta para títulos y gráficos."""
    sufijo = {"Playoffs": " PO", "Ambos": " RS+PO"}.get(tipo, "")
    if temporada == OPCION_CARRERA:
        return f"Carrera{sufijo}"
    return f"{temporada}{sufijo}"


def fmt_rank(rank, total) -> str:
    return f"#{rank} / {total}" if rank else "—"


def tabla_comparativa_html(
    stats1: dict, stats2: dict,
    panel1: dict, panel2: dict,
    nombre1: str, nombre2: str,
    temporada1: str, temporada2: str,
    tipo1: str, tipo2: str,
) -> str:
    """Genera HTML de tabla comparativa con stats básicas y avanzadas."""

    def hl(v1, v2, higher=True) -> tuple:
        if v1 is None or v2 is None or v1 == v2:
            return "", ""
        return ("mejor", "peor") if (v1 > v2) == higher else ("peor", "mejor")

    ts1 = calcular_ts(panel1["pts"], panel1["fga"], panel1["fta"])
    ts2 = calcular_ts(panel2["pts"], panel2["fga"], panel2["fta"])
    ts1_str = f"{ts1*100:.1f}%" if ts1 else "N/A"
    ts2_str = f"{ts2*100:.1f}%" if ts2 else "N/A"

    pm1 = panel1["plus_minus"]
    pm2 = panel2["plus_minus"]
    pm1_str = str(pm1) if pm1 is not None else "N/A (carrera)"
    pm2_str = str(pm2) if pm2 is not None else "N/A (carrera)"

    cls_fg  = hl(panel1["rank_fg"],  panel2["rank_fg"],  higher=False) \
              if panel1["rank_fg"]  and panel2["rank_fg"]  else ("", "")
    cls_fg3 = hl(panel1["rank_fg3"], panel2["rank_fg3"], higher=False) \
              if panel1["rank_fg3"] and panel2["rank_fg3"] else ("", "")

    # Indicamos si el ranking aplica según tipo elegido
    def rank_label(tipo: str, temporada: str) -> str:
        if temporada == OPCION_CARRERA or tipo == "Ambos":
            return "No aplica"
        return ""

    nota_rank1 = rank_label(tipo1, temporada1)
    nota_rank2 = rank_label(tipo2, temporada2)

    rows = [
        ("Partidos jugados",
         str(panel1["gp"]),        str(panel2["gp"]),
         *hl(panel1["gp"],         panel2["gp"])),

        ("Min. por partido",
         str(panel1["min_pg"]),    str(panel2["min_pg"]),
         *hl(panel1["min_pg"],     panel2["min_pg"])),

        ("Plus / Minus",
         pm1_str, pm2_str,
         *(hl(pm1, pm2) if pm1 is not None and pm2 is not None else ("", ""))),

        ("% de tiro (FG%)",
         f"{stats1['fg_pct']}%",   f"{stats2['fg_pct']}%",
         *hl(stats1["fg_pct"],     stats2["fg_pct"])),

        ("% de triples (3PT%)",
         f"{stats1['fg3_pct']}%",  f"{stats2['fg3_pct']}%",
         *hl(stats1["fg3_pct"],    stats2["fg3_pct"])),

        ("TS% ★",
         ts1_str, ts2_str,
         *(hl(ts1, ts2) if ts1 and ts2 else ("", ""))),

        ("Tiros intentados",
         str(stats1["intentos"]),  str(stats2["intentos"]),
         *hl(stats1["intentos"],   stats2["intentos"])),

        ("Tiros convertidos",
         str(stats1["metidos"]),   str(stats2["metidos"]),
         *hl(stats1["metidos"],    stats2["metidos"])),

        ("Triples intentados",
         str(stats1["intentos_3"]), str(stats2["intentos_3"]),
         *hl(stats1["intentos_3"], stats2["intentos_3"])),

        ("Triples convertidos",
         str(stats1["metidos_3"]), str(stats2["metidos_3"]),
         *hl(stats1["metidos_3"],  stats2["metidos_3"])),

        ("Ranking FG% en liga",
         nota_rank1 or fmt_rank(panel1["rank_fg"],  panel1["total_fg"]),
         nota_rank2 or fmt_rank(panel2["rank_fg"],  panel2["total_fg"]),
         cls_fg[0],  cls_fg[1]),

        ("Ranking 3PT% en liga",
         nota_rank1 or fmt_rank(panel1["rank_fg3"], panel1["total_fg3"]),
         nota_rank2 or fmt_rank(panel2["rank_fg3"], panel2["total_fg3"]),
         cls_fg3[0], cls_fg3[1]),
    ]

    filas = "".join(f"""
    <tr>
        <td class="{c1}">{v1}</td>
        <td style="color:#888;font-size:12px;">{m}</td>
        <td class="{c2}">{v2}</td>
    </tr>""" for m, v1, v2, c1, c2 in rows)

    min_rs  = "300 FGM / 82 3PM"
    min_po  = "50 FGM / 20 3PM"

    return f"""
    <table class="stat-table">
      <thead><tr>
        <th style="color:#00ff88;">{nombre1}</th>
        <th>Estadística</th>
        <th style="color:#4dabf7;">{nombre2}</th>
      </tr></thead>
      <tbody>{filas}</tbody>
    </table>
    <p style="color:#555;font-size:11px;margin-top:10px;">
      ★ <b>True Shooting %</b> = PTS / (2 × (FGA + 0.44 × FTA)). Promedio NBA ~56%.<br>
      Mínimos de ranking — Regular Season: {min_rs} · Playoffs: {min_po}.<br>
      El ranking no aplica para carrera completa ni para tipo "Ambos".
    </p>"""


# ── Selector de jugador reutilizable ──────────────────────────────────────────

def selector_jugador(label: str, key_prefix: str, nombres: list,
                     temporadas_list: list, default_nombre: str = "Stephen Curry") -> tuple:
    """
    Muestra selectores de jugador, temporada y tipo.
    Si elige "Toda la carrera", muestra checkbox de slider.
    Retorna (jugador, temporada, tipo, quiere_slider).
    """
    jugador   = st.selectbox(label, nombres,
                              index=nombres.index(default_nombre), key=f"{key_prefix}_j")
    temporada = st.selectbox("Temporada", temporadas_list,     key=f"{key_prefix}_t")
    tipo      = st.selectbox("Tipo",      TIPOS,               key=f"{key_prefix}_tp")

    quiere_slider = False
    if temporada == OPCION_CARRERA:
        quiere_slider = st.checkbox(
            "Ver temporada por temporada",
            key=f"{key_prefix}_slider",
            help="Después de generar podés filtrar por temporada con un selector."
        )
    return jugador, temporada, tipo, quiere_slider


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏀 Mapa de tiros NBA")
    st.markdown("---")

    modo     = st.radio("Modo", ["👤 Un jugador", "⚔️ Comparar jugadores"], horizontal=True)
    comparar = modo == "⚔️ Comparar jugadores"
    st.markdown("---")

    todos   = players.get_players()
    nombres = sorted([j["full_name"] for j in todos])

    hoy             = datetime.now()
    año_actual      = hoy.year if hoy.month >= 9 else hoy.year - 1
    temporadas_list = [OPCION_CARRERA] + [
        f"{y}-{str(y+1)[2:]}" for y in range(año_actual, 1995, -1)
    ]

    if not comparar:
        st.markdown("**Jugador**")
        jugador1, temporada1, tipo1, slider1 = selector_jugador(
            "", "j1", nombres, temporadas_list, "Stephen Curry")
        jugador2 = temporada2 = tipo2 = slider2 = None

        st.markdown("---")
        st.markdown("**¿Qué querés generar?**")
        quiere_video  = st.checkbox("🎬 Animación", value=False,
                                    help="Solo disponible para una temporada, no para carrera completa.")
        quiere_mapa   = st.checkbox("📍 Mapa de tiros", value=True)
        quiere_hexbin = st.checkbox("🔥 Hexbin", value=False)

        if temporada1 == OPCION_CARRERA and quiere_video:
            st.warning("⚠️ La animación no está disponible para carrera completa.")
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

    buscar = st.button("Generar", use_container_width=True,
                       disabled=not alguno if not comparar else False)


# ── Título ────────────────────────────────────────────────────────────────────

if comparar:
    st.title(f"{jugador1} ({label_temporada(temporada1, tipo1)})  "
             f"⚔️  {jugador2} ({label_temporada(temporada2, tipo2)})")
else:
    st.title(f"{jugador1} — {label_temporada(temporada1, tipo1)}")


# ── Obtención de datos ────────────────────────────────────────────────────────

if buscar:
    pid1 = id_de_nombre(jugador1, todos)
    pid2 = id_de_nombre(jugador2, todos) if comparar else None

    with st.spinner("Obteniendo datos..."):
        try:
            # Jugador 1
            if temporada1 == OPCION_CARRERA:
                tiros1, temps_carrera1 = obtener_tiros_carrera(pid1, tipo1)
            else:
                tiros1, temps_carrera1 = obtener_tiros(pid1, temporada1, tipo1), None

            stats1 = calcular_stats(tiros1)
            panel1 = obtener_stats_panel(pid1, api_temporada(temporada1), tipo1)

            # Jugador 2
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
            st.error("❌ Error al conectarse con la NBA API. Intentá de nuevo.")
            st.stop()

    # ── Generación de charts ──────────────────────────────────────────────────
    resultados = {}
    lbl1 = label_temporada(temporada1, tipo1)

    if comparar:
        with st.spinner("📊 Generando comparación..."):
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
        "resultados"     : resultados,
        "comparar"       : comparar,
        "stats1"         : stats1,
        "panel1"         : panel1,
        "stats2"         : stats2,
        "panel2"         : panel2,
        "jugador1"       : jugador1,
        "jugador2"       : jugador2,
        "temporada1"     : temporada1,
        "temporada2"     : temporada2,
        "tipo1"          : tipo1,
        "tipo2"          : tipo2,
        "tiros1"         : tiros1,
        "tiros2"         : tiros2,
        "temps_carrera1" : temps_carrera1,
        "temps_carrera2" : temps_carrera2,
        "slider1"        : slider1,
        "slider2"        : slider2,
        "video_mostrado" : False,
    })


# ── Renderizado ───────────────────────────────────────────────────────────────

if "resultados" not in st.session_state or not st.session_state.resultados:
    st.info("Elegí un jugador, seleccioná las visualizaciones y presioná Generar.")
    st.stop()

resultados  = st.session_state.resultados
es_comparar = st.session_state.comparar


def render_slider_y_charts(
    key_prefix: str,
    tiros_full: "pd.DataFrame",
    temps_carrera: list | None,
    jugador: str,
    temporada: str,
    tipo: str,
    pid: int,
    quiere_slider: bool,
) -> tuple:
    """
    Muestra el slider de temporada (si aplica) y devuelve
    (df_a_usar, lbl_a_usar, panel_a_usar) para renderizar los charts.
    """
    import pandas as pd

    if quiere_slider and temps_carrera:
        # Agregamos "Toda la carrera" al inicio del slider
        opciones_slider = [OPCION_CARRERA] + temps_carrera
        sel = st.select_slider(
            f"Temporada — {jugador}",
            options=opciones_slider,
            value=OPCION_CARRERA,
            key=f"{key_prefix}_sel_slider",
        )

        if sel == OPCION_CARRERA:
            df_usar    = tiros_full
            lbl_usar   = label_temporada(temporada, tipo)
            # Extraemos "1" o "2" del key_prefix (j1, j1h, j2, j2h → "1" o "2")
            num = next(c for c in key_prefix if c in ("1", "2"))
            panel_usar = st.session_state[f"panel{num}"]
        else:
            df_usar  = tiros_full[tiros_full["TEMPORADA"] == sel]
            lbl_usar = label_temporada(sel, tipo)
            # Recalculamos el panel para esa temporada específica
            panel_usar = obtener_stats_panel(pid, sel, tipo)
    else:
        df_usar    = tiros_full
        lbl_usar   = label_temporada(temporada, tipo)
        num        = next(c for c in key_prefix if c in ("1", "2"))
        panel_usar = st.session_state[f"panel{num}"]

    return df_usar, lbl_usar, panel_usar


# ── MODO COMPARACIÓN ──────────────────────────────────────────────────────────
if es_comparar:
    tab_mapa, tab_hexbin, tab_stats = st.tabs(
        ["📍 Mapa de tiros", "🔥 Hexbin", "📊 Estadísticas"])

    with tab_mapa:
        # Sliders individuales para cada jugador (si eligieron carrera)
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            df1_usar, lbl1_usar, panel1_usar = render_slider_y_charts(
                "j1",
                st.session_state.tiros1,
                st.session_state.temps_carrera1,
                st.session_state.jugador1,
                st.session_state.temporada1,
                st.session_state.tipo1,
                id_de_nombre(st.session_state.jugador1, todos),
                st.session_state.slider1,
            )
        with col_s2:
            df2_usar, lbl2_usar, panel2_usar = render_slider_y_charts(
                "j2",
                st.session_state.tiros2,
                st.session_state.temps_carrera2,
                st.session_state.jugador2,
                st.session_state.temporada2,
                st.session_state.tipo2,
                id_de_nombre(st.session_state.jugador2, todos),
                st.session_state.slider2,
            )

        # Regeneramos el chart solo si cambió la selección
        titulo_comp = (f"{st.session_state.jugador1} ({lbl1_usar})  "
                       f"vs  {st.session_state.jugador2} ({lbl2_usar})")
        with st.spinner("Actualizando mapa..."):
            ruta_mapa = generar_comparacion_mapa(
                df1_usar, df2_usar,
                st.session_state.jugador1, st.session_state.jugador2,
                titulo_comp)
        st.image(ruta_mapa, use_container_width=True)
        with open(ruta_mapa, "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_mapa.png", mime="image/png")

    with tab_hexbin:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            df1_usar, lbl1_usar, panel1_usar = render_slider_y_charts(
                "j1h",
                st.session_state.tiros1,
                st.session_state.temps_carrera1,
                st.session_state.jugador1,
                st.session_state.temporada1,
                st.session_state.tipo1,
                id_de_nombre(st.session_state.jugador1, todos),
                st.session_state.slider1,
            )
        with col_s2:
            df2_usar, lbl2_usar, panel2_usar = render_slider_y_charts(
                "j2h",
                st.session_state.tiros2,
                st.session_state.temps_carrera2,
                st.session_state.jugador2,
                st.session_state.temporada2,
                st.session_state.tipo2,
                id_de_nombre(st.session_state.jugador2, todos),
                st.session_state.slider2,
            )
        titulo_comp = (f"{st.session_state.jugador1} ({lbl1_usar})  "
                       f"vs  {st.session_state.jugador2} ({lbl2_usar})")
        with st.spinner("Actualizando hexbin..."):
            ruta_hb = generar_comparacion_hexbin(
                df1_usar, df2_usar,
                st.session_state.jugador1, st.session_state.jugador2,
                titulo_comp)
        st.image(ruta_hb, use_container_width=True)
        st.caption("Escala unificada entre jugadores.")
        with open(ruta_hb, "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_hexbin.png", mime="image/png")

    with tab_stats:
        # En stats usamos siempre los paneles del estado guardado
        # (no los del slider, para mostrar el contexto original)
        st.markdown("<br>", unsafe_allow_html=True)
        html = tabla_comparativa_html(
            st.session_state.stats1, st.session_state.stats2,
            st.session_state.panel1, st.session_state.panel2,
            st.session_state.jugador1, st.session_state.jugador2,
            st.session_state.temporada1, st.session_state.temporada2,
            st.session_state.tipo1, st.session_state.tipo2,
        )
        st.markdown(html, unsafe_allow_html=True)


# ── MODO UN JUGADOR ───────────────────────────────────────────────────────────
else:
    col_grafico, col_stats = st.columns([3, 1])

    with col_grafico:
        # Slider (si eligió carrera completa + checkbox)
        df1_usar, lbl1_usar, panel1_usar = render_slider_y_charts(
            "j1",
            st.session_state.tiros1,
            st.session_state.temps_carrera1,
            st.session_state.jugador1,
            st.session_state.temporada1,
            st.session_state.tipo1,
            id_de_nombre(st.session_state.jugador1, todos),
            st.session_state.slider1,
        )

        # Si el slider cambió la selección, regeneramos charts on-the-fly
        charts_dinamicos = st.session_state.get("slider1") and \
                           st.session_state.temps_carrera1 is not None
        if charts_dinamicos:
            with st.spinner("Regenerando charts..."):
                rutas_din  = generar_imagenes(df1_usar, st.session_state.jugador1, lbl1_usar)
                hexbin_din = generar_hexbin(df1_usar, st.session_state.jugador1, lbl1_usar)
            resultados_render = {
                **resultados,
                "mapa"  : rutas_din,
                "hexbin": {"ruta": hexbin_din},
            }
        else:
            resultados_render = resultados

        labels  = []
        if "video"  in resultados_render: labels.append("🎬 Animación")
        if "mapa"   in resultados_render: labels.append("📍 Mapa de tiros")
        if "hexbin" in resultados_render: labels.append("🔥 Hexbin")

        tabs    = st.tabs(labels)
        tab_idx = 0

        # Tab: Animación
        if "video" in resultados_render:
            with tabs[tab_idx]:
                vd = resultados_render["video"]
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
                    rutas    = vd["rutas_charts"]
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                        st.caption("✅ Tiros convertidos")
                        if st.button("Ver en grande", key="btn_vc", use_container_width=True):
                            ver_imagen_grande(rutas["convertidos"]["ruta"],
                                              rutas["convertidos"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
                    with col_b:
                        st.image(rutas["fallados"]["ruta"], use_container_width=True)
                        st.caption("❌ Tiros fallados")
                        if st.button("Ver en grande", key="btn_vf", use_container_width=True):
                            ver_imagen_grande(rutas["fallados"]["ruta"],
                                              rutas["fallados"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
                    _, col_c, _ = st.columns([1, 2, 1])
                    with col_c:
                        st.image(rutas["completo"]["ruta"], use_container_width=True)
                        st.caption("⚖️ Vista completa")
                        if st.button("Ver en grande", key="btn_vco", use_container_width=True):
                            ver_imagen_grande(rutas["completo"]["ruta"],
                                              rutas["completo"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada1)
            tab_idx += 1

        # Tab: Mapa de tiros
        if "mapa" in resultados_render:
            with tabs[tab_idx]:
                rutas    = resultados_render["mapa"]
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                    st.caption("✅ Tiros convertidos")
                    if st.button("Ver en grande", key="btn_convertidos", use_container_width=True):
                        ver_imagen_grande(rutas["convertidos"]["ruta"],
                                          rutas["convertidos"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
                with col_b:
                    st.image(rutas["fallados"]["ruta"], use_container_width=True)
                    st.caption("❌ Tiros fallados")
                    if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                        ver_imagen_grande(rutas["fallados"]["ruta"],
                                          rutas["fallados"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
                _, col_c, _ = st.columns([1, 2, 1])
                with col_c:
                    st.image(rutas["completo"]["ruta"], use_container_width=True)
                    st.caption("⚖️ Vista completa")
                    if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                        ver_imagen_grande(rutas["completo"]["ruta"],
                                          rutas["completo"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada1)
            tab_idx += 1

        # Tab: Hexbin
        if "hexbin" in resultados_render:
            with tabs[tab_idx]:
                ruta_hb = resultados_render["hexbin"]["ruta"]
                st.image(ruta_hb, use_container_width=True)
                st.caption("Tamaño = volumen · Color = FG% (azul frío → rojo caliente)")
                with open(ruta_hb, "rb") as f:
                    st.download_button("⬇ Descargar", data=f,
                                       file_name=f"hexbin_{st.session_state.jugador1}.png",
                                       mime="image/png", use_container_width=True)

    # ── Panel de estadísticas ─────────────────────────────────────────────────
    with col_stats:
        st.markdown("#### Estadísticas")
        # Si hay slider activo, usamos el panel recalculado para esa temporada
        p  = panel1_usar
        s  = calcular_stats(df1_usar)
        ts = calcular_ts(p["pts"], p["fga"], p["fta"])
        pm = p["plus_minus"]

        st.metric("% de tiro", f"{s['fg_pct']}%",
                  f"#{p['rank_fg']} de {p['total_fg']}" if p["rank_fg"] else "No aplica")
        st.metric("% de triples", f"{s['fg3_pct']}%",
                  f"#{p['rank_fg3']} de {p['total_fg3']}" if p["rank_fg3"] else "No aplica")
        st.metric("TS%", f"{ts*100:.1f}%" if ts else "N/A",
                  help="True Shooting %: PTS / (2 × (FGA + 0.44 × FTA)). Promedio NBA ~56%.")
        st.metric("Partidos jugados",  p["gp"])
        st.metric("Min. por partido",  p["min_pg"])
        st.metric("Plus / Minus",
                  str(pm) if pm is not None else "N/A",
                  help="N/A para carrera completa — el +/- no acumula significado entre temporadas.")
        st.metric("Tiros intentados",  s["intentos"])
        st.metric("Tiros convertidos", s["metidos"])