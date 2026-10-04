/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Refined Editorial Gold & Charcoal Palette
        atmos: {
          bg: '#F7F7F5',
          surface: '#FFFFFF',
          text: '#111111',
          secondary: '#66635C',
          muted: '#96938B',
          border: '#E5E2DA',
          gold: '#D9A441',
          goldWarm: '#E2B84A',
          goldDark: '#A97820',
          goldLight: '#F7EED7',
          success: '#2E7D5B',
          charcoal: '#111111',
        },
        dark: {
          bg: '#0F1117',
          surface: '#161822',
          text: '#F3F4F6',
          secondary: '#9CA3AF',
          muted: '#6B7280',
          border: '#262938',
          gold: '#D9A441',
        }
      },
      borderRadius: {
        'lg': '0.5rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px 0 rgba(0, 0, 0, 0.02)',
        'card': '0 2px 8px -2px rgba(0, 0, 0, 0.04)',
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}



