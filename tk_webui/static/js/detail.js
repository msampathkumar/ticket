// tk Web UI: detail module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, renderMarkdown, showToast, getPriorityBadge, getTypeBadge, getStatusBadge } from './utils.js';
import { fetchTickets, removeDependency, setTicketParent, removeTicketLink, updateTicketTagsApi } from './api.js';

export function toggleSection(contentId, headerEl) {
  const content = document.getElementById(contentId);
  const chevron = headerEl.querySelector('.section-chevron');
  if (!content) return;
  if (content.classList.contains('hidden')) {
    content.classList.remove('hidden');
    if (chevron) chevron.style.transform = 'rotate(0deg)';
  } else {
    content.classList.add('hidden');
    if (chevron) chevron.style.transform = 'rotate(-90deg)';
  }
}

export function setSectionState(contentId, expanded) {
  const content = document.getElementById(contentId);
  if (!content) return;
  const headerEl = content.previousElementSibling || (content.parentElement ? content.parentElement.querySelector('.cursor-pointer') : null);
  const chevron = headerEl ? headerEl.querySelector('.section-chevron') : null;
  if (expanded) {
    content.classList.remove('hidden');
    if (chevron) chevron.style.transform = 'rotate(0deg)';
  } else {
    content.classList.add('hidden');
    if (chevron) chevron.style.transform = 'rotate(-90deg)';
  }
}

// DETAIL MODAL
export function openDetailModal(ticket) {
  state.activeTicket = ticket;

  const idEl = document.getElementById('detailId');
  idEl.textContent = ticket.id;
  idEl.className = 'font-mono text-xs font-bold text-brand-600 dark:text-brand-400 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-lg';

  document.getElementById('detailTypeContainer').innerHTML = getTypeBadge(ticket.type);
  document.getElementById('detailPriorityContainer').innerHTML = getPriorityBadge(ticket.priority);

  document.getElementById('detailStatusSelect').value = ticket.status;
  document.getElementById('detailTitle').textContent = ticket.title;
  document.getElementById('detailAssignee').textContent = ticket.assignee || 'Unassigned';
  document.getElementById('detailCreated').textContent = ticket.created ? new Date(ticket.created).toLocaleString() : 'Recently';

  const tagsContainer = document.getElementById('detailTagsContainer');
  tagsContainer.innerHTML = (ticket.tags || []).map(t => 
    `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
       <span>#${escapeHtml(t)}</span>
       <button data-remove-tag="${escapeHtml(t)}" class="detail-remove-tag text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 p-0.5 rounded" title="Remove tag">
         <i data-lucide="x" class="w-3 h-3"></i>
       </button>
     </span>`
  ).join('');
  tagsContainer.querySelectorAll('.detail-remove-tag').forEach(btn => {
    btn.addEventListener('click', () => removeTagFromDetail(btn.dataset.removeTag));
  });

  const blockedAlert = document.getElementById('detailBlockedAlert');
  const blockedList = document.getElementById('detailBlockedList');
  if (ticket.is_blocked && ticket.blocked_by.length > 0) {
    blockedAlert.classList.remove('hidden');
    blockedList.innerHTML = ticket.blocked_by.map(b => `<span class="px-2 py-0.5 bg-rose-200/80 dark:bg-rose-900 rounded">${escapeHtml(b)}</span>`).join('');
  } else {
    blockedAlert.classList.add('hidden');
  }

  const descEl = document.getElementById('detailDescription');
  descEl.innerHTML = ticket.description ? renderMarkdown(ticket.description) : '<p class="text-slate-400 italic">No description provided.</p>';

  if (ticket.design) {
    document.getElementById('detailDesign').innerHTML = renderMarkdown(ticket.design);
    setSectionState('detailDesignContent', true);
  } else {
    document.getElementById('detailDesign').innerHTML = '';
    setSectionState('detailDesignContent', false);
  }

  if (ticket.acceptance) {
    document.getElementById('detailAcceptance').innerHTML = renderMarkdown(ticket.acceptance);
    setSectionState('detailAcceptanceContent', true);
  } else {
    document.getElementById('detailAcceptance').innerHTML = '';
    setSectionState('detailAcceptanceContent', false);
  }

  renderDetailParent(ticket);
  setSectionState('detailParentContent', !!ticket.parent);

  renderDetailSubtasks(ticket);
  const subtasksCount = state.tickets.filter(t => t.parent === ticket.id).length;
  setSectionState('detailSubtasksContent', subtasksCount > 0);

  renderDetailDependencies(ticket);
  setSectionState('detailDepsContent', ticket.deps && ticket.deps.length > 0);

  renderDetailLinks(ticket);
  setSectionState('detailLinksContent', ticket.links && ticket.links.length > 0);

  renderDetailNotes(ticket);
  setSectionState('detailNotesContent', ticket.notes && ticket.notes.length > 0);

  elements.detailModal.classList.remove('hidden');
  lucide.createIcons();
}

export function getDescendantIds(ticketId) {
  const descendants = new Set();
  const queue = [ticketId];
  while (queue.length > 0) {
    const curr = queue.shift();
    for (const t of state.tickets) {
      if (t.parent === curr && !descendants.has(t.id)) {
        descendants.add(t.id);
        queue.push(t.id);
      }
    }
  }
  return descendants;
}

export function getAncestorIds(ticketId) {
  const ancestors = new Set();
  let curr = state.tickets.find(t => t.id === ticketId);
  while (curr && curr.parent) {
    if (ancestors.has(curr.parent)) break;
    ancestors.add(curr.parent);
    curr = state.tickets.find(t => t.id === curr.parent);
  }
  return ancestors;
}

export function renderDetailParent(ticket) {
  const parentDisplay = document.getElementById('detailParentDisplay');
  const parentSelect = document.getElementById('detailParentSelect');
  const toggleBtnLabel = document.getElementById('detailToggleParentLabel');
  const parentForm = document.getElementById('detailSetParentForm');
  if (parentForm) parentForm.classList.add('hidden');

  // Populate Parent dropdown with available candidates
  const descendants = getDescendantIds(ticket.id);
  const availableParents = state.tickets.filter(t => t.id !== ticket.id && !descendants.has(t.id) && t.id !== ticket.parent);
  
  if (parentSelect) {
    parentSelect.innerHTML = '<option value="">-- Select Parent Ticket --</option>' +
      availableParents.map(t => `<option value="${escapeHtml(t.id)}">[${escapeHtml(t.id)}] ${escapeHtml(t.title)} (${escapeHtml(t.status)})</option>`).join('');
  }

  if (ticket.parent) {
    const parentTicket = state.tickets.find(t => t.id === ticket.parent);
    if (toggleBtnLabel) toggleBtnLabel.textContent = 'Change Parent';
    if (parentTicket) {
      parentDisplay.innerHTML = `
        <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-brand-500 transition group cursor-pointer detail-open-parent">
          <div class="flex items-center gap-2 truncate">
            <span class="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(parentTicket.id)}</span>
            <span class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">${escapeHtml(parentTicket.title)}</span>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            ${getStatusBadge(parentTicket.status, parentTicket.is_blocked)}
            <button title="Unlink Parent" class="p-1 text-slate-400 hover:text-rose-500 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition detail-unlink-parent">
              <i data-lucide="unlink" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
    } else {
      parentDisplay.innerHTML = `
        <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80">
          <span class="font-mono text-xs text-slate-500">${escapeHtml(ticket.parent)} (unresolved parent)</span>
          <button title="Unlink Parent" class="p-1 text-slate-400 hover:text-rose-500 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition detail-unlink-parent">
            <i data-lucide="unlink" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
    }
    const openParentEl = parentDisplay.querySelector('.detail-open-parent');
    if (openParentEl) {
      openParentEl.addEventListener('click', () => openDetailModal(parentTicket));
    }
    const unlinkParentBtn = parentDisplay.querySelector('.detail-unlink-parent');
    if (unlinkParentBtn) {
      unlinkParentBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        setTicketParent(ticket.id, '');
      });
    }
  } else {
    if (toggleBtnLabel) toggleBtnLabel.textContent = 'Set Parent';
    parentDisplay.innerHTML = '<span class="text-slate-400 text-xs italic">No parent ticket (Root-level task).</span>';
  }
  lucide.createIcons();
}

export function renderDetailSubtasks(ticket) {
  const container = document.getElementById('detailSubtasksList');
  const linkChildForm = document.getElementById('linkChildForm');
  const linkChildSelect = document.getElementById('linkChildSelect');
  if (linkChildForm) linkChildForm.classList.add('hidden');

  if (!container) return;
  container.innerHTML = '';

  // Populate linkChildSelect with candidate children
  const ancestors = getAncestorIds(ticket.id);
  const candidateChildren = state.tickets.filter(t => t.id !== ticket.id && !ancestors.has(t.id) && t.parent !== ticket.id);
  if (linkChildSelect) {
    linkChildSelect.innerHTML = '<option value="">-- Select Existing Ticket to Link as Child --</option>' +
      candidateChildren.map(t => `<option value="${escapeHtml(t.id)}">[${escapeHtml(t.id)}] ${escapeHtml(t.title)} (${escapeHtml(t.status)})</option>`).join('');
  }

  const subtasks = state.tickets.filter(t => t.parent === ticket.id);
  if (subtasks.length === 0) {
    container.innerHTML = '<span class="text-slate-400 text-xs italic">No subtasks created for this ticket.</span>';
    lucide.createIcons();
    return;
  }

  subtasks.forEach(st => {
    const item = document.createElement('div');
    item.className = 'flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-brand-500 cursor-pointer transition';
    item.innerHTML = `
      <div class="flex items-center gap-2 truncate">
        <span class="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(st.id)}</span>
        <span class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">${escapeHtml(st.title)}</span>
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        ${getStatusBadge(st.status, st.is_blocked)}
        ${getPriorityBadge(st.priority)}
        <button title="Unlink Child" class="p-1 text-slate-400 hover:text-rose-500 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition ml-1 detail-unlink-child">
          <i data-lucide="unlink" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;
    item.querySelector('.detail-unlink-child').addEventListener('click', (e) => {
      e.stopPropagation();
      setTicketParent(st.id, '');
    });
    item.onclick = () => {
      openDetailModal(st);
    };
    container.appendChild(item);
  });
  lucide.createIcons();
}

export function renderDetailDependencies(ticket) {
  const depsList = document.getElementById('detailDepsList');
  const depSelect = document.getElementById('newDepSelect');
  const depForm = document.getElementById('addDepForm');
  if (depForm) depForm.classList.add('hidden');

  depsList.innerHTML = '';

  // Populate candidate dependencies
  const currentDeps = new Set(ticket.deps || []);
  const candidateDeps = state.tickets.filter(t => t.id !== ticket.id && !currentDeps.has(t.id));
  if (depSelect) {
    depSelect.innerHTML = '<option value="">-- Select Blocker / Dependency Ticket --</option>' +
      candidateDeps.map(t => `<option value="${escapeHtml(t.id)}">[${escapeHtml(t.id)}] ${escapeHtml(t.title)} (${escapeHtml(t.status)})</option>`).join('');
  }

  if (ticket.deps && ticket.deps.length > 0) {
    ticket.deps.forEach(depId => {
      const depBadge = document.createElement('div');
      depBadge.className = 'flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700';
      depBadge.innerHTML = `
        <i data-lucide="git-commit" class="w-3 h-3 text-slate-400"></i>
        <span>${escapeHtml(depId)}</span>
        <button title="Remove dependency" class="detail-remove-dep text-slate-400 hover:text-rose-500 ml-1 p-0.5">
          <i data-lucide="x" class="w-3 h-3"></i>
        </button>
      `;
      depBadge.querySelector('.detail-remove-dep').addEventListener('click', () => removeDependency(ticket.id, depId));
      depsList.appendChild(depBadge);
    });
  } else {
    depsList.innerHTML = '<span class="text-slate-400 text-xs italic">No dependencies</span>';
  }
  lucide.createIcons();
}

export function renderDetailLinks(ticket) {
  const linksList = document.getElementById('detailLinksList');
  const linkSelect = document.getElementById('newLinkSelect');
  const linkForm = document.getElementById('addLinkForm');
  if (linkForm) linkForm.classList.add('hidden');

  if (!linksList) return;
  linksList.innerHTML = '';

  const currentLinks = new Set(ticket.links || []);
  const candidateLinks = state.tickets.filter(t => t.id !== ticket.id && !currentLinks.has(t.id));
  if (linkSelect) {
    linkSelect.innerHTML = '<option value="">-- Select Related Ticket --</option>' +
      candidateLinks.map(t => `<option value="${escapeHtml(t.id)}">[${escapeHtml(t.id)}] ${escapeHtml(t.title)} (${escapeHtml(t.status)})</option>`).join('');
  }

  if (ticket.links && ticket.links.length > 0) {
    ticket.links.forEach(linkId => {
      const linkBadge = document.createElement('div');
      linkBadge.className = 'flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700';
      linkBadge.innerHTML = `
        <i data-lucide="link-2" class="w-3 h-3 text-indigo-500"></i>
        <span>${escapeHtml(linkId)}</span>
        <button title="Remove link" class="detail-remove-link text-slate-400 hover:text-rose-500 ml-1 p-0.5">
          <i data-lucide="x" class="w-3 h-3"></i>
        </button>
      `;
      linkBadge.querySelector('.detail-remove-link').addEventListener('click', () => removeTicketLink(ticket.id, linkId));
      linksList.appendChild(linkBadge);
    });
  } else {
    linksList.innerHTML = '<span class="text-slate-400 text-xs italic">No related links</span>';
  }
  lucide.createIcons();
}

export function renderDetailNotes(ticket) {
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
        <span class="font-mono text-[11px]">${escapeHtml(formattedTime)}</span>
      </div>
      <div class="prose dark:prose-invert text-xs text-slate-800 dark:text-slate-200 pt-1">
        ${renderMarkdown(n.text)}
      </div>
    `;
    notesFeed.appendChild(item);
  });
}

// EDIT TICKET MODAL HANDLERS (msa-y8zi)
export function openEditTicketModal(ticket) {
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

export async function handleEditTicketSubmit(e) {
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
export async function submitReviewNote() {
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

// TAG ACTIONS
export async function addTagToDetail() {
  if (!state.activeTicket) return;
  const input = document.getElementById('detailNewTagInput');
  const newTag = input.value.trim().replace(/^#/, '');
  if (!newTag) return;

  const currentTags = state.activeTicket.tags || [];
  if (currentTags.includes(newTag)) {
    showToast('Tag already exists on ticket', 'info');
    input.value = '';
    return;
  }

  const updatedTags = [...currentTags, newTag];
  await updateTicketTagsApi(updatedTags);
  input.value = '';
}

export async function removeTagFromDetail(tagToRemove) {
  if (!state.activeTicket) return;
  const currentTags = state.activeTicket.tags || [];
  const updatedTags = currentTags.filter(t => t !== tagToRemove);
  await updateTicketTagsApi(updatedTags);
}
