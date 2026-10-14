// tk Web UI: table module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, getPriorityBadge, getTypeBadge, getStatusBadge } from './utils.js';
import { openDetailModal } from './detail.js';

// 2. RENDER TABLE VIEW (msa-cvsb)
export function renderTableView() {
  elements.tableBody.innerHTML = '';
  elements.tableResultsCount.textContent = `${state.filteredTickets.length} tickets`;

  if (state.filteredTickets.length === 0) {
    elements.tableBody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-400 text-sm">No tickets found</td></tr>`;
    return;
  }

  state.filteredTickets.forEach(t => {
    const tr = document.createElement('tr');
    tr.className = 'group hover:bg-slate-50/90 dark:hover:bg-slate-800/60 transition duration-150 cursor-pointer select-none border-b border-slate-100 dark:border-slate-800/60 last:border-b-0';
    
    const tagsHtml = (t.tags || []).map(tag => 
      `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 mr-1">#${escapeHtml(tag)}</span>`
    ).join('');

    tr.innerHTML = `
      <td class="p-3.5 font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(t.id)}</td>
      <td class="p-3.5 font-semibold text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition max-w-xs 2xl:max-w-xl truncate">${escapeHtml(t.title)}</td>
      <td class="p-3.5">${getStatusBadge(t.status, t.is_blocked)}</td>
      <td class="p-3.5">${getTypeBadge(t.type)}</td>
      <td class="p-3.5">${getPriorityBadge(t.priority)}</td>
      <td class="p-3.5 text-xs text-slate-600 dark:text-slate-300 font-medium">${escapeHtml(t.assignee || '—')}</td>
      <td class="p-3.5">${tagsHtml || '<span class="text-slate-400 text-xs">—</span>'}</td>
      <td class="p-3.5 text-xs text-slate-400 font-mono">${t.created ? new Date(t.created).toLocaleDateString() : '—'}</td>
      <td class="p-3.5 text-right">
        <button class="table-view-btn p-1 text-slate-400 group-hover:text-brand-600 dark:group-hover:text-brand-400 hover:bg-slate-200/70 dark:hover:bg-slate-700/70 rounded transition">
          <i data-lucide="eye" class="w-4 h-4"></i>
        </button>
      </td>
    `;
    tr.querySelector('.table-view-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      openDetailModal(t);
    });
    tr.addEventListener('click', () => openDetailModal(t));
    elements.tableBody.appendChild(tr);
  });

  lucide.createIcons();
}
