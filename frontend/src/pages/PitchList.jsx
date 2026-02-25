import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { listSessions, deleteSession, restoreSession, permanentlyDeleteSession } from "../api";
import { parseSentiment, parseProductName, sentimentColor, aggregateSentiments } from "../utils/sentiment";

const PAGE_SIZE = 10;
const SECTORS = ["tech", "financial", "political"];

export default function PitchList() {
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef(null);

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearch(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(val);
      setOffset(0);
    }, 300);
  };

  const fetchSessions = useCallback(() => {
    setLoading(true);
    setError(null);
    listSessions({
      limit: PAGE_SIZE,
      offset,
      search: debouncedSearch || undefined,
      sector: sector || undefined,
      deleted: showDeleted || undefined,
    })
      .then((data) => {
        setSessions(data.items);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [offset, debouncedSearch, sector, showDeleted]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleDelete = async (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await deleteSession(id);
      fetchSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRestore = async (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await restoreSession(id);
      fetchSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const handlePermanentDelete = async (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await permanentlyDeleteSession(id);
      fetchSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div>
      <div className="pitch-list-header">
        <h1>{showDeleted ? "Recently Deleted" : "Your Pitches"}</h1>
        <Link to="/new" className="btn-new-pitch">+ New Pitch</Link>
      </div>

      <div className="search-filter-bar">
        <input
          type="text"
          className="search-input"
          placeholder="Search pitches..."
          value={search}
          onChange={handleSearchChange}
        />
        <select
          className="sector-filter"
          value={sector}
          onChange={(e) => { setSector(e.target.value); setOffset(0); }}
        >
          <option value="">All sectors</option>
          {SECTORS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button
          className={`deleted-toggle ${showDeleted ? "active" : ""}`}
          onClick={() => { setShowDeleted(!showDeleted); setOffset(0); }}
          type="button"
        >
          {showDeleted ? "Show Active" : "Recently Deleted"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <p className="loading">Loading...</p>
      ) : sessions.length === 0 ? (
        <p>{showDeleted ? "No deleted pitches." : offset === 0 ? <>No pitches yet. <Link to="/new">Create your first pitch.</Link></> : "No results."}</p>
      ) : (
        <>
          <div className="pitch-grid">
            {sessions.map((s) => (
              <PitchCard
                key={s.id}
                session={s}
                isDeleted={showDeleted}
                onDelete={handleDelete}
                onRestore={handleRestore}
                onPermanentDelete={handlePermanentDelete}
              />
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

function PitchCard({ session, isDeleted, onDelete, onRestore, onPermanentDelete }) {
  const name = parseProductName(session.question);
  const responses = session.responses || [];
  const hasSentiment = responses.length > 0;
  const sentiments = hasSentiment ? aggregateSentiments(responses) : null;
  const positivePercent = sentiments && sentiments.total > 0
    ? Math.round((sentiments.positive / sentiments.total) * 100)
    : 0;

  const daysRemaining = isDeleted && session.deleted_at
    ? Math.max(0, 30 - Math.floor((Date.now() - new Date(session.deleted_at).getTime()) / (1000 * 60 * 60 * 24)))
    : null;

  return (
    <Link to={`/sessions/${session.id}`} className={`pitch-card ${isDeleted ? "deleted" : ""}`}>
      <div className="pitch-card-top-row">
        <h3 className="pitch-card-name">{name}</h3>
        {!isDeleted && (
          <button
            className="pitch-card-delete"
            onClick={(e) => onDelete(e, session.id)}
            title="Delete"
            type="button"
          >
            &times;
          </button>
        )}
      </div>
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
        {isDeleted && daysRemaining !== null ? (
          <span className="days-remaining">{daysRemaining}d left</span>
        ) : (
          <span>{new Date(session.created_at).toLocaleDateString()}</span>
        )}
      </div>
      {isDeleted && (
        <div className="deleted-actions">
          <button
            className="btn-restore"
            onClick={(e) => onRestore(e, session.id)}
            type="button"
          >
            Restore
          </button>
          <button
            className="btn-permanent-delete"
            onClick={(e) => onPermanentDelete(e, session.id)}
            type="button"
          >
            Delete Forever
          </button>
        </div>
      )}
    </Link>
  );
}
