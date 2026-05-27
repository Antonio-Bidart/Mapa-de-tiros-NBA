# NBA Shot Chart

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://mapa-de-tiros-nba.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![nba_api](https://img.shields.io/badge/nba__api-1.11-17408B?style=for-the-badge)](https://github.com/swar/nba_api)

Herramienta de análisis visual de tiros NBA. Conecta en tiempo real con la NBA Stats API para generar shot charts, animaciones por temporada y comparativas entre jugadores — desde 1996 hasta la temporada actual.

**[→ Ver demo en vivo](https://mapa-de-tiros-nba.streamlit.app/)**

</div>

---

<img width="1920" height="1080" alt="NBA Shot Chart — dark UI" src="https://github.com/user-attachments/assets/be5a6279-9a95-4821-84aa-88819b5478be" />

## Features

### Modos de análisis

**Un jugador** — exploración individual con tres visualizaciones independientes:
- `Animación` — video partido a partido con efecto trail. Cada frame es un partido; los tiros más recientes tienen mayor opacidad. Al final se disuelven los fallados, dejando solo los convertidos como firma visual de la temporada.
- `Mapa de tiros` — scatter plot sobre cancha dibujada con matplotlib. Vista separada de convertidos/fallados + completa. Descargable como PNG.
- `Hexbin` — mapa de calor hexagonal donde el tamaño de cada celda representa volumen de tiros y el color representa FG% (escala fría→caliente).

**Comparar** — análisis lado a lado de dos jugadores con cancha compartida, hexbin con escala unificada y tabla comparativa de estadísticas con highlight automático del mejor valor en cada categoría.

### Toda la carrera
Selector especial que agrega todos los tiros de la trayectoria completa del jugador. Incluye un slider interactivo para recorrer temporada por temporada sin recargar datos.

### Estadísticas con criterio oficial NBA
FG% y 3PT% se rankean usando los mínimos reales publicados en [nba.com/stats/help/statminimums](https://www.nba.com/stats/help/statminimums): 300 FGM y 82 triples convertidos. True Shooting % calculado como `PTS / (2 × (FGA + 0.44 × FTA))`.

### Caché automático
Las llamadas a la NBA API se cachean por 1 hora con `@st.cache_data`. Repetir una consulta es instantáneo.

## Stack

| | Herramienta | Rol |
|---|---|---|
| Datos | `nba_api 1.11` | Shot chart y estadísticas de liga en tiempo real |
| App | `Streamlit 1.57` | Framework web + layout responsivo |
| Visualización | `Matplotlib 3.10` | Cancha, scatter, hexbin, animación |
| Procesamiento | `pandas 3.0` / `numpy` | Transformación y agregación de datos |
| Video | `FFMpegWriter` | Renderizado del mp4 animado |

## Instalación local

```bash
git clone https://github.com/Antonio-Bidart/Mapa-de-tiros-NBA.git
cd Mapa-de-tiros-NBA

# ffmpeg es necesario para generar la animación
# Ubuntu/Debian:
sudo apt-get install ffmpeg
# macOS:
brew install ffmpeg

pip install -r requirements.txt
streamlit run app.py
```

La app queda disponible en `http://localhost:8501`.

## Estructura

```
Mapa-de-tiros-NBA/
├── app.py                  # UI principal — sidebar, tabs, lógica de estado
├── nba/
│   ├── api.py              # Capa de datos — NBA Stats API + caché
│   ├── charts.py           # Visualizaciones — cancha, scatter, hexbin, video
│   ├── stats.py            # Cálculos — FG%, 3PT%, TS%, rankings
│   └── styles.py           # Tema visual — CSS inyectado, paleta dark
├── .streamlit/
│   └── config.toml         # Tema Streamlit — dark, primaryColor blanco
├── requirements.txt
└── packages.txt            # Dependencias del sistema (ffmpeg)
```

## Roadmap

- [ ] Base de datos SQLite para persistir temporadas ya consultadas
- [ ] Filtros por cuarto, tipo de tiro y distancia
- [ ] Clustering de jugadores por perfil de tiro (ML)
- [ ] Predicción de FG% por zona con modelos de expected points
- [ ] Búsqueda por equipo y temporada

## Datos

Todos los datos provienen de la [NBA Stats API](https://www.nba.com/stats) vía [`nba_api`](https://github.com/swar/nba_api). Uso no comercial.

---

<div align="center">
Desarrollado por <a href="https://github.com/Antonio-Bidart">Antonio Bidart</a> · Estudiante de Ciencia de Datos, UBA
</div>