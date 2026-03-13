import { Link } from "react-router-dom";

export default function About() {
  return (
    <div className="about-page">
      <h1>What is FocusTest?</h1>
      <p className="about-lead">
        FocusTest is an AI-powered focus group platform that gives you instant,
        diverse feedback on your product ideas, cutting out the cost and delays
        of traditional research.
      </p>

      <section className="about-section">
        <h2>The Problem</h2>
        <p>
          Traditional focus groups are expensive, often costing tens of thousands
          of dollars. They take weeks to organize, recruit, and run. And even
          then, you're limited to a handful of perspectives from one geographic
          area.
        </p>
        <p style={{ marginTop: "0.5rem" }}>
          For most product teams, that means skipping consumer research entirely
          or relying on gut instinct. FocusTest changes that.
        </p>
      </section>

      <section className="about-section">
        <h2>How It Works</h2>
        <ol className="about-steps">
          <li>
            <strong>Write your pitch.</strong> Describe your product and choose
            a sector (Tech, Financial, or Political). We recommend at least 100
            words to get the best results.
          </li>
          <li>
            <strong>We build your panel.</strong> Our system selects diverse
            participants from a pool of real demographic data, ensuring a mix of
            ages, genders, income levels, and backgrounds.
          </li>
          <li>
            <strong>Get instant feedback.</strong> Each participant responds to
            your pitch in their own voice and style, just like a real focus group.
          </li>
          <li>
            <strong>Analyze the results.</strong> See sentiment breakdowns
            (positive, mixed, negative, neutral) at a glance with visual charts.
          </li>
          <li>
            <strong>Run pricing analysis.</strong> Optionally test price
            sensitivity with Van Westendorp and demand curve tools to find your
            optimal price point.
          </li>
        </ol>
      </section>

      <section className="about-section">
        <h2>What You Get</h2>
        <ul className="about-list">
          <li>
            Feedback from a diverse panel, varied by age, gender, income, and
            life stage
          </li>
          <li>
            Sentiment analysis showing how your pitch lands across different
            demographics
          </li>
          <li>
            Pricing analysis tools to find the right price point before you
            launch
          </li>
          <li>Results in seconds, not weeks</li>
        </ul>
      </section>

      <section className="about-section">
        <h2>Coming Soon</h2>
        <ul className="about-list">
          <li>PDF export for sharing results with your team</li>
          <li>Multimodal media support for richer pitches</li>
          <li>Chat directly with individual focus group members</li>
          <li>Live group conversations with your entire panel</li>
        </ul>
      </section>

      <section className="about-section about-cta">
        <h2>Get Started</h2>
        <p>
          Ready to test your next idea? Create your first pitch and get feedback
          in under a minute.
        </p>
        <Link to="/new" className="btn-new-pitch" style={{ marginTop: "0.75rem", display: "inline-block" }}>
          + New Pitch
        </Link>
      </section>
    </div>
  );
}
