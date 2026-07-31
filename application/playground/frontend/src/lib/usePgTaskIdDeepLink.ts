/**
 * Apply a one-shot Task Gallery deep-link (`pgTaskId`) into Playground selection.
 */
import { useEffect, useRef } from "react";

import type { PlaygroundTaskType } from "@/components/cockpit/TaskTypeSwitch";
import { recordRecentTaskSelection } from "@/lib/cockpitTaskRailStorage";
import { useUrlState } from "@/lib/useUrlState";

export function usePgTaskIdDeepLink(
  taskType: PlaygroundTaskType,
  knownTaskIds: readonly string[],
  setSelectedTaskId: (taskId: string) => void,
  isActive = true,
): void {
  const { state: urlState, setState: setUrlState } = useUrlState();
  const appliedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isActive) return;
    const wanted = urlState.pgTaskId?.trim() ?? "";
    if (!wanted) {
      appliedRef.current = null;
      return;
    }
    if (urlState.pgTask && urlState.pgTask !== taskType) return;
    if (appliedRef.current === wanted) return;
    if (!knownTaskIds.includes(wanted)) return;

    appliedRef.current = wanted;
    setSelectedTaskId(wanted);
    recordRecentTaskSelection(taskType, wanted);
    setUrlState({ pgTaskId: null });
  }, [
    isActive,
    knownTaskIds,
    setSelectedTaskId,
    setUrlState,
    taskType,
    urlState.pgTask,
    urlState.pgTaskId,
  ]);
}
