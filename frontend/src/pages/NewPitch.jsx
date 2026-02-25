import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../api";

const SECTORS = ["", "tech", "financial", "political"];
const AGE_GROUPS = ["", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"];
const GENDERS = ["", "male", "female", "non-binary"];

export default function NewPitch() {
  const navigate = useNavigate();
  const [productName, setProductName] = useState("");
  const [description, setDescription] = useState("");
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

    const question = `Product: ${productName.trim()}\n\n${description.trim()}`;

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
      <h1>Pitch Your Product</h1>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <label>
          Product Name
          <input
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            required
            placeholder="e.g. SmartBudget"
          />
        </label>

        <label>
          Describe your product
          <span className="helper-text">
            Write your pitch the way you'd present it to a real focus group.
            What does it do? Who is it for? Why should someone care?
          </span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            placeholder="SmartBudget is a mobile app that uses AI to automatically categorize your spending and suggest personalized saving goals..."
            className="pitch-textarea"
          />
        </label>

        <fieldset className="target-audience">
          <legend>Target audience</legend>
          <div className="audience-filters">
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
              Age group
              <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                {AGE_GROUPS.map((a) => (
                  <option key={a} value={a}>
                    {a || "Any"}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Gender
              <select value={gender} onChange={(e) => setGender(e.target.value)}>
                {GENDERS.map((g) => (
                  <option key={g} value={g}>
                    {g || "Any"}
                  </option>
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

        <button type="submit" disabled={loading || !productName.trim() || !description.trim()}>
          {loading ? "Running..." : "Run Focus Group"}
        </button>
      </form>
    </div>
  );
}
