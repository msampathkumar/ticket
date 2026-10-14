// tk Web UI: timeline module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, getPriorityBadge, getTypeBadge, getStatusBadge } from './utils.js';
import { openDetailModal } from './detail.js';

// 4. RENDER TIMELINE VIEW (msa-cvsb)
export function renderTimelineView() {
  elements.timelineContainer.innerHTML = '';

  const sortedTickets = [...state.filteredTickets].sort((a, b) => {
    const da = a.created ? new Date(a.created).getTime() : 0;
    const db = b.created ? new Date(b.created).getTime() : 0;
    return db - da;
  });

  if (sortedTickets.length === 0) {
    elements.timelineContainer.innerHTML = `<div class="text-center text-slate-400 py-12">No tickets to show in timeline</div>`;
    return;
  }

  sortedTickets.forEach(t => {
    const item = document.createElement('div');
    item.className = 'relative pl-8 pb-6 border-l-2 border-slate-200 dark:border-slate-800 last:border-l-0 cursor-pointer group';
    
    const dotColor = t.status === 'closed' ? 'bg-emerald-500' : t.is_blocked ? 'bg-rose-500' : t.status === 'in_progress' ? 'bg-amber-500' : 'bg-blue-500';

    item.innerHTML = `
      <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full ${dotColor} ring-4 ring-white dark:ring-slate-900"></div>
      <div class="bg-slate-50 dark:bg-slate-950/70 p-4 rounded-2xl border border-slate-300 dark:border-slate-800/80 group-hover:border-brand-500 transition">
        <div class="flex items-center justify-between text-xs text-slate-400 mb-1 font-mono">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(t.id)}</span>
            ${getStatusBadge(t.status, t.is_blocked)}
            ${getTypeBadge(t.type)}
            ${getPriorityBadge(t.priority)}
          </div>
          <span>${t.created ? new Date(t.created).toLocaleString() : 'Recently'}</span>
        </div>
        <h4 class="font-semibold text-sm text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition">${escapeHtml(t.title)}</h4>
        <p class="text-xs text-slate-500 mt-1 line-clamp-2">${escapeHtml(t.description || 'No description provided')}</p>
      </div>
    `;

    item.addEventListener('click', () => openDetailModal(t));
    elements.timelineContainer.appendChild(item);
  });

  lucide.createIcons();
}
