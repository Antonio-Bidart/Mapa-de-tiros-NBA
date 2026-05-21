"""
nba/api.py
----------
Comunicación con la NBA Stats API.

Mínimos oficiales para rankings:
    Regular Season: 300 FGM, 82 3PM  (nba.com/stats/help/statminimums)
    Playoffs:        50 FGM, 20 3PM  (≈4 FGM/partido × ~13 partidos)
    Toda la carrera: sin ranking (no aplica)
    Ambos (RS+PO):   sin ranking (universos mezclados)
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

# ── Mínimos para rankings ──────────────────────────────────────────────────────
MIN_FGM      = 300   # Regular Season FG%
MIN_FG3M     = 82    # Regular Season 3PT%
MIN_FGM_PO   = 50    # Playoffs FG%  (~4 FGM/partido × ~13 partidos)
MIN_FG3M_PO  = 20    # Playoffs 3PT% (~1.5 3PM/partido × ~13 partidos)

PRIMERA_TEMPORADA_DISPONIBLE = 1996
OPCION_CARRERA_API = "Toda la carrera"   # String interno (sin emoji)


# ── Funciones internas ────────────────────────────────────────────────────────

def _fetch_tiros(player_id: int, temporada: str, tipo: str) -> pd.DataFrame:
    """Llama a ShotChartDetail sin caché. Para uso interno en loops."""
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
    """Año de debut del jugador. Cachea 24h."""
    info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
    return int(info.get_data_frames()[0]["FROM_YEAR"].values[0])


# ── Funciones públicas ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_tiros(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> pd.DataFrame:
    """
    Tiros de un jugador en una temporada específica.

    tipo puede ser "Regular Season", "Playoffs" o "Ambos".
    "Ambos" concatena RS + PO; si no hay playoffs, devuelve solo RS.
    """
    if tipo == "Ambos":
        dfs = []
        for t in ["Regular Season", "Playoffs"]:
            try:
                df = _fetch_tiros(player_id, temporada, t)
                df = df.copy(); df["TIPO"] = t
                dfs.append(df)
            except ValueError:
                pass
        if not dfs:
            raise ValueError(
                f"Sin datos para {player_id} en {temporada} (RS ni PO).")
        return pd.concat(dfs, ignore_index=True)

    return _fetch_tiros(player_id, temporada, tipo)


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_tiros_carrera(
    player_id: int,
    tipo: str = "Regular Season",
) -> tuple:
    """
    Todos los tiros de la carrera de un jugador.

    Itera desde el debut hasta hoy. Las temporadas sin datos se saltan
    silenciosamente (lesiones, temporadas fuera de la NBA, etc.).

    Returns:
        (df_completo, temporadas_con_datos)
        df_completo incluye columnas TEMPORADA y TIPO para filtrar.
    """
    hoy        = datetime.now()
    año_actual = hoy.year if hoy.month >= 9 else hoy.year - 1
    año_debut  = max(_obtener_debut(player_id), PRIMERA_TEMPORADA_DISPONIBLE)
    tipos_pedir = ["Regular Season", "Playoffs"] if tipo == "Ambos" else [tipo]

    dfs: list[pd.DataFrame] = []
    temporadas_con_datos: list[str] = []

    for año in range(año_debut, año_actual + 1):
        temporada = f"{año}-{str(año + 1)[2:]}"
        tuvo_datos = False
        for t in tipos_pedir:
            try:
                df = _fetch_tiros(player_id, temporada, t)
                df = df.copy()
                df["TEMPORADA"] = temporada
                df["TIPO"]      = t
                dfs.append(df)
                tuvo_datos = True
            except ValueError:
                pass
        if tuvo_datos and temporada not in temporadas_con_datos:
            temporadas_con_datos.append(temporada)

    if not dfs:
        raise ValueError(f"Sin tiros en ninguna temporada del jugador {player_id}.")

    return pd.concat(dfs, ignore_index=True), temporadas_con_datos


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_stats_panel(
    player_id: int,
    temporada: str = "2025-26",
    tipo: str = "Regular Season",
) -> dict:
    """
    Stats completas para el panel de comparación.

    Retorna rankings, GP, MIN/partido, +/-, PTS, FGA, FTA.

    Reglas de ranking:
        - "Toda la carrera"  → sin ranking (no aplica)
        - tipo "Ambos"       → sin ranking (universos mezclados)
        - "Playoffs"         → mínimos reducidos (50 FGM, 20 3PM)
        - "Regular Season"   → mínimos estándar (300 FGM, 82 3PM)

    Plus/Minus:
        - Por temporada → valor oficial de leaguedashplayerstats
        - Toda la carrera → None (no acumula significado entre temporadas)
    """

    # ── Carrera completa ──────────────────────────────────────────────────────
    if temporada == OPCION_CARRERA_API:
        carrera   = playercareerstats.PlayerCareerStats(player_id=player_id)
        dfs_lista = carrera.get_data_frames()
        df_rs = dfs_lista[0] if len(dfs_lista) > 0 else pd.DataFrame()
        df_po = dfs_lista[2] if len(dfs_lista) > 2 else pd.DataFrame()

        tipos_usar = {"Regular Season": df_rs, "Playoffs": df_po}
        if tipo != "Ambos":
            tipos_usar = {tipo: tipos_usar.get(tipo, pd.DataFrame())}

        gp = pts = fga = fta = min_total = 0
        for df_t in tipos_usar.values():
            if df_t.empty:
                continue
            gp        += int(df_t["GP"].sum())
            pts       += int(df_t["PTS"].sum())
            fga       += int(df_t["FGA"].sum())
            fta       += int(df_t["FTA"].sum())
            min_total += float(df_t["MIN"].sum())

        return {
            "rank_fg": None, "rank_fg3": None,
            "total_fg": None, "total_fg3": None,
            "gp"        : gp,
            "min_pg"    : round(min_total / gp, 1) if gp > 0 else 0,
            "plus_minus": None,   # No acumula significado a lo largo de la carrera
            "pts": pts, "fga": fga, "fta": fta,
        }

    # ── Temporada específica ──────────────────────────────────────────────────
    tipos_usar = ["Regular Season", "Playoffs"] if tipo == "Ambos" else [tipo]

    # Elegimos mínimos y tipo de ranking
    calcular_ranking = tipo not in ("Ambos",)   # Sin ranking para "Ambos"
    if calcular_ranking:
        tipo_ranking = tipo  # "Regular Season" o "Playoffs"
        min_fgm  = MIN_FGM_PO  if tipo == "Playoffs" else MIN_FGM
        min_fg3m = MIN_FG3M_PO if tipo == "Playoffs" else MIN_FG3M
    else:
        tipo_ranking = "Regular Season"   # Solo para obtener stats del jugador
        min_fgm = min_fg3m = 0

    respuesta = leaguedashplayerstats.LeagueDashPlayerStats(
        season=temporada,
        season_type_all_star=tipo_ranking,
    )
    df_liga = respuesta.get_data_frames()[0]

    # Rankings (solo si aplica)
    if calcular_ranking:
        cal_fg  = df_liga[df_liga["FGM"]  >= min_fgm].copy()
        cal_fg3 = df_liga[df_liga["FG3M"] >= min_fg3m].copy()
        cal_fg["rank_fg"]   = cal_fg["FG_PCT"].rank(ascending=False).astype(int)
        cal_fg3["rank_fg3"] = cal_fg3["FG3_PCT"].rank(ascending=False).astype(int)
        jug_fg  = cal_fg[cal_fg["PLAYER_ID"]   == player_id]
        jug_fg3 = cal_fg3[cal_fg3["PLAYER_ID"] == player_id]
        rank_fg   = int(jug_fg["rank_fg"].values[0])   if not jug_fg.empty  else None
        rank_fg3  = int(jug_fg3["rank_fg3"].values[0]) if not jug_fg3.empty else None
        total_fg  = len(cal_fg)
        total_fg3 = len(cal_fg3)
    else:
        rank_fg = rank_fg3 = total_fg = total_fg3 = None

    # Stats del jugador (suma si tipo="Ambos")
    gp = pts = fga = fta = min_total = 0
    plus_minus = 0.0
    for t in tipos_usar:
        if t != tipo_ranking:
            r2  = leaguedashplayerstats.LeagueDashPlayerStats(
                season=temporada, season_type_all_star=t)
            df2 = r2.get_data_frames()[0]
        else:
            df2 = df_liga

        jug = df2[df2["PLAYER_ID"] == player_id]
        if jug.empty:
            continue
        gp         += int(jug["GP"].values[0])
        pts        += int(jug["PTS"].values[0])
        fga        += int(jug["FGA"].values[0])
        fta        += int(jug["FTA"].values[0])
        min_total  += float(jug["MIN"].values[0])
        plus_minus += float(jug["PLUS_MINUS"].values[0])

    return {
        "rank_fg"   : rank_fg,
        "rank_fg3"  : rank_fg3,
        "total_fg"  : total_fg,
        "total_fg3" : total_fg3,
        "gp"        : gp,
        "min_pg"    : round(min_total / gp, 1) if gp > 0 else 0,
        "plus_minus": round(plus_minus, 1),
        "pts"       : pts,
        "fga"       : fga,
        "fta"       : fta,
    }


def obtener_ranking(player_id: int, temporada: str, tipo: str) -> dict:
    """Alias de obtener_stats_panel() para compatibilidad."""
    stats = obtener_stats_panel(player_id, temporada, tipo)
    return {k: stats[k] for k in ("rank_fg", "rank_fg3", "total_fg", "total_fg3")}