// tk Web UI: views module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { renderKanban } from './kanban.js';
import { renderTableView } from './table.js';
import { renderTreeView } from './graph.js';
import { renderTimelineView } from './timeline.js';

export function filterTickets() {
  const query = elements.searchInput.value.toLowerCase().trim();
  const typeVal = elements.typeFilter.value;

  state.filteredTickets = state.tickets.filter(t => {
    if (typeVal !== 'all' && t.type !== typeVal) return false;

    // Date range filter (tic-6mex)
    if (state.startDateFilter && t.created) {
      const ticketDate = new Date(t.created).toISOString().split('T')[0];
      if (ticketDate < state.startDateFilter) return false;
    }
    if (state.endDateFilter && t.created) {
      const ticketDate = new Date(t.created).toISOString().split('T')[0];
      if (ticketDate > state.endDateFilter) return false;
    }

    if (query) {
      const matchId = t.id.toLowerCase().includes(query);
      const matchTitle = t.title.toLowerCase().includes(query);
      const matchDesc = (t.description || '').toLowerCase().includes(query);
      const matchAssignee = (t.assignee || '').toLowerCase().includes(query);
      const matchTags = (t.tags || []).some(tag => tag.toLowerCase().includes(query));
      if (!matchId && !matchTitle && !matchDesc && !matchAssignee && !matchTags) {
        return false;
      }
    }
    return true;
  });

  renderActiveView();
  updateStats();
}

export function updateStats() {
  const openCount = state.tickets.filter(t => t.status === 'open' && !t.is_blocked).length;
  const inProgressCount = state.tickets.filter(t => t.status === 'in_progress').length;
  const blockedCount = state.tickets.filter(t => t.status !== 'closed' && t.is_blocked).length;
  const closedCount = state.tickets.filter(t => t.status === 'closed').length;

  elements.statReady.textContent = openCount;
  elements.statProgress.textContent = inProgressCount;
  elements.statBlocked.textContent = blockedCount;
  elements.statClosed.textContent = closedCount;

  elements.countOpen.textContent = openCount;
  elements.countInProgress.textContent = inProgressCount;
  elements.countBlocked.textContent = blockedCount;
  elements.countClosed.textContent = closedCount;

  elements.ticketCountBadge.textContent = `${state.tickets.length} tickets`;
  elements.ticketCountBadge.classList.remove('hidden');
}

// VIEW SWITCHER LOGIC
export function hideAllViews() {
  elements.viewContainers.forEach(c => c.classList.add('hidden'));
}

export function switchView(viewName) {
  state.activeView = viewName;
  hideAllViews();

  elements.viewButtons.forEach(btn => {
    if (btn.dataset.view === viewName) {
      btn.className = 'view-tab-btn flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-900 shadow-sm text-brand-600 dark:text-brand-400 transition';
    } else {
      btn.className = 'view-tab-btn flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition';
    }
  });

  if (viewName === 'kanban') elements.kanbanBoard.classList.remove('hidden');
  else if (viewName === 'table') elements.tableView.classList.remove('hidden');
  else if (viewName === 'tree') elements.treeView.classList.remove('hidden');
  else if (viewName === 'timeline') elements.timelineView.classList.remove('hidden');

  renderActiveView();
  lucide.createIcons();
}

export function renderActiveView() {
  if (state.activeView === 'kanban') renderKanban();
  else if (state.activeView === 'table') renderTableView();
  else if (state.activeView === 'tree') renderTreeView();
  else if (state.activeView === 'timeline') renderTimelineView();
}
