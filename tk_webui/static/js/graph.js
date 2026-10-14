// tk Web UI: graph module (split from app.js, tic-4h0q).
import { state, elements } from './state.js';
import { escapeHtml, getPriorityBadge, getTypeBadge, getStatusBadge } from './utils.js';
import { openDetailModal } from './detail.js';
import { openNewTicketModal } from './create.js';

// 3. RENDER TREE / DEPENDENCY GRAPH VIEW (tic-d04l & tic-s0le)
export function updateTreeStatusSummary() {
  if (!elements.treeStatusFilterSummary) return;
  const s = state.treeStatusFilter;
  if (s.size === 4) {
    elements.treeStatusFilterSummary.textContent = 'All';
  } else if (s.size === 0) {
    elements.treeStatusFilterSummary.textContent = 'None';
  } else if (s.has('ready') && s.has('in_progress') && s.has('blocked') && !s.has('closed')) {
    elements.treeStatusFilterSummary.textContent = 'Active';
  } else {
    elements.treeStatusFilterSummary.textContent = `${s.size} sel`;
  }
}

export function renderTreeView() {
  elements.treeContainer.innerHTML = '';
  elements.treeSvgEdges.innerHTML = '';

  const isHorizontal = state.treeOrientation === 'horizontal';
  elements.treeOrientationLabel.textContent = isHorizontal ? 'Left-to-Right' : 'Top-Down';
  updateTreeStatusSummary();

  // Filter tickets by selected statuses (tic-s0le)
  const tickets = state.filteredTickets.filter(t => {
    let category = 'ready';
    if (t.status === 'closed') category = 'closed';
    else if (t.is_blocked) category = 'blocked';
    else if (t.status === 'in_progress') category = 'in_progress';
    else category = 'ready';
    return state.treeStatusFilter.has(category);
  });

  const projectName = state.currentDir.split('/').filter(Boolean).pop() || 'Project';

  // Build hierarchy and dependency index
  const ticketMap = new Map();
  const childrenMap = new Map(); // parentId -> [childTicket]
  const topLevel = [];
  const parentIds = new Set();

  tickets.forEach(t => {
    ticketMap.set(t.id, t);
    if (t.parent) parentIds.add(t.parent);
  });

  const isAllCollapsed = parentIds.size > 0 && state.collapsedNodes.size >= parentIds.size;

  function createRootNode(pos) {
    const rootNode = document.createElement('div');
    rootNode.className = 'graph-node-card graph-root-node flex items-center justify-between gap-3 px-4 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-2xl shadow-xl font-bold text-sm tracking-wide border-2 border-white/20 dark:border-slate-800 transition select-none';
    rootNode.style.left = `${pos.x}px`;
    rootNode.style.top = `${pos.y}px`;

    rootNode.innerHTML = `
      <div class="flex items-center gap-2 min-w-0 flex-1 mr-1">
        <span class="p-1 bg-white/20 rounded-lg shrink-0"><i data-lucide="folder-git-2" class="w-4 h-4"></i></span>
        <span class="truncate font-bold text-sm tracking-wide" title="${escapeHtml(projectName)}">${escapeHtml(projectName)}</span>
      </div>
      <div class="flex items-center gap-1.5 shrink-0">
        <button class="root-add-task-btn p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white transition shrink-0" title="Create new task">
          <i data-lucide="plus" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;

    rootNode.addEventListener('click', (e) => {
      const addBtn = e.target.closest('.root-add-task-btn');
      if (addBtn) {
        e.stopPropagation();
        openNewTicketModal('open');
        return;
      }
      openNewTicketModal('open');
    });

    return rootNode;
  }

  tickets.forEach(t => {
    if (t.parent && ticketMap.has(t.parent)) {
      if (!childrenMap.has(t.parent)) childrenMap.set(t.parent, []);
      childrenMap.get(t.parent).push(t);
    } else {
      topLevel.push(t);
    }
  });

  const CARD_WIDTH = 270;
  const CARD_HEIGHT = 135;
  const posMap = new Map(); // ticketId -> { x, y }

  if (!isHorizontal) {
    // -------------------------------------------------------------
    // VERTICAL (TOP-DOWN) LAYOUT
    // -------------------------------------------------------------
    const HORIZONTAL_GAP = 50;
    const VERTICAL_GAP = 175;

    function getSubtreeWidth(ticket) {
      if (state.collapsedNodes.has(ticket.id)) {
        return CARD_WIDTH + HORIZONTAL_GAP;
      }
      const children = childrenMap.get(ticket.id) || [];
      if (children.length === 0) return CARD_WIDTH + HORIZONTAL_GAP;
      let sum = 0;
      children.forEach(c => { sum += getSubtreeWidth(c); });
      return Math.max(CARD_WIDTH + HORIZONTAL_GAP, sum);
    }

    let totalTopWidth = 0;
    topLevel.forEach(t => { totalTopWidth += getSubtreeWidth(t); });

    const canvasWidth = Math.max(1200, totalTopWidth + 200);
    let currentX = (canvasWidth - totalTopWidth) / 2;
    const rootPos = { x: canvasWidth / 2, y: topLevel.length === 0 ? 140 : 55 };

    let maxDepth = 1;

    function layoutVertical(ticket, leftX, tier) {
      if (tier > maxDepth) maxDepth = tier;
      const branchWidth = getSubtreeWidth(ticket);
      const x = leftX + branchWidth / 2;
      const y = 55 + tier * VERTICAL_GAP;
      posMap.set(ticket.id, { x, y });

      if (state.collapsedNodes.has(ticket.id)) return;

      const children = childrenMap.get(ticket.id) || [];
      let childLeftX = leftX;
      children.forEach(c => {
        layoutVertical(c, childLeftX, tier + 1);
        childLeftX += getSubtreeWidth(c);
      });
    }

    topLevel.forEach(t => {
      const branchWidth = getSubtreeWidth(t);
      layoutVertical(t, currentX, 1);
      currentX += branchWidth;
    });

    const canvasHeight = Math.max(650, 55 + (maxDepth + 1) * VERTICAL_GAP + 100);

    elements.treeSvgLayer.setAttribute('width', canvasWidth);
    elements.treeSvgLayer.setAttribute('height', canvasHeight);
    elements.treeSvgLayer.style.width = `${canvasWidth}px`;
    elements.treeSvgLayer.style.height = `${canvasHeight}px`;
    elements.treeContainer.style.width = `${canvasWidth}px`;
    elements.treeContainer.style.height = `${canvasHeight}px`;

    // Root Node
    const rootNode = createRootNode(rootPos);
    elements.treeContainer.appendChild(rootNode);

    if (tickets.length === 0) {
      const emptyHint = document.createElement('div');
      emptyHint.className = 'graph-empty-hint flex flex-col items-center justify-center text-slate-400 text-xs gap-1 pointer-events-none text-center';
      emptyHint.style.left = `${rootPos.x}px`;
      emptyHint.style.top = `${rootPos.y + 60}px`;
      emptyHint.style.transform = 'translate(-50%, 0)';
      emptyHint.innerHTML = `
        <p class="font-medium text-slate-500 dark:text-slate-400">No tasks match current filters</p>
        <p class="text-[11px] text-slate-400">Click <span class="font-semibold text-brand-600 dark:text-brand-400">+</span> on <span class="font-semibold text-slate-700 dark:text-slate-300">${escapeHtml(projectName)}</span> to create a task</p>
      `;
      elements.treeContainer.appendChild(emptyHint);
    }

    // Hierarchy Lines
    topLevel.forEach(t => {
      const p = posMap.get(t.id);
      if (!p) return;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M ${rootPos.x} ${rootPos.y + 25} C ${rootPos.x} ${(rootPos.y + p.y) / 2}, ${p.x} ${(rootPos.y + p.y) / 2}, ${p.x} ${p.y - 50}`);
      path.setAttribute('class', 'graph-edge');
      elements.treeSvgEdges.appendChild(path);
    });

    childrenMap.forEach((children, parentId) => {
      if (state.collapsedNodes.has(parentId)) return;
      const parentPos = posMap.get(parentId);
      if (!parentPos) return;
      children.forEach(c => {
        const childPos = posMap.get(c.id);
        if (!childPos) return;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M ${parentPos.x} ${parentPos.y + 50} C ${parentPos.x} ${(parentPos.y + childPos.y) / 2}, ${childPos.x} ${(parentPos.y + childPos.y) / 2}, ${childPos.x} ${childPos.y - 50}`);
        path.setAttribute('class', 'graph-edge');
        elements.treeSvgEdges.appendChild(path);
      });
    });

  } else {
    // -------------------------------------------------------------
    // HORIZONTAL (LEFT-TO-RIGHT) LAYOUT
    // -------------------------------------------------------------
    const VERTICAL_GAP = 35;
    const HORIZONTAL_GAP = 330;

    function getSubtreeHeight(ticket) {
      if (state.collapsedNodes.has(ticket.id)) {
        return CARD_HEIGHT + VERTICAL_GAP;
      }
      const children = childrenMap.get(ticket.id) || [];
      if (children.length === 0) return CARD_HEIGHT + VERTICAL_GAP;
      let sum = 0;
      children.forEach(c => { sum += getSubtreeHeight(c); });
      return Math.max(CARD_HEIGHT + VERTICAL_GAP, sum);
    }

    let totalTopHeight = 0;
    topLevel.forEach(t => { totalTopHeight += getSubtreeHeight(t); });

    const canvasHeight = Math.max(650, totalTopHeight + 150);
    let currentY = (canvasHeight - totalTopHeight) / 2;
    const rootPos = { x: 120, y: topLevel.length === 0 ? canvasHeight / 2 : canvasHeight / 2 };

    let maxDepth = 1;

    function layoutHorizontal(ticket, topY, tier) {
      if (tier > maxDepth) maxDepth = tier;
      const branchHeight = getSubtreeHeight(ticket);
      const x = 120 + tier * HORIZONTAL_GAP;
      const y = topY + branchHeight / 2;
      posMap.set(ticket.id, { x, y });

      if (state.collapsedNodes.has(ticket.id)) return;

      const children = childrenMap.get(ticket.id) || [];
      let childTopY = topY;
      children.forEach(c => {
        layoutHorizontal(c, childTopY, tier + 1);
        childTopY += getSubtreeHeight(c);
      });
    }

    topLevel.forEach(t => {
      const branchHeight = getSubtreeHeight(t);
      layoutHorizontal(t, currentY, 1);
      currentY += branchHeight;
    });

    const canvasWidth = Math.max(1200, 120 + (maxDepth + 1) * HORIZONTAL_GAP + 150);

    elements.treeSvgLayer.setAttribute('width', canvasWidth);
    elements.treeSvgLayer.setAttribute('height', canvasHeight);
    elements.treeSvgLayer.style.width = `${canvasWidth}px`;
    elements.treeSvgLayer.style.height = `${canvasHeight}px`;
    elements.treeContainer.style.width = `${canvasWidth}px`;
    elements.treeContainer.style.height = `${canvasHeight}px`;

    // Root Node
    const rootNode = createRootNode(rootPos);
    elements.treeContainer.appendChild(rootNode);

    if (tickets.length === 0) {
      const emptyHint = document.createElement('div');
      emptyHint.className = 'graph-empty-hint flex flex-col items-start justify-center text-slate-400 text-xs gap-1 pointer-events-none';
      emptyHint.style.left = `${rootPos.x + 190}px`;
      emptyHint.style.top = `${rootPos.y}px`;
      emptyHint.style.transform = 'translate(0, -50%)';
      emptyHint.innerHTML = `
        <p class="font-medium text-slate-500 dark:text-slate-400">No tasks match current filters</p>
        <p class="text-[11px] text-slate-400">Click <span class="font-semibold text-brand-600 dark:text-brand-400">+</span> on <span class="font-semibold text-slate-700 dark:text-slate-300">${escapeHtml(projectName)}</span> to create a task</p>
      `;
      elements.treeContainer.appendChild(emptyHint);
    }

    // Hierarchy Lines
    topLevel.forEach(t => {
      const p = posMap.get(t.id);
      if (!p) return;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M ${rootPos.x + 90} ${rootPos.y} C ${(rootPos.x + p.x) / 2} ${rootPos.y}, ${(rootPos.x + p.x) / 2} ${p.y}, ${p.x - 135} ${p.y}`);
      path.setAttribute('class', 'graph-edge');
      elements.treeSvgEdges.appendChild(path);
    });

    childrenMap.forEach((children, parentId) => {
      if (state.collapsedNodes.has(parentId)) return;
      const parentPos = posMap.get(parentId);
      if (!parentPos) return;
      children.forEach(c => {
        const childPos = posMap.get(c.id);
        if (!childPos) return;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M ${parentPos.x + 135} ${parentPos.y} C ${(parentPos.x + childPos.x) / 2} ${parentPos.y}, ${(parentPos.x + childPos.x) / 2} ${childPos.y}, ${childPos.x - 135} ${childPos.y}`);
        path.setAttribute('class', 'graph-edge');
        elements.treeSvgEdges.appendChild(path);
      });
    });
  }

  // Draw Directional Dependency Arrows (DAG)
  tickets.forEach(t => {
    if (!t.deps || t.deps.length === 0) return;
    const targetPos = posMap.get(t.id);
    if (!targetPos) return;

    t.deps.forEach(blockerId => {
      const sourcePos = posMap.get(blockerId);
      if (!sourcePos) return;

      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      const dx = targetPos.x - sourcePos.x;
      const dy = targetPos.y - sourcePos.y;
      const offset = 45;
      const cx1 = sourcePos.x + dx * 0.3 + (isHorizontal ? 0 : offset);
      const cy1 = sourcePos.y + dy * 0.5 + (isHorizontal ? offset : 0);
      const cx2 = targetPos.x - dx * 0.3 + (isHorizontal ? 0 : offset);
      const cy2 = targetPos.y - dy * 0.5 + (isHorizontal ? offset : 0);

      path.setAttribute('d', `M ${sourcePos.x} ${sourcePos.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${targetPos.x} ${targetPos.y}`);
      path.setAttribute('class', 'graph-edge-dep');
      path.setAttribute('marker-end', 'url(#arrow)');
      elements.treeSvgEdges.appendChild(path);
    });
  });

  // Render Visible Ticket Node Cards
  posMap.forEach((pos, ticketId) => {
    const t = ticketMap.get(ticketId);
    if (!t) return;

    const children = childrenMap.get(ticketId) || [];
    const hasChildren = children.length > 0;
    const isCollapsed = state.collapsedNodes.has(ticketId);

    const card = document.createElement('div');
    card.id = `tree-node-${t.id}`;
    card.className = 'graph-node-card bg-white dark:bg-slate-900 p-3.5 rounded-2xl border border-slate-300 dark:border-slate-800 shadow-md hover:border-brand-500 cursor-pointer space-y-2 select-none';
    card.style.left = `${pos.x}px`;
    card.style.top = `${pos.y}px`;

    const depsBadge = (t.deps && t.deps.length > 0)
      ? `<div class="text-[10px] text-rose-500 dark:text-rose-400 font-semibold flex items-center gap-1 truncate"><i data-lucide="link" class="w-3 h-3 shrink-0"></i><span class="truncate">Depends: ${escapeHtml(t.deps.join(', '))}</span></div>`
      : '';

    let collapseBadge = '';
    if (hasChildren) {
      collapseBadge = isCollapsed
        ? `<button data-toggle-id="${escapeHtml(t.id)}" title="Expand subtasks" class="tree-toggle-collapse flex items-center gap-1 px-2 py-0.5 rounded-md bg-brand-50 dark:bg-slate-800 text-brand-600 dark:text-brand-400 text-[10px] font-bold border border-brand-200 dark:border-slate-700 hover:bg-brand-100 transition">
             <i data-lucide="plus-circle" class="w-3 h-3"></i>
             <span>+${children.length} subtask${children.length === 1 ? '' : 's'}</span>
           </button>`
        : `<button data-toggle-id="${escapeHtml(t.id)}" title="Collapse subtasks" class="tree-toggle-collapse flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-500 text-[10px] font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition">
             <i data-lucide="minus-circle" class="w-3 h-3"></i>
             <span>${children.length}</span>
           </button>`;
    }

    card.innerHTML = `
      <div class="flex items-center justify-between gap-1">
        <div class="flex items-center gap-1.5">
          <span class="font-mono text-xs font-bold text-brand-600 dark:text-brand-400">${escapeHtml(t.id)}</span>
          ${collapseBadge}
        </div>
        <div class="flex items-center gap-1">
          ${getTypeBadge(t.type)}
          ${getPriorityBadge(t.priority)}
        </div>
      </div>
      <h4 class="font-semibold text-xs text-slate-800 dark:text-slate-100 line-clamp-2 leading-snug">${escapeHtml(t.title)}</h4>
      <div class="flex items-center justify-between pt-1 border-t border-slate-100 dark:border-slate-800/80 text-[10px]">
        ${getStatusBadge(t.status, t.is_blocked)}
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400 truncate max-w-[80px] font-mono">${escapeHtml(t.assignee || 'Unassigned')}</span>
          <button data-add-child-id="${escapeHtml(t.id)}" title="Add Subtask under this ticket" class="tree-add-subtask p-0.5 text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
            <i data-lucide="plus" class="w-3 h-3"></i>
          </button>
        </div>
      </div>
      ${depsBadge}
    `;

    card.addEventListener('click', (e) => {
      const toggleBtn = e.target.closest('.tree-toggle-collapse');
      const addSubtaskBtn = e.target.closest('.tree-add-subtask');
      if (toggleBtn) {
        e.stopPropagation();
        const id = toggleBtn.dataset.toggleId;
        if (state.collapsedNodes.has(id)) {
          state.collapsedNodes.delete(id);
        } else {
          state.collapsedNodes.add(id);
        }
        localStorage.setItem('tk_tree_collapsed', JSON.stringify([...state.collapsedNodes]));
        renderTreeView();
        return;
      }
      if (addSubtaskBtn) {
        e.stopPropagation();
        const parentId = addSubtaskBtn.dataset.addChildId;
        openNewTicketModal('open', parentId);
        return;
      }
      openDetailModal(t);
    });

    elements.treeContainer.appendChild(card);
  });

  applyTreeZoom();
  lucide.createIcons();
}

export function applyTreeZoom() {
  const transform = `scale(${state.treeZoom})`;
  elements.treeContainer.style.transform = transform;
  elements.treeSvgLayer.style.transform = transform;
  elements.treeContainer.style.transformOrigin = state.treeOrientation === 'horizontal' ? 'left center' : 'top center';
  elements.treeSvgLayer.style.transformOrigin = state.treeOrientation === 'horizontal' ? 'left center' : 'top center';
}
