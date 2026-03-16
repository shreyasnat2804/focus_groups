import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import EmptyState from "../EmptyState";

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("EmptyState", () => {
  it("renders title", () => {
    renderWithRouter(<EmptyState title="No data" />);
    expect(screen.getByText("No data")).toBeTruthy();
  });

  it("renders description when provided", () => {
    renderWithRouter(<EmptyState title="Empty" description="Nothing here yet." />);
    expect(screen.getByText("Nothing here yet.")).toBeTruthy();
  });

  it("does not render description when omitted", () => {
    const { container } = renderWithRouter(<EmptyState title="Empty" />);
    expect(container.querySelector(".empty-state-desc")).toBeNull();
  });

  it("renders action link when both actionLabel and actionTo are provided", () => {
    renderWithRouter(
      <EmptyState title="Empty" actionLabel="Create" actionTo="/new" />
    );
    const link = screen.getByText("Create");
    expect(link).toBeTruthy();
    expect(link.getAttribute("href")).toBe("/new");
  });

  it("does not render action link when actionLabel is omitted", () => {
    renderWithRouter(<EmptyState title="Empty" actionTo="/new" />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders the SVG icon", () => {
    const { container } = renderWithRouter(<EmptyState title="Empty" />);
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
