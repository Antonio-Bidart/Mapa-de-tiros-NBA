"""
nba/api.py
----------
Comunicación con la NBA Stats API.

Toda llamada al mundo exterior vive acá. Si la API cambia (endpoints,
parámetros, formato de respuesta), este es el único archivo que hay que tocar.

Usa @st.cache_data para evitar llamadas repetidas dentro de la misma sesión.
El TTL de 1 hora es razonable: los datos de tiros de una temporada pasada
no cambian, y los de la temporada actual cambian cada día de partido.
"""

import pandas as pd
import streamlit as st
from nba_api.stats.endpoints import shotchartdetail, leaguedashplayerstats


# Mínimos oficiales de la NBA para calificar en los rankings de porcentaje.
# Fuente: https://www.nba.com/stats/help/statminimums
MIN_FGM  = 300  # Field goals convertidos para calificar en FG%
MIN_FG3M = 82   # Triples convertidos para calificar en 3PT%


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_tiros(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> pd.DataFrame:
    """
    Obtiene el registro completo de tiros de un jugador desde la NBA Stats API.

    Args:
        player_id: ID interno del jugador en la NBA API.
        temporada: Temporada en formato "YYYY-YY" (p. ej. "2024-25").
        tipo: "Regular Season" o "Playoffs".

    Returns:
        DataFrame con una fila por tiro intentado. Las columnas más relevantes son:
            LOC_X, LOC_Y        - Coordenadas del tiro en la cancha.
            SHOT_MADE_FLAG      - 1 si convirtió, 0 si falló.
            SHOT_TYPE           - "2PT Field Goal" o "3PT Field Goal".
            GAME_DATE           - Fecha del partido en formato "YYYYMMDD".
            PERIOD              - Cuarto del partido.

    Raises:
        ValueError: Si la API no devuelve datos para la combinación pedida
                    (jugador sin minutos en esa temporada/tipo).
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
        raise ValueError(
            f"No se encontraron tiros para el jugador {player_id} "
            f"en la temporada {temporada} ({tipo})."
        )
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_ranking(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> dict:
    """
    Calcula el ranking de un jugador en FG% y 3PT% respecto a la liga.

    Usa los mínimos oficiales de la NBA (ver constantes MIN_FGM y MIN_FG3M).
    Cada categoría tiene su propio universo de calificados: un jugador puede
    rankear en FG% pero no en 3PT% si no lanza suficientes triples.

    Args:
        player_id: ID interno del jugador en la NBA API.
        temporada: Temporada en formato "YYYY-YY".
        tipo: "Regular Season" o "Playoffs".

    Returns:
        dict con:
            rank_fg   - Posición en FG%  (None si no alcanza MIN_FGM).
            rank_fg3  - Posición en 3PT% (None si no alcanza MIN_FG3M).
            total_fg  - Jugadores calificados en FG%.
            total_fg3 - Jugadores calificados en 3PT%.
    """
    respuesta = leaguedashplayerstats.LeagueDashPlayerStats(
        season=temporada,
        season_type_all_star=tipo,
    )
    df_liga = respuesta.get_data_frames()[0]

    # Universos separados: los calificados para cada categoría no son el mismo grupo
    calificados_fg  = df_liga[df_liga["FGM"]  >= MIN_FGM].copy()
    calificados_fg3 = df_liga[df_liga["FG3M"] >= MIN_FG3M].copy()

    calificados_fg["rank_fg"]   = calificados_fg["FG_PCT"].rank(ascending=False).astype(int)
    calificados_fg3["rank_fg3"] = calificados_fg3["FG3_PCT"].rank(ascending=False).astype(int)

    jugador_fg  = calificados_fg[calificados_fg["PLAYER_ID"]  == player_id]
    jugador_fg3 = calificados_fg3[calificados_fg3["PLAYER_ID"] == player_id]

    return {
        "rank_fg"  : int(jugador_fg["rank_fg"].values[0])   if not jugador_fg.empty  else None,
        "rank_fg3" : int(jugador_fg3["rank_fg3"].values[0]) if not jugador_fg3.empty else None,
        "total_fg" : len(calificados_fg),
        "total_fg3": len(calificados_fg3),
    }
