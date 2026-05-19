"""
nba/api.py
----------
Comunicación con la NBA Stats API.

Toda llamada al mundo exterior vive acá. Si la API cambia (endpoints,
parámetros, formato de respuesta), este es el único archivo que hay que tocar.

Funciones públicas:
    obtener_tiros()         - Tiros de una temporada (soporta tipo="Ambos")
    obtener_tiros_carrera() - Tiros de toda la carrera, ignora temporadas sin datos
    obtener_stats_panel()   - Stats completas: rankings, GP, MIN, +/-, PTS, FTA
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from nba_api.stats.endpoints import (
    shotchartdetail,
    leaguedashplayerstats,
    commonplayerinfo,
    playercareerstats,
)


# Mínimos oficiales de la NBA para calificar en rankings de porcentaje.
# Fuente: https://www.nba.com/stats/help/statminimums
MIN_FGM  = 300  # Field goals convertidos para calificar en FG%
MIN_FG3M = 82   # Triples convertidos para calificar en 3PT%

# La NBA API tiene datos de shot chart desde la temporada 1996-97
PRIMERA_TEMPORADA_DISPONIBLE = 1996


# ── Funciones internas (sin caché) ────────────────────────────────────────────

def _fetch_tiros(player_id: int, temporada: str, tipo: str) -> pd.DataFrame:
    """
    Llama a ShotChartDetail y devuelve el DataFrame crudo.

    Función interna sin caché — permite que obtener_tiros_carrera la llame
    en un loop sin romper el mecanismo de caché de Streamlit.

    Raises:
        ValueError: Si no hay datos para esa combinación.
    """
    respuesta = shotchartdetail.ShotChartDetail(
        team_id=0,
        player_id=player_id,
        season_nullable=temporada,
        season_type_all_star=tipo,
        context_measure_simple="FGA",
    )
    df = respuesta.get_data_frames()[0]
    if df.empty:
        raise ValueError(f"Sin datos: jugador {player_id}, {temporada}, {tipo}.")
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def _obtener_debut(player_id: int) -> int:
    """
    Retorna el año de debut del jugador en la NBA.

    Cachea por 24 horas — esta info no cambia nunca para un jugador retirado
    y cambia a lo sumo una vez por año para un jugador activo.
    """
    info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
    df   = info.get_data_frames()[0]
    return int(df["FROM_YEAR"].values[0])


# ── Funciones públicas ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_tiros(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> pd.DataFrame:
    """
    Obtiene el registro de tiros de un jugador en una temporada.

    Args:
        player_id: ID del jugador en la NBA API.
        temporada: Formato "YYYY-YY" (p. ej. "2024-25").
        tipo: "Regular Season", "Playoffs" o "Ambos".
              "Ambos" concatena Regular Season + Playoffs de esa temporada.

    Returns:
        DataFrame con una fila por tiro. Columnas clave:
            LOC_X, LOC_Y       - Coordenadas (décimas de pie, aro en origen).
            SHOT_MADE_FLAG     - 1 convertido, 0 fallado.
            SHOT_TYPE          - "2PT Field Goal" o "3PT Field Goal".
            GAME_DATE          - Fecha en formato "YYYYMMDD".
            PERIOD             - Cuarto del partido.

    Raises:
        ValueError: Si no hay datos para la combinación pedida.
    """
    if tipo == "Ambos":
        dfs = []
        for t in ["Regular Season", "Playoffs"]:
            try:
                df = _fetch_tiros(player_id, temporada, t)
                df = df.copy()
                df["TIPO"] = t
                dfs.append(df)
            except ValueError:
                pass   # Sin playoffs ese año → lo ignoramos silenciosamente
        if not dfs:
            raise ValueError(
                f"No se encontraron tiros para el jugador {player_id} "
                f"en la temporada {temporada} (Regular Season ni Playoffs)."
            )
        return pd.concat(dfs, ignore_index=True)

    return _fetch_tiros(player_id, temporada, tipo)


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_tiros_carrera(
    player_id: int,
    tipo: str = "Regular Season",
) -> tuple:
    """
    Obtiene todos los tiros de la carrera de un jugador.

    Itera desde el año de debut hasta la temporada actual. Las temporadas
    anteriores a 1996-97 (límite de la API) se saltan automáticamente.
    Las temporadas sin datos (lesiones, temporadas fuera de la NBA) se
    ignoran silenciosamente sin lanzar error.

    Args:
        player_id: ID del jugador en la NBA API.
        tipo: "Regular Season", "Playoffs" o "Ambos".

    Returns:
        Tuple (df, temporadas_con_datos) donde:
            df                  - DataFrame con todos los tiros concatenados.
                                  Incluye columna "TEMPORADA" para filtrar.
            temporadas_con_datos - Lista ordenada de temporadas con datos
                                   (p. ej. ["2009-10", "2010-11", ...]).

    Raises:
        ValueError: Si no se encontró ningún tiro en toda la carrera.
    """
    hoy          = datetime.now()
    año_actual   = hoy.year if hoy.month >= 9 else hoy.year - 1
    año_debut    = max(_obtener_debut(player_id), PRIMERA_TEMPORADA_DISPONIBLE)
    tipos_a_pedir = ["Regular Season", "Playoffs"] if tipo == "Ambos" else [tipo]

    dfs: list[pd.DataFrame] = []
    temporadas_con_datos: list[str] = []

    for año in range(año_debut, año_actual + 1):
        temporada = f"{año}-{str(año + 1)[2:]}"
        temporada_tiene_datos = False

        for t in tipos_a_pedir:
            try:
                df = _fetch_tiros(player_id, temporada, t)
                df = df.copy()
                df["TEMPORADA"] = temporada
                df["TIPO"]      = t
                dfs.append(df)
                temporada_tiene_datos = True
            except ValueError:
                pass   # Sin datos ese año/tipo → seguimos

        if temporada_tiene_datos and temporada not in temporadas_con_datos:
            temporadas_con_datos.append(temporada)

    if not dfs:
        raise ValueError(
            f"No se encontraron tiros en ninguna temporada del jugador {player_id}."
        )

    return pd.concat(dfs, ignore_index=True), temporadas_con_datos


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_panel(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> dict:
    """
    Obtiene estadísticas completas de un jugador para el panel de comparación.

    Combina datos de leaguedashplayerstats (para rankings y stats de temporada)
    con los mínimos oficiales de la NBA para FG% y 3PT%.

    Para tipo="Ambos" promedia las stats de Regular Season y Playoffs.
    Para tipo="Toda la carrera" usa playercareerstats (totales históricos).

    Args:
        player_id: ID del jugador.
        temporada: Formato "YYYY-YY" o "Toda la carrera".
        tipo: "Regular Season", "Playoffs" o "Ambos".

    Returns:
        dict con:
            rank_fg, rank_fg3, total_fg, total_fg3  - Rankings (None si no califica).
            gp       - Partidos jugados.
            min_pg   - Minutos promedio por partido.
            plus_minus - Plus/Minus total de la temporada.
            pts      - Puntos totales.
            fga      - Intentos de tiro de campo.
            fta      - Intentos de tiro libre.
    """
    # ── Carrera completa: usamos playercareerstats ─────────────────────────────
    if temporada == "Toda la carrera":
        carrera = playercareerstats.PlayerCareerStats(player_id=player_id)
        tipos_df = {
            "Regular Season": carrera.get_data_frames()[0],  # SeasonTotalsRegularSeason
            "Playoffs"       : carrera.get_data_frames()[2],  # SeasonTotalsPostSeason
        }
        tipos_usar = ["Regular Season", "Playoffs"] if tipo == "Ambos" else [tipo]
        gp = pts = fga = fta = plus_minus = min_total = 0
        for t in tipos_usar:
            df_t = tipos_df[t]
            if df_t.empty:
                continue
            gp         += int(df_t["GP"].sum())
            pts        += int(df_t["PTS"].sum())
            fga        += int(df_t["FGA"].sum())
            fta        += int(df_t["FTA"].sum())
            plus_minus += float(df_t["PLUS_MINUS"].sum()) if "PLUS_MINUS" in df_t.columns else 0
            min_total  += float(df_t["MIN"].sum())

        min_pg = round(min_total / gp, 1) if gp > 0 else 0
        return {
            "rank_fg": None, "rank_fg3": None,
            "total_fg": None, "total_fg3": None,
            "gp": gp, "min_pg": min_pg,
            "plus_minus": round(plus_minus, 1),
            "pts": pts, "fga": fga, "fta": fta,
        }

    # ── Temporada específica ──────────────────────────────────────────────────
    tipos_usar = ["Regular Season", "Playoffs"] if tipo == "Ambos" else [tipo]
    gp = pts = fga = fta = plus_minus_total = min_total = 0

    # Para rankings solo usamos el tipo principal (los rankings no aplican a "Ambos")
    tipo_ranking = "Regular Season" if tipo == "Ambos" else tipo

    respuesta = leaguedashplayerstats.LeagueDashPlayerStats(
        season=temporada,
        season_type_all_star=tipo_ranking,
    )
    df_liga = respuesta.get_data_frames()[0]

    # Rankings con mínimos oficiales
    cal_fg  = df_liga[df_liga["FGM"]  >= MIN_FGM].copy()
    cal_fg3 = df_liga[df_liga["FG3M"] >= MIN_FG3M].copy()
    cal_fg["rank_fg"]   = cal_fg["FG_PCT"].rank(ascending=False).astype(int)
    cal_fg3["rank_fg3"] = cal_fg3["FG3_PCT"].rank(ascending=False).astype(int)
    jug_fg  = cal_fg[cal_fg["PLAYER_ID"]   == player_id]
    jug_fg3 = cal_fg3[cal_fg3["PLAYER_ID"] == player_id]

    rank_fg   = int(jug_fg["rank_fg"].values[0])   if not jug_fg.empty  else None
    rank_fg3  = int(jug_fg3["rank_fg3"].values[0]) if not jug_fg3.empty else None
    total_fg  = len(cal_fg)
    total_fg3 = len(cal_fg3)

    # Stats del jugador (sumamos si tipo="Ambos")
    for t in tipos_usar:
        if t != tipo_ranking:
            r2 = leaguedashplayerstats.LeagueDashPlayerStats(
                season=temporada, season_type_all_star=t)
            df2 = r2.get_data_frames()[0]
        else:
            df2 = df_liga

        jug = df2[df2["PLAYER_ID"] == player_id]
        if jug.empty:
            continue
        gp             += int(jug["GP"].values[0])
        pts            += int(jug["PTS"].values[0])
        fga            += int(jug["FGA"].values[0])
        fta            += int(jug["FTA"].values[0])
        plus_minus_total += float(jug["PLUS_MINUS"].values[0])
        min_total      += float(jug["MIN"].values[0])

    min_pg = round(min_total / gp, 1) if gp > 0 else 0

    return {
        "rank_fg"   : rank_fg,
        "rank_fg3"  : rank_fg3,
        "total_fg"  : total_fg,
        "total_fg3" : total_fg3,
        "gp"        : gp,
        "min_pg"    : min_pg,
        "plus_minus": round(plus_minus_total, 1),
        "pts"       : pts,
        "fga"       : fga,
        "fta"       : fta,
    }


# Alias para compatibilidad con el código existente
def obtener_ranking(player_id: int, temporada: str, tipo: str) -> dict:
    """
    Alias de obtener_stats_panel() que devuelve solo los campos de ranking.
    Mantiene compatibilidad con el código anterior que usaba obtener_ranking().
    """
    stats = obtener_stats_panel(player_id, temporada, tipo)
    return {
        "rank_fg"  : stats["rank_fg"],
        "rank_fg3" : stats["rank_fg3"],
        "total_fg" : stats["total_fg"],
        "total_fg3": stats["total_fg3"],
    }