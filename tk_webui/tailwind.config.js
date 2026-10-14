// Build-time Tailwind config for the Web UI. Not loaded by the browser.
// Regenerate static/css/tailwind.css with scripts/build-webui-css.sh (see static/vendor/README.md).
module.exports = {
  content: ['./static/index.html', './static/js/**/*.js'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
      },
    },
  },
};
