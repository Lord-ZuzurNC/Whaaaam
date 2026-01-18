/** @type {import('tailwindcss').Config} */
module.exports = {
  // Content paths: TailwindCSS scans these files to determine which classes to include
  // Only classes actually used in these files will be included in the final CSS output (tree-shaking)
  content: [
    "./templates/**/*.html",  // All HTML templates
    "./static/**/*.js",       // All JavaScript files (including app.js with ThemeManager)
  ],

  theme: {
    extend: {
      colors: {
        // Catppuccin color palettes: https://github.com/catppuccin/catppuccin
        // Each palette contains 17 colors: 5 base colors + 12 accent colors
        // Usage: bg-{palette}-{color}, text-{palette}-{color}, border-{palette}-{color}
        // Example: bg-mocha-base, text-latte-text, border-frappe-mauve

        // Catppuccin Latte - Light theme with warm, cozy colors
        // Best for: Daytime use, bright environments
        latte: {
          // Base colors (backgrounds, surfaces, text)
          base: '#eff1f5',       // Main background
          surface: '#e6e9ef',    // Card/panel backgrounds
          overlay: '#dce0e8',    // Overlays, modals
          text: '#4c4f69',       // Primary text
          subtext: '#5c5f77',    // Secondary text, labels

          // Accent colors (buttons, highlights, semantic colors)
          rosewater: '#dc8a78', // Warm accent
          flamingo: '#dd7878',  // Warm accent
          pink: '#ea76cb',      // Vibrant accent
          mauve: '#8839ef',     // Theme signature color
          red: '#d20f39',       // Error states
          maroon: '#e64553',    // Alternate error
          peach: '#fe640b',     // Warning states
          yellow: '#df8e1d',    // Caution states
          green: '#40a02b',     // Success states
          teal: '#179299',      // Info states
          sky: '#04a5e5',       // Info accent
          sapphire: '#209fb5',  // Info accent
          blue: '#1e66f5',      // Primary accent
          lavender: '#7287fd',  // Soft accent
        },

        // Catppuccin Frappé - Cool dark theme with subtle purple tones
        // Best for: Evening use, moderate contrast preference
        frappe: {
          // Base colors
          base: '#303446',       // Main background
          surface: '#414559',    // Card/panel backgrounds
          overlay: '#51576d',    // Overlays, modals
          text: '#c6d0f5',       // Primary text
          subtext: '#a5adce',    // Secondary text, labels

          // Accent colors
          rosewater: '#f2d5cf',
          flamingo: '#eebebe',
          pink: '#f4b8e4',
          mauve: '#ca9ee6',
          red: '#e78284',
          maroon: '#ea999c',
          peach: '#ef9f76',
          yellow: '#e5c890',
          green: '#a6d189',
          teal: '#81c8be',
          sky: '#99d1db',
          sapphire: '#85c1dc',
          blue: '#8caaee',
          lavender: '#babbf1',
        },

        // Catppuccin Macchiato - Rich, saturated dark colors
        // Best for: Late evening use, MacOS aesthetic
        macchiato: {
          // Base colors
          base: '#24273a',       // Main background
          surface: '#363a4f',    // Card/panel backgrounds
          overlay: '#494d64',    // Overlays, modals
          text: '#cad3f5',       // Primary text
          subtext: '#a5adcb',    // Secondary text, labels

          // Accent colors
          rosewater: '#f4dbd6',
          flamingo: '#f0c6c6',
          pink: '#f5bde6',
          mauve: '#c6a0f6',
          red: '#ed8796',
          maroon: '#ee99a0',
          peach: '#f5a97f',
          yellow: '#eed49f',
          green: '#a6da95',
          teal: '#8bd5ca',
          sky: '#91d7e3',
          sapphire: '#7dc4e4',
          blue: '#8aadf4',
          lavender: '#b7bdf8',
        },

        // Catppuccin Mocha - Deep dark theme (default)
        // Best for: Late-night use, maximum contrast, OLED displays
        mocha: {
          // Base colors
          base: '#1e1e2e',       // Main background
          surface: '#313244',    // Card/panel backgrounds
          overlay: '#45475a',    // Overlays, modals
          text: '#cdd6f4',       // Primary text
          subtext: '#a6adc8',    // Secondary text, labels

          // Accent colors
          rosewater: '#f5e0dc',
          flamingo: '#f2cdcd',
          pink: '#f5c2e7',
          mauve: '#cba6f7',
          red: '#f38ba8',
          maroon: '#eba0ac',
          peach: '#fab387',
          yellow: '#f9e2af',
          green: '#a6e3a1',
          teal: '#94e2d5',
          sky: '#89dceb',
          sapphire: '#74c7ec',
          blue: '#89b4fa',
          lavender: '#b4befe',
        },
      },
    },
  },

  // Plugins: Additional Tailwind functionality
  // Currently empty, but can be extended with:
  // - @tailwindcss/forms - Better form styling
  // - @tailwindcss/typography - Prose styling
  // - @tailwindcss/aspect-ratio - Aspect ratio utilities
  plugins: [],
}

