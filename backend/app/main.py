import asyncio
import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    QuestionRequest,
    QuestionResponse,
    EvaluationRequest,
    EvaluationResponse,
    SummaryRequest,
    SummaryResponse,
)
from .config import (
    ALLOWED_ORIGINS,
    ALLOWED_ORIGIN_REGEX,
    GEMINI_API_KEY,
    EVALUATION_DELAY_MS,
    SUMMARY_DELAY_MS,
)
from .fallback import (
    DIFFICULTY_CONTEXT,
    MAX_SCORES,
    get_fallback_question,
    get_intelligent_evaluation,
    get_intelligent_summary,
)
from .gemini_client import call_gemini_api

logger = logging.getLogger("interview_assistant")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Crisp Interview Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUESTION_PREFIX_RE = re.compile(
    r"^(Question:|Answer:|Here's a question:|Here is a question:)\s*",
    re.I,
)
SUMMARY_PREFIX_RE = re.compile(
    r"^(Summary:|Here's a summary:|Interview Summary:)\s*",
    re.I,
)


def _clean_question(text: str) -> str:
    question = QUESTION_PREFIX_RE.sub("", text).replace("\n", " ").strip()
    question = question.strip(' "\'')
    if len(question.split()) > 20:
        words = question.split()
        question = " ".join(words[:15]).rstrip("?") + "?"
    if question and not question.endswith("?"):
        question += "?"
    return question


def _clean_summary(text: str) -> str:
    return SUMMARY_PREFIX_RE.sub("", text).strip()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/question", response_model=QuestionResponse)
async def generate_question(req: QuestionRequest) -> QuestionResponse:
    if not GEMINI_API_KEY:
        question = get_fallback_question(req.difficulty, req.previous_questions)
        logger.info(
            "question_source=fallback reason=no_api_key difficulty=%s prev_count=%s",
            req.difficulty,
            len(req.previous_questions),
        )
        return QuestionResponse(question=question, source="fallback")

    try:
        avoid_text = ""
        if req.previous_questions:
            avoid_text = f"\nAvoid: {'; '.join(req.previous_questions[:3])}"

        prompt = (
            f"Generate ONE short {req.difficulty} interview question for Full Stack Developer (React/Node.js).\n\n"
            f"Topic: {DIFFICULTY_CONTEXT[req.difficulty]}{avoid_text}\n\n"
            "Requirements:\n"
            "- Maximum 15 words\n"
            "- Clear and specific\n"
            "- One question only\n"
            "- No explanations\n\n"
            "Return ONLY the question."
        )

        raw = await call_gemini_api(prompt)
        question = _clean_question(raw)

        if not question:
            raise ValueError("Empty question")

        logger.info(
            "question_source=gemini difficulty=%s prev_count=%s",
            req.difficulty,
            len(req.previous_questions),
        )
        return QuestionResponse(question=question, source="gemini")
    except Exception as exc:
        question = get_fallback_question(req.difficulty, req.previous_questions)
        logger.warning(
            "question_source=fallback reason=exception difficulty=%s prev_count=%s error=%s",
            req.difficulty,
            len(req.previous_questions),
            exc,
        )
        return QuestionResponse(question=question, source="fallback")


@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_answer(req: EvaluationRequest) -> EvaluationResponse:
    max_score = MAX_SCORES[req.difficulty]

    if not GEMINI_API_KEY:
        result = get_intelligent_evaluation(req.answer, req.difficulty)
        logger.info(
            "evaluation_source=fallback reason=no_api_key difficulty=%s score=%s",
            req.difficulty,
            result["score"],
        )
        return EvaluationResponse(
            score=result["score"],
            judgement=result["judgement"],
            max_score=max_score,
            source="fallback",
        )

    try:
        await asyncio.sleep(EVALUATION_DELAY_MS / 1000)

        prompt = (
            f"Evaluate this {req.difficulty} interview answer.\n\n"
            f"Q: {req.question}\n"
            f"A: {req.answer}\n\n"
            "Format:\n"
            f"SCORE: [0-{max_score}]\n"
            "FEEDBACK: [2 short sentences]"
        )

        text = await call_gemini_api(prompt)

        score_match = re.search(r"SCORE[:\s]+(\d+)", text, re.I)
        feedback_match = re.search(r"FEEDBACK[:\s]+(.+)", text, re.I | re.S)

        if not score_match:
            raise ValueError("Score not found")

        score = min(int(score_match.group(1)), max_score)
        judgement = (
            feedback_match.group(1).strip()[:250]
            if feedback_match
            else "Your answer shows understanding. Consider providing more specific examples and technical details."
        )
        judgement = re.sub(r"\s+", " ", judgement).strip()

        logger.info(
            "evaluation_source=gemini difficulty=%s score=%s",
            req.difficulty,
            score,
        )
        return EvaluationResponse(
            score=score,
            judgement=judgement,
            max_score=max_score,
            source="gemini",
        )
    except Exception as exc:
        result = get_intelligent_evaluation(req.answer, req.difficulty)
        logger.warning(
            "evaluation_source=fallback reason=exception difficulty=%s score=%s error=%s",
            req.difficulty,
            result["score"],
            exc,
        )
        return EvaluationResponse(
            score=result["score"],
            judgement=result["judgement"],
            max_score=max_score,
            source="fallback",
        )


@app.post("/api/summary", response_model=SummaryResponse)
async def generate_summary(req: SummaryRequest) -> SummaryResponse:
    percentage = round((req.total_score / 120) * 100)

    if not GEMINI_API_KEY:
        summary = get_intelligent_summary(
            req.candidate_name,
            req.questions,
            req.total_score,
            percentage,
        )
        logger.info(
            "summary_source=fallback reason=no_api_key percentage=%s",
            percentage,
        )
        return SummaryResponse(summary=summary, percentage=percentage, source="fallback")

    try:
        await asyncio.sleep(SUMMARY_DELAY_MS / 1000)

        performance = ", ".join(
            [f"Q{i + 1}({q.difficulty}): {q.score}" for i, q in enumerate(req.questions)]
        )

        prompt = (
            f"Professional interview summary for {req.candidate_name}.\n\n"
            f"Score: {req.total_score}/120 ({percentage}%)\n"
            f"Performance: {performance}\n\n"
            "Write 3 sentences covering:\n"
            "1. Performance level\n"
            "2. Key strength\n"
            "3. Recommendation (Strong Yes/Yes/Maybe/No)"
        )

        summary = await call_gemini_api(prompt)
        summary = _clean_summary(summary)

        if not summary:
            raise ValueError("Empty summary")

        logger.info(
            "summary_source=gemini percentage=%s",
            percentage,
        )
        return SummaryResponse(summary=summary, percentage=percentage, source="gemini")
    except Exception as exc:
        summary = get_intelligent_summary(
            req.candidate_name,
            req.questions,
            req.total_score,
            percentage,
        )
        logger.warning(
            "summary_source=fallback reason=exception percentage=%s error=%s",
            percentage,
            exc,
        )
        return SummaryResponse(summary=summary, percentage=percentage, source="fallback")
