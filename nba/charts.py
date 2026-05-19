"""
nba/charts.py
-------------
Visualizaciones del proyecto: cancha, mapas de tiro, video animado y heatmap.

Todas las funciones reciben datos y devuelven figuras o archivos en disco.
No saben nada de Streamlit ni de la NBA API.

Paleta de colores del proyecto:
    Fondo:      #000000
    Cancha:     #000000  (líneas: #1a6b3a)
    Convertido: #00ff88
    Fallado:    #ff3333
"""

import os
import tempfile

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
from matplotlib.animation import FuncAnimation, FFMpegWriter



# ── Cancha ────────────────────────────────────────────────────────────────────

def dibujar_cancha(
    ax=None,
    color_lineas: str = "white",
    color_cancha: str = "#1a1a2e",
    lw: float = 1.5,
):
    """
    Dibuja una media cancha de NBA sobre un Axes de matplotlib.

    Las coordenadas siguen el sistema de la NBA API: el aro está en (0, 0),
    el eje X va de -250 a 250 (décimas de pie) y el eje Y de -47.5 a 422.5.

    Args:
        ax: Axes donde dibujar. Si es None, se crea uno nuevo.
        color_lineas: Color de las líneas de la cancha.
        color_cancha: Color de fondo del área de juego.
        lw: Grosor de las líneas.

    Returns:
        El Axes con la cancha dibujada.
    """
    if ax is None:
        _, ax = plt.subplots()

    ax.set_facecolor(color_cancha)

    # Elementos estructurales
    tablero          = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color_lineas, fill=False)
    aro              = Circle((0, 0), radius=7.5, linewidth=lw, color=color_lineas, fill=False)
    zona_restringida = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color_lineas)
    pintura_exterior = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color_lineas, fill=False)
    pintura_interior = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color_lineas, fill=False)
    linea_tiro_libre = Rectangle((-60, 142.5), 120, 0, linewidth=lw, color=color_lineas)
    semicirculo_tl   = Arc((0, 142.5), 120, 120, theta1=0,   theta2=180, linewidth=lw, color=color_lineas)
    semicirculo_tl_inferior = Arc(
        (0, 142.5), 120, 120, theta1=180, theta2=0,
        linewidth=lw, color=color_lineas, linestyle="dashed",
    )
    arco_tres = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color_lineas)

    for patch in [
        tablero, aro, zona_restringida, pintura_exterior, pintura_interior,
        linea_tiro_libre, semicirculo_tl, semicirculo_tl_inferior, arco_tres,
    ]:
        ax.add_patch(patch)

    # Líneas rectas: esquinas del triple y perímetro
    ax.plot([-220, -220], [-47.5,  92.5], linewidth=lw, color=color_lineas)
    ax.plot([ 220,  220], [-47.5,  92.5], linewidth=lw, color=color_lineas)
    ax.plot([-250,  250], [-47.5, -47.5], linewidth=lw, color=color_lineas)
    ax.plot([-250, -250], [-47.5, 422.5], linewidth=lw, color=color_lineas)
    ax.plot([ 250,  250], [-47.5, 422.5], linewidth=lw, color=color_lineas)

    ax.set_xlim(-260, 260)
    ax.set_ylim(-60, 370)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


# ── Mapas de tiro estáticos ───────────────────────────────────────────────────

def generar_imagenes(
    df: pd.DataFrame,
    nombre_jugador: str,
    temporada_elegida: str,
) -> dict:
    """
    Genera tres variantes del mapa de tiros estático y las guarda en disco.

    Variantes:
        convertidos - Solo tiros metidos (fallados casi invisibles).
        fallados    - Solo tiros fallados (metidos casi invisibles).
        completo    - Ambos con igual peso visual.

    Args:
        df: DataFrame con los tiros del jugador (resultado de api.obtener_tiros).
        nombre_jugador: Nombre para el título.
        temporada_elegida: Etiqueta de temporada para el subtítulo.

    Returns:
        dict con claves "convertidos", "fallados" y "completo", cada una
        conteniendo {"ruta": str, "titulo": str}.
    """
    metidos  = df[df["SHOT_MADE_FLAG"] == 1]
    fallados = df[df["SHOT_MADE_FLAG"] == 0]

    variantes = [
        {"key": "convertidos", "titulo": "Tiros convertidos", "met_alpha": 0.80, "fal_alpha": 0.02},
        {"key": "fallados",    "titulo": "Tiros fallados",    "met_alpha": 0.02, "fal_alpha": 0.80},
        {"key": "completo",    "titulo": "Vista completa",    "met_alpha": 0.50, "fal_alpha": 0.50},
    ]

    rutas = {}
    for v in variantes:
        fig, ax = plt.subplots(figsize=(8, 7))
        fig.patch.set_facecolor("#000000")
        dibujar_cancha(ax, color_lineas="#1a6b3a", color_cancha="#000000")

        ax.scatter(fallados["LOC_X"], fallados["LOC_Y"],
                   c="#ff3333", alpha=v["fal_alpha"], s=8)
        ax.scatter(metidos["LOC_X"],  metidos["LOC_Y"],
                   c="#00ff88", alpha=v["met_alpha"], s=8)

        ax.set_title(nombre_jugador, color="white", fontsize=16, fontweight="bold", pad=15)
        ax.text(0, 355, f"Temporada {temporada_elegida}",
                color="#888888", fontsize=12, ha="center")

        ruta = os.path.join(tempfile.gettempdir(), f"shot_chart_{v['key']}.png")
        fig.savefig(ruta, dpi=100, bbox_inches="tight", facecolor="#000000")
        plt.close(fig)

        rutas[v["key"]] = {"ruta": ruta, "titulo": v["titulo"]}

    return rutas


# ── Hexbin: tamaño = volumen, color = eficiencia ─────────────────────────────

def generar_hexbin(
    df: pd.DataFrame,
    nombre_jugador: str,
    temporada_elegida: str,
    gridsize: int = 25,
    min_intentos: int = 3,
) -> str:
    """
    Genera un hexbin chart y lo guarda en disco.

    Cada hexágono codifica dos dimensiones simultáneamente:
        - Tamaño   → volumen de tiros en esa zona (más grande = más intentos).
        - Color    → eficiencia (% de tiro). Escala relativa a la liga: azul = frío,
                     blanco = promedio (~46%), rojo = caliente.

    Esta es la visualización estándar en la industria NBA analytics
    (Kirk Goldsberry, The Athletic, equipos de la liga).

    Técnica:
        1. matplotlib hexbin agrupa los tiros en celdas hexagonales y cuenta intentos.
        2. Para cada hex calculamos FG% = convertidos / intentos (si intentos >= min_intentos).
        3. Redibujamos los hexágonos escalando su tamaño por volumen y coloreándolos por FG%.

    Args:
        df: DataFrame con los tiros (resultado de api.obtener_tiros).
        nombre_jugador: Nombre para el título.
        temporada_elegida: Etiqueta de temporada para el subtítulo.
        gridsize: Cantidad de hexágonos por eje. 25 es el balance estándar.
        min_intentos: Mínimo de intentos para dibujar un hexágono.
                      Evita hexágonos de 1 tiro con 100% que distorsionan la escala.

    Returns:
        Ruta en disco del archivo PNG generado.
    """
    # Promedio histórico de FG% en la NBA (punto neutro de la escala de color)
    LIGA_FG_PCT = 0.46

    x = df["LOC_X"].values
    y = df["LOC_Y"].values
    made = df["SHOT_MADE_FLAG"].values

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#000000")
    dibujar_cancha(ax, color_lineas="#555555", color_cancha="#000000", lw=1.2)

    # ── Paso 1: hexbin oculto para obtener la grilla y los centros ────────────
    # Usamos hexbin solo para que matplotlib calcule dónde cae cada tiro.
    # Lo dibujamos invisible (alpha=0) porque después lo redibujamos a mano.
    hb = ax.hexbin(
        x, y,
        gridsize=gridsize,
        extent=(-250, 250, -47.5, 422.5),
        alpha=0,          # invisible — solo nos importan los offsets
    )
    plt.close("all")

    # ── Paso 2: calcular FG% y volumen por hexágono ───────────────────────────
    # offsets: coordenadas (x, y) del centro de cada hexágono
    offsets  = hb.get_offsets()
    conteos  = hb.get_array()          # cantidad de tiros por hex (del hexbin)

    fg_pcts  = np.full(len(offsets), np.nan)
    volumenes = np.zeros(len(offsets))

    # Para cada tiro, buscamos a qué hexágono pertenece usando distancia mínima
    for i, (hx, hy) in enumerate(offsets):
        if conteos[i] < min_intentos:
            continue
        # Máscara: tiros que el hexbin asignó a este hex
        # Usamos una ventana de proximidad basada en el tamaño del hex
        radio = 250 / gridsize * 1.5
        mask  = (np.abs(x - hx) < radio) & (np.abs(y - hy) < radio)
        if mask.sum() < min_intentos:
            continue
        fg_pcts[i]   = made[mask].mean()
        volumenes[i] = mask.sum()

    # ── Paso 3: escalar tamaños y normalizar colores ──────────────────────────
    vol_max  = volumenes.max() if volumenes.max() > 0 else 1
    # Tamaño de marcador: entre 20 (poco volumen) y 300 (máximo volumen)
    sizes = np.where(
        volumenes >= min_intentos,
        20 + (volumenes / vol_max) * 280,
        0,   # hexágonos sin suficientes tiros: tamaño 0 (invisibles)
    )

    # Colormap divergente: azul (frío) → blanco (promedio liga) → rojo (caliente)
    cmap = plt.cm.RdYlBu_r
    # Normalizamos respecto al promedio de la liga para que blanco = ~liga
    vmin, vmax = LIGA_FG_PCT - 0.20, LIGA_FG_PCT + 0.20  # ±20% alrededor del promedio

    # ── Paso 4: redibujar los hexágonos a mano ────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#000000")
    dibujar_cancha(ax, color_lineas="#555555", color_cancha="#000000", lw=1.2)

    sc = ax.scatter(
        offsets[:, 0], offsets[:, 1],
        s=sizes,
        c=fg_pcts,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        marker="h",        # "h" = hexágono en matplotlib
        linewidths=0.3,
        edgecolors="#222222",
        alpha=0.90,
        zorder=2,
    )

    # ── Colorbar ──────────────────────────────────────────────────────────────
    cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("% de tiro", color="white", fontsize=11)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.set_ticks([vmin, LIGA_FG_PCT, vmax])
    cbar.set_ticklabels([
        f"{int(vmin*100)}% (frío)",
        f"{int(LIGA_FG_PCT*100)}% (liga)",
        f"{int(vmax*100)}% (caliente)",
    ])

    # ── Leyenda de tamaño ─────────────────────────────────────────────────────
    # Muestra que el tamaño del hex = volumen de tiros
    for vol, label in [(0.25, "Bajo"), (0.60, "Medio"), (1.0, "Alto")]:
        ax.scatter([], [], s=20 + vol * 280, c="white", alpha=0.6,
                   marker="h", label=label)
    legend = ax.legend(
        title="Volumen", title_fontsize=9, fontsize=8,
        loc="lower right", framealpha=0.15,
        labelcolor="white", facecolor="#111111",
    )
    legend.get_title().set_color("white")

    ax.set_title(nombre_jugador, color="white", fontsize=16, fontweight="bold", pad=15)
    ax.text(0, 355, f"Eficiencia y volumen de tiro — {temporada_elegida}",
            color="#888888", fontsize=12, ha="center")

    ruta = os.path.join(tempfile.gettempdir(), "hexbin.png")
    fig.savefig(ruta, dpi=120, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    return ruta


# ── Video animado ─────────────────────────────────────────────────────────────

def generar_video(df: pd.DataFrame, nombre_jugador: str, ruta_salida: str) -> float:
    """
    Genera un video MP4 animado que muestra los tiros partido a partido.

    La animación acumula los tiros a lo largo de la temporada, mostrando un
    "trail" de los últimos tiros y un flash en el tiro más reciente.
    Al final, los tiros fallados se desvanecen y quedan solo los convertidos.

    Args:
        df: DataFrame con los tiros del jugador (resultado de api.obtener_tiros).
        nombre_jugador: Nombre a mostrar en el título del video.
        ruta_salida: Ruta completa donde guardar el archivo .mp4.

    Returns:
        Duración del video en segundos (para sincronizar la UI de Streamlit).
    """
    MESES        = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    FPS          = 3
    TRAIL        = 30   # Tiros recientes con mayor opacidad
    FINAL_FRAMES = 40   # Frames de la animación de cierre

    df_ord = df.sort_values(
        by=["GAME_DATE", "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING"],
        ascending=[True, True, False, False],
    ).reset_index(drop=True)

    partidos  = df_ord["GAME_DATE"].unique()
    fecha_min = pd.to_datetime(df_ord["GAME_DATE"].min(), format="%Y%m%d")
    temporada = (
        f"{fecha_min.year}-{str(fecha_min.year + 1)[2:]}"
        if fecha_min.month >= 9
        else f"{fecha_min.year - 1}-{str(fecha_min.year)[2:]}"
    )

    total_frames = len(partidos) + FINAL_FRAMES
    duracion     = total_frames / FPS

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#000000")
    dibujar_cancha(ax, color_lineas="#1a6b3a", color_cancha="#000000")
    ax.set_title(nombre_jugador, color="white", fontsize=16, fontweight="bold", pad=15)
    fecha_text = ax.text(0, 355, "", color="#888888", fontsize=12, ha="center")

    sc_fal_base  = ax.scatter([], [], c="#ff3333", alpha=0.15, s=8)
    sc_met_base  = ax.scatter([], [], c="#00ff88", alpha=0.15, s=8)
    sc_fal_trail = ax.scatter([], [], c="#ff3333", alpha=0.55, s=14)
    sc_met_trail = ax.scatter([], [], c="#00ff88", alpha=0.55, s=14)
    sc_fal_glow  = ax.scatter([], [], c="#ff3333", alpha=0.12, s=80)
    sc_met_glow  = ax.scatter([], [], c="#00ff88", alpha=0.12, s=80)
    sc_flash     = ax.scatter([], [], c="white",   alpha=0.45, s=25, zorder=5)

    todos: list[tuple] = []

    def _set(sc, pts: list) -> None:
        sc.set_offsets(np.array(pts) if pts else np.empty((0, 2)))

    def actualizar(frame: int):
        if frame < len(partidos):
            fecha = partidos[frame]
            for _, t in df_ord[df_ord["GAME_DATE"] == fecha].iterrows():
                todos.append((t["LOC_X"], t["LOC_Y"], t["SHOT_MADE_FLAG"]))

            met       = [(x, y) for x, y, m in todos          if m == 1]
            fal       = [(x, y) for x, y, m in todos          if m == 0]
            trail_met = [(x, y) for x, y, m in todos[-TRAIL:] if m == 1]
            trail_fal = [(x, y) for x, y, m in todos[-TRAIL:] if m == 0]
            ultimo    = [todos[-1][:2]] if todos else []

            _set(sc_met_base,  met);  _set(sc_fal_base,  fal)
            _set(sc_met_trail, trail_met); _set(sc_fal_trail, trail_fal)
            _set(sc_met_glow,  trail_met); _set(sc_fal_glow,  trail_fal)
            _set(sc_flash, ultimo)

            dt = pd.to_datetime(fecha, format="%Y%m%d")
            fecha_text.set_text(f"{MESES[dt.month - 1]} {dt.year}")

        else:
            progreso = (frame - len(partidos)) / FINAL_FRAMES
            if frame == len(partidos):
                _set(sc_flash, [])
                fecha_text.set_text(f"Temporada {temporada}")

            sc_fal_base.set_alpha( max(0.15 - progreso * 0.13, 0.02))
            sc_fal_trail.set_alpha(max(0.55 - progreso * 0.55, 0.00))
            sc_fal_glow.set_alpha( max(0.12 - progreso * 0.12, 0.00))
            sc_met_trail.set_alpha(max(0.55 - progreso * 0.55, 0.00))
            sc_met_glow.set_alpha( max(0.12 - progreso * 0.12, 0.00))
            sc_met_base.set_alpha( min(0.15 + progreso * 0.65, 0.80))

        return (sc_met_base, sc_fal_base, sc_met_trail, sc_fal_trail,
                sc_met_glow, sc_fal_glow, sc_flash, fecha_text)

    writer = FFMpegWriter(fps=FPS, bitrate=1800)
    anim   = FuncAnimation(fig, actualizar, frames=total_frames,
                           interval=1000 // FPS, blit=True)
    anim.save(ruta_salida, writer=writer)
    plt.close(fig)
    return duracion


# ── Comparador: mapa de tiros lado a lado ─────────────────────────────────────

def generar_comparacion_mapa(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    nombre1: str,
    nombre2: str,
    temporada: str,
) -> str:
    """
    Genera un mapa de tiros comparativo con dos canchas lado a lado.

    Muestra la vista completa (convertidos + fallados) de cada jugador
    en la misma figura para facilitar la comparación visual directa.

    Args:
        df1: DataFrame de tiros del jugador 1.
        df2: DataFrame de tiros del jugador 2.
        nombre1: Nombre del jugador 1 (título cancha izquierda).
        nombre2: Nombre del jugador 2 (título cancha derecha).
        temporada: Etiqueta de temporada para el subtítulo.

    Returns:
        Ruta en disco del archivo PNG generado.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#000000")
    fig.suptitle(f"{nombre1}  vs  {nombre2} — {temporada}",
                 color="white", fontsize=16, fontweight="bold", y=1.01)

    for ax, df, nombre in [(ax1, df1, nombre1), (ax2, df2, nombre2)]:
        dibujar_cancha(ax, color_lineas="#1a6b3a", color_cancha="#000000")

        metidos  = df[df["SHOT_MADE_FLAG"] == 1]
        fallados = df[df["SHOT_MADE_FLAG"] == 0]

        ax.scatter(fallados["LOC_X"], fallados["LOC_Y"],
                   c="#ff3333", alpha=0.45, s=8)
        ax.scatter(metidos["LOC_X"],  metidos["LOC_Y"],
                   c="#00ff88", alpha=0.45, s=8)

        ax.set_title(nombre, color="white", fontsize=13, fontweight="bold", pad=10)

    fig.text(0.5, -0.02, "🟢 Convertidos   🔴 Fallados",
             color="#888888", fontsize=11, ha="center")

    plt.tight_layout()
    ruta = os.path.join(tempfile.gettempdir(), "comparacion_mapa.png")
    fig.savefig(ruta, dpi=110, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    return ruta


# ── Comparador: hexbin lado a lado ────────────────────────────────────────────

def generar_comparacion_hexbin(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    nombre1: str,
    nombre2: str,
    temporada: str,
    gridsize: int = 25,
    min_intentos: int = 3,
) -> str:
    """
    Genera un hexbin comparativo con dos canchas lado a lado.

    Usa la misma escala de color en ambas canchas (vmin/vmax fijos) para que
    la comparación visual sea justa: el mismo tono de rojo significa el mismo
    FG% en los dos jugadores.

    Args:
        df1: DataFrame de tiros del jugador 1.
        df2: DataFrame de tiros del jugador 2.
        nombre1: Nombre del jugador 1.
        nombre2: Nombre del jugador 2.
        temporada: Etiqueta de temporada.
        gridsize: Hexágonos por eje.
        min_intentos: Mínimo de tiros por hexágono para dibujarlo.

    Returns:
        Ruta en disco del archivo PNG generado.
    """
    LIGA_FG_PCT = 0.46
    vmin, vmax  = LIGA_FG_PCT - 0.20, LIGA_FG_PCT + 0.20
    cmap        = plt.cm.RdYlBu_r

    def _calcular_hexbin(df: pd.DataFrame, ax) -> tuple:
        """Calcula offsets, FG% y volumen por hexágono para un DataFrame dado."""
        x    = df["LOC_X"].values
        y    = df["LOC_Y"].values
        made = df["SHOT_MADE_FLAG"].values

        hb = ax.hexbin(x, y, gridsize=gridsize,
                       extent=(-250, 250, -47.5, 422.5), alpha=0)
        plt.close("all")

        offsets  = hb.get_offsets()
        conteos  = hb.get_array()
        fg_pcts  = np.full(len(offsets), np.nan)
        volumenes = np.zeros(len(offsets))
        radio     = 250 / gridsize * 1.5

        for i, (hx, hy) in enumerate(offsets):
            if conteos[i] < min_intentos:
                continue
            mask = (np.abs(x - hx) < radio) & (np.abs(y - hy) < radio)
            if mask.sum() < min_intentos:
                continue
            fg_pcts[i]    = made[mask].mean()
            volumenes[i]  = mask.sum()

        return offsets, fg_pcts, volumenes

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor("#000000")
    fig.suptitle(f"{nombre1}  vs  {nombre2} — {temporada}",
                 color="white", fontsize=16, fontweight="bold", y=1.01)

    sc_last = None
    vol_global_max = 1

    # Primera pasada: calcular el volumen máximo global para escalar igual en ambas canchas
    datos_ambos = []
    for df, ax in [(df1, ax1), (df2, ax2)]:
        offsets, fg_pcts, volumenes = _calcular_hexbin(df, ax)
        datos_ambos.append((offsets, fg_pcts, volumenes))
        if volumenes.max() > vol_global_max:
            vol_global_max = volumenes.max()

    # Segunda pasada: dibujar con la misma escala
    for (offsets, fg_pcts, volumenes), ax, nombre in zip(
        datos_ambos, (ax1, ax2), (nombre1, nombre2)
    ):
        dibujar_cancha(ax, color_lineas="#555555", color_cancha="#000000", lw=1.2)

        sizes = np.where(
            volumenes >= min_intentos,
            20 + (volumenes / vol_global_max) * 280,
            0,
        )
        sc_last = ax.scatter(
            offsets[:, 0], offsets[:, 1],
            s=sizes, c=fg_pcts,
            cmap=cmap, vmin=vmin, vmax=vmax,
            marker="h", linewidths=0.3,
            edgecolors="#222222", alpha=0.90, zorder=2,
        )
        ax.set_title(nombre, color="white", fontsize=13, fontweight="bold", pad=10)

    # Colorbar compartida (una sola para los dos, misma escala)
    cbar = fig.colorbar(sc_last, ax=[ax1, ax2], fraction=0.02, pad=0.02)
    cbar.set_label("% de tiro", color="white", fontsize=11)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.set_ticks([vmin, LIGA_FG_PCT, vmax])
    cbar.set_ticklabels([
        f"{int(vmin*100)}% (frío)",
        f"{int(LIGA_FG_PCT*100)}% (liga)",
        f"{int(vmax*100)}% (caliente)",
    ])

    fig.text(0.5, -0.02, "Tamaño = volumen de tiros · Escala de tamaño y color unificada entre jugadores",
             color="#888888", fontsize=10, ha="center")

    plt.tight_layout()
    ruta = os.path.join(tempfile.gettempdir(), "comparacion_hexbin.png")
    fig.savefig(ruta, dpi=110, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    return ruta