/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Government-aesthetic blues and whites
        'gov-blue': '#1e3a8a',
        'gov-light': '#f0f4f8',
      },
    },
  },
  plugins: [],
};
