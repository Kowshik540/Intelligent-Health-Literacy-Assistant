export type Page =
  | "Overview"
  | "Assistant"
  | "Knowledge"
  | "Safety";

export type FeedbackKind =
  | "Incorrect answer"
  | "Incorrect citation"
  | "Missing information"
  | "Too technical"
  | "Other";

export type ApiResponse = {
  answer: string;
  plain: string;
  source: string;
  institution?: string;
  page: string;
  totalPages: string;
  section: string;
  snippet: string;
  confidence: string;
  conversation_id?: string;
  message_id?: string;
};

export type Message = {
  id: number;
  role: "user" | "assistant";
  text: string;
  response?: ApiResponse;
  unsupported?: boolean;
  // True when the answer is helpful general knowledge (not a refusal) but is
  // not backed by a verified document citation.
  general?: boolean;
  // Both answer versions from the backend, so the Clinical / Plain-Language
  // toggle works for every assistant message, not only verified ones.
  clinical?: string;
  plain?: string;
};