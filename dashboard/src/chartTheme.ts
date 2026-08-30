/** Single source of truth for chart colors, so every chart reads as one system.
 *  These are the dark-surface steps of a CVD-validated palette -- chosen for the
 *  dark band rather than flipped from the light values. The APIx/CPI pair scores
 *  26.8 deltaE under protanopia and 31.8 in normal vision against the #14171c
 *  card surface (floors: 8 / 15), so the two series stay separable for
 *  colorblind readers. */
export const chart = {
  grid: "#242a33",
  axis: "#6b7481",
  axisLine: "#2e353f",
  surface: "#14171c",
  border: "#262c35",
  ink: "#eaeef4",

  series1: "#3987e5", // APIx
  series2: "#d95926", // CPI

  /** Sequential blue ramp for the heatmap, low -> high. On a dark surface the
   *  low end recedes toward the background and the high end brightens, so cell
   *  luminance reads directly as "more expensive". Single hue, never a rainbow. */
  sequential: [
    "#104281",
    "#184f95",
    "#1c5cab",
    "#256abf",
    "#2a78d6",
    "#3987e5",
    "#5598e7",
    "#6da7ec",
    "#86b6ef",
  ],
} as const;

/** Shared Recharts tooltip styling. */
export const tooltipStyle = {
  background: "#1a1e25",
  border: `1px solid ${chart.border}`,
  borderRadius: 8,
  fontSize: 13,
  boxShadow: "0 8px 28px rgba(0,0,0,0.55)",
  color: chart.ink,
};

export const axisProps = {
  stroke: chart.axisLine,
  tick: { fill: chart.axis, fontSize: 12 },
  tickLine: false,
} as const;

/** Maps a value in [min, max] onto the sequential ramp. */
export function sequentialColor(value: number, min: number, max: number): string {
  const ramp = chart.sequential;
  if (!(max > min)) return ramp[Math.floor(ramp.length / 2)];
  const t = (value - min) / (max - min);
  const idx = Math.min(ramp.length - 1, Math.max(0, Math.round(t * (ramp.length - 1))));
  return ramp[idx];
}

/** Ink that stays legible on a given ramp step -- the bright top of the ramp
 *  needs dark text, the deep end needs light text. */
export function sequentialTextColor(value: number, min: number, max: number): string {
  if (!(max > min)) return "#eaeef4";
  const t = (value - min) / (max - min);
  return t > 0.72 ? "#0a1120" : "#eaeef4";
}
