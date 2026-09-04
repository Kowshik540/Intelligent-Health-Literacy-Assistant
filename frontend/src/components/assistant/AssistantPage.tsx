import { useEffect, useState } from "react";
import axios from "axios";
import type { Message, ApiResponse } from "../../types";

type SpeechRecognitionResultItem = {
  transcript: string;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<ArrayLike<SpeechRecognitionResultItem>>;
};

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

type BackendCitation = {
  source: string;
  page_number: string;
  section_header: string;
  relevance_score: number;
  text_snippet: string;
};

type BackendChatResponse = {
  conversation_id: string;
  message: {
    id: string;
    role: string;
    content: string;
    created_at: string;
  };
  sources: string[];
  citations: BackendCitation[];
  clinical_answer: string;
  simplified_answer: string;
  is_emergency: boolean;
  pii_detected: boolean;
};

type BackendConversation = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type BackendConversationMessage = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

type BackendConversationWithMessages = BackendConversation & {
  messages: BackendConversationMessage[];
};

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  const [stage, setStage] = useState<
    | "idle"
    | "analyzing"
    | "safety"
    | "retrieving"
    | "verifying"
    | "blocked"
    | "complete"
  >("idle");

  const [safetyResult, setSafetyResult] = useState<
    "safe" | "blocked" | "emergency" | null
  >(null);

  const [selectedSource, setSelectedSource] =
    useState<ApiResponse | null>(null);

  const [feedback, setFeedback] = useState<
    "up" | "down" | null
  >(null);

  const [sourceOpen, setSourceOpen] = useState(false);

  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);

  const [answerMode, setAnswerMode] =
    useState<"clinical" | "plain">("clinical");

  const [feedbackType, setFeedbackType] = useState("");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackMessageId, setFeedbackMessageId] = useState<number | null>(null);

  // Current backend conversation and saved conversation history.
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<BackendConversation[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [loadingConversationId, setLoadingConversationId] = useState<string | null>(null);

  const loadConversations = async () => {
    setHistoryLoading(true);
    setHistoryError(false);

    try {
      const result = await axios.get<BackendConversation[]>(
        "http://localhost:8000/api/v1/chat/conversations"
      );
      setConversations(result.data);
    } catch (error) {
      console.error("Health.AI conversation history error:", error);
      setHistoryError(true);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadConversation = async (id: string) => {
    if (loadingConversationId) return;

    setLoadingConversationId(id);
    setHistoryError(false);

    try {
      const result = await axios.get<BackendConversationWithMessages>(
        `http://localhost:8000/api/v1/chat/conversations/${id}`
      );

      const data = result.data;

      const restoredMessages: Message[] = data.messages.map(
        (item, index): Message => ({
          id: Number(item.id) || Date.now() + index,
          role: item.role.toLowerCase() === "user" ? "user" : "assistant",
          text: item.content,
        })
      );

      setMessages(restoredMessages);
      setConversationId(data.id);
      setQuestion("");
      setSelectedSource(null);
      setSourceOpen(false);
      setFeedback(null);
      setFeedbackType("");
      setFeedbackComment("");
      setFeedbackSubmitted(false);
      setFeedbackMessageId(null);
      setAnswerMode("clinical");
      setSafetyResult(null);
      setStage("complete");
      setHistoryOpen(false);
    } catch (error) {
      console.error("Health.AI conversation load error:", error);
      setHistoryError(true);
    } finally {
      setLoadingConversationId(null);
    }
  };

  const startNewConversation = () => {
    stopListening();
    setConversationId(null);
    setMessages([]);
    setQuestion("");
    setSelectedSource(null);
    setSourceOpen(false);
    setFeedback(null);
    setFeedbackType("");
    setFeedbackComment("");
    setFeedbackSubmitted(false);
    setFeedbackMessageId(null);
    setAnswerMode("clinical");
    setSafetyResult(null);
    setStage("idle");
    setHistoryOpen(false);
  };

  useEffect(() => {
    void loadConversations();
  }, []);

  const stopListening = () => {
    const speechWindow = window as Window & {
      __healthAiRecognition?: SpeechRecognitionInstance;
    };

    const recognition = speechWindow.__healthAiRecognition;

    if (recognition) {
      recognition.stop();
    }

    setIsListening(false);
  };

  const startListening = () => {
    const speechWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
      __healthAiRecognition?: SpeechRecognitionInstance;
    };

    const SpeechRecognition =
      speechWindow.SpeechRecognition ||
      speechWindow.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechSupported(false);
      setIsListening(false);
      return;
    }

    if (isListening) {
      stopListening();
      return;
    }

    const recognition = new SpeechRecognition();

    speechWindow.__healthAiRecognition = recognition;

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-IN";

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      let transcript = "";

      for (
        let index = event.resultIndex;
        index < event.results.length;
        index += 1
      ) {
        const result = event.results[index];
        const item = result?.[0];

        if (item) {
          transcript += item.transcript;
        }
      }

      const cleanTranscript = transcript.trim();

      if (cleanTranscript) {
        setQuestion(cleanTranscript);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);

      if (speechWindow.__healthAiRecognition === recognition) {
        delete speechWindow.__healthAiRecognition;
      }
    };

    try {
      recognition.start();
    } catch {
      setIsListening(false);
      setSpeechSupported(false);
    }
  };

  const submitFeedback = async (
    ratingValue?: "up" | "down",
    targetMessageId?: number,
  ) => {
    // Use explicit arguments when provided (avoids React state-update races);
    // otherwise fall back to the current state (used by the down-vote form).
    const rating = ratingValue ?? feedback;
    const msgId = targetMessageId ?? feedbackMessageId;

    if (!rating || msgId === null || msgId === undefined) return;

    const assistantMessageIndex = messages.findIndex(
      (message) => message.id === msgId
    );

    if (assistantMessageIndex === -1) return;

    const assistantMessage = messages[assistantMessageIndex];
    const response = assistantMessage.response;

    if (
      assistantMessage.role !== "assistant" ||
      !response?.message_id ||
      !response.conversation_id
    ) {
      console.error("Feedback cannot be submitted: missing message/conversation ID.");
      return;
    }

    // Find the user's question immediately before this assistant response.
    let originalQuestion = "";
    for (let index = assistantMessageIndex - 1; index >= 0; index -= 1) {
      if (messages[index].role === "user") {
        originalQuestion = messages[index].text;
        break;
      }
    }

    if (!originalQuestion) {
      console.error("Feedback cannot be submitted: original question not found.");
      return;
    }

    // A positive rating can be submitted immediately.
    // A negative rating requires the selected issue before submission.
    if (rating === "down" && !feedbackType) return;

    try {
      await axios.post("http://localhost:8000/api/v1/feedback/", {
        message_id: response.message_id,
        conversation_id: response.conversation_id,
        is_positive: rating === "up",
        original_question: originalQuestion,
        ai_answer: response.answer,
        user_correction:
          rating === "down" ? feedbackComment.trim() || null : null,
        error_category:
          rating === "down" ? feedbackType || null : null,
      });

      setFeedbackSubmitted(true);

      window.setTimeout(() => {
        setFeedbackSubmitted(false);
        setFeedback(null);
        setFeedbackMessageId(null);
        setFeedbackType("");
        setFeedbackComment("");
      }, 2500);
    } catch (error) {
      console.error("Health.AI feedback API error:", error);
    }
  };

  const runSafetyCheck = (
    query: string
  ): "safe" | "blocked" | "emergency" => {
    const normalized = query.toLowerCase();

    const emergencyPatterns = [
      "severe chest pain",
      "heart attack",
      "can't breathe",
      "cannot breathe",
      "difficulty breathing",
      "stroke",
      "unconscious",
      "severe bleeding",
    ];

    const highRiskPatterns = [
      "overdose",
      "suicide",
      "kill myself",
      "dangerous dose",
      "take extra medication",
      "mix medications",
    ];

    if (
      emergencyPatterns.some((pattern) =>
        normalized.includes(pattern)
      )
    ) {
      return "emergency";
    }

    if (
      highRiskPatterns.some((pattern) =>
        normalized.includes(pattern)
      )
    ) {
      return "blocked";
    }

    return "safe";
  };

  const askQuestion = async () => {
    const trimmed = question.trim();

    if (
      !trimmed ||
      (stage !== "idle" && stage !== "complete")
    ) {
      return;
    }

    const safety = runSafetyCheck(trimmed);

    setMessages((previous) => [
      ...previous,
      {
        id: Date.now(),
        role: "user",
        text: trimmed,
      },
    ]);

    stopListening();
    setQuestion("");
    setSelectedSource(null);
    setSourceOpen(false);
    setFeedback(null);
    setFeedbackType("");
    setFeedbackComment("");
    setFeedbackSubmitted(false);
    setFeedbackMessageId(null);
    setAnswerMode("clinical");
    setSafetyResult(safety);

    /*
     * Keep the new UI's safety presentation.
     * The backend also has its own GuardrailsService,
     * which remains the authoritative safety layer.
     */
    if (safety !== "safe") {
      setStage("analyzing");

      window.setTimeout(() => {
        setStage("safety");

        window.setTimeout(() => {
          setStage("blocked");
        }, 500);
      }, 500);

      return;
    }

    setStage("analyzing");

    const safetyTimer = window.setTimeout(() => {
      setStage("safety");
    }, 400);

    const retrievalTimer = window.setTimeout(() => {
      setStage("retrieving");
    }, 900);

    const verificationTimer = window.setTimeout(() => {
      setStage("verifying");
    }, 1400);

    try {
      const result = await axios.post<BackendChatResponse>(
        "http://localhost:8000/api/v1/chat/",
        {
          message: trimmed,
          ...(conversationId ? { conversation_id: conversationId } : {}),
        }
      );

      window.clearTimeout(safetyTimer);
      window.clearTimeout(retrievalTimer);
      window.clearTimeout(verificationTimer);

      const data = result.data;

      // Reuse the backend conversation for the next question.
      setConversationId(data.conversation_id);

      /*
       * The backend returns detailed citation information
       * using page_number, section_header, relevance_score
       * and text_snippet.
       */
      const citation = data.citations?.[0];

      const response: ApiResponse = {
        answer: data.clinical_answer || "",
        plain: data.simplified_answer || "",

        source:
          citation?.source ||
          data.sources?.[0] ||
          "Verified medical source",

        institution: "",

        page: String(
          citation?.page_number || "1"
        ),

        /*
         * The current backend does not return the total
         * number of pages in ChatResponse.
         */
        totalPages: "1",

        section:
          citation?.section_header ||
          "Medical guidance",

        snippet:
          citation?.text_snippet ||
          "",

        confidence:
          typeof citation?.relevance_score === "number"
            ? citation.relevance_score.toFixed(2)
            : "Verified",

        conversation_id:
          data.conversation_id,

        message_id:
          data.message?.id,
      };

      /*
       * Backend safety result takes priority.
       */
      if (data.is_emergency) {
        setSafetyResult("emergency");
        setStage("blocked");
        return;
      }

      setStage("complete");

      const answerText = data.clinical_answer || data.simplified_answer || "";
      const lowerAnswer = answerText.toLowerCase();

      // A hard refusal has no usable answer text.
      const isRefusal = lowerAnswer.includes("i cannot provide information");

      const hasCitations = Boolean(data.citations?.length);

      // A greeting / assistant intro / "please rephrase" prompt is
      // conversational, not a medical answer — show it plainly.
      const isGreeting =
        lowerAnswer.includes("i'm a health information assistant") ||
        lowerAnswer.includes("ask me a health question") ||
        lowerAnswer.includes("understood that as a health question");

      // A clarification prompt asks the user for more details.
      const isClarification = lowerAnswer.includes(
        "i need a little more information"
      );

      // General-knowledge answers carry this disclaimer from the backend.
      const isGeneral =
        !hasCitations &&
        !isRefusal &&
        !isGreeting &&
        !isClarification &&
        lowerAnswer.includes("general health information");

      // A verified answer has real document citations.
      const hasVerified =
        Boolean(answerText.trim()) && hasCitations && !isRefusal;

      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",

        text:
          answerText ||
          "I could not find sufficient information to answer this question safely. Please consult a healthcare professional.",

        response: hasVerified ? response : undefined,

        // Only a true refusal is flagged unsupported. Greetings, clarifications,
        // general answers, and verified answers all avoid the warning banner.
        unsupported:
          !hasVerified &&
          !isGeneral &&
          !isGreeting &&
          !isClarification &&
          isRefusal,

        // General-knowledge answers get a softer, honest note.
        general: isGeneral,
      };

      setMessages((previous) => [
        ...previous,
        assistantMessage,
      ]);

      if (hasVerified && data.citations?.length) {
        setSelectedSource(response);
      }

      // Refresh saved conversations so the current chat appears in history.
      void loadConversations();

    } catch (error) {
      window.clearTimeout(safetyTimer);
      window.clearTimeout(retrievalTimer);
      window.clearTimeout(verificationTimer);

      console.error(
        "Health.AI chat API error:",
        error
      );

      setStage("complete");

      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: "assistant",
          text:
            "I'm unable to connect to the health assistant service right now. Please make sure the backend server is running on port 8000 and try again.",
          unsupported: true,
        },
      ]);
    }
  };

  const isProcessing =
    stage === "analyzing" ||
    stage === "safety" ||
    stage === "retrieving" ||
    stage === "verifying";

  const stageText = {
    analyzing: "Analyzing clinical query",
    safety: "Running safety screening",
    retrieving: "Retrieving verified evidence",
    verifying: "Validating citations",
  };

  const suggestedQuestions = [
    "What are the symptoms of hypertension?",
    "What is myocardial infarction?",
    "What is diabetes?",
  ];

  return (
    <main className="full-page">
      {/* PAGE HEADER */}
      <div className="page-heading">
        <div>
          <span className="tiny-label">
            CLINICAL ASSISTANT
          </span>

          <h1>Evidence-grounded answers.</h1>

          <p>
            Ask health questions and receive responses
            backed by verified medical sources.
          </p>
        </div>

        <div className="mode-badge">
          <span />

          <button
            type="button"
            onClick={() =>
              setAnswerMode("clinical")
            }
            aria-pressed={
              answerMode === "clinical"
            }
          >
            CLINICAL
          </button>

          <button
            type="button"
            onClick={() =>
              setAnswerMode("plain")
            }
            aria-pressed={
              answerMode === "plain"
            }
          >
            PLAIN LANGUAGE
          </button>
        </div>
      </div>

      {/* MAIN ASSISTANT AREA */}
      <div className="assistant-layout">
        {/* CHAT */}
        <section className="chat-panel">
          <div className="chat-header">
            <div>
              <strong>
                Health.AI Assistant
              </strong>

              <small>
                Evidence retrieval and citation
                verification active
              </small>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  const nextOpen = !historyOpen;
                  setHistoryOpen(nextOpen);
                  if (nextOpen) {
                    void loadConversations();
                  }
                }}
                style={{
                  border: "1px solid #dbe7ec",
                  background: "#ffffff",
                  borderRadius: "999px",
                  padding: "7px 11px",
                  fontSize: "10px",
                  letterSpacing: "0.08em",
                  cursor: "pointer",
                }}
              >
                HISTORY
              </button>

              <button
                type="button"
                onClick={startNewConversation}
                style={{
                  border: "1px solid #dbe7ec",
                  background: "#ffffff",
                  borderRadius: "999px",
                  padding: "7px 11px",
                  fontSize: "10px",
                  letterSpacing: "0.08em",
                  cursor: "pointer",
                }}
              >
                NEW CHAT
              </button>

              <span className="online-dot" />
            </div>
          </div>

          {historyOpen && (
            <div
              style={{
                borderBottom: "1px solid #e5edf1",
                background: "#fbfdfe",
                padding: "12px 14px",
                maxHeight: "220px",
                overflowY: "auto",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "8px",
                }}
              >
                <strong style={{ fontSize: "11px", letterSpacing: "0.08em" }}>
                  CONVERSATION HISTORY
                </strong>

                <button
                  type="button"
                  onClick={() => void loadConversations()}
                  disabled={historyLoading}
                  style={{
                    border: "none",
                    background: "transparent",
                    fontSize: "14px",
                    cursor: historyLoading ? "default" : "pointer",
                  }}
                >
                  ↻
                </button>
              </div>

              {historyError && (
                <div style={{ fontSize: "12px", padding: "8px 0" }}>
                  Unable to load conversation history.
                </div>
              )}

              {!historyError && !historyLoading && conversations.length === 0 && (
                <div style={{ fontSize: "12px", padding: "8px 0" }}>
                  No saved conversations yet.
                </div>
              )}

              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => void loadConversation(conversation.id)}
                  disabled={loadingConversationId !== null}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    border: "1px solid #e2ebef",
                    background:
                      conversation.id === conversationId ? "#eef8fb" : "#ffffff",
                    borderRadius: "8px",
                    padding: "9px 10px",
                    marginBottom: "6px",
                    cursor:
                      loadingConversationId !== null ? "default" : "pointer",
                  }}
                >
                  <strong
                    style={{
                      display: "block",
                      fontSize: "12px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {loadingConversationId === conversation.id
                      ? "Loading..."
                      : conversation.title || "New Conversation"}
                  </strong>

                  <span
                    style={{
                      display: "block",
                      marginTop: "3px",
                      fontSize: "10px",
                      opacity: 0.65,
                    }}
                  >
                    {new Date(conversation.updated_at).toLocaleString()}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="chat-body">
            {messages.length === 0 &&
              !isProcessing && (
                <div className="chat-empty">
                  <div className="empty-icon">
                    ✦
                  </div>

                  <h2>
                    What would you like to
                    <br />
                    understand?
                  </h2>

                  <p>
                    Ask about conditions, symptoms,
                    treatments, guidelines, or general
                    health information.
                  </p>

                  <div className="suggestion-row">
                    {suggestedQuestions.map(
                      (suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() =>
                            setQuestion(
                              suggestion
                            )
                          }
                        >
                          {suggestion}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}

            {/* MESSAGES */}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.role}`}
              >
                <div className="message-label">
                  {message.role === "user"
                    ? "YOU"
                    : "HEALTH.AI"}
                </div>

                <div className="message-bubble">
                  {message.role === "assistant" &&
                  message.response
                    ? answerMode ===
                      "clinical"
                      ? message.response
                          .answer
                      : message.response
                          .plain
                    : message.text}
                </div>

                {/* VERIFIED RESPONSE */}
                {message.role ===
                  "assistant" &&
                  message.response &&
                  !message.unsupported && (
                    <div className="verified-answer">
                      <div className="verified-header">
                        <span>
                          ✓ VERIFIED RESPONSE
                        </span>

                        <div className="feedback">
                          <button
                            className={
                              feedback ===
                              "up"
                                ? "feedback-active"
                                : ""
                            }
                            onClick={() => {
                              setFeedback("up");
                              setFeedbackMessageId(message.id);
                              setFeedbackType("");
                              setFeedbackComment("");
                              setFeedbackSubmitted(false);
                              // Pass values explicitly to avoid a state race.
                              void submitFeedback("up", message.id);
                            }}
                          >
                            👍
                          </button>

                          <button
                            className={
                              feedback ===
                              "down"
                                ? "feedback-active"
                                : ""
                            }
                            onClick={() => {
                              setFeedback("down");
                              setFeedbackMessageId(message.id);
                              setFeedbackType("");
                              setFeedbackComment("");
                              setFeedbackSubmitted(false);
                            }}
                          >
                            👎
                          </button>
                        </div>
                      </div>

                      <p>
                        Evidence confidence:{" "}
                        <strong>
                          {
                            message
                              .response
                              .confidence
                          }
                        </strong>
                      </p>

                      <button
                        className="citation-button"
                        onClick={() => {
                          setSelectedSource(
                            message.response!
                          );

                          

                          setSourceOpen(true);
                        }}
                      >
                        View supporting citation ↗
                      </button>

                      {feedback === "up" &&
                        feedbackMessageId === message.id &&
                        feedbackSubmitted && (
                        <div
                          className="feedback-success"
                          role="status"
                        >
                          ✓ Thank you for your
                          feedback
                        </div>
                      )}

                      {feedback === "down" &&
                        feedbackMessageId === message.id && (
                        <div className="feedback-form">
                          {!feedbackSubmitted ? (
                            <>
                              <div className="feedback-form-title">
                                What went wrong?
                              </div>

                              <select
                                value={
                                  feedbackType
                                }
                                onChange={(
                                  event
                                ) =>
                                  setFeedbackType(
                                    event.target
                                      .value
                                  )
                                }
                                aria-label="Feedback reason"
                              >
                                <option value="">
                                  Select an issue
                                </option>

                                <option value="Incorrect answer">
                                  Incorrect answer
                                </option>

                                <option value="Incorrect citation">
                                  Incorrect citation
                                </option>

                                <option value="Missing information">
                                  Missing information
                                </option>

                                <option value="Too technical">
                                  Too technical
                                </option>

                                <option value="Other">
                                  Other
                                </option>
                              </select>

                              <textarea
                                value={
                                  feedbackComment
                                }
                                onChange={(
                                  event
                                ) =>
                                  setFeedbackComment(
                                    event.target
                                      .value
                                  )
                                }
                                placeholder="Tell us what should be corrected..."
                                rows={4}
                                aria-label="Feedback correction"
                              />

                              <button
                                type="button"
                                className="feedback-submit"
                                disabled={
                                  !feedbackType
                                }
                                onClick={() => {
                                  void submitFeedback(
                                    "down",
                                    message.id,
                                  );
                                }}
                              >
                                SUBMIT FEEDBACK
                              </button>
                            </>
                          ) : (
                            <div
                              className="feedback-success"
                              role="status"
                            >
                              ✓ Feedback recorded
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                {/* GENERAL KNOWLEDGE (helpful, but not from a verified document) */}
                {message.role === "assistant" &&
                  message.general && (
                    <div className="general-answer">
                      <span>
                        ⓘ GENERAL INFORMATION
                      </span>

                      <p>
                        This answer is based on general medical
                        knowledge, not a specific verified document
                        in the library. Please confirm with a
                        qualified healthcare professional.
                      </p>
                    </div>
                  )}

                {/* UNSUPPORTED — only for a true refusal with no answer */}
                {message.role === "assistant" &&
                  message.unsupported && (
                    <div className="unsupported-answer">
                      <span>
                        ⚠ NO VERIFIED EVIDENCE
                      </span>

                      <p>
                        The system did not find sufficient
                        evidence to answer this safely and did
                        not guess. Please consult a healthcare
                        professional.
                      </p>
                    </div>
                  )}
              </div>
            ))}

            {/* PROCESSING */}
            {isProcessing && (
              <div className="message assistant">
                <div className="message-label">
                  HEALTH.AI
                </div>

                <div className="verification-box">
                  <div className="verification-spinner" />

                  <div>
                    <strong>
                      {stageText[stage]}
                    </strong>

                    <small>
                      {stage ===
                        "analyzing" &&
                        "Understanding the clinical intent..."}

                      {stage === "safety" &&
                        "Checking the request for high-risk or emergency patterns..."}

                      {stage ===
                        "retrieving" &&
                        "Searching the verified knowledge base..."}

                      {stage ===
                        "verifying" &&
                        "Every generated claim must have supporting evidence."}
                    </small>
                  </div>
                </div>
              </div>
            )}

            {stage === "blocked" && (
              <div className="message assistant">
                <div className="message-label">
                  HEALTH.AI
                </div>

                {safetyResult ===
                "emergency" ? (
                  <div className="safety-result emergency">
                    <div className="alert-icon">
                      !
                    </div>

                    <div>
                      <strong>
                        EMERGENCY QUERY DETECTED
                      </strong>

                      <h3>
                        Clinical advice
                        generation blocked.
                      </h3>

                      <p>
                        This request may
                        describe a medical
                        emergency. The system
                        has stopped normal AI
                        generation. Seek
                        emergency medical
                        assistance immediately.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="safety-result blocked">
                    <strong>
                      ⚠ HIGH-RISK QUERY BLOCKED
                    </strong>

                    <p>
                      The safety layer
                      intercepted this request
                      before evidence retrieval
                      and normal response
                      generation.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* INPUT */}
          <div className="chat-input">
            <input
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  askQuestion();
                }
              }}
              placeholder={
                isListening
                  ? "Listening..."
                  : "Ask a health question..."
              }
              disabled={isProcessing}
            />

            <button
              type="button"
              className={
                isListening
                  ? "voice-button listening"
                  : "voice-button"
              }
              onClick={startListening}
              disabled={
                isProcessing ||
                !speechSupported
              }
              aria-label={
                speechSupported
                  ? isListening
                    ? "Stop listening"
                    : "Speak your question"
                  : "Speech input is not supported"
              }
              title={
                speechSupported
                  ? isListening
                    ? "Stop listening"
                    : "Speak your question"
                  : "Speech input is not supported in this browser"
              }
            >
              {isListening ? "■" : "🎤"}
            </button>

            <button
              type="button"
              onClick={askQuestion}
              disabled={
                isProcessing ||
                !question.trim()
              }
              aria-label="Send question"
            >
              ↗
            </button>
          </div>
        </section>

        {/* SOURCE SIDEBAR */}
        <aside className="source-panel">
          <div className="source-heading">
            <div>
              <span className="tiny-label">
                EVIDENCE
              </span>

              <h2>
                Source Verification
              </h2>
            </div>

            {selectedSource && (
              <span className="source-count">
                01
              </span>
            )}
          </div>

          {!selectedSource ? (
            <div className="source-empty">
              <div>◇</div>

              <strong>
                No citation selected
              </strong>

              <p>
                Ask a question to retrieve
                verified medical evidence.
              </p>
            </div>
          ) : (
            <div className="citation-card">
              <div className="citation-status">
                <span>✓</span>
                CITATION VERIFIED
              </div>

              <h3>
                {selectedSource.source}
              </h3>

              <div className="source-meta">
                <span>
                  Page {selectedSource.page}
                </span>

                <span>
                  Confidence{" "}
                  {selectedSource.confidence}
                </span>
              </div>

              <div className="source-section">
                <span>SECTION</span>

                <strong>
                  {selectedSource.section}
                </strong>
              </div>

              <div className="evidence-snippet">
                <span>“</span>

                {selectedSource.snippet}

                <span>”</span>
              </div>

              <button
                className="source-preview-button"
                onClick={() => {
                  setSourceOpen(
                    !sourceOpen
                  );

                  
                }}
              >
                {sourceOpen
                  ? "Hide source preview"
                  : "Open source preview"}
              </button>

              {sourceOpen && (
                <div className="pdf-preview">
                  <div className="pdf-toolbar">
                    <span>
                      CITATION · PAGE{" "}
                      {selectedSource.page}
                    </span>

                    <span>
                      VERIFIED SOURCE
                    </span>
                  </div>

                  <div className="pdf-source-info">
                    <div className="pdf-source-title">
                      {selectedSource.source}
                    </div>

                    <div className="pdf-source-page">
                      Page{" "}
                      {selectedSource.page}
                    </div>
                  </div>

                  <div className="pdf-callout">
                    <span>SECTION</span>

                    <strong>
                      {selectedSource.section}
                    </strong>
                  </div>

                  <div className="pdf-callout">
                    <span>
                      SUPPORTING PASSAGE
                    </span>

                    <p>
                      {selectedSource.snippet ||
                        "No supporting passage was returned for this citation."}
                    </p>
                  </div>

                  <div className="pdf-citation-details">
                    <div>
                      <span>SOURCE</span>

                      <strong>
                        {selectedSource.source}
                      </strong>
                    </div>

                    <div>
                      <span>PAGE</span>

                      <strong>
                        {selectedSource.page}
                      </strong>
                    </div>

                    <div>
                      <span>CONFIDENCE</span>

                      <strong>
                        {
                          selectedSource.confidence
                        }
                      </strong>
                    </div>
                  </div>

                  <div className="citation-footer">
                    ✓ CLAIM SUPPORTED BY THIS
                    SOURCE PASSAGE
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}