/**
 * Parse sentiment label from the first word/line of a response.
 * Returns { sentiment, text } where text has the label stripped.
 */
const VALID_SENTIMENTS = new Set(["POSITIVE", "NEGATIVE", "MIXED", "NEUTRAL"]);

export function parseSentiment(responseText) {
  if (!responseText) return { sentiment: null, text: "" };

  const trimmed = responseText.trim();
  const firstLine = trimmed.split("\n")[0].trim();
  const firstWord = firstLine.split(/\s+/)[0].toUpperCase();

  if (VALID_SENTIMENTS.has(firstWord)) {
    // Strip the sentiment label from the displayed text
    const rest = trimmed.slice(firstWord.length).trim();
    // Also strip a leading newline if the label was on its own line
    return { sentiment: firstWord, text: rest };
  }

  return { sentiment: null, text: trimmed };
}

export function sentimentColor(sentiment) {
  switch (sentiment) {
    case "POSITIVE": return "#2b8a3e";
    case "NEGATIVE": return "#e03131";
    case "MIXED": return "#e8590c";
    case "NEUTRAL": return "#868e96";
    default: return "#868e96";
  }
}

export function sentimentDot(sentiment) {
  return sentimentColor(sentiment);
}

export function sentimentClass(sentiment) {
  switch (sentiment) {
    case "POSITIVE": return "positive";
    case "NEGATIVE": return "negative";
    case "MIXED": return "mixed";
    case "NEUTRAL": return "neutral";
    default: return "neutral";
  }
}

/**
 * Parse product name from the question field.
 * Convention: "Product: Name\n\nDescription..."
 * Falls back to first 50 chars of question.
 */
export function parseProductName(question) {
  if (!question) return "Untitled";
  const match = question.match(/^Product:\s*(.+)/);
  if (match) return match[1].trim();
  // Fallback: use first line, truncated
  const firstLine = question.split("\n")[0];
  return firstLine.length > 50 ? firstLine.slice(0, 50) + "..." : firstLine;
}

/**
 * Parse product description from the question field.
 */
export function parseProductDescription(question) {
  if (!question) return "";
  const match = question.match(/^Product:\s*.+\n\n([\s\S]*)/);
  if (match) return match[1].trim();
  return question;
}

/**
 * Aggregate sentiments from an array of responses.
 * Returns { positive, negative, mixed, neutral, total }
 */
export function aggregateSentiments(responses) {
  const counts = { positive: 0, negative: 0, mixed: 0, neutral: 0 };
  for (const r of responses) {
    const { sentiment } = parseSentiment(r.response_text);
    if (sentiment === "POSITIVE") counts.positive++;
    else if (sentiment === "NEGATIVE") counts.negative++;
    else if (sentiment === "MIXED") counts.mixed++;
    else counts.neutral++;
  }
  return { ...counts, total: responses.length };
}
