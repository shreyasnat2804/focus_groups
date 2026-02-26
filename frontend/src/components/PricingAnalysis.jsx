import { useState, useEffect } from "react";
import { runWtpAnalysis } from "../api";
import VanWestendorpChart from "./VanWestendorpChart";
import DemandCurveChart from "./DemandCurveChart";
import PriceGauge from "./PriceGauge";

const SEGMENT_OPTIONS = [
  { value: "income_bracket", label: "Income bracket" },
  { value: "age_group", label: "Age group" },
  { value: "gender", label: "Gender" },
];

const DEFAULT_PRICES = "49, 99, 199, 299, 499";

export default function PricingAnalysis({ sessionId }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Config
  const [pricesInput, setPricesInput] = useState(DEFAULT_PRICES);
  const [segmentBy, setSegmentBy] = useState("income_bracket");

  // Restore from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(`wtp_results_${sessionId}`);
    if (saved) {
      try {
        const { results: savedResults, pricesInput: savedPrices, segmentBy: savedSegment } = JSON.parse(saved);
        setResults(savedResults);
        setPricesInput(savedPrices);
        setSegmentBy(savedSegment);
        setExpanded(true);
      } catch {
        // ignore corrupt saved state
      }
    }
  }, [sessionId]);

  async function handleRun() {
    setLoading(true);
    setError(null);

    const pricePoints = pricesInput
      .split(",")
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0);

    if (pricePoints.length === 0) {
      setError("Enter at least one valid price point.");
      setLoading(false);
      return;
    }

    try {
      const data = await runWtpAnalysis(sessionId, {
        price_points: pricePoints,
        segment_by: segmentBy,
      });
      setResults(data);
      setExpanded(true);
      localStorage.setItem(
        `wtp_results_${sessionId}`,
        JSON.stringify({ results: data, pricesInput, segmentBy })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="pricing-analysis-section">
      <div className="pricing-analysis-header">
        <h2>Pricing Analysis</h2>
        {results && (
          <button
            type="button"
            className="pitch-toggle"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
        )}
      </div>

      {!results && (
        <p className="pricing-analysis-desc">
          Run willingness-to-pay analysis on this panel's personas to find
          optimal pricing and demand curves.
        </p>
      )}

      <div className="pricing-config">
        <label>
          Price points ($)
          <input
            type="text"
            value={pricesInput}
            onChange={(e) => setPricesInput(e.target.value)}
            placeholder="49, 99, 199, 299, 499"
            className="pricing-prices-input"
          />
        </label>
        <label>
          Segment by
          <select value={segmentBy} onChange={(e) => setSegmentBy(e.target.value)}>
            {SEGMENT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={handleRun}
          disabled={loading}
          className="pricing-run-btn"
        >
          {loading ? "Analyzing..." : results ? "Re-run Analysis" : "Run Pricing Analysis"}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {results && expanded && (
        <div className="pricing-results">
          <div className="pricing-results-meta">
            {results.num_personas} personas analyzed
          </div>

          <PriceGauge
            label="Recommended Price"
            optimalPrice={results.van_westendorp.optimal_price}
            minPrice={Math.min(...results.van_westendorp.curves.price_points)}
            maxPrice={Math.max(...results.van_westendorp.curves.price_points)}
          />

          <VanWestendorpChart
            curves={results.van_westendorp.curves}
            pricePoints={{
              optimal_price: results.van_westendorp.optimal_price,
              acceptable_range: results.van_westendorp.acceptable_range,
            }}
          />

          <DemandCurveChart
            demandCurve={results.gabor_granger.demand_curve}
            segmentDemand={results.segments?.demand}
            segmentDimension={results.segments?.dimension}
          />

          {/* Segmented PSM summary */}
          {results.segments?.psm && Object.keys(results.segments.psm).length > 0 && (
            <div className="wtp-segment-summary">
              <h3>Price Sensitivity by {results.segments.dimension?.replace("_", " ")}</h3>
              <table className="wtp-segment-table">
                <thead>
                  <tr>
                    <th>Segment</th>
                    <th>N</th>
                    <th>Optimal Price</th>
                    <th>Acceptable Range</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(results.segments.psm)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([name, seg]) => (
                      <tr key={name}>
                        <td>{name.replace("_", " ")}</td>
                        <td>{seg.n}</td>
                        <td>${seg.optimal_price.toFixed(0)}</td>
                        <td>
                          ${seg.acceptable_range[0].toFixed(0)} &ndash; $
                          {seg.acceptable_range[1].toFixed(0)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
