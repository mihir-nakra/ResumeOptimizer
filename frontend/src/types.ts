export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';
export type RequestStatus = 'processing' | 'completed' | 'failed';

export interface StageResult<T = unknown> {
  status: StageStatus;
  result: T | null;
  error: string | null;
}

export interface ScoreCategory {
  matched: number;
  total: number;
  rate: number;
  weighted_contribution: number;
}

export interface ScoreBreakdown {
  technical_skills: ScoreCategory;
  soft_skills: ScoreCategory;
  qualifications: ScoreCategory;
  experience_requirements: ScoreCategory;
}

export interface OptimizedSection {
  section_name: string;
  original_content: string;
  optimized_content: string;
  keywords_incorporated: string[];
  changes_summary: string;
}

export interface ATSResult {
  ats_score: number;
  score_breakdown: ScoreBreakdown;
  optimized_resume: Record<string, unknown>;
  optimized_sections: OptimizedSection[];
}

export interface Suggestion {
  section: string;
  suggestion: string;
  example: string;
  gap_addressed: string;
  impact: 'high' | 'medium' | 'low';
}

export interface SuggestionsResult {
  suggestions: Suggestion[];
  priority_areas: string[];
}

export interface InterviewQuestion {
  question: string;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard';
  skill_assessed: string;
  follow_ups: string[];
  what_to_look_for: string;
}

export interface InterviewResult {
  questions: InterviewQuestion[];
  difficulty_levels: { easy: number; medium: number; hard: number };
  candidate_strengths_to_probe: string[];
  potential_gaps_to_assess: string[];
}

export interface ParsingResult {
  structured_data: Record<string, unknown>;
}

export interface StatusResponse {
  request_id: string;
  status: RequestStatus;
  created_at: string;
  file_path: string;
  job_description: string;
  error: string | null;
  stages: {
    parsing: StageResult<ParsingResult>;
    ats_optimization: StageResult<ATSResult>;
    suggestions: StageResult<SuggestionsResult>;
    interview: StageResult<InterviewResult>;
  };
}

export interface UploadResponse {
  request_id: string;
  status: string;
}

export type StageName = 'parsing' | 'ats_optimization' | 'suggestions' | 'interview';
