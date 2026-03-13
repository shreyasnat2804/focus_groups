import { useState, useEffect, useMemo } from "react";
import { runWtpAnalysis } from "../api";
import VanWestendorpChart from "./VanWestendorpChart";
import DemandCurveChart from "./DemandCurveChart";

const SEGMENT_OPTIONS = [
  { value: "income_bracket", label: "Income bracket" },
  { value: "age_group", label: "Age group" },
  { value: "gender", label: "Gender" },
];

const PRICING_MODELS = [
  { value: "one_time", label: "One-time purchase" },
  { value: "subscription", label: "Subscription" },
  { value: "hybrid", label: "Upfront + Subscription" },
];

const STORAGE_KEY = (id) => `wtp_results_${id}`;

function parseCommaList(str) {
  return str
    .split(",")
    .map((s) => parseFloat(s.trim()))
    .filter((n) => !isNaN(n) && n > 0);
}

function formatCurrency(n) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export default function PricingAnalysis({ sessionId }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Config
  const [pricingModel, setPricingModel] = useState("one_time");
  const [segmentBy, setSegmentBy] = useState("income_bracket");

  // Per-model inputs
  const [pricesInput, setPricesInput] = useState("");
  const [upfrontInput, setUpfrontInput] = useState("");
  const [subscriptionInput, setSubscriptionInput] = useState("");

  // Restore from localStorage on mount
  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY(sessionId));
    if (!raw) return;
    try {
      const saved = JSON.parse(raw);
      const activeModel = saved.activePricingModel || "one_time";
      setPricingModel(activeModel);

      const modelData = saved[activeModel];
      if (modelData) {
        setResults(modelData.results);
        if (modelData.segmentBy) setSegmentBy(modelData.segmentBy);
        if (modelData.pricesInput) setPricesInput(modelData.pricesInput);
        if (modelData.upfrontInput) setUpfrontInput(modelData.upfrontInput);
        if (modelData.subscriptionInput) setSubscriptionInput(modelData.subscriptionInput);
        setExpanded(true);
      }
    } catch {
      // ignore corrupt saved state
    }
  }, [sessionId]);

  // When pricing model changes, restore saved data for that model
  function handleModelChange(newModel) {
    setPricingModel(newModel);
    setError(null);

    const raw = localStorage.getItem(STORAGE_KEY(sessionId));
    if (raw) {
      try {
        const saved = JSON.parse(raw);
        const modelData = saved[newModel];
        if (modelData) {
          setResults(modelData.results);
          if (modelData.segmentBy) setSegmentBy(modelData.segmentBy);
          if (modelData.pricesInput) setPricesInput(modelData.pricesInput);
          if (modelData.upfrontInput) setUpfrontInput(modelData.upfrontInput);
          if (modelData.subscriptionInput) setSubscriptionInput(modelData.subscriptionInput);
          setExpanded(true);
          return;
        }
      } catch {
        // ignore
      }
    }

    // No saved data for this model — clear results and reset inputs
    setResults(null);
    setPricesInput("");
    setUpfrontInput("");
    setSubscriptionInput("");
    setExpanded(false);
  }

  // Hybrid combination preview
  const hybridPreview = useMemo(() => {
    if (pricingModel !== "hybrid") return null;
    const upfronts = parseCommaList(upfrontInput);
    const subs = parseCommaList(subscriptionInput);
    if (upfronts.length === 0 || subs.length === 0) return null;

    const combos = [];
    for (const u of upfronts) {
      for (const s of subs) {
        combos.push({ upfront: u, monthly: s, total: u + s * 12 });
      }
    }
    combos.sort((a, b) => a.total - b.total);
    return combos;
  }, [pricingModel, upfrontInput, subscriptionInput]);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const params = {
        pricing_model: pricingModel,
        segment_by: segmentBy,
      };

      if (pricingModel === "hybrid") {
        const upfronts = parseCommaList(upfrontInput);
        const subs = parseCommaList(subscriptionInput);
        if (upfronts.length === 0 || subs.length === 0) {
          throw new Error("Please provide both setup fees and monthly prices for hybrid model.");
        }
        params.upfront_price_points = upfronts;
        params.subscription_price_points = subs;
      } else {
        const prices = parseCommaList(pricesInput);
        if (prices.length > 0) {
          params.price_points = prices;
        }
      }

      const data = await runWtpAnalysis(sessionId, params);
      setResults(data);
      setExpanded(true);

      // Save per-model to localStorage
      const raw = localStorage.getItem(STORAGE_KEY(sessionId));
      const saved = raw ? JSON.parse(raw) : {};
      saved.activePricingModel = pricingModel;
      saved[pricingModel] = {
        results: data,
        segmentBy,
        pricesInput,
        upfrontInput,
        subscriptionInput,
      };
      localStorage.setItem(STORAGE_KEY(sessionId), JSON.stringify(saved));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const isHybrid = results?.pricing_model === "hybrid";

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

      {/* Pricing model selector */}
      <div className="pricing-model-selector">
        {PRICING_MODELS.map((m) => (
          <button
            key={m.value}
            type="button"
            className={`pricing-model-btn${pricingModel === m.value ? " active" : ""}`}
            onClick={() => handleModelChange(m.value)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Dynamic price inputs */}
      <div className="pricing-config">
        {pricingModel === "hybrid" ? (
          <>
            <label>
              Setup fee options (comma-separated)
              <input
                type="text"
                value={upfrontInput}
                onChange={(e) => setUpfrontInput(e.target.value)}
                placeholder="500, 1000, 2500"
              />
            </label>
            <label>
              Monthly price options (comma-separated)
              <input
                type="text"
                value={subscriptionInput}
                onChange={(e) => setSubscriptionInput(e.target.value)}
                placeholder="49, 99, 199"
              />
            </label>
          </>
        ) : (
          <label>
            {pricingModel === "subscription" ? "Monthly price points" : "Price points"} (comma-separated, optional)
            <input
              type="text"
              value={pricesInput}
              onChange={(e) => setPricesInput(e.target.value)}
              placeholder={pricingModel === "subscription" ? "9, 19, 49, 99, 199" : "99, 199, 299, 499, 999"}
            />
          </label>
        )}

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

      {/* Hybrid combination preview */}
      {pricingModel === "hybrid" && hybridPreview && (
        <div className="hybrid-preview">
          {hybridPreview.length} combination{hybridPreview.length !== 1 ? "s" : ""} will be tested:{" "}
          {hybridPreview.map((c, i) => (
            <span key={i}>
              {i > 0 && " · "}
              {formatCurrency(c.upfront)} + {formatCurrency(c.monthly)}/mo = {formatCurrency(c.total)}/yr
            </span>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {results && expanded && (
        <div className="pricing-results">
          <div className="pricing-results-meta">
            {results.num_personas} personas analyzed
            {isHybrid && " (prices normalized to 12-month total)"}
          </div>

          {/* Hybrid callout */}
          {isHybrid && results.hybrid_tiers && (
            <div className="hybrid-callout">
              Prices normalized to 12-month total cost for comparison.
              {(() => {
                const optimal = results.van_westendorp.optimal_price;
                const closest = results.hybrid_tiers.reduce((best, t) =>
                  Math.abs(t.total_12m - optimal) < Math.abs(best.total_12m - optimal) ? t : best
                );
                return ` Optimal tier: ${formatCurrency(closest.upfront)} setup + ${formatCurrency(closest.monthly)}/mo`;
              })()}
            </div>
          )}

          <div className="recommended-price">
            <div className="recommended-price-label">Recommended Price</div>
            <div className="recommended-price-value">
              {isHybrid
                ? `${formatCurrency(results.van_westendorp.optimal_price)}/yr total`
                : pricingModel === "subscription"
                  ? `${formatCurrency(results.van_westendorp.optimal_price)}/mo`
                  : formatCurrency(results.van_westendorp.optimal_price)
              }
            </div>
            {isHybrid && results.hybrid_tiers && (() => {
              const optimal = results.van_westendorp.optimal_price;
              const closest = results.hybrid_tiers.reduce((best, t) =>
                Math.abs(t.total_12m - optimal) < Math.abs(best.total_12m - optimal) ? t : best
              );
              return (
                <div className="recommended-price-breakdown">
                  {formatCurrency(closest.upfront)} setup + {formatCurrency(closest.monthly)}/mo
                </div>
              );
            })()}
            <div className="recommended-price-range">
              Acceptable range: {formatCurrency(results.van_westendorp.acceptable_range[0])}
              {" - "}{formatCurrency(results.van_westendorp.acceptable_range[1])}
              {isHybrid && "/yr"}
            </div>
          </div>

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
            pricingModel={results.pricing_model}
            hybridTiers={results.hybrid_tiers}
          />

          {/* Segmented PSM summary */}
          {results.segments?.psm && Object.keys(results.segments.psm).filter((n) => n !== "unknown").length > 0 && (
            <div className="wtp-segment-summary">
              <h3>Price Sensitivity by {results.segments.dimension?.replaceAll("_", " ")}</h3>
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
                    .filter(([name]) => name !== "unknown")
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([name, seg]) => (
                      <tr key={name}>
                        <td>{name.replaceAll("_", " ")}</td>
                        <td>{seg.n}</td>
                        <td>{formatCurrency(seg.optimal_price)}</td>
                        <td>
                          {formatCurrency(seg.acceptable_range[0])} &ndash;{" "}
                          {formatCurrency(seg.acceptable_range[1])}
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
