"""
app.py
------
Interfaz de usuario de la aplicación NBA Shot Chart.

Modos:
    Un jugador  → scatter maps, hexbin, animación por partidos
    Comparar    → mapa lado a lado, hexbin lado a lado, tabla de stats

Estructura del proyecto:
    app.py          ← estás acá
    nba/
        api.py      → comunicación con la NBA Stats API
        stats.py    → cálculos sobre los datos
        charts.py   → visualizaciones (cancha, mapas, video, hexbin, comparador)
"""

import os
import time
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st
from nba_api.stats.static import players

from nba.api    import obtener_tiros, obtener_ranking
from nba.stats  import calcular_stats
from nba.charts import (
    generar_imagenes, generar_video, generar_hexbin,
    generar_comparacion_mapa, generar_comparacion_hexbin,
)


# ── Configuración de la página ────────────────────────────────────────────────

st.set_page_config(
    page_title="Mapa de tiros NBA",
    page_icon="🏀",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stApp { background-color: #0a0a0a; }
    h1, h2, h3, h4 { color: white; }
    video { border-radius: 8px; }
    /* Tabla de comparación */
    .stat-table { width: 100%; border-collapse: collapse; color: white; font-size: 14px; }
    .stat-table th { background: #1a1a2e; padding: 8px 12px; text-align: center; }
    .stat-table td { padding: 7px 12px; text-align: center; border-bottom: 1px solid #222; }
    .stat-table tr:hover td { background: #111122; }
    .mejor { color: #00ff88; font-weight: bold; }
    .peor  { color: #ff3333; }
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


def tabla_comparativa_html(
    stats1: dict, stats2: dict,
    ranking1: dict, ranking2: dict,
    nombre1: str, nombre2: str,
) -> str:
    """
    Genera HTML de una tabla comparativa de estadísticas entre dos jugadores.

    Resalta en verde al jugador con mejor valor en cada métrica,
    y en rojo al que tiene el peor valor.
    """
    def highlight(v1, v2, higher_is_better=True):
        """Devuelve clases CSS para cada celda según quién gana."""
        if v1 is None or v2 is None:
            return "", ""
        ganador = (v1 > v2) if higher_is_better else (v1 < v2)
        if v1 == v2:
            return "", ""
        return ("mejor", "peor") if ganador else ("peor", "mejor")

    def fmt_rank(rank, total):
        return f"#{rank} / {total}" if rank else "No califica"

    rows = [
        ("% de tiro (FG%)",
         f"{stats1['fg_pct']}%", f"{stats2['fg_pct']}%",
         *highlight(stats1["fg_pct"], stats2["fg_pct"])),

        ("% de triples (3PT%)",
         f"{stats1['fg3_pct']}%", f"{stats2['fg3_pct']}%",
         *highlight(stats1["fg3_pct"], stats2["fg3_pct"])),

        ("Tiros intentados",
         f"{stats1['intentos']}", f"{stats2['intentos']}",
         *highlight(stats1["intentos"], stats2["intentos"])),

        ("Tiros convertidos",
         f"{stats1['metidos']}", f"{stats2['metidos']}",
         *highlight(stats1["metidos"], stats2["metidos"])),

        ("Triples intentados",
         f"{stats1['intentos_3']}", f"{stats2['intentos_3']}",
         *highlight(stats1["intentos_3"], stats2["intentos_3"])),

        ("Triples convertidos",
         f"{stats1['metidos_3']}", f"{stats2['metidos_3']}",
         *highlight(stats1["metidos_3"], stats2["metidos_3"])),

    ]

    # Rankings: los calculamos aparte porque el * unpacking en tuplas con
    # condicional no es sintaxis válida en Python
    cls_rank_fg  = highlight(ranking1["rank_fg"],  ranking2["rank_fg"],  higher_is_better=False) \
                   if ranking1["rank_fg"]  and ranking2["rank_fg"]  else ("", "")
    cls_rank_fg3 = highlight(ranking1["rank_fg3"], ranking2["rank_fg3"], higher_is_better=False) \
                   if ranking1["rank_fg3"] and ranking2["rank_fg3"] else ("", "")

    rows += [
        ("Ranking FG% en liga",
         fmt_rank(ranking1["rank_fg"],  ranking1["total_fg"]),
         fmt_rank(ranking2["rank_fg"],  ranking2["total_fg"]),
         cls_rank_fg[0],  cls_rank_fg[1]),

        ("Ranking 3PT% en liga",
         fmt_rank(ranking1["rank_fg3"], ranking1["total_fg3"]),
         fmt_rank(ranking2["rank_fg3"], ranking2["total_fg3"]),
         cls_rank_fg3[0], cls_rank_fg3[1]),
    ]

    filas_html = ""
    for metrica, v1, v2, cls1, cls2 in rows:
        filas_html += f"""
        <tr>
            <td class="{cls1}">{v1}</td>
            <td style="color:#888888; font-size:12px;">{metrica}</td>
            <td class="{cls2}">{v2}</td>
        </tr>"""

    return f"""
    <table class="stat-table">
        <thead>
            <tr>
                <th style="color:#00ff88;">{nombre1}</th>
                <th>Estadística</th>
                <th style="color:#4dabf7;">{nombre2}</th>
            </tr>
        </thead>
        <tbody>{filas_html}</tbody>
    </table>
    """


def id_de_nombre(nombre: str, lista: list) -> int:
    return next(j["id"] for j in lista if j["full_name"] == nombre)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏀 Mapa de tiros NBA")
    st.markdown("---")

    # ── Modo ─────────────────────────────────────────────────────────────────
    modo = st.radio(
        "Modo",
        options=["👤 Un jugador", "⚔️ Comparar jugadores"],
        horizontal=True,
    )
    comparar = modo == "⚔️ Comparar jugadores"

    st.markdown("---")

    todos = players.get_players()
    nombres = sorted([j["full_name"] for j in todos])

    hoy = datetime.now()
    temporada_actual = hoy.year if hoy.month >= 9 else hoy.year - 1
    temporadas = [f"{y}-{str(y + 1)[2:]}" for y in range(temporada_actual, 1995, -1)]
    tipos = ["Regular Season", "Playoffs"]

    if not comparar:
        # ── Modo un jugador ───────────────────────────────────────────────────
        jugador1 = st.selectbox("Jugador", options=nombres,
                                index=nombres.index("Stephen Curry"))
        temporada1 = st.selectbox("Temporada", options=temporadas)
        tipo1      = st.selectbox("Tipo", options=tipos)
        jugador2 = temporada2 = tipo2 = None

    else:
        # ── Modo comparar: cada jugador tiene su propia temporada y tipo ──────
        st.markdown("**Jugador 1**")
        jugador1   = st.selectbox("", options=nombres,
                                  index=nombres.index("Stephen Curry"),
                                  key="j1")
        temporada1 = st.selectbox("", options=temporadas, key="t1")
        tipo1      = st.selectbox("", options=tipos, key="tp1")

        st.markdown("**Jugador 2**")
        jugador2   = st.selectbox("", options=nombres,
                                  index=nombres.index("Klay Thompson"),
                                  key="j2")
        temporada2 = st.selectbox("", options=temporadas, key="t2")
        tipo2      = st.selectbox("", options=tipos, key="tp2")

    st.markdown("---")

    # ── Opciones de visualización (solo modo un jugador) ──────────────────────
    if not comparar:
        st.markdown("**¿Qué querés generar?**")
        quiere_video  = st.checkbox("🎬 Animación por partidos", value=False,
                                    help="~20 seg. Al terminar muestra los charts.")
        quiere_mapa   = st.checkbox("📍 Mapa de tiros",          value=True,
                                    help="~3 seg. Scatter con convertidos y fallados.")
        quiere_hexbin = st.checkbox("🔥 Hexbin (eficiencia)",    value=False,
                                    help="~3 seg. Tamaño = volumen, color = FG%.")
        alguno = quiere_video or quiere_mapa or quiere_hexbin
        if not alguno:
            st.warning("Elegí al menos una visualización.")
    else:
        alguno = True   # En modo comparar siempre generamos todo

    buscar = st.button("Generar", use_container_width=True, disabled=not alguno)


# ── Título dinámico ───────────────────────────────────────────────────────────

if comparar:
    st.title(f"{jugador1} ({temporada1})  ⚔️  {jugador2} ({temporada2})")
else:
    st.title(f"{jugador1} — {temporada1}")


# ── Generación de datos y charts ──────────────────────────────────────────────

if buscar:
    with st.spinner("Obteniendo datos..."):
        try:
            pid1     = id_de_nombre(jugador1, todos)
            tiros1   = obtener_tiros(pid1, temporada1, tipo1)
            stats1   = calcular_stats(tiros1)
            ranking1 = obtener_ranking(pid1, temporada1, tipo1)

            if comparar:
                pid2     = id_de_nombre(jugador2, todos)
                tiros2   = obtener_tiros(pid2, temporada2, tipo2)
                stats2   = calcular_stats(tiros2)
                ranking2 = obtener_ranking(pid2, temporada2, tipo2)

        except ValueError as e:
            st.warning(f"⚠️ {e}")
            st.info("Probá con otra temporada o con 'Regular Season'.")
            st.stop()
        except Exception:
            st.error("❌ Error al conectarse con la NBA API. Intentá de nuevo.")
            st.stop()

    resultados = {}

    if comparar:
        with st.spinner("📊 Generando comparación..."):
            # En el título del chart mostramos temporada de cada jugador por separado
            titulo_comp = f"{jugador1} ({temporada1})  vs  {jugador2} ({temporada2})"
            resultados["comp_mapa"]   = generar_comparacion_mapa(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
            resultados["comp_hexbin"] = generar_comparacion_hexbin(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
            resultados["comp_stats"]  = {
                "stats1": stats1, "stats2": stats2,
                "ranking1": ranking1, "ranking2": ranking2,
            }
    else:
        if quiere_video:
            with st.spinner("🎬 Generando animación (~20 seg)..."):
                ruta_mp4       = os.path.join(tempfile.gettempdir(), "shot_chart.mp4")
                duracion_video = generar_video(tiros1, jugador1, ruta_mp4)
                rutas_post     = generar_imagenes(tiros1, jugador1, temporada1)
                resultados["video"] = {"ruta": ruta_mp4, "duracion": duracion_video,
                                       "rutas_charts": rutas_post}

        if quiere_mapa:
            with st.spinner("📍 Generando mapa de tiros..."):
                rutas = (resultados["video"]["rutas_charts"] if "video" in resultados
                         else generar_imagenes(tiros1, jugador1, temporada1))
                resultados["mapa"] = rutas

        if quiere_hexbin:
            with st.spinner("🔥 Generando hexbin..."):
                resultados["hexbin"] = {
                    "ruta": generar_hexbin(tiros1, jugador1, temporada1)}

    st.session_state.update({
        "resultados"    : resultados,
        "comparar"      : comparar,
        "stats1"        : stats1,
        "ranking1"      : ranking1,
        "stats2"        : stats2    if comparar else None,
        "ranking2"      : ranking2  if comparar else None,
        "jugador1"      : jugador1,
        "jugador2"      : jugador2  if comparar else None,
        "temporada"     : temporada1,
        "video_mostrado": False,
    })


# ── Renderizado ───────────────────────────────────────────────────────────────

if "resultados" not in st.session_state or not st.session_state.resultados:
    st.info("Elegí un jugador, seleccioná las visualizaciones y presioná Generar.")
    st.stop()

resultados = st.session_state.resultados
es_comparar = st.session_state.comparar

# ── MODO COMPARACIÓN ──────────────────────────────────────────────────────────
if es_comparar:
    tab_mapa, tab_hexbin, tab_stats = st.tabs([
        "📍 Mapa de tiros", "🔥 Hexbin", "📊 Estadísticas"
    ])

    with tab_mapa:
        st.image(resultados["comp_mapa"], use_container_width=True)
        with open(resultados["comp_mapa"], "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name=f"comparacion_mapa_{st.session_state.temporada}.png",
                               mime="image/png")

    with tab_hexbin:
        st.image(resultados["comp_hexbin"], use_container_width=True)
        st.caption("Escala de tamaño y color unificada — comparación directa entre jugadores.")
        with open(resultados["comp_hexbin"], "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name=f"comparacion_hexbin_{st.session_state.temporada}.png",
                               mime="image/png")

    with tab_stats:
        st.markdown("<br>", unsafe_allow_html=True)
        html = tabla_comparativa_html(
            st.session_state.stats1,   st.session_state.stats2,
            st.session_state.ranking1, st.session_state.ranking2,
            st.session_state.jugador1, st.session_state.jugador2,
        )
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("🟢 Mejor valor en la categoría   🔴 Peor valor en la categoría")

# ── MODO UN JUGADOR ───────────────────────────────────────────────────────────
else:
    col_grafico, col_stats = st.columns([3, 1])

    with col_grafico:
        labels = []
        if "video"  in resultados: labels.append("🎬 Animación")
        if "mapa"   in resultados: labels.append("📍 Mapa de tiros")
        if "hexbin" in resultados: labels.append("🔥 Hexbin")

        tabs    = st.tabs(labels)
        tab_idx = 0

        # Tab: Animación
        if "video" in resultados:
            with tabs[tab_idx]:
                vd = resultados["video"]
                if not st.session_state.get("video_mostrado", False):
                    with open(vd["ruta"], "rb") as f:
                        st.video(f.read(), autoplay=True)
                    time.sleep(vd["duracion"])
                    st.session_state.video_mostrado = True
                    st.rerun()
                else:
                    col_replay, _ = st.columns([1, 3])
                    with col_replay:
                        if st.button("🎬 Ver animación de nuevo", use_container_width=True):
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
                                              st.session_state.temporada)
                    with col_b:
                        st.image(rutas["fallados"]["ruta"], use_container_width=True)
                        st.caption("❌ Tiros fallados")
                        if st.button("Ver en grande", key="btn_vf", use_container_width=True):
                            ver_imagen_grande(rutas["fallados"]["ruta"],
                                              rutas["fallados"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada)
                    _, col_c, _ = st.columns([1, 2, 1])
                    with col_c:
                        st.image(rutas["completo"]["ruta"], use_container_width=True)
                        st.caption("⚖️ Vista completa")
                        if st.button("Ver en grande", key="btn_vco", use_container_width=True):
                            ver_imagen_grande(rutas["completo"]["ruta"],
                                              rutas["completo"]["titulo"],
                                              st.session_state.jugador1,
                                              st.session_state.temporada)
            tab_idx += 1

        # Tab: Mapa de tiros
        if "mapa" in resultados:
            with tabs[tab_idx]:
                rutas    = resultados["mapa"]
                col_a, col_b = st.columns(2)
                with col_a:
                    st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                    st.caption("✅ Tiros convertidos")
                    if st.button("Ver en grande", key="btn_convertidos", use_container_width=True):
                        ver_imagen_grande(rutas["convertidos"]["ruta"],
                                          rutas["convertidos"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada)
                with col_b:
                    st.image(rutas["fallados"]["ruta"], use_container_width=True)
                    st.caption("❌ Tiros fallados")
                    if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                        ver_imagen_grande(rutas["fallados"]["ruta"],
                                          rutas["fallados"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada)
                _, col_c, _ = st.columns([1, 2, 1])
                with col_c:
                    st.image(rutas["completo"]["ruta"], use_container_width=True)
                    st.caption("⚖️ Vista completa")
                    if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                        ver_imagen_grande(rutas["completo"]["ruta"],
                                          rutas["completo"]["titulo"],
                                          st.session_state.jugador1,
                                          st.session_state.temporada)
            tab_idx += 1

        # Tab: Hexbin
        if "hexbin" in resultados:
            with tabs[tab_idx]:
                ruta_hb = resultados["hexbin"]["ruta"]
                st.image(ruta_hb, use_container_width=True)
                st.caption("Tamaño = volumen · Color = FG% (azul frío → rojo caliente)")
                with open(ruta_hb, "rb") as f:
                    st.download_button("⬇ Descargar hexbin", data=f,
                                       file_name=f"hexbin_{st.session_state.jugador1}.png",
                                       mime="image/png", use_container_width=True)

    with col_stats:
        st.markdown("#### Estadísticas")
        s = st.session_state.stats1
        r = st.session_state.ranking1
        st.metric("% de tiro",    f"{s['fg_pct']}%",
                  f"#{r['rank_fg']} de {r['total_fg']}"   if r["rank_fg"]  else "No califica (< 300 FGM)")
        st.metric("% de triples", f"{s['fg3_pct']}%",
                  f"#{r['rank_fg3']} de {r['total_fg3']}" if r["rank_fg3"] else "No califica (< 82 3PM)")
        st.metric("Tiros intentados", s["intentos"])
        st.metric("Tiros convertidos", s["metidos"])