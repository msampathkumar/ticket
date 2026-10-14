// tk Web UI: state module (split from app.js, tic-4h0q).

// State management
export const state = {
  currentDir: '',
  tickets: [],
  filteredTickets: [],
  activeTicket: null,
  activeView: 'kanban', // 'kanban', 'table', 'tree', 'timeline'
  showAllClosed: false,
  recentDirs: JSON.parse(localStorage.getItem('tk_recent_dirs') || '[]'),
  browsingDir: '~',
  isDarkMode: localStorage.getItem('tk_theme') === 'dark' || (!('tk_theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches),
  accentColor: localStorage.getItem('tk_accent') || 'indigo',
  fontFamily: localStorage.getItem('tk_font_family') || 'sans',
  fontSize: localStorage.getItem('tk_font_size') || 'md',
  contrastHigh: localStorage.getItem('tk_contrast_high') === 'true',
  startDateFilter: localStorage.getItem('tk_filter_start_date') || '',
  endDateFilter: localStorage.getItem('tk_filter_date_end') || '',
  treeZoom: 1.0,
  treeOrientation: localStorage.getItem('tk_tree_orientation') || 'vertical', // 'vertical' (top-down) or 'horizontal' (left-to-right)
  collapsedNodes: new Set(JSON.parse(localStorage.getItem('tk_tree_collapsed') || '[]')),
  treeStatusFilter: new Set(JSON.parse(localStorage.getItem('tk_tree_status_filter') || '["ready", "in_progress", "blocked"]')),
  // Auto-refresh (tic-da9d)
  isDragging: false,
  ticketsVersion: null,     // last seen /api/tickets/version fingerprint
  ticketsVersionDir: null,  // directory that fingerprint belongs to
  pollInFlight: false,
};

export const POLL_INTERVAL_MS = 3000;

// DOM elements
export const elements = {
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
  settingsBtn: document.getElementById('settingsBtn'),
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
  treeSvgLayer: document.getElementById('treeSvgLayer'),
  treeSvgEdges: document.getElementById('treeSvgEdges'),
  treeZoomInBtn: document.getElementById('treeZoomInBtn'),
  treeZoomOutBtn: document.getElementById('treeZoomOutBtn'),
  treeResetZoomBtn: document.getElementById('treeResetZoomBtn'),
  treeOrientationBtn: document.getElementById('treeOrientationBtn'),
  treeOrientationLabel: document.getElementById('treeOrientationLabel'),
  treeCollapseAllBtn: document.getElementById('treeCollapseAllBtn'),
  treeCollapseAllLabel: document.getElementById('treeCollapseAllLabel'),
  treeStatusFilterBtn: document.getElementById('treeStatusFilterBtn'),
  treeStatusFilterSummary: document.getElementById('treeStatusFilterSummary'),
  treeStatusFilterMenu: document.getElementById('treeStatusFilterMenu'),
  treeStatusReady: document.getElementById('treeStatusReady'),
  treeStatusInProgress: document.getElementById('treeStatusInProgress'),
  treeStatusBlocked: document.getElementById('treeStatusBlocked'),
  treeStatusClosed: document.getElementById('treeStatusClosed'),
  timelineContainer: document.getElementById('timelineContainer'),

  // Settings Modal (tic-6mex)
  settingsModal: document.getElementById('settingsModal'),
  closeSettingsModalBtn: document.getElementById('closeSettingsModalBtn'),
  saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  resetSettingsBtn: document.getElementById('resetSettingsBtn'),
  fontFamilySelect: document.getElementById('fontFamilySelect'),
  fontSizeSelect: document.getElementById('fontSizeSelect'),
  highContrastToggle: document.getElementById('highContrastToggle'),
  startDateFilter: document.getElementById('startDateFilter'),
  endDateFilter: document.getElementById('endDateFilter'),
  clearDateFilterBtn: document.getElementById('clearDateFilterBtn'),

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
