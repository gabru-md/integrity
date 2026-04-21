/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
    "./apps/**/*.py",
    "./services/**/*.py",
  ],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [],
};
