import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../api";

const SECTORS = ["", "tech", "financial", "political"];
const AGE_GROUPS = ["", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"];
const GENDERS = ["", "male", "female", "non-binary"];

export default function NewSession() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [sector, setSector] = useState("");
  const [numPersonas, setNumPersonas] = useState(5);
  const [ageGroup, setAgeGroup] = useState("");
  const [gender, setGender] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const demographic_filter = {};
    if (ageGroup) demographic_filter.age_group = ageGroup;
    if (gender) demographic_filter.gender = gender;

    try {
      const result = await createSession({
        question,
        sector: sector || null,
        num_personas: numPersonas,
        demographic_filter: Object.keys(demographic_filter).length
          ? demographic_filter
          : null,
      });
      navigate(`/sessions/${result.session_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>New Focus Group Session</h1>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <label>
          Question
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
            placeholder="What do you think about..."
          />
        </label>

        <label>
          Sector
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {s || "All sectors"}
              </option>
            ))}
          </select>
        </label>

        <label>
          Number of personas
          <input
            type="number"
            min={1}
            max={50}
            value={numPersonas}
            onChange={(e) => setNumPersonas(Number(e.target.value))}
          />
        </label>

        <label>
          Age group (optional)
          <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
            {AGE_GROUPS.map((a) => (
              <option key={a} value={a}>
                {a || "Any"}
              </option>
            ))}
          </select>
        </label>

        <label>
          Gender (optional)
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            {GENDERS.map((g) => (
              <option key={g} value={g}>
                {g || "Any"}
              </option>
            ))}
          </select>
        </label>

        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Running..." : "Run Focus Group"}
        </button>
      </form>
    </div>
  );
}
