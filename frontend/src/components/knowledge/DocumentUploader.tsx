import { useEffect, useMemo, useState } from "react";
import axios from "axios";

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

export default function DocumentUploader() {
  const [documents, setDocuments] = useState<BackendDocument[]>([]);
  const [selectedDocument, setSelectedDocument] =
    useState<BackendDocument | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const loadDocuments = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.get<DocumentsResponse>(
        "http://localhost:8000/api/v1/documents"
      );

      const verified = response.data.documents.filter(
        (document) =>
          document.source_trusted &&
          document.admin_approved &&
          document.status === "completed"
      );

      setDocuments(verified);

      // Automatically select the first verified document.
      if (verified.length > 0) {
        setSelectedDocument((current) => {
          if (
            current &&
            verified.some((document) => document.id === current.id)
          ) {
            return current;
          }

          return verified[0];
        });
      } else {
        setSelectedDocument(null);
      }
    } catch (err) {
      console.error("Failed to load knowledge documents:", err);
      setError("Unable to load the verified knowledge base.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDocuments();
  }, []);

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter(
      (document) =>
        document.filename.toLowerCase().includes(query) ||
        (document.publisher || "").toLowerCase().includes(query)
    );
  }, [documents, search]);

  const pdfUrl = selectedDocument
    ? `http://localhost:8000/api/v1/documents/${selectedDocument.id}/file`
    : "";

  return (
    <div className="knowledge-toolbar">
      <div
        style={{
          width: "100%",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
        }}
      >
        {/* HEADER */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
          }}
        >
          <div>
            <strong>VERIFIED KNOWLEDGE BASE</strong>

            <div
              style={{
                marginTop: "4px",
                fontSize: "12px",
                opacity: 0.7,
              }}
            >
              Only trusted and indexed medical documents are available to
              users.
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
            }}
          >
            {loading ? "LOADING..." : "REFRESH"}
          </button>
        </div>

        {/* ERROR */}
        {error && (
          <div
            style={{
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid #eadada",
              fontSize: "12px",
            }}
          >
            {error}
          </div>
        )}

        {/* EMPTY */}
        {!loading && !error && documents.length === 0 && (
          <div
            style={{
              padding: "16px",
              border: "1px solid #e2ebef",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          >
            No verified documents are currently available.
          </div>
        )}

        {documents.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(300px, 0.8fr) minmax(500px, 1.7fr)",
              gap: "20px",
              width: "100%",
            }}
          >
            {/* DOCUMENT LIST */}
            <div
              style={{
                border: "1px solid #e2ebef",
                borderRadius: "12px",
                background: "#ffffff",
                padding: "18px",
                minHeight: "600px",
              }}
            >
              {/* SEARCH */}
              <div
                style={{
                  position: "relative",
                  marginBottom: "14px",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    fontSize: "14px",
                    opacity: 0.6,
                  }}
                >
                  ⌕
                </span>

                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search medical sources..."
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    border: "1px solid #dbe7ec",
                    borderRadius: "8px",
                    padding: "12px 12px 12px 34px",
                    fontSize: "12px",
                    outline: "none",
                  }}
                />
              </div>

              {/* LIST */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                {filteredDocuments.map((document) => {
                  const selected =
                    selectedDocument?.id === document.id;

                  return (
                    <button
                      key={document.id}
                      type="button"
                      onClick={() => setSelectedDocument(document)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        border: selected
                          ? "1px solid #8ecde3"
                          : "1px solid transparent",
                        borderRadius: "10px",
                        background: selected
                          ? "#f1f9fc"
                          : "#ffffff",
                        padding: "13px",
                        cursor: "pointer",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "10px",
                        }}
                      >
                        <div
                          style={{
                            width: "38px",
                            height: "38px",
                            border: "1px solid #dbe7ec",
                            borderRadius: "8px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "9px",
                            flexShrink: 0,
                          }}
                        >
                          PDF
                        </div>

                        <div
                          style={{
                            minWidth: 0,
                            flex: 1,
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
                            {document.filename}
                          </strong>

                          <span
                            style={{
                              display: "block",
                              marginTop: "5px",
                              fontSize: "10px",
                              opacity: 0.7,
                            }}
                          >
                            {document.publisher ||
                              "Verified Medical Source"}
                          </span>

                          <span
                            style={{
                              display: "block",
                              marginTop: "5px",
                              fontSize: "9px",
                              opacity: 0.6,
                            }}
                          >
                            {document.chunk_count} indexed chunks ·
                            ChromaDB
                          </span>
                        </div>

                        <span
                          style={{
                            fontSize: "14px",
                            opacity: 0.6,
                          }}
                        >
                          ›
                        </span>
                      </div>
                    </button>
                  );
                })}

                {filteredDocuments.length === 0 && (
                  <div
                    style={{
                      padding: "16px 8px",
                      fontSize: "11px",
                      opacity: 0.65,
                    }}
                  >
                    No matching documents.
                  </div>
                )}
              </div>
            </div>

            {/* ACTUAL DOCUMENT VIEWER */}
            <div
              style={{
                border: "1px solid #e2ebef",
                borderRadius: "12px",
                background: "#ffffff",
                overflow: "hidden",
                minHeight: "600px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {selectedDocument ? (
                <>
                  {/* VIEWER HEADER */}
                  <div
                    style={{
                      padding: "18px 20px",
                      borderBottom: "1px solid #e2ebef",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "15px",
                    }}
                  >
                    <div
                      style={{
                        minWidth: 0,
                      }}
                    >
                      <div
                        style={{
                          fontSize: "9px",
                          letterSpacing: "0.18em",
                          marginBottom: "5px",
                          opacity: 0.6,
                        }}
                      >
                        SOURCE DOCUMENT
                      </div>

                      <strong
                        style={{
                          display: "block",
                          fontSize: "16px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {selectedDocument.filename}
                      </strong>

                      <span
                        style={{
                          display: "block",
                          marginTop: "5px",
                          fontSize: "10px",
                          opacity: 0.65,
                        }}
                      >
                        {selectedDocument.publisher ||
                          "Verified Medical Source"}
                      </span>
                    </div>

                    <span
                      style={{
                        borderRadius: "999px",
                        padding: "6px 10px",
                        background: "#eef8f3",
                        fontSize: "9px",
                        letterSpacing: "0.08em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      ✓ VERIFIED
                    </span>
                  </div>

                  {/* ACTUAL PDF */}
                  <div
                    style={{
                      flex: 1,
                      background: "#f5f8fa",
                      padding: "14px",
                    }}
                  >
                    <iframe
                      key={selectedDocument.id}
                      src={pdfUrl}
                      title={selectedDocument.filename}
                      style={{
                        width: "100%",
                        height: "700px",
                        border: "1px solid #dbe7ec",
                        borderRadius: "8px",
                        background: "#ffffff",
                      }}
                    />
                  </div>
                </>
              ) : (
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "12px",
                    opacity: 0.65,
                  }}
                >
                  Select a verified document to view it.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}