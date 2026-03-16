import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SECTORS } from "../constants";
import { useTheme } from "../hooks/useTheme";

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
  tech: { emoji: "\u{1F4BB}", desc: "Software, hardware, apps, SaaS" },
  financial: { emoji: "\u{1F4CA}", desc: "Fintech, banking, insurance, investing" },
  political: { emoji: "\u{1F3DB}\uFE0F", desc: "Policy, campaigns, civic tech" },
};

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [selectedSector, setSelectedSector] = useState("");
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

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
        {/* Theme toggle + Progress dots */}
        <div className="onboarding-header">
          <div className="onboarding-progress">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`onboarding-dot ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}
              />
            ))}
          </div>
          <button
            type="button"
            className="theme-toggle onboarding-theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
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
