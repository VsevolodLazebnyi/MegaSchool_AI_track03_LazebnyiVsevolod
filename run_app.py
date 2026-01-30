import streamlit as st
import numpy as np
from PIL import Image
import time
from datetime import datetime, timedelta
from modules.graph import build_graph
from modules.vision import VisionSystem
from modules.audio import AudioSystem
from modules.utils import save_log
import warnings
warnings.filterwarnings("ignore", message=".*NNPACK.*")

st.set_page_config(page_title="AI Interview Coach (Local)", layout="wide")

if 'vision' not in st.session_state:
    st.session_state.vision = VisionSystem()
if 'audio' not in st.session_state:
    st.session_state.audio = AudioSystem()
if 'graph' not in st.session_state:
    st.session_state.graph = build_graph()
if 'history' not in st.session_state:
    st.session_state.history = []
if 'use_tts' not in st.session_state:
    st.session_state.use_tts = True
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'answer_start_time' not in st.session_state:
    st.session_state.answer_start_time = None
if 'answer_timeout' not in st.session_state:
    st.session_state.answer_timeout = 120
if 'question_skipped' not in st.session_state:
    st.session_state.question_skipped = False
if 'pending_input' not in st.session_state:
    st.session_state.pending_input = None

with st.sidebar:
    st.header("Настройки кандидата")
    name = st.text_input("Имя", "Всеволод")
    position = st.selectbox("Позиция", ["Python Backend", "Frontend React", "Data Scientist"])
    grade = st.selectbox("Грейд", ["Junior", "Middle", "Senior"])
    st.session_state.use_tts = st.checkbox("Озвучивать вопросы", value=True)

    total_q = st.number_input("Количество вопросов", min_value=1, max_value=50, value=10, step=1)
    st.session_state.total_questions = int(total_q)
    
    st.markdown("---")
    st.subheader("Управление аудио")
    
    if st.button("Проверить звук"):
        st.info("Проверка звука...")
        st.session_state.audio.play_audio_streamlit(
            "Проверка звука. Если вы слышите это сообщение, звук работает корректно."
        )
    
    if st.button("Начать собеседование", type="primary"):
        st.session_state.history = []
        st.session_state.recording = False
        st.session_state.answer_start_time = None
        st.session_state.question_skipped = False
        st.session_state.pending_input = None
        st.session_state.graph_state = {
            "participant_name": name,
            "position": position,
            "grade": grade,
            "history": [],
            "turns": [],
            "current_difficulty": 5,
            "last_user_input": "",
            "vision_context": "Camera active",
            "observer_instruction": "",
            "all_observer_thoughts": [],
            "final_feedback": "",
            "conversation_active": True,
            "total_questions": st.session_state.get('total_questions', 10),
            "current_question_number": 0
        }
        
        with st.spinner("Запуск собеседования..."):
            initial = st.session_state.graph.invoke(st.session_state.graph_state)
            st.session_state.graph_state = initial
            st.session_state.answer_start_time = datetime.now()
            
            if initial.get('turns') and len(initial['turns']) > 0:
                first_msg = initial['turns'][-1].get('agent_visible_message', '')
                if first_msg:
                    st.session_state.history.append({
                        "role": "ai", 
                        "content": first_msg, 
                        "id": len(st.session_state.history)
                    })
            else:
                st.warning("Не удалось получить первый вопрос")
        
        st.rerun()

st.title("AI Tech Interviewer")


if 'graph_state' not in st.session_state:
    st.info("👈 Заполните данные слева и нажмите 'Начать собеседование'.")
    
    with st.expander("ℹ️ Как пользоваться системой"):
        st.markdown("""
        ### 🎤 Запись голоса
        1. Нажмите кнопку **🎤 Записать** внизу экрана
        2. Говорите ваш ответ четко и громко
        3. После окончания речи система автоматически отправит ответ
        4. Или дождитесь **2-минутного таймера** — вопрос будет пропущен
        
        ### 🔊 Звук
        - Нажмите "Проверить звук" в боковой панели
        - Разрешите воспроизведение в браузере
        - Кнопка 🔊 рядом с вопросом — повторное прослушивание
        
        ### ⏱️ Таймеры
        - **45 сек** — максимальное время записи на один вопрос
        - **2 мин** — общий таймер на ответ, после истечения вопрос пропускается
        """)
    
    st.stop()

with st.expander("Vision Monitoring", expanded=True):
    col_cam, col_stat = st.columns([1, 2])
    with col_cam:
        img_file = st.camera_input("Снимок для анализа", key="camera_input")
    
    vision_status = "Ожидание снимка..."
    if img_file:
        try:
            image = Image.open(img_file)
            frame = np.array(image)
            vision_status = st.session_state.vision.analyze_frame(frame)
            st.session_state.graph_state['vision_context'] = vision_status
        except Exception as e:
            vision_status = f"Ошибка камеры: {str(e)}"
            st.session_state.graph_state['vision_context'] = "Camera error"
    
    with col_stat:
        st.write(f"Статус: {vision_status}")
        if "ALERT" in vision_status:
            st.error("ВНИМАНИЕ: Обнаружено подозрительное поведение!")

st.subheader("Диалог собеседования")
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "ai" and msg["content"]:
                if st.button("Воспроизвести", key=f"audio_btn_{i}"):
                    st.session_state.audio.play_audio_streamlit(msg["content"])

st.divider()
st.subheader("Время на ответ")

if st.session_state.get('answer_start_time') and st.session_state.graph_state.get('conversation_active'):
    elapsed = (datetime.now() - st.session_state.answer_start_time).total_seconds()
    remaining = st.session_state.answer_timeout - elapsed
    
    col_timer, col_rec_time = st.columns(2)
    
    with col_timer:
        if remaining > 0:
            if remaining > 60:
                state_label = "OK"
            elif remaining > 30:
                state_label = "WARN"
            else:
                state_label = "ALERT"
            
            st.metric(
                "Осталось времени",
                f"{int(remaining)} сек",
                f"{int(elapsed)} / {int(st.session_state.answer_timeout)} сек"
            )
        else:
            st.error("ВРЕМЯ ИСТЕКЛО! Вопрос пропущен.")
            st.session_state.question_skipped = True
    
    with col_rec_time:
        if st.session_state.recording:
            st.warning("Идет запись")
        else:
            st.info("Готово к ответу")

st.divider()
st.subheader("Ваш ответ")

col_text, col_rec, col_help = st.columns([4, 1, 1])

with col_text:
    user_text = st.chat_input("Напишите ответ или нажмите на кнопку для записи голоса...")

with col_rec:
    if st.session_state.graph_state.get('conversation_active') and not st.session_state.question_skipped:
        if st.button("Записать голос", key="mic_button", use_container_width=True):
            st.session_state.recording = True
            st.session_state.pending_input = None
            st.rerun()

with col_help:
    if st.button("Справка", help="Справка", use_container_width=True):
        st.info("""
        Способы ответа:
        - Введите текст в поле ввода
        - Нажмите "Записать голос"
        
        После нажатия на запись:
        - Говорите четко и громко
        - Система автоматически распознает речь
        - Ответ отправится сам после окончания речи
        """)

if st.session_state.recording and st.session_state.graph_state.get('conversation_active'):
    if not st.session_state.question_skipped:
        st.warning("Идет запись... Говорите ваш ответ (до 45 сек)")
        
        with st.spinner("Распознавание речи..."):
            text = st.session_state.audio.listen_from_mic(timeout=5, phrase_time_limit=45)
            
            if text:
                st.session_state.pending_input = text
                st.session_state.recording = False
                st.success(f"Распознано: {text}")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.recording = False
                st.warning("Речь не распознана. Попробуйте еще раз или введите текст.")
                st.rerun()

input_val = None
if st.session_state.pending_input:
    input_val = st.session_state.pending_input
    st.session_state.pending_input = None  # Очищаем after use
elif user_text:
    input_val = user_text

if input_val and st.session_state.graph_state.get('conversation_active'):
    st.session_state.history.append({
        "role": "user", 
        "content": input_val,
        "id": len(st.session_state.history)
    })
    st.session_state.graph_state['last_user_input'] = input_val
    
    with st.spinner("Интервьюер анализирует ответ..."):
        new_state = st.session_state.graph.invoke(st.session_state.graph_state)
        st.session_state.graph_state = new_state
        st.session_state.answer_start_time = datetime.now()
        st.session_state.question_skipped = False
        
        if new_state.get('final_feedback'):
            st.session_state.history.append({
                "role": "ai", 
                "content": "Интервью окончено. Формирую итоговый отчет...",
                "id": len(st.session_state.history)
            })
            save_log(name, new_state['turns'], new_state['final_feedback'])
        else:
            if new_state['turns']:
                ai_msg = new_state['turns'][-1].get('agent_visible_message', '')
                if ai_msg:
                    msg_id = len(st.session_state.history)
                    st.session_state.history.append({
                        "role": "ai", 
                        "content": ai_msg,
                        "id": msg_id
                    })
                    if st.session_state.use_tts:
                        st.info("Воспроизведение следующего вопроса...")
                        st.session_state.audio.play_audio_streamlit(ai_msg)
    
    st.rerun()

if st.session_state.get('answer_start_time') and st.session_state.graph_state.get('conversation_active'):
    elapsed = (datetime.now() - st.session_state.answer_start_time).total_seconds()
    if elapsed > st.session_state.answer_timeout and not st.session_state.question_skipped:
        st.session_state.question_skipped = True
        st.session_state.history.append({
            "role": "system", 
            "content": "Время на ответ истекло. Вопрос пропущен и не будет учитываться в оценке.",
            "id": len(st.session_state.history)
        })
        
        with st.spinner("Переход к следующему вопросу..."):
            new_state = st.session_state.graph.invoke({
                **st.session_state.graph_state,
                'last_user_input': '[SKIPPED - Timeout]',
            })
            st.session_state.graph_state = new_state
            st.session_state.answer_start_time = datetime.now()
            
            if new_state.get('turns'):
                ai_msg = new_state['turns'][-1].get('agent_visible_message', '')
                if ai_msg:
                    st.session_state.history.append({
                        "role": "ai", 
                        "content": ai_msg,
                        "id": len(st.session_state.history)
                    })
                    
                    if st.session_state.use_tts:
                        st.session_state.audio.play_audio_streamlit(ai_msg)
        
        st.rerun()

if st.session_state.graph_state.get('final_feedback'):
    st.divider()
    st.subheader("Результаты интервью")
    st.markdown(st.session_state.graph_state['final_feedback'])
    
    col_audio, col_download = st.columns(2)
    
    with col_audio:
        if st.button("Озвучить полный отчет"):
            st.session_state.audio.play_audio_streamlit(
                st.session_state.graph_state['final_feedback']
            )
    
    with col_download:
        try:
            with open("interview_log.json", "rb") as f:
                st.download_button(
                    "Скачать лог", 
                    f, 
                    "interview_log.json",
                    help="Скачать полный лог собеседования в формате JSON"
                )
        except:
            st.warning("Лог собеседования не найден")

if st.session_state.graph_state.get('turns'):
    with st.expander("Анализ"):
        last_turn = st.session_state.graph_state['turns'][-1]
        st.write(last_turn.get('internal_thoughts', ''))

with st.sidebar:
    st.markdown("---")
    st.subheader("Управление звуком")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Откл.", use_container_width=True):
            st.session_state.use_tts = False
            st.rerun()
    
    with col2:
        if st.button("Вкл.", use_container_width=True):
            st.session_state.use_tts = True
            st.rerun()
    
    st.caption(f"{'Озвучка: ВКЛ' if st.session_state.use_tts else 'Озвучка: ВЫКЛ'}")