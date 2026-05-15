"""
app.py
------
Interfaz de usuario de la aplicación NBA Shot Chart.

Este archivo solo orquesta: llama a los módulos del paquete `nba` y
construye la UI con Streamlit. No contiene lógica de datos ni de visualización.

Estructura del proyecto:
    app.py          ← estás acá
    nba/
        api.py      → comunicación con la NBA Stats API
        stats.py    → cálculos sobre los datos
        charts.py   → visualizaciones (cancha, mapas, video, hexbin)
"""

import os
import time
import tempfile
from datetime import datetime

import streamlit as st
from nba_api.stats.static import players

from nba.api    import obtener_tiros, obtener_ranking
from nba.stats  import calcular_stats
from nba.charts import generar_imagenes, generar_video, generar_hexbin


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
</style>
""", unsafe_allow_html=True)


# ── Modal de imagen ampliada ──────────────────────────────────────────────────

@st.dialog("Mapa de tiros", width="large")
def ver_imagen_grande(ruta: str, titulo: str, nombre_jugador: str, temporada: str) -> None:
    """Muestra una imagen ampliada con opción de descarga."""
    st.markdown(f"#### {titulo} — {nombre_jugador} {temporada}")
    st.image(ruta, use_container_width=True)
    with open(ruta, "rb") as f:
        st.download_button(
            label="⬇ Descargar imagen",
            data=f,
            file_name=f"{nombre_jugador}_{temporada}_{titulo}.png",
            mime="image/png",
            use_container_width=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏀 Mapa de tiros NBA")
    st.markdown("---")

    todos_los_jugadores = players.get_players()
    nombres = sorted([j["full_name"] for j in todos_los_jugadores])

    jugador_elegido = st.selectbox(
        "Buscá un jugador",
        options=nombres,
        index=nombres.index("Stephen Curry"),
    )

    hoy = datetime.now()
    temporada_actual = hoy.year if hoy.month >= 9 else hoy.year - 1
    temporadas = [f"{y}-{str(y + 1)[2:]}" for y in range(temporada_actual, 1995, -1)]

    temporada_elegida = st.selectbox("Temporada", options=temporadas)
    tipo_elegido      = st.selectbox("Tipo", options=["Regular Season", "Playoffs"])

    st.markdown("---")
    st.markdown("**¿Qué querés generar?**")

    quiere_video  = st.checkbox("🎬 Animación por partidos", value=False,
                                help="~20 segundos. Al terminar muestra los charts automáticamente.")
    quiere_mapa   = st.checkbox("📍 Mapa de tiros",          value=True,
                                help="~3 segundos. Scatter plot con convertidos y fallados.")
    quiere_hexbin = st.checkbox("🔥 Hexbin (eficiencia)",    value=False,
                                help="~3 segundos. Tamaño = volumen, color = % de tiro por zona.")

    alguno_elegido = quiere_video or quiere_mapa or quiere_hexbin

    if not alguno_elegido:
        st.warning("Elegí al menos una visualización.")

    buscar = st.button(
        "Generar",
        use_container_width=True,
        disabled=not alguno_elegido,
    )


# ── Área principal ────────────────────────────────────────────────────────────

st.title(f"{jugador_elegido} — {temporada_elegida}")

col_grafico, col_stats = st.columns([3, 1])

if buscar:
    info_jugador = next(j for j in todos_los_jugadores if j["full_name"] == jugador_elegido)
    player_id    = info_jugador["id"]

    with st.spinner("Obteniendo datos..."):
        try:
            tiros   = obtener_tiros(player_id, temporada_elegida, tipo_elegido)
            stats   = calcular_stats(tiros)
            ranking = obtener_ranking(player_id, temporada_elegida, tipo_elegido)
        except ValueError as e:
            st.warning(f"⚠️ {e}")
            st.info("Probá con otra temporada o con 'Regular Season'.")
            st.stop()
        except Exception:
            st.error("❌ Hubo un problema al conectarse con la NBA API. Intentá de nuevo en unos segundos.")
            st.stop()

    resultados = {}

    if quiere_video:
        with st.spinner("🎬 Generando animación (~20 seg)..."):
            ruta_mp4       = os.path.join(tempfile.gettempdir(), "shot_chart.mp4")
            duracion_video = generar_video(tiros, jugador_elegido, ruta_mp4)
            # Las imágenes estáticas siempre se generan junto con el video
            # para mostrarlas automáticamente cuando la animación termina
            rutas_post_video = generar_imagenes(tiros, jugador_elegido, temporada_elegida)
            resultados["video"] = {
                "ruta"        : ruta_mp4,
                "duracion"    : duracion_video,
                "rutas_charts": rutas_post_video,
            }

    if quiere_mapa:
        with st.spinner("📍 Generando mapa de tiros..."):
            # Si el video ya generó las imágenes, las reutilizamos sin regenerar
            rutas_imagenes = (
                resultados["video"]["rutas_charts"]
                if "video" in resultados
                else generar_imagenes(tiros, jugador_elegido, temporada_elegida)
            )
            resultados["mapa"] = rutas_imagenes

    if quiere_hexbin:
        with st.spinner("🔥 Generando hexbin..."):
            ruta_hexbin = generar_hexbin(tiros, jugador_elegido, temporada_elegida)
            resultados["hexbin"] = {"ruta": ruta_hexbin}

    st.session_state.update({
        "resultados"    : resultados,
        "stats"         : stats,
        "ranking"       : ranking,
        "jugador"       : jugador_elegido,
        "temporada"     : temporada_elegida,
        "video_mostrado": False,   # reset al generar
    })


# ── Mostrar resultados ────────────────────────────────────────────────────────

if "resultados" in st.session_state and st.session_state.resultados:
    resultados = st.session_state.resultados

    with col_grafico:
        labels = []
        if "video"  in resultados: labels.append("🎬 Animación")
        if "mapa"   in resultados: labels.append("📍 Mapa de tiros")
        if "hexbin" in resultados: labels.append("🔥 Hexbin")

        tabs    = st.tabs(labels)
        tab_idx = 0

        # ── Tab: Animación ────────────────────────────────────────────────────
        if "video" in resultados:
            with tabs[tab_idx]:
                video_data = resultados["video"]

                if not st.session_state.get("video_mostrado", False):
                    # Primera vez: reproducir el video y esperar que termine
                    with open(video_data["ruta"], "rb") as f:
                        st.video(f.read(), autoplay=True)
                    time.sleep(video_data["duracion"])
                    st.session_state.video_mostrado = True
                    st.rerun()

                else:
                    # Video terminó: mostrar los charts estáticos + botón de replay
                    col_replay, _ = st.columns([1, 3])
                    with col_replay:
                        if st.button("🎬 Ver animación de nuevo", use_container_width=True):
                            st.session_state.video_mostrado = False
                            st.rerun()

                    st.markdown("---")

                    rutas    = video_data["rutas_charts"]
                    col_a, col_b = st.columns(2)

                    with col_a:
                        st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                        st.caption("✅ Tiros convertidos")
                        if st.button("Ver en grande", key="btn_vc", use_container_width=True):
                            ver_imagen_grande(
                                rutas["convertidos"]["ruta"], rutas["convertidos"]["titulo"],
                                st.session_state.jugador, st.session_state.temporada,
                            )
                    with col_b:
                        st.image(rutas["fallados"]["ruta"], use_container_width=True)
                        st.caption("❌ Tiros fallados")
                        if st.button("Ver en grande", key="btn_vf", use_container_width=True):
                            ver_imagen_grande(
                                rutas["fallados"]["ruta"], rutas["fallados"]["titulo"],
                                st.session_state.jugador, st.session_state.temporada,
                            )

                    _, col_c, _ = st.columns([1, 2, 1])
                    with col_c:
                        st.image(rutas["completo"]["ruta"], use_container_width=True)
                        st.caption("⚖️ Vista completa")
                        if st.button("Ver en grande", key="btn_vco", use_container_width=True):
                            ver_imagen_grande(
                                rutas["completo"]["ruta"], rutas["completo"]["titulo"],
                                st.session_state.jugador, st.session_state.temporada,
                            )
            tab_idx += 1

        # ── Tab: Mapa de tiros ────────────────────────────────────────────────
        if "mapa" in resultados:
            with tabs[tab_idx]:
                rutas    = resultados["mapa"]
                col_a, col_b = st.columns(2)

                with col_a:
                    st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                    st.caption("✅ Tiros convertidos")
                    if st.button("Ver en grande", key="btn_convertidos", use_container_width=True):
                        ver_imagen_grande(
                            rutas["convertidos"]["ruta"], rutas["convertidos"]["titulo"],
                            st.session_state.jugador, st.session_state.temporada,
                        )
                with col_b:
                    st.image(rutas["fallados"]["ruta"], use_container_width=True)
                    st.caption("❌ Tiros fallados")
                    if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                        ver_imagen_grande(
                            rutas["fallados"]["ruta"], rutas["fallados"]["titulo"],
                            st.session_state.jugador, st.session_state.temporada,
                        )

                _, col_c, _ = st.columns([1, 2, 1])
                with col_c:
                    st.image(rutas["completo"]["ruta"], use_container_width=True)
                    st.caption("⚖️ Vista completa")
                    if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                        ver_imagen_grande(
                            rutas["completo"]["ruta"], rutas["completo"]["titulo"],
                            st.session_state.jugador, st.session_state.temporada,
                        )
            tab_idx += 1

        # ── Tab: Hexbin ───────────────────────────────────────────────────────
        if "hexbin" in resultados:
            with tabs[tab_idx]:
                ruta_hb = resultados["hexbin"]["ruta"]
                st.image(ruta_hb, use_container_width=True)
                st.caption("Tamaño del hexágono = volumen de tiros · Color = % de tiro (azul frío → rojo caliente)")
                with open(ruta_hb, "rb") as f:
                    st.download_button(
                        label="⬇ Descargar hexbin",
                        data=f,
                        file_name=f"hexbin_{st.session_state.jugador}_{st.session_state.temporada}.png",
                        mime="image/png",
                        use_container_width=True,
                    )

    # ── Panel de estadísticas ─────────────────────────────────────────────────
    with col_stats:
        st.markdown("#### Estadísticas")

        rank_fg   = st.session_state.ranking["rank_fg"]
        rank_fg3  = st.session_state.ranking["rank_fg3"]
        total_fg  = st.session_state.ranking["total_fg"]
        total_fg3 = st.session_state.ranking["total_fg3"]

        st.metric(
            "% de tiro",
            f"{st.session_state.stats['fg_pct']}%",
            f"#{rank_fg} de {total_fg}" if rank_fg else "No califica (< 300 FGM)",
        )
        st.metric(
            "% de triples",
            f"{st.session_state.stats['fg3_pct']}%",
            f"#{rank_fg3} de {total_fg3}" if rank_fg3 else "No califica (< 82 3PM)",
        )
        st.metric("Tiros intentados", st.session_state.stats["intentos"])
        st.metric("Tiros convertidos", st.session_state.stats["metidos"])

else:
    with col_grafico:
        st.info("Elegí un jugador, seleccioná qué visualizaciones querés y presioná Generar.")