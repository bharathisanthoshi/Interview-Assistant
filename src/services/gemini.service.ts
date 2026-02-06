import { QuestionDifficulty } from '../store/types';
import { CHAT_RESPONSES } from './constants';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface EvaluationResult {
  score: number;
  judgement: string;
}

interface QuestionResponse {
  question: string;
}

interface EvaluationResponse {
  score: number;
  judgement: string;
  max_score?: number;
}

interface SummaryResponse {
  summary: string;
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // ignore response parsing errors
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export class GeminiService {
  static async generateQuestion(
    difficulty: QuestionDifficulty,
    previousQuestions: string[]
  ): Promise<string> {
    const data = await apiPost<QuestionResponse>('/api/question', {
      difficulty,
      previous_questions: previousQuestions,
    });
    return data.question;
  }

  static async evaluateAnswer(
    question: string,
    answer: string,
    difficulty: QuestionDifficulty
  ): Promise<EvaluationResult> {
    const data = await apiPost<EvaluationResponse>('/api/evaluate', {
      question,
      answer,
      difficulty,
    });

    return { score: data.score, judgement: data.judgement };
  }

  static async generateFinalSummary(
    candidateName: string,
    questions: Array<{
      question: string;
      answer: string;
      score: number;
      difficulty: QuestionDifficulty;
    }>,
    totalScore: number
  ): Promise<string> {
    const data = await apiPost<SummaryResponse>('/api/summary', {
      candidate_name: candidateName,
      questions,
      total_score: totalScore,
    });
    return data.summary;
  }

  static async chatResponse(_message: string, context: string): Promise<string> {
    for (const [key, response] of Object.entries(CHAT_RESPONSES)) {
      if (key === 'default') continue;
      if (context.includes(key)) return response;
    }

    return CHAT_RESPONSES.default;
  }
}
