import os
import re
import sys

import numpy as np
import sounddevice as sd

from piper import PiperVoice

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VOICE = os.path.join(_BASE_DIR, "voices", "en_GB-alan-medium.onnx")


class JarvisVoice:
    def __init__(self, voice_path: str = DEFAULT_VOICE):
        self.voice = PiperVoice.load(voice_path)
        self.sample_rate = self.voice.config.sample_rate

    def _clean(self, text: str) -> str:
        text = re.sub(r"[*_`#\[\]]+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def speak(self, text: str, blocking: bool = True) -> None:
        text = self._clean(text)
        if not text:
            return
        audio = bytearray()
        for chunk in self.voice.synthesize(text):
            if chunk.audio_int16_bytes is not None:
                audio.extend(chunk.audio_int16_bytes)
        if not audio:
            return
        samples = np.frombuffer(bytes(audio), dtype=np.int16)
        sd.play(samples, self.sample_rate)
        if blocking:
            sd.wait()
