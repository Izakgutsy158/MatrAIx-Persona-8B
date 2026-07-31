import { TaskGalleryContent } from "./TaskGalleryContent";
import type { PlaygroundTaskType } from "./cockpit/TaskTypeSwitch";
import { StudioMeshShell, StudioPageFrame, StudioPageHeader } from "./studio/StudioShell";

export interface TaskGalleryViewProps {
  onOpenInPlayground: (taskType: PlaygroundTaskType, taskId: string) => void;
}

export function TaskGalleryView({ onOpenInPlayground }: TaskGalleryViewProps) {
  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          eyebrow="MatrAIx · Task Gallery"
          title="Browse tasks"
          subtitle="All survey, chatbot, web, and OS-app tasks — search, filter, then open one in Playground."
        />
        <TaskGalleryContent onOpenInPlayground={onOpenInPlayground} autoFocusSearch />
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default TaskGalleryView;
