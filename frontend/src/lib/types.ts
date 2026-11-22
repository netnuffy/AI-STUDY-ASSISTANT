/* Types mirroring the FastAPI backend schemas (backend/schemas/*.py). */

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type DocumentStatus = "uploading" | "processing" | "ready" | "failed";

export interface StudyDocument {
  id: string;
  title: string;
  filename: string;
  file_size_bytes: number;
  page_count: number | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface KeyConcept {
  term: string;
  definition: string;
}

export interface Summary {
  document_id: string;
  content: string;
  key_points: string[];
  key_concepts: KeyConcept[];
  important_questions: string[];
}

export interface RecentSummary {
  document_id: string;
  document_title: string;
  content_preview: string;
  key_points_count: number;
  updated_at: string;
}

export interface ChatSource {
  page: number | null;
  excerpt: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  document_id: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  document_id: string | null;
  created_at: string;
}

export interface Flashcard {
  id: string;
  document_id: string;
  front: string;
  back: string;
  difficulty: string;
  known: boolean;
  review_count: number;
  last_reviewed_at: string | null;
}

export type QuestionType = "multiple_choice" | "true_false" | "short_answer";

export interface QuizQuestionPublic {
  type: QuestionType;
  question: string;
  options: string[] | null;
}

export interface Quiz {
  id: string;
  document_id: string;
  title: string;
  questions: QuizQuestionPublic[];
  created_at: string;
}

export interface QuizResultItem {
  type: QuestionType;
  question: string;
  selected: number | string | null;
  correct: number | string;
  is_correct: boolean;
  explanation: string;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  results: QuizResultItem[];
}

export interface QuizAttempt {
  id: string;
  quiz_id: string;
  score: number;
  total: number;
  answers: (number | string)[];
  completed_at: string;
}

export interface RecentQuizAttempt {
  id: string;
  quiz_id: string;
  quiz_title: string;
  score: number;
  total: number;
  percentage: number;
  completed_at: string;
}

export interface PlanTask {
  date: string;
  topic: string;
  document_id: string | null;
  minutes: number;
  done: boolean;
}

export interface WeeklyGoal {
  week: number;
  goal: string;
  start_date: string | null;
  end_date: string | null;
}

export interface RevisionItem {
  date: string;
  topic: string;
  minutes: number;
}

export interface StudyPlan {
  id: string;
  title: string;
  goal: string;
  exam_date: string | null;
  daily_minutes: number;
  tasks: PlanTask[];
  weekly_goals: WeeklyGoal[];
  revision_schedule: RevisionItem[];
  is_active: boolean;
  created_at: string;
}

export interface ProgressStats {
  total_minutes: number;
  streak_days: number;
  total_documents: number;
  total_quizzes_taken: number;
  average_quiz_score: number | null;
  flashcards_known: number;
  flashcards_total: number;
}

export interface ActivityPoint {
  date: string;
  minutes: number;
}
