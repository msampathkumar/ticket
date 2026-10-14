// tk Web UI: main module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { showToast } from './utils.js';
import { initTheme, toggleTheme } from './theme.js';
import { renderRecentDirs, loadDirectory, openFolderBrowser, initRepository } from './directory.js';
import { setupAutoRefresh } from './autorefresh.js';
import { fetchTickets, addDependency, setTicketParent, addTicketLink } from './api.js';
import { filterTickets, switchView } from './views.js';
import { renderKanban, setupDragAndDrop } from './kanban.js';
import { updateTreeStatusSummary, renderTreeView, applyTreeZoom } from './graph.js';
import { toggleSection, openEditTicketModal, handleEditTicketSubmit, submitReviewNote, addTagToDetail } from './detail.js';
import { openNewTicketModal, handleCreateTicket } from './create.js';

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  setupEventListeners();
  setupDragAndDrop();
  setupAutoRefresh();

  try {
    const res = await fetch('/api/projects');
    if (res.ok) {
      const data = await res.json();
      if (data.projects && Array.isArray(data.projects)) {
        const localRecent = JSON.parse(localStorage.getItem('tk_recent_dirs') || '[]');
        const merged = [...new Set([...data.projects, ...localRecent])].slice(0, 8);
        state.recentDirs = merged;
        localStorage.setItem('tk_recent_dirs', JSON.stringify(merged));
      }
    }
  } catch (e) {
    console.error('Failed to load global projects', e);
  }

  // Initial project priority (tic-qiet): ?dir= URL param (keeps the user's switch on
  // reload), then the CLI launch directory (/api/config), then the last opened project, then '.'.
  let serverInitialDir = null;
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      const config = await res.json();
      serverInitialDir = config.initial_dir || null;
    }
  } catch (e) {
    console.error('Failed to load server config', e);
  }

  const urlParams = new URLSearchParams(window.location.search);
  const dirParam = urlParams.get('dir');
  const initialDir = dirParam || serverInitialDir || localStorage.getItem('tk_current_dir') || '.';

  elements.dirInput.value = initialDir;
  await loadDirectory(initialDir);
});

// SETUP EVENT LISTENERS
export function setupEventListeners() {
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

  const detailAddTagBtn = document.getElementById('detailAddTagBtn');
  if (detailAddTagBtn) {
    detailAddTagBtn.addEventListener('click', addTagToDetail);
  }
  const detailNewTagInput = document.getElementById('detailNewTagInput');
  if (detailNewTagInput) {
    detailNewTagInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addTagToDetail();
      }
    });
  }

  // Parent linking
  const detailToggleParentBtn = document.getElementById('detailToggleParentBtn');
  if (detailToggleParentBtn) {
    detailToggleParentBtn.addEventListener('click', () => {
      document.getElementById('detailSetParentForm').classList.toggle('hidden');
    });
  }
  const cancelSetParentBtn = document.getElementById('cancelSetParentBtn');
  if (cancelSetParentBtn) {
    cancelSetParentBtn.addEventListener('click', () => {
      document.getElementById('detailSetParentForm').classList.add('hidden');
    });
  }
  const submitSetParentBtn = document.getElementById('submitSetParentBtn');
  if (submitSetParentBtn) {
    submitSetParentBtn.addEventListener('click', () => {
      const parentSelect = document.getElementById('detailParentSelect');
      const parentId = parentSelect ? parentSelect.value : '';
      if (parentId && state.activeTicket) {
        setTicketParent(state.activeTicket.id, parentId);
        document.getElementById('detailSetParentForm').classList.add('hidden');
      }
    });
  }

  // Link child
  const linkChildToggleBtn = document.getElementById('linkChildToggleBtn');
  if (linkChildToggleBtn) {
    linkChildToggleBtn.addEventListener('click', () => {
      document.getElementById('linkChildForm').classList.toggle('hidden');
    });
  }
  const cancelLinkChildBtn = document.getElementById('cancelLinkChildBtn');
  if (cancelLinkChildBtn) {
    cancelLinkChildBtn.addEventListener('click', () => {
      document.getElementById('linkChildForm').classList.add('hidden');
    });
  }
  const submitLinkChildBtn = document.getElementById('submitLinkChildBtn');
  if (submitLinkChildBtn) {
    submitLinkChildBtn.addEventListener('click', () => {
      const childSelect = document.getElementById('linkChildSelect');
      const childId = childSelect ? childSelect.value : '';
      if (childId && state.activeTicket) {
        setTicketParent(childId, state.activeTicket.id);
        document.getElementById('linkChildForm').classList.add('hidden');
      }
    });
  }

  // Add subtask modal opener
  const addSubtaskModalBtn = document.getElementById('addSubtaskModalBtn');
  if (addSubtaskModalBtn) {
    addSubtaskModalBtn.addEventListener('click', () => {
      if (state.activeTicket) {
        openNewTicketModal('open', state.activeTicket.id);
      }
    });
  }

  // Add dependency
  const addDepToggleBtn = document.getElementById('addDepToggleBtn');
  if (addDepToggleBtn) {
    addDepToggleBtn.addEventListener('click', () => {
      document.getElementById('addDepForm').classList.toggle('hidden');
    });
  }
  const cancelAddDepBtn = document.getElementById('cancelAddDepBtn');
  if (cancelAddDepBtn) {
    cancelAddDepBtn.addEventListener('click', () => {
      document.getElementById('addDepForm').classList.add('hidden');
    });
  }
  const submitAddDepBtn = document.getElementById('submitAddDepBtn');
  if (submitAddDepBtn) {
    submitAddDepBtn.addEventListener('click', () => {
      const depSelect = document.getElementById('newDepSelect');
      const depId = depSelect ? depSelect.value.trim() : '';
      if (depId && state.activeTicket) {
        addDependency(state.activeTicket.id, depId);
        document.getElementById('addDepForm').classList.add('hidden');
      }
    });
  }

  // Related links
  const addLinkToggleBtn = document.getElementById('addLinkToggleBtn');
  if (addLinkToggleBtn) {
    addLinkToggleBtn.addEventListener('click', () => {
      document.getElementById('addLinkForm').classList.toggle('hidden');
    });
  }
  const cancelAddLinkBtn = document.getElementById('cancelAddLinkBtn');
  if (cancelAddLinkBtn) {
    cancelAddLinkBtn.addEventListener('click', () => {
      document.getElementById('addLinkForm').classList.add('hidden');
    });
  }
  const submitAddLinkBtn = document.getElementById('submitAddLinkBtn');
  if (submitAddLinkBtn) {
    submitAddLinkBtn.addEventListener('click', () => {
      const linkSelect = document.getElementById('newLinkSelect');
      const targetId = linkSelect ? linkSelect.value.trim() : '';
      if (targetId && state.activeTicket) {
        addTicketLink(state.activeTicket.id, targetId);
        document.getElementById('addLinkForm').classList.add('hidden');
      }
    });
  }

  elements.initTicketsBtn.addEventListener('click', initRepository);

  // Settings Modal (tic-6mex)
  function updateAccentButtons() {
    document.querySelectorAll('.accent-btn').forEach(btn => {
      if (btn.dataset.accent === state.accentColor) {
        btn.className = 'accent-btn flex flex-col items-center gap-1.5 p-2 rounded-xl border-2 border-brand-500 bg-brand-50/50 dark:bg-brand-950/40 shadow-sm';
      } else {
        btn.className = 'accent-btn flex flex-col items-center gap-1.5 p-2 rounded-xl border-2 border-transparent hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50 dark:bg-slate-800/50';
      }
    });
  }

  function openSettingsModal() {
    updateAccentButtons();
    if (elements.fontFamilySelect) elements.fontFamilySelect.value = state.fontFamily;
    if (elements.fontSizeSelect) elements.fontSizeSelect.value = state.fontSize;
    elements.highContrastToggle.checked = state.contrastHigh;
    elements.startDateFilter.value = state.startDateFilter;
    elements.endDateFilter.value = state.endDateFilter;
    elements.settingsModal.classList.remove('hidden');
    lucide.createIcons();
  }

  elements.settingsBtn.addEventListener('click', openSettingsModal);
  elements.closeSettingsModalBtn.addEventListener('click', () => elements.settingsModal.classList.add('hidden'));
  elements.saveSettingsBtn.addEventListener('click', () => elements.settingsModal.classList.add('hidden'));
  elements.settingsModal.addEventListener('click', (e) => {
    if (e.target === elements.settingsModal) elements.settingsModal.classList.add('hidden');
  });

  if (elements.fontFamilySelect) {
    elements.fontFamilySelect.addEventListener('change', (e) => {
      const font = e.target.value;
      state.fontFamily = font;
      localStorage.setItem('tk_font_family', font);
      initTheme();
      showToast(`Font family updated to ${e.target.options[e.target.selectedIndex].text}`, 'info');
    });
  }

  if (elements.fontSizeSelect) {
    elements.fontSizeSelect.addEventListener('change', (e) => {
      const size = e.target.value;
      state.fontSize = size;
      localStorage.setItem('tk_font_size', size);
      initTheme();
      showToast(`Font size updated to ${e.target.options[e.target.selectedIndex].text}`, 'info');
    });
  }

  document.querySelectorAll('.accent-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const accent = btn.dataset.accent;
      state.accentColor = accent;
      localStorage.setItem('tk_accent', accent);
      initTheme();
      updateAccentButtons();
      showToast(`Accent color updated to ${accent}`, 'info');
    });
  });

  elements.highContrastToggle.addEventListener('change', (e) => {
    state.contrastHigh = e.target.checked;
    localStorage.setItem('tk_contrast_high', state.contrastHigh ? 'true' : 'false');
    initTheme();
    showToast(`High contrast ${state.contrastHigh ? 'enabled' : 'disabled'}`, 'info');
  });

  elements.startDateFilter.addEventListener('change', (e) => {
    state.startDateFilter = e.target.value;
    localStorage.setItem('tk_filter_start_date', state.startDateFilter);
    filterTickets();
  });

  elements.endDateFilter.addEventListener('change', (e) => {
    state.endDateFilter = e.target.value;
    localStorage.setItem('tk_filter_end_date', state.endDateFilter);
    filterTickets();
  });

  elements.clearDateFilterBtn.addEventListener('click', () => {
    state.startDateFilter = '';
    state.endDateFilter = '';
    elements.startDateFilter.value = '';
    elements.endDateFilter.value = '';
    localStorage.removeItem('tk_filter_start_date');
    localStorage.removeItem('tk_filter_end_date');
    filterTickets();
    showToast('Date range filter reset', 'info');
  });

  elements.resetSettingsBtn.addEventListener('click', () => {
    state.accentColor = 'indigo';
    state.fontFamily = 'sans';
    state.fontSize = 'md';
    state.contrastHigh = false;
    state.startDateFilter = '';
    state.endDateFilter = '';
    localStorage.removeItem('tk_accent');
    localStorage.removeItem('tk_font_family');
    localStorage.removeItem('tk_font_size');
    localStorage.removeItem('tk_contrast_high');
    localStorage.removeItem('tk_filter_start_date');
    localStorage.removeItem('tk_filter_end_date');
    if (elements.fontFamilySelect) elements.fontFamilySelect.value = 'sans';
    if (elements.fontSizeSelect) elements.fontSizeSelect.value = 'md';
    elements.highContrastToggle.checked = false;
    elements.startDateFilter.value = '';
    elements.endDateFilter.value = '';
    initTheme();
    updateAccentButtons();
    filterTickets();
    showToast('Settings restored to defaults', 'success');
  });

  // Tree Orientation & Collapse Controls (tic-d04l)
  elements.treeOrientationBtn.addEventListener('click', () => {
    state.treeOrientation = state.treeOrientation === 'vertical' ? 'horizontal' : 'vertical';
    localStorage.setItem('tk_tree_orientation', state.treeOrientation);
    renderTreeView();
    showToast(`Mind Map oriented ${state.treeOrientation === 'horizontal' ? 'Left-to-Right' : 'Top-Down'}`, 'info');
  });

  elements.treeCollapseAllBtn.addEventListener('click', () => {
    // Find all tickets that have children
    const parentIds = new Set();
    state.filteredTickets.forEach(t => {
      if (t.parent) parentIds.add(t.parent);
    });

    if (state.collapsedNodes.size >= parentIds.size && parentIds.size > 0) {
      // Expand all
      state.collapsedNodes.clear();
      elements.treeCollapseAllLabel.textContent = 'Collapse All';
      showToast('Expanded all subtrees', 'info');
    } else {
      // Collapse all
      parentIds.forEach(id => state.collapsedNodes.add(id));
      elements.treeCollapseAllLabel.textContent = 'Expand All';
      showToast('Collapsed all subtrees', 'info');
    }
    localStorage.setItem('tk_tree_collapsed', JSON.stringify([...state.collapsedNodes]));
    renderTreeView();
  });

  document.getElementById('addSubtaskModalBtn')?.addEventListener('click', () => {
    if (state.activeTicket) {
      openNewTicketModal('open', state.activeTicket.id);
    }
  });

  // Tree Status Multi-Select Filter (tic-s0le)
  function syncTreeStatusCheckboxes() {
    if (elements.treeStatusReady) elements.treeStatusReady.checked = state.treeStatusFilter.has('ready');
    if (elements.treeStatusInProgress) elements.treeStatusInProgress.checked = state.treeStatusFilter.has('in_progress');
    if (elements.treeStatusBlocked) elements.treeStatusBlocked.checked = state.treeStatusFilter.has('blocked');
    if (elements.treeStatusClosed) elements.treeStatusClosed.checked = state.treeStatusFilter.has('closed');
    updateTreeStatusSummary();
  }
  syncTreeStatusCheckboxes();

  elements.treeStatusFilterBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    elements.treeStatusFilterMenu?.classList.toggle('hidden');
  });

  document.addEventListener('click', (e) => {
    if (elements.treeStatusFilterMenu && !elements.treeStatusFilterMenu.contains(e.target) && !elements.treeStatusFilterBtn?.contains(e.target)) {
      elements.treeStatusFilterMenu.classList.add('hidden');
    }
  });

  [
    elements.treeStatusReady,
    elements.treeStatusInProgress,
    elements.treeStatusBlocked,
    elements.treeStatusClosed
  ].forEach(cb => {
    cb?.addEventListener('change', () => {
      const val = cb.value;
      if (cb.checked) {
        state.treeStatusFilter.add(val);
      } else {
        state.treeStatusFilter.delete(val);
      }
      localStorage.setItem('tk_tree_status_filter', JSON.stringify([...state.treeStatusFilter]));
      updateTreeStatusSummary();
      renderTreeView();
    });
  });

  // Tree Zoom Controls (tic-d04l)
  elements.treeZoomInBtn.addEventListener('click', () => {
    state.treeZoom = Math.min(2.0, state.treeZoom + 0.15);
    applyTreeZoom();
  });
  elements.treeZoomOutBtn.addEventListener('click', () => {
    state.treeZoom = Math.max(0.4, state.treeZoom - 0.15);
    applyTreeZoom();
  });
  elements.treeResetZoomBtn.addEventListener('click', () => {
    state.treeZoom = 1.0;
    applyTreeZoom();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      elements.newTicketModal.classList.add('hidden');
      elements.editTicketModal.classList.add('hidden');
      elements.detailModal.classList.add('hidden');
      elements.folderModal.classList.add('hidden');
      elements.recentDirsPopover.classList.add('hidden');
      elements.settingsModal.classList.add('hidden');
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

// Inline onclick handlers in index.html call these by name; module scope is not global.
window.openNewTicketModal = openNewTicketModal;
window.toggleSection = toggleSection;
