// tk Web UI: api module (split from app.js, tic-4h0q).
import { state } from './state.js';
import { showToast } from './utils.js';
import { filterTickets } from './views.js';
import { openDetailModal, renderDetailDependencies, renderDetailLinks } from './detail.js';

export async function fetchTickets() {
  try {
    const res = await fetch(`/api/tickets?directory=${encodeURIComponent(state.currentDir)}`);
    if (!res.ok) throw new Error('Failed to load tickets');
    state.tickets = await res.json();
    filterTickets();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// DEPENDENCY ACTIONS
export async function addDependency(ticketId, depId) {
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

export async function removeDependency(ticketId, depId) {
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

// PARENT AND LINK ACTIONS
export async function setTicketParent(ticketId, parentId) {
  try {
    const res = await fetch('/api/tickets', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: ticketId,
        parent: parentId || ''
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update parent');
    }

    showToast(parentId ? `Linked parent ${parentId} to ${ticketId}` : `Unlinked parent for ${ticketId}`, 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === (state.activeTicket ? state.activeTicket.id : ticketId));
    if (updated) {
      openDetailModal(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

export async function addTicketLink(ticketId, targetId) {
  try {
    const res = await fetch('/api/tickets/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: ticketId,
        target_id: targetId
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add link');
    }

    showToast(`Linked ${ticketId} <-> ${targetId}`, 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === ticketId);
    if (updated) {
      state.activeTicket = updated;
      renderDetailLinks(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

export async function removeTicketLink(ticketId, targetId) {
  try {
    const res = await fetch('/api/tickets/links', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: ticketId,
        target_id: targetId
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to remove link');
    }

    showToast(`Unlinked ${ticketId} <-> ${targetId}`, 'success');
    await fetchTickets();

    const updated = state.tickets.find(t => t.id === ticketId);
    if (updated) {
      state.activeTicket = updated;
      renderDetailLinks(updated);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

export async function updateTicketTagsApi(newTags) {
  try {
    const res = await fetch('/api/tickets', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        directory: state.currentDir,
        ticket_id: state.activeTicket.id,
        tags: newTags
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update tags');
    }
    await fetchTickets();
    const updated = state.tickets.find(t => t.id === state.activeTicket.id);
    if (updated) {
      openDetailModal(updated);
    }
    showToast('Tags updated successfully', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}
