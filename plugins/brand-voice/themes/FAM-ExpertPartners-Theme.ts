/**
 * ==========================================================================
 * FREE AGENT MOVEMENT – BRAND THEME
 * Version: 3.1 (Visual Identity System v3.1, 2026-06-13)
 *
 * The complete, reusable theme for the Free Agent Movement (movement brand)
 * visual identity. v3.1 decoupled FAM from Expert Partners: FAM is now its
 * own accent-less system so it can layer over each member's personal brand.
 *
 * What changed from v2.0:
 *   1. The Brand Blue (#2757CF) accent is RETIRED. FAM uses NO color accent.
 *      Emphasis comes from Black, Dark Gray, contrast, and typography.
 *   2. Body/label fonts changed from Overpass + Poppins to Neue Swiss.
 *      PT Serif stays for headlines; IBM Plex Mono added for technical detail.
 *   3. Warm Bone (#F7F4EF) added for subtle card/section warmth.
 *
 * Expert Partners (the company brand) keeps its own corporate identity and is
 * NOT defined here. Warmth in FAM lives only in photography, never in the UI.
 * ==========================================================================
 */

export const FAMTheme = {
  name: "Free Agent Movement – Brand Theme",
  version: "3.1",

  // ==========================================================================
  // BRAND COLORS — no accent. Black/White/Warm Bone + neutral grays only.
  // ==========================================================================
  colors: {
    primary: {
      black: "#000000",      // HSL: 0 0% 0%   - text, dark sections, emphasis
      white: "#ffffff",      // HSL: 0 0% 100% - primary background; crisp contrast
      warmBone: "#f7f4ef",   // HSL: 40 33% 95% - subtle warmth on cards/boxes/select sections
    },
    neutral: {
      lightGray: "#f5f5f5",  // HSL: 0 0% 96% - borders, structure
      midGray: "#cccccc",    // HSL: 0 0% 80% - borders, structure
      darkGray: "#333333",   // HSL: 0 0% 20% - secondary text, hover states
    },
    semantic: {
      background: { light: "#ffffff", dark: "#0d0d0d" },
      foreground: { light: "#000000", dark: "#fafafa" },
      card: { light: "#ffffff", dark: "#141414" },
      muted: { light: "#f5f5f5", dark: "#262626" },
      accent: "#000000",     // Accent token maps to BLACK. There is no color accent.
    },
    // No destructive / red token exists in the FAM palette.
  },

  // ==========================================================================
  // BRAND TYPOGRAPHY — PT Serif + Neue Swiss + IBM Plex Mono
  // ==========================================================================
  typography: {
    fonts: {
      headline: {
        family: "'PT Serif', Georgia, serif",
        weight: 400,
        usage: "Hero headers & major page titles",
      },
      subhead: {
        family: "'Neue Swiss', 'Neue Haas Display', system-ui, sans-serif",
        weight: 500,
        usage: "Section titles & mid-size headings (Neue Swiss Medium)",
      },
      body: {
        family: "'Neue Swiss', 'Neue Haas Display', system-ui, sans-serif",
        weight: 300,
        usage: "Paragraph text (Neue Swiss Light/Regular, 300/400)",
      },
      label: {
        family: "'Neue Swiss', 'Neue Haas Display', system-ui, sans-serif",
        weight: 500,
        usage: "Eyebrows, labels, CTAs — ALL CAPS, slight negative letter spacing",
      },
      detail: {
        family: "'IBM Plex Mono', ui-monospace, monospace",
        weight: 400,
        usage: "Numbers, tags, and technical labels only",
      },
    },
    scale: {
      headlineXL: {
        size: "clamp(2.25rem, 5vw, 3.75rem)", // 36px to 60px
        lineHeight: 1.1,
        letterSpacing: "-0.03em",
      },
      headlineLG: {
        size: "clamp(1.75rem, 4vw, 2.5rem)", // 28px to 40px
        lineHeight: 1.1,
        letterSpacing: "-0.03em",
      },
      headlineMD: {
        size: "clamp(1.5rem, 3vw, 2rem)", // 24px to 32px
        lineHeight: 1.15,
        letterSpacing: "-0.02em",
      },
      subhead: {
        size: "clamp(1.125rem, 2vw, 1.875rem)", // 18px to 30px
        lineHeight: 1.35,
        letterSpacing: "-0.01em",
      },
      bodyLG: {
        size: "1.3125rem", // 21px
        lineHeight: 1.6,
        letterSpacing: "-0.01em",
      },
      body: {
        size: "clamp(1rem, 1.5vw, 1.3125rem)", // 16px to 21px
        lineHeight: 1.6,
        letterSpacing: "-0.01em",
      },
      label: {
        size: "1rem", // 16px
        lineHeight: 1.4,
        letterSpacing: "-0.03em",
        textTransform: "uppercase" as const,
      },
    },
  },

  // ==========================================================================
  // SPACING SYSTEM (Locked)
  // ==========================================================================
  spacing: {
    xs: "4px",
    s: "8px",
    m: "16px",
    l: "24px",
    xl: "32px",
  },

  // ==========================================================================
  // SHADOWS — clean, neutral only. No warm/brown tint, no blue glow.
  // ==========================================================================
  shadows: {
    brand: "0px 2px 8px hsla(0, 0%, 0%, 0.06)",
    card: "0px 2px 8px hsla(0, 0%, 0%, 0.06)",
    cardHover: "0px 4px 16px hsla(0, 0%, 0%, 0.12)",
  },

  // ==========================================================================
  // CARD STYLING
  // ==========================================================================
  cards: {
    borderRadius: "8px",
    background: {
      light: "#ffffff",      // White, or Warm Bone for subtle warmth
      warm: "#f7f4ef",       // Warm Bone for cards/boxes/select sections
      dark: "#141414",
    },
    border: {
      light: "1px solid #f5f5f5",   // Light Gray
      mid: "1px solid #cccccc",     // Mid Gray
      dark: "1px solid rgba(255, 255, 255, 0.08)",
    },
    shadow: "0px 2px 8px hsla(0, 0%, 0%, 0.06)",
    rules: [
      "White or Warm Bone background; subtle Light/Mid Gray border, neutral shadow",
      "Card-with-logo headers use a Black bar with the white logo",
      "Always equal height in card grids",
    ],
  },

  // ==========================================================================
  // BUTTON STYLES — Black primary, outlined secondary. No color accent.
  // ==========================================================================
  buttons: {
    primary: {
      background: "#000000",
      text: "#ffffff",
      hoverBackground: "#333333", // Dark Gray
      borderRadius: "4px",
      padding: "12px 24px",
    },
    secondary: {
      background: "transparent",
      border: "1px solid #000000",
      text: "#000000",
      hoverBackground: "#000000",
      hoverText: "#ffffff",
      borderRadius: "4px",
      padding: "12px 24px",
    },
  },

  // ==========================================================================
  // LOGO SYSTEM
  // ==========================================================================
  logo: {
    freeAgentMovement: {
      icon: {
        white: "fam-icon-white.svg",
        black: "fam-icon-black.svg",
        description: "FAM square icon for compact spaces, community badges",
      },
      wordmark: {
        white: "fam-logo-white.svg",
        black: "fam-logo-black.svg",
        description: "Full FAM wordmark for movement hero sections & community pages",
      },
    },
    autoSwitching: {
      rules: [
        "Background lightness 0-45%: use the white logo (dark background)",
        "Background lightness 45-100%: use the black logo (light background)",
      ],
    },
    sizes: {
      xs: { icon: "16px", wordmark: "80px" },
      sm: { icon: "24px", wordmark: "120px" },
      md: { icon: "32px", wordmark: "180px" },
      lg: { icon: "48px", wordmark: "240px" },
      xl: { icon: "64px", wordmark: "280px" },
      hero: { icon: "80-96px", wordmark: "280-360px" },
      sidebar: { icon: "80%", wordmark: "90%" },
      auto: { icon: "100%", wordmark: "100%" },
    },
    scaling: {
      rules: [
        "Maintain aspect ratio always",
        "Never stretch, skew, crop, or add a color accent to the mark",
        "Use object-fit: contain",
        "Max width 280-360px for large spaces",
        "Scale between 16-48px for small icons",
        "Never place full wordmarks in small squares",
      ],
    },
    usage: {
      sidebar: "Place the FAM logo inside a Black square with the white logo, centered with padding",
      heroSections: "Use the full FAM wordmark based on page context",
      smallSpaces: "Use the compact FAM icon",
      darkBackgrounds: "Always use white logo variants",
      lightBackgrounds: "Always use black logo variants",
    },
  },

  // ==========================================================================
  // ICON SYSTEM
  // ==========================================================================
  icons: {
    rules: [
      "White icons on Black or dark sections",
      "Black icons on White or Warm Bone surfaces",
      "Stroke width: 1.5 for Lucide icons",
    ],
    strokeWidth: 1.5,
  },

  // ==========================================================================
  // SIDEBAR LAYOUT — always Black; active nav is Black surface, White text.
  // ==========================================================================
  sidebar: {
    background: "#000000", // Always dark
    foreground: "#d9d9d9",
    width: {
      expanded: "240px",
      collapsed: "56px",
    },
    logo: {
      size: "sidebar",
      containerPadding: "12px",
    },
    accent: "#000000", // No color accent; active/selected uses Black surface + White text
  },

  // ==========================================================================
  // CSS VARIABLES (for index.css) — accent/ring map to neutral, never blue.
  // ==========================================================================
  cssVariables: {
    light: {
      "--background": "0 0% 100%",
      "--foreground": "0 0% 0%",
      "--card": "0 0% 100%",
      "--card-foreground": "0 0% 0%",
      "--primary": "0 0% 0%",
      "--primary-foreground": "0 0% 100%",
      "--secondary": "0 0% 96%",
      "--secondary-foreground": "0 0% 0%",
      "--muted": "0 0% 96%",
      "--muted-foreground": "0 0% 45%",
      "--accent": "0 0% 0%",
      "--accent-foreground": "0 0% 100%",
      "--border": "0 0% 90%",
      "--ring": "0 0% 0%",
      "--radius": "0.5rem",
    },
    dark: {
      "--background": "0 0% 5%",
      "--foreground": "0 0% 98%",
      "--card": "0 0% 8%",
      "--card-foreground": "0 0% 98%",
      "--primary": "0 0% 98%",
      "--primary-foreground": "0 0% 0%",
      "--secondary": "0 0% 15%",
      "--secondary-foreground": "0 0% 95%",
      "--muted": "0 0% 15%",
      "--muted-foreground": "0 0% 55%",
      "--accent": "0 0% 98%",
      "--accent-foreground": "0 0% 0%",
      "--border": "0 0% 20%",
      "--ring": "0 0% 98%",
    },
    sidebar: {
      "--sidebar-background": "0 0% 0%",
      "--sidebar-foreground": "0 0% 85%",
      "--sidebar-primary": "0 0% 98%",
      "--sidebar-primary-foreground": "0 0% 0%",
      "--sidebar-accent": "0 0% 15%",
      "--sidebar-accent-foreground": "0 0% 95%",
      "--sidebar-border": "0 0% 20%",
      "--sidebar-ring": "0 0% 98%",
    },
  },

  // ==========================================================================
  // TAILWIND CONFIG EXTENSIONS
  // ==========================================================================
  tailwindExtensions: {
    fontFamily: {
      sans: ["Neue Swiss", "Neue Haas Display", "system-ui", "sans-serif"],
      display: ["PT Serif", "Georgia", "serif"],
      subhead: ["Neue Swiss", "Neue Haas Display", "system-ui", "sans-serif"],
      body: ["Neue Swiss", "Neue Haas Display", "system-ui", "sans-serif"],
      mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
    },
    colors: {
      brand: {
        black: "#000000",
        white: "#ffffff",
        "warm-bone": "#f7f4ef",
      },
      gray: {
        light: "#f5f5f5",
        mid: "#cccccc",
        dark: "#333333",
      },
    },
    spacing: {
      xs: "4px",
      s: "8px",
      m: "16px",
      l: "24px",
      xl: "32px",
    },
    borderRadius: {
      card: "8px",
      button: "4px",
    },
    boxShadow: {
      brand: "0px 2px 8px hsla(0, 0%, 0%, 0.06)",
      card: "0px 2px 8px hsla(0, 0%, 0%, 0.06)",
      "card-hover": "0px 4px 16px hsla(0, 0%, 0%, 0.12)",
    },
  },
} as const;

// Export type for TypeScript support
export type FAMThemeType = typeof FAMTheme;

export default FAMTheme;

/*
Free Agent Movement visual style

Aesthetic is editorial neutral. Black, White, and a single subtle Warm Bone
(#F7F4EF) only; black dominant; NO accent colors. Typography is PT Serif for
headlines, Neue Swiss for subheads/body/labels, IBM Plex Mono for technical
detail. The energy is structural, architectural, gender-neutral, inspired by
Monocle and The Economist. Bold, modern, stripped-down. Movement-coded, not
person-coded. Universally claimable for any operator in the movement, never
leans feminine or masculine. Strength through restraint. Warmth comes only from
photography, never the UI. Primary logo is the FAM mark. Never reintroduce blue,
brown, sepia, or any color accent. (Visual Identity System v3.1, 2026-06-13.)
*/
