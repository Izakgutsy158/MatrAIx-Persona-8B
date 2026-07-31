import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { takePersonaHandoff, peekPersonaHandoff } from "@/lib/personaHandoffStorage";
import { useUrlState } from "@/lib/useUrlState";
import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import type { ConfigOptionsResponse, PlaygroundPersona, TaskPersonaStrategy } from "@/lib/types";
import { PERSONA_BENCH_POOL } from "@/lib/types";

import {
  defaultPersonaSetup,
  hasStoredPersonaSetup,
  readCockpitPersonaSetup,
  sanitizePersonaPool,
  setupFromPersonaStrategy,
  writeCockpitPersonaSetup,
  type CockpitPersonaSetupRecord,
} from "./cockpitPersonaSetupStorage";
import {
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";

function applyPersonaHandoffToSetup(
  handoff: { pool: string; personaIds: string[] },
  base: CockpitPersonaSetupRecord,
): CockpitPersonaSetupRecord {
  const ids = handoff.personaIds.filter(Boolean);
  return {
    ...base,
    selectedPersonaIds: ids,
    personaPool: sanitizePersonaPool(handoff.pool) || base.personaPool || PERSONA_BENCH_POOL,
    samplingMode: ids.length > 1 ? "random" : "single",
    useTaskDefaultStrategy: false,
    taskDefaultStrategyDismissed: true,
  };
}

export function useSetupPersonaSampling(
  options: ConfigOptionsResponse | null,
  taskKind: HarborCockpitTaskKind,
  taskPath: string | null = null,
  isActive = true,
) {
  const fallbackPersonaModel =
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5";
  const normalizedPath = taskPath?.trim() || null;
  const [initial] = useState(() =>
    readCockpitPersonaSetup(taskKind, fallbackPersonaModel, normalizedPath),
  );

  const [personaModel, setPersonaModel] = useState<string>(
    initial.personaModel === "anthropic/claude-sonnet-4-6" ? fallbackPersonaModel : initial.personaModel,
  );
  const [samplingMode, setSamplingMode] = useState<PersonaSamplingMode>(initial.samplingMode);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>(initial.selectedPersonaIds);
  const [groupFilters, setGroupFilters] = useState<PersonaDimensionFilters>(initial.groupFilters);
  const [stratifyFields, setStratifyFields] = useState<string[]>(initial.stratifyFields);
  const [sampleSize, setSampleSize] = useState(initial.sampleSize);
  const [sampleSizePerValueGroup, setSampleSizePerValueGroup] = useState(
    initial.sampleSizePerValueGroup,
  );
  const [seed] = useState(42);
  const [parallelTrials, setParallelTrials] = useState(initial.parallelTrials);
  const [personaPool, setPersonaPool] = useState(
    sanitizePersonaPool(initial.personaPool) || PERSONA_BENCH_POOL,
  );
  const [persona, setPersona] = useState<PlaygroundPersona | null>(null);
  const [taskPersonaStrategy, setTaskPersonaStrategy] = useState<TaskPersonaStrategy | null>(null);
  const [useTaskDefaultStrategy, setUseTaskDefaultStrategyState] = useState(
    initial.useTaskDefaultStrategy,
  );
  const [taskDefaultStrategyDismissed, setTaskDefaultStrategyDismissed] = useState(
    initial.taskDefaultStrategyDismissed === true,
  );
  const hydratedPathRef = useRef<string | null>(null);
  const skipNextPersistRef = useRef(false);
  const handoffAppliedRef = useRef(false);
  const { state: urlState, setState: setUrlState } = useUrlState();

  const strategyQuery = useQuery({
    queryKey: ["task-persona-strategy", normalizedPath],
    queryFn: async () => {
      if (!normalizedPath) return null;
      const response = await api.getTaskPersonaStrategy(normalizedPath);
      return response.personaStrategy ?? null;
    },
    enabled: Boolean(normalizedPath),
    staleTime: 60_000,
  });

  const applySetupRecord = useCallback((record: CockpitPersonaSetupRecord) => {
    skipNextPersistRef.current = true;
    setSamplingMode(record.samplingMode);
    setSelectedPersonaIds(record.selectedPersonaIds);
    setGroupFilters(record.groupFilters);
    setStratifyFields(record.stratifyFields);
    setSampleSize(record.sampleSize);
    setSampleSizePerValueGroup(record.sampleSizePerValueGroup);
    setPersonaModel(record.personaModel);
    setParallelTrials(record.parallelTrials);
    setPersonaPool(sanitizePersonaPool(record.personaPool));
    setUseTaskDefaultStrategyState(record.useTaskDefaultStrategy);
    setTaskDefaultStrategyDismissed(record.taskDefaultStrategyDismissed === true);
  }, []);

  const resetToTaskStrategy = useCallback(() => {
    const strategy = strategyQuery.data ?? taskPersonaStrategy;
    const applied = setupFromPersonaStrategy(strategy, fallbackPersonaModel, {
      ...defaultPersonaSetup(fallbackPersonaModel),
      personaModel,
      parallelTrials,
    });
    applySetupRecord(applied);
    setTaskPersonaStrategy(strategy);
  }, [
    applySetupRecord,
    fallbackPersonaModel,
    parallelTrials,
    personaModel,
    strategyQuery.data,
    taskPersonaStrategy,
  ]);

  const setUseTaskDefaultStrategy = useCallback(
    (next: boolean) => {
      if (next) {
        resetToTaskStrategy();
        return;
      }
      // Explicit operator opt-out — do not confuse with pre-hydrate false.
      setTaskDefaultStrategyDismissed(true);
      setUseTaskDefaultStrategyState(false);
      // Custom stratified UI expects an editable per-cell; invent 1 only after unlock.
      setSampleSizePerValueGroup((prev) => (prev == null ? 1 : prev));
    },
    [resetToTaskStrategy],
  );

  useEffect(() => {
    setTaskPersonaStrategy(strategyQuery.data ?? null);
  }, [strategyQuery.data]);

  useEffect(() => {
    const path = normalizedPath;
    if (!path) {
      hydratedPathRef.current = null;
      return;
    }
    if (hydratedPathRef.current === path) return;

    // Wait for strategy fetch so default-on can re-apply persona_strategy.json.
    if (strategyQuery.isFetching || strategyQuery.isLoading) return;

    const stored = readCockpitPersonaSetup(taskKind, fallbackPersonaModel, path);
    const strategy = strategyQuery.data;
    const dismissed = stored.taskDefaultStrategyDismissed === true;

    const hasTaskSpecificStore = hasStoredPersonaSetup(path);
    const effectiveModel = hasTaskSpecificStore ? stored.personaModel : fallbackPersonaModel;

    let applied: CockpitPersonaSetupRecord;
    if (strategy && !dismissed) {
      applied = setupFromPersonaStrategy(strategy, fallbackPersonaModel, {
        ...defaultPersonaSetup(fallbackPersonaModel),
        personaModel: effectiveModel,
        parallelTrials: stored.parallelTrials,
      });
      // Keep last cohort selection across remount/navigation. Strategy apply
      // clears preview ids intentionally for explicit "Task default" toggles,
      // but hydrate must not wipe a selection the operator already made.
      if (stored.selectedPersonaIds.length > 0) {
        applied.selectedPersonaIds = stored.selectedPersonaIds;
      }
    } else if (hasTaskSpecificStore) {
      applied = {
        ...stored,
        useTaskDefaultStrategy: Boolean(strategy) && stored.useTaskDefaultStrategy,
        taskDefaultStrategyDismissed: dismissed,
      };
    } else {
      applied = setupFromPersonaStrategy(strategy, fallbackPersonaModel, {
        ...defaultPersonaSetup(fallbackPersonaModel),
        personaModel: effectiveModel,
        parallelTrials: stored.parallelTrials,
      });
      if (stored.selectedPersonaIds.length > 0) {
        applied.selectedPersonaIds = stored.selectedPersonaIds;
      }
    }

    const handoff = isActive ? peekPersonaHandoff() : null;
    if (handoff && handoff.personaIds.length > 0) {
      applied = applyPersonaHandoffToSetup(handoff, applied);
      takePersonaHandoff();
      handoffAppliedRef.current = true;
      if (urlState.pgPersonaHandoff) {
        setUrlState({ pgPersonaHandoff: null });
      }
    }

    applySetupRecord(applied);
    hydratedPathRef.current = path;
  }, [
    applySetupRecord,
    fallbackPersonaModel,
    isActive,
    normalizedPath,
    setUrlState,
    strategyQuery.data,
    strategyQuery.isFetching,
    strategyQuery.isLoading,
    taskKind,
    urlState.pgPersonaHandoff,
  ]);

  // Handoff while already on a hydrated task (Persona World → Playground).
  useEffect(() => {
    if (urlState.pgPersonaHandoff === "1") {
      handoffAppliedRef.current = false;
    }
  }, [urlState.pgPersonaHandoff]);

  useEffect(() => {
    if (!isActive) return;
    if (handoffAppliedRef.current) return;
    if (!normalizedPath || hydratedPathRef.current !== normalizedPath) return;
    if (urlState.pgPersonaHandoff !== "1" && !peekPersonaHandoff()) return;

    const handoff = takePersonaHandoff();
    if (!handoff?.personaIds.length) {
      if (urlState.pgPersonaHandoff) setUrlState({ pgPersonaHandoff: null });
      return;
    }
    handoffAppliedRef.current = true;
    const base = readCockpitPersonaSetup(taskKind, fallbackPersonaModel, normalizedPath);
    applySetupRecord(applyPersonaHandoffToSetup(handoff, base));
    setUrlState({ pgPersonaHandoff: null });
  }, [
    applySetupRecord,
    fallbackPersonaModel,
    isActive,
    normalizedPath,
    setUrlState,
    taskKind,
    urlState.pgPersonaHandoff,
  ]);

  useEffect(() => {
    // Do not persist the pre-hydrate default (useTaskDefaultStrategy=false) —
    // that used to lock Task default strategy Off in localStorage forever.
    if (!normalizedPath || hydratedPathRef.current !== normalizedPath) {
      return;
    }
    if (skipNextPersistRef.current) {
      skipNextPersistRef.current = false;
      return;
    }
    writeCockpitPersonaSetup(
      taskKind,
      {
        selectedPersonaIds,
        samplingMode,
        groupFilters,
        stratifyFields,
        sampleSize,
        sampleSizePerValueGroup,
        parallelTrials,
        personaModel,
        personaPool,
        useTaskDefaultStrategy,
        taskDefaultStrategyDismissed,
      },
      normalizedPath,
    );
  }, [
    taskKind,
    normalizedPath,
    selectedPersonaIds,
    samplingMode,
    groupFilters,
    stratifyFields,
    sampleSize,
    sampleSizePerValueGroup,
    parallelTrials,
    personaModel,
    personaPool,
    useTaskDefaultStrategy,
    taskDefaultStrategyDismissed,
  ]);

  useEffect(() => {
    const id = selectedPersonaIds[0];
    if (!id) {
      setPersona(null);
      return;
    }
    setPersona({
      id,
      name: `persona-${id}`,
      source: "matraix-persona-dev-sample",
    });
  }, [selectedPersonaIds]);

  const isBatchRun = samplingMode !== "single" || selectedPersonaIds.length > 1;

  const personaModelKnob = options?.knobs.find((k) => k.key === "personaModel");
  const personaModelOptions =
    personaModelKnob?.options.map((o) => ({
      value: o.value,
      label: o.label,
    })) ?? [{ value: personaModel, label: personaModel }];

  const togglePersona = useCallback(
    (personaId: string) => {
      if (samplingMode === "single") {
        setSelectedPersonaIds((prev) => (prev.includes(personaId) ? [] : [personaId]));
        return;
      }
      setSelectedPersonaIds((prev) =>
        prev.includes(personaId) ? prev.filter((id) => id !== personaId) : [...prev, personaId],
      );
    },
    [samplingMode],
  );

  const hasTaskStrategy = Boolean(taskPersonaStrategy);

  return {
    persona,
    personaModel,
    setPersonaModel,
    personaModelOptions,
    samplingMode,
    setSamplingMode,
    selectedPersonaIds,
    setSelectedPersonaIds,
    togglePersona,
    groupFilters,
    setGroupFilters,
    stratifyFields,
    setStratifyFields,
    sampleSize,
    setSampleSize,
    sampleSizePerValueGroup,
    setSampleSizePerValueGroup,
    seed,
    parallelTrials,
    setParallelTrials,
    personaPool,
    setPersonaPool,
    isBatchRun,
    hasTaskStrategy,
    taskPersonaStrategy,
    useTaskDefaultStrategy: hasTaskStrategy && useTaskDefaultStrategy,
    setUseTaskDefaultStrategy,
  };
}
