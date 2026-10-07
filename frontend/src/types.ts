export type Json = Record<string, unknown>;
export interface Source {
  id: string;
  url: string;
  title: string;
  excerpt: string;
  published_at: string | null;
  consulted_at: string;
}
export interface Relation {
  id: string;
  classification: string;
  reason: string;
}
export interface Idea {
  id: string;
  title: string;
  summary: string;
  angle: string;
  topic: string;
  content_type: string;
  rationale: string;
  project_connection: string;
  origin: string;
  original_input: string;
  status: string;
  discard_reason: string;
  notes: string;
  current_news: boolean;
  relations: Relation[];
  signals: Json[];
  revision: number;
  created_at: string;
  updated_at: string;
  publication_id: string | null;
  sources: Source[];
}
export interface Article {
  title: string;
  seo_title: string;
  body: string;
  keyphrase: string;
  slug: string;
  meta_description: string;
  excerpt: string;
  categories: number[];
  tags: number[];
  image_alt: string;
}
export interface Version {
  id: string;
  channel: "wordpress" | "linkedin";
  reason: string;
  data: Article | { text: string };
  fingerprint: string;
  based_on: string | null;
  created_at: string;
}
export interface Evaluation {
  id: string;
  score: number;
  evaluator: string;
  result: {
    checks: {
      key: string;
      label: string;
      weight: number;
      passed: boolean;
      applicable: boolean;
      advice: string;
    }[];
    coverage: number;
    words: number;
    density: number;
    pending_site_checks: string[];
    warnings: string[];
    readability: {
      long_sentence_percent: number;
      paragraphs: number;
      method: string;
    };
  };
  editorial: {
    warnings?: string[];
    personal_claims_to_confirm?: string[];
    unsupported_claims?: string[];
    readability_notes?: string[];
  };
  created_at: string;
}
export interface Publication {
  id: string;
  idea_id: string | null;
  title: string;
  wp_status: string;
  li_status: string;
  wp_id: number | null;
  li_id: string | null;
  canonical_url: string;
  url_history: string[];
  revision: number;
  updated_at: string;
  current_wp: string | null;
  current_li: string | null;
  best_wp: string | null;
  li_stale: boolean;
  external_change: boolean;
  public_verified: boolean;
  confirmations: Record<string, boolean>;
  wordpress: Version | null;
  linkedin: Version | null;
  evaluation: Evaluation | null;
  evaluation_stale: boolean;
  image: {
    id: string;
    path: string;
    alt: string;
    wp_id: number | null;
    upload_uncertain: boolean;
  } | null;
  sources: Source[];
}
export interface Preferences {
  app_name: string;
  provider: "openai" | "anthropic";
  model: string;
  max_cost: string;
  fallback: boolean;
  fallback_provider: "openai" | "anthropic";
  fallback_model: string;
  max_ideas: number;
  max_searches: number;
  max_output_tokens: number;
  max_context_chars: number;
}
export interface Estimate {
  currency: string;
  low: string | null;
  high: string | null;
  assumptions: Record<string, unknown>;
}
export interface Model {
  id: string;
  provider: "openai" | "anthropic";
  name: string;
  description: string;
  input: string | null;
  output: string | null;
  cached: string | null;
  cache_write?: string | null;
  search: string | null;
  web_search: boolean;
  verified: string;
  source: string;
  availability?: string;
  estimate?: Estimate;
}
export interface Catalog {
  version: string;
  models: Model[];
}
export interface Job {
  id: string;
  kind: string;
  state: string;
  phase: string;
  progress: number;
  parameters: Json;
  selection: Preferences;
  checkpoints: Json;
  result: Json;
  error: { code?: string; message?: string; action?: string };
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
}
export interface Notice {
  id: string;
  message: string;
  kind: string;
  read: boolean;
  job_id: string | null;
  created_at: string;
}
export interface Connection {
  provider: string;
  config: Record<string, string>;
  status: string;
  detail: string;
  has_secrets: boolean;
  checked_at: string | null;
  balance: string | null;
}
export interface OwnerContext {
  id: string;
  revision: number;
  body: {
    profile: string;
    projects: string;
    goals: string;
    audience: string;
    tone: string;
    avoid: string;
    confirmed_facts: string;
    style_examples: string;
    references: Json[];
  };
  updated_at: string;
}
export interface Signal {
  publication_id: string;
  provider: string;
  start: string;
  end: string;
  quality: string;
  values: Record<string, number>;
  title: string;
  topic: string;
  content_type: string;
  message: string;
  linkedin_sessions: number;
  article_age_days: number | null;
}
export interface MetricComparison {
  publication_id: string;
  title: string;
  provider: string;
  current: [string, string];
  previous: [string, string];
  indicator: string;
  difference: number;
  relative_change: number | null;
  quality: string;
  message: string;
}
export interface Metrics {
  state: string;
  message: string;
  signals: Signal[];
  comparisons?: MetricComparison[];
}
export interface Costs {
  currency: string;
  calculated: string;
  uncertain_reserved: string;
  scope: string;
  calls: {
    id: string;
    provider: string;
    model: string;
    phase: string;
    calculated_cost: string | null;
    estimated_cost: string | null;
    uncertain: boolean;
    status: string;
    created_at: string;
    usage: Record<string, number>;
  }[];
}
