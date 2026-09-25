import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Comprimir GIF"
MAX_INPUT_MB = 100
MAX_OUTPUT_MB = 10

# Meta interna abaixo de 10 MB para evitar exceder o limite por alguns KB.
SAFE_OUTPUT_MB = 9.3
BYTES_PER_MB = 1024 * 1024


class CompressionCancelled(Exception):
    pass


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path

    return Path(__file__).resolve().parent / relative_path


def tool_path(filename: str) -> str:
    path = resource_path(f"tools/{filename}")

    if not path.exists():
        raise FileNotFoundError(
            f"Não encontrei tools\\{filename}.\n\n"
            "Confira se ffmpeg.exe e ffprobe.exe estão dentro da pasta tools."
        )

    return str(path)


def file_size_mb(path: Path) -> float:
    return path.stat().st_size / BYTES_PER_MB


def format_mb(value: float) -> str:
    return f"{value:.2f} MB".replace(".", ",")


def even(value: int) -> int:
    value = max(2, value)
    return value if value % 2 == 0 else value - 1


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))

    if seconds < 60:
        return f"{seconds}s"

    minutes, seconds = divmod(seconds, 60)

    if minutes < 60:
        return f"{minutes}min {seconds}s"

    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}min"


def create_output_path(input_path: Path) -> Path:
    output = input_path.with_name(f"{input_path.stem}_comprimido.mp4")
    index = 2

    while output.exists():
        output = input_path.with_name(
            f"{input_path.stem}_comprimido_{index}.mp4"
        )
        index += 1

    return output


def get_media_info(input_path: Path) -> dict:
    ffprobe = tool_path("ffprobe.exe")

    command = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(input_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace"
    )

    data = json.loads(result.stdout)
    stream = data["streams"][0]

    width = int(stream["width"])
    height = int(stream["height"])
    duration = max(float(data["format"]["duration"]), 0.1)

    fps_text = stream.get("r_frame_rate", "10/1")

    try:
        numerator, denominator = fps_text.split("/")
        fps = float(numerator) / float(denominator)
    except Exception:
        fps = 10.0

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "fps": max(1.0, fps)
    }


def calculate_video_bitrate_kbps(duration_seconds: float) -> int:
    safe_bytes = SAFE_OUTPUT_MB * BYTES_PER_MB
    safe_bits = safe_bytes * 8
    raw_kbps = (safe_bits / duration_seconds) / 1000

    # Margem para metadados e variação do container MP4.
    target_kbps = raw_kbps * 0.92

    return max(120, int(target_kbps))


def build_profiles(media: dict) -> list[dict]:
    source_fps = media["fps"]

    return [
        {
            "name": "Qualidade alta",
            "scale": 1.00,
            "fps": min(source_fps, 20),
            "bitrate_factor": 1.00
        },
        {
            "name": "Equilibrado",
            "scale": 0.82,
            "fps": min(source_fps, 15),
            "bitrate_factor": 0.92
        },
        {
            "name": "Compacto",
            "scale": 0.68,
            "fps": min(source_fps, 12),
            "bitrate_factor": 0.82
        }
    ]


class ComprimirGifApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.configure(bg="#171A20")
        self.root.resizable(False, False)

        icon_path = resource_path("assets/comprimir-gif.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        self.input_path: Path | None = None
        self.output_path: Path | None = None

        self.is_compressing = False
        self.cancel_requested = False
        self.current_process: subprocess.Popen | None = None

        self.file_name_var = tk.StringVar(
            value="Nenhum arquivo selecionado"
        )
        self.before_var = tk.StringVar(value="Antes: —")
        self.after_var = tk.StringVar(value="Depois: —")
        self.status_var = tk.StringVar(
            value="Selecione um arquivo GIF para começar."
        )
        self.progress_text_var = tk.StringVar(value="")

        self.create_interface()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_interface(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Comprimir.Horizontal.TProgressbar",
            troughcolor="#2A2F39",
            background="#2ED0AA",
            bordercolor="#2A2F39",
            lightcolor="#2ED0AA",
            darkcolor="#2ED0AA"
        )

        container = tk.Frame(
            self.root,
            bg="#171A20",
            padx=24,
            pady=24
        )
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Comprimir GIF",
            font=("Segoe UI", 21, "bold"),
            bg="#171A20",
            fg="#FFFFFF"
        ).pack(anchor="w")

        tk.Label(
            container,
            text="Converta GIFs grandes em vídeos MP4 menores e legíveis.",
            font=("Segoe UI", 10),
            bg="#171A20",
            fg="#ABB3C1"
        ).pack(anchor="w", pady=(4, 22))

        file_card = tk.Frame(
            container,
            bg="#252A33",
            padx=14,
            pady=14
        )
        file_card.pack(fill="x")

        tk.Label(
            file_card,
            text="Arquivo GIF",
            font=("Segoe UI", 10, "bold"),
            bg="#252A33",
            fg="#FFFFFF"
        ).pack(anchor="w")

        file_row = tk.Frame(file_card, bg="#252A33")
        file_row.pack(fill="x", pady=(9, 0))

        tk.Label(
            file_row,
            textvariable=self.file_name_var,
            font=("Segoe UI", 9),
            bg="#252A33",
            fg="#D7DCE5",
            anchor="w",
            width=36
        ).pack(side="left", fill="x", expand=True)

        self.select_button = tk.Button(
            file_row,
            text="Selecionar arquivo",
            command=self.select_file,
            font=("Segoe UI", 9, "bold"),
            bg="#2ED0AA",
            fg="#101215",
            activebackground="#66E4C8",
            activeforeground="#101215",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=7,
            cursor="hand2"
        )
        self.select_button.pack(side="right", padx=(10, 0))

        result_card = tk.Frame(
            container,
            bg="#252A33",
            padx=14,
            pady=14
        )
        result_card.pack(fill="x", pady=(12, 0))

        tk.Label(
            result_card,
            text="Resultado",
            font=("Segoe UI", 10, "bold"),
            bg="#252A33",
            fg="#FFFFFF"
        ).pack(anchor="w")

        tk.Label(
            result_card,
            text="Formato MP4 • arquivo final com até 10 MB",
            font=("Segoe UI", 10),
            bg="#252A33",
            fg="#D7DCE5"
        ).pack(anchor="w", pady=(8, 0))

        tk.Label(
            result_card,
            text=(
                "O aplicativo preserva a qualidade sempre que possível "
                "e reduz resolução ou fluidez apenas quando necessário."
            ),
            font=("Segoe UI", 8),
            bg="#252A33",
            fg="#9FA8B7",
            justify="left",
            wraplength=400
        ).pack(anchor="w", pady=(7, 0))

        sizes = tk.Frame(container, bg="#171A20")
        sizes.pack(fill="x", pady=(16, 0))

        tk.Label(
            sizes,
            textvariable=self.before_var,
            font=("Segoe UI", 10, "bold"),
            bg="#171A20",
            fg="#FFFFFF"
        ).pack(side="left")

        tk.Label(
            sizes,
            textvariable=self.after_var,
            font=("Segoe UI", 10, "bold"),
            bg="#171A20",
            fg="#FFFFFF"
        ).pack(side="right")

        self.progress = ttk.Progressbar(
            container,
            mode="determinate",
            maximum=100,
            value=0,
            style="Comprimir.Horizontal.TProgressbar",
            length=420
        )

        self.progress_label = tk.Label(
            container,
            textvariable=self.progress_text_var,
            font=("Segoe UI", 9, "bold"),
            bg="#171A20",
            fg="#2ED0AA"
        )

        self.compress_button = tk.Button(
            container,
            text="Comprimir",
            command=self.start_compression,
            font=("Segoe UI", 11, "bold"),
            bg="#2ED0AA",
            fg="#101215",
            activebackground="#66E4C8",
            activeforeground="#101215",
            relief="flat",
            borderwidth=0,
            pady=11,
            cursor="hand2"
        )
        self.compress_button.pack(fill="x", pady=(20, 0))

        self.cancel_button = tk.Button(
            container,
            text="Cancelar",
            command=self.cancel_compression,
            font=("Segoe UI", 10, "bold"),
            bg="#C64E5B",
            fg="#FFFFFF",
            activebackground="#E26775",
            activeforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            pady=9,
            cursor="hand2"
        )

        self.open_button = tk.Button(
            container,
            text="Abrir pasta do arquivo",
            command=self.open_output_folder,
            state="disabled",
            font=("Segoe UI", 10, "bold"),
            bg="#343B48",
            fg="#808997",
            activebackground="#4B5565",
            activeforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            pady=9,
            cursor="hand2"
        )
        self.open_button.pack(fill="x", pady=(8, 0))

        tk.Label(
            container,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#171A20",
            fg="#ABB3C1",
            wraplength=420,
            justify="left"
        ).pack(anchor="w", pady=(15, 0))

    def set_progress(self, percent: float, text: str):
        self.root.after(0, self._set_progress_ui, percent, text)

    def _set_progress_ui(self, percent: float, text: str):
        percent = max(0, min(100, percent))
        self.progress.configure(value=percent)
        self.progress_text_var.set(f"{percent:.0f}% — {text}")

    def select_file(self):
        if self.is_compressing:
            return

        selected = filedialog.askopenfilename(
            title="Selecionar arquivo GIF",
            filetypes=[("Arquivos GIF", "*.gif")]
        )

        if not selected:
            return

        path = Path(selected)
        size_mb = file_size_mb(path)

        if size_mb > MAX_INPUT_MB:
            messagebox.showwarning(
                APP_NAME,
                f"Este arquivo tem {format_mb(size_mb)}.\n\n"
                f"O limite de entrada é {MAX_INPUT_MB} MB."
            )
            return

        self.input_path = path
        self.output_path = None

        self.file_name_var.set(path.name)
        self.before_var.set(f"Antes: {format_mb(size_mb)}")
        self.after_var.set("Depois: —")
        self.status_var.set(
            "Arquivo selecionado. Clique em Comprimir para criar o vídeo."
        )

        self.open_button.configure(
            state="disabled",
            bg="#343B48",
            fg="#808997"
        )

    def start_compression(self):
        if self.is_compressing:
            return

        if self.input_path is None:
            messagebox.showwarning(
                APP_NAME,
                "Selecione um arquivo GIF antes de comprimir."
            )
            return

        self.is_compressing = True
        self.cancel_requested = False
        self.output_path = None

        self.select_button.configure(state="disabled")
        self.compress_button.configure(
            state="disabled",
            text="Comprimindo..."
        )
        self.open_button.configure(state="disabled")

        self.progress.configure(value=0)
        self.progress_text_var.set("0% — Preparando...")
        self.progress.pack(
            fill="x",
            pady=(13, 0),
            before=self.compress_button
        )
        self.progress_label.pack(
            anchor="w",
            pady=(5, 0),
            before=self.compress_button
        )
        self.cancel_button.pack(
            fill="x",
            pady=(8, 0),
            after=self.compress_button
        )

        self.status_var.set("Analisando o GIF e preparando o vídeo.")

        worker = threading.Thread(
            target=self.compress_in_background,
            daemon=True
        )
        worker.start()

    def run_process_with_progress(
        self,
        command: list[str],
        duration: float,
        progress_start: float,
        progress_end: float,
        label: str
    ):
        self.current_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        try:
            last_processed_seconds = 0.0
            started_at = time.time()

            while True:
                if self.cancel_requested:
                    self.stop_current_process()
                    raise CompressionCancelled()

                line = self.current_process.stdout.readline()

                if not line:
                    if self.current_process.poll() is not None:
                        break

                    time.sleep(0.03)
                    continue

                line = line.strip()

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                if key != "out_time_ms":
                    continue

                try:
                    seconds = int(value) / 1_000_000
                except ValueError:
                    continue

                last_processed_seconds = max(
                    last_processed_seconds,
                    seconds
                )

                inner_percent = min(
                    99.5,
                    (last_processed_seconds / duration) * 100
                )

                percent = progress_start + (
                    (progress_end - progress_start) * inner_percent / 100
                )

                elapsed = time.time() - started_at

                if last_processed_seconds > 0:
                    process_speed = last_processed_seconds / elapsed
                    remaining_seconds = max(
                        0,
                        (duration - last_processed_seconds)
                        / max(process_speed, 0.01)
                    )
                    remaining_text = format_time(remaining_seconds)
                else:
                    remaining_text = "calculando..."

                self.set_progress(
                    percent,
                    f"{label} • restante: {remaining_text}"
                )

            return_code = self.current_process.wait()

            if self.cancel_requested:
                raise CompressionCancelled()

            if return_code != 0:
                raise RuntimeError(
                    "Não foi possível converter este GIF."
                )

        finally:
            self.current_process = None

    def stop_current_process(self):
        if (
            self.current_process is not None
            and self.current_process.poll() is None
        ):
            try:
                self.current_process.terminate()

                try:
                    self.current_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()

            except OSError:
                pass

    def build_ffmpeg_command(
        self,
        source: Path,
        destination: Path,
        width: int,
        height: int,
        fps: int,
        bitrate_kbps: int,
        pass_number: int,
        passlog_prefix: Path,
        output_to_null: bool
    ) -> list[str]:
        ffmpeg = tool_path("ffmpeg.exe")

        video_filter = (
            f"fps={fps},"
            f"scale={width}:{height}:flags=lanczos"
        )

        command = [
            ffmpeg,
            "-y",
            "-i", str(source),
            "-vf", video_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-b:v", f"{bitrate_kbps}k",
            "-maxrate", f"{bitrate_kbps}k",
            "-bufsize", f"{bitrate_kbps * 2}k",
            "-preset", "medium",
            "-pass", str(pass_number),
            "-passlogfile", str(passlog_prefix),
            "-an",
            "-progress", "pipe:1",
            "-nostats"
        ]

        if output_to_null:
            command.extend([
                "-f", "null",
                "NUL"
            ])
        else:
            command.extend([
                "-movflags", "+faststart",
                str(destination)
            ])

        return command

    def compress_in_background(self):
        temporary_files = []
        passlog_files = []

        try:
            self.set_progress(2, "Lendo informações do arquivo...")
            media = get_media_info(self.input_path)

            base_bitrate = calculate_video_bitrate_kbps(
                media["duration"]
            )
            profiles = build_profiles(media)

            final_output = create_output_path(self.input_path)

            best_file = None
            best_size = None
            best_settings = None
            total_profiles = len(profiles)

            for index, profile in enumerate(profiles):
                if self.cancel_requested:
                    raise CompressionCancelled()

                width = even(
                    int(media["width"] * profile["scale"])
                )
                height = even(
                    int(media["height"] * profile["scale"])
                )
                fps = max(6, int(round(profile["fps"])))
                bitrate = max(
                    120,
                    int(base_bitrate * profile["bitrate_factor"])
                )

                temporary_output = final_output.with_name(
                    f".{final_output.stem}_tentativa_{index + 1}.mp4"
                )
                temporary_files.append(temporary_output)

                passlog_prefix = final_output.with_name(
                    f".{final_output.stem}_pass_{index + 1}"
                )

                passlog_files.extend([
                    Path(f"{passlog_prefix}-0.log"),
                    Path(f"{passlog_prefix}-0.log.mbtree")
                ])

                profile_start = (index / total_profiles) * 95
                profile_end = ((index + 1) / total_profiles) * 95
                pass_one_end = profile_start + (
                    (profile_end - profile_start) * 0.42
                )

                self.set_progress(
                    profile_start,
                    f"{profile['name']} • "
                    f"{width}×{height} • {fps} FPS"
                )

                pass_one_command = self.build_ffmpeg_command(
                    source=self.input_path,
                    destination=temporary_output,
                    width=width,
                    height=height,
                    fps=fps,
                    bitrate_kbps=bitrate,
                    pass_number=1,
                    passlog_prefix=passlog_prefix,
                    output_to_null=True
                )

                self.run_process_with_progress(
                    pass_one_command,
                    media["duration"],
                    profile_start,
                    pass_one_end,
                    "Analisando vídeo"
                )

                if self.cancel_requested:
                    raise CompressionCancelled()

                pass_two_command = self.build_ffmpeg_command(
                    source=self.input_path,
                    destination=temporary_output,
                    width=width,
                    height=height,
                    fps=fps,
                    bitrate_kbps=bitrate,
                    pass_number=2,
                    passlog_prefix=passlog_prefix,
                    output_to_null=False
                )

                self.run_process_with_progress(
                    pass_two_command,
                    media["duration"],
                    pass_one_end,
                    profile_end,
                    "Criando vídeo"
                )

                if not temporary_output.exists():
                    raise RuntimeError(
                        "A conversão terminou, mas o arquivo não foi criado."
                    )

                current_size = file_size_mb(temporary_output)

                if best_size is None or current_size < best_size:
                    best_file = temporary_output
                    best_size = current_size
                    best_settings = {
                        "name": profile["name"],
                        "width": width,
                        "height": height,
                        "fps": fps,
                        "bitrate": bitrate
                    }

                self.set_progress(
                    profile_end,
                    f"{profile['name']} concluído: {format_mb(current_size)}"
                )

                if current_size <= SAFE_OUTPUT_MB:
                    break

            if self.cancel_requested:
                raise CompressionCancelled()

            if best_file is None or best_size is None:
                raise RuntimeError(
                    "Não foi possível criar um vídeo comprimido."
                )

            self.set_progress(97, "Salvando melhor resultado...")
            os.replace(best_file, final_output)
            temporary_files.remove(best_file)

            self.set_progress(100, "Concluído.")

            self.root.after(
                0,
                self.compression_succeeded,
                final_output,
                best_size,
                best_settings
            )

        except CompressionCancelled:
            self.root.after(0, self.compression_cancelled)

        except Exception as error:
            self.root.after(
                0,
                self.compression_failed,
                str(error)
            )

        finally:
            self.current_process = None

            for path in temporary_files + passlog_files:
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass

    def restore_interface(self):
        self.is_compressing = False
        self.cancel_requested = False
        self.current_process = None

        self.select_button.configure(state="normal")
        self.compress_button.configure(
            state="normal",
            text="Comprimir"
        )
        self.cancel_button.pack_forget()

    def compression_succeeded(
        self,
        output_path: Path,
        final_size: float,
        settings: dict
    ):
        self.restore_interface()

        self.output_path = output_path
        self.after_var.set(f"Depois: {format_mb(final_size)}")

        self.open_button.configure(
            state="normal",
            bg="#343B48",
            fg="#FFFFFF"
        )

        self.status_var.set(
            f"Concluído: {output_path.name} foi salvo na mesma pasta."
        )

        if final_size <= MAX_OUTPUT_MB:
            messagebox.showinfo(
                APP_NAME,
                "Compressão concluída.\n\n"
                f"Antes: {format_mb(file_size_mb(self.input_path))}\n"
                f"Depois: {format_mb(final_size)}\n"
                f"Resolução: {settings['width']}×{settings['height']}\n"
                f"Fluidez: {settings['fps']} FPS\n\n"
                f"Arquivo criado:\n{output_path.name}"
            )
        else:
            messagebox.showwarning(
                APP_NAME,
                "O vídeo foi criado, mas ficou acima de 10 MB.\n\n"
                f"Resultado: {format_mb(final_size)}\n\n"
                "Tente reduzir a duração do GIF ou use um arquivo de origem menor."
            )

    def compression_cancelled(self):
        self.restore_interface()
        self.after_var.set("Depois: —")
        self.status_var.set(
            "Compressão cancelada. Agora você pode selecionar outro arquivo."
        )

        messagebox.showinfo(
            APP_NAME,
            "A compressão foi cancelada.\n\n"
            "Os arquivos temporários foram removidos."
        )

    def compression_failed(self, error_message: str):
        self.restore_interface()
        self.status_var.set("Não foi possível comprimir o arquivo.")

        messagebox.showerror(
            APP_NAME,
            f"Ocorreu um erro durante a compressão:\n\n{error_message}"
        )

    def cancel_compression(self):
        if not self.is_compressing:
            return

        self.cancel_requested = True

        self.cancel_button.configure(
            state="disabled",
            text="Cancelando..."
        )

        self.status_var.set(
            "Cancelando compressão e removendo arquivos temporários..."
        )

        self.stop_current_process()

    def open_output_folder(self):
        if self.output_path is None or not self.output_path.exists():
            messagebox.showwarning(
                APP_NAME,
                "Ainda não existe um arquivo para abrir."
            )
            return

        os.startfile(str(self.output_path.parent))

    def on_close(self):
        if self.is_compressing:
            should_close = messagebox.askyesno(
                APP_NAME,
                "Uma compressão está em andamento.\n\n"
                "Deseja cancelar e fechar?"
            )

            if not should_close:
                return

            self.cancel_requested = True
            self.stop_current_process()

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    ComprimirGifApp(root)
    root.mainloop()