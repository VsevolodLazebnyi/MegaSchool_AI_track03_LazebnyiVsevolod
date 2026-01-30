from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY not found in .env file")

llm = ChatMistralAI(
    model="mistral-large-latest",
    api_key=api_key,
    temperature=0.6
)

observer_prompt = ChatPromptTemplate.from_template("""
Ты - Опытный Технический Лид (Observer). 
Твоя задача: анализировать интервью в реальном времени и управлять Интервьюером.

КОНТЕКСТ:
Позиция: {position} ({grade})
Сложность (1-10): {difficulty}
История (последние 3): {history}
Ввод кандидата: "{last_user_input}"
Данные с камеры: {vision_data}

ЗАДАЧИ:
1. Валидация: Проверь техническую достоверность ответа. Если кандидат бредит - заметь это.
2. Проверка поведения: Используй данные с камеры (vision_data). Если там телефон - это "Red Flag".
3. Управление: Реши, какой вопрос задать следующим. Углубиться? Сменить тему? 

ВЫВЕДИ ТОЛЬКО JSON:
{{
  "thought_process": "Твои мысли (анализ ответа и поведения)",
  "next_instruction_to_interviewer": "Точная инструкция, что спросить или сказать",
  "difficulty_adjustment": -1 (проще), 0 (так же), 1 (сложнее),
  "status": "continue" или "finish"
}}
""")

interviewer_prompt = ChatPromptTemplate.from_template("""
Ты - Технический Рекрутер. Ты говоришь с кандидатом {candidate_name}.
Твоя цель: выполнить инструкцию Ментора, сохраняя профессиональный тон.

Инструкция Ментора: {observer_instruction}
Предыдущий ответ кандидата: {last_user_input}

Сформулируй свой ответ/вопрос кандидату. Будь краток и четок.
Текст ответа:
""")

feedback_prompt = ChatPromptTemplate.from_template("""
Составь финальный отчет по интервью для {position}.
Мысли Ментора за все время:
{all_observer_thoughts}

Формат Markdown:
# Результат
**Грейд:** ...
**Решение:** ... (Hire/No Hire)

# Анализ
* Hard Skills: (что знает, что нет)
* Soft Skills & Поведение: (честность, списывал ли)
* Рекомендации: ...
""")

observer_chain = observer_prompt | llm | StrOutputParser()
interviewer_chain = interviewer_prompt | llm | StrOutputParser()
feedback_chain = feedback_prompt | llm | StrOutputParser()