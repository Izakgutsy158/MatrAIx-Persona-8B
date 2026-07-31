import { useEffect, useState } from "react";

const GAP_PX = 10;
const MIN_CARD_WIDTH = 124;
const MIN_CARD_HEIGHT = 72;

const CHIP_GAP_PX = 8;
const CHIP_WIDTH = 108;
const CHIP_HEIGHT = 46;
const CHIP_MIN_HEIGHT = 44;

/**
 * Cohort display tiers. The roster scales from individual portraits to an
 * aggregate pixel-wall as the population grows, keeping the DOM bounded.
 */
export type BatchGridMode = "cards" | "chips" | "mosaic";

/** > this many people → drop full cards for compact, virtualized chips. */
export const BATCH_CHIPS_THRESHOLD = 60;
/** > this many people → drop per-person DOM for the canvas pixel-wall. */
export const BATCH_MOSAIC_THRESHOLD = 600;

export function resolveBatchGridMode(count: number): BatchGridMode {
  if (count > BATCH_MOSAIC_THRESHOLD) return "mosaic";
  if (count > BATCH_CHIPS_THRESHOLD) return "chips";
  return "cards";
}

export type BatchGridLayout = {
  mode: BatchGridMode;
  cols: number;
  rows: number;
  scroll: boolean;
  rowHeight: number;
  gap: number;
  /** Measured content-box of the stage — mosaic sizes its canvas from this. */
  width: number;
  height: number;
};

function computeCardsLayout(
  count: number,
  width: number,
  height: number,
): Pick<BatchGridLayout, "cols" | "rows" | "scroll" | "rowHeight"> {
  const maxCols = Math.max(
    1,
    Math.min(count, Math.floor((width + GAP_PX) / (MIN_CARD_WIDTH + GAP_PX))),
  );

  let best: { cols: number; rows: number; rowHeight: number; score: number } | null = null;

  for (let cols = 1; cols <= maxCols; cols += 1) {
    const rows = Math.ceil(count / cols);
    const cellW = (width - (cols - 1) * GAP_PX) / cols;
    const rowHeight = (height - (rows - 1) * GAP_PX) / rows;
    if (rowHeight < MIN_CARD_HEIGHT || cellW < MIN_CARD_WIDTH) continue;

    const waste = cols * rows - count;
    const score = rowHeight * cellW - waste * 400;
    if (!best || score > best.score) {
      best = { cols, rows, rowHeight, score };
    }
  }

  if (best) {
    return { cols: best.cols, rows: best.rows, scroll: false, rowHeight: best.rowHeight };
  }

  const cols = Math.max(1, Math.min(maxCols, count > 60 ? maxCols : Math.min(4, maxCols)));
  const rows = Math.ceil(count / cols);
  const contentHeight = rows * MIN_CARD_HEIGHT + (rows - 1) * GAP_PX;
  return {
    cols,
    rows,
    scroll: contentHeight > height + 1,
    rowHeight: MIN_CARD_HEIGHT,
  };
}

/**
 * Compact chips. When the whole cohort fits, rows stretch to fill the stage
 * (like cards). When it overflows, chips take a fixed height and the grid is
 * virtualized so the DOM stays bounded.
 */
function computeChipsLayout(
  count: number,
  width: number,
  height: number,
): Pick<BatchGridLayout, "cols" | "rows" | "scroll" | "rowHeight"> {
  const cols = Math.max(
    1,
    Math.min(count, Math.floor((width + CHIP_GAP_PX) / (CHIP_WIDTH + CHIP_GAP_PX))),
  );
  const rows = Math.ceil(count / cols);
  const contentMin = rows * CHIP_MIN_HEIGHT + (rows - 1) * CHIP_GAP_PX;
  const scroll = contentMin > height + 1;
  return { cols, rows, scroll, rowHeight: CHIP_HEIGHT };
}

export function computeBatchGridLayout(
  count: number,
  width: number,
  height: number,
): BatchGridLayout {
  const mode = resolveBatchGridMode(count);
  const base: BatchGridLayout = {
    mode,
    cols: 1,
    rows: 1,
    scroll: false,
    rowHeight: MIN_CARD_HEIGHT,
    gap: mode === "cards" ? GAP_PX : CHIP_GAP_PX,
    width,
    height,
  };

  if (count <= 0 || width <= 0 || height <= 0) return base;

  if (mode === "mosaic") {
    // Canvas owns its own geometry; the hook only forwards the measured box.
    return { ...base, cols: 0, rows: 0, scroll: false };
  }

  if (mode === "chips") {
    return { ...base, ...computeChipsLayout(count, width, height) };
  }

  return { ...base, ...computeCardsLayout(count, width, height) };
}

export function useBatchGridLayout(count: number) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [layout, setLayout] = useState<BatchGridLayout>(() =>
    computeBatchGridLayout(count, 480, 320),
  );

  useEffect(() => {
    if (!container) return;

    const measure = () => {
      const rect = container.getBoundingClientRect();
      setLayout(computeBatchGridLayout(count, rect.width, rect.height));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [container, count]);

  return { setContainer, container, layout };
}
