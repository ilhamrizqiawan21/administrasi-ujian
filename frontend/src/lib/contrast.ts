/** Programmatic WCAG 2.2 contrast ratio utilities for Ocean Ledger tokens. */

function srgbChannel(hexByte: number): number {
  const c = hexByte / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex: string): number {
  const clean = hex.replace(/^#/, "");
  if (clean.length !== 6) {
    throw new Error(`Invalid hex color: ${hex}`);
  }
  const r = srgbChannel(parseInt(clean.slice(0, 2), 16));
  const g = srgbChannel(parseInt(clean.slice(2, 4), 16));
  const b = srgbChannel(parseInt(clean.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(fgHex: string, bgHex: string): number {
  const l1 = relativeLuminance(fgHex);
  const l2 = relativeLuminance(bgHex);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

export const OCEAN_LEDGER_PALETTE = {
  light: {
    canvas: "#E7EFF3",
    surface: "#F1F6F7",
    surfaceRaised: "#F7FAFA",
    nav: "#183544",
    navText: "#E6F1F4",
    primary: "#22677B",
    primaryOn: "#FFFFFF",
    text: "#193440",
    muted: "#4D6570",
    success: "#236B54",
    warning: "#805311",
    destructive: "#A33D43",
  },
  dark: {
    canvas: "#14232F",
    surface: "#1C2D3A",
    surfaceRaised: "#253947",
    nav: "#10232D",
    navText: "#E6F1F4",
    primary: "#7EC9D5",
    primaryOn: "#10232D",
    text: "#E6F1F4",
    muted: "#A5BDC6",
    success: "#8ED2AB",
    warning: "#E7BF78",
    destructive: "#F4A5A9",
  },
} as const;
