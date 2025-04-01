import io
import os
import threading
import wave

import keyboard
import pyaudio
from google.cloud import speech

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'data/practical-link-410619-651baa0933cd.json'

class VoiceGpt:
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    def __init__(self):
        self.audio_frames = []
        self.stop_event = threading.Event()
        self.recording_thread = threading.Thread(target=self.continuously_capture_audio)

    def get_stereo_mix_index(self):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if (dev['name'] == 'Stereomix (Realtek(R) Audio)' and dev['hostApi'] == 0):
                return dev['index']
        raise Exception("Stereo Mix device not found")

    def save_audio(self, filename="logs/output.wav"):
        p = pyaudio.PyAudio()
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.audio_frames))
        wf.close()
        print(f"Audio saved to {filename}")

    def continuously_capture_audio(self):
        p = pyaudio.PyAudio()
        stereo_mix_index = self.get_stereo_mix_index()

        stream = p.open(format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.CHUNK,
                        input_device_index=stereo_mix_index)

        print("Starting continuous recording...")
        while not self.stop_event.is_set():
            data = stream.read(self.CHUNK)
            self.audio_frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def convert_to_text(self):
        client = speech.SpeechClient()

        audio_stream = io.BytesIO()
        with wave.open(audio_stream, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(pyaudio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.audio_frames))
        
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

    def handle_operations(self):
        self.recording_thread.start()
        try:
            while True:
                if keyboard.is_pressed('½'):  # Detect the specific key press
                    # self.save_audio()
                    print("Processing audio...")
                    text = self.convert_to_text()
                    print("Transcribed Text:", text)
                    self.audio_frames.clear()  # Clear the buffer after processing
        except KeyboardInterrupt:
            print("Exiting...")
            self.stop_event.set()
            self.recording_thread.join()