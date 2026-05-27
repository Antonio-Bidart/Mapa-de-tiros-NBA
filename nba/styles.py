"""
nba/styles.py
-------------
Sistema de tema visual para la app NBA Shot Chart.

Tema único:
    "dark"  → Midnight Court: negro profundo, tipografía editorial, acento blanco.

Uso:
    from nba.styles import aplicar_estilos, stat_table_html
    aplicar_estilos()   # llama a st.markdown con el CSS completo
"""

import streamlit as st


# ── Paletas ───────────────────────────────────────────────────────────────────

TEMAS = {
    "dark": {
        # Fondos
        "bg_app"        : "#0a0a0a",
        "bg_sidebar"    : "#050505",
        "bg_card"       : "#111111",
        "bg_input"      : "#161616",
        "bg_tab_active" : "#0a0a0a",

        # Texto
        "text_primary"  : "#f0ece4",
        "text_secondary": "#888888",
        "text_sidebar"  : "#f0ece4",
        "text_muted"    : "#444444",

        # Acentos — Blanco editorial
        "accent"        : "#e8e8e8",
        "accent_hover"  : "#ffffff",
        "accent_text"   : "#0a0a0a",

        # Bordes
        "border"        : "#1e1e1e",
        "border_sidebar": "#1e1e1e",

        # Tabla
        "tabla_header"  : "#111111",
        "tabla_header_text": "#f0ece4",
        "tabla_row_hover": "#161616",
        "tabla_border"  : "#1e1e1e",
        "mejor"         : "#00cc6a",
        "peor"          : "#e05555",
    },
}


def aplicar_estilos(tema: str = "dark") -> None:
    """
    Inyecta el CSS completo del tema en la app de Streamlit.

    Importa Bebas Neue e IBM Plex desde Google Fonts.
    Sobreescribe los estilos por defecto de Streamlit con selectores específicos.

    Args:
        tema: actualmente solo "dark" (Midnight Court).
    """
    c = TEMAS.get(tema, TEMAS["dark"])

    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* ── Variables globales ── */
    :root {{
        --accent:         {c['accent']};
        --accent-text:    {c['accent_text']};
        --text-primary:   {c['text_primary']};
        --text-secondary: {c['text_secondary']};
        --text-muted:     {c['text_muted']};
        --bg-app:         {c['bg_app']};
        --bg-card:        {c['bg_card']};
        --bg-input:       {c['bg_input']};
        --border:         {c['border']};
    }}

    /* ── App base ── */
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {c['bg_app']} !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        color: {c['text_primary']} !important;
    }}

    .block-container {{
        padding-top: 2.2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background-color: {c['bg_sidebar']} !important;
        border-right: 1px solid {c['border_sidebar']} !important;
    }}

    [data-testid="stSidebar"] * {{
        color: {c['text_sidebar']} !important;
    }}

    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        color: #555555 !important;
    }}

    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background: #222222 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 4px !important;
        color: #aaaaaa !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
    }}

    [data-testid="stSidebar"] .stSelectbox svg {{
        fill: #555555 !important;
    }}

    [data-testid="stSidebar"] .stCheckbox label p {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.05em !important;
        text-transform: none !important;
        color: #666666 !important;
    }}

    [data-testid="stSidebar"] .stCheckbox input:checked + div {{
        background-color: {c['accent']} !important;
        border-color: {c['accent']} !important;
    }}

    /* El ícono del checkmark (SVG) debe ser oscuro sobre fondo blanco */
    [data-testid="stSidebar"] .stCheckbox input:checked + div svg {{
        stroke: {c['accent_text']} !important;
        color: {c['accent_text']} !important;
    }}

    /* ── Botón principal Generar ── */
    [data-testid="stSidebar"] .stButton button,
    [data-testid="stSidebar"] .stButton button p,
    [data-testid="stSidebar"] .stButton button span {{
        background-color: {c['accent']} !important;
        color: {c['accent_text']} !important;
        border: none !important;
        border-radius: 3px !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 18px !important;
        letter-spacing: 0.12em !important;
        padding: 10px 0 !important;
        width: 100% !important;
        transition: opacity 0.2s !important;
    }}

    [data-testid="stSidebar"] .stButton button:hover {{
        opacity: 0.88 !important;
    }}

    [data-testid="stSidebar"] .stButton button:disabled {{
        opacity: 0.35 !important;
        cursor: not-allowed !important;
    }}

    /* ── Botones secundarios (Ver en grande, Ver de nuevo) ── */
    .main-content .stButton button,
    [data-testid="stVerticalBlock"] .stButton button {{
        background: transparent !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_secondary']} !important;
        border-radius: 3px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        transition: border-color 0.2s, color 0.2s !important;
    }}

    .main-content .stButton button:hover {{
        border-color: {c['accent']} !important;
        color: {c['accent']} !important;
    }}

    /* ── Radio (modo toggle en sidebar) ── */
    [data-testid="stSidebar"] .stRadio > div {{
        flex-direction: row !important;
        gap: 4px !important;
    }}

    [data-testid="stSidebar"] .stRadio label {{
        background: #1e1e1e !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 3px !important;
        padding: 5px 10px !important;
        font-size: 10px !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
    }}

    [data-testid="stSidebar"] .stRadio label:has(input:checked) {{
        background: {c['accent']} !important;
        border-color: {c['accent']} !important;
        color: {c['accent_text']} !important;
    }}

    /* Forzar color oscuro en todos los hijos del label activo.
       Necesario porque [stSidebar] * tiene color: text_sidebar !important
       y gana sobre el color del label por especificidad. */
    [data-testid="stSidebar"] .stRadio label:has(input:checked) *,
    [data-testid="stSidebar"] .stRadio label:has(input:checked) p,
    [data-testid="stSidebar"] .stRadio label:has(input:checked) span,
    [data-testid="stSidebar"] .stRadio label:has(input:checked) div {{
        color: {c['accent_text']} !important;
    }}

    [data-testid="stSidebar"] .stRadio input {{
        display: none !important;
    }}

    /* ── Títulos principales ── */
    h1 {{
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 3.2rem !important;
        letter-spacing: 0.02em !important;
        color: {c['text_primary']} !important;
        line-height: 1 !important;
        padding-bottom: 0.3rem !important;
        border-bottom: 2px solid {c['text_primary']} !important;
        margin-bottom: 0.5rem !important;
    }}

    h2 {{
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.6rem !important;
        letter-spacing: 0.04em !important;
        color: {c['text_primary']} !important;
    }}

    h3, h4 {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.18em !important;
        text-transform: uppercase !important;
        color: {c['text_muted']} !important;
        font-weight: 400 !important;
    }}

    /* ── Tabs ── */
    [data-baseweb="tab-list"] {{
        background: transparent !important;
        border-bottom: 1px solid {c['border']} !important;
        gap: 0 !important;
    }}

    [data-baseweb="tab"] {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        color: {c['text_muted']} !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
        padding: 10px 18px !important;
        transition: color 0.2s !important;
    }}

    [aria-selected="true"][data-baseweb="tab"] {{
        color: {c['text_primary']} !important;
        border-bottom-color: {c['accent']} !important;
        background: transparent !important;
    }}

    [data-baseweb="tab-highlight"] {{
        background-color: {c['accent']} !important;
    }}

    [data-baseweb="tab-border"] {{
        background-color: {c['border']} !important;
    }}

    /* ── Métricas ── */
    [data-testid="stMetric"] {{
        background: {c['bg_card']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 4px !important;
        padding: 10px 14px !important;
        margin-bottom: 6px !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 9px !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        color: {c['text_muted']} !important;
    }}

    [data-testid="stMetricValue"] {{
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 2rem !important;
        color: {c['text_primary']} !important;
        line-height: 1.1 !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        color: {c['accent']} !important;
    }}

    [data-testid="stMetricDelta"] svg {{
        display: none !important;
    }}

    /* ── Selectbox principal ── */
    .stSelectbox > div > div {{
        background: {c['bg_input']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 4px !important;
        color: {c['text_primary']} !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
    }}

    /* ── Slider ── */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background: {c['accent']} !important;
        border-color: {c['accent']} !important;
    }}

    .stSlider [data-baseweb="slider"] [data-testid="stTickBar"] {{
        color: {c['text_muted']} !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 9px !important;
    }}

    /* ── Spinner ── */
    .stSpinner > div {{
        border-top-color: {c['accent']} !important;
    }}

    /* ── Info / Warning / Error boxes ── */
    [data-testid="stInfoBox"] {{
        background: {c['bg_card']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 4px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        color: {c['text_secondary']} !important;
    }}

    /* ── Download button ── */
    [data-testid="stDownloadButton"] button {{
        background: transparent !important;
        border: 1px solid {c['border']} !important;
        color: {c['text_secondary']} !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        border-radius: 3px !important;
        transition: border-color 0.2s, color 0.2s !important;
    }}

    [data-testid="stDownloadButton"] button:hover {{
        border-color: {c['accent']} !important;
        color: {c['accent']} !important;
    }}

    /* ── Captions ── */
    [data-testid="stCaptionContainer"] {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 0.08em !important;
        color: {c['text_muted']} !important;
        text-align: center !important;
        margin-top: 4px !important;
    }}

    /* ── Divisor ── */
    hr {{
        border-color: {c['border']} !important;
        margin: 1rem 0 !important;
    }}

    /* ── Imágenes ── */
    img {{
        border-radius: 6px !important;
    }}

    video {{
        border-radius: 6px !important;
    }}

    /* ── Dialog / Modal ── */
    [data-testid="stModal"] {{
        background: {c['bg_app']} !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{
        width: 4px;
        height: 4px;
    }}
    ::-webkit-scrollbar-track {{
        background: {c['bg_app']};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {c['border']};
        border-radius: 2px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {c['accent']};
    }}

    /* ── Tag de temporada en el título ── */
    .season-tag {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.1em;
        color: {c['accent']};
        border: 1px solid {c['accent']}55;
        background: {c['accent']}11;
        padding: 2px 10px;
        border-radius: 3px;
        margin-left: 12px;
        vertical-align: middle;
        position: relative;
        top: -4px;
    }}

    /* ── Separador de sección en sidebar ── */
    .sidebar-section {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: #333333;
        padding: 6px 0 4px;
        border-top: 1px solid #2a2a2a;
        margin-top: 4px;
    }}
    """

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def stat_table_html(
    stats1: dict, stats2: dict,
    panel1: dict, panel2: dict,
    nombre1: str, nombre2: str,
    temporada1: str, temporada2: str,
    tipo1: str, tipo2: str,
    tema: str = "dark",
) -> str:
    """
    Genera la tabla comparativa HTML con estilos del tema activo.
    """
    from nba.stats import calcular_ts
    c = TEMAS.get(tema, TEMAS["dark"])

    OPCION_CARRERA = "📅 Toda la carrera"

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
    pm1_str = str(pm1) if pm1 is not None else "N/A"
    pm2_str = str(pm2) if pm2 is not None else "N/A"

    def fmt_rank(rank, total):
        return f"#{rank} / {total}" if rank else "—"

    def no_aplica(tipo, temporada):
        return temporada == OPCION_CARRERA or tipo == "Ambos"

    cls_fg  = hl(panel1["rank_fg"],  panel2["rank_fg"],  higher=False) \
              if panel1["rank_fg"] and panel2["rank_fg"] else ("", "")
    cls_fg3 = hl(panel1["rank_fg3"], panel2["rank_fg3"], higher=False) \
              if panel1["rank_fg3"] and panel2["rank_fg3"] else ("", "")

    rows = [
        ("Partidos jugados",
         str(panel1["gp"]), str(panel2["gp"]),
         *hl(panel1["gp"], panel2["gp"])),

        ("Min. por partido",
         str(panel1["min_pg"]), str(panel2["min_pg"]),
         *hl(panel1["min_pg"], panel2["min_pg"])),

        ("Plus / Minus",
         pm1_str, pm2_str,
         *(hl(pm1, pm2) if pm1 is not None and pm2 is not None else ("", ""))),

        ("% de tiro (FG%)",
         f"{stats1['fg_pct']}%", f"{stats2['fg_pct']}%",
         *hl(stats1["fg_pct"], stats2["fg_pct"])),

        ("% de triples (3PT%)",
         f"{stats1['fg3_pct']}%", f"{stats2['fg3_pct']}%",
         *hl(stats1["fg3_pct"], stats2["fg3_pct"])),

        ("TS% ★",
         ts1_str, ts2_str,
         *(hl(ts1, ts2) if ts1 and ts2 else ("", ""))),

        ("Tiros intentados",
         str(stats1["intentos"]), str(stats2["intentos"]),
         *hl(stats1["intentos"], stats2["intentos"])),

        ("Tiros convertidos",
         str(stats1["metidos"]), str(stats2["metidos"]),
         *hl(stats1["metidos"], stats2["metidos"])),

        ("Triples intentados",
         str(stats1["intentos_3"]), str(stats2["intentos_3"]),
         *hl(stats1["intentos_3"], stats2["intentos_3"])),

        ("Triples convertidos",
         str(stats1["metidos_3"]), str(stats2["metidos_3"]),
         *hl(stats1["metidos_3"], stats2["metidos_3"])),

        ("Ranking FG%",
         "No aplica" if no_aplica(tipo1, temporada1) else fmt_rank(panel1["rank_fg"], panel1["total_fg"]),
         "No aplica" if no_aplica(tipo2, temporada2) else fmt_rank(panel2["rank_fg"], panel2["total_fg"]),
         cls_fg[0], cls_fg[1]),

        ("Ranking 3PT%",
         "No aplica" if no_aplica(tipo1, temporada1) else fmt_rank(panel1["rank_fg3"], panel1["total_fg3"]),
         "No aplica" if no_aplica(tipo2, temporada2) else fmt_rank(panel2["rank_fg3"], panel2["total_fg3"]),
         cls_fg3[0], cls_fg3[1]),
    ]

    filas = "".join(f"""
    <tr>
        <td class="{c1}" style="text-align:right;padding:9px 16px;
            border-bottom:1px solid {c['tabla_border']};
            font-family:'IBM Plex Mono',monospace;font-size:13px;">{v1}</td>
        <td style="text-align:center;padding:9px 12px;
            border-bottom:1px solid {c['tabla_border']};
            font-family:'IBM Plex Mono',monospace;font-size:9px;
            letter-spacing:0.12em;text-transform:uppercase;
            color:{c['text_muted']};">{m}</td>
        <td class="{c2}" style="text-align:left;padding:9px 16px;
            border-bottom:1px solid {c['tabla_border']};
            font-family:'IBM Plex Mono',monospace;font-size:13px;">{v2}</td>
    </tr>""" for m, v1, v2, c1, c2 in rows)

    return f"""
    <style>
        .mejor {{ color: {c['mejor']}; font-weight: 600; }}
        .peor  {{ color: {c['peor']}; }}
        .stat-table {{ width:100%; border-collapse:collapse; }}
        .stat-table thead tr th {{
            background: {c['tabla_header']};
            color: {c['tabla_header_text']};
            padding: 10px 16px;
            font-family: 'Bebas Neue', sans-serif;
            font-size: 16px;
            letter-spacing: 0.08em;
        }}
        .stat-table thead tr th:first-child {{ text-align:right; color:{c['accent']}; }}
        .stat-table thead tr th:last-child  {{ text-align:left;  color:{c['accent']}; }}
        .stat-table thead tr th:nth-child(2) {{ color:{c['tabla_header_text']}; text-align:center; font-size:10px; letter-spacing:0.2em; font-family:'IBM Plex Mono',monospace; }}
        .stat-table tbody tr:hover td {{ background: {c['tabla_row_hover']}; }}
    </style>
    <table class="stat-table">
      <thead><tr>
        <th>{nombre1}</th>
        <th>Estadística</th>
        <th>{nombre2}</th>
      </tr></thead>
      <tbody>{filas}</tbody>
    </table>
    <p style="font-family:'IBM Plex Mono',monospace;font-size:10px;
              color:{c['text_muted']};margin-top:12px;line-height:1.6;">
      ★ True Shooting % = PTS / (2 × (FGA + 0.44 × FTA)). Liga ~56%.<br>
      Mínimos: Regular Season 300 FGM / 82 3PM · Playoffs 50 FGM / 20 3PM.
    </p>"""