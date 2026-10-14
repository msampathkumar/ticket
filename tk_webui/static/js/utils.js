// tk Web UI: utils module (split from app.js, tic-4h0q).
import { elements } from './state.js';

// Escape a value for safe interpolation into HTML text or quoted attributes.
export function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Render untrusted markdown to sanitised HTML. Falls back to escaped text if DOMPurify is unavailable.
export function renderMarkdown(text) {
  const raw = text || '';
  if (typeof DOMPurify === 'undefined' || typeof marked === 'undefined') {
    return `<p>${escapeHtml(raw)}</p>`;
  }
  return DOMPurify.sanitize(marked.parse(raw));
}

export function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  const bg = type === 'error' ? 'bg-rose-600 text-white' : type === 'success' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900';
  toast.className = `${bg} px-4 py-2.5 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2 animate-fade-in pointer-events-auto transition duration-200`;
  
  const icon = type === 'error' ? 'alert-circle' : type === 'success' ? 'check-circle' : 'info';
  toast.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4"></i> <span>${escapeHtml(message)}</span>`;
  elements.toastContainer.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}

export function getPriorityBadge(priority) {
  const p = String(priority);
  switch (p) {
    case '0': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300">P0</span>`;
    case '1': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/70 dark:text-amber-300">P1</span>`;
    case '2': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-950/70 dark:text-blue-300">P2</span>`;
    case '3': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">P3</span>`;
    default: return `<span class="px-1.5 py-0.5 rounded text-[10px] text-slate-500">P4</span>`;
  }
}

export function getTypeBadge(type) {
  const t = (type || 'task').toLowerCase();
  const styles = {
    feature: 'bg-purple-100 text-purple-700 dark:bg-purple-950/70 dark:text-purple-300',
    bug: 'bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300',
    task: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950/70 dark:text-indigo-300',
    epic: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950/70 dark:text-fuchsia-300',
    chore: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  };
  const cls = styles[t] || styles.task;
  return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${cls}">${escapeHtml(t)}</span>`;
}

export function getStatusBadge(status, isBlocked = false) {
  if (status === 'closed') {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300">Closed</span>`;
  } else if (isBlocked) {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300">Blocked</span>`;
  } else if (status === 'in_progress') {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300">In Progress</span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300">Ready</span>`;
}
