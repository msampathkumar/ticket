// State management
const state = {
  currentDir: '',
  tickets: [],
  filteredTickets: [],
  activeTicket: null,
  activeView: 'kanban', // 'kanban', 'table', 'tree', 'timeline'
  showAllClosed: false,
  recentDirs: JSON.parse(localStorage.getItem('tk_recent_dirs') || '[]'),
  browsingDir: '~',
  isDarkMode: localStorage.getItem('tk_theme') === 'dark' || (!('tk_theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)
};

// DOM elements
const elements = {
  dirInput: document.getElementById('dirInput'),
  loadDirBtn: document.getElementById('loadDirBtn'),
  recentDirsBtn: document.getElementById('recentDirsBtn'),
  recentDirsPopover: document.getElementById('recentDirsPopover'),
  recentDirsList: document.getElementById('recentDirsList'),
  browseBtn: document.getElementById('browseBtn'),
  searchInput: document.getElementById('searchInput'),
  typeFilter: document.getElementById('typeFilter'),
  refreshBtn: document.getElementById('refreshBtn'),
  themeToggle: document.getElementById('themeToggle'),
  themeIcon: document.getElementById('themeIcon'),
  statusDot: document.getElementById('statusDot'),
  currentPathLabel: document.getElementById('currentPathLabel'),
  ticketCountBadge: document.getElementById('ticketCountBadge'),
  statsBar: document.getElementById('statsBar'),
  statReady: document.getElementById('statReady'),
  statProgress: document.getElementById('statProgress'),
  statBlocked: document.getElementById('statBlocked'),
  statClosed: document.getElementById('statClosed'),
  noTicketsBanner: document.getElementById('noTicketsBanner'),
  initTicketsBtn: document.getElementById('initTicketsBtn'),
  
  // Views
  viewButtons: document.querySelectorAll('.view-tab-btn'),
  viewContainers: document.querySelectorAll('.view-container'),
  kanbanBoard: document.getElementById('kanbanBoard'),
  tableView: document.getElementById('tableView'),
  treeView: document.getElementById('treeView'),
  timelineView: document.getElementById('timelineView'),
  tableBody: document.getElementById('tableBody'),
  tableResultsCount: document.getElementById('tableResultsCount'),
  treeContainer: document.getElementById('treeContainer'),
  timelineContainer: document.getElementById('timelineContainer'),

  // Lanes
  laneOpen: document.getElementById('lane-open'),
  laneInProgress: document.getElementById('lane-in_progress'),
  laneBlocked: document.getElementById('lane-blocked'),
  laneClosed: document.getElementById('lane-closed'),
  countOpen: document.getElementById('count-open'),
  countInProgress: document.getElementById('count-in_progress'),
  countBlocked: document.getElementById('count-blocked'),
  countClosed: document.getElementById('count-closed'),
  toggleOlderClosedBtn: document.getElementById('toggleOlderClosedBtn'),
  toggleOlderClosedText: document.getElementById('toggleOlderClosedText'),

  // New Ticket Modal
  openNewTicketModalBtn: document.getElementById('openNewTicketModalBtn'),
  newTicketModal: document.getElementById('newTicketModal'),
  closeNewTicketModalBtn: document.getElementById('closeNewTicketModalBtn'),
  cancelNewTicketBtn: document.getElementById('cancelNewTicketBtn'),
  createTicketForm: document.getElementById('createTicketForm'),

  // Edit Ticket Modal (msa-y8zi)
  editTicketModal: document.getElementById('editTicketModal'),
  closeEditTicketModalBtn: document.getElementById('closeEditTicketModalBtn'),
  cancelEditTicketBtn: document.getElementById('cancelEditTicketBtn'),
  editTicketForm: document.getElementById('editTicketForm'),
  editActiveTicketBtn: document.getElementById('editActiveTicketBtn'),
  editTicketIdLabel: document.getElementById('editTicketIdLabel'),
  editTicketTitle: document.getElementById('editTicketTitle'),
  editTicketType: document.getElementById('editTicketType'),
  editTicketPriority: document.getElementById('editTicketPriority'),
  editTicketAssignee: document.getElementById('editTicketAssignee'),
  editTicketDescription: document.getElementById('editTicketDescription'),
  editTicketTags: document.getElementById('editTicketTags'),
  editTicketDesign: document.getElementById('editTicketDesign'),
  editTicketAcceptance: document.getElementById('editTicketAcceptance'),

  // Detail Modal
  detailModal: document.getElementById('detailModal'),
  closeDetailModalBtn: document.getElementById('closeDetailModalBtn'),

  // Folder Explorer Modal
  folderModal: document.getElementById('folderModal'),
  closeFolderModalBtn: document.getElementById('closeFolderModalBtn'),
  folderList: document.getElementById('folderList'),
  folderCurrentPath: document.getElementById('folderCurrentPath'),
  folderUpBtn: document.getElementById('folderUpBtn'),
  selectCurrentFolderBtn: document.getElementById('selectCurrentFolderBtn'),
  toastContainer: document.getElementById('toastContainer'),
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  setupEventListeners();
  setupDragAndDrop();

  const urlParams = new URLSearchParams(window.location.search);
  const dirParam = urlParams.get('dir');
  const initialDir = dirParam || localStorage.getItem('tk_current_dir') || '.';

  elements.dirInput.value = initialDir;
  await loadDirectory(initialDir);
});

function initTheme() {
  if (state.isDarkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  updateThemeIcon();
}

function updateThemeIcon() {
  if (state.isDarkMode) {
    elements.themeIcon.setAttribute('data-lucide', 'sun');
  } else {
    elements.themeIcon.setAttribute('data-lucide', 'moon');
  }
  lucide.createIcons();
}

function toggleTheme() {
  state.isDarkMode = !state.isDarkMode;
  localStorage.setItem('tk_theme', state.isDarkMode ? 'dark' : 'light');
  initTheme();
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  const bg = type === 'error' ? 'bg-rose-600 text-white' : type === 'success' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900';
  toast.className = `${bg} px-4 py-2.5 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2 animate-fade-in pointer-events-auto transition duration-200`;
  
  const icon = type === 'error' ? 'alert-circle' : type === 'success' ? 'check-circle' : 'info';
  toast.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4"></i> <span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}

function addRecentDir(dir) {
  if (!dir) return;
  state.recentDirs = [dir, ...state.recentDirs.filter(d => d !== dir)].slice(0, 8);
  localStorage.setItem('tk_recent_dirs', JSON.stringify(state.recentDirs));
  renderRecentDirs();
}

function renderRecentDirs() {
  elements.recentDirsList.innerHTML = '';
  if (state.recentDirs.length === 0) {
    elements.recentDirsList.innerHTML = '<div class="text-xs text-slate-400 p-2">No recent projects</div>';
    return;
  }
  state.recentDirs.forEach(dir => {
    const item = document.createElement('button');
    item.className = 'w-full text-left px-2.5 py-1.5 text-xs rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 truncate font-mono text-slate-700 dark:text-slate-300 flex items-center gap-2';
    item.innerHTML = `<i data-lucide="folder" class="w-3.5 h-3.5 shrink-0 text-slate-400"></i> <span class="truncate">${dir}</span>`;
    item.onclick = () => {
      elements.recentDirsPopover.classList.add('hidden');
      elements.dirInput.value = dir;
      loadDirectory(dir);
    };
    elements.recentDirsList.appendChild(item);
  });
  lucide.createIcons();
}

async function loadDirectory(path) {
  try {
    const res = await fetch(`/api/check-directory?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error('Failed to verify directory');
    const data = await res.json();

    state.currentDir = data.path;
    elements.dirInput.value = data.path;
    elements.currentPathLabel.textContent = data.path;
    localStorage.setItem('tk_current_dir', data.path);
    addRecentDir(data.path);

    const url = new URL(window.location);
    url.searchParams.set('dir', data.path);
    window.history.replaceState({}, '', url);

    if (!data.has_tickets) {
      elements.statusDot.className = 'inline-block w-2 h-2 rounded-full bg-amber-500';
      elements.ticketCountBadge.classList.add('hidden');
      elements.noTicketsBanner.classList.remove('hidden');
      hideAllViews();
      state.tickets = [];
      updateStats();
      return;
    }

    elements.statusDot.className = 'inline-block w-2 h-2 rounded-full bg-emerald-500';
    elements.noTicketsBanner.classList.add('hidden');
    switchView(state.activeView);

    await fetchTickets();
  } catch (err) {
    showToast(err.message, 'error');
    elements.statusDot.className = 'inline-block w-2 h-2 rounded-full bg-rose-500';
  }
}

async function fetchTickets() {
  try {
    const res = await fetch(`/api/tickets?directory=${encodeURIComponent(state.currentDir)}`);
    if (!res.ok) throw new Error('Failed to load tickets');
    state.tickets = await res.json();
    filterTickets();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function filterTickets() {
  const query = elements.searchInput.value.toLowerCase().trim();
  const typeVal = elements.typeFilter.value;

  state.filteredTickets = state.tickets.filter(t => {
    if (typeVal !== 'all' && t.type !== typeVal) return false;

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

function updateStats() {
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
function hideAllViews() {
  elements.viewContainers.forEach(c => c.classList.add('hidden'));
}

function switchView(viewName) {
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

function renderActiveView() {
  if (state.activeView === 'kanban') renderKanban();
  else if (state.activeView === 'table') renderTableView();
  else if (state.activeView === 'tree') renderTreeView();
  else if (state.activeView === 'timeline') renderTimelineView();
}

function getPriorityBadge(priority) {
  const p = String(priority);
  switch (p) {
    case '0': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-extrabold bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300">P0</span>`;
    case '1': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/70 dark:text-amber-300">P1</span>`;
    case '2': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-950/70 dark:text-blue-300">P2</span>`;
    case '3': return `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">P3</span>`;
    default: return `<span class="px-1.5 py-0.5 rounded text-[10px] text-slate-500">P4</span>`;
  }
}

function getTypeBadge(type) {
  const t = (type || 'task').toLowerCase();
  const styles = {
    feature: 'bg-purple-100 text-purple-700 dark:bg-purple-950/70 dark:text-purple-300',
    bug: 'bg-rose-100 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300',
    task: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950/70 dark:text-indigo-300',
    epic: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950/70 dark:text-fuchsia-300',
    chore: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  };
  const cls = styles[t] || styles.task;
  return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${cls}">${t}</span>`;
}

function getStatusBadge(status, isBlocked = false) {
  if (status === 'closed') {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300">Closed</span>`;
  } else if (isBlocked) {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300">Blocked</span>`;
  } else if (status === 'in_progress') {
    return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300">In Progress</span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300">Ready</span>`;
}

// 1. RENDER KANBAN (with Hide/Show Older Tasks - msa-6yop)
function renderKanban() {
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

function createTicketCardElement(ticket) {
  const card = document.createElement('div');
  card.id = `card-${ticket.id}`;
  card.dataset.id = ticket.id;
  card.className = `group bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-md hover:border-brand-500/50 dark:hover:border-brand-500/40 transition duration-150 cursor-pointer select-none`;

  const tagsHtml = (ticket.tags || []).map(tag => 
    `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">#${tag}</span>`
  ).join('');

  const notesCount = (ticket.notes || []).length;
  const notesBadge = notesCount > 0 
    ? `<span title="${notesCount} notes/comments" class="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500"><i data-lucide="message-square" class="w-3 h-3"></i>${notesCount}</span>`
    : '';

  const blockedBadge = ticket.is_blocked
    ? `<div class="mt-2 text-[11px] flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded-md border border-rose-200/60 dark:border-rose-900/60 truncate">
        <i data-lucide="shield-alert" class="w-3 h-3 shrink-0"></i>
        <span class="truncate">Blocked: ${ticket.blocked_by.join(', ')}</span>
       </div>`
    : '';

  card.innerHTML = `
    <div class="flex items-center justify-between gap-2 mb-2">
      <div class="flex items-center gap-1.5 flex-wrap">
        <span class="font-mono text-xs font-bold text-slate-500 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition">${ticket.id}</span>
        ${getTypeBadge(ticket.type)}
        ${getPriorityBadge(ticket.priority)}
      </div>
      <div class="flex items-center gap-1.5">
        ${notesBadge}
      </div>
    </div>

    <h3 class="font-semibold text-sm text-slate-900 dark:text-slate-100 leading-snug line-clamp-2 mb-2">${ticket.title}</h3>

    ${blockedBadge}

    <div class="flex items-center justify-between gap-2 mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80 text-xs">
      <div class="flex items-center gap-1 flex-wrap overflow-hidden">
        ${tagsHtml}
      </div>
      <div class="flex items-center gap-1 text-slate-400 text-[11px] font-medium shrink-0" title="Assignee: ${ticket.assignee || 'Unassigned'}">
        <i data-lucide="user" class="w-3 h-3"></i>
        <span class="truncate max-w-[80px]">${ticket.assignee || '—'}</span>
      </div>
    </div>
  `;

  card.addEventListener('click', () => openDetailModal(ticket));
  return card;
}

// 2. RENDER TABLE VIEW (msa-cvsb)
function renderTableView() {
  elements.tableBody.innerHTML = '';
  elements.tableResultsCount.textContent = `${state.filteredTickets.length} tickets`;

  if (state.filteredTickets.length === 0) {
    elements.tableBody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-400 text-sm">No tickets found</td></tr>`;
    return;
  }

  state.filteredTickets.forEach(t => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition cursor-pointer';
    
    const tagsHtml = (t.tags || []).map(tag => 
      `<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 mr-1">#${tag}</span>`
    ).join('');

    tr.innerHTML = `
      <td class="p-3.5 font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${t.id}</td>
      <td class="p-3.5 font-semibold text-slate-900 dark:text-slate-100 max-w-xs truncate">${t.title}</td>
      <td class="p-3.5">${getStatusBadge(t.status, t.is_blocked)}</td>
      <td class="p-3.5">${getTypeBadge(t.type)}</td>
      <td class="p-3.5">${getPriorityBadge(t.priority)}</td>
      <td class="p-3.5 text-xs text-slate-600 dark:text-slate-300 font-medium">${t.assignee || '—'}</td>
      <td class="p-3.5">${tagsHtml || '<span class="text-slate-400 text-xs">—</span>'}</td>
      <td class="p-3.5 text-xs text-slate-400 font-mono">${t.created ? new Date(t.created).toLocaleDateString() : '—'}</td>
      <td class="p-3.5 text-right">
        <button class="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded" onclick="event.stopPropagation(); openDetailModal(state.tickets.find(x => x.id === '${t.id}'))">
          <i data-lucide="eye" class="w-4 h-4"></i>
        </button>
      </td>
    `;
    tr.addEventListener('click', () => openDetailModal(t));
    elements.tableBody.appendChild(tr);
  });

  lucide.createIcons();
}

// 3. RENDER TREE / DEPENDENCY GRAPH VIEW (msa-cvsb)
function renderTreeView() {
  elements.treeContainer.innerHTML = '';

  const projectName = state.currentDir.split('/').filter(Boolean).pop() || 'Project';

  const rootNode = document.createElement('div');
  rootNode.className = 'p-4 bg-brand-600 text-white rounded-2xl shadow-lg font-bold text-base flex items-center gap-2 mb-8';
  rootNode.innerHTML = `<i data-lucide="folder-git-2" class="w-5 h-5"></i> <span>${projectName} Root</span>`;
  elements.treeContainer.appendChild(rootNode);

  // Group root tasks vs dependent child tasks
  const grid = document.createElement('div');
  grid.className = 'w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6';

  state.filteredTickets.forEach(t => {
    const node = document.createElement('div');
    node.className = 'p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-2 hover:border-brand-500 cursor-pointer transition';
    
    let depsHtml = '';
    if (t.deps && t.deps.length > 0) {
      depsHtml = `<div class="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
        <i data-lucide="link" class="w-3 h-3 text-brand-500"></i> Depends on: <strong>${t.deps.join(', ')}</strong>
      </div>`;
    }

    let parentHtml = '';
    if (t.parent) {
      parentHtml = `<div class="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
        <i data-lucide="corner-down-right" class="w-3 h-3 text-indigo-500"></i> Parent: <strong>${t.parent}</strong>
      </div>`;
    }

    node.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-mono text-xs font-bold text-brand-600">${t.id}</span>
        ${getStatusBadge(t.status, t.is_blocked)}
      </div>
      <h4 class="font-semibold text-sm text-slate-800 dark:text-slate-200 leading-snug">${t.title}</h4>
      ${parentHtml}
      ${depsHtml}
    `;

    node.addEventListener('click', () => openDetailModal(t));
    grid.appendChild(node);
  });

  elements.treeContainer.appendChild(grid);
  lucide.createIcons();
}

// 4. RENDER TIMELINE VIEW (msa-cvsb)
function renderTimelineView() {
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
      <div class="bg-slate-50 dark:bg-slate-950/70 p-4 rounded-2xl border border-slate-200 dark:border-slate-800/80 group-hover:border-brand-500 transition">
        <div class="flex items-center justify-between text-xs text-slate-400 mb-1 font-mono">
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-700 dark:text-slate-300">${t.id}</span>
            ${getTypeBadge(t.type)}
            ${getPriorityBadge(t.priority)}
          </div>
          <span>${t.created ? new Date(t.created).toLocaleString() : 'Recently'}</span>
        </div>
        <h4 class="font-semibold text-sm text-slate-900 dark:text-slate-100">${t.title}</h4>
        <p class="text-xs text-slate-500 mt-1 line-clamp-2">${t.description || 'No description provided'}</p>
      </div>
    `;

    item.addEventListener('click', () => openDetailModal(t));
    elements.timelineContainer.appendChild(item);
  });

  lucide.createIcons();
}

// SETUP DRAG & DROP
function setupDragAndDrop() {
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
      onEnd: async (evt) => {
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

// DETAIL MODAL
function openDetailModal(ticket) {
  state.activeTicket = ticket;

  document.getElementById('detailId').textContent = ticket.id;
  
  const typeEl = document.getElementById('detailType');
  typeEl.textContent = ticket.type;
  typeEl.className = `text-xs uppercase tracking-wider font-bold px-2 py-0.5 rounded ${ticket.type === 'bug' ? 'bg-rose-100 text-rose-700' : 'bg-brand-100 text-brand-700'}`;

  const prioEl = document.getElementById('detailPriority');
  prioEl.textContent = `Priority ${ticket.priority}`;
  prioEl.className = `text-xs font-bold px-2 py-0.5 rounded ${ticket.priority <= 1 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`;

  document.getElementById('detailStatusSelect').value = ticket.status;
  document.getElementById('detailTitle').textContent = ticket.title;
  document.getElementById('detailAssignee').textContent = ticket.assignee || 'Unassigned';
  document.getElementById('detailCreated').textContent = ticket.created ? new Date(ticket.created).toLocaleString() : 'Recently';

  const tagsContainer = document.getElementById('detailTagsContainer');
  tagsContainer.innerHTML = (ticket.tags || []).map(t => 
    `<span class="px-2 py-0.5 text-xs font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">#${t}</span>`
  ).join('');

  const blockedAlert = document.getElementById('detailBlockedAlert');
  const blockedList = document.getElementById('detailBlockedList');
  if (ticket.is_blocked && ticket.blocked_by.length > 0) {
    blockedAlert.classList.remove('hidden');
    blockedList.innerHTML = ticket.blocked_by.map(b => `<span class="px-2 py-0.5 bg-rose-200/80 dark:bg-rose-900 rounded">${b}</span>`).join('');
  } else {
    blockedAlert.classList.add('hidden');
  }

  const descEl = document.getElementById('detailDescription');
  descEl.innerHTML = ticket.description ? marked.parse(ticket.description) : '<p class="text-slate-400 italic">No description provided.</p>';

  const designSec = document.getElementById('detailDesignSec');
  if (ticket.design) {
    designSec.classList.remove('hidden');
    document.getElementById('detailDesign').innerHTML = marked.parse(ticket.design);
  } else {
    designSec.classList.add('hidden');
  }

  const acceptSec = document.getElementById('detailAcceptanceSec');
  if (ticket.acceptance) {
    acceptSec.classList.remove('hidden');
    document.getElementById('detailAcceptance').innerHTML = marked.parse(ticket.acceptance);
  } else {
    acceptSec.classList.add('hidden');
  }

  renderDetailDependencies(ticket);
  renderDetailNotes(ticket);

  elements.detailModal.classList.remove('hidden');
  lucide.createIcons();
}

function renderDetailDependencies(ticket) {
  const depsList = document.getElementById('detailDepsList');
  depsList.innerHTML = '';

  if (ticket.deps && ticket.deps.length > 0) {
    ticket.deps.forEach(depId => {
      const depBadge = document.createElement('div');
      depBadge.className = 'flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700';
      depBadge.innerHTML = `
        <i data-lucide="git-commit" class="w-3 h-3 text-slate-400"></i>
        <span>${depId}</span>
        <button title="Remove dependency" class="text-slate-400 hover:text-rose-500 ml-1 p-0.5" onclick="removeDependency('${ticket.id}', '${depId}')">
          <i data-lucide="x" class="w-3 h-3"></i>
        </button>
      `;
      depsList.appendChild(depBadge);
    });
  } else {
    depsList.innerHTML = '<span class="text-slate-400 text-xs italic">No dependencies</span>';
  }
}

function renderDetailNotes(ticket) {
  const notesFeed = document.getElementById('detailNotesFeed');
  const countLabel = document.getElementById('detailNotesCount');
  notesFeed.innerHTML = '';

  const notes = ticket.notes || [];
  countLabel.textContent = `${notes.length} note${notes.length === 1 ? '' : 's'}`;

  if (notes.length === 0) {
    notesFeed.innerHTML = '<div class="text-xs text-slate-400 italic p-3 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 text-center">No review notes or comments yet. Add the first one below!</div>';
    return;
  }

  notes.forEach((n, idx) => {
    const item = document.createElement('div');
    item.className = 'p-3.5 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200/80 dark:border-slate-800/80 space-y-1.5';
    
    let formattedTime = n.timestamp;
    try { formattedTime = new Date(n.timestamp).toLocaleString(); } catch (e) {}

    item.innerHTML = `
      <div class="flex items-center justify-between text-xs text-slate-400">
        <span class="flex items-center gap-1.5 font-semibold text-slate-600 dark:text-slate-300">
          <i data-lucide="user-check" class="w-3.5 h-3.5 text-brand-500"></i>
          <span>Note #${idx + 1}</span>
        </span>
        <span class="font-mono text-[11px]">${formattedTime}</span>
      </div>
      <div class="prose dark:prose-invert text-xs text-slate-800 dark:text-slate-200 pt-1">
        ${marked.parse(n.text)}
      </div>
    `;
    notesFeed.appendChild(item);
  });
}

// EDIT TICKET MODAL HANDLERS (msa-y8zi)
function openEditTicketModal(ticket) {
  if (!ticket) return;
  elements.editTicketIdLabel.textContent = `[${ticket.id}]`;
  elements.editTicketTitle.value = ticket.title || '';
  elements.editTicketType.value = ticket.type || 'task';
  elements.editTicketPriority.value = String(ticket.priority ?? 2);
  elements.editTicketAssignee.value = ticket.assignee || '';
  elements.editTicketDescription.value = ticket.description || '';
  elements.editTicketTags.value = (ticket.tags || []).join(', ');
  elements.editTicketDesign.value = ticket.design || '';
  elements.editTicketAcceptance.value = ticket.acceptance || '';

  elements.editTicketModal.classList.remove('hidden');
  elements.editTicketTitle.focus();
  lucide.createIcons();
}

async function handleEditTicketSubmit(e) {
  e.preventDefault();
  if (!state.activeTicket) return;

  const title = elements.editTicketTitle.value.trim();
  const type = elements.editTicketType.value;
  const priority = parseInt(elements.editTicketPriority.value, 10);
  const assignee = elements.editTicketAssignee.value.trim() || null;
  const description = elements.editTicketDescription.value.trim() || null;
  const tagsStr = elements.editTicketTags.value.trim();
  const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];
  const design = elements.editTicketDesign.value.trim() || null;
  const acceptance = elements.editTicketAcceptance.value.trim() || null;

  try {
    const res = await fetch('/api/tickets', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: state.activeTicket.id,
        title,
        type,
        priority,
        assignee,
        description,
        tags,
        design,
        acceptance,
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update ticket');
    }

    showToast(`Ticket ${state.activeTicket.id} updated`, 'success');
    elements.editTicketModal.classList.add('hidden');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === state.activeTicket.id);
    if (updated) openDetailModal(updated);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// POST REVIEW NOTE
async function submitReviewNote() {
  if (!state.activeTicket) return;
  const input = document.getElementById('newNoteInput');
  const text = input.value.trim();
  if (!text) {
    showToast('Please type a note first', 'error');
    return;
  }

  try {
    const res = await fetch('/api/tickets/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: state.activeTicket.id,
        note: text
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to post note');
    }

    input.value = '';
    showToast('Review note appended', 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === state.activeTicket.id);
    if (updated) {
      state.activeTicket = updated;
      renderDetailNotes(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// DEPENDENCY ACTIONS
async function addDependency(ticketId, depId) {
  try {
    const res = await fetch('/api/tickets/dependencies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: ticketId,
        dep_id: depId
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add dependency');
    }

    showToast(`Added dependency ${ticketId} -> ${depId}`, 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === ticketId);
    if (updated) {
      state.activeTicket = updated;
      renderDetailDependencies(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function removeDependency(ticketId, depId) {
  try {
    const res = await fetch('/api/tickets/dependencies', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: ticketId,
        dep_id: depId
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to remove dependency');
    }

    showToast(`Removed dependency ${ticketId} -> ${depId}`, 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === ticketId);
    if (updated) {
      state.activeTicket = updated;
      renderDetailDependencies(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// CREATE TICKET
function openNewTicketModal(status = 'open') {
  elements.createTicketForm.reset();
  elements.newTicketModal.classList.remove('hidden');
  document.getElementById('newTicketTitle').focus();
  lucide.createIcons();
}

async function handleCreateTicket(e) {
  e.preventDefault();
  const title = document.getElementById('newTicketTitle').value.trim();
  const type = document.getElementById('newTicketType').value;
  const priority = parseInt(document.getElementById('newTicketPriority').value, 10);
  const assignee = document.getElementById('newTicketAssignee').value.trim() || null;
  const description = document.getElementById('newTicketDescription').value.trim() || null;
  const tagsStr = document.getElementById('newTicketTags').value.trim();
  const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : null;
  const design = document.getElementById('newTicketDesign').value.trim() || null;
  const acceptance = document.getElementById('newTicketAcceptance').value.trim() || null;
  const parent = document.getElementById('newTicketParent').value.trim() || null;
  const externalRef = document.getElementById('newTicketExternalRef').value.trim() || null;

  try {
    const res = await fetch('/api/tickets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        title,
        type,
        priority,
        assignee,
        description,
        tags,
        design,
        acceptance,
        parent,
        external_ref: externalRef
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create ticket');
    }

    const data = await res.json();
    showToast(`Ticket ${data.ticket_id} created`, 'success');
    elements.newTicketModal.classList.add('hidden');
    await fetchTickets();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// FOLDER BROWSER
async function openFolderBrowser(path = '~') {
  state.browsingDir = path;
  elements.folderCurrentPath.textContent = path;
  elements.folderModal.classList.remove('hidden');

  try {
    const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error('Failed to browse folders');
    const items = await res.json();

    elements.folderList.innerHTML = '';
    if (items.length === 0) {
      elements.folderList.innerHTML = '<div class="text-xs text-slate-400 p-4 text-center">No subfolders</div>';
      return;
    }

    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'flex items-center justify-between p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg cursor-pointer group';
      
      const badge = item.has_tickets 
        ? `<span class="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold">.tickets</span>` 
        : '';

      row.innerHTML = `
        <div class="flex items-center gap-2 truncate">
          <i data-lucide="folder" class="w-4 h-4 text-brand-500 shrink-0"></i>
          <span class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">${item.name}</span>
        </div>
        <div class="flex items-center gap-2">
          ${badge}
          <i data-lucide="chevron-right" class="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition"></i>
        </div>
      `;

      row.onclick = () => openFolderBrowser(item.path);
      elements.folderList.appendChild(row);
    });

    lucide.createIcons();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function initRepository() {
  try {
    const res = await fetch('/api/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ directory: state.currentDir })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Initialization failed');
    }

    showToast('Initialized .tickets repository', 'success');
    await loadDirectory(state.currentDir);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// SETUP EVENT LISTENERS
function setupEventListeners() {
  elements.loadDirBtn.addEventListener('click', () => loadDirectory(elements.dirInput.value.trim()));
  elements.dirInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') loadDirectory(elements.dirInput.value.trim());
  });

  // View switchers
  elements.viewButtons.forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // Toggle older closed tasks (msa-6yop)
  elements.toggleOlderClosedBtn.addEventListener('click', () => {
    state.showAllClosed = !state.showAllClosed;
    renderKanban();
  });

  // Recent projects
  elements.recentDirsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    renderRecentDirs();
    const rect = elements.recentDirsBtn.getBoundingClientRect();
    elements.recentDirsPopover.style.top = `${rect.bottom + 8}px`;
    elements.recentDirsPopover.style.left = `${Math.max(10, rect.left - 180)}px`;
    elements.recentDirsPopover.classList.toggle('hidden');
  });

  document.addEventListener('click', (e) => {
    if (!elements.recentDirsPopover.contains(e.target) && e.target !== elements.recentDirsBtn) {
      elements.recentDirsPopover.classList.add('hidden');
    }
  });

  // Browse folders
  elements.browseBtn.addEventListener('click', () => openFolderBrowser(elements.dirInput.value.trim() || '~'));
  elements.closeFolderModalBtn.addEventListener('click', () => elements.folderModal.classList.add('hidden'));
  elements.folderUpBtn.addEventListener('click', () => {
    const parent = state.browsingDir.split('/').slice(0, -1).join('/') || '/';
    openFolderBrowser(parent);
  });
  elements.selectCurrentFolderBtn.addEventListener('click', () => {
    elements.folderModal.classList.add('hidden');
    elements.dirInput.value = state.browsingDir;
    loadDirectory(state.browsingDir);
  });

  // Search & Filter
  elements.searchInput.addEventListener('input', filterTickets);
  elements.typeFilter.addEventListener('change', filterTickets);
  elements.refreshBtn.addEventListener('click', fetchTickets);
  elements.themeToggle.addEventListener('click', toggleTheme);

  // New Ticket Modal
  elements.openNewTicketModalBtn.addEventListener('click', () => openNewTicketModal('open'));
  elements.closeNewTicketModalBtn.addEventListener('click', () => elements.newTicketModal.classList.add('hidden'));
  elements.cancelNewTicketBtn.addEventListener('click', () => elements.newTicketModal.classList.add('hidden'));
  elements.createTicketForm.addEventListener('submit', handleCreateTicket);

  // Edit Ticket Modal (msa-y8zi)
  elements.editActiveTicketBtn.addEventListener('click', () => openEditTicketModal(state.activeTicket));
  elements.closeEditTicketModalBtn.addEventListener('click', () => elements.editTicketModal.classList.add('hidden'));
  elements.cancelEditTicketBtn.addEventListener('click', () => elements.editTicketModal.classList.add('hidden'));
  elements.editTicketForm.addEventListener('submit', handleEditTicketSubmit);

  // Detail Modal
  elements.closeDetailModalBtn.addEventListener('click', () => elements.detailModal.classList.add('hidden'));
  elements.detailModal.addEventListener('click', (e) => {
    if (e.target === elements.detailModal) elements.detailModal.classList.add('hidden');
  });

  document.getElementById('detailStatusSelect').addEventListener('change', async (e) => {
    if (!state.activeTicket) return;
    const newStatus = e.target.value;
    try {
      const res = await fetch('/api/tickets/status', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          directory: state.currentDir,
          ticket_id: state.activeTicket.id,
          status: newStatus
        })
      });
      if (!res.ok) throw new Error('Status update failed');
      showToast(`Status updated to ${newStatus}`, 'success');
      await fetchTickets();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('submitNoteBtn').addEventListener('click', submitReviewNote);
  document.getElementById('newNoteInput').addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      submitReviewNote();
    }
  });

  document.getElementById('addDepToggleBtn').addEventListener('click', () => {
    document.getElementById('addDepForm').classList.toggle('hidden');
  });
  document.getElementById('submitAddDepBtn').addEventListener('click', () => {
    const depInput = document.getElementById('newDepIdInput');
    const depId = depInput.value.trim();
    if (depId && state.activeTicket) {
      addDependency(state.activeTicket.id, depId);
      depInput.value = '';
      document.getElementById('addDepForm').classList.add('hidden');
    }
  });

  elements.initTicketsBtn.addEventListener('click', initRepository);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      elements.newTicketModal.classList.add('hidden');
      elements.editTicketModal.classList.add('hidden');
      elements.detailModal.classList.add('hidden');
      elements.folderModal.classList.add('hidden');
      elements.recentDirsPopover.classList.add('hidden');
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      elements.searchInput.focus();
    }
    if (e.key.toLowerCase() === 'n' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      e.preventDefault();
      openNewTicketModal();
    }
  });
}
