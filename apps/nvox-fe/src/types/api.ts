// Authentication types
export interface SignupRequest {
  email: string;
  password: string;
}

export interface SignupResponse {
  success: boolean;
  user_id: string;
  email: string;
  message: string;
  journey: {
    current_stage: string;
    started_at: string;
  };
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
}

export interface QuestionConstraints {
  min?: number;
  max?: number;
}

export interface Question {
  id: string;
  text: string;
  type: "number" | "boolean" | "text" | "string";
  constraints?: QuestionConstraints;
  previous_answer?: number | boolean | string;
}

export interface JourneyState {
  user_id: string;
  current_stage: string;
  stage_name: string;
  visit_number: number;
  questions: Question[];
  journey_started_at: string;
  last_updated_at: string;
}

export interface SubmitAnswerRequest {
  question_id: string;
  answer_value: number | boolean | string;
}

export interface SubmitAnswerResponse {
  success: boolean;
  question_id: string;
  answer_value: number | boolean | string;
  transition_occurred: boolean;
  previous_stage?: string;
  current_stage: string;
  message: string;
}

export interface ApiError {
  detail: string;
}

export interface StageHistoryItem {
  stage_id: string;
  stage_name: string;
  visit_number: number;
  entered_at: string;
  exited_at: string | null;
  is_current: boolean;
  questions_answered: number;
}

export interface JourneyHistoryResponse {
  success: boolean;
  user_id: string;
  stages: StageHistoryItem[];
  total_stages_visited: number;
  journey_started_at: string;
  message?: string;
}

export interface StageDetailsResponse {
  success: boolean;
  stage_id: string;
  stage_name: string;
  visit_number: number;
  questions: Question[];
  entered_at: string;
  exited_at: string | null;
  is_current: boolean;
  message?: string;
}
