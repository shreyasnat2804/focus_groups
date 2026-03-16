import { parseSentiment } from "../utils/sentiment";

function sentimentClass(sentiment) {
  switch (sentiment) {
    case "POSITIVE": return "positive";
    case "NEGATIVE": return "negative";
    case "MIXED": return "mixed";
    case "NEUTRAL": return "neutral";
    default: return "neutral";
  }
}

export default function ResponseCard({ response }) {
  const { sentiment, text } = parseSentiment(response.response_text);

  return (
    <div className="response-card">
      <div className="response-card-header">
        <span className={`sentiment-badge ${sentimentClass(sentiment)}`}>
          {sentiment || "UNKNOWN"}
        </span>
        <span className="persona-summary">{response.persona_summary}</span>
      </div>
      <p className="response-text">{text}</p>
    </div>
  );
}
