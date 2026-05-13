import os
import time
import tempfile
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
from matplotlib.animation import FuncAnimation, FFMpegWriter
from nba_api.stats.static import players
from nba_api.stats.endpoints import shotchartdetail, leaguedashplayerstats


# ── Funciones ────────────────────────────────────────────────────────────────

def dibujar_cancha(ax=None, color_lineas="white", color_cancha="#1a1a2e", lw=1.5):
    if ax is None:
        _, ax = plt.subplots()
    ax.set_facecolor(color_cancha)
    tablero                 = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color_lineas, fill=False)
    aro                     = Circle((0, 0), radius=7.5, linewidth=lw, color=color_lineas, fill=False)
    zona_restringida        = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color_lineas)
    pintura_exterior        = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color_lineas, fill=False)
    pintura_interior        = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color_lineas, fill=False)
    linea_tiro_libre        = Rectangle((-60, 142.5), 120, 0, linewidth=lw, color=color_lineas)
    semicirculo_tl          = Arc((0, 142.5), 120, 120, theta1=0,   theta2=180, linewidth=lw, color=color_lineas)
    semicirculo_tl_inferior = Arc((0, 142.5), 120, 120, theta1=180, theta2=0,   linewidth=lw, color=color_lineas, linestyle='dashed')
    arco_tres               = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color_lineas)
    for patch in [tablero, aro, zona_restringida, pintura_exterior, pintura_interior,
                  linea_tiro_libre, semicirculo_tl, semicirculo_tl_inferior, arco_tres]:
        ax.add_patch(patch)
    ax.plot([-220, -220], [-47.5, 92.5],  linewidth=lw, color=color_lineas)
    ax.plot([ 220,  220], [-47.5, 92.5],  linewidth=lw, color=color_lineas)
    ax.plot([-250,  250], [-47.5, -47.5], linewidth=lw, color=color_lineas)
    ax.plot([-250, -250], [-47.5, 422.5], linewidth=lw, color=color_lineas)
    ax.plot([ 250,  250], [-47.5, 422.5], linewidth=lw, color=color_lineas)
    ax.set_xlim(-260, 260)
    ax.set_ylim(-60, 370)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def obtener_tiros(player_id, temporada="2025-26", tipo="Regular Season"):
    respuesta = shotchartdetail.ShotChartDetail(
        team_id=0,
        player_id=player_id,
        season_nullable=temporada,
        season_type_all_star=tipo,
        context_measure_simple="FGA"
    )
    return respuesta.get_data_frames()[0]


def calcular_stats(df):
    total_intentos = len(df)
    total_metidos  = df["SHOT_MADE_FLAG"].sum()
    tiros_3        = df[df["SHOT_TYPE"] == "3PT Field Goal"]
    intentos_3     = len(tiros_3)
    metidos_3      = tiros_3["SHOT_MADE_FLAG"].sum()
    fg_pct  = round(total_metidos / total_intentos * 100, 1) if total_intentos > 0 else 0
    fg3_pct = round(metidos_3     / intentos_3     * 100, 1) if intentos_3     > 0 else 0
    return {
        "fg_pct"     : fg_pct,
        "fg3_pct"    : fg3_pct,
        "intentos"   : total_intentos,
        "metidos"    : int(total_metidos),
        "intentos_3" : intentos_3,
        "metidos_3"  : int(metidos_3),
    }


def obtener_ranking(player_id, temporada="2025-26", tipo="Regular Season"):
    respuesta = leaguedashplayerstats.LeagueDashPlayerStats(
        season=temporada,
        season_type_all_star=tipo
    )
    df_liga = respuesta.get_data_frames()[0]
    df_liga = df_liga[df_liga["FGA"] * df_liga["GP"] >= 100].copy()
    df_liga["rank_fg"]  = df_liga["FG_PCT"].rank(ascending=False).astype(int)
    df_liga["rank_fg3"] = df_liga["FG3_PCT"].rank(ascending=False).astype(int)
    jugador = df_liga[df_liga["PLAYER_ID"] == player_id]
    if jugador.empty:
        return {"rank_fg": None, "rank_fg3": None, "total_jugadores": len(df_liga)}
    return {
        "rank_fg"         : int(jugador["rank_fg"].values[0]),
        "rank_fg3"        : int(jugador["rank_fg3"].values[0]),
        "total_jugadores" : len(df_liga)
    }


def generar_video(df, nombre_jugador, ruta_salida):
    meses = ["Ene","Feb","Mar","Abr","May","Jun",
             "Jul","Ago","Sep","Oct","Nov","Dic"]

    df_ord = df.sort_values(
        by=["GAME_DATE", "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING"],
        ascending=[True, True, False, False]
    ).reset_index(drop=True)

    partidos     = df_ord["GAME_DATE"].unique()
    fecha_min    = pd.to_datetime(df_ord["GAME_DATE"].min(), format="%Y%m%d")
    temporada    = f"{fecha_min.year}-{str(fecha_min.year + 1)[2:]}" if fecha_min.month >= 9 \
                   else f"{fecha_min.year - 1}-{str(fecha_min.year)[2:]}"

    FPS          = 3
    TRAIL        = 30
    FINAL_FRAMES = 40
    total_frames = len(partidos) + FINAL_FRAMES
    duracion     = total_frames / FPS

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#000000")
    dibujar_cancha(ax, color_lineas="#1a6b3a", color_cancha="#000000")
    ax.set_title(nombre_jugador, color="white", fontsize=16, fontweight="bold", pad=15)
    fecha_text   = ax.text(0, 355, "", color="#888888", fontsize=12, ha="center")
    sc_fal_base  = ax.scatter([], [], c="#ff3333", alpha=0.15, s=8)
    sc_met_base  = ax.scatter([], [], c="#00ff88", alpha=0.15, s=8)
    sc_fal_trail = ax.scatter([], [], c="#ff3333", alpha=0.55, s=14)
    sc_met_trail = ax.scatter([], [], c="#00ff88", alpha=0.55, s=14)
    sc_fal_glow  = ax.scatter([], [], c="#ff3333", alpha=0.12, s=80)
    sc_met_glow  = ax.scatter([], [], c="#00ff88", alpha=0.12, s=80)
    sc_flash     = ax.scatter([], [], c="white",   alpha=0.45, s=25, zorder=5)

    todos = []

    def set_sc(sc, pts):
        sc.set_offsets(np.array(pts) if pts else np.empty((0, 2)))

    def actualizar(frame):
        if frame < len(partidos):
            fecha = partidos[frame]
            for _, t in df_ord[df_ord["GAME_DATE"] == fecha].iterrows():
                todos.append((t["LOC_X"], t["LOC_Y"], t["SHOT_MADE_FLAG"]))
            met       = [(x, y) for x, y, m in todos if m == 1]
            fal       = [(x, y) for x, y, m in todos if m == 0]
            trail_met = [(x, y) for x, y, m in todos[-TRAIL:] if m == 1]
            trail_fal = [(x, y) for x, y, m in todos[-TRAIL:] if m == 0]
            ultimo    = [todos[-1][:2]] if todos else []
            set_sc(sc_met_base,  met)
            set_sc(sc_fal_base,  fal)
            set_sc(sc_met_trail, trail_met)
            set_sc(sc_fal_trail, trail_fal)
            set_sc(sc_met_glow,  trail_met)
            set_sc(sc_fal_glow,  trail_fal)
            set_sc(sc_flash,     ultimo)
            dt = pd.to_datetime(fecha, format="%Y%m%d")
            fecha_text.set_text(f"{meses[dt.month - 1]}  {dt.year}")
        else:
            progreso = (frame - len(partidos)) / FINAL_FRAMES
            if frame == len(partidos):
                set_sc(sc_flash, [])
                fecha_text.set_text(f"Temporada  {temporada}")
            sc_fal_base.set_alpha(  max(0.15 - progreso * 0.13, 0.02) )
            sc_fal_trail.set_alpha( max(0.55 - progreso * 0.55, 0.0)  )
            sc_fal_glow.set_alpha(  max(0.12 - progreso * 0.12, 0.0)  )
            sc_met_trail.set_alpha( max(0.55 - progreso * 0.55, 0.0)  )
            sc_met_glow.set_alpha(  max(0.12 - progreso * 0.12, 0.0)  )
            sc_met_base.set_alpha(  min(0.15 + progreso * 0.65, 0.80) )

        return (sc_met_base, sc_fal_base, sc_met_trail, sc_fal_trail,
                sc_met_glow, sc_fal_glow, sc_flash, fecha_text)

    writer = FFMpegWriter(fps=FPS, bitrate=1800)
    anim   = FuncAnimation(fig, actualizar, frames=total_frames, interval=1000 // FPS, blit=True)
    anim.save(ruta_salida, writer=writer)
    plt.close(fig)
    return duracion


def generar_imagenes(df, nombre_jugador, temporada_elegida):
    """Genera las tres variantes del mapa de tiros y las guarda en disco."""
    metidos  = df[df["SHOT_MADE_FLAG"] == 1]
    fallados = df[df["SHOT_MADE_FLAG"] == 0]

    variantes = [
        {
            "key"       : "convertidos",
            "titulo"    : "Tiros convertidos",
            "met_alpha" : 0.80,
            "fal_alpha" : 0.02,
        },
        {
            "key"       : "fallados",
            "titulo"    : "Tiros fallados",
            "met_alpha" : 0.02,
            "fal_alpha" : 0.80,
        },
        {
            "key"       : "completo",
            "titulo"    : "Vista completa",
            "met_alpha" : 0.50,
            "fal_alpha" : 0.50,
        },
    ]

    rutas = {}
    for v in variantes:
        fig, ax = plt.subplots(figsize=(8, 7))
        fig.patch.set_facecolor("#000000")
        dibujar_cancha(ax, color_lineas="#1a6b3a", color_cancha="#000000")
        ax.scatter(fallados["LOC_X"], fallados["LOC_Y"], c="#ff3333", alpha=v["fal_alpha"], s=8)
        ax.scatter(metidos["LOC_X"],  metidos["LOC_Y"],  c="#00ff88", alpha=v["met_alpha"], s=8)
        ax.set_title(nombre_jugador, color="white", fontsize=16, fontweight="bold", pad=15)
        ax.text(0, 355, f"Temporada  {temporada_elegida}", color="#888888", fontsize=12, ha="center")
        ruta = os.path.join(tempfile.gettempdir(), f"shot_chart_{v['key']}.png")
        fig.savefig(ruta, dpi=100, bbox_inches="tight", facecolor="#000000")
        plt.close(fig)
        rutas[v["key"]] = {"ruta": ruta, "titulo": v["titulo"]}

    return rutas


# ── Modal de imagen ampliada ─────────────────────────────────────────────────

@st.dialog("Mapa de tiros", width="large")
def ver_imagen_grande(ruta, titulo, nombre_jugador, temporada):
    st.markdown(f"#### {titulo} — {nombre_jugador} {temporada}")
    st.image(ruta, use_container_width=True)
    with open(ruta, "rb") as f:
        st.download_button(
            label="⬇ Descargar imagen",
            data=f,
            file_name=f"{nombre_jugador}_{temporada}_{titulo}.png",
            mime="image/png",
            use_container_width=True
        )


# ── Configuración de la página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Mapa de tiros NBA",
    page_icon="🏀",
    layout="wide"
)

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        .stApp { background-color: #0a0a0a; }
        h1, h2, h3, h4 { color: white; }
        video { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏀 Mapa de tiros NBA")
    st.markdown("---")

    todos_los_jugadores = players.get_players()
    nombres             = sorted([j["full_name"] for j in todos_los_jugadores])

    jugador_elegido = st.selectbox(
        "Buscá un jugador",
        options=nombres,
        index=nombres.index("Stephen Curry")
    )

    temporadas = ["2025-26","2024-25","2023-24","2022-23",
                  "2021-22","2020-21","2019-20","2018-19"]

    temporada_elegida = st.selectbox("Temporada", options=temporadas)
    tipo_elegido      = st.selectbox("Tipo", options=["Regular Season", "Playoffs"])
    buscar            = st.button("Generar mapa de tiros", use_container_width=True)

    if buscar:
        st.session_state.video_mostrado = False


# ── Área principal ───────────────────────────────────────────────────────────
st.title(f"{jugador_elegido}  —  {temporada_elegida}")

col_grafico, col_stats = st.columns([3, 1])

if buscar:
    info_jugador = next(j for j in todos_los_jugadores if j["full_name"] == jugador_elegido)
    player_id    = info_jugador["id"]

    with st.spinner("Generando mapa de tiros..."):
        tiros   = obtener_tiros(player_id, temporada_elegida, tipo_elegido)
        stats   = calcular_stats(tiros)
        ranking = obtener_ranking(player_id, temporada_elegida, tipo_elegido)

        ruta_mp4 = os.path.join(tempfile.gettempdir(), "shot_chart.mp4")
        duracion_video = generar_video(tiros, jugador_elegido, ruta_mp4)
        rutas_imagenes = generar_imagenes(tiros, jugador_elegido, temporada_elegida)

        st.session_state.ruta_mp4       = ruta_mp4
        st.session_state.rutas_imagenes = rutas_imagenes
        st.session_state.stats          = stats
        st.session_state.ranking        = ranking
        st.session_state.jugador        = jugador_elegido
        st.session_state.temporada      = temporada_elegida
        st.session_state.duracion_video = duracion_video
        st.session_state.video_mostrado = False

if "rutas_imagenes" in st.session_state:
    with col_grafico:
        st.markdown("#### Mapa de tiros")

        placeholder = st.empty()

        if not st.session_state.video_mostrado:
            with open(st.session_state.ruta_mp4, "rb") as f:
                placeholder.video(f.read(), autoplay=True)
            time.sleep(st.session_state.duracion_video)
            st.session_state.video_mostrado = True
            st.rerun()
        else:
            # Galería de tres imágenes
            rutas = st.session_state.rutas_imagenes

            col_a, col_b = st.columns(2)

            with col_a:
                st.image(rutas["convertidos"]["ruta"], use_container_width=True)
                st.caption("✅ Tiros convertidos")
                if st.button("Ver en grande", key="btn_convertidos", use_container_width=True):
                    ver_imagen_grande(
                        rutas["convertidos"]["ruta"],
                        rutas["convertidos"]["titulo"],
                        st.session_state.jugador,
                        st.session_state.temporada
                    )

            with col_b:
                st.image(rutas["fallados"]["ruta"], use_container_width=True)
                st.caption("❌ Tiros fallados")
                if st.button("Ver en grande", key="btn_fallados", use_container_width=True):
                    ver_imagen_grande(
                        rutas["fallados"]["ruta"],
                        rutas["fallados"]["titulo"],
                        st.session_state.jugador,
                        st.session_state.temporada
                    )

            _, col_c, _ = st.columns([1, 2, 1])
            with col_c:
                st.image(rutas["completo"]["ruta"], use_container_width=True)
                st.caption("⚖️ Vista completa")
                if st.button("Ver en grande", key="btn_completo", use_container_width=True):
                    ver_imagen_grande(
                        rutas["completo"]["ruta"],
                        rutas["completo"]["titulo"],
                        st.session_state.jugador,
                        st.session_state.temporada
                    )

    with col_stats:
        st.markdown("#### Estadísticas")
        st.metric("% de tiro",        f"{st.session_state.stats['fg_pct']}%",
                  f"#{st.session_state.ranking['rank_fg']} en la liga")
        st.metric("% de triples",     f"{st.session_state.stats['fg3_pct']}%",
                  f"#{st.session_state.ranking['rank_fg3']} en la liga")
        st.metric("Tiros intentados",  st.session_state.stats["intentos"])
        st.metric("Tiros convertidos", st.session_state.stats["metidos"])

else:
    with col_grafico:
        st.info("Elegí un jugador y presioná Generar.")
