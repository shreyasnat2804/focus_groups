import { Link } from "react-router-dom";
import { useTheme } from "../hooks/useTheme";

const FEATURES = [
  {
    title: "Instant Feedback",
    desc: "Get diverse consumer reactions to your pitch in seconds, not weeks.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
  },
  {
    title: "Pricing Analysis",
    desc: "Find the optimal price point with Van Westendorp and demand curve tools.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    title: "Diverse Panels",
    desc: "Demographically varied panelists across age, gender, income, and background.",
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
];

const STATS = [
  { value: "< 60s", label: "Average response time" },
  { value: "3", label: "Sector models" },
  { value: "50+", label: "Panelists per session" },
];

export default function LandingPage() {
  const isOnboarded = localStorage.getItem("focustest_onboarded") === "true";
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="landing">
      {/* Floating nav */}
      <nav className="landing-nav">
        <span className="landing-nav-brand">FocusTest</span>
        <div className="landing-nav-links">
          {isOnboarded ? (
            <Link to="/dashboard" className="landing-nav-cta">Dashboard</Link>
          ) : (
            <>
              <Link to="/dashboard">Dashboard</Link>
              <Link to="/onboarding" className="landing-nav-cta">Get Started</Link>
            </>
          )}
          <button
            type="button"
            className="landing-theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
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
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        {/* Decorative glassmorphism blobs */}
        <div className="landing-blob landing-blob-1" />
        <div className="landing-blob landing-blob-2" />
        <div className="landing-blob landing-blob-3" />

        <div className="landing-hero-content">
          <h1 className="landing-headline">
            Know what your{" "}
            <span className="accent-font">customers</span>{" "}
            think before{" "}
            <span className="accent-font">launch</span>
          </h1>
          <p className="landing-subtitle">
            AI-powered synthetic focus groups that give you real consumer
            insight in seconds — not weeks.
          </p>
          <div className="landing-hero-actions">
            {isOnboarded ? (
              <Link to="/dashboard" className="landing-btn-primary">
                Go to Dashboard
              </Link>
            ) : (
              <Link to="/onboarding" className="landing-btn-primary">
                Get Started
              </Link>
            )}
            <Link to="/about" className="landing-btn-secondary">
              Learn more
            </Link>
          </div>
        </div>

        {/* Glass card preview */}
        <div className="landing-glass-preview">
          <div className="landing-glass-card">
            <div className="landing-glass-card-badge positive">Positive</div>
            <div className="landing-glass-card-persona">Sarah, 28 — Tech professional</div>
            <div className="landing-glass-card-text">
              "This solves a real pain point. I'd switch from my current tool
              immediately."
            </div>
          </div>
          <div className="landing-glass-card">
            <div className="landing-glass-card-badge mixed">Mixed</div>
            <div className="landing-glass-card-persona">James, 45 — Financial analyst</div>
            <div className="landing-glass-card-text">
              "Interesting concept but I'd need to see the data privacy
              guarantees first."
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="landing-stats">
        {STATS.map((s) => (
          <div key={s.label} className="landing-stat">
            <div className="landing-stat-value">{s.value}</div>
            <div className="landing-stat-label">{s.label}</div>
          </div>
        ))}
      </section>

      {/* Features */}
      <section className="landing-features">
        <h2 className="landing-features-heading">
          Everything you need to{" "}
          <span className="accent-font">validate</span>
        </h2>
        <div className="landing-features-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-feature-card">
              <div className="landing-feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="landing-bottom-cta">
        <div className="landing-bottom-cta-glass">
          <h2>
            Ready to test your{" "}
            <span className="accent-font">next idea</span>?
          </h2>
          <p>Create your first focus group in under a minute.</p>
          {isOnboarded ? (
            <Link to="/dashboard" className="landing-btn-primary">
              Go to Dashboard
            </Link>
          ) : (
            <Link to="/onboarding" className="landing-btn-primary">
              Get Started
            </Link>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <span>FocusTest</span>
        <span className="landing-footer-sep">·</span>
        <Link to="/about">About</Link>
      </footer>
    </div>
  );
}
