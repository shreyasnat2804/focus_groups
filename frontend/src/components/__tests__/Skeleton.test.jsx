import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { SkeletonLine, SkeletonCard, PitchGridSkeleton, SessionDetailSkeleton } from "../Skeleton";

describe("SkeletonLine", () => {
  it("renders with default dimensions", () => {
    const { container } = render(<SkeletonLine />);
    const el = container.querySelector(".skeleton-line");
    expect(el).toBeTruthy();
    expect(el.style.width).toBe("100%");
    expect(el.style.height).toBe("1rem");
  });

  it("accepts custom width and height", () => {
    const { container } = render(<SkeletonLine width="50%" height="2rem" />);
    const el = container.querySelector(".skeleton-line");
    expect(el.style.width).toBe("50%");
    expect(el.style.height).toBe("2rem");
  });
});

describe("SkeletonCard", () => {
  it("renders skeleton card structure", () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector(".skeleton-card")).toBeTruthy();
    expect(container.querySelectorAll(".skeleton-line").length).toBeGreaterThanOrEqual(4);
  });
});

describe("PitchGridSkeleton", () => {
  it("renders default 6 skeleton cards", () => {
    const { container } = render(<PitchGridSkeleton />);
    expect(container.querySelectorAll(".skeleton-card").length).toBe(6);
  });

  it("renders custom count", () => {
    const { container } = render(<PitchGridSkeleton count={3} />);
    expect(container.querySelectorAll(".skeleton-card").length).toBe(3);
  });
});

describe("SessionDetailSkeleton", () => {
  it("renders detail skeleton structure", () => {
    const { container } = render(<SessionDetailSkeleton />);
    expect(container.querySelector(".skeleton-detail")).toBeTruthy();
    expect(container.querySelectorAll(".skeleton-response").length).toBe(3);
  });
});
