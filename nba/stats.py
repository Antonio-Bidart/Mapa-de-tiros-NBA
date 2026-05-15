"""
nba/stats.py
------------
Cálculos y transformaciones sobre los datos de tiros.

Este módulo no sabe nada de la API ni de la UI — solo recibe DataFrames
y devuelve números. Eso lo hace fácil de testear de forma aislada.
"""

import pandas as pd


def calcular_stats(df: pd.DataFrame) -> dict:
    """
    Calcula estadísticas básicas de tiro a partir de un DataFrame de ShotChartDetail.

    Args:
        df: DataFrame devuelto por api.obtener_tiros().

    Returns:
        dict con las siguientes claves:
            fg_pct      - Porcentaje general de tiro (float, 0-100).
            fg3_pct     - Porcentaje de triples (float, 0-100).
            intentos    - Total de intentos de tiro.
            metidos     - Total de tiros convertidos.
            intentos_3  - Total de intentos de triple.
            metidos_3   - Total de triples convertidos.
    """
    total_intentos = len(df)
    total_metidos  = df["SHOT_MADE_FLAG"].sum()

    tiros_3    = df[df["SHOT_TYPE"] == "3PT Field Goal"]
    intentos_3 = len(tiros_3)
    metidos_3  = tiros_3["SHOT_MADE_FLAG"].sum()

    fg_pct  = round(total_metidos / total_intentos * 100, 1) if total_intentos > 0 else 0.0
    fg3_pct = round(metidos_3    / intentos_3     * 100, 1) if intentos_3     > 0 else 0.0

    return {
        "fg_pct"    : fg_pct,
        "fg3_pct"   : fg3_pct,
        "intentos"  : total_intentos,
        "metidos"   : int(total_metidos),
        "intentos_3": intentos_3,
        "metidos_3" : int(metidos_3),
    }
