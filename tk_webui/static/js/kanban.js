// tk Web UI: kanban module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, showToast, getPriorityBadge, getTypeBadge } from './utils.js';
import { fetchTickets } from './api.js';
import { renderActiveView } from './views.js';
import { openDetailModal } from './detail.js';

// 1. RENDER KANBAN (with Hide/Show Older Tasks - msa-6yop)
export function renderKanban() {
  elements.laneOpen.innerHTML = '';
  elements.laneInProgress.innerHTML = '';
  elements.laneBlocked.innerHTML = '';
  elements.laneClosed.innerHTML = '';

  const closedTickets = state.filteredTickets.filter(t => t.status === 'closed');
  const nonClosedTickets = state.filteredTickets.filter(t => t.status !== 'closed');

  nonClosedTickets.forEach(t => {
    const card = createTicketCardElement(t);
    if (t.is_blocked) {
      elements.laneBlocked.appendChild(card);
    } else if (t.status === 'in_progress') {
      elements.laneInProgress.appendChild(card);
    } else {
      elements.laneOpen.appendChild(card);
    }
  });

  // Closed tasks pagination (msa-6yop)
  const limit = 5;
  const showMoreNeeded = closedTickets.length > limit;
  const ticketsToRender = state.showAllClosed ? closedTickets : closedTickets.slice(0, limit);

  ticketsToRender.forEach(t => {
    elements.laneClosed.appendChild(createTicketCardElement(t));
  });

  if (showMoreNeeded) {
    elements.toggleOlderClosedBtn.classList.remove('hidden');
    elements.toggleOlderClosedText.textContent = state.showAllClosed 
      ? 'Show less completed tasks' 
      : `Show ${closedTickets.length - limit} older completed tasks`;
  } else {
    elements.toggleOlderClosedBtn.classList.add('hidden');
  }

  lucide.createIcons();
}

export function createTicketCardElement(ticket) {
  const card = document.createElement('div');
  card.id = `card-${ticket.id}`;
  card.dataset.id = ticket.id;
  card.className = `group bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-300 dark:border-slate-800 shadow-sm hover:shadow-md hover:border-brand-500/50 dark:hover:border-brand-500/40 transition duration-150 cursor-pointer select-none`;

  const tagsHtml = (ticket.tags || []).map(tag => 
    `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">#${escapeHtml(tag)}</span>`
  ).join('');

  const notesCount = (ticket.notes || []).length;
  const notesBadge = notesCount > 0 
    ? `<span title="${notesCount} notes/comments" class="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500"><i data-lucide="message-square" class="w-3 h-3"></i>${notesCount}</span>`
    : '';

  const blockedBadge = ticket.is_blocked
    ? `<div class="mt-2 text-[11px] flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded-md border border-rose-200/60 dark:border-rose-900/60 truncate">
        <i data-lucide="shield-alert" class="w-3 h-3 shrink-0"></i>
        <span class="truncate">Blocked: ${escapeHtml(ticket.blocked_by.join(', '))}</span>
       </div>`
    : '';

  card.innerHTML = `
    <div class="flex items-center justify-between gap-2 mb-2">
      <div class="flex items-center gap-1.5 flex-wrap">
        <span class="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(ticket.id)}</span>
        ${getTypeBadge(ticket.type)}
        ${getPriorityBadge(ticket.priority)}
      </div>
      <div class="flex items-center gap-1.5">
        ${notesBadge}
      </div>
    </div>

    <h3 class="font-semibold text-sm text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition leading-snug line-clamp-2 mb-2">${escapeHtml(ticket.title)}</h3>

    ${blockedBadge}

    <div class="flex items-center justify-between gap-2 mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80 text-xs">
      <div class="flex items-center gap-1 flex-wrap overflow-hidden">
        ${tagsHtml}
      </div>
      <div class="flex items-center gap-1 text-slate-400 text-[11px] font-medium shrink-0" title="Assignee: ${escapeHtml(ticket.assignee || 'Unassigned')}">
        <i data-lucide="user" class="w-3 h-3"></i>
        <span class="truncate max-w-[80px]">${escapeHtml(ticket.assignee || '—')}</span>
      </div>
    </div>
  `;

  card.addEventListener('click', () => openDetailModal(ticket));
  return card;
}

// SETUP DRAG & DROP
export function setupDragAndDrop() {
  const lanes = [
    { el: elements.laneOpen, status: 'open' },
    { el: elements.laneInProgress, status: 'in_progress' },
    { el: elements.laneBlocked, status: 'blocked' },
    { el: elements.laneClosed, status: 'closed' },
  ];

  lanes.forEach(lane => {
    new Sortable(lane.el, {
      group: 'kanban',
      animation: 150,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      onStart: () => { state.isDragging = true; },
      onEnd: async (evt) => {
        state.isDragging = false;
        const ticketId = evt.item.dataset.id;
        const targetStatus = evt.to.dataset.status;
        const sourceStatus = evt.from.dataset.status;

        if (targetStatus === sourceStatus) return;
        const statusToApply = targetStatus === 'blocked' ? 'open' : targetStatus;
        
        try {
          const res = await fetch('/api/tickets/status', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              directory: state.currentDir,
              ticket_id: ticketId,
              status: statusToApply
            })
          });

          if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Status update failed');
          }

          showToast(`Updated ${ticketId} -> ${statusToApply}`, 'success');
          await fetchTickets();
        } catch (err) {
          showToast(err.message, 'error');
          renderActiveView();
        }
      }
    });
  });
}
