import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSession } from "../api";
import ResponseCard from "../components/ResponseCard";
import ExportButtons from "../components/ExportButtons";

export default function SessionDetail() {
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

  return (
    <div>
      <h1>Session #{session.id}</h1>

      <div className="meta">
        <p>Question: {session.question}</p>
        <p>Sector: {session.sector || "all"}</p>
        <p>Status: {session.status}</p>
        <p>Personas: {session.num_personas}</p>
        <p>Created: {new Date(session.created_at).toLocaleString()}</p>
      </div>

      <ExportButtons sessionId={session.id} />

      <h2>Responses ({session.responses.length})</h2>
      {session.responses.length === 0 ? (
        <p>No responses yet.</p>
      ) : (
        session.responses.map((r) => <ResponseCard key={r.id} response={r} />)
      )}
    </div>
  );
}
