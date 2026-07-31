/**
 * Atmosphere overlays behind the Home globe.
 * Base color comes from `.landing-home-stage` CSS (theme-aware) — this canvas
 * only draws bloom, two concentric rings, and sparse dots on a transparent field.
 */
import { useEffect, useRef } from "react";
import { useIsLightTheme } from "../../hooks/useIsLightTheme";

type Star = { x: number; y: number; size: number; phase: number; speed: number };

interface FieldPalette {
  bloom: [string, string, string, string];
  ring: string;
  star: (alpha: number) => string;
}

const DARK_FIELD: FieldPalette = {
  bloom: [
    "rgba(60, 100, 140, 0.14)",
    "rgba(30, 55, 85, 0.06)",
    "rgba(10, 20, 35, 0.02)",
    "rgba(2, 4, 6, 0)",
  ],
  ring: "rgba(210, 222, 234, 0.2)",
  star: (a) => `rgba(190, 205, 220, ${a})`,
};

const LIGHT_FIELD: FieldPalette = {
  bloom: [
    "rgba(255, 255, 255, 0.5)",
    "rgba(170, 198, 218, 0.12)",
    "rgba(220, 228, 236, 0.04)",
    "rgba(226, 232, 239, 0)",
  ],
  ring: "rgba(18, 24, 32, 0.24)",
  star: (a) => `rgba(18, 24, 32, ${a * 0.5})`,
};

export function CosmicField({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isLight = useIsLightTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    const palette = isLight ? LIGHT_FIELD : DARK_FIELD;

    let raf = 0;
    let w = 0;
    let h = 0;
    let t = 0;
    let stars: Star[] = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, rect.width);
      h = Math.max(1, rect.height);
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(70, Math.max(30, Math.round((w * h) / 28000)));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        size: 0.4 + Math.random() * 1.1,
        phase: Math.random() * Math.PI * 2,
        speed: 0.01 + Math.random() * 0.02,
      }));
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = () => {
      const cx = w * 0.5;
      const cy = h * 0.36;
      const span = Math.min(w, h);

      // Transparent — stage CSS owns the theme background.
      ctx.clearRect(0, 0, w, h);

      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, span * 0.5);
      glow.addColorStop(0, palette.bloom[0]);
      glow.addColorStop(0.35, palette.bloom[1]);
      glow.addColorStop(0.7, palette.bloom[2]);
      glow.addColorStop(1, palette.bloom[3]);
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // Concentric rings temporarily disabled.

      for (const star of stars) {
        const pulse = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(t * star.speed + star.phase));
        const dist = Math.hypot(star.x - cx, star.y - cy) / (span * 0.5);
        const alpha = (0.12 + 0.28 * pulse) * Math.min(1, dist * 0.9 + 0.15);
        ctx.beginPath();
        ctx.fillStyle = palette.star(alpha);
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      }

      t += 1;
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [isLight]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      style={{ background: "transparent" }}
      aria-hidden
    />
  );
}
