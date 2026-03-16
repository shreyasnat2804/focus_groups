import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SECTORS } from "../constants";

const STEPS = [
  {
    title: "Welcome to FocusTest",
    body: "Get instant, diverse feedback on your product ideas using AI-powered synthetic focus groups. No recruiting. No scheduling. Just real insight.",
  },
  {
    title: "Pick Your Sector",
    body: "We have specialized models for different industries. Choose the one closest to your product — you can always change it later.",
  },
  {
    title: "You're All Set",
    body: "Create your first pitch and get feedback from a diverse panel in seconds. Write your pitch, pick your audience, and hit run.",
  },
];

const SECTOR_DETAILS = {
  tech: { emoji: "💻", desc: "Software, hardware, apps, SaaS" },
  financial: { emoji: "📊", desc: "Fintech, banking, insurance, investing" },
  political: { emoji: "🏛️", desc: "Policy, campaigns, civic tech" },
};

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [selectedSector, setSelectedSector] = useState("");
  const navigate = useNavigate();

  function handleFinish() {
    localStorage.setItem("focustest_onboarded", "true");
    if (selectedSector) {
      localStorage.setItem("focustest_preferred_sector", selectedSector);
    }
    navigate("/new");
  }

  const isLast = step === STEPS.length - 1;

  return (
    <div className="onboarding">
      {/* Background decoration */}
      <div className="onboarding-blob onboarding-blob-1" />
      <div className="onboarding-blob onboarding-blob-2" />

      <div className="onboarding-card">
        {/* Progress dots */}
        <div className="onboarding-progress">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`onboarding-dot ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}
            />
          ))}
        </div>

        {/* Step content */}
        <h1 className="onboarding-title">{STEPS[step].title}</h1>
        <p className="onboarding-body">{STEPS[step].body}</p>

        {/* Sector selector on step 2 */}
        {step === 1 && (
          <div className="onboarding-sectors">
            {SECTORS.map((s) => (
              <button
                key={s}
                type="button"
                className={`onboarding-sector-btn ${selectedSector === s ? "selected" : ""}`}
                onClick={() => setSelectedSector(s === selectedSector ? "" : s)}
              >
                <span className="onboarding-sector-emoji">
                  {SECTOR_DETAILS[s].emoji}
                </span>
                <span className="onboarding-sector-name">{s}</span>
                <span className="onboarding-sector-desc">
                  {SECTOR_DETAILS[s].desc}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Illustration on step 3 */}
        {step === 2 && (
          <div className="onboarding-ready-graphic">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
        )}

        {/* Navigation */}
        <div className="onboarding-actions">
          {step > 0 && (
            <button
              type="button"
              className="onboarding-btn-back"
              onClick={() => setStep(step - 1)}
            >
              Back
            </button>
          )}
          {isLast ? (
            <button
              type="button"
              className="onboarding-btn-next"
              onClick={handleFinish}
            >
              Create Your First Pitch
            </button>
          ) : (
            <button
              type="button"
              className="onboarding-btn-next"
              onClick={() => setStep(step + 1)}
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
