import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSession } from "../api";
import ResponseCard from "../components/ResponseCard";
import ExportButtons from "../components/ExportButtons";
import {
  parseProductName,
  aggregateSentiments,
} from "../utils/sentiment";

export default function PitchResults() {
  const { id } = useParams();
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSession(id)
      .then(setSession)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!session) return <p className="loading">Loading session...</p>;

  const productName = parseProductName(session.question);
  const responses = session.responses || [];
  const sentiments = aggregateSentiments(responses);

  return (
    <div>
      <h1>{productName}</h1>
      <div className="pitch-meta">
        {session.sector && <span className="sector-tag">{session.sector}</span>}
        <span>{session.num_personas} personas</span>
        <span>{new Date(session.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
      </div>

      {responses.length > 0 && (
        <div className="sentiment-overview">
          <h2>Sentiment Overview</h2>
          <div className="sentiment-bar-large">
            {sentiments.positive > 0 && (
              <div
                className="sentiment-segment positive"
                style={{ width: `${(sentiments.positive / sentiments.total) * 100}%` }}
              />
            )}
            {sentiments.mixed > 0 && (
              <div
                className="sentiment-segment mixed"
                style={{ width: `${(sentiments.mixed / sentiments.total) * 100}%` }}
              />
            )}
            {sentiments.negative > 0 && (
              <div
                className="sentiment-segment negative"
                style={{ width: `${(sentiments.negative / sentiments.total) * 100}%` }}
              />
            )}
            {sentiments.neutral > 0 && (
              <div
                className="sentiment-segment neutral"
                style={{ width: `${(sentiments.neutral / sentiments.total) * 100}%` }}
              />
            )}
          </div>
          <div className="sentiment-labels">
            {sentiments.positive > 0 && <span className="sentiment-label positive">{sentiments.positive} positive</span>}
            {sentiments.mixed > 0 && <span className="sentiment-label mixed">{sentiments.mixed} mixed</span>}
            {sentiments.negative > 0 && <span className="sentiment-label negative">{sentiments.negative} negative</span>}
            {sentiments.neutral > 0 && <span className="sentiment-label neutral">{sentiments.neutral} neutral</span>}
          </div>
        </div>
      )}

      <ExportButtons sessionId={session.id} />

      <h2>Panel Responses ({responses.length})</h2>
      {responses.length === 0 ? (
        <p>No responses yet.</p>
      ) : (
        responses.map((r) => <ResponseCard key={r.id} response={r} />)
      )}
    </div>
  );
}
