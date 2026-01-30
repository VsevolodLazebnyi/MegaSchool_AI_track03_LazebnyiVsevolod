import speech_recognition as sr
from gtts import gTTS
import base64
import io
import streamlit as st

class AudioSystem:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            print(f"Microphone init warning: {e}")

    def listen_from_mic(self, timeout=5, phrase_time_limit=10):
        try:
            with sr.Microphone() as source:
                print("Слушаю...")
                audio_data = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                print("Распознаю...")
                text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"Ошибка микрофона: {e}")
            return None

    def text_to_speech_base64(self, text, lang='ru'):
        if not text:
            return None, 0
        
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            audio_bytes = audio_buffer.read()
            b64 = base64.b64encode(audio_bytes).decode()
            return b64, len(audio_bytes)
        except Exception as e:
            print(f"TTS Error: {e}")
            return None, 0

    def play_audio_streamlit(self, text):
        if not text:
            return
        
        try:
            tts = gTTS(text=text, lang='ru', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            st.audio(audio_buffer, format="audio/mp3")
        except Exception as e:
            st.error(f"Ошибка воспроизведения: {e}")

    def create_audio_button(self, text, button_text="Воспроизвести"):
        if not text:
            return False
        
        if st.button(button_text, key=f"btn_{hash(text)}"):
            self.play_audio_streamlit(text)
            return True
        return False