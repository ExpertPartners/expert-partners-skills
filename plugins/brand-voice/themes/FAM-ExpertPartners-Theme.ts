/**
 * ==========================================================================
 * FREE AGENT MOVEMENT – EXPERT PARTNERS THEME
 * Version: 2.0
 *
 * A complete, reusable brand theme for both Expert Partners (company brand)
 * and Free Agent Movement (movement brand) visual identity.
 * Includes automatic light/dark logo switching for both brands.
 * ==========================================================================
 */

export const FAMTheme = {
  name: "Free Agent Movement – Expert Partners Theme",
  version: "2.0",

  // ==========================================================================
  // BRAND COLORS
  // ==========================================================================
  colors: {
    primary: {
      black: "#000000",      // HSL: 0 0% 0%
      white: "#ffffff",      // HSL: 0 0% 100%
      blue: "#2757CF",       // HSL: 220 68% 48% - Highlight/Accent
      blueHover: "#3A6BFF",  // HSL: 224 100% 61%
    },
    neutral: {
      lightGray: "#f5f5f5",  // HSL: 0 0% 96%
      midGray: "#cccccc",    // HSL: 0 0% 80%
      darkGray: "#333333",   // HSL: 0 0% 20%
    },
    semantic: {
      background: { light: "#ffffff", dark: "#0d0d0d" },
      foreground: { light: "#000000", dark: "#fafafa" },
      card: { light: "#ffffff", dark: "#141414" },
      muted: { light: "#f5f5f5", dark: "#262626" },
      accent: "#2757CF",
    },
  },

  // ==========================================================================
  // BRAND TYPOGRAPHY
  // ==========================================================================
  typography: {
    fonts: {
      headline: {
        family: "'PT Serif', Georgia, serif",
        weight: 400,
        usage: "Hero headers & major page titles",
      },
      subhead: {
        family: "'Overpass', system-ui, sans-serif",
        weight: 400,
        usage: "Section titles & mid-size headings",
      },
      body: {
        family: "'Poppins', sans-serif",
        weight: 300,
        usage: "Paragraph text, clean and readable",
      },
      label: {
        family: "'Poppins', sans-serif",
        weight: 500,
        usage: "Eyebrows, labels, CTAs (all caps for labels)",
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
        lineHeight: 1.15,
        letterSpacing: "-0.03em",
      },
      headlineMD: {
        size: "clamp(1.5rem, 3vw, 2rem)", // 24px to 32px
        lineHeight: 1.2,
        letterSpacing: "-0.02em",
      },
      subhead: {
        size: "clamp(1.125rem, 2vw, 1.875rem)", // 18px to 30px
        lineHeight: 1.3,
        letterSpacing: "-0.02em",
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
  // SHADOWS
  // ==========================================================================
  shadows: {
    brand: "0px 2px 8px rgba(0, 0, 0, 0.08)",
    card: "0px 2px 8px rgba(0, 0, 0, 0.08)",
    cardHover: "0px 4px 16px rgba(0, 0, 0, 0.12)",
    glow: "0 0 20px hsla(220, 68%, 48%, 0.15)",
  },

  // ==========================================================================
  // CARD STYLING
  // ==========================================================================
  cards: {
    borderRadius: "8px",
    border: {
      light: "1px solid rgba(0, 0, 0, 0.06)",
      dark: "1px solid rgba(255, 255, 255, 0.08)",
    },
    shadow: "0px 2px 8px rgba(0, 0, 0, 0.08)",
    rules: [
      "Always equal height in card grids",
      "Use brand shadow consistently",
      "Support auto logo switching in card headers",
    ],
  },

  // ==========================================================================
  // BUTTON STYLES
  // ==========================================================================
  buttons: {
    primary: {
      background: "#2757CF",
      text: "#ffffff",
      hoverBackground: "#3A6BFF",
      borderRadius: "8px",
      padding: "12px 24px",
    },
    secondary: {
      background: "transparent",
      border: "1px solid #2757CF",
      text: "#2757CF",
      hoverBackground: "rgba(39, 87, 207, 0.1)",
      borderRadius: "8px",
      padding: "12px 24px",
    },
  },

  // ==========================================================================
  // LOGO SYSTEM (Dual Brand Support)
  // ==========================================================================
  logo: {
    // Expert Partners (Company Brand)
    expertPartners: {
      icon: {
        white: "ep-logo-white.svg",
        black: "ep-logo-black.svg",
        description: "Compact EP logo for tight/square spaces",
      },
      wordmark: {
        white: "expert-partners-logo-white.svg",
        black: "expert-partners-logo-black.svg",
        description: "Full Expert Partners wordmark for hero sections",
      },
    },
    // Free Agent Movement (Movement Brand)
    freeAgentMovement: {
      icon: {
        white: "fam-icon-white.svg",
        black: "fam-icon-black.svg",
        description: "FAM square icon for compact spaces",
      },
      wordmark: {
        white: "fam-logo-white.svg",
        black: "fam-logo-black.svg",
        description: "Full FAM wordmark for movement-specific pages",
      },
    },
    autoSwitching: {
      rules: [
        "Lightness 0-30%: Use white logo (dark background)",
        "Lightness 30-45%: Use white logo (mid-dark background)",
        "Lightness 45-60%: Use black logo (mid-light background)",
        "Lightness 60-100%: Use black logo (light background)",
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
        "Never stretch, skew, or crop",
        "Use object-fit: contain",
        "Max width 280-360px for large spaces",
        "Scale between 16-48px for small icons",
        "Never place full wordmarks in small squares",
      ],
    },
    usage: {
      sidebar: "Use ep-icon (Expert Partners compact) in brand blue square",
      heroSections: "Use full wordmark (EP or FAM) based on page context",
      smallSpaces: "Use compact icons (ep-icon or fam-icon)",
      darkBackgrounds: "Always use white logo variants",
      lightBackgrounds: "Always use black logo variants",
    },
  },

  // ==========================================================================
  // ICON SYSTEM
  // ==========================================================================
  icons: {
    rules: [
      "White icons on blue (#2757CF), black, or dark backgrounds",
      "Black icons on white or light backgrounds",
      "Stroke width: 1.5 for Lucide icons",
    ],
    strokeWidth: 1.5,
  },

  // ==========================================================================
  // SIDEBAR LAYOUT
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
    accent: "#2757CF",
  },

  // ==========================================================================
  // CSS VARIABLES (for index.css)
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
      "--accent": "220 68% 48%",
      "--accent-foreground": "0 0% 100%",
      "--border": "0 0% 90%",
      "--ring": "220 68% 48%",
      "--radius": "0.5rem",
    },
    dark: {
      "--background": "0 0% 5%",
      "--foreground": "0 0% 98%",
      "--card": "0 0% 8%",
      "--card-foreground": "0 0% 98%",
      "--primary": "220 68% 48%",
      "--primary-foreground": "0 0% 100%",
      "--secondary": "0 0% 15%",
      "--secondary-foreground": "0 0% 95%",
      "--muted": "0 0% 15%",
      "--muted-foreground": "0 0% 55%",
      "--accent": "220 68% 48%",
      "--accent-foreground": "0 0% 100%",
      "--border": "0 0% 20%",
      "--ring": "220 68% 48%",
    },
    sidebar: {
      "--sidebar-background": "0 0% 0%",
      "--sidebar-foreground": "0 0% 85%",
      "--sidebar-primary": "220 68% 48%",
      "--sidebar-primary-foreground": "0 0% 100%",
      "--sidebar-accent": "0 0% 15%",
      "--sidebar-accent-foreground": "0 0% 95%",
      "--sidebar-border": "0 0% 20%",
      "--sidebar-ring": "220 68% 48%",
    },
  },

  // ==========================================================================
  // TAILWIND CONFIG EXTENSIONS
  // ==========================================================================
  tailwindExtensions: {
    fontFamily: {
      sans: ["Poppins", "system-ui", "sans-serif"],
      display: ["PT Serif", "Georgia", "serif"],
      subhead: ["Overpass", "system-ui", "sans-serif"],
      body: ["Poppins", "system-ui", "sans-serif"],
    },
    colors: {
      brand: {
        black: "#000000",
        white: "#ffffff",
        blue: "#2757CF",
        "blue-hover": "#3A6BFF",
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
    },
    boxShadow: {
      brand: "0px 2px 8px rgba(0, 0, 0, 0.08)",
      card: "0px 2px 8px rgba(0, 0, 0, 0.08)",
      "card-hover": "0px 4px 16px rgba(0, 0, 0, 0.12)",
      glow: "0 0 20px hsla(220, 68%, 48%, 0.15)",
    },
  },
} as const;

// Export type for TypeScript support
export type FAMThemeType = typeof FAMTheme;

export default FAMTheme;

Free Agent Movement visual style

Aesthetic is editorial neutral. Black and white only, black dominant, no accent colors. Same monochrome palette as Allison Gaddy personal brand, but the energy is structural, architectural, gender-neutral, inspired by Monocle and The Economist. Bold, modern, stripped-down. Movement-coded, not person-coded. Universally claimable for any operator in the movement, never leans feminine or masculine. Strength through restraint. Primary logo is the FAM mark.

Moxie visual style
Typography is Playfair Display for headers, Montserrat for body. Color palette is Rich Gold, Deep Black, Pure White. Positioning is Elevated Accessible Premium. Always co-brand with eXp Realty per their guidelines. Avoid flashy or trendy aesthetics. Stay clean, confident, classic luxury.

Expert Partners visual style
Aesthetic is black-dominant with Brand Blue #2757CF accents. Typography is PT Serif for editorial, Overpass and Poppins for body and interface. Strategic Command Center feel, inspired by freeagentmovement.io and innercircleresources.com. Bold, modern, editorial, with blue used as a strategic accent, never decorative.

Allison Gaddy’s personal visual stye
Aesthetic is editorial feminine. Black and white only, black dominant, no accent colors. Same monochrome palette as Free Agent Movement, but the energy is refined, considered, soft strength, fashion editorial inspired by Vogue, Kinfolk, and Cereal magazine. High-contrast serif typography, generous negative space, slow restrained pacing. Primary logo is the AG Signature script. Use for personal vulnerability content, origin story, book content, YouTube long-form authority videos, and behind-the-scenes operator content where Allison-as-woman is the focal point.
