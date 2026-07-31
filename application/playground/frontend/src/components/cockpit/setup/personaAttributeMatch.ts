import type { PersonaMatchedAttribute } from "@/lib/types";

import type { PersonaDimensionFilters } from "./personaSamplingTypes";

/** Debounced NL / token length that is worth sending to Treiver. */
export function shouldMatchAttributes(query: string): boolean {
  return query.trim().length >= 3;
}

export function suggestionKey(attr: PersonaMatchedAttribute): string {
  return `${attr.dimensionId}:${attr.value}`;
}

export function isSuggestionSelected(
  filters: PersonaDimensionFilters,
  attr: PersonaMatchedAttribute,
): boolean {
  return (filters.dimensionFilters[attr.dimensionId] ?? []).includes(attr.value);
}

export function toggleSuggestionInFilters(
  filters: PersonaDimensionFilters,
  attr: PersonaMatchedAttribute,
): PersonaDimensionFilters {
  const current = filters.dimensionFilters[attr.dimensionId] ?? [];
  const nextValues = current.includes(attr.value)
    ? current.filter((item) => item !== attr.value)
    : [...current, attr.value];
  const nextFilters = { ...filters.dimensionFilters };
  if (nextValues.length === 0) delete nextFilters[attr.dimensionId];
  else nextFilters[attr.dimensionId] = nextValues;
  return { ...filters, dimensionFilters: nextFilters };
}

export function applyAllSuggestions(
  filters: PersonaDimensionFilters,
  attrs: PersonaMatchedAttribute[],
): PersonaDimensionFilters {
  let next = filters;
  for (const attr of attrs) {
    if (!isSuggestionSelected(next, attr)) {
      next = toggleSuggestionInFilters(next, attr);
    }
  }
  return next;
}
