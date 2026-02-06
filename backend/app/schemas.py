\
from pydantic import BaseModel, Field
from typing import List, Literal

Difficulty = Literal["EASY", "MEDIUM", "HARD"]


class QuestionRequest(BaseModel):
    difficulty: Difficulty
    previous_questions: List[str] = Field(default_factory=list)


class QuestionResponse(BaseModel):
    question: str
    source: Literal["gemini", "fallback"]


class EvaluationRequest(BaseModel):
    question: str
    answer: str
    difficulty: Difficulty


class EvaluationResponse(BaseModel):
    score: int
    judgement: str
    max_score: int
    source: Literal["gemini", "fallback"]


class SummaryQuestion(BaseModel):
    question: str
    answer: str
    score: int
    difficulty: Difficulty


class SummaryRequest(BaseModel):
    candidate_name: str
    questions: List[SummaryQuestion]
    total_score: int


class SummaryResponse(BaseModel):
    summary: str
    percentage: int
    source: Literal["gemini", "fallback"]
