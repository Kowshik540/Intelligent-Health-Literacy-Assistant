import { useState } from "react";
import axios from "axios";
import { apiUrl } from "../../config";

type SafetyResponse = {
  is_safe: boolean;
  sanitized_text: string;
  pii_detected: boolean;
  is_emergency: boolean;
  refusal_message: string | null;
};

export default function PIIDemo() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isEmergency, setIsEmergency] = useState(false);

  const sanitize = async () => {
    if (!text.trim()) {
      setResult(null);
      setCount(0);
      setIsEmergency(false);
      return;
    }

    setLoading(true);
    setResult(null);
    setCount(0);
    setIsEmergency(false);

    try {
      const response = await axios.post<SafetyResponse>(
        apiUrl("/safety/check"),
        {
          text: text,
        }
      );

      const data = response.data;

      setResult(
        data.is_emergency
          ? data.refusal_message || "Emergency detected."
          : data.sanitized_text
      );

      setIsEmergency(data.is_emergency);

      if (data.pii_detected) {
        const redactionMatches = data.sanitized_text.match(
          /\[(EMAIL|PHONE|SSN|DATE_OF_BIRTH|MEDICAL_RECORD_NUMBER|ADDRESS|NAME_PATTERN)_REDACTED\]/g
        );

        setCount(redactionMatches?.length ?? 1);
      } else {
        setCount(0);
      }
    } catch (error) {
      console.error("Safety check failed:", error);
      setResult("Unable to connect to the safety service.");
      setCount(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="pii-card">
      <div className="safety-test-heading">
        <div>
          <span className="tiny-label">
            PII SANITIZATION
          </span>

          <h2>Protect sensitive information.</h2>
        </div>

        <span>LIVE BACKEND</span>
      </div>

      <p>
        Enter text containing personal information to test
        the real preprocessing safety layer.
      </p>

      <textarea
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setResult(null);
          setCount(0);
          setIsEmergency(false);
        }}
        placeholder="Example: My name is John Smith, patient ID 45219, email john@example.com..."
      />

      <button
        type="button"
        className="sanitize-button"
        onClick={sanitize}
        disabled={loading}
      >
        {loading ? "CHECKING..." : "SANITIZE INPUT"}
      </button>

      {result !== null && (
        <div className="sanitized-result">
          <div>
            <span>
              {isEmergency
                ? "⚠ EMERGENCY DETECTED"
                : "✓ PII SANITIZATION COMPLETE"}
            </span>

            <small>
              {isEmergency
                ? "Safety guardrail activated"
                : count === 0
                ? "No PII detected"
                : `${count} item${count === 1 ? "" : "s"} redacted`}
            </small>
          </div>

          <p>{result}</p>
        </div>
      )}
    </section>
  );
}