"""
app.py
------
Interfaz de usuario de la aplicación NBA Shot Chart.

Modos:
    Un jugador  → scatter maps, hexbin, animación por partidos
    Comparar    → mapa lado a lado, hexbin lado a lado, tabla de stats

Opciones de temporada: cualquier temporada desde 1996-97, "Toda la carrera"
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

OPCION_CARRERA = "📅 Toda la carrera"
TIPOS          = ["Regular Season", "Playoffs", "Ambos"]


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


def label_temporada(temporada: str, tipo: str) -> str:
    """Genera la etiqueta corta de temporada para títulos y gráficos."""
    sufijo = {"Playoffs": " PO", "Ambos": " RS+PO"}.get(tipo, "")
    if temporada == OPCION_CARRERA:
        return f"Carrera{sufijo}"
    return f"{temporada}{sufijo}"


def tabla_comparativa_html(
    stats1: dict, stats2: dict,
    panel1: dict, panel2: dict,
    nombre1: str, nombre2: str,
) -> str:
    """Genera HTML de tabla comparativa con stats básicas y avanzadas."""

    def hl(v1, v2, higher=True) -> tuple:
        if v1 is None or v2 is None or v1 == v2:
            return "", ""
        ganador = (v1 > v2) if higher else (v1 < v2)
        return ("mejor", "peor") if ganador else ("peor", "mejor")

    def fmt(v, suffix="") -> str:
        return f"{v}{suffix}" if v is not None else "N/A"

    ts1 = calcular_ts(panel1["pts"], panel1["fga"], panel1["fta"])
    ts2 = calcular_ts(panel2["pts"], panel2["fga"], panel2["fta"])

    ts1_str = f"{ts1*100:.1f}%" if ts1 else "N/A"
    ts2_str = f"{ts2*100:.1f}%" if ts2 else "N/A"

    def fmt_rank(rank, total):
        return f"#{rank} / {total}" if rank else "No califica"

    cls_fg   = hl(panel1["rank_fg"],   panel2["rank_fg"],   higher=False) \
               if panel1["rank_fg"]  and panel2["rank_fg"]  else ("", "")
    cls_fg3  = hl(panel1["rank_fg3"],  panel2["rank_fg3"],  higher=False) \
               if panel1["rank_fg3"] and panel2["rank_fg3"] else ("", "")
    cls_ts   = hl(ts1, ts2)

    rows = [
        # Stats básicas
        ("Partidos jugados",
         fmt(panel1["gp"]), fmt(panel2["gp"]),
         *hl(panel1["gp"], panel2["gp"])),

        ("Min. promedio por partido",
         fmt(panel1["min_pg"]), fmt(panel2["min_pg"]),
         *hl(panel1["min_pg"], panel2["min_pg"])),

        ("Plus / Minus",
         fmt(panel1["plus_minus"]), fmt(panel2["plus_minus"]),
         *hl(panel1["plus_minus"], panel2["plus_minus"])),

        # Shooting
        ("% de tiro (FG%)",
         f"{stats1['fg_pct']}%", f"{stats2['fg_pct']}%",
         *hl(stats1["fg_pct"], stats2["fg_pct"])),

        ("% de triples (3PT%)",
         f"{stats1['fg3_pct']}%", f"{stats2['fg3_pct']}%",
         *hl(stats1["fg3_pct"], stats2["fg3_pct"])),

        # Stat avanzada — TS%
        # El asterisco remite a la nota al pie con la fórmula
        ("TS% ★",
         ts1_str, ts2_str,
         cls_ts[0], cls_ts[1]),

        ("Tiros intentados",
         fmt(stats1["intentos"]), fmt(stats2["intentos"]),
         *hl(stats1["intentos"], stats2["intentos"])),

        ("Tiros convertidos",
         fmt(stats1["metidos"]), fmt(stats2["metidos"]),
         *hl(stats1["metidos"], stats2["metidos"])),

        ("Triples intentados",
         fmt(stats1["intentos_3"]), fmt(stats2["intentos_3"]),
         *hl(stats1["intentos_3"], stats2["intentos_3"])),

        ("Triples convertidos",
         fmt(stats1["metidos_3"]), fmt(stats2["metidos_3"]),
         *hl(stats1["metidos_3"], stats2["metidos_3"])),

        # Rankings
        ("Ranking FG% en liga",
         fmt_rank(panel1["rank_fg"],  panel1["total_fg"]),
         fmt_rank(panel2["rank_fg"],  panel2["total_fg"]),
         cls_fg[0], cls_fg[1]),

        ("Ranking 3PT% en liga",
         fmt_rank(panel1["rank_fg3"], panel1["total_fg3"]),
         fmt_rank(panel2["rank_fg3"], panel2["total_fg3"]),
         cls_fg3[0], cls_fg3[1]),
    ]

    filas = ""
    for metrica, v1, v2, c1, c2 in rows:
        filas += f"""
        <tr>
            <td class="{c1}">{v1}</td>
            <td style="color:#888;font-size:12px;">{metrica}</td>
            <td class="{c2}">{v2}</td>
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
      <tbody>{filas}</tbody>
    </table>
    <p style="color:#666;font-size:11px;margin-top:8px;">
      ★ <b>True Shooting % (TS%)</b> — mide la eficiencia de anotación
      considerando tiros de campo, triples y tiros libres.<br>
      Fórmula: <code>PTS / (2 × (FGA + 0.44 × FTA))</code>.
      Promedio histórico de la NBA: ~56%.
    </p>
    """


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
    temporadas_list = [OPCION_CARRERA] + [f"{y}-{str(y+1)[2:]}" for y in range(año_actual, 1995, -1)]

    if not comparar:
        jugador1   = st.selectbox("Jugador", nombres, index=nombres.index("Stephen Curry"))
        temporada1 = st.selectbox("Temporada", temporadas_list)
        tipo1      = st.selectbox("Tipo", TIPOS)
        jugador2 = temporada2 = tipo2 = None

        # Slider de carrera (solo visible si eligió "Toda la carrera")
        slider_carrera = False
        if temporada1 == OPCION_CARRERA:
            slider_carrera = st.checkbox(
                "Ver temporada por temporada",
                help="Genera el mapa de toda la carrera y luego podés filtrar por temporada."
            )
    else:
        st.markdown("**Jugador 1**")
        jugador1   = st.selectbox("", nombres, index=nombres.index("Stephen Curry"), key="j1")
        temporada1 = st.selectbox("", temporadas_list, key="t1")
        tipo1      = st.selectbox("", TIPOS, key="tp1")
        st.markdown("**Jugador 2**")
        jugador2   = st.selectbox("", nombres, index=nombres.index("Klay Thompson"), key="j2")
        temporada2 = st.selectbox("", temporadas_list, key="t2")
        tipo2      = st.selectbox("", TIPOS, key="tp2")
        slider_carrera = False

    st.markdown("---")

    if not comparar:
        st.markdown("**¿Qué querés generar?**")
        quiere_video  = st.checkbox("🎬 Animación", value=False,
                                    help="~20 seg. Solo disponible para una temporada, no para carrera completa.")
        quiere_mapa   = st.checkbox("📍 Mapa de tiros", value=True)
        quiere_hexbin = st.checkbox("🔥 Hexbin", value=False)

        # La animación no tiene sentido para carrera completa
        if temporada1 == OPCION_CARRERA and quiere_video:
            st.warning("⚠️ La animación no está disponible para toda la carrera.")
            quiere_video = False

        alguno = quiere_video or quiere_mapa or quiere_hexbin
        if not alguno:
            st.warning("Elegí al menos una visualización.")
    else:
        alguno = True

    buscar = st.button("Generar", use_container_width=True, disabled=not alguno)


# ── Título ────────────────────────────────────────────────────────────────────

if comparar:
    lbl1 = label_temporada(temporada1, tipo1)
    lbl2 = label_temporada(temporada2, tipo2)
    st.title(f"{jugador1} ({lbl1})  ⚔️  {jugador2} ({lbl2})")
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
                tiros1, temporadas_con_datos1 = obtener_tiros_carrera(pid1, tipo1)
            else:
                tiros1 = obtener_tiros(pid1, temporada1, tipo1)
                temporadas_con_datos1 = None

            stats1  = calcular_stats(tiros1)
            # Normalizamos: la API recibe "Toda la carrera", no el string con emoji
            temp1_api = "Toda la carrera" if temporada1 == OPCION_CARRERA else temporada1
            panel1    = obtener_stats_panel(pid1, temp1_api, tipo1)

            # Jugador 2 (modo comparar)
            if comparar:
                if temporada2 == OPCION_CARRERA:
                    tiros2, temporadas_con_datos2 = obtener_tiros_carrera(pid2, tipo2)
                else:
                    tiros2 = obtener_tiros(pid2, temporada2, tipo2)
                    temporadas_con_datos2 = None

                stats2    = calcular_stats(tiros2)
                temp2_api = "Toda la carrera" if temporada2 == OPCION_CARRERA else temporada2
                panel2    = obtener_stats_panel(pid2, temp2_api, tipo2)

        except ValueError as e:
            st.warning(f"⚠️ {e}")
            st.info("Probá con otra temporada o tipo.")
            st.stop()
        except Exception as e:
            st.error("❌ Error al conectarse con la NBA API. Intentá de nuevo.")
            st.stop()

    # ── Generación de charts ──────────────────────────────────────────────────
    resultados = {}

    if comparar:
        with st.spinner("📊 Generando comparación..."):
            titulo_comp = f"{jugador1} ({label_temporada(temporada1, tipo1)})  vs  {jugador2} ({label_temporada(temporada2, tipo2)})"
            resultados["comp_mapa"]   = generar_comparacion_mapa(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
            resultados["comp_hexbin"] = generar_comparacion_hexbin(
                tiros1, tiros2, jugador1, jugador2, titulo_comp)
            resultados["comp_stats"]  = True
    else:
        lbl = label_temporada(temporada1, tipo1)
        if quiere_video:
            with st.spinner("🎬 Generando animación (~20 seg)..."):
                ruta_mp4       = os.path.join(tempfile.gettempdir(), "shot_chart.mp4")
                duracion_video = generar_video(tiros1, jugador1, ruta_mp4)
                rutas_post     = generar_imagenes(tiros1, jugador1, lbl)
                resultados["video"] = {"ruta": ruta_mp4, "duracion": duracion_video,
                                       "rutas_charts": rutas_post}
        if quiere_mapa:
            with st.spinner("📍 Generando mapa de tiros..."):
                rutas = (resultados["video"]["rutas_charts"] if "video" in resultados
                         else generar_imagenes(tiros1, jugador1, lbl))
                resultados["mapa"] = rutas
        if quiere_hexbin:
            with st.spinner("🔥 Generando hexbin..."):
                resultados["hexbin"] = {"ruta": generar_hexbin(tiros1, jugador1, lbl)}

    st.session_state.update({
        "resultados"           : resultados,
        "comparar"             : comparar,
        "stats1"               : stats1,
        "panel1"               : panel1,
        "stats2"               : stats2  if comparar else None,
        "panel2"               : panel2  if comparar else None,
        "jugador1"             : jugador1,
        "jugador2"             : jugador2,
        "temporada1"           : temporada1,
        "temporada2"           : temporada2,
        "tipo1"                : tipo1,
        "tipo2"                : tipo2,
        "tiros1"               : tiros1,
        "temporadas_carrera1"  : temporadas_con_datos1,
        "tiros2"               : tiros2 if comparar else None,
        "temporadas_carrera2"  : temporadas_con_datos2 if comparar else None,
        "video_mostrado"       : False,
        "slider_carrera"       : slider_carrera,
    })


# ── Renderizado ───────────────────────────────────────────────────────────────

if "resultados" not in st.session_state or not st.session_state.resultados:
    st.info("Elegí un jugador, seleccioná las visualizaciones y presioná Generar.")
    st.stop()

resultados  = st.session_state.resultados
es_comparar = st.session_state.comparar

# ── MODO COMPARACIÓN ──────────────────────────────────────────────────────────
if es_comparar:
    tab_mapa, tab_hexbin, tab_stats = st.tabs(["📍 Mapa de tiros", "🔥 Hexbin", "📊 Estadísticas"])

    with tab_mapa:
        st.image(resultados["comp_mapa"], use_container_width=True)
        with open(resultados["comp_mapa"], "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_mapa.png", mime="image/png")

    with tab_hexbin:
        st.image(resultados["comp_hexbin"], use_container_width=True)
        st.caption("Escala de tamaño y color unificada — comparación directa.")
        with open(resultados["comp_hexbin"], "rb") as f:
            st.download_button("⬇ Descargar", data=f,
                               file_name="comparacion_hexbin.png", mime="image/png")

    with tab_stats:
        st.markdown("<br>", unsafe_allow_html=True)
        html = tabla_comparativa_html(
            st.session_state.stats1, st.session_state.stats2,
            st.session_state.panel1, st.session_state.panel2,
            st.session_state.jugador1, st.session_state.jugador2,
        )
        st.markdown(html, unsafe_allow_html=True)

# ── MODO UN JUGADOR ───────────────────────────────────────────────────────────
else:
    col_grafico, col_stats = st.columns([3, 1])

    with col_grafico:
        # ── Slider de carrera ─────────────────────────────────────────────────
        temporadas_carrera = st.session_state.get("temporadas_carrera1")
        if st.session_state.get("slider_carrera") and temporadas_carrera:
            temporada_sel = st.select_slider(
                "Temporada",
                options=temporadas_carrera,
                value=temporadas_carrera[-1],
            )
            # Filtramos el DataFrame completo por la temporada elegida
            df_filtrado = st.session_state.tiros1[
                st.session_state.tiros1["TEMPORADA"] == temporada_sel
            ]
            lbl_slider = label_temporada(temporada_sel, st.session_state.tipo1)
            with st.spinner("Regenerando charts..."):
                rutas_slider  = generar_imagenes(df_filtrado, st.session_state.jugador1, lbl_slider)
                hexbin_slider = generar_hexbin(df_filtrado, st.session_state.jugador1, lbl_slider)
            resultados_render = {
                "mapa"  : rutas_slider,
                "hexbin": {"ruta": hexbin_slider},
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
                            ver_imagen_grande(rutas["convertidos"]["ruta"], rutas["convertidos"]["titulo"],
                                              st.session_state.jugador1, st.session_state.temporada1)
                    with col_b:
                        st.image(rutas["fallados"]["ruta"], use_container_width=True)
                        st.caption("❌ Tiros fallados")
                        if st.button("Ver en grande", key="btn_vf", use_container_width=True):
                            ver_imagen_grande(rutas["fallados"]["ruta"], rutas["fallados"]["titulo"],
                                              st.session_state.jugador1, st.session_state.temporada1)
                    _, col_c, _ = st.columns([1, 2, 1])
                    with col_c:
                        st.image(rutas["completo"]["ruta"], use_container_width=True)
                        st.caption("⚖️ Vista completa")
                        if st.button("Ver en grande", key="btn_vco", use_container_width=True):
                            ver_imagen_grande(rutas["completo"]["ruta"], rutas["completo"]["titulo"],
                                              st.session_state.jugador1, st.session_state.temporada1)
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
                        ver_imagen_grande(rutas["convertidos"]["ruta"], rutas["convertidos"]["titulo"],
                                          st.session_state.jugador1, st.session_state.temporada1)
                with col_b:
                    st.image(rutas["fallados"]["ruta"], use_container_width=True)
                    st.caption("❌ Tiros fallados")
                    if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                        ver_imagen_grande(rutas["fallados"]["ruta"], rutas["fallados"]["titulo"],
                                          st.session_state.jugador1, st.session_state.temporada1)
                _, col_c, _ = st.columns([1, 2, 1])
                with col_c:
                    st.image(rutas["completo"]["ruta"], use_container_width=True)
                    st.caption("⚖️ Vista completa")
                    if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                        ver_imagen_grande(rutas["completo"]["ruta"], rutas["completo"]["titulo"],
                                          st.session_state.jugador1, st.session_state.temporada1)
            tab_idx += 1

        # Tab: Hexbin
        if "hexbin" in resultados_render:
            with tabs[tab_idx]:
                ruta_hb = resultados_render["hexbin"]["ruta"]
                st.image(ruta_hb, use_container_width=True)
                st.caption("Tamaño = volumen · Color = FG% (azul frío → rojo caliente)")
                with open(ruta_hb, "rb") as f:
                    st.download_button("⬇ Descargar hexbin", data=f,
                                       file_name=f"hexbin_{st.session_state.jugador1}.png",
                                       mime="image/png", use_container_width=True)

    # ── Panel de estadísticas (un jugador) ────────────────────────────────────
    with col_stats:
        st.markdown("#### Estadísticas")
        s = st.session_state.stats1
        p = st.session_state.panel1
        ts = calcular_ts(p["pts"], p["fga"], p["fta"])

        st.metric("% de tiro",    f"{s['fg_pct']}%",
                  f"#{p['rank_fg']} de {p['total_fg']}"   if p["rank_fg"]  else "No califica (< 300 FGM)")
        st.metric("% de triples", f"{s['fg3_pct']}%",
                  f"#{p['rank_fg3']} de {p['total_fg3']}" if p["rank_fg3"] else "No califica (< 82 3PM)")
        st.metric("TS%", f"{ts*100:.1f}%" if ts else "N/A",
                  help="True Shooting %: eficiencia considerando tiros de campo y libres.\nFórmula: PTS / (2 × (FGA + 0.44 × FTA)). Promedio NBA: ~56%.")
        st.metric("Partidos jugados",  p["gp"])
        st.metric("Min. promedio",     p["min_pg"])
        st.metric("Plus / Minus",      p["plus_minus"])
        st.metric("Tiros intentados",  s["intentos"])
        st.metric("Tiros convertidos", s["metidos"])