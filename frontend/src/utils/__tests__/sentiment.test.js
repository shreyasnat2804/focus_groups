import { describe, it, expect } from "vitest";
import {
  parseSentiment,
  sentimentColor,
  sentimentDot,
  parseProductName,
  parseProductDescription,
  aggregateSentiments,
} from "../sentiment";

describe("parseSentiment", () => {
  it("extracts POSITIVE and strips label", () => {
    const result = parseSentiment("POSITIVE\nI love this product!");
    expect(result.sentiment).toBe("POSITIVE");
    expect(result.text).toBe("I love this product!");
  });

  it("extracts NEGATIVE and strips label", () => {
    const result = parseSentiment("NEGATIVE\nThis is overpriced.");
    expect(result.sentiment).toBe("NEGATIVE");
    expect(result.text).toBe("This is overpriced.");
  });

  it("extracts MIXED and strips label", () => {
    const result = parseSentiment("MIXED\nSome good, some bad.");
    expect(result.sentiment).toBe("MIXED");
    expect(result.text).toBe("Some good, some bad.");
  });

  it("extracts NEUTRAL and strips label", () => {
    const result = parseSentiment("NEUTRAL\nI have no strong opinion.");
    expect(result.sentiment).toBe("NEUTRAL");
    expect(result.text).toBe("I have no strong opinion.");
  });

  it("is case-insensitive for the first word", () => {
    const result = parseSentiment("positive\nGreat stuff!");
    expect(result.sentiment).toBe("POSITIVE");
  });

  it("returns null sentiment for missing label", () => {
    const result = parseSentiment("Just a regular response");
    expect(result.sentiment).toBeNull();
    expect(result.text).toBe("Just a regular response");
  });

  it("returns null sentiment and empty text for empty string", () => {
    const result = parseSentiment("");
    expect(result.sentiment).toBeNull();
    expect(result.text).toBe("");
  });

  it("returns null sentiment and empty text for null/undefined", () => {
    expect(parseSentiment(null)).toEqual({ sentiment: null, text: "" });
    expect(parseSentiment(undefined)).toEqual({ sentiment: null, text: "" });
  });

  it("handles label inline with text (no newline)", () => {
    const result = parseSentiment("POSITIVE I really like it");
    expect(result.sentiment).toBe("POSITIVE");
    expect(result.text).toBe("I really like it");
  });
});

describe("sentimentColor", () => {
  it("returns green for POSITIVE", () => {
    expect(sentimentColor("POSITIVE")).toBe("#2b8a3e");
  });

  it("returns red for NEGATIVE", () => {
    expect(sentimentColor("NEGATIVE")).toBe("#e03131");
  });

  it("returns orange for MIXED", () => {
    expect(sentimentColor("MIXED")).toBe("#e8590c");
  });

  it("returns gray for NEUTRAL", () => {
    expect(sentimentColor("NEUTRAL")).toBe("#868e96");
  });

  it("returns gray for unknown sentiment", () => {
    expect(sentimentColor("UNKNOWN")).toBe("#868e96");
    expect(sentimentColor(null)).toBe("#868e96");
  });
});

describe("sentimentDot", () => {
  it("is an alias for sentimentColor", () => {
    expect(sentimentDot("POSITIVE")).toBe(sentimentColor("POSITIVE"));
    expect(sentimentDot("NEGATIVE")).toBe(sentimentColor("NEGATIVE"));
  });
});

describe("parseProductName", () => {
  it("extracts name from Product: convention", () => {
    expect(parseProductName("Product: FocusApp\n\nA great app")).toBe("FocusApp");
  });

  it("trims whitespace from product name", () => {
    expect(parseProductName("Product:   My App  ")).toBe("My App");
  });

  it("falls back to first line when no Product: prefix", () => {
    expect(parseProductName("My cool product idea")).toBe("My cool product idea");
  });

  it("truncates long first lines to 50 chars", () => {
    const longLine = "A".repeat(60);
    expect(parseProductName(longLine)).toBe("A".repeat(50) + "...");
  });

  it("returns Untitled for null/undefined", () => {
    expect(parseProductName(null)).toBe("Untitled");
    expect(parseProductName(undefined)).toBe("Untitled");
  });

  it("returns Untitled for empty string", () => {
    expect(parseProductName("")).toBe("Untitled");
  });
});

describe("parseProductDescription", () => {
  it("extracts description after Product: line", () => {
    expect(parseProductDescription("Product: App\n\nThis is the description")).toBe(
      "This is the description"
    );
  });

  it("returns full question when no Product: prefix", () => {
    expect(parseProductDescription("Just a question")).toBe("Just a question");
  });

  it("returns empty string for null/undefined", () => {
    expect(parseProductDescription(null)).toBe("");
    expect(parseProductDescription(undefined)).toBe("");
  });
});

describe("aggregateSentiments", () => {
  it("counts sentiments from responses", () => {
    const responses = [
      { response_text: "POSITIVE\nGreat!" },
      { response_text: "NEGATIVE\nBad!" },
      { response_text: "POSITIVE\nAwesome!" },
      { response_text: "MIXED\nOkay..." },
      { response_text: "No label here" },
    ];

    const result = aggregateSentiments(responses);
    expect(result).toEqual({
      positive: 2,
      negative: 1,
      mixed: 1,
      neutral: 1,
      total: 5,
    });
  });

  it("returns all zeros for empty array", () => {
    const result = aggregateSentiments([]);
    expect(result).toEqual({
      positive: 0,
      negative: 0,
      mixed: 0,
      neutral: 0,
      total: 0,
    });
  });
});
