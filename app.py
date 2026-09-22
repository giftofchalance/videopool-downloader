import os
import re
import sys
import shutil
import threading
import subprocess
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

# Constantes y Rutas (Ruta dinámica para cualquier usuario del sistema)
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "VIDEOPOOL", "CLIPS")

# Configuración inicial de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def normalize_time(time_str: str) -> str:
    """Normaliza formatos de tiempo a formato aceptado por yt-dlp (HH:MM:SS o segundos)."""
    t = time_str.strip()
    if not t:
        return ""
    # Si es solo números (ej: 45 o 120)
    if t.isdigit():
        total_sec = int(t)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    # Si viene en formato MM:SS (ej: 01:30)
    parts = t.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"00:{int(parts[0]):02d}:{int(parts[1]):02d}"
    # Si ya viene en formato HH:MM:SS
    if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
    return t


def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta a un recurso, compatible con desarrollo y PyInstaller onefile."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VideoPool Downloader - Clips & Audio")
        self.geometry("780x780")
        self.minsize(680, 580)

        # Configurar icono nativo en barra de tareas de Windows
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("videopool.downloader.clips.v1")
            except Exception:
                pass

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Variables de estado
        self.output_dir = DEFAULT_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        self.is_downloading = False
        self.cancel_requested = False
        self.current_process = None
        self.worker_thread = None

        # Verificación de herramientas externas
        self.has_ytdlp = shutil.which("yt-dlp") is not None
        self.has_ffmpeg = shutil.which("ffmpeg") is not None

        # Construcción de la interfaz
        self._build_ui()

        # Si falta alguna herramienta, avisar al usuario
        self._check_dependencies_notice()

    def _build_ui(self):
        # Frame principal contenedor con scrollbar automática si se redimensiona
        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)

        # --- CABECERA ---
        header_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#18181b")
        header_frame.pack(fill="x", pady=(0, 12), ipady=6)

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ VIDEOPOOL CLIP DOWNLOADER",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38bdf8",
        )
        title_label.pack(pady=(8, 2))

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Descarga rápida de YouTube, Shorts, TikTok e Instagram a máxima calidad",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
        )
        subtitle_label.pack(pady=(0, 8))

        # Indicadores de estado de herramientas en cabecera
        tools_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        tools_frame.pack(pady=(0, 6))

        ytdlp_color = "#10b981" if self.has_ytdlp else "#ef4444"
        ytdlp_text = "● yt-dlp detectado" if self.has_ytdlp else "▲ yt-dlp NO encontrado en PATH"
        lbl_ytdlp = ctk.CTkLabel(tools_frame, text=ytdlp_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=ytdlp_color)
        lbl_ytdlp.pack(side="left", padx=10)

        ffmpeg_color = "#10b981" if self.has_ffmpeg else "#f59e0b"
        ffmpeg_text = "● ffmpeg detectado" if self.has_ffmpeg else "▲ ffmpeg no detectado"
        lbl_ffmpeg = ctk.CTkLabel(tools_frame, text=ffmpeg_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=ffmpeg_color)
        lbl_ffmpeg.pack(side="left", padx=10)

        # --- SECCIÓN ENLACES ---
        links_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#202025")
        links_frame.pack(fill="x", pady=8, padx=2)

        links_title = ctk.CTkLabel(
            links_frame,
            text="🔗 Enlaces a descargar (uno por línea o pegados juntos):",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        links_title.pack(fill="x", padx=15, pady=(12, 6))

        self.txt_links = ctk.CTkTextbox(
            links_frame,
            height=105,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8,
            border_width=1,
            border_color="#3f3f46",
        )
        self.txt_links.pack(fill="x", padx=15, pady=(0, 8))

        btn_row_links = ctk.CTkFrame(links_frame, fg_color="transparent")
        btn_row_links.pack(fill="x", padx=15, pady=(0, 12))

        self.btn_paste = ctk.CTkButton(
            btn_row_links,
            text="📋 Pegar del Portapapeles",
            command=self._paste_clipboard,
            width=180,
            fg_color="#334155",
            hover_color="#475569",
        )
        self.btn_paste.pack(side="left", padx=(0, 10))

        self.btn_clear_links = ctk.CTkButton(
            btn_row_links,
            text="🗑️ Limpiar Enlaces",
            command=self._clear_links,
            width=140,
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
        )
        self.btn_clear_links.pack(side="left")

        # --- SECCIÓN CONFIGURACIÓN (FORMATO Y RECORTE) ---
        opts_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#202025")
        opts_frame.pack(fill="x", pady=8, padx=2)

        opts_title = ctk.CTkLabel(
            opts_frame,
            text="⚙️ Formato y Opciones de Recorte:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        opts_title.pack(fill="x", padx=15, pady=(12, 8))

        # Selector de formato
        format_row = ctk.CTkFrame(opts_frame, fg_color="transparent")
        format_row.pack(fill="x", padx=15, pady=(0, 12))

        lbl_format = ctk.CTkLabel(format_row, text="Formato de salida:", font=ctk.CTkFont(size=13))
        lbl_format.pack(side="left", padx=(0, 15))

        self.format_var = ctk.StringVar(value="mp4_max")
        self.seg_format = ctk.CTkSegmentedButton(
            format_row,
            values=["🎬 MP4 (Máxima calidad)", "🎬 MP4 (1080p)", "🎵 Audio MP3 (320k)", "🎵 Audio WAV"],
            command=self._on_format_changed,
            selected_color="#0284c7",
            selected_hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.seg_format.set("🎬 MP4 (Máxima calidad)")
        self.seg_format.pack(side="left", fill="x", expand=True)

        # Opciones avanzadas de descarga (Metadatos y Acelerador)
        adv_opts_frame = ctk.CTkFrame(opts_frame, fg_color="transparent")
        adv_opts_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.embed_meta_var = ctk.BooleanVar(value=True)
        self.chk_embed_meta = ctk.CTkCheckBox(
            adv_opts_frame,
            text="🖼️ Incrustar carátula y metadatos",
            variable=self.embed_meta_var,
            font=ctk.CTkFont(size=12),
            checkbox_height=18,
            checkbox_width=18,
            text_color="#cbd5e1",
        )
        self.chk_embed_meta.pack(side="left", padx=(0, 15))

        self.fast_dl_var = ctk.BooleanVar(value=True)
        self.chk_fast_dl = ctk.CTkCheckBox(
            adv_opts_frame,
            text="⚡ Acelerador multihilo (-N 4 para archivos grandes)",
            variable=self.fast_dl_var,
            font=ctk.CTkFont(size=12),
            checkbox_height=18,
            checkbox_width=18,
            text_color="#cbd5e1",
        )
        self.chk_fast_dl.pack(side="left")

        # Opciones de recorte
        trim_card = ctk.CTkFrame(opts_frame, corner_radius=8, fg_color="#18181b")
        trim_card.pack(fill="x", padx=15, pady=(0, 12))

        self.trim_switch_var = ctk.BooleanVar(value=False)
        self.switch_trim = ctk.CTkSwitch(
            trim_card,
            text="✂️ Activar Modo Recorte (Fragmento Inicio y Fin)",
            variable=self.trim_switch_var,
            command=self._toggle_trim_inputs,
            font=ctk.CTkFont(size=13, weight="bold"),
            progress_color="#0284c7",
        )
        self.switch_trim.pack(anchor="w", padx=15, pady=(10, 8))

        self.trim_inputs_frame = ctk.CTkFrame(trim_card, fg_color="transparent")
        self.trim_inputs_frame.pack(fill="x", padx=15, pady=(0, 10))

        lbl_start = ctk.CTkLabel(self.trim_inputs_frame, text="Inicio:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_start.grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.entry_start = ctk.CTkEntry(
            self.trim_inputs_frame,
            placeholder_text="00:00:10",
            width=110,
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.entry_start.grid(row=0, column=1, padx=(0, 20), sticky="w")

        lbl_end = ctk.CTkLabel(self.trim_inputs_frame, text="Fin:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_end.grid(row=0, column=2, padx=(0, 5), sticky="w")

        self.entry_end = ctk.CTkEntry(
            self.trim_inputs_frame,
            placeholder_text="00:00:40",
            width=110,
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.entry_end.grid(row=0, column=3, padx=(0, 20), sticky="w")

        lbl_trim_help = ctk.CTkLabel(
            self.trim_inputs_frame,
            text="Formatos: HH:MM:SS, MM:SS o segundos (ej. 30)",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        lbl_trim_help.grid(row=0, column=4, sticky="w")

        # --- SECCIÓN CARPETA DESTINO ---
        folder_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#202025")
        folder_frame.pack(fill="x", pady=8, padx=2)

        lbl_dest = ctk.CTkLabel(
            folder_frame,
            text="📁 Guardado automático en:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        lbl_dest.pack(fill="x", padx=15, pady=(10, 4))

        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_path_display = ctk.CTkEntry(
            folder_row,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.lbl_path_display.insert(0, self.output_dir)
        self.lbl_path_display.configure(state="readonly")
        self.lbl_path_display.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_change_folder = ctk.CTkButton(
            folder_row,
            text="📁 Cambiar",
            command=self._change_output_folder,
            width=90,
            fg_color="#27272a",
            hover_color="#3f3f46",
        )
        self.btn_change_folder.pack(side="right", padx=(6, 0))

        self.btn_open_folder = ctk.CTkButton(
            folder_row,
            text="📂 Abrir Carpeta",
            command=self._open_output_folder,
            width=120,
            fg_color="#334155",
            hover_color="#475569",
        )
        self.btn_open_folder.pack(side="right")

        # --- BOTONES DE ACCIÓN PRINCIPALES ---
        action_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        action_frame.pack(fill="x", pady=(10, 6), padx=2)

        self.btn_start = ctk.CTkButton(
            action_frame,
            text="🚀 INICIAR DESCARGA",
            command=self._start_download_task,
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            action_frame,
            text="⏹ Cancelar",
            command=self._cancel_download,
            height=46,
            width=130,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            state="disabled",
        )
        self.btn_cancel.pack(side="right")

        # --- PROGRESO Y ESTADO ---
        progress_card = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#202025")
        progress_card.pack(fill="x", pady=8, padx=2)

        status_row = ctk.CTkFrame(progress_card, fg_color="transparent")
        status_row.pack(fill="x", padx=15, pady=(10, 4))

        self.lbl_status = ctk.CTkLabel(
            status_row,
            text="Listo para procesar enlaces.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
            anchor="w",
        )
        self.lbl_status.pack(side="left", fill="x", expand=True)

        self.lbl_pct = ctk.CTkLabel(
            status_row,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8",
        )
        self.lbl_pct.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(progress_card, height=14, corner_radius=7, progress_color="#0284c7")
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 12))

        # --- CONSOLA DE LOGS EN VIVO ---
        console_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="#18181b")
        console_frame.pack(fill="both", expand=True, pady=8, padx=2)

        console_header = ctk.CTkFrame(console_frame, fg_color="transparent")
        console_header.pack(fill="x", padx=15, pady=(8, 4))

        lbl_console = ctk.CTkLabel(
            console_header,
            text="📟 Consola de actividad yt-dlp:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
        )
        lbl_console.pack(side="left")

        btn_clear_console = ctk.CTkButton(
            console_header,
            text="Limpiar consola",
            command=self._clear_console,
            width=100,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#27272a",
            hover_color="#3f3f46",
        )
        btn_clear_console.pack(side="right")

        self.txt_console = ctk.CTkTextbox(
            console_frame,
            height=160,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#09090b",
            text_color="#22c55e",
            corner_radius=8,
            border_width=1,
            border_color="#27272a",
        )
        self.txt_console.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.txt_console.configure(state="disabled")

    # --- CONTROL DE INTERFAZ ---

    def _on_format_changed(self, choice):
        # Callback opcional si se requiere ajuste dinámico
        pass

    def _toggle_trim_inputs(self):
        is_on = self.trim_switch_var.get()
        new_state = "normal" if is_on else "disabled"
        self.entry_start.configure(state=new_state)
        self.entry_end.configure(state=new_state)
        if is_on:
            self._log_console("Modo recorte activado.")
        else:
            self._log_console("Modo recorte desactivado.")

    def _paste_clipboard(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                current_text = self.txt_links.get("1.0", "end").strip()
                if current_text:
                    self.txt_links.insert("end", "\n" + clipboard_text.strip())
                else:
                    self.txt_links.insert("1.0", clipboard_text.strip())
                self._log_console("Contenido pegado desde el portapapeles.")
        except Exception as e:
            self._log_console(f"No se pudo acceder al portapapeles: {e}")

    def _clear_links(self):
        self.txt_links.delete("1.0", "end")
        self._log_console("Lista de enlaces limpiada.")

    def _clear_console(self):
        self.txt_console.configure(state="normal")
        self.txt_console.delete("1.0", "end")
        self.txt_console.configure(state="disabled")

    def _change_output_folder(self):
        from tkinter import filedialog
        new_dir = filedialog.askdirectory(initialdir=self.output_dir, title="Seleccionar carpeta de descargas")
        if new_dir:
            self.output_dir = os.path.normpath(new_dir)
            self.lbl_path_display.configure(state="normal")
            self.lbl_path_display.delete(0, "end")
            self.lbl_path_display.insert(0, self.output_dir)
            self.lbl_path_display.configure(state="readonly")
            self._log_console(f"Carpeta de destino actualizada a: {self.output_dir}")

    def _open_output_folder(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(self.output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.output_dir])
            else:
                subprocess.Popen(["xdg-open", self.output_dir])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    def _log_console(self, message: str):
        def _append():
            self.txt_console.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.txt_console.insert("end", f"[{ts}] {message}\n")
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")
        self.after(0, _append)

    def _set_status(self, text: str, color: str = "#38bdf8", pct: float = None):
        def _update():
            self.lbl_status.configure(text=text, text_color=color)
            if pct is not None:
                clamped_pct = max(0.0, min(1.0, pct))
                self.progress_bar.set(clamped_pct)
                self.lbl_pct.configure(text=f"{int(clamped_pct * 100)}%")
        self.after(0, _update)

    def _check_dependencies_notice(self):
        if not self.has_ytdlp:
            self._log_console("ADVERTENCIA: 'yt-dlp' no se encuentra en el PATH del sistema.")
            messagebox.showwarning(
                "yt-dlp no detectado",
                "No se encontró 'yt-dlp' en el PATH. Las descargas fallarán a menos que esté instalado y accesible.",
            )
        if not self.has_ffmpeg:
            self._log_console("ADVERTENCIA: 'ffmpeg' no se encuentra en el PATH. La conversión a MP3 y recorte preciso pueden fallar.")

    # --- LÓGICA DE DESCARGA ASÍNCRONA ---

    def _start_download_task(self):
        if self.is_downloading:
            return

        raw_text = self.txt_links.get("1.0", "end").strip()
        if not raw_text:
            messagebox.showwarning("Atención", "Por favor ingresa al menos un enlace para descargar.")
            return

        # Separar por líneas y espacios para extraer URLs
        raw_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        urls = []
        for line in raw_lines:
            # Dividir por espacios por si pegaron varios links en una sola linea
            parts = line.split()
            for part in parts:
                cleaned = part.strip()
                if cleaned.startswith("http://") or cleaned.startswith("https://") or "youtu" in cleaned or "tiktok" in cleaned or "instagram" in cleaned:
                    urls.append(cleaned)
                elif cleaned:
                    urls.append(cleaned)

        if not urls:
            messagebox.showwarning("Atención", "No se detectaron enlaces válidos en el texto ingresado.")
            return

        # Validaciones de recorte
        use_trim = self.trim_switch_var.get()
        start_time = ""
        end_time = ""
        if use_trim:
            start_raw = self.entry_start.get().strip()
            end_raw = self.entry_end.get().strip()
            if not start_raw and not end_raw:
                messagebox.showwarning("Modo Recorte", "Has activado el modo recorte pero no especificaste tiempo de inicio ni de fin.")
                return
            start_time = normalize_time(start_raw)
            end_time = normalize_time(end_raw)

        # Preparar UI para descarga
        self.is_downloading = True
        self.cancel_requested = False
        self.btn_start.configure(state="disabled", fg_color="#334155")
        self.btn_cancel.configure(state="normal")
        self.btn_clear_links.configure(state="disabled")
        self.btn_paste.configure(state="disabled")

        selected_format_label = self.seg_format.get()
        embed_meta = self.embed_meta_var.get()
        fast_dl = self.fast_dl_var.get()

        # Lanzar hilo en background
        self.worker_thread = threading.Thread(
            target=self._download_worker,
            args=(urls, selected_format_label, embed_meta, fast_dl, use_trim, start_time, end_time),
            daemon=True,
        )
        self.worker_thread.start()

    def _cancel_download(self):
        if not self.is_downloading:
            return
        self.cancel_requested = True
        self._set_status("Cancelando descarga...", color="#ef4444")
        self._log_console("Cancelación solicitada por el usuario.")

        # Terminar subproceso activo si existe
        if self.current_process and self.current_process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], capture_output=True)
                else:
                    self.current_process.kill()
            except Exception as e:
                self._log_console(f"Error al detener proceso: {e}")

    def _download_worker(self, urls, selected_format, embed_meta, fast_dl, use_trim, start_time, end_time):
        total_urls = len(urls)
        success_count = 0
        error_count = 0

        self._log_console(f"--- Iniciando lote de {total_urls} enlace(s) ---")
        self._set_status(f"Iniciando descarga (0/{total_urls})...", color="#38bdf8", pct=0.0)

        # Expresión regular para porcentaje de yt-dlp
        pct_regex = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")

        for idx, url in enumerate(urls, start=1):
            if self.cancel_requested:
                self._log_console("Descarga de lote cancelada.")
                break

            self._set_status(f"Descargando ({idx}/{total_urls}): {url[:45]}...", color="#38bdf8", pct=(idx - 1) / total_urls)
            self._log_console(f"[{idx}/{total_urls}] Procesando: {url}")

            # Construcción de comando yt-dlp
            suffix = "_clip" if use_trim else ""
            out_template = os.path.join(self.output_dir, f"%(title).120B{suffix} [%(id)s].%(ext)s").replace("\\", "/")

            cmd = [
                "yt-dlp",
                "--newline",
                "--no-playlist",
                "--progress",
                "-o", out_template,
            ]

            # Formato
            if "WAV" in selected_format:
                cmd.extend(["-x", "--audio-format", "wav"])
            elif "MP3" in selected_format:
                cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
            elif "1080p" in selected_format:
                cmd.extend([
                    "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4] / bv*[height<=1080]+ba/b[height<=1080] / b",
                    "--merge-output-format", "mp4",
                ])
            else:
                # MP4 Máxima Calidad
                cmd.extend([
                    "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b",
                    "--merge-output-format", "mp4",
                ])

            # Acelerador multihilo
            if fast_dl:
                cmd.extend(["-N", "4"])

            # Metadatos y carátula
            if embed_meta:
                cmd.extend(["--embed-metadata", "--embed-thumbnail"])

            # Opciones de recorte
            if use_trim:
                s_part = start_time if start_time else "0"
                e_part = end_time if end_time else "inf"
                section_arg = f"*{s_part}-{e_part}"
                cmd.extend([
                    "--download-sections", section_arg,
                    "--force-keyframes-at-cuts",
                ])
                self._log_console(f"Aplicando recorte: {section_arg}")

            cmd.append(url)

            # Ejecución del proceso capturando salida en vivo
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=creationflags,
                )

                while True:
                    line = self.current_process.stdout.readline()
                    if not line:
                        if self.current_process.poll() is not None:
                            break
                        continue

                    clean_line = line.strip()
                    if not clean_line:
                        continue

                    # Parsear porcentaje
                    match = pct_regex.search(clean_line)
                    if match:
                        try:
                            val = float(match.group(1)) / 100.0
                            # Progreso ponderado en base al lote total
                            current_total_progress = ((idx - 1) + val) / total_urls
                            self._set_status(
                                f"Descargando ({idx}/{total_urls}) - {match.group(1)}%",
                                color="#38bdf8",
                                pct=current_total_progress,
                            )
                        except ValueError:
                            pass
                    elif "[Merger]" in clean_line or "[ExtractAudio]" in clean_line or "ffmpeg" in clean_line.lower():
                        self._set_status(f"Procesando con ffmpeg ({idx}/{total_urls})...", color="#f59e0b")

                    # Mostrar línea en consola
                    self._log_console(clean_line)

                return_code = self.current_process.wait()

                if self.cancel_requested:
                    self._log_console(f"Enlace {idx} cancelado.")
                    break

                if return_code == 0:
                    success_count += 1
                    self._log_console(f"✓ Descarga exitosa ({idx}/{total_urls})")
                else:
                    error_count += 1
                    self._log_console(f"✖ Error en descarga ({idx}/{total_urls}) - Código de salida: {return_code}")

            except Exception as e:
                error_count += 1
                self._log_console(f"Excepción al ejecutar yt-dlp: {e}")

        # Finalización del lote
        self.is_downloading = False
        self.current_process = None

        def _finish_ui():
            self.btn_start.configure(state="normal", fg_color="#0284c7")
            self.btn_cancel.configure(state="disabled")
            self.btn_clear_links.configure(state="normal")
            self.btn_paste.configure(state="normal")

            if self.cancel_requested:
                self._set_status("Operación cancelada por el usuario.", color="#ef4444", pct=0.0)
                messagebox.showinfo("Cancelado", "La descarga fue cancelada.")
            elif error_count == 0 and success_count > 0:
                self._set_status(f"¡Completado! {success_count} archivo(s) guardados con éxito.", color="#10b981", pct=1.0)
                self._log_console(f"=== Proceso finalizado con éxito ({success_count}/{total_urls}) ===")
                # Preguntar si desea abrir la carpeta
                if messagebox.askyesno("Descarga completada", f"Se descargaron {success_count} archivo(s) con éxito.\n¿Deseas abrir la carpeta de descargas?"):
                    self._open_output_folder()
            elif success_count > 0 and error_count > 0:
                self._set_status(f"Completado con errores: {success_count} OK, {error_count} fallidos.", color="#f59e0b", pct=1.0)
                messagebox.showwarning("Finalizado con advertencias", f"Se descargaron {success_count} enlaces pero fallaron {error_count}.\nRevisa la consola para más detalles.")
            else:
                self._set_status("La descarga falló. Revisa la consola para ver los detalles.", color="#ef4444", pct=0.0)
                messagebox.showerror("Error", "No se pudo completar la descarga. Revisa los mensajes en la consola.")

        self.after(0, _finish_ui)


if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()
