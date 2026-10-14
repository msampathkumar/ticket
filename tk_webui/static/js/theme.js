// tk Web UI: theme module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';

export function initTheme() {
  if (state.isDarkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  document.body.setAttribute('data-accent', state.accentColor);
  document.body.setAttribute('data-font-family', state.fontFamily);
  document.documentElement.setAttribute('data-font-size', state.fontSize);
  if (state.contrastHigh) {
    document.body.classList.add('contrast-high');
  } else {
    document.body.classList.remove('contrast-high');
  }
  updateThemeIcon();
}

export function updateThemeIcon() {
  if (state.isDarkMode) {
    elements.themeIcon.setAttribute('data-lucide', 'sun');
  } else {
    elements.themeIcon.setAttribute('data-lucide', 'moon');
  }
  lucide.createIcons();
}

export function toggleTheme() {
  state.isDarkMode = !state.isDarkMode;
  localStorage.setItem('tk_theme', state.isDarkMode ? 'dark' : 'light');
  initTheme();
}
