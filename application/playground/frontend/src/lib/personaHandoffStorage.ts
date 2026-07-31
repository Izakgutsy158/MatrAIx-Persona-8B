/** One-shot Persona World → Playground persona cohort handoff. */

const STORAGE_KEY = "playground.personaHandoff";

export interface PersonaHandoffPayload {
  pool: string;
  personaIds: string[];
  /** Unix ms — ignore stale handoffs. */
  ts: number;
}

const MAX_AGE_MS = 60 * 60 * 1000;

export function writePersonaHandoff(input: {
  pool: string;
  personaIds: string[];
}): void {
  const personaIds = [...new Set(input.personaIds.map((id) => id.trim()).filter(Boolean))];
  if (personaIds.length === 0) return;
  const payload: PersonaHandoffPayload = {
    pool: input.pool.trim(),
    personaIds,
    ts: Date.now(),
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* ignore quota / private mode */
  }
}

export function peekPersonaHandoff(): PersonaHandoffPayload | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersonaHandoffPayload;
    if (!parsed || !Array.isArray(parsed.personaIds) || parsed.personaIds.length === 0) {
      return null;
    }
    if (typeof parsed.ts === "number" && Date.now() - parsed.ts > MAX_AGE_MS) {
      clearPersonaHandoff();
      return null;
    }
    return {
      pool: String(parsed.pool || "").trim(),
      personaIds: parsed.personaIds.map((id) => String(id).trim()).filter(Boolean),
      ts: typeof parsed.ts === "number" ? parsed.ts : Date.now(),
    };
  } catch {
    return null;
  }
}

export function clearPersonaHandoff(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Read and clear in one step. */
export function takePersonaHandoff(): PersonaHandoffPayload | null {
  const payload = peekPersonaHandoff();
  if (payload) clearPersonaHandoff();
  return payload;
}
