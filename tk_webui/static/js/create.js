// tk Web UI: create module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { showToast } from './utils.js';
import { fetchTickets } from './api.js';

// CREATE TICKET
export function openNewTicketModal(status = 'open', prefillParent = '') {
  elements.createTicketForm.reset();
  if (prefillParent) {
    document.getElementById('newTicketParent').value = prefillParent;
  }
  elements.newTicketModal.classList.remove('hidden');
  document.getElementById('newTicketTitle').focus();
  lucide.createIcons();
}

export async function handleCreateTicket(e) {
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
