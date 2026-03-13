import { parseSentiment, sentimentColor } from "../utils/sentiment";

export default function ResponseCard({ response }) {
  const { sentiment, text } = parseSentiment(response.response_text);

  return (
    <div className="response-card">
      <div className="response-card-header">
        <span className="sentiment-badge" style={{ backgroundColor: sentimentColor(sentiment) }}>
          {sentiment || "UNKNOWN"}
        </span>
        <span className="persona-summary">{response.persona_summary}</span>
      </div>
      <p className="response-text">{text}</p>
    </div>
  );
}
