// tk Web UI: autorefresh module (split from app.js, tic-4h0q).
import { state, POLL_INTERVAL_MS, elements } from './state.js';
import { loadDirectory } from './directory.js';
import { fetchTickets } from './api.js';

// AUTO-REFRESH (tic-da9d): poll a cheap fingerprint of .tickets/*.md while the tab
// is visible and refetch only when it changes, so CLI/agent edits appear live.
export function setupAutoRefresh() {
  setInterval(pollTicketsVersion, POLL_INTERVAL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') pollTicketsVersion();
  });
}

// Defer refreshes while the user is mid-edit or mid-drag; retried on the next tick.
export function isUserBusy() {
  return state.isDragging ||
    !elements.editTicketModal.classList.contains('hidden') ||
    !elements.newTicketModal.classList.contains('hidden');
}

export async function fetchTicketsVersion(dir) {
  const res = await fetch(`/api/tickets/version?directory=${encodeURIComponent(dir)}`);
  if (!res.ok) throw new Error('Failed to read tickets version');
  return (await res.json()).version;
}

// Called by loadDirectory() before it fetches tickets, so no change is missed in between.
export async function recordTicketsVersion(dir) {
  try {
    state.ticketsVersion = await fetchTicketsVersion(dir);
    state.ticketsVersionDir = dir;
  } catch (e) {
    state.ticketsVersionDir = null; // the next poll records it
  }
}

export async function pollTicketsVersion() {
  if (document.visibilityState !== 'visible' || !state.currentDir || state.pollInFlight) return;
  state.pollInFlight = true;
  try {
    const dir = state.currentDir;
    const version = await fetchTicketsVersion(dir);
    if (dir !== state.currentDir) return;

    if (state.ticketsVersionDir !== dir) {
      state.ticketsVersionDir = dir;
      state.ticketsVersion = version;
      return;
    }
    if (version === state.ticketsVersion || isUserBusy()) return;

    const hadTickets = state.ticketsVersion !== null;
    state.ticketsVersion = version;
    if (!hadTickets || version === null) {
      await loadDirectory(dir); // .tickets appeared or vanished: refresh banner and views
    } else {
      await fetchTickets();
    }
  } catch (e) {
    // Server unreachable: stay quiet and retry on the next tick.
  } finally {
    state.pollInFlight = false;
  }
}
