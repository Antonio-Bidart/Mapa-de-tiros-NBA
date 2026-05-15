# 🏀 Mapa de Tiros NBA

<div align="center">

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B?style=for-the-badge)](https://mapa-de-tiros-nba.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

Aplicación interactiva para explorar los mapas de tiro de cualquier jugador NBA desde 1996 hasta la temporada actual.

**[→ Ver demo en vivo](https://mapa-de-tiros-nba.streamlit.app/)**

</div>

---
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/be5a6279-9a95-4821-84aa-88819b5478be" />


## ¿Qué hace?

Conecta con la NBA Stats API en tiempo real para obtener el registro completo de tiros de cualquier jugador en cualquier temporada. A partir de ese dataset genera:

- Un **video animado** que muestra los tiros partido a partido a lo largo de la temporada, con un efecto de "trail" sobre los últimos tiros y una animación final que desvanece los fallados — dejando solo los convertidos como firma visual de la temporada
- Tres **mapas de tiro estáticos** (tiros convertidos, fallados y vista completa) descargables como imagen
- **Estadísticas con ranking oficial** de la liga, usando los mínimos reales de la NBA (300 FGM para FG%, 82 triples convertidos para 3PT%)

## Features

### Animación temporal de tiros
Cada frame del video representa un partido. Los tiros se acumulan cronológicamente y los más recientes se muestran con mayor opacidad ("trail"), dando una sensación de movimiento y ritmo de la temporada.

### Ranking con criterio oficial NBA
El ranking de FG% y 3PT% usa los mínimos publicados en [nba.com/stats/help/statminimums](https://www.nba.com/stats/help/statminimums): 300 FGM y 82 triples convertidos respectivamente. Cada categoría tiene su propio universo de calificados, igual que los líderes oficiales de la liga.

### Exportación de imágenes
Cualquiera de los tres mapas de tiro se puede ampliar en un modal y descargar como PNG en alta resolución.

### Caché inteligente
Las llamadas a la NBA API se cachean por 1 hora con `@st.cache_data`. Consultar el mismo jugador/temporada por segunda vez es instantáneo.

## Stack tecnológico

| Herramienta | Uso |
|---|---|
| `nba_api` | Fuente de datos — shot chart y estadísticas de liga |
| `Streamlit` | Framework de la aplicación web |
| `Matplotlib` | Renderizado de la cancha y los mapas de tiro |
| `pandas` / `numpy` | Procesamiento y transformación de datos |
| `FFMpegWriter` | Generación del video animado |

## Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/Antonio-Bidart/Mapa-de-tiros-NBA.git
cd Mapa-de-tiros-NBA

# 2. Instalar dependencias del sistema (necesario para la generación de video)
# En Ubuntu/Debian:
sudo apt-get install ffmpeg

# 3. Instalar dependencias de Python
pip install -r requirements.txt

# 4. Correr la aplicación
streamlit run app.py
```

La app queda disponible en `http://localhost:8501`.

## Cómo usar

1. Buscá un jugador en el selector del sidebar
2. Elegí la temporada (disponibles desde 1996-97)
3. Seleccioná Regular Season o Playoffs
4. Presioná **Generar mapa de tiros**

La app primero muestra el video animado de la temporada. Cuando termina, aparece la galería de imágenes estáticas con las estadísticas y el ranking en la columna derecha.

## Estructura del proyecto

```
Mapa-de-tiros-NBA/
├── app.py              # Aplicación completa (lógica + UI)
├── requirements.txt    # Dependencias de Python
├── packages.txt        # Dependencias del sistema (ffmpeg)
└── README.md
```

## Roadmap

- [ ] Heatmap de eficiencia por zona de la cancha
- [ ] Comparador de dos jugadores en paralelo
- [ ] Filtros por cuarto, tipo de tiro y distancia
- [ ] Base de datos SQLite para cachear temporadas completas
- [ ] Clustering de jugadores por perfil de tiro (ML)

## Datos

Todos los datos provienen de la [NBA Stats API](https://www.nba.com/stats) a través de la librería [`nba_api`](https://github.com/swar/nba_api). Los datos son de acceso público y de uso no comercial.

---

<div align="center">
Desarrollado por <a href="https://github.com/Antonio-Bidart">Antonio Bidart</a> · Estudiante de Ciencia de Datos, UBA
</div>
