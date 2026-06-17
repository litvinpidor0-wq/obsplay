import os, io, struct, threading, tempfile, traceback
from typing import Optional, Callable

import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal


class EqualizerProcessor:

    BAND_FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    BAND_NAMES        = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
    DEFAULT_Q         = 1.41

    def __init__(self, sample_rate: int = 44100, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.gains = [0.0] * len(self.BAND_FREQUENCIES)
        self.bypassed = False
        self._coeffs: list[np.ndarray] = []
        self._states: np.ndarray = np.zeros((0,))
        self._dirty = True

    def set_gain(self, band_idx: int, gain_db: float):
        if 0 <= band_idx < len(self.gains):
            self.gains[band_idx] = max(-12.0, min(12.0, gain_db))
            self._dirty = True

    def set_sample_rate(self, sr: int):
        if sr != self.sample_rate:
            self.sample_rate = sr
            self._dirty = True

    def set_channels(self, ch: int):
        if ch != self.channels:
            self.channels = ch
            self._dirty = True

    def reset(self):
        self.gains = [0.0] * len(self.BAND_FREQUENCIES)
        self._dirty = True

    def process(self, data: np.ndarray) -> np.ndarray:
        if self.bypassed:
            return data

        if data.ndim == 1:
            data = data.reshape(-1, 1)
            mono = True
        else:
            mono = False

        if self._dirty:
            self._rebuild_filters()

        out = np.require(data, dtype=np.float64, requirements="C")
        n_samples = out.shape[0]

        for band_idx, coeffs in enumerate(self._coeffs):
            b0, b1, b2, a1, a2 = coeffs
            for ch in range(out.shape[1]):
                x1, x2, y1, y2 = self._states[band_idx, ch]
                ch_data = out[:, ch]
                for n in range(n_samples):
                    xn = ch_data[n]
                    yn = b0 * xn + b1 * x1 + b2 * x2 + a1 * y1 + a2 * y2
                    x2, x1 = x1, xn
                    y2, y1 = y1, yn
                    ch_data[n] = yn
                self._states[band_idx, ch] = (x1, x2, y1, y2)

        return (out[:, 0] if mono else out).astype(data.dtype)

    def _rebuild_filters(self):
        fs = self.sample_rate
        self._coeffs = []
        for freq, gain_db in zip(self.BAND_FREQUENCIES, self.gains):
            coeffs = self._peaking_coeffs(freq, gain_db, self.DEFAULT_Q, fs)
            self._coeffs.append(coeffs)
        self._states = np.zeros((len(self._coeffs), self.channels, 4))
        self._dirty = False

    @staticmethod
    def _peaking_coeffs(freq: float, gain_db: float, q: float, fs: int) -> np.ndarray:
        A = 10.0 ** (gain_db / 40.0)
        w0 = 2.0 * np.pi * freq / fs
        cos_w = np.cos(w0)
        sin_w = np.sin(w0)
        alpha = sin_w / (2.0 * q)

        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w
        a2 = 1.0 - alpha / A

        inv_a0 = 1.0 / a0
        return np.array([b0 * inv_a0, b1 * inv_a0, b2 * inv_a0,
                         -a1 * inv_a0, -a2 * inv_a0], dtype=np.float64)


try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False


class EQStreamPlayer(QObject):

    stateChanged = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)
    positionChanged = pyqtSignal(int)
    trackEnded = pyqtSignal()

    def __init__(self, processor: EqualizerProcessor, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.processor = processor
        self._volume = 1.0
        self._playing = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._ffmpeg_path: Optional[str] = None
        self._total_frames = 0
        self._sample_rate = 44100
        self._tmp_path: Optional[str] = None
        self._seek_ms = 0
        self._user_stop = False
        self._try_locate_ffmpeg()

    def play(self, url: str):
        self.stop()
        self._seek_ms = 0
        self._playing = True
        self._paused = False
        self.stateChanged.emit("buffering")
        self._thread = threading.Thread(target=self._run, args=(url,), daemon=True)
        self._thread.start()

    def stop(self):
        if self._playing:
            self._user_stop = True
            self._playing = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._thread = None
            self.stateChanged.emit("stopped")
        self._cleanup_tmp()

    def seek(self, ms: int):
        if not self._tmp_path or not os.path.exists(self._tmp_path):
            return
        self._seek_ms = max(0, ms)
        self._playing = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if not self._tmp_path or not os.path.exists(self._tmp_path):
            return
        self._playing = True
        self._user_stop = False
        self._thread = threading.Thread(target=self._play_from_temp, daemon=True)
        self._thread.start()

    def toggle_pause(self):
        self._paused = not self._paused
        self.stateChanged.emit("paused" if self._paused else "playing")

    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def set_volume(self, linear: float):
        self._volume = max(0.0, min(1.0, linear))

    def _cleanup_tmp(self):
        if self._tmp_path and os.path.exists(self._tmp_path):
            try:
                os.unlink(self._tmp_path)
            except Exception:
                pass
        self._tmp_path = None

    def _try_locate_ffmpeg(self):
        try:
            import shutil
            if shutil.which("ffmpeg"):
                self._ffmpeg_path = "ffmpeg"
                return
        except Exception:
            pass
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            self._ffmpeg_path = get_ffmpeg_exe()
        except ImportError:
            pass
        for p in (r"C:\ffmpeg\bin\ffmpeg.exe",
                  os.path.expanduser(r"~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe")):
            if os.path.isfile(p):
                self._ffmpeg_path = p
                return

    def _run(self, url: str):
        if not HAS_PYAUDIO:
            self.errorOccurred.emit("PyAudio не установлен. Установи: pip install pyaudio")
            self._playing = False
            return

        tmp_path: Optional[str] = None
        natural_end = False
        try:
            import requests
            import audioread

            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            self._tmp_path = tmp_path
            tmp.close()

            resp = requests.get(url, stream=True, timeout=30,
                                headers={"User-Agent":
                                         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                         "AppleWebKit/537.36"})
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            CHUNK = 65536

            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK):
                    if not self._playing:
                        return
                    f.write(chunk)
                    downloaded += len(chunk)

            if not self._playing:
                return

            self.stateChanged.emit("playing")

            p = pyaudio.PyAudio()
            try:
                self._decode_and_play(tmp_path, p)
                natural_end = self._playing and not self._user_stop
            finally:
                p.terminate()

        except Exception as exc:
            traceback.print_exc()
            self.errorOccurred.emit(str(exc))
        finally:
            self._playing = False
            self.stateChanged.emit("stopped")
            if natural_end:
                self.trackEnded.emit()

    def _play_from_temp(self):
        if not self._tmp_path or not os.path.exists(self._tmp_path):
            self._playing = False
            self.stateChanged.emit("stopped")
            return
        natural_end = False
        p = pyaudio.PyAudio()
        try:
            self.stateChanged.emit("playing")
            self._decode_and_play(self._tmp_path, p)
            natural_end = self._playing and not self._user_stop
        except Exception as exc:
            traceback.print_exc()
            self.errorOccurred.emit(str(exc))
        finally:
            p.terminate()
            self._playing = False
            self.stateChanged.emit("stopped")
            if natural_end:
                self.trackEnded.emit()

    def _decode_and_play(self, path: str, p: pyaudio.PyAudio):
        start_ms = self._seek_ms
        self._seek_ms = 0
        import audioread

        try:
            with audioread.audio_open(path) as af:
                sr = af.samplerate
                ch = af.channels
                self._sample_rate = sr
                self._total_frames = 0
                self.processor.set_sample_rate(sr)
                self.processor.set_channels(ch)

                stream = p.open(format=pyaudio.paFloat32,
                                channels=ch,
                                rate=sr,
                                output=True,
                                frames_per_buffer=2048)

                emit_interval = sr // 5
                frames_since_emit = 0
                frames_to_skip = int(start_ms * sr / 1000) if start_ms > 0 else 0
                frames_skipped = 0

                for buf in af:
                    if not self._playing:
                        break
                    while self._paused and self._playing:
                        import time
                        time.sleep(0.05)

                    raw = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
                    raw = raw.reshape(-1, ch)
                    frames = raw.shape[0]

                    if frames_to_skip > 0 and frames_skipped < frames_to_skip:
                        remaining = frames_to_skip - frames_skipped
                        if frames <= remaining:
                            frames_skipped += frames
                            continue
                        raw = raw[remaining:]
                        frames = raw.shape[0]
                        frames_skipped = frames_to_skip

                    self._total_frames += frames
                    frames_since_emit += frames
                    if frames_since_emit >= emit_interval:
                        self.positionChanged.emit(int(self._total_frames / sr * 1000))
                        frames_since_emit = 0

                    processed = self.processor.process(raw)
                    stream.write((processed * self._volume).astype(np.float32).tobytes())

                stream.close()
            return
        except audioread.DecodeError:
            pass
        except Exception:
            traceback.print_exc()
            return

        if self._ffmpeg_path:
            try:
                sr = 44100
                ch = 2
                self._sample_rate = sr
                self._total_frames = 0
                self.processor.set_sample_rate(sr)
                self.processor.set_channels(ch)

                stream = p.open(format=pyaudio.paFloat32,
                                channels=ch,
                                rate=sr,
                                output=True,
                                frames_per_buffer=2048)

                import subprocess
                cmd = [self._ffmpeg_path]
                if start_ms > 0:
                    cmd.extend(["-ss", str(start_ms / 1000.0)])
                cmd.extend(["-i", path,
                           "-f", "f32le", "-acodec", "pcm_f32le",
                           "-ac", str(ch), "-ar", str(sr),
                           "-hide_banner", "-loglevel", "quiet",
                           "pipe:1"])
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL,
                                        bufsize=4096)

                emit_interval = sr // 5
                frames_since_emit = 0

                try:
                    BYTES_PER_FRAME = ch * 4
                    while self._playing and proc.poll() is None:
                        while self._paused and self._playing:
                            import time
                            time.sleep(0.05)
                        raw = proc.stdout.read(BYTES_PER_FRAME * 2048)
                        if not raw:
                            break
                        data = np.frombuffer(raw, dtype=np.float32).reshape(-1, ch)
                        frames = data.shape[0]
                        self._total_frames += frames
                        frames_since_emit += frames
                        if frames_since_emit >= emit_interval:
                            self.positionChanged.emit(int(self._total_frames / sr * 1000))
                            frames_since_emit = 0
                        processed = self.processor.process(data)
                        stream.write((processed * self._volume).tobytes())
                    if self._playing:
                        remaining = proc.stdout.read()
                        if remaining:
                            data = np.frombuffer(remaining, dtype=np.float32).reshape(-1, ch)
                            frames = data.shape[0]
                            self._total_frames += frames
                            self.positionChanged.emit(int(self._total_frames / sr * 1000))
                            processed = self.processor.process(data)
                            stream.write((processed * self._volume).tobytes())
                finally:
                    proc.kill()
                    proc.wait(timeout=3)

                stream.close()
                return
            except Exception:
                traceback.print_exc()

        self.errorOccurred.emit(
            "Не удалось декодировать аудио. Установи ffmpeg:\n"
            "  pip install imageio-ffmpeg\n"
            "или добавь ffmpeg.exe в PATH."
        )


class ToneGenerator:

    @staticmethod
    def pink_noise(duration_sec: float = 2.0, sample_rate: int = 44100,
                   channels: int = 2) -> np.ndarray:
        n = int(duration_sec * sample_rate)
        white = np.random.randn(n)
        pink = np.zeros(n)
        for i in range(1, n):
            pink[i] = pink[i-1] + white[i] * 0.02 - white[max(0, i-100)] * 0.005
        peak = np.max(np.abs(pink))
        if peak > 0:
            pink /= peak
        return np.tile(pink.reshape(-1, 1), (1, channels)).astype(np.float32)

    @staticmethod
    def sine_sweep(duration_sec: float = 3.0, sample_rate: int = 44100,
                   channels: int = 2) -> np.ndarray:
        n = int(duration_sec * sample_rate)
        t = np.linspace(0, duration_sec, n, endpoint=False)
        f_start, f_end = 20.0, 20000.0
        k = duration_sec / np.log(f_end / f_start)
        sweep = np.sin(2 * np.pi * f_start * k * (np.exp(t / k) - 1))
        sweep *= np.linspace(0.1, 1.0, n)
        return np.tile(sweep.reshape(-1, 1), (1, channels)).astype(np.float32)
