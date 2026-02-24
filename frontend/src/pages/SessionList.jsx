import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions } from "../api";

export default function SessionList() {
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <div>
      <h1>Focus Group Sessions</h1>
      {sessions.length === 0 ? (
        <p>No sessions yet. <Link to="/new">Create one.</Link></p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Question</th>
              <th>Sector</th>
              <th>Personas</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>
                  <Link to={`/sessions/${s.id}`}>#{s.id}</Link>
                </td>
                <td>{s.question}</td>
                <td>{s.sector || "all"}</td>
                <td>{s.num_personas}</td>
                <td>{s.status}</td>
                <td>{new Date(s.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
