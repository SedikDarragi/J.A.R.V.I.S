import io
import time
import wave
from collections import deque

import numpy as np
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SECONDS = 0.1
BLOCK_SAMPLES = int(SAMPLE_RATE * BLOCK_SECONDS)
PREROLL_BLOCKS = 5
MAX_SPEECH_SECONDS = 12.0
MIN_SPEECH_SECONDS = 0.35
SILENCE_END_SECONDS = 1.2
MIN_LEVEL = 0.012
NOISE_EMA = 0.9


class SpeechToText:
    def __init__(self, language: str = "en-US", device: int | None = None):
        self.language = language
        self.device = device
        self.recognizer = sr.Recognizer()
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
        for block in self._stream_blocks():
            if should_record():
                if recording is None:
                    recording = list(preroll)
                recording.append(block)
            elif recording is not None:
                break
            else:
                preroll.append(block)
        if not recording:
            return None
        return np.concatenate(recording)

    def record_utterance(self):
        state = {"noise": 0.01, "utterance": None, "last_speech": None, "start": None}
        for block in self._stream_blocks():
            rms = float(np.sqrt(np.mean(block ** 2)))
            state["noise"] = NOISE_EMA * state["noise"] + (1 - NOISE_EMA) * min(rms, 0.05)
            threshold = max(MIN_LEVEL, state["noise"] * 2.5)
            speaking = rms > threshold
            if speaking:
                state["last_speech"] = time.time()
                if state["utterance"] is None:
                    state["utterance"] = []
                    state["start"] = time.time()
                state["utterance"].append(block)
            elif state["utterance"] is not None:
                state["utterance"].append(block)
                if time.time() - state["last_speech"] > SILENCE_END_SECONDS:
                    break
                if time.time() - state["start"] > MAX_SPEECH_SECONDS:
                    break
        if not state["utterance"]:
            return None
        audio = np.concatenate(state["utterance"])
        if len(audio) / SAMPLE_RATE < MIN_SPEECH_SECONDS:
            return None
        return audio

    def transcribe(self, audio) -> str | None:
        if audio is None:
            return None
        pcm = self._audio_to_pcm(audio)
        audio_data = sr.AudioData(pcm.tobytes(), SAMPLE_RATE, 2)
        try:
            return self.recognizer.recognize_google(audio_data, language=self.language)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            raise RuntimeError(f"speech-to-text service error: {e}")
