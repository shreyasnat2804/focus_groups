import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions } from "../api";
import { parseSentiment, parseProductName, sentimentColor, aggregateSentiments } from "../utils/sentiment";

const PAGE_SIZE = 10;

export default function PitchList() {
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listSessions({ limit: PAGE_SIZE, offset })
      .then((data) => {
        setSessions(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [offset]);

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  if (error) return <div className="error">{error}</div>;

  return (
    <div>
      <div className="pitch-list-header">
        <h1>Your Pitches</h1>
        <Link to="/new" className="btn-new-pitch">+ New Pitch</Link>
      </div>
      {loading ? (
        <p className="loading">Loading...</p>
      ) : sessions.length === 0 && offset === 0 ? (
        <p>No pitches yet. <Link to="/new">Create your first pitch.</Link></p>
      ) : (
        <>
          <div className="pitch-grid">
            {sessions.map((s) => (
              <PitchCard key={s.id} session={s} />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="pagination">
              <button disabled={!hasPrev} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button disabled={!hasNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function PitchCard({ session }) {
  const name = parseProductName(session.question);
  const responses = session.responses || [];
  const hasSentiment = responses.length > 0;
  const sentiments = hasSentiment ? aggregateSentiments(responses) : null;
  const positivePercent = sentiments && sentiments.total > 0
    ? Math.round((sentiments.positive / sentiments.total) * 100)
    : 0;

  return (
    <Link to={`/sessions/${session.id}`} className="pitch-card">
      <h3 className="pitch-card-name">{name}</h3>
      <div className="pitch-card-meta">
        {session.sector && <span className="sector-tag">{session.sector}</span>}
        <span>{session.num_personas} {session.num_personas === 1 ? "person" : "people"}</span>
      </div>
      {hasSentiment && (
        <div className="sentiment-bar-container">
          <div className="sentiment-bar">
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
          <span className="sentiment-pct">{positivePercent}% positive</span>
        </div>
      )}
      <div className="pitch-card-footer">
        <span className={`status-badge status-${session.status}`}>{session.status}</span>
        <span>{new Date(session.created_at).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}
