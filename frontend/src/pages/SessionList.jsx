import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions } from "../api";

const PAGE_SIZE = 10;

export default function SessionList() {
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
      <h1>Focus Group Sessions</h1>
      {loading ? (
        <p>Loading...</p>
      ) : sessions.length === 0 && offset === 0 ? (
        <p>No sessions yet. <Link to="/new">Create one.</Link></p>
      ) : (
        <>
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
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "1rem" }}>
            <button disabled={!hasPrev} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              Previous
            </button>
            <span>Page {page} of {totalPages}</span>
            <button disabled={!hasNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
