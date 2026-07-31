import type { PersonaMatchedAttribute, PersonaPoolCatalog, PersonaPoolPersonaCard } from "@/lib/types";

export interface PersonaSearchHit {
  dimensionId: string;
  label: string;
  value: string;
  kind: "attribute" | "substring";
}

/** Minimum characters before we run substring hit attribution (short tokens are too noisy/expensive). */
export const MIN_HIT_QUERY_LENGTH = 3;

let cachedDimIdsKey = "";
let cachedDimIdSet: Set<string> = new Set();

export function catalogDimIdSet(catalog: PersonaPoolCatalog | null | undefined): Set<string> {
  const groups = catalog?.dimensionCategories?.devProfile?.groups ?? [];
  // Cheap cache key: group count + first/last ids.
  const key = `${groups.length}:${groups[0]?.id ?? ""}:${groups[groups.length - 1]?.id ?? ""}:${catalog?.pool ?? ""}`;
  if (key === cachedDimIdsKey && cachedDimIdSet.size > 0) return cachedDimIdSet;
  const ids = new Set<string>();
  for (const group of groups) {
    for (const dim of group.dimensions ?? []) ids.add(dim.id.toLowerCase());
    for (const sub of group.subgroups ?? []) {
      for (const dim of sub.dimensions ?? []) ids.add(dim.id.toLowerCase());
    }
  }
  cachedDimIdsKey = key;
  cachedDimIdSet = ids;
  return ids;
}

export function personaSearchHaystack(persona: PersonaPoolPersonaCard): string {
  if (persona.searchText?.trim()) {
    return persona.searchText.toLowerCase();
  }
  const parts = [
    persona.personaId,
    persona.name ?? "",
    persona.source ?? "",
    ...Object.entries(persona.dimensions).flatMap(([key, value]) => [key, value]),
  ];
  return parts.join(" ").toLowerCase();
}

/** Whole-token match: ``reading`` hits values, not ``proofreading`` / ``lstyle_reading_freq``. */
export function textMatchesQuery(text: string, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = text.toLowerCase();
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Underscore counts as a word char so dimension ids don't false-hit on embedded tokens.
  return new RegExp(`(?:^|[^a-z0-9_])${escaped}(?:[^a-z0-9_]|$)`, "i").test(hay);
}

export function personaMatchesQuery(persona: PersonaPoolPersonaCard, query: string): boolean {
  return textMatchesQuery(personaSearchHaystack(persona), query);
}

export function personaHasDimensionValue(
  persona: PersonaPoolPersonaCard,
  dimId: string,
  value: string,
): boolean {
  const cardValue = persona.dimensions[dimId];
  if (cardValue && cardValue === value) return true;
  const hay = personaSearchHaystack(persona);
  return hay.includes(`${dimId.toLowerCase()} ${value.toLowerCase()}`);
}

/**
 * Locate which attribute values contain ``query``.
 * Uses card dims + Treiver suggestions first; only then a cheap walk-back over searchText
 * at query match positions (never scans all 1290 dims × full text).
 */
export function findPersonaSearchHits(
  persona: PersonaPoolPersonaCard,
  query: string,
  catalog: PersonaPoolCatalog | null | undefined,
  suggestions: PersonaMatchedAttribute[] = [],
  dimIds?: Set<string>,
): PersonaSearchHit[] {
  const q = query.trim().toLowerCase();
  const hits: PersonaSearchHit[] = [];
  const seen = new Set<string>();

  const push = (hit: PersonaSearchHit) => {
    const key = `${hit.dimensionId}:${hit.value}`.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    hits.push(hit);
  };

  for (const attr of suggestions) {
    if (personaHasDimensionValue(persona, attr.dimensionId, attr.value)) {
      push({
        dimensionId: attr.dimensionId,
        label: attr.label || attr.dimensionId.replace(/_/g, " "),
        value: attr.value,
        kind: "attribute",
      });
    }
  }

  if (!q) return hits;

  for (const [dimId, value] of Object.entries(persona.dimensions ?? {})) {
    if (textMatchesQuery(value, q) || textMatchesQuery(dimId, q)) {
      push({
        dimensionId: dimId,
        label: dimId.replace(/_/g, " "),
        value,
        kind: "substring",
      });
    }
  }

  if (q.length < MIN_HIT_QUERY_LENGTH) return hits;

  const searchText = persona.searchText?.trim();
  if (!searchText) {
    if (hits.length === 0 && personaMatchesQuery(persona, q)) {
      push({
        dimensionId: "profile",
        label: "profile",
        value: query.trim(),
        kind: "substring",
      });
    }
    return hits;
  }

  const idSet = dimIds ?? catalogDimIdSet(catalog);
  if (idSet.size === 0) {
    if (hits.length === 0 && personaMatchesQuery(persona, q)) {
      push({
        dimensionId: "profile",
        label: "profile",
        value: query.trim(),
        kind: "substring",
      });
    }
    return hits;
  }

  const lower = searchText.toLowerCase();
  let from = 0;
  let matchCount = 0;
  while (from < lower.length && matchCount < 8 && hits.length < 6) {
    const at = lower.indexOf(q, from);
    if (at < 0) break;
    matchCount += 1;
    from = at + Math.max(q.length, 1);

    // Skip matches that sit inside a larger alphanumeric/underscore token
    // (e.g. query "reading" inside "proofreading" or "lstyle_reading_freq").
    const prev = at === 0 ? "" : lower[at - 1];
    const next = lower[at + q.length] ?? "";
    const boundaryOk =
      (at === 0 || /[^a-z0-9_]/.test(prev)) &&
      (at + q.length >= lower.length || /[^a-z0-9_]/.test(next));
    if (!boundaryOk) continue;

    const before = lower.slice(0, at).trimEnd();
    if (!before) continue;
    const tokens = before.split(/\s+/);
    let dimId: string | null = null;
    for (let i = tokens.length - 1; i >= Math.max(0, tokens.length - 12); i--) {
      const tok = tokens[i];
      if (idSet.has(tok)) {
        dimId = tok;
        break;
      }
    }
    if (!dimId) continue;

    const dimAt = before.toLowerCase().lastIndexOf(dimId);
    const valueStart = dimAt + dimId.length;
    const after = searchText.slice(valueStart, valueStart + 160);
    const afterTokens = after.trim().split(/\s+/);
    const valueParts: string[] = [];
    for (const tok of afterTokens) {
      if (idSet.has(tok.toLowerCase())) break;
      valueParts.push(tok);
      if (valueParts.join(" ").length > 80) break;
    }
    const value = valueParts.join(" ").trim();
    if (!value || !textMatchesQuery(value, q)) continue;
    push({
      dimensionId: dimId,
      label: dimId.replace(/_/g, " "),
      value,
      kind: "substring",
    });
  }

  if (hits.length === 0 && personaMatchesQuery(persona, q)) {
    push({
      dimensionId: "profile",
      label: "profile",
      value: query.trim(),
      kind: "substring",
    });
  }

  return hits;
}

export function summarizeHitsAcrossPersonas(
  personas: PersonaPoolPersonaCard[],
  query: string,
  catalog: PersonaPoolCatalog | null | undefined,
  suggestions: PersonaMatchedAttribute[],
): Array<PersonaSearchHit & { personaCount: number }> {
  const q = query.trim();
  if (q.length > 0 && q.length < MIN_HIT_QUERY_LENGTH && suggestions.length === 0) {
    return [];
  }
  const dimIds = catalogDimIdSet(catalog);
  const counts = new Map<string, PersonaSearchHit & { personaCount: number }>();
  for (const persona of personas) {
    const hits = findPersonaSearchHits(persona, q, catalog, suggestions, dimIds);
    const seenLocal = new Set<string>();
    for (const hit of hits) {
      const key = `${hit.dimensionId}:${hit.value}`.toLowerCase();
      if (seenLocal.has(key)) continue;
      seenLocal.add(key);
      const prev = counts.get(key);
      if (prev) prev.personaCount += 1;
      else counts.set(key, { ...hit, personaCount: 1 });
    }
  }
  return [...counts.values()].sort(
    (a, b) => b.personaCount - a.personaCount || a.label.localeCompare(b.label),
  );
}
