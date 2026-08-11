# voice_pipeline.py
import pyttsx3
import pyaudio
import json
import logging
import time
from vosk import Model, KaldiRecognizer
import os

class VoicePipeline:
    def __init__(self):
        # 1. Pick TTS voice/rate settings once (used to configure a fresh engine per utterance --
        #    see note in speak() about why we don't reuse one long-lived pyttsx3 engine).
        self.tts_rate = 180
        self.tts_voice_id = None
        probe_engine = pyttsx3.init()
        for voice in probe_engine.getProperty('voices'):
            if any(name in voice.name.lower() for name in ['zira', 'hazel', 'female', 'sara', 'jenny']):
                self.tts_voice_id = voice.id
                break
        probe_engine.stop()
        
        # 2. Initialize Vosk STT
        model_path = "model"
        if not os.path.exists(model_path):
            error_msg = "Vosk model not found. Ensure the 'model' folder exists in your project directory."
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        
        # 3. Initialize PyAudio Stream with optimized buffer size for real-time processing
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16, 
            channels=1, 
            rate=16000, 
            input=True, 
            frames_per_buffer=1024
        )
        self.stream.start_stream()
        logging.info("Vosk STT Engine Initialized for Real-Time Processing.")

    def listen(self):
        """Instantly processes audio chunks for real-time speech recognition."""
        if not getattr(self, "stream", None):
            # Stream was never opened successfully; don't spin on this forever.
            logging.error("Voice Capture Error: audio stream is not available.")
            time.sleep(2)
            return None
        try:
            while True:
                data = self.stream.read(1024, exception_on_overflow=False)
                # Check if speech is fully uttered or currently being parsed
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        return text
                else:
                    # Optional: Check partial results for instant feedback if needed, 
                    # but returning on AcceptWaveform ensures clean sentences.
                    pass
        except Exception as e:
            logging.error(f"Voice Capture Error: {e}")
            time.sleep(0.5)  # avoid a tight error loop flooding the log/CPU
            return None

    def speak(self, text):
        """Synthesizes text to spoken audio.

        NOTE: pyttsx3 has a well-documented bug (especially with the Windows
        SAPI5 driver) where reusing a single engine instance for repeated
        say()/runAndWait() calls causes it to speak the first time and then
        go silent on later calls. Creating a fresh engine per utterance
        avoids that, at the cost of a small (~tens of ms) init overhead --
        worth it so Yuri reliably responds every single time.
        """
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.tts_rate)
            if self.tts_voice_id:
                engine.setProperty('voice', self.tts_voice_id)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            logging.info(f"Spoke response: {text}")
        except Exception as e:
            logging.error(f"TTS Error: {e}")