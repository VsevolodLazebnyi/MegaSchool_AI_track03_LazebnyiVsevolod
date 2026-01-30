import os
import json
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


class MistralAnswerEvaluator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        temperature: float = 0.2
    ):
        api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in .env")

        model = model or os.getenv("MISTRAL_EVAL_MODEL", "mistral-small-latest")

        self.llm = ChatMistralAI(
            model=model,
            api_key=api_key,
            temperature=temperature
        )

        self.prompt = ChatPromptTemplate.from_template("""
Ты — строгий технический экзаменатор.
Оцени ответ кандидата на вопрос.

Вопрос: {question}
Ответ: {answer}
Контекст: {context}

Верни ТОЛЬКО JSON (без markdown/```):
{{
  "score": 0-100,
  "correct": true/false,
  "mistakes": ["..."],
  "good_points": ["..."],
  "topics_to_repeat": ["..."],
  "short_feedback": "1-2 предложения на русском"
}}
""")

        self.chain = self.prompt | self.llm | StrOutputParser()

    def evaluate_answer(self, question: str, answer: str, context: str = "") -> Dict:
        raw = self.chain.invoke({"question": question, "answer": answer, "context": context})
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(clean)
        except Exception:
            data = {
                "score": 0,
                "correct": False,
                "mistakes": ["Не удалось распарсить JSON оценщика."],
                "good_points": [],
                "topics_to_repeat": [],
                "short_feedback": clean[:300]
            }
        return data


class GPT4FreeEvaluator:
    def evaluate_answer(self, question: str, answer: str, context: str = "") -> Dict:
        return {
            "score": 0,
            "feedback": "GPT4FreeEvaluator не подключен (заглушка).",
            "correctness": "unknown",
            "topics_mentioned": [],
            "suggested_topics": []
        }

    def generate_final_report(self, questions: List[str], answers: List[str], evaluations: List[Dict], position: str) -> Dict:
        scores = [e.get("score", 0) for e in evaluations] if evaluations else []
        avg = sum(scores) / len(scores) if scores else 0
        return {
            "overall_score": int(avg),
            "verdict": "Не определен",
            "grade_estimate": "Не определен",
            "detailed_feedback": "Нет данных для детального отчета.",
            "strengths": [],
            "weaknesses": [],
            "topics_to_study": [],
            "recommendations": []
        }


def aggregate_final(
    position: str,
    questions: List[str],
    answers: List[str],
    per_turn: List[Dict],
    correct_threshold: int = 70
) -> Dict:
    scores = [t.get("combined", {}).get("score", 0) for t in per_turn] if per_turn else []
    avg = sum(scores) / len(scores) if scores else 0

    correct_flags = [bool(t.get("combined", {}).get("score", 0) >= correct_threshold) for t in per_turn]
    correct_percent = (sum(correct_flags) / len(correct_flags) * 100.0) if correct_flags else 0.0

    strengths = []
    weaknesses = []
    topics = []

    for t in per_turn:
        c = t.get("combined", {})
        strengths += c.get("good_points", []) or []
        weaknesses += c.get("mistakes", []) or []
        topics += c.get("topics_to_repeat", []) or []

    def uniq(xs):
        seen = set()
        out = []
        for x in xs:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    strengths = uniq(strengths)[:7]
    weaknesses = uniq(weaknesses)[:7]
    topics = uniq(topics)[:7]

    verdict = "Hire" if avg >= 75 and correct_percent >= 60 else "No Hire"

    return {
        "overall_score": int(round(avg)),
        "correct_percent": round(correct_percent, 1),
        "verdict": verdict,
        "grade_estimate": "Junior/Middle/Senior (эвристика не настроена)",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "topics_to_study": topics,
        "detailed_feedback": (
            f"Средний балл: {avg:.1f}/100. "
            f"Процент правильных (score>={correct_threshold}): {correct_percent:.1f}%."
        ),
        "recommendations": uniq(topics)[:5]
    }