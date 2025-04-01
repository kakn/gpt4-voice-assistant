import io
import os
import threading
import time
import wave

import keyboard
from openai import OpenAI
import pyaudio
from dotenv import load_dotenv
from google.cloud import speech

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'data/practical-link-410619-651baa0933cd.json'
load_dotenv()

class VoiceGpt:
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    def __init__(self):
        self.audio_frames = []
        self.start_transcription = None
        self.end_transcription = None
        self.stop_event = threading.Event()
        self.switch_device_event = threading.Event()
        self.current_device_index = self.get_stereo_mix_index()
        self.recording_thread = threading.Thread(target=self.continuously_capture_audio)
        self.five_seconds_frames = 5 * self.RATE // self.CHUNK
        self.client = OpenAI(api_key=os.getenv("OPENAI_SECRET"))

    def get_stereo_mix_index(self):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if (dev['name'] == 'Stereomix (Realtek(R) Audio)' and dev['hostApi'] == 0):
                return dev['index']
        raise Exception("Stereo Mix device not found")

    def get_microphone_index(self):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if (dev['name'] == 'Mikrofon (Realtek(R) Audio)' and dev['hostApi'] == 0):
                return dev['index']
        raise Exception("Microphone device not found")

    def switch_input_device(self):
        if self.current_device_index == self.get_stereo_mix_index():
            print("AIVA: Switching to Microphone")
            self.current_device_index = self.get_microphone_index()
        else:
            print("AIVA: Switching to Stereo Mix")
            self.current_device_index = self.get_stereo_mix_index()
        self.switch_device_event.set()

    def continuously_capture_audio(self):
        p = pyaudio.PyAudio()

        while not self.stop_event.is_set():
            stream = p.open(format=self.FORMAT,
                            channels=self.CHANNELS,
                            rate=self.RATE,
                            input=True,
                            frames_per_buffer=self.CHUNK,
                            input_device_index=self.current_device_index)

            print(f"AIVA: Recording from device index {self.current_device_index}")
            while not self.stop_event.is_set() and not self.switch_device_event.is_set():
                data = stream.read(self.CHUNK)
                self.audio_frames.append(data)

            stream.stop_stream()
            stream.close()
            self.switch_device_event.clear()

        p.terminate()

    def convert_to_text(self):
        client = speech.SpeechClient()

        # Use only the relevant part of the audio for transcription
        relevant_audio = self.audio_frames[self.start_transcription:self.end_transcription]

        audio_stream = io.BytesIO()
        with wave.open(audio_stream, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(pyaudio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(relevant_audio))
        
        audio_stream.seek(0)
        content = audio_stream.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.RATE,
            language_code='en-US'
        )

        response = client.recognize(config=config, audio=audio)

        return ' '.join([result.alternatives[0].transcript for result in response.results])

    def send_message_to_gpt_and_stream_response(self, message):
        stream = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message}],
            stream=True,
        )
        for chunk in stream:
            print(chunk.choices[0].delta.content or "", end="")

    def handle_operations(self):
        self.recording_thread.start()
        try:
            while True:
                if keyboard.is_pressed('å') and self.start_transcription is None:
                    self.start_transcription = max(0, len(self.audio_frames) - self.five_seconds_frames)
                    print("AIVA: Marked start time of transcription...")

                if keyboard.is_pressed('½'):
                    self.end_transcription = len(self.audio_frames)
                    print("AIVA: Processing audio...")
                    text = self.convert_to_text()
                    print("AIVA: Transcribed Text:", text)
                    self.send_message_to_gpt_and_stream_response(text)
                    self.audio_frames.clear()  # Clear the buffer after processing
                    self.start_transcription = None
                    self.end_transcription = None

                if keyboard.is_pressed('ø'):
                    self.switch_input_device()
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("AIVA: Exiting...")
            self.stop_event.set()
            self.recording_thread.join()