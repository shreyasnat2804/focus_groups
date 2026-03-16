import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LandingPage from "./LandingPage";

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>
  );
}

describe("LandingPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders the hero headline with mixed fonts", () => {
    renderLanding();
    expect(screen.getByText(/customers/i)).toBeInTheDocument();
    expect(screen.getByText(/launch/i)).toBeInTheDocument();
  });

  it("renders CTA buttons linking to onboarding", () => {
    renderLanding();
    const ctas = screen.getAllByRole("link", { name: /get started/i });
    expect(ctas.length).toBeGreaterThanOrEqual(2);
    ctas.forEach((cta) => {
      expect(cta).toHaveAttribute("href", "/onboarding");
    });
  });

  it("renders feature cards", () => {
    renderLanding();
    expect(screen.getByText(/instant feedback/i)).toBeInTheDocument();
    expect(screen.getByText(/pricing analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/diverse panels/i)).toBeInTheDocument();
  });

  it("renders the secondary CTA for existing users", () => {
    renderLanding();
    const link = screen.getByRole("link", { name: /dashboard/i });
    expect(link).toHaveAttribute("href", "/dashboard");
  });

  it("has glassmorphism hero section", () => {
    renderLanding();
    const hero = document.querySelector(".landing-hero");
    expect(hero).toBeInTheDocument();
  });

  it("uses accent font class for emphasized words", () => {
    renderLanding();
    const accents = document.querySelectorAll(".accent-font");
    expect(accents.length).toBeGreaterThanOrEqual(2);
  });

  it("redirects onboarded users to /dashboard", () => {
    localStorage.setItem("focustest_onboarded", "true");
    renderLanding();
    // Hero should not render since we redirect
    expect(document.querySelector(".landing-hero")).not.toBeInTheDocument();
  });

  it("shows landing page for new users", () => {
    renderLanding();
    expect(document.querySelector(".landing-hero")).toBeInTheDocument();
  });
});
