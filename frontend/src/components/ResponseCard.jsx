export default function ResponseCard({ response }) {
  return (
    <div className="card">
      <h3>{response.persona_summary}</h3>
      <p>{response.response_text}</p>
    </div>
  );
}
