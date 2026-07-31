import { PersonaStoreContent } from "./PersonaStoreContent";
import { StudioMeshShell, StudioPageFrame, StudioPageHeader } from "./studio/StudioShell";

export interface PersonaStoreViewProps {
  onOpenInPlayground?: (input: { pool: string; personaIds: string[] }) => void;
}

export function PersonaStoreView({ onOpenInPlayground }: PersonaStoreViewProps) {
  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          eyebrow="MatrAIx · Persona World"
          title="Browse personas"
          subtitle="Click a Matches chip to select that whole group, then Open in Playground."
        />
        <PersonaStoreContent onOpenInPlayground={onOpenInPlayground} autoFocusSearch />
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default PersonaStoreView;
