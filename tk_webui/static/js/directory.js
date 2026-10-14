// tk Web UI: directory module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, showToast } from './utils.js';
import { recordTicketsVersion } from './autorefresh.js';
import { fetchTickets } from './api.js';
import { updateStats, hideAllViews, switchView } from './views.js';

export function addRecentDir(dir) {
  if (!dir) return;
  state.recentDirs = [dir, ...state.recentDirs.filter(d => d !== dir)].slice(0, 8);
  localStorage.setItem('tk_recent_dirs', JSON.stringify(state.recentDirs));
  renderRecentDirs();
  fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: dir })
  }).catch(() => {});
}

export function renderRecentDirs() {
  elements.recentDirsList.innerHTML = '';
  if (state.recentDirs.length === 0) {
    elements.recentDirsList.innerHTML = '<div class="text-xs text-slate-400 p-2">No recent projects</div>';
    return;
  }
  state.recentDirs.forEach(dir => {
    const item = document.createElement('button');
    item.className = 'w-full text-left px-2.5 py-1.5 text-xs rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 truncate font-mono text-slate-700 dark:text-slate-300 flex items-center gap-2';
    item.innerHTML = `<i data-lucide="folder" class="w-3.5 h-3.5 shrink-0 text-slate-400"></i> <span class="truncate">${escapeHtml(dir)}</span>`;
    item.onclick = () => {
      elements.recentDirsPopover.classList.add('hidden');
      elements.dirInput.value = dir;
      loadDirectory(dir);
    };
    elements.recentDirsList.appendChild(item);
  });
  lucide.createIcons();
}

export async function loadDirectory(path) {
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
    await recordTicketsVersion(data.path);

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

// FOLDER BROWSER
export async function openFolderBrowser(path = '~') {
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
          <span class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">${escapeHtml(item.name)}</span>
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

export async function initRepository() {
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
