import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import About from "../About";

function renderAbout() {
  return render(
    <MemoryRouter>
      <About />
    </MemoryRouter>
  );
}

describe("About", () => {
  it("renders all section headings", () => {
    renderAbout();
    expect(screen.getByText("What is FocusTest?")).toBeInTheDocument();
    expect(screen.getByText("The Problem")).toBeInTheDocument();
    expect(screen.getByText("How It Works")).toBeInTheDocument();
    expect(screen.getByText("What You Get")).toBeInTheDocument();
    expect(screen.getByText("Get Started")).toBeInTheDocument();
  });

  it("renders the new pitch CTA link", () => {
    renderAbout();
    const cta = screen.getByRole("link", { name: "+ New Pitch" });
    expect(cta).toHaveAttribute("href", "/new");
  });
});
