import { Canvas } from "@react-three/fiber";
import { useEffect, useState } from "react";
import axios from "axios";
import { safetyModules } from "./data/mockData";
import MedicalScene from "./components/3d/MedicalScene";
import StatCard from "./components/common/StatCard";
import FloatingMarker from "./components/common/FloatingMarker";
import AssistantPage from "./components/assistant/AssistantPage";
import ClinicalCore from "./components/common/ClinicalCore";
import Header from "./components/layout/Header";
import PIIDemo from "./components/safety/PIIDemo";

import type { Page } from "./types";

import "./App.css";

/* ------------------------------------------------------------------ */
/* Backend document types                                              */
/* ------------------------------------------------------------------ */

type BackendDocument = {
  id: string;
  filename: string;
  status: string;
  file_hash?: string | null;
  publisher?: string | null;
  source_trusted: boolean;
  admin_approved: boolean;
  chunk_count: number;
  created_at?: string | null;
};

type DocumentsResponse = {
  total: number;
  documents: BackendDocument[];
};

/* ------------------------------------------------------------------ */
/* Overview                                                            */
/* ------------------------------------------------------------------ */

function OverviewPage({
  onOpenAssistant,
}: {
  onOpenAssistant: () => void;
}) {
  return (
    <main className="content">
      <section className="hero-section">
        <div className="hero-copy">
          <div className="tiny-label">
            CLINICAL INTELLIGENCE PLATFORM
          </div>

          <h1>
            Health
            <br />
            <span>Intelligence</span>
          </h1>

          <p>
            Evidence-grounded health information,
            powered by verified medical knowledge.
          </p>

          <div className="hero-status">
            <span className="pulse" />
            Evidence engine online
          </div>
        </div>

        <div className="scene-container">
          <Canvas camera={{ position: [0, 0, 6], fov: 42 }}>
            <MedicalScene />
          </Canvas>

          <div className="scene-caption">
            <span>AI MEDICAL CORE</span>
            <small>LIVE INTELLIGENCE</small>
          </div>

          <FloatingMarker
            label="Evidence"
            value="98%"
            variant="evidence"
          />

          <FloatingMarker
            label="Safety"
            value="ACTIVE"
            variant="safety"
          />
        </div>

        <div className="stats-row">
          <StatCard
            label="VERIFIED SOURCES"
            value="1,284"
            detail="+12 this week"
          />

          <StatCard
            label="CITATION ACCURACY"
            value="98.6%"
            detail="Evidence matched"
          />

          <StatCard
            label="SAFETY ENGINE"
            value="ACTIVE"
            detail="Risk monitoring"
          />
        </div>
      </section>

      <aside className="right-panel">
        <ClinicalCore />

        <button
          className="overview-assistant-button"
          onClick={onOpenAssistant}
        >
          <span>
            <small>HEALTH ASSISTANT</small>
            Ask Health.AI
          </span>

          <strong>↗</strong>
        </button>

        <div className="privacy">
          <span>⌾</span>
          Your session is protected by safety guardrails.
        </div>
      </aside>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Assistant                                                           */
/* ------------------------------------------------------------------ */

function AssistantSection() {
  return <AssistantPage />;
}

/* ------------------------------------------------------------------ */
/* Knowledge                                                           */
/* ------------------------------------------------------------------ */

function KnowledgePage() {
  const [documents, setDocuments] = useState<BackendDocument[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDocuments = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.get<DocumentsResponse>(
        "http://localhost:8000/api/v1/documents"
      );

      const verifiedDocuments = response.data.documents.filter(
        (document) =>
          document.source_trusted &&
          document.admin_approved &&
          document.status === "completed"
      );

      setDocuments(verifiedDocuments);

      setSelectedId((currentId) => {
        if (
          currentId &&
          verifiedDocuments.some(
            (document) => document.id === currentId
          )
        ) {
          return currentId;
        }

        return verifiedDocuments[0]?.id ?? null;
      });
    } catch (err) {
      console.error("Failed to load knowledge documents:", err);

      setError(
        "Unable to load the verified knowledge base."
      );

      setDocuments([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDocuments();
  }, []);

  const filteredDocuments = documents.filter((document) =>
    `${document.filename} ${document.publisher ?? ""}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const selectedDocument =
    documents.find(
      (document) => document.id === selectedId
    ) ?? filteredDocuments[0] ?? null;

  const selectDocument = (document: BackendDocument) => {
    setSelectedId(document.id);
  };

  return (
    <main className="full-page">
      <div className="page-heading">
        <div>
          <span className="tiny-label">
            KNOWLEDGE BASE
          </span>

          <h1>Verified medical knowledge.</h1>

          <p>
            Medical documents indexed for evidence-grounded
            retrieval and citation.
          </p>
        </div>

        <div className="source-library-count">
          <strong>{documents.length}</strong>
          <span>VERIFIED DOCUMENTS</span>
        </div>
      </div>

      <div
        style={{
          marginBottom: "20px",
          padding: "12px 16px",
          border: "1px solid #dbe7ec",
          borderRadius: "10px",
          fontSize: "12px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <div>
          <strong>VERIFIED KNOWLEDGE BASE</strong>

          <div
            style={{
              marginTop: "4px",
              opacity: 0.7,
            }}
          >
            Only trusted and indexed medical documents are
            available to users.
          </div>
        </div>

        <button
          type="button"
          onClick={() => void loadDocuments()}
          disabled={loading}
          style={{
            border: "1px solid #dbe7ec",
            background: "#ffffff",
            borderRadius: "999px",
            padding: "7px 12px",
            cursor: loading ? "default" : "pointer",
            fontSize: "10px",
            letterSpacing: "0.08em",
            whiteSpace: "nowrap",
          }}
        >
          {loading ? "LOADING..." : "REFRESH"}
        </button>
      </div>

      {error && (
        <div
          style={{
            marginBottom: "20px",
            padding: "14px 16px",
            border: "1px solid #eadada",
            borderRadius: "10px",
            fontSize: "12px",
          }}
        >
          {error}
        </div>
      )}

      {!loading && !error && documents.length === 0 && (
        <div
          style={{
            marginBottom: "20px",
            padding: "18px",
            border: "1px solid #dbe7ec",
            borderRadius: "10px",
            fontSize: "12px",
          }}
        >
          No verified documents are currently available.
        </div>
      )}

      <div className="knowledge-layout">
        <section className="source-library">
          <div className="library-search">
            <span>⌕</span>

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search medical sources..."
            />
          </div>

          <div className="source-list">
            {loading && (
              <div
                style={{
                  padding: "18px",
                  fontSize: "12px",
                  opacity: 0.7,
                }}
              >
                Loading verified medical documents...
              </div>
            )}

            {!loading &&
              !error &&
              filteredDocuments.length === 0 &&
              documents.length > 0 && (
                <div
                  style={{
                    padding: "18px",
                    fontSize: "12px",
                    opacity: 0.7,
                  }}
                >
                  No documents match your search.
                </div>
              )}

            {!loading &&
              filteredDocuments.map((item) => {
                const isSelected =
                  selectedDocument?.id === item.id;

                return (
                  <button
                    key={item.id}
                    className={
                      isSelected
                        ? "source-list-item selected"
                        : "source-list-item"
                    }
                    onClick={() => selectDocument(item)}
                  >
                    <div className="document-icon">
                      PDF
                    </div>

                    <div>
                      <strong>{item.filename}</strong>

                      <small>
                        {item.publisher ||
                          "Verified Medical Source"}
                      </small>

                      <span>
                        {item.chunk_count} indexed chunks
                        {" · "}
                        ChromaDB
                      </span>
                    </div>

                    <b>›</b>
                  </button>
                );
              })}
          </div>
        </section>

        <section className="document-panel">
          {!selectedDocument ? (
            <div
              style={{
                padding: "30px",
                fontSize: "13px",
                opacity: 0.7,
              }}
            >
              Select a verified document to view its
              details.
            </div>
          ) : (
            <>
              <div className="document-toolbar">
                <div>
                  <span className="tiny-label">
                    SOURCE PREVIEW
                  </span>

                  <h2>{selectedDocument.filename}</h2>
                </div>

                <div className="document-page">
                  VERIFIED
                </div>
              </div>

              <div className="document-paper">
                <div className="paper-header">
                  <span>
                    {selectedDocument.publisher ||
                      "Verified Medical Source"}
                  </span>

                  <span>PDF</span>
                </div>

                <h3>
                  {selectedDocument.filename}
                </h3>

                <p>
                  This is a verified medical document
                  available in the Health.AI knowledge base.
                  Its contents have been indexed for
                  evidence-grounded retrieval and citation.
                </p>

                <div className="highlighted-paragraph">
                  <div className="line-number">
                    ✓
                  </div>

                  <p>
                    This document is currently indexed in
                    ChromaDB and available to the retrieval
                    system.
                  </p>
                </div>

                <p>
                  Source status:{" "}
                  <strong>
                    {selectedDocument.status}
                  </strong>
                  .
                  <br />
                  Indexed chunks:{" "}
                  <strong>
                    {selectedDocument.chunk_count}
                  </strong>
                  .
                </p>

                <div className="document-footer">
                  <span>✓ VERIFIED SOURCE</span>
                  <span>HEALTH.AI INDEX</span>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Safety                                                              */
/* ------------------------------------------------------------------ */

function SafetyPage() {
  return (
    <main className="full-page">
      <div className="page-heading">
        <div>
          <span className="tiny-label">
            SAFETY ENGINE
          </span>

          <h1>Safety before generation.</h1>

          <p>
            Multiple guardrails protect users from
            unsupported or high-risk medical responses.
          </p>
        </div>

        <div className="safety-status">
          <span />
          ALL SYSTEMS ACTIVE
        </div>
      </div>

      <div className="safety-grid">
        <section className="safety-overview">
          <div className="safety-ring">
            <div>
              <strong>04</strong>
              <span>GUARDRAILS</span>
            </div>
          </div>

          <div>
            <span className="tiny-label">
              PROTECTION LAYER
            </span>

            <h2>
              Clinical safety
              <br />
              infrastructure.
            </h2>

            <p>
              High-risk requests can be intercepted before
              the language model produces a response.
            </p>
          </div>
        </section>

        <section className="safety-modules">
          {safetyModules.map((module, index) => (
            <div
              className="safety-module"
              key={module.name}
            >
              <div className="safety-index">
                0{index + 1}
              </div>

              <div>
                <strong>{module.name}</strong>
                <small>{module.detail}</small>
              </div>

              <span>● ACTIVE</span>
            </div>
          ))}
        </section>

        <PIIDemo />
      </div>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* App                                                                 */
/* ------------------------------------------------------------------ */

function App() {
  const [activeTab, setActiveTab] =
    useState<Page>("Overview");

  const navigate = (page: Page) => {
    setActiveTab(page);
  };

  const renderPage = () => {
    switch (activeTab) {
      case "Assistant":
        return <AssistantSection />;

      case "Knowledge":
        return <KnowledgePage />;

      case "Safety":
        return <SafetyPage />;

      case "Overview":
      default:
        return (
          <OverviewPage
            onOpenAssistant={() =>
              navigate("Assistant")
            }
          />
        );
    }
  };

  return (
    <div className="page">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="grid-overlay" />

      <div className="shell">
        <Header
          activeTab={activeTab}
          onTabChange={navigate}
        />

        {renderPage()}

        <footer className="footer">
          <div>
            <span className="footer-dot" />
            SYSTEMS OPERATIONAL
          </div>

          <div className="footer-center">
            RAG · VERIFICATION · SAFETY
          </div>

          <div>HEALTH.AI © 2026</div>
        </footer>
      </div>
    </div>
  );
}

export default App;