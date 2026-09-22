# ⚡ VideoPool Downloader

> Aplicación de escritorio moderna y oscura para Windows desarrollada en Python con **CustomTkinter**. Permite descargar y recortar videos o extraer audio de múltiples plataformas (YouTube, Shorts, TikTok, Instagram) utilizando `yt-dlp` y `ffmpeg` sin bloquear la interfaz.

---

## ✨ Características

- 🎨 **Interfaz Moderna & Oscura**: Desarrollada con CustomTkinter en modo oscuro elegante y limpio.
- 📋 **Descargas Múltiples**: Pega uno o varios enlaces a la vez (uno por línea o en bloque).
- 🎬 **Formatos de Video**:
  - `MP4 (Máxima calidad)`: Descarga en la mayor resolución disponible (4K/2K/1080p) uniendo flujos automáticamente con ffmpeg.
  - `MP4 (1080p)`: Limita a 1080p para ahorrar espacio y tiempo.
- 🎵 **Formatos de Audio**:
  - `Audio MP3 (320 kbps)`: Extracción de audio en alta calidad.
  - `Audio WAV`: Audio sin pérdida de compresión.
- ✂️ **Modo Recorte de Clips**: Especifica tiempo de inicio y fin (`HH:MM:SS`, `MM:SS` o segundos) para descargar únicamente el fragmento deseado.
- 🖼️ **Carátulas y Metadatos**: Opción para incrustar la miniatura como portada y añadir tags ID3/metadatos al archivo.
- ⚡ **Acelerador Multihilo (`-N 4`)**: Descarga fragmentos DASH/HLS en paralelo para maximizar la velocidad en archivos grandes.
- 📁 **Carpeta Dinámica**: Guarda automáticamente en `Documentos/VIDEOPOOL/CLIPS` del usuario actual, con botón para abrirla directamente en el Explorador de Windows.
- 🔄 **Procesamiento Asíncrono**: La interfaz nunca se congela; incluye barra de progreso, porcentaje en vivo, consola de actividad y botón para cancelar.

---

## 🛠️ Requisitos Previos

Para que la aplicación pueda procesar y fusionar las descargas, requiere tener en el `PATH` del sistema:

1. [**yt-dlp**](https://github.com/yt-dlp/yt-dlp): Motor de descarga multimedia.
2. [**ffmpeg**](https://ffmpeg.org/download.html): Necesario para recortar, convertir a MP3 y fusionar video con audio.

---

## 🚀 Uso e Instalación

### Opción 1: Ejecutable listo para usar (.exe)
Descarga la última versión de **`VideoPoolDownloader.exe`** desde la sección [Releases](../../releases) y ejecútala directamente con doble clic.

### Opción 2: Ejecutar desde el código fuente

1. Clona este repositorio:
   ```bash
   git clone https://github.com/giftofchalance/videopool-downloader.git
   cd videopool-downloader
   ```

2. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta la aplicación:
   ```bash
   python app.py
   ```
   *(O ejecuta `iniciar_app.bat` en Windows)*

---

## ⚖️ Descargo de Responsabilidad (Disclaimer)

Esta herramienta ha sido desarrollada únicamente con fines educativos y para respaldo o edición personal de contenido propio o bajo licencias libres. El usuario es el único responsable de cumplir con las leyes de propiedad intelectual aplicables y los Términos de Servicio de las plataformas de las que descargue material.

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.
