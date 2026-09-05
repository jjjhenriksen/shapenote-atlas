export function resolveKeyContext(score, metadata, enteredKey = "", { parseKey, keyEvidenceFor, allowMetadataFallback = true } = {}) {
  if (typeof parseKey !== "function" || typeof keyEvidenceFor !== "function") {
    throw new TypeError("resolveKeyContext requires parseKey and keyEvidenceFor callbacks");
  }
  const scoreKey = score?.keySignature || "";
  if (parseKey(scoreKey)) return { value: scoreKey, evidence: keyEvidenceFor(score) };
  const metadataKey = metadata?.keySignature || "";
  if (allowMetadataFallback && parseKey(metadataKey)) return { value: metadataKey, evidence: keyEvidenceFor(metadata) };
  if (parseKey(enteredKey)) return { value: enteredKey, evidence: { status: "entered", source: "user-entered source key" } };
  return { value: "", evidence: keyEvidenceFor(score, allowMetadataFallback ? keyEvidenceFor(metadata) : null) };
}
