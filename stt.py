import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.1
BLOCK_SAMPLES = int(SAMPLE_RATE * BLOCK_SECONDS)
PREROLL_BLOCKS = 6
MAX_SPEECH_SECONDS = 30.0


class SpeechToText:
    def __init__(self, language: str = "en-US", device: int | None = None, engine: str = "auto", whisper_model: str = "base"):
        self.language = language
        self.device = device
        self.engine = engine
        self.whisper_model = whisper_model
        self.recognizer = sr.Recognizer()
        self._whisper = None
        self._whisper_loading = threading.Event()
        if device is None:
            try:
                self.device = sd.default.device[0]
            except Exception:
                self.device = None

    def list_devices(self) -> str:
        lines = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                lines.append(f"  [{i}] {d['name']}")
        return "\n".join(lines)

    def load_whisper_async(self) -> None:
        def _load():
            try:
                from faster_whisper import WhisperModel
                self._whisper = WhisperModel(self.whisper_model, device="cpu", compute_type="int8")
            except Exception:
                self._whisper = None
            finally:
                self._whisper_loading.set()
        threading.Thread(target=_load, daemon=True).start()

    def whisper_ready(self) -> bool:
        return self._whisper is not None

    def _whisper_lang(self) -> str:
        return self.language.split("-")[0].lower()

    def _stream_blocks(self):
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCK_SAMPLES,
            device=self.device,
        )
        with stream:
            while True:
                data, _ = stream.read(BLOCK_SAMPLES)
                yield np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

    def _audio_to_pcm(self, audio):
        return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

    def record_while(self, should_record):
        preroll = deque(maxlen=PREROLL_BLOCKS)
        recording = None
        started_at = None
        for block in self._stream_blocks():
            if should_record():
                if recording is None:
                    recording = list(preroll)
                    started_at = time.time()
                recording.append(block)
                if time.time() - started_at > MAX_SPEECH_SECONDS:
                    break
            elif recording is not None:
                break
            else:
                preroll.append(block)
        if not recording:
            return None
        return np.concatenate(recording)

    def transcribe(self, audio) -> str | None:
        if audio is None:
            return None
        pcm = self._audio_to_pcm(audio)
        text = self._transcribe_whisper(pcm)
        if text is not None:
            return text
        audio_data = sr.AudioData(pcm.tobytes(), SAMPLE_RATE, 2)
        try:
            return self.recognizer.recognize_google(audio_data, language=self.language)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            raise RuntimeError(f"speech-to-text service error: {e}")

    def _transcribe_whisper(self, pcm) -> str | None:
        if self.engine == "google":
            return None
        if not self.whisper_ready():
            self._whisper_loading.wait(timeout=20)
        if not self.whisper_ready():
            return None
        try:
            audio = pcm.astype(np.float32) / 32767.0
            segments, info = self._whisper.transcribe(
                audio, language=self._whisper_lang(), beam_size=1,
                condition_on_previous_text=False, vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text if text.strip() else None
        except Exception:
            return None
