import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getSession, createSession, rerunSession, renameSession } from "../api";
import ResponseCard from "../components/ResponseCard";
import ExportButtons from "../components/ExportButtons";
import PricingAnalysis from "../components/PricingAnalysis";
import ErrorBoundary from "../components/ErrorBoundary";
import SentimentBar from "../components/SentimentBar";
import { SessionDetailSkeleton } from "../components/Skeleton";
import {
  parseProductName,
  parseProductDescription,
  aggregateSentiments,
} from "../utils/sentiment";
import { SECTORS, AGE_GROUPS, GENDERS } from "../constants";

export default function PitchResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  // Session name editing state
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const nameInputRef = useRef(null);

  // Pitch editing state
  const [pitchExpanded, setPitchExpanded] = useState(false);
  const [editedPitch, setEditedPitch] = useState("");

  // Focus group composition overrides
  const [sector, setSector] = useState("");
  const [numPersonas, setNumPersonas] = useState(5);
  const [ageGroup, setAgeGroup] = useState("");
  const [gender, setGender] = useState("");

  // Rerun state
  const [rerunning, setRerunning] = useState(false);
  const [rerunError, setRerunError] = useState(null);
  const [showRerunChoice, setShowRerunChoice] = useState(false);

  useEffect(() => {
    getSession(id)
      .then((s) => {
        setSession(s);
        setNameValue(s.name ?? parseProductName(s.question));
        setEditedPitch(parseProductDescription(s.question));
        // Initialize composition from session
        setSector(s.sector || "");
        setNumPersonas(s.num_personas || 5);
        const df = s.demographic_filter || {};
        setAgeGroup(df.age_group || "");
        setGender(df.gender || "");
      })
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!session) return <SessionDetailSkeleton />;

  const productName = parseProductName(session.question);
  const displayName = nameValue || productName;
  const responses = session.responses || [];
  const sentiments = aggregateSentiments(responses);

  function startEditingName() {
    setEditingName(true);
    // Focus the input after render
    setTimeout(() => nameInputRef.current?.select(), 0);
  }

  async function commitName() {
    const trimmed = nameValue.trim();
    const resolved = trimmed || null;
    setEditingName(false);
    if (resolved === (session.name ?? null) || (!resolved && !session.name && trimmed === productName)) {
      // No real change
      setNameValue(session.name ?? productName);
      return;
    }
    try {
      await renameSession(id, resolved);
      setSession((prev) => ({ ...prev, name: resolved }));
      setNameValue(resolved ?? productName);
    } catch {
      // Revert on error
      setNameValue(session.name ?? productName);
    }
  }

  function handleNameKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      commitName();
    } else if (e.key === "Escape") {
      setEditingName(false);
      setNameValue(session.name ?? productName);
    }
  }

  function buildQuestion() {
    return `Product: ${productName}\n\n${editedPitch.trim()}`;
  }

  function buildDemographicFilter() {
    const df = {};
    if (ageGroup) df.age_group = ageGroup;
    if (gender) df.gender = gender;
    return Object.keys(df).length ? df : null;
  }

  async function handleNewSession() {
    setRerunning(true);
    setRerunError(null);
    try {
      const result = await createSession({
        question: buildQuestion(),
        sector: sector || null,
        num_personas: numPersonas,
        demographic_filter: buildDemographicFilter(),
      });
      navigate(`/sessions/${result.session_id}`);
    } catch (err) {
      setRerunError(err.message);
    } finally {
      setRerunning(false);
      setShowRerunChoice(false);
    }
  }

  async function handleOverwrite() {
    setRerunning(true);
    setRerunError(null);
    try {
      await rerunSession(id, {
        question: buildQuestion(),
        sector: sector || null,
        num_personas: numPersonas,
        demographic_filter: buildDemographicFilter(),
      });
      // Reload session data
      const updated = await getSession(id);
      setSession(updated);
      setEditedPitch(parseProductDescription(updated.question));
      setPitchExpanded(false);
    } catch (err) {
      setRerunError(err.message);
    } finally {
      setRerunning(false);
      setShowRerunChoice(false);
    }
  }

  return (
    <div>
      {editingName ? (
        <input
          ref={nameInputRef}
          className="session-name-input"
          value={nameValue}
          onChange={(e) => setNameValue(e.target.value)}
          onBlur={commitName}
          onKeyDown={handleNameKeyDown}
          autoFocus
        />
      ) : (
        <h1
          className="session-name-heading"
          onClick={startEditingName}
          title="Click to rename"
        >
          {displayName}
        </h1>
      )}
      <div className="pitch-meta">
        {session.sector && <span className="sector-tag">{session.sector}</span>}
        <span>{session.num_personas} personas</span>
        <span>{new Date(session.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</span>
      </div>

      {/* Collapsible pitch section */}
      <div className="pitch-edit-section">
        <button
          type="button"
          className="pitch-toggle"
          onClick={() => setPitchExpanded(!pitchExpanded)}
        >
          {pitchExpanded ? "Hide pitch" : "View pitch"}
        </button>

        {pitchExpanded && (
          <div className="pitch-edit-body">
            <textarea
              className="pitch-textarea"
              value={editedPitch}
              onChange={(e) => setEditedPitch(e.target.value)}
            />

            <fieldset className="target-audience">
              <legend>Focus group composition</legend>
              <div className="audience-filters">
                <label>
                  Sector
                  <select value={sector} onChange={(e) => setSector(e.target.value)}>
                    <option value="">All sectors</option>
                    {SECTORS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Age group
                  <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                    <option value="">Any</option>
                    {AGE_GROUPS.map((a) => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Gender
                  <select value={gender} onChange={(e) => setGender(e.target.value)}>
                    <option value="">Any</option>
                    {GENDERS.map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </label>
              </div>
            </fieldset>

            <label>
              Panel size
              <div className="panel-size-row">
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={numPersonas}
                  onChange={(e) => setNumPersonas(Number(e.target.value))}
                />
                <span>people</span>
              </div>
            </label>

            {rerunError && <div className="error">{rerunError}</div>}

            <div className="rerun-actions">
              {!showRerunChoice ? (
                <button
                  type="button"
                  onClick={() => setShowRerunChoice(true)}
                  disabled={rerunning || !editedPitch.trim()}
                >
                  Re-run
                </button>
              ) : (
                <>
                  <button type="button" onClick={handleNewSession} disabled={rerunning}>
                    {rerunning ? "Running..." : "New session"}
                  </button>
                  <button type="button" onClick={handleOverwrite} disabled={rerunning}>
                    {rerunning ? "Running..." : "Overwrite this session"}
                  </button>
                  <button
                    type="button"
                    className="btn-cancel"
                    onClick={() => setShowRerunChoice(false)}
                    disabled={rerunning}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {responses.length > 0 && (
        <div className="sentiment-overview">
          <h2>Sentiment Overview</h2>
          <SentimentBar sentiments={sentiments} size="large" showLabels />
        </div>
      )}

      <ExportButtons sessionId={session.id} />

      {session.status === "completed" && responses.length > 0 && (
        <ErrorBoundary
          fallback={({ reset }) => (
            <div className="chart-error">
              <p>Failed to render pricing analysis.</p>
              <button onClick={reset}>Retry</button>
            </div>
          )}
        >
          <PricingAnalysis sessionId={session.id} />
        </ErrorBoundary>
      )}

      <h2>Panel Responses ({responses.length})</h2>
      {responses.length === 0 ? (
        <p>No responses yet.</p>
      ) : (
        responses.map((r) => (
          <ErrorBoundary
            key={r.id}
            fallback={() => (
              <div className="card response-card error">
                <p>Failed to render this response.</p>
              </div>
            )}
          >
            <ResponseCard response={r} />
          </ErrorBoundary>
        ))
      )}
    </div>
  );
}
