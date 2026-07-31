/**
 * Reactive "is light theme" flag for canvas/WebGL components that cannot use
 * CSS variables. Watches the `light` class on <html> (toggled by useTheme).
 */
import { useEffect, useState } from "react";

export function useIsLightTheme(): boolean {
  const [light, setLight] = useState(() =>
    document.documentElement.classList.contains("light"),
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setLight(document.documentElement.classList.contains("light"));
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  return light;
}
