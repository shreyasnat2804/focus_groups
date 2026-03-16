import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SentimentBar from "../SentimentBar";

const SENTIMENTS = { positive: 5, mixed: 2, negative: 1, neutral: 2, total: 10 };

describe("SentimentBar", () => {
  it("renders nothing when sentiments is null", () => {
    const { container } = render(<SentimentBar sentiments={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders nothing when total is 0", () => {
    const { container } = render(
      <SentimentBar sentiments={{ positive: 0, mixed: 0, negative: 0, neutral: 0, total: 0 }} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders sentiment segments", () => {
    const { container } = render(<SentimentBar sentiments={SENTIMENTS} />);
    const segments = container.querySelectorAll(".sentiment-segment");
    expect(segments.length).toBe(4);
  });

  it("uses small bar class by default", () => {
    const { container } = render(<SentimentBar sentiments={SENTIMENTS} />);
    expect(container.querySelector(".sentiment-bar")).toBeTruthy();
    expect(container.querySelector(".sentiment-bar-large")).toBeNull();
  });

  it("uses large bar class when size=large", () => {
    const { container } = render(<SentimentBar sentiments={SENTIMENTS} size="large" />);
    expect(container.querySelector(".sentiment-bar-large")).toBeTruthy();
  });

  it("shows percent text when showPercent is true", () => {
    render(<SentimentBar sentiments={SENTIMENTS} showPercent />);
    expect(screen.getByText("50% positive")).toBeTruthy();
  });

  it("does not show percent text by default", () => {
    render(<SentimentBar sentiments={SENTIMENTS} />);
    expect(screen.queryByText(/positive/)).toBeNull();
  });

  it("shows labels when showLabels is true", () => {
    render(<SentimentBar sentiments={SENTIMENTS} showLabels />);
    expect(screen.getByText("5 positive")).toBeTruthy();
    expect(screen.getByText("2 mixed")).toBeTruthy();
    expect(screen.getByText("1 negative")).toBeTruthy();
    expect(screen.getByText("2 neutral")).toBeTruthy();
  });

  it("omits segments and labels for zero counts", () => {
    const partial = { positive: 3, mixed: 0, negative: 0, neutral: 7, total: 10 };
    const { container } = render(<SentimentBar sentiments={partial} showLabels />);
    const segments = container.querySelectorAll(".sentiment-segment");
    expect(segments.length).toBe(2);
    expect(screen.queryByText(/mixed/)).toBeNull();
    expect(screen.queryByText(/negative/)).toBeNull();
  });
});
