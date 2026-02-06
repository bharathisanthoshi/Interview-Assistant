\
import random
import re
from dataclasses import dataclass
from typing import Dict, List

TECHNICAL_TERMS = [
    "component", "hook", "state", "props", "render", "virtual dom",
    "async", "await", "promise", "callback", "closure", "scope",
    "api", "rest", "graphql", "middleware", "authentication",
    "optimization", "performance", "memoization", "lazy loading",
    "reconciliation", "redux", "context", "useeffect", "usestate",
    "jsx", "typescript", "node.js", "express", "mongodb", "sql",
    "jwt", "token", "cache", "redis", "websocket", "ssr", "csr",
]

CODE_PATTERNS = [
    re.compile(r"```[\s\S]*?```"),
    re.compile(r"`[^`]+`"),
    re.compile(r"\b(function|const|let|var|if|else|return|import|export)\b"),
    re.compile(r"[{}\[\]();]"),
    re.compile(r"=>"),
]

EXPLANATION_PATTERNS = [
    re.compile(r"\b(because|since|due to|reason|allows|enables|helps)\b", re.I),
    re.compile(r"\b(for example|such as|like|including)\b", re.I),
    re.compile(r"\b(first|second|then|finally|additionally)\b", re.I),
]

QUESTION_BANK = {
    "EASY": [
        "What is JSX in React and why is it useful?",
        "Explain the difference between let, const, and var in JavaScript.",
        "What are props in React components?",
        "What is the purpose of the useState hook?",
        "How do you handle events in React?",
        "What is the virtual DOM in React?",
        "What is the difference between == and === in JavaScript?",
        "Explain what arrow functions are and their benefits.",
    ],
    "MEDIUM": [
        "Explain how the useEffect hook works in React and its dependency array.",
        "What is the difference between controlled and uncontrolled components?",
        "How does async/await work in JavaScript?",
        "Explain React Context API and when you would use it.",
        "What are Higher Order Components (HOCs) in React?",
        "How would you optimize a React component that re-renders too often?",
        "Explain closure in JavaScript with a practical example.",
        "What is the difference between REST and GraphQL APIs?",
    ],
    "HARD": [
        "How would you optimize performance in a large React application?",
        "Explain the concept of reconciliation in React and how keys work.",
        "Design a scalable folder structure for a large React/Node.js application.",
        "How would you implement server-side rendering with React?",
        "Explain memory leaks in JavaScript and how to prevent them.",
        "Design a caching strategy for a REST API with Redis.",
        "How would you implement authentication using JWT in a Node.js application?",
        "Explain the Event Loop in Node.js and how it handles asynchronous operations.",
    ],
}

DIFFICULTY_CONTEXT = {
    "EASY": "basic concepts like variables, functions, simple syntax",
    "MEDIUM": "intermediate topics like APIs, state management, async operations",
    "HARD": "advanced concepts like optimization, architecture, design patterns",
}

MAX_SCORES = {
    "EASY": 10,
    "MEDIUM": 20,
    "HARD": 30,
}

SCORING_THRESHOLDS = {
    "wordCount": {
        "minimal": 10,
        "short": 25,
        "medium": 50,
        "long": 100,
    },
    "baseScores": {
        "minimal": 0.2,
        "short": 0.4,
        "medium": 0.6,
        "long": 0.75,
        "extensive": 0.85,
    },
    "bonuses": {
        "technicalTermMax": 0.2,
        "technicalTermMultiplier": 0.05,
        "codeExample": 0.15,
        "explanation": 0.1,
        "complexityMax": 0.1,
    },
    "difficultyMultipliers": {
        "EASY": 0.9,
        "MEDIUM": 0.85,
        "HARD": 0.8,
    },
    "finalScore": {
        "min": 0.15,
        "max": 0.95,
    },
}

PERFORMANCE_THRESHOLDS = {
    "exceptional": 85,
    "strong": 75,
    "solid": 65,
    "adequate": 50,
}


@dataclass
class QuestionMetrics:
    word_count: int
    has_code_example: bool
    technical_term_count: int
    has_explanation: bool
    complexity: float


def get_fallback_question(difficulty: str, previous_questions: List[str]) -> str:
    diff = difficulty.upper()
    questions = QUESTION_BANK[diff]
    available = [q for q in questions if q not in previous_questions]
    pool = available if available else questions
    return random.choice(pool)


def analyze_answer(answer: str) -> QuestionMetrics:
    words = [w for w in re.split(r"\s+", answer.strip()) if w]
    word_count = len(words)

    has_code_example = any(pattern.search(answer) for pattern in CODE_PATTERNS)

    lower_answer = answer.lower()
    technical_term_count = sum(1 for term in TECHNICAL_TERMS if term in lower_answer)

    has_explanation = any(pattern.search(answer) for pattern in EXPLANATION_PATTERNS)

    sentences = [s for s in re.split(r"[.!?]+", answer) if len(s.strip()) > 10]
    avg_sentence_length = (len(words) / len(sentences)) if sentences else 0

    complexity = min(
        (avg_sentence_length / 15)
        + (technical_term_count * 0.1)
        + (0.3 if has_code_example else 0),
        1.0,
    )

    return QuestionMetrics(
        word_count=word_count,
        has_code_example=has_code_example,
        technical_term_count=technical_term_count,
        has_explanation=has_explanation,
        complexity=complexity,
    )


def get_intelligent_evaluation(answer: str, difficulty: str) -> Dict[str, str | int]:
    diff = difficulty.upper()
    metrics = analyze_answer(answer)

    wc = SCORING_THRESHOLDS["wordCount"]
    bs = SCORING_THRESHOLDS["baseScores"]

    if metrics.word_count < wc["minimal"]:
        base_score = bs["minimal"]
    elif metrics.word_count < wc["short"]:
        base_score = bs["short"]
    elif metrics.word_count < wc["medium"]:
        base_score = bs["medium"]
    elif metrics.word_count < wc["long"]:
        base_score = bs["long"]
    else:
        base_score = bs["extensive"]

    bonuses = SCORING_THRESHOLDS["bonuses"]
    technical_bonus = min(
        metrics.technical_term_count * bonuses["technicalTermMultiplier"],
        bonuses["technicalTermMax"],
    )
    code_bonus = bonuses["codeExample"] if metrics.has_code_example else 0
    explanation_bonus = bonuses["explanation"] if metrics.has_explanation else 0
    complexity_bonus = metrics.complexity * bonuses["complexityMax"]

    final_score = base_score + technical_bonus + code_bonus + explanation_bonus + complexity_bonus
    final_score *= SCORING_THRESHOLDS["difficultyMultipliers"][diff]

    final_min = SCORING_THRESHOLDS["finalScore"]["min"]
    final_max = SCORING_THRESHOLDS["finalScore"]["max"]
    final_score = min(max(final_score, final_min), final_max)

    score = round(MAX_SCORES[diff] * final_score)

    feedback_parts: List[str] = []

    if metrics.word_count < wc["short"]:
        feedback_parts.append("Consider providing more detailed explanations")
    elif metrics.word_count > wc["long"]:
        feedback_parts.append("Comprehensive answer with good depth")
    else:
        feedback_parts.append("Good level of detail in your explanation")

    if metrics.has_code_example:
        feedback_parts.append("excellent use of code examples to illustrate concepts")
    elif diff != "EASY":
        feedback_parts.append("adding code examples would strengthen your answer")

    if metrics.technical_term_count >= 3:
        feedback_parts.append("strong technical vocabulary demonstrated")
    elif metrics.technical_term_count == 0:
        feedback_parts.append("include more technical terminology to show depth of knowledge")

    if metrics.has_explanation:
        feedback_parts.append("clear reasoning and structure")

    judgement = ", ".join(feedback_parts[:2]).strip() + "."
    if judgement:
        judgement = judgement[0].upper() + judgement[1:]

    return {"score": score, "judgement": judgement}


def get_intelligent_summary(
    candidate_name: str,
    questions: List[Dict[str, str | int]],
    total_score: int,
    percentage: int,
) -> str:
    performance_by_difficulty = {
        "EASY": {"scores": [], "max": MAX_SCORES["EASY"]},
        "MEDIUM": {"scores": [], "max": MAX_SCORES["MEDIUM"]},
        "HARD": {"scores": [], "max": MAX_SCORES["HARD"]},
    }

    for q in questions:
        diff = str(q.get("difficulty", "")).upper()
        if diff in performance_by_difficulty:
            performance_by_difficulty[diff]["scores"].append(int(q.get("score", 0)))

    def get_average(scores: List[int], max_score: int) -> int:
        if not scores:
            return 0
        return round((sum(scores) / len(scores) / max_score) * 100)

    easy_perf = get_average(
        performance_by_difficulty["EASY"]["scores"],
        performance_by_difficulty["EASY"]["max"],
    )
    medium_perf = get_average(
        performance_by_difficulty["MEDIUM"]["scores"],
        performance_by_difficulty["MEDIUM"]["max"],
    )
    hard_perf = get_average(
        performance_by_difficulty["HARD"]["scores"],
        performance_by_difficulty["HARD"]["max"],
    )

    strengths: List[str] = []
    weaknesses: List[str] = []

    if easy_perf >= 70:
        strengths.append("fundamental concepts")
    elif easy_perf < 50:
        weaknesses.append("basic fundamentals")

    if medium_perf >= 70:
        strengths.append("intermediate problem-solving")
    elif medium_perf < 50:
        weaknesses.append("intermediate topics")

    if hard_perf >= 70:
        strengths.append("advanced architecture and optimization")
    elif hard_perf < 50:
        weaknesses.append("complex system design")

    answer_metrics = [analyze_answer(str(q.get("answer", ""))) for q in questions]
    if answer_metrics:
        avg_technical_terms = sum(m.technical_term_count for m in answer_metrics) / len(answer_metrics)
    else:
        avg_technical_terms = 0
    code_example_count = sum(1 for m in answer_metrics if m.has_code_example)

    if avg_technical_terms >= 3:
        strengths.append("strong technical vocabulary")
    if code_example_count >= 3:
        strengths.append("practical code examples")

    pt = PERFORMANCE_THRESHOLDS
    if percentage >= pt["exceptional"]:
        performance_desc = "exceptional performance"
    elif percentage >= pt["strong"]:
        performance_desc = "strong performance"
    elif percentage >= pt["solid"]:
        performance_desc = "solid performance"
    elif percentage >= pt["adequate"]:
        performance_desc = "adequate performance"
    else:
        performance_desc = "developing performance"

    if percentage >= pt["exceptional"]:
        recommendation = "Strong Yes - Outstanding candidate with deep technical knowledge"
    elif percentage >= pt["strong"]:
        recommendation = "Yes - Solid hire with good technical foundation"
    elif percentage >= 60:
        recommendation = "Maybe - Shows potential, needs development in specific areas"
    else:
        recommendation = "No - Requires significant additional experience"

    strengths_text = (
        f"Demonstrated {' and '.join(strengths[:2])}."
        if strengths
        else "Shows baseline technical awareness."
    )
    weakness_text = f" Needs improvement in {weaknesses[0]}." if weaknesses else ""

    return (
        f"{candidate_name} achieved {total_score}/120 ({percentage}%), "
        f"demonstrating {performance_desc}. {strengths_text}{weakness_text} "
        f"Recommendation: {recommendation}"
    )
