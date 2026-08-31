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
};