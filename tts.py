import os
import re
import sys

import numpy as np
import sounddevice as sd

from piper import PiperVoice

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VOICE = os.path.join(_BASE_DIR, "voices", "en_GB-alan-medium.onnx")


def _pick_output_device(pref: str = ""):
    try:
        default_out = sd.default.device[1]
    except Exception:
        default_out = None
    try:
        devices = [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_output_channels"] > 0]
    except Exception:
        devices = []
    if pref:
        for i, name in devices:
            if pref.lower() in name.lower():
                return i
    if default_out is not None:
        try:
            sd.check_output_settings(device=default_out)
            return default_out
        except Exception:
            pass
    for i, name in devices:
        if "speaker" in name.lower() or "headphone" in name.lower():
            try:
                sd.check_output_settings(device=i)
                return i
            except Exception:
                continue
    return default_out


class JarvisVoice:
    def __init__(self, voice_path: str = DEFAULT_VOICE, device_pref: str = ""):
        self.voice = PiperVoice.load(voice_path)
        self.sample_rate = self.voice.config.sample_rate
        self._device = _pick_output_device(device_pref) if device_pref else None

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
        samples = np.frombuffer(bytes(audio), dtype=np.int16).astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        print(f"  [speech] play device={self._device} samples={len(samples)} rms={rms:.2f}")
        try:
            sd.play(samples, self.sample_rate, device=self._device)
            if blocking:
                sd.wait()
            print("  [speech] play finished ok")
        except Exception as e:
            print(f"  [speech] playback error: {e}; retrying on default")
            try:
                sd.play(samples, self.sample_rate)
                if blocking:
                    sd.wait()
                print("  [speech] retry finished ok")
            except Exception as e2:
                print(f"  [speech] playback retry failed: {e2}")
