import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getSession, createSession, rerunSession } from "../api";
import ResponseCard from "../components/ResponseCard";
import ExportButtons from "../components/ExportButtons";
import {
  parseProductName,
  parseProductDescription,
  aggregateSentiments,
} from "../utils/sentiment";

const SECTORS = ["", "tech", "financial", "political"];
const AGE_GROUPS = ["", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"];
const GENDERS = ["", "male", "female", "non-binary"];

export default function PitchResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

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
  if (!session) return <p className="loading">Loading session...</p>;

  const productName = parseProductName(session.question);
  const responses = session.responses || [];
  const sentiments = aggregateSentiments(responses);

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
      <h1>{productName}</h1>
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
                    {SECTORS.map((s) => (
                      <option key={s} value={s}>{s || "All sectors"}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Age group
                  <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                    {AGE_GROUPS.map((a) => (
                      <option key={a} value={a}>{a || "Any"}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Gender
                  <select value={gender} onChange={(e) => setGender(e.target.value)}>
                    {GENDERS.map((g) => (
                      <option key={g} value={g}>{g || "Any"}</option>
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
