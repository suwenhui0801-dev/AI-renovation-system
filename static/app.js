import * as THREE from 'https://unpkg.com/three@0.160.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js?module';
import { PointerLockControls } from 'https://unpkg.com/three@0.160.0/examples/jsm/controls/PointerLockControls.js?module';
import { GLTFLoader } from 'https://unpkg.com/three@0.160.0/examples/jsm/loaders/GLTFLoader.js?module';

const el = {
  planCanvas: document.getElementById('planCanvas'),
  planStage: document.getElementById('planStage'),
  threeContainer: document.getElementById('threeContainer'),
  firstPersonBtn: document.getElementById('firstPersonBtn'),
  editModeBtn: document.getElementById('editModeBtn'),
  firstPersonHint: document.getElementById('firstPersonHint'),
  messageBox: document.getElementById('messageBox'),
  selectionInfo: document.getElementById('selectionInfo'),
  commandInput: document.getElementById('commandInput'),
  voiceCommandBtn: document.getElementById('voiceCommandBtn'),
  undoBtn: document.getElementById('undoBtn'),
  // redoBtn: document.getElementById('redoBtn'),

  toggleRoomPanelBtn: document.getElementById('toggleRoomPanelBtn'),
  toggleOpeningPanelBtn: document.getElementById('toggleOpeningPanelBtn'),
  toggleFurniturePanelBtn: document.getElementById('toggleFurniturePanelBtn'),
  toggleFurnitureEditorPanelBtn: document.getElementById('toggleFurnitureEditorPanelBtn'),
  showCommandPanelBtn: document.getElementById('showCommandPanelBtn'),
  showAIFloorplanPanelBtn: document.getElementById('showAIFloorplanPanelBtn'),
  commandPanel: document.getElementById('commandPanel'),
  aiFloorplanPanel: document.getElementById('aiFloorplanPanel'),

  roomListPanel: document.getElementById('roomListPanel'),
  openingListPanel: document.getElementById('openingListPanel'),
  furnitureListPanel: document.getElementById('furnitureListPanel'),
  furnitureEditorPanel: document.getElementById('furnitureEditorPanel'),

  roomNameInput: document.getElementById('roomNameInput'),
  // roomTypeSelect: document.getElementById('roomTypeSelect'),
  roomXInput: document.getElementById('roomXInput'),
  roomYInput: document.getElementById('roomYInput'),
  roomWidthInput: document.getElementById('roomWidthInput'),
  roomDepthInput: document.getElementById('roomDepthInput'),
  roomHeightInput: document.getElementById('roomHeightInput'),
  roomColorInput: document.getElementById('roomColorInput'),
  addRoomBtn: document.getElementById('addRoomBtn'),
  applyRoomBtn: document.getElementById('applyRoomBtn'),
  deleteRoomBtn: document.getElementById('deleteRoomBtn'),

  openingNameInput: document.getElementById('openingNameInput'),
  // openingRoomSelect: document.getElementById('openingRoomSelect'),
  // openingTypeSelect: document.getElementById('openingTypeSelect'),
  openingWallSelect: document.getElementById('openingWallSelect'),
  openingOffsetInput: document.getElementById('openingOffsetInput'),
  openingWidthInput: document.getElementById('openingWidthInput'),
  addOpeningBtn: document.getElementById('addOpeningBtn'),
  applyOpeningBtn: document.getElementById('applyOpeningBtn'),
  deleteOpeningBtn: document.getElementById('deleteOpeningBtn'),

  furnitureSearchInput: document.getElementById('furnitureSearchInput'),
  furnitureCategoryTabs: document.getElementById('furnitureCategoryTabs'),
  furnitureLibrary: document.getElementById('furnitureLibrary'),
  placementHint: document.getElementById('placementHint'),
  furnitureSelect: document.getElementById('furnitureSelect'),
  popupFurnitureTitle: document.getElementById('popupFurnitureTitle'),
  furnitureLabelInput: document.getElementById('furnitureLabelInput'),
  // furnitureTypeSelect: document.getElementById('furnitureTypeSelect'),
  // furnitureRoomSelect: document.getElementById('furnitureRoomSelect'),
  furnitureColorInput: document.getElementById('furnitureColorInput'),
  furnitureMaterialInput: document.getElementById('furnitureMaterialInput'),
  furnitureWidthInput: document.getElementById('furnitureWidthInput'),
  furnitureDepthInput: document.getElementById('furnitureDepthInput'),
  furnitureXInput: document.getElementById('furnitureXInput'),
  furnitureYInput: document.getElementById('furnitureYInput'),
  furnitureRotationInput: document.getElementById('furnitureRotationInput'),
  addFurnitureBtn: document.getElementById('addFurnitureBtn'),
  applyFurnitureBtn: document.getElementById('applyFurnitureBtn'),
  
  deleteFurnitureBtn: document.getElementById('deleteFurnitureBtn'),

  gestureToggleBtn: document.getElementById('gestureToggleBtn'),
  gestureStatusText: document.getElementById('gestureStatusText'),
  gestureActionText: document.getElementById('gestureActionText'),
  gestureVideo: document.getElementById('gestureVideo'),
  gestureOverlay: document.getElementById('gestureOverlay'),
  
  // AI户型模块
  aiFloorplanInput: document.getElementById('aiFloorplanInput'),
  floorplanPreview: document.getElementById('floorplanPreview'),
  aiGenerateFloorplanBtn: document.getElementById('aiGenerateFloorplanBtn'),
  uploadFloorplanBtn: document.getElementById('uploadFloorplanBtn'),
  saveFloorplanBtn: document.getElementById('saveFloorplanBtn'),
  applyFloorplanBtn: document.getElementById('applyFloorplanBtn'),
  floorplanStatusText: document.getElementById('floorplanStatusText'),
};


const ctx = el.planCanvas.getContext('2d');
let state = null;
let selected = { type: 'room', id: null };
let preferredFurnitureType = 'loungeSofa';
let pendingPlacementType = null;
let librarySearch = '';
let libraryCategory = '全部';
let lastFeedbackKind = 'info';

const planPadding = 28;
let planZoom = 1;
let planPanX = 0;
let planPanY = 0;

const drag = {
  mode: null,
  id: null,
  kind: null,
  dx: 0,
  dy: 0,
  edge: null,
  startX: 0,
  startY: 0,
  startPanX: 0,
  startPanY: 0,
};

let mouseDown = false;

const previewState = {
  hoverPlacement: null,
  snapLines: [],
  collision: false,
  collisionId: null,
};

const roomMeshes = new Map();
const furnitureGroups = new Map();
const openingMeshes = new Map();

let gltfLoader;
const modelCache = new Map();
let render3DToken = 0;



let scene;
let camera;
let renderer;
let controls;
let fpControls;
let isFirstPersonMode = false;
let firstPersonClock;
const FIRST_PERSON_HEIGHT = 1.65;
const firstPersonKeys = { forward: false, backward: false, left: false, right: false };
let savedOrbitView = null;
let raycaster;
let pointer;
let fitCameraPending = true;

const threeClickState = { down: false, x: 0, y: 0 };
const threeDrag = { active: false, id: null, type: null, offsetX: 0, offsetY: 0, moved: false };

const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
let speechRecognition = null;

const gestureState = {
  enabled: false,
  stream: null,
  hands: null,
  camera: null,
  overlayCtx: null,
  lastActionText: '等待手势操作',
  lastZoomDistance: null,
  lastPinch: false,
  pinchDragging: false,
  dragFurnitureId: null,
  resizeDistance: null,
  openPalmActive: false,
  openPalmLastCenterY: null,
  lastOkAt: 0,
  lastDeleteAt: 0,
  // 删除手势倒计时相关
  deleteCountdownTimer: null,
  deleteCountdown: 0,
  // 撤销手势倒计时相关
  undoCountdownTimer: null,
  undoCountdown: 0,
  lastUndoAt: 0,
  // 正赞手势倒计时相关
  thumbUpCountdownTimer: null,
  thumbUpCountdown: 0,
  lastThumbUpAt: 0,
  // 1手势光标相关
  cursorVisible: true,
  cursorX: 0,
  cursorY: 0,
};
let isVoiceRecording = false;
let speechFinalText = '';
let voiceAutoRunTimer = null;
const VOICE_MODEL_LABEL = '';


function selectedRoom() {
  if (!selected) return null;
  return selected.type === 'room' ? state?.rooms.find(r => r.id === selected.id) : null;
}

function selectedOpening() {
  if (!selected) return null;
  return selected.type === 'opening' ? state?.openings.find(o => o.id === selected.id) : null;
}

function selectedFurniture() {
  if (!selected) return null;
  return selected.type === 'furniture' ? state?.furnitures.find(f => f.id === selected.id) : null;
}

function getFurnitureCatalog() {
  return state?.options?.furniture_catalog || [];
}

function getFurnitureMeta(type) {
  return getFurnitureCatalog().find(item => item.value === type) || null;
}

function getFurnitureModelConfig(type) {
  const meta = getFurnitureMeta(type);
  if (!meta || !meta.model) {
    throw new Error(`未找到家具类型 ${type} 对应的模型文件`);
  }

  return {
    url: `/static/models/${meta.model}`,
    rotationOffset: Number(meta.rotationOffset || 0),
    yOffset: Number(meta.yOffset || 0),
    wallMount: !!meta.wallMount,
    defaultMountHeight: Number(meta.defaultMountHeight || meta.yOffset || 1.5),
  };
}

function isWallMountableType(type) {
  return !!getFurnitureMeta(type)?.wallMount;
}

function isWallFurniture(item) {
  return item?.placement === 'wall';
}

function getWallLength(room, wall) {
  return (wall === 'top' || wall === 'bottom') ? room.width : room.depth;
}

function clampWallOffset(room, wall, offset) {
  const length = getWallLength(room, wall);
  return clamp(Number(offset || 0), 0.05, Math.max(0.05, length - 0.05));
}

function clampMountHeight(room, height, fallback = 1.5) {
  const roomHeight = Number(room?.height || 3);
  const safeMax = Math.max(0.5, roomHeight - 0.25);
  return clamp(Number(height || fallback), 0.3, safeMax);
}

function wallPlacementToWorld(room, wall, offset, mountHeight = 1.5) {
  const safeOffset = clampWallOffset(room, wall, offset);
  if (wall === 'top') return { x: room.x + safeOffset, y: room.y, z: room.y, rotation: 0, wallOffset: safeOffset };
  if (wall === 'bottom') return { x: room.x + safeOffset, y: room.y + room.depth, z: room.y + room.depth, rotation: 180, wallOffset: safeOffset };
  if (wall === 'left') return { x: room.x, y: room.y + safeOffset, z: room.y + safeOffset, rotation: 90, wallOffset: safeOffset };
  return { x: room.x + room.width, y: room.y + safeOffset, z: room.y + safeOffset, rotation: 270, wallOffset: safeOffset };
}

function nearestWallFromPoint(room, x, y) {
  const distances = [
    { wall: 'top', d: Math.abs(y - room.y), offset: x - room.x },
    { wall: 'bottom', d: Math.abs(y - (room.y + room.depth)), offset: x - room.x },
    { wall: 'left', d: Math.abs(x - room.x), offset: y - room.y },
    { wall: 'right', d: Math.abs(x - (room.x + room.width)), offset: y - room.y },
  ];
  distances.sort((a, b) => a.d - b.d);
  const hit = distances[0];
  return { wall: hit.wall, offset: clampWallOffset(room, hit.wall, hit.offset), distance: hit.d };
}

function furnitureFootprint(item) {
  const rot = ((((item.rotation || 0) % 180) + 180) % 180);
  return Math.abs(rot - 90) < 1 ? { width: item.depth, depth: item.width } : { width: item.width, depth: item.depth };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function closeSidePanels() {
  el.roomListPanel.classList.remove('visible');
  el.openingListPanel.classList.remove('visible');
  el.furnitureListPanel.classList.remove('visible');
  el.furnitureEditorPanel.classList.remove('visible');
  
  // 所有按钮变为未选中状态
  el.toggleRoomPanelBtn.classList.add('secondary');
  el.toggleOpeningPanelBtn.classList.add('secondary');
  el.toggleFurniturePanelBtn.classList.add('secondary');
  el.toggleFurnitureEditorPanelBtn.classList.add('secondary');
}

function showSidePanel(name) {
  const target = {
    room: el.roomListPanel,
    opening: el.openingListPanel,
    furniture: el.furnitureListPanel,
    furnitureEditor: el.furnitureEditorPanel,
  }[name];
  if (!target) return;
  closeSidePanels();
  target.classList.add('visible');
  
  // 切换按钮样式
  const buttons = {
    room: el.toggleRoomPanelBtn,
    opening: el.toggleOpeningPanelBtn,
    furniture: el.toggleFurniturePanelBtn,
    furnitureEditor: el.toggleFurnitureEditorPanelBtn,
  };
  
  Object.entries(buttons).forEach(([key, button]) => {
    if (key === name) {
      button.classList.remove('secondary');
    } else {
      button.classList.add('secondary');
    }
  });
}

function toggleSidePanel(name) {
  const target = {
    room: el.roomListPanel,
    opening: el.openingListPanel,
    furniture: el.furnitureListPanel,
    furnitureEditor: el.furnitureEditorPanel,
  }[name];
  if (!target) return;
  const willOpen = !target.classList.contains('visible');
  closeSidePanels();
  if (willOpen) target.classList.add('visible');
  
  // 切换按钮样式
  const buttons = {
    room: el.toggleRoomPanelBtn,
    opening: el.toggleOpeningPanelBtn,
    furniture: el.toggleFurniturePanelBtn,
    furnitureEditor: el.toggleFurnitureEditorPanelBtn,
  };
  
  Object.entries(buttons).forEach(([key, button]) => {
    if (key === name && willOpen) {
      button.classList.remove('secondary');
    } else {
      button.classList.add('secondary');
    }
  });
}

function showTopPanel(name) {
  const isCommand = name === 'command';
  if (el.commandPanel) el.commandPanel.classList.toggle('visible', isCommand);
  if (el.aiFloorplanPanel) el.aiFloorplanPanel.classList.toggle('visible', !isCommand);
  if (el.showCommandPanelBtn) el.showCommandPanelBtn.classList.toggle('active', isCommand);
  if (el.showAIFloorplanPanelBtn) el.showAIFloorplanPanelBtn.classList.toggle('active', !isCommand);
}

function getBounds() {
  if (!state || !state.rooms.length) return { minX: 0, minY: 0, maxX: 6, maxY: 6, width: 6, height: 6 };
  const xs = state.rooms.flatMap(r => [r.x, r.x + r.width]);
  const ys = state.rooms.flatMap(r => [r.y, r.y + r.depth]);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 6);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 6);
  return { minX, minY, maxX, maxY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY) };
}

function getViewport() {
  const bounds = getBounds();
  const cw = el.planCanvas.clientWidth;
  const ch = el.planCanvas.clientHeight;
  const baseScale = Math.min((cw - planPadding * 2) / bounds.width, (ch - planPadding * 2) / bounds.height);
  const scale = Math.max(8, baseScale * planZoom);
  const offsetX = cw / 2 - ((bounds.minX + bounds.maxX) / 2) * scale + planPanX;
  const offsetY = ch / 2 - ((bounds.minY + bounds.maxY) / 2) * scale + planPanY;
  return { cw, ch, scale, offsetX, offsetY };
}

function clampPlanPan() {
  const bounds = getBounds();
  const cw = el.planCanvas.clientWidth;
  const ch = el.planCanvas.clientHeight;

  const baseScale = Math.min(
    (cw - planPadding * 2) / bounds.width,
    (ch - planPadding * 2) / bounds.height
  );
  const scale = Math.max(8, baseScale * planZoom);

  // 允许少量拖动余量，但不能把整个户型拖没
  const maxPanX = Math.max(80, bounds.width * scale * 0.35);
  const maxPanY = Math.max(80, bounds.height * scale * 0.35);

  planPanX = clamp(planPanX, -maxPanX, maxPanX);
  planPanY = clamp(planPanY, -maxPanY, maxPanY);
}

const toCanvasX = (x, v) => v.offsetX + x * v.scale;
const toCanvasY = (y, v) => v.offsetY + y * v.scale;
const fromCanvasX = (x, v) => (x - v.offsetX) / v.scale;
const fromCanvasY = (y, v) => (y - v.offsetY) / v.scale;

function resizeCanvas() {
  const rect = el.planCanvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  el.planCanvas.width = Math.round(rect.width * dpr);
  el.planCanvas.height = Math.round(rect.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function canvasPoint(evt) {
  const rect = el.planCanvas.getBoundingClientRect();
  return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
}

function hitRoom(px, py) {
  if (!state) return null;
  const v = getViewport();
  const rx = fromCanvasX(px, v);
  const ry = fromCanvasY(py, v);
  for (let i = state.rooms.length - 1; i >= 0; i -= 1) {
    const room = state.rooms[i];
    if (rx >= room.x && rx <= room.x + room.width && ry >= room.y && ry <= room.y + room.depth) return room;
  }
  return null;
}

function hitFurniture(px, py) {
  if (!state) return null;
  const v = getViewport();
  const rx = fromCanvasX(px, v);
  const ry = fromCanvasY(py, v);
  for (let i = state.furnitures.length - 1; i >= 0; i -= 1) {
    const item = state.furnitures[i];
    const fp = furnitureFootprint(item);
    if (rx >= item.x && rx <= item.x + fp.width && ry >= item.y && ry <= item.y + fp.depth) return item;
  }
  return null;
}

function openingSegment(room, opening, v) {
  const x = toCanvasX(room.x, v);
  const y = toCanvasY(room.y, v);
  const w = room.width * v.scale;
  const h = room.depth * v.scale;
  const offset = opening.offset * v.scale;
  const width = opening.width * v.scale;
  if (opening.wall === 'top') return { x1: x + offset, y1: y, x2: x + offset + width, y2: y };
  if (opening.wall === 'bottom') return { x1: x + offset, y1: y + h, x2: x + offset + width, y2: y + h };
  if (opening.wall === 'left') return { x1: x, y1: y + offset, x2: x, y2: y + offset + width };
  return { x1: x + w, y1: y + offset, x2: x + w, y2: y + offset + width };
}

function hitOpening(px, py) {
  if (!state) return null;
  const v = getViewport();
  for (let i = state.openings.length - 1; i >= 0; i -= 1) {
    const opening = state.openings[i];
    const room = state.rooms.find(r => r.id === opening.room_id);
    if (!room) continue;
    const seg = openingSegment(room, opening, v);
    const dx = seg.x2 - seg.x1;
    const dy = seg.y2 - seg.y1;
    const len2 = dx * dx + dy * dy || 1;
    const t = Math.max(0, Math.min(1, ((px - seg.x1) * dx + (py - seg.y1) * dy) / len2));
    const projX = seg.x1 + t * dx;
    const projY = seg.y1 + t * dy;
    if (Math.hypot(px - projX, py - projY) <= 12) return opening;
  }
  return null;
}

function roomEdgeHit(room, px, py) {
  const v = getViewport();
  const x = toCanvasX(room.x, v);
  const y = toCanvasY(room.y, v);
  const w = room.width * v.scale;
  const h = room.depth * v.scale;
  const eps = 12;
  if (Math.abs(py - y) < eps && px >= x && px <= x + w) return 'top';
  if (Math.abs(py - (y + h)) < eps && px >= x && px <= x + w) return 'bottom';
  if (Math.abs(px - x) < eps && py >= y && py <= y + h) return 'left';
  if (Math.abs(px - (x + w)) < eps && py >= y && py <= y + h) return 'right';
  return null;
}

function findRoomForFurniturePlacement(x, y, item) {
  const fp = furnitureFootprint(item);
  const cx = x + fp.width / 2;
  const cy = y + fp.depth / 2;
  for (let i = state.rooms.length - 1; i >= 0; i -= 1) {
    const room = state.rooms[i];
    if (cx >= room.x && cx <= room.x + room.width && cy >= room.y && cy <= room.y + room.depth) return room;
  }
  return null;
}

function clampFurnitureInsideRoomLocal(item) {
  const room = state.rooms.find(r => r.id === item.room_id);
  if (!room) return;
  const fp = furnitureFootprint(item);
  item.x = clamp(item.x, room.x + 0.05, room.x + room.width - fp.width - 0.05);
  item.y = clamp(item.y, room.y + 0.05, room.y + room.depth - fp.depth - 0.05);
}

function collidesLocal(item) {
  const fp = furnitureFootprint(item);
  return state.furnitures.some(other => {
    if (other.id === item.id || other.room_id !== item.room_id) return false;
    const of = furnitureFootprint(other);
    return !(item.x + fp.width <= other.x || other.x + of.width <= item.x || item.y + fp.depth <= other.y || other.y + of.depth <= item.y);
  });
}

function computeSnapForFurnitureLocal(item) {
  const room = state.rooms.find(r => r.id === item.room_id);
  previewState.snapLines = [];
  previewState.collision = false;
  previewState.collisionId = item.id;
  if (!room) return;

  const fp = furnitureFootprint(item);
  const threshold = 0.22;
  const lines = [];

  const left = room.x + 0.05;
  const right = room.x + room.width - fp.width - 0.05;
  const top = room.y + 0.05;
  const bottom = room.y + room.depth - fp.depth - 0.05;
  const centerX = room.x + (room.width - fp.width) / 2;
  const centerY = room.y + (room.depth - fp.depth) / 2;

  const snapX = (value, lineX) => {
    item.x = value;
    lines.push({ kind: 'vertical', value: lineX });
  };
  const snapY = (value, lineY) => {
    item.y = value;
    lines.push({ kind: 'horizontal', value: lineY });
  };

  if (Math.abs(item.x - left) <= threshold) snapX(left, left);
  if (Math.abs(item.x - right) <= threshold) snapX(right, right + fp.width);
  if (Math.abs(item.y - top) <= threshold) snapY(top, top);
  if (Math.abs(item.y - bottom) <= threshold) snapY(bottom, bottom + fp.depth);
  if (Math.abs(item.x - centerX) <= threshold) snapX(centerX, centerX + fp.width / 2);
  if (Math.abs(item.y - centerY) <= threshold) snapY(centerY, centerY + fp.depth / 2);

  state.furnitures.forEach(other => {
    if (other.id === item.id || other.room_id !== item.room_id) return;
    const of = furnitureFootprint(other);
    const candidatesX = [
      { value: other.x, line: other.x },
      { value: other.x + of.width, line: other.x + of.width },
      { value: other.x + (of.width - fp.width) / 2, line: other.x + of.width / 2 },
    ];
    const candidatesY = [
      { value: other.y, line: other.y },
      { value: other.y + of.depth, line: other.y + of.depth },
      { value: other.y + (of.depth - fp.depth) / 2, line: other.y + of.depth / 2 },
    ];
    candidatesX.forEach(candidate => {
      if (Math.abs(item.x - candidate.value) <= threshold) snapX(candidate.value, candidate.line);
    });
    candidatesY.forEach(candidate => {
      if (Math.abs(item.y - candidate.value) <= threshold) snapY(candidate.value, candidate.line);
    });
  });

  clampFurnitureInsideRoomLocal(item);
  previewState.snapLines = lines;
  previewState.collision = collidesLocal(item);
}

function applyFurnitureLocalPlacement(item) {
  const targetRoom = findRoomForFurniturePlacement(item.x, item.y, item) || state.rooms.find(r => r.id === item.room_id);
  if (targetRoom) item.room_id = targetRoom.id;
  clampFurnitureInsideRoomLocal(item);
  computeSnapForFurnitureLocal(item);
}

function inferFeedbackKind(message, explicitKind = null) {
  if (explicitKind) return explicitKind;
  const msg = String(message || '');
  if (!msg) return 'info';
  if (/(失败|错误|不存在|重叠|请选择|未识别|不可用)/.test(msg)) return 'error';
  if (/(已|成功|欢迎|恢复|撤销|添加|更新|删除)/.test(msg)) return 'success';
  return 'info';
}

function setMessage(message, kind = null) {
  const resolvedKind = inferFeedbackKind(message, kind);
  lastFeedbackKind = resolvedKind;
  el.messageBox.textContent = message || '';
  const holder = el.messageBox.closest('.feedback-item');
  holder.classList.remove('feedback-success', 'feedback-error', 'feedback-info');
  holder.classList.add(`feedback-${resolvedKind}`);
}


function renderFurnitureLibrary() {
  if (!state || !el.furnitureLibrary || !el.furnitureCategoryTabs) return;

  const catalog = getFurnitureCatalog();
  const categories = [
    '全部',
    '浴室家具',
    '卧室家具',
    '客厅家具',
    '厨房家具',
    '书房/办公家具',
    '电器设备',
    '其他物品',
  ];

  el.furnitureCategoryTabs.innerHTML = categories.map(category => `
    <button type="button" class="library-tab ${libraryCategory === category ? 'active' : ''}" data-category="${category}">
      ${category}
    </button>
  `).join('');

  el.furnitureCategoryTabs.querySelectorAll('.library-tab').forEach(btn => {
    btn.onclick = () => {
      libraryCategory = btn.dataset.category;
      renderFurnitureLibrary();
    };
  });

  const filtered = catalog.filter(item => {
    const matchCategory = libraryCategory === '全部' || (item.category || '家具') === libraryCategory;
    const keyword = librarySearch.trim().toLowerCase();
    const hay = [item.label || '', item.category || '', item.group || '', ...(item.tags || [])].join(' ').toLowerCase();
    const matchSearch = !keyword || hay.includes(keyword);
    return matchCategory && matchSearch;
  });

  if (!filtered.length) {
    el.furnitureLibrary.innerHTML = '<div class="library-empty">没有找到匹配的家具，换个关键词试试 </div>';
    return;
  }

  el.furnitureLibrary.innerHTML = filtered.map(item => {
    return `
      <div class="furniture-list-item ${pendingPlacementType === item.value ? 'active' : ''}" data-type="${item.value}">
        <div class="furniture-list-main">
          <div class="furniture-list-title">${item.label || '未命名家具'}</div>
          <div class="furniture-list-sub">
            ${(item.category || '家具')} · ${(item.group || '家具')}
          </div>
        </div>
        <div class="furniture-list-meta">
          ${Number(item.width || 1).toFixed(1)}m × ${Number(item.depth || 1).toFixed(1)}m
          ${item.wallMount ? '<span class="wall-mount-pill">可上墙</span>' : ''}
        </div>
      </div>
    `;
  }).join('');

  el.furnitureLibrary.querySelectorAll('.furniture-list-item').forEach(card => {
    card.onclick = () => {
      const type = card.dataset.type;
      preferredFurnitureType = type;
      pendingPlacementType = pendingPlacementType === type ? null : type;

      updatePlacementHint();
      renderFurnitureLibrary();
      render2D();
      render3D();

      if (pendingPlacementType) {
        const meta = getFurnitureMeta(type);
        setMessage(meta?.wallMount
          ? `已选中${meta?.label || '家具'}，请点击 2D 房间边线或 3D 墙面进行上墙摆放`
          : `已选中${meta?.label || '家具'}，请点击 2D 或 3D 场景中的房间位置放置`, 'info');
      }
    };
  });
}

function updatePlacementHint() {

  if (!el.placementHint) return;
  const meta = getFurnitureMeta(pendingPlacementType);
  if (!pendingPlacementType || !meta) {
    el.placementHint.textContent = '当前未进入待放置状态';
    el.placementHint.classList.remove('active');
    return;
  }
  el.placementHint.textContent = meta.wallMount
    ? `待放置：${meta.label} · 墙面摆放模式 · 点击2D房间边线或3D墙面放置`
    : `待放置：${meta.label} · ${meta.width.toFixed(1)}m × ${meta.depth.toFixed(1)}m · 点击房间即可落位`;
  el.placementHint.classList.add('active');
}

async function request(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json();
  const shouldAutoFit =  url === '/api/room' ||  url === '/api/import';

  if (data.state) {
    state = data.state;
    if (shouldAutoFit) fitCameraPending = true;

    if (shouldAutoFit) {
      planPanX = 0;
      planPanY = 0;
      planZoom = 1;
    }
  } else if (data.rooms) {
    state = data;
    if (shouldAutoFit) fitCameraPending = true;

    if (shouldAutoFit) {
      planPanX = 0;
      planPanY = 0;
      planZoom = 1;
    }
  }

  if (data.message || state?.message) setMessage(data.message || state.message, response.ok && data.ok === false ? 'error' : null);

  syncUI();
  render2D();
  render3D();
  afterStateUpdated();
  return data;
}


async function loadState() {
  const response = await fetch('/api/state');
  state = await response.json();

  if (!selected || !selected.id) {
    selected = state.rooms[0] ? { type: 'room', id: state.rooms[0].id } : null;
  }

  // 强制重置 2D 视图位置
  planPanX = 0;
  planPanY = 0;
  planZoom = 1;

  initThree();
  resizeCanvas();
  resize3DRenderer();
  syncUI();
  render2D();
  render3D();
  afterStateUpdated();
}


function fillRoomForm(room) {
  if (!room) return;
  el.roomNameInput.value = room.name || '';
  el.roomXInput.value = room.x;
  el.roomYInput.value = room.y;
  el.roomWidthInput.value = room.width;
  el.roomDepthInput.value = room.depth;
  if (el.roomHeightInput) el.roomHeightInput.value = Number(room.height || 3).toFixed(1);
  if (el.roomColorInput) el.roomColorInput.value = room.wall_color || '#f0efe9';
}

function fillOpeningForm(opening) {
  if (!opening) {
    el.openingNameInput.value = '';
    el.openingWallSelect.value = state.options.walls[0]?.value || 'top';
    el.openingOffsetInput.value = 0;
    el.openingWidthInput.value = 0.9;
    return;
  }
  el.openingNameInput.value = opening.name || '';
  el.openingWallSelect.value = opening.wall;
  el.openingOffsetInput.value = opening.offset;
  el.openingWidthInput.value = opening.width;
}

function fillFurnitureForm(item) {
  if (!item) {
    el.popupFurnitureTitle.textContent = '家具库';
    const meta = getFurnitureMeta(preferredFurnitureType) || getFurnitureCatalog()[0];
    el.furnitureWidthInput.value = meta?.width || 1.2;
    el.furnitureDepthInput.value = meta?.depth || 0.8;
    el.furnitureXInput.value = 0;
    el.furnitureYInput.value = 0;
    el.furnitureRotationInput.value = 0;
    return;
  }
  el.popupFurnitureTitle.textContent = '家具库';
  el.furnitureWidthInput.value = item.width;
  el.furnitureDepthInput.value = item.depth;
  el.furnitureXInput.value = item.x;
  el.furnitureYInput.value = item.y;
  el.furnitureRotationInput.value = item.rotation;
}

function syncUI() {
  if (!state) return;
  setMessage(state.message || '', lastFeedbackKind);

  let selectionText = '未选中';
  if (selected?.type === 'room') {
    selectionText = `房间：${selectedRoom()?.name || '无'}`;
  } else if (selected?.type === 'opening') {
    selectionText = `门窗：${selectedOpening()?.name || '无'}`;
  } else if (selected?.type === 'furniture') {
    selectionText = `家具：${selectedFurniture()?.label || '无'}`;
  }

  el.selectionInfo.textContent = selectionText;

  // const roomOptions = state.rooms.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
  // const furnitureOptions = getFurnitureCatalog().map(v => `<option value="${v.value}">${v.label}</option>`).join('');
  const historyOptions = state.options?.history || { can_undo: true, can_redo: false };

  el.undoBtn.disabled = !historyOptions.can_undo;
  // el.redoBtn.disabled = !historyOptions.can_redo;

  // el.roomTypeSelect.innerHTML = state.options.room_types.map(v => `<option value="${v}">${v}</option>`).join('');

  // el.openingRoomSelect.innerHTML = roomOptions;
  // el.openingTypeSelect.innerHTML = state.options.opening_types.map(v => `<option value="${v.value}">${v.label}</option>`).join('');
  el.openingWallSelect.innerHTML = state.options.walls.map(v => `<option value="${v.value}">${v.label}</option>`).join('');

  // el.furnitureRoomSelect.innerHTML = roomOptions;
  // el.furnitureTypeSelect.innerHTML = furnitureOptions;

  const room = selectedRoom() || state.rooms[0];
  const opening = selectedOpening();
  const furniture = selectedFurniture();

  if (room) fillRoomForm(room);
  fillOpeningForm(opening);
  fillFurnitureForm(furniture);
  updatePlacementHint();
  renderFurnitureLibrary();
}

function drawGrid(v) {
  if (!state.show_grid) return;
  ctx.save();
  ctx.strokeStyle = '#e5edf6';
  ctx.lineWidth = 1;
  const step = Math.max(18, state.grid_size_m * v.scale);
  let startX = ((-v.offsetX % step) + step) % step;
  let startY = ((-v.offsetY % step) + step) % step;
  for (let x = startX; x <= v.cw; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, v.ch);
    ctx.stroke();
  }
  for (let y = startY; y <= v.ch; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(v.cw, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawRoomDecor(room, x, y, w, h) {
  ctx.save();
  ctx.strokeStyle = 'rgba(51,65,85,.25)';
  ctx.fillStyle = 'rgba(255,255,255,.30)';
  const name = room.name || '';

  if (name.includes('厨房')) {
    ctx.strokeRect(x + 16, y + 14, Math.max(22, w * 0.55), 16);
    ctx.fillRect(x + 18, y + 16, Math.max(18, w * 0.22), 12);
    ctx.beginPath();
    ctx.arc(x + Math.max(28, w * 0.48), y + 22, 6, 0, Math.PI * 2);
    ctx.stroke();
  }

  if (name.includes('浴室')) {
    ctx.strokeRect(x + 16, y + 16, Math.max(22, w * 0.28), Math.max(18, h * 0.18));
    ctx.beginPath();
    ctx.arc(x + Math.max(46, w * 0.42), y + Math.max(34, h * 0.26), 10, 0, Math.PI * 2);
    ctx.stroke();
  }

  if (name.includes('阳台')) {
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(x + 12, y + 12, w - 24, h - 24);
    ctx.setLineDash([]);
  }

  ctx.restore();
}

function drawRoom(room, v) {
  const x = toCanvasX(room.x, v);
  const y = toCanvasY(room.y, v);
  const w = room.width * v.scale;
  const h = room.depth * v.scale;
  const active = selected?.type === 'room' && selected?.id === room.id;

  ctx.save();
  ctx.fillStyle = '#f7f3e8';
  ctx.strokeStyle = '#334155';
  ctx.lineWidth = 8;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);

  ctx.strokeStyle = 'rgba(255,255,255,.7)';
  ctx.lineWidth = 2;
  ctx.strokeRect(x + 8, y + 8, Math.max(0, w - 16), Math.max(0, h - 16));

  drawRoomDecor(room, x, y, w, h);

  if (active) {
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 5]);
    ctx.strokeRect(x + 6, y + 6, w - 12, h - 12);
    ctx.setLineDash([]);
  }

  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 16px "PingFang SC", sans-serif';
  ctx.fillText(room.name, x + 14, y + 24);
  ctx.fillStyle = '#64748b';
  ctx.font = '12px "PingFang SC", sans-serif';
  ctx.fillText(`${room.width.toFixed(1)}m × ${room.depth.toFixed(1)}m`, x + 14, y + 44);
  ctx.fillText(`墙高 ${Number(room.height || 3).toFixed(1)}m`, x + 14, y + 62);
  ctx.restore();
}

function drawDoorSymbol(seg, opening, active) {
  const dx = seg.x2 - seg.x1;
  const dy = seg.y2 - seg.y1;
  const length = Math.hypot(dx, dy);
  const nx = dx / (length || 1);
  const ny = dy / (length || 1);
  const centerX = (seg.x1 + seg.x2) / 2;
  const centerY = (seg.y1 + seg.y2) / 2;
  const inwardX = opening.wall === 'top' ? 0 : opening.wall === 'bottom' ? 0 : opening.wall === 'left' ? 1 : -1;
  const inwardY = opening.wall === 'top' ? 1 : opening.wall === 'bottom' ? -1 : 0;
  const doorDepth = 22;

  ctx.save();
  ctx.strokeStyle = '#8b6a4d';
  ctx.lineWidth = 6;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(seg.x1, seg.y1);
  ctx.lineTo(seg.x2, seg.y2);
  ctx.stroke();

  // ctx.strokeStyle = 'rgba(139,106,77,.45)';
  // ctx.lineWidth = 2;
  // ctx.beginPath();
  // if (opening.wall === 'top' || opening.wall === 'bottom') {
  //   const startX = seg.x1;
  //   const startY = seg.y1;
  //   ctx.moveTo(startX, startY);
  //   ctx.lineTo(startX + nx * length, startY + inwardY * doorDepth);
  //   // ctx.arc(startX, startY, length, inwardY > 0 ? 0 : Math.PI, inwardY > 0 ? Math.PI / 2 : -Math.PI / 2, inwardY <= 0);
  // } else {
  //   const startX = seg.x1;
  //   const startY = seg.y1;
  //   ctx.moveTo(startX, startY);
  //   ctx.lineTo(startX + inwardX * doorDepth, startY + ny * length);
  //   // ctx.arc(startX, startY, length, inwardX > 0 ? -Math.PI / 2 : Math.PI / 2, inwardX > 0 ? 0 : Math.PI, inwardX <= 0);
  // }
  // ctx.stroke();

  if (active) {
    ctx.strokeStyle = '#ef4444';
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(seg.x1, seg.y1);
    ctx.lineTo(seg.x2, seg.y2);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.restore();
}

function drawWindowSymbol(seg, active) {
  const dx = seg.x2 - seg.x1;
  const dy = seg.y2 - seg.y1;
  const length = Math.hypot(dx, dy) || 1;
  const nx = dx / length;
  const ny = dy / length;

  const px = -ny;
  const py = nx;

  ctx.save();

  // 窗外框主线
  ctx.strokeStyle = '#7dc7ff';
  ctx.lineWidth = 8;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(seg.x1, seg.y1);
  ctx.lineTo(seg.x2, seg.y2);
  ctx.stroke();

  // 玻璃高光线
  ctx.strokeStyle = 'rgba(255,255,255,0.95)';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(seg.x1, seg.y1);
  ctx.lineTo(seg.x2, seg.y2);
  ctx.stroke();

  // 两条分隔线，增强“窗”的视觉效果
  const t1x = seg.x1 + nx * (length * 0.33);
  const t1y = seg.y1 + ny * (length * 0.33);
  const t2x = seg.x1 + nx * (length * 0.66);
  const t2y = seg.y1 + ny * (length * 0.66);
  const crossLen = 14;

  ctx.strokeStyle = '#eaf6ff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(t1x - px * crossLen / 2, t1y - py * crossLen / 2);
  ctx.lineTo(t1x + px * crossLen / 2, t1y + py * crossLen / 2);
  ctx.moveTo(t2x - px * crossLen / 2, t2y - py * crossLen / 2);
  ctx.lineTo(t2x + px * crossLen / 2, t2y + py * crossLen / 2);
  ctx.stroke();

  if (active) {
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(seg.x1, seg.y1);
    ctx.lineTo(seg.x2, seg.y2);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.restore();
}

function drawOpenings(v) {
  state.openings.forEach(opening => {
    const room = state.rooms.find(r => r.id === opening.room_id);
    if (!room) return;
    const seg = openingSegment(room, opening, v);
    const active = selected?.type === 'opening' && selected?.id === opening.id;
    if (opening.type === 'door') drawDoorSymbol(seg, opening, active);
    else drawWindowSymbol(seg, active);
  });
}

function drawSofaSymbol(x, y, w, h) {
  ctx.fillStyle = 'rgba(255,255,255,0.22)';
  ctx.fillRect(x + 6, y + 6, w - 12, h - 12);
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.fillRect(x + 10, y + 10, w - 20, Math.max(10, h * 0.2));
  ctx.fillRect(x + 10, y + 10, Math.max(10, w * 0.16), h - 20);
  ctx.fillRect(x + w - 10 - Math.max(10, w * 0.16), y + 10, Math.max(10, w * 0.16), h - 20);
}

function drawTableSymbol(x, y, w, h) {
  ctx.strokeStyle = 'rgba(15,23,42,0.55)';
  ctx.lineWidth = 1.2;
  ctx.strokeRect(x + 8, y + 8, w - 16, h - 16);
}

function drawWardrobeSymbol(x, y, w, h) {
  ctx.strokeStyle = 'rgba(15,23,42,0.5)';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x + w / 2, y + 6);
  ctx.lineTo(x + w / 2, y + h - 6);
  ctx.stroke();
}

function drawPlantSymbol(x, y, w, h) {
  ctx.fillStyle = 'rgba(120,70,30,0.8)';
  ctx.fillRect(x + w * 0.34, y + h * 0.62, w * 0.32, h * 0.2);
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.beginPath();
  ctx.arc(x + w / 2, y + h * 0.36, Math.min(w, h) * 0.22, 0, Math.PI * 2);
  ctx.fill();
}

function drawBedSymbol(x, y, w, h) {
  ctx.fillStyle = 'rgba(255,255,255,0.65)';
  ctx.fillRect(x + 8, y + 8, w - 16, h - 16);
  ctx.strokeStyle = 'rgba(15,23,42,0.6)';
  ctx.strokeRect(x + 8, y + 8, w - 16, h - 16);
}

function drawBathSymbol(x, y, w, h) {
  ctx.strokeStyle = 'rgba(255,255,255,.85)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.roundRect(x + 8, y + 10, w - 16, h - 20, 12);
  ctx.stroke();
}

function drawFurniture(item, v) {
  if (isWallFurniture(item)) {
    const room = state?.rooms?.find(r => r.id === item.room_id);
    if (!room) return;
    const wall = item.wall || 'top';
    const offset = clampWallOffset(room, wall, item.wall_offset || 0.3);
    const center = wallPlacementToWorld(room, wall, offset, item.mount_height || 1.5);
    const cx = toCanvasX(center.x, v);
    const cy = toCanvasY(center.y, v);
    const horizontal = wall === 'top' || wall === 'bottom';
    const len = Math.max(20, (horizontal ? item.width : item.depth) * v.scale);
    const active = selected?.type === 'furniture' && selected?.id === item.id;
    ctx.save();
    ctx.lineCap = 'round';
    ctx.strokeStyle = active ? '#ef4444' : '#3165f5';
    ctx.lineWidth = active ? 5 : 4;
    ctx.beginPath();
    if (horizontal) {
      ctx.moveTo(cx - len / 2, cy);
      ctx.lineTo(cx + len / 2, cy);
    } else {
      ctx.moveTo(cx, cy - len / 2);
      ctx.lineTo(cx, cy + len / 2);
    }
    ctx.stroke();
    ctx.fillStyle = active ? '#7f1d1d' : '#1d4ed8';
    ctx.font = 'bold 12px "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(item.label, cx, cy - 8);
    ctx.restore();
    return;
  }
  const fp = furnitureFootprint(item);
  const x = toCanvasX(item.x, v);
  const y = toCanvasY(item.y, v);
  const w = fp.width * v.scale;
  const h = fp.depth * v.scale;
  const active = selected?.type === 'furniture' && selected?.id === item.id;
  const isCollision = previewState.collision && previewState.collisionId === item.id;

  ctx.save();
  ctx.fillStyle = item.color;
  ctx.strokeStyle = isCollision ? '#d03434' : active ? '#ef4444' : '#334155';
  ctx.lineWidth = active || isCollision ? 3 : 1.6;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);

  if (['bedBunk', 'bedDouble', 'bedSingle', 'cabinetBed', 'cabinetBedDrawerTable'].includes(item.type)) {
    drawBedSymbol(x, y, w, h);
  } else if ([
    'benchCushion', 'chairCushion', 'chairModernCushion', 'chairRounded',
    'loungeChair', 'loungeChairRelax', 'loungeDesignChair',
    'loungeDesignSofa', 'loungeDesignSofaCorner', 'loungeSofa', 'loungeSofaLong'
  ].includes(item.type)) {
    drawSofaSymbol(x, y, w, h);
  } else if ([
    'tableCoffee', 'tableCoffeeGlass', 'kitchenBar', 'desk', 'table', 'tableGlass', 'tableRound'
  ].includes(item.type)) {
    drawTableSymbol(x, y, w, h);
  } else if ([
    'bathroomCabinet', 'kitchenCabinet', 'kitchenCabinetDrawer',
    'bookcaseClosedDoors', 'bookcaseClosedWide', 'bookcaseOpenLow',
    'cabinetTelevision', 'cabinetTelevisionDoors', 'coatRack', 'coatRackStanding'
  ].includes(item.type)) {
    drawWardrobeSymbol(x, y, w, h);
  } else if ([
    'plantSmall1', 'plantSmall2', 'plantSmall3', 'pottedPlant'
  ].includes(item.type)) {
    drawPlantSymbol(x, y, w, h);
  } else if ([
    'bathtub', 'toilet', 'shower', 'showerRound', 'bathroomSink', 'kitchenSink'
  ].includes(item.type)) {
    drawBathSymbol(x, y, w, h);
  }

  ctx.fillStyle = active ? '#7f1d1d' : '#0f172a';
  ctx.font = '12px "PingFang SC", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(item.label, x + w / 2, y + h / 2 + 4);
  ctx.restore();
}

function drawSnapLines(v) {
  if (!previewState.snapLines.length) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(59,130,246,.65)';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([8, 5]);
  previewState.snapLines.forEach(line => {
    if (line.kind === 'vertical') {
      const x = toCanvasX(line.value, v);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, v.ch);
      ctx.stroke();
    } else {
      const y = toCanvasY(line.value, v);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(v.cw, y);
      ctx.stroke();
    }
  });
  ctx.setLineDash([]);
  ctx.restore();
}

function drawPlacementPreview(v) {
  if (!pendingPlacementType || !previewState.hoverPlacement) return;
  const meta = getFurnitureMeta(pendingPlacementType);
  if (!meta) return;
  const item = {
    id: '__preview__',
    type: pendingPlacementType,
    label: meta.label,
    room_id: previewState.hoverPlacement.room.id,
    x: previewState.hoverPlacement.x,
    y: previewState.hoverPlacement.y,
    width: meta.width,
    depth: meta.depth,
    rotation: 0,
    color: meta.color,
    material: meta.material,
    placement: previewState.hoverPlacement.placement || 'floor',
    wall: previewState.hoverPlacement.wall,
    wall_offset: previewState.hoverPlacement.wall_offset,
    mount_height: meta.defaultMountHeight || meta.yOffset || 1.5,
  };
  if (item.placement === 'wall') {
    drawFurniture(item, v);
    return;
  }
  applyFurnitureLocalPlacement(item);

  const fp = furnitureFootprint(item);
  const x = toCanvasX(item.x, v);
  const y = toCanvasY(item.y, v);
  const w = fp.width * v.scale;
  const h = fp.depth * v.scale;

  ctx.save();
  ctx.globalAlpha = 0.6;
  ctx.fillStyle = previewState.collision ? '#fca5a5' : meta.color;
  ctx.strokeStyle = previewState.collision ? '#dc2626' : '#2563eb';
  ctx.lineWidth = 2;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.restore();
}

function render2D() {
  if (!state) return;
  const v = getViewport();
  previewState.snapLines = drag.kind === 'furniture' || pendingPlacementType ? previewState.snapLines : [];
  ctx.clearRect(0, 0, v.cw, v.ch);
  const bg = ctx.createLinearGradient(0, 0, 0, v.ch);
  bg.addColorStop(0, '#fbfdff');
  bg.addColorStop(1, '#f3f7fb');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, v.cw, v.ch);

  drawGrid(v);
  state.rooms.forEach(room => drawRoom(room, v));
  drawOpenings(v);
  state.furnitures.forEach(item => drawFurniture(item, v));
  drawSnapLines(v);
  drawPlacementPreview(v);
  
  // 绘制1手势光标
  if (gestureState.cursorVisible) {
    const cursorX = gestureState.cursorX || v.cw / 2;
    const cursorY = gestureState.cursorY || v.ch / 2;
    
    // 绘制光标外圈
    ctx.beginPath();
    ctx.arc(cursorX, cursorY, 15, 0, 2 * Math.PI);
    ctx.strokeStyle = '#0066ff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 绘制光标内圈
    ctx.beginPath();
    ctx.arc(cursorX, cursorY, 5, 0, 2 * Math.PI);
    ctx.fillStyle = '#0066ff';
    ctx.fill();
  }
}

function materialFromName(color, materialName) {
  const params = { color, roughness: 0.72, metalness: 0.08 };
  if (materialName === '金属') { params.roughness = 0.28; params.metalness = 0.82; }
  if (materialName === '玻璃') { params.roughness = 0.06; params.metalness = 0.1; params.transparent = true; params.opacity = 0.55; }
  if (materialName === '皮质') { params.roughness = 0.55; }
  if (materialName === '石材' || materialName === '大理石') { params.roughness = 0.92; }
  return new THREE.MeshStandardMaterial(params);
}

function initThree() {
  if (renderer) return;
  scene = new THREE.Scene();
  scene.background = new THREE.Color('#f3f7fb');

  camera = new THREE.PerspectiveCamera(52, el.threeContainer.clientWidth / el.threeContainer.clientHeight, 0.1, 2000);
  camera.position.set(12, 11, 12);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(el.threeContainer.clientWidth, el.threeContainer.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  el.threeContainer.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = true;
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 2;
  controls.maxDistance = 80;
  controls.minPolarAngle = 0.05;
  controls.maxPolarAngle = Math.PI / 2 - 0.04;
  controls.target.set(3.5, 0.8, 3.5);
  controls.mouseButtons.LEFT = THREE.MOUSE.PAN;
  controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
  controls.update();

  fpControls = new PointerLockControls(camera, renderer.domElement);
  firstPersonClock = new THREE.Clock();
  fpControls.addEventListener('lock', () => {
    isFirstPersonMode = true;
    controls.enabled = false;
    el.threeContainer?.classList.add('first-person-active');
    el.firstPersonBtn?.classList.add('active');
    el.editModeBtn?.classList.remove('active');
    setMessage('已进入第一人称：鼠标查看，WASD 移动，可穿墙进入其他房间，ESC 退出', 'info');
  });
  fpControls.addEventListener('unlock', () => {
    isFirstPersonMode = false;
    controls.enabled = true;
    el.threeContainer?.classList.remove('first-person-active');
    el.firstPersonBtn?.classList.remove('active');
    el.editModeBtn?.classList.add('active');
    Object.keys(firstPersonKeys).forEach(key => { firstPersonKeys[key] = false; });
  });

  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  gltfLoader = new GLTFLoader();

  scene.add(new THREE.AmbientLight(0xffffff, 1.25));
  const dir = new THREE.DirectionalLight(0xffffff, 1.15);
  dir.position.set(12, 18, 10);
  dir.castShadow = true;
  dir.shadow.mapSize.set(2048, 2048);
  scene.add(dir);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(120, 120),
    new THREE.MeshStandardMaterial({ color: '#e6eef7' })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.02;
  floor.receiveShadow = true;
  scene.add(floor);

  renderer.domElement.addEventListener('pointerdown', onThreePointerDown);
  renderer.domElement.addEventListener('pointermove', onThreePointerMove);
  renderer.domElement.addEventListener('pointerup', onThreePointerUp);
  renderer.domElement.addEventListener('pointerleave', onThreePointerUp);
  renderer.domElement.addEventListener('pointercancel', onThreePointerUp);

  const animate = () => {
    requestAnimationFrame(animate);
    const delta = firstPersonClock ? firstPersonClock.getDelta() : 0.016;
    if (isFirstPersonMode) updateFirstPersonMovement(delta);
    else controls.update();
    renderer.render(scene, camera);
  };
  animate();
}

function resize3DRenderer() {
  if (!renderer || !camera || !el.threeContainer) return;
  const w = Math.max(1, el.threeContainer.clientWidth);
  const h = Math.max(1, el.threeContainer.clientHeight);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function getPlanBoundsWithMargin(margin = 0.45) {
  if (!state?.rooms?.length) return null;
  return {
    minX: Math.min(...state.rooms.map(room => Number(room.x || 0))) - margin,
    maxX: Math.max(...state.rooms.map(room => Number(room.x || 0) + Number(room.width || 0))) + margin,
    minZ: Math.min(...state.rooms.map(room => Number(room.y || 0))) - margin,
    maxZ: Math.max(...state.rooms.map(room => Number(room.y || 0) + Number(room.depth || 0))) + margin,
  };
}

function limitFirstPersonToPlanBounds(position) {
  const bounds = getPlanBoundsWithMargin(0.55);
  if (!bounds) return position;
  position.x = clamp(position.x, bounds.minX, bounds.maxX);
  position.z = clamp(position.z, bounds.minZ, bounds.maxZ);
  return position;
}

function enterFirstPersonMode() {
  if (!fpControls || !camera || !state?.rooms?.length) return;
  savedOrbitView = {
    position: camera.position.clone(),
    target: controls?.target?.clone(),
  };
  const room = selectedRoom() || state.rooms[0];
  camera.position.set(room.x + room.width / 2, FIRST_PERSON_HEIGHT, room.y + room.depth / 2);
  camera.rotation.set(0, 0, 0);
  fpControls.lock();
}

function exitFirstPersonMode() {
  if (fpControls?.isLocked) fpControls.unlock();
  if (savedOrbitView && camera && controls) {
    camera.position.copy(savedOrbitView.position);
    if (savedOrbitView.target) controls.target.copy(savedOrbitView.target);
    controls.update();
  }
}

function updateFirstPersonMovement(delta) {
  if (!isFirstPersonMode || !fpControls?.isLocked || !camera) return;
  const speed = 2.8;
  const moveDistance = speed * delta;
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  forward.y = 0;
  if (forward.lengthSq() === 0) return;
  forward.normalize();
  const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();
  const move = new THREE.Vector3();
  if (firstPersonKeys.forward) move.add(forward);
  if (firstPersonKeys.backward) move.sub(forward);
  if (firstPersonKeys.right) move.add(right);
  if (firstPersonKeys.left) move.sub(right);
  if (move.lengthSq() === 0) {
    camera.position.y = FIRST_PERSON_HEIGHT;
    return;
  }
  move.normalize().multiplyScalar(moveDistance);
  const nextPosition = camera.position.clone().add(move);
  camera.position.copy(limitFirstPersonToPlanBounds(nextPosition));
  camera.position.y = FIRST_PERSON_HEIGHT;
}

function clearMeshes(map) {
  map.forEach(mesh => scene.remove(mesh));
  map.clear();
}

function createPart(geometry, color, materialName, x, y, z) {
  const mesh = new THREE.Mesh(geometry, materialFromName(color, materialName));
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function normalizeModelRoot(source) {
  const root = source.clone(true);
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  root.position.x -= center.x;
  root.position.y -= box.min.y;
  root.position.z -= center.z;
  return { root, size };
}

function toRenderableMaterial(mat) {
  const material = new THREE.MeshStandardMaterial({
    color: (mat && mat.color && mat.color.isColor) ? mat.color.clone() : new THREE.Color('#cfcfcf'),
    roughness: typeof mat?.roughness === 'number' ? mat.roughness : 0.78,
    metalness: typeof mat?.metalness === 'number' ? mat.metalness : 0.08,
    transparent: !!mat?.transparent,
    opacity: typeof mat?.opacity === 'number' ? mat.opacity : 1,
    side: THREE.DoubleSide,
  });

  if (mat?.map) material.map = mat.map;
  if (mat?.normalMap) material.normalMap = mat.normalMap;
  if (mat?.roughnessMap) material.roughnessMap = mat.roughnessMap;
  if (mat?.metalnessMap) material.metalnessMap = mat.metalnessMap;
  if (mat?.emissiveMap) material.emissiveMap = mat.emissiveMap;
  if (mat?.aoMap) material.aoMap = mat.aoMap;

  material.emissive = new THREE.Color(0x000000);
  material.emissiveIntensity = 0;
  material.needsUpdate = true;

  return material;
}

function sanitizeModelMaterials(root) {
  root.traverse(child => {
    if (!child.isMesh) return;

    if (Array.isArray(child.material)) {
      child.material = child.material.map(mat => toRenderableMaterial(mat));
    } else {
      child.material = toRenderableMaterial(child.material);
    }

    child.geometry = child.geometry.clone();

    child.castShadow = true;
    child.receiveShadow = true;
  });
}

function loadModel(url) {
  if (modelCache.has(url)) return modelCache.get(url);
  const promise = new Promise((resolve, reject) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const normalized = normalizeModelRoot(gltf.scene);
        modelCache.set(url, Promise.resolve(normalized));
        resolve(normalized);
      },
      undefined,
      (error) => reject(error)
    );
  });
  modelCache.set(url, promise);
  return promise;
}

async function buildFurnitureGroup(item) {
  try {
    const config = getFurnitureModelConfig(item.type);
    if (!config || !config.url) {
      console.warn(`未找到家具类型 ${item.type} 对应的模型配置`);
      return new THREE.Group();
    }
    const { root: cachedRoot, size } = await loadModel(config.url);

  const group = new THREE.Group();
  const root = cachedRoot.clone(true);

  // 关键修复：把 glb 子网格材质统一转成稳定可渲染材质
  sanitizeModelMaterials(root);

  group.add(root);

  const safeX = Math.max(size.x || 0, 0.01);
  const safeY = Math.max(size.y || 0, 0.01);
  const safeZ = Math.max(size.z || 0, 0.01);

  group.scale.set(
    item.width / safeX,
    Math.max(item.height || safeY, 0.1) / safeY,
    item.depth / safeZ
  );

  const fp = furnitureFootprint(item);
  if (isWallFurniture(item)) {
    const room = state?.rooms?.find(r => r.id === item.room_id);
    const wall = item.wall || 'top';
    const mountHeight = clampMountHeight(room, item.mount_height || config.defaultMountHeight || 1.5, config.defaultMountHeight || 1.5);
    if (room) {
      const placement = wallPlacementToWorld(room, wall, item.wall_offset || 0.3, mountHeight);
      const inset = 0.055;
      let px = placement.x;
      let pz = placement.y;
      if (wall === 'top') pz += inset;
      if (wall === 'bottom') pz -= inset;
      if (wall === 'left') px += inset;
      if (wall === 'right') px -= inset;
      group.position.set(px, mountHeight, pz);
      group.rotation.y = THREE.MathUtils.degToRad((placement.rotation || 0) + (config.rotationOffset || 0));
    } else {
      group.position.set(item.x, mountHeight, item.y);
      group.rotation.y = THREE.MathUtils.degToRad((item.rotation || 0) + (config.rotationOffset || 0));
    }
  } else {
    group.rotation.y = THREE.MathUtils.degToRad((item.rotation || 0) + (config.rotationOffset || 0));
    group.position.set(item.x + fp.width / 2, config.yOffset || 0, item.y + fp.depth / 2);
  }
  group.userData = { type: 'furniture', id: item.id, placement: item.placement || 'floor' };

  group.traverse(child => {
    child.userData = { type: 'furniture', id: item.id };
  });

  return group;
  } catch (error) {
    console.warn('构建家具组失败:', item.type, item.label, error);
    return new THREE.Group();
  }
}

function createOpeningMesh(room, opening) {
  const group = new THREE.Group();
  const isDoor = opening.type === 'door';

  const roomOffsetX = room.x || 0;
  const roomOffsetZ = room.y || 0;
  const frameMat = new THREE.MeshStandardMaterial({
    color: isDoor ? 0x8b6b3f : 0xe5e7eb,
    roughness: 0.72,
    metalness: 0.08,
    transparent: !isDoor,
    opacity: isDoor ? 1 : 0.95
  });

  const fillMat = new THREE.MeshStandardMaterial({
    color: isDoor ? 0xa67c52 : 0x9fd3ff,
    roughness: isDoor ? 0.78 : 0.18,
    metalness: isDoor ? 0.05 : 0.12,
    transparent: !isDoor,
    opacity: isDoor ? 1 : 0.58
  });

  const thickness = 0.18;
  const height = isDoor ? 2.15 : 1.2;
  const sill = isDoor ? 0 : 0.95;
  const frameThickness = Math.min(0.08, opening.width * 0.18);
  const yCenter = sill + height / 2;

  const addPart = (geometry, x, y, z, material = frameMat) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.position.set(x, y, z);
    group.add(mesh);
    return mesh;
  };

  if (opening.wall === 'top' || opening.wall === 'bottom') {
    const z = opening.wall === 'top'
      ? room.y + thickness / 2
      : room.y + room.depth - thickness / 2;

    const centerX = room.x + opening.offset + opening.width / 2;


    // 左右边框
    addPart(
      new THREE.BoxGeometry(frameThickness, height, thickness * 0.8),
      centerX - opening.width / 2 + frameThickness / 2,
      yCenter,
      z
    );
    addPart(
      new THREE.BoxGeometry(frameThickness, height, thickness * 0.8),
      centerX + opening.width / 2 - frameThickness / 2,
      yCenter,
      z
    );

    // 上边框
    addPart(
      new THREE.BoxGeometry(opening.width, frameThickness, thickness * 0.8),
      centerX,
      sill + height - frameThickness / 2,
      z
    );

    // 下边框（窗才有完整边框，门默认不开底框）
    if (!isDoor) {
      addPart(
        new THREE.BoxGeometry(opening.width, frameThickness, thickness * 0.8),
        centerX,
        sill + frameThickness / 2,
        z
      );
    }

    if (isDoor) {
      addPart(
        new THREE.BoxGeometry(opening.width * 0.94, height * 0.96, thickness * 0.55),
        centerX,
        yCenter,
        z,
        fillMat
      );
    } else {
      addPart(
        new THREE.BoxGeometry(opening.width * 0.92, height * 0.9, thickness * 0.45),
        centerX,
        yCenter,
        z,
        fillMat
      );

      // 窗中竖挺
      addPart(
        new THREE.BoxGeometry(0.04, height * 0.88, thickness * 0.6),
        centerX,
        yCenter,
        z
      );

      // 窗中横挺
      addPart(
        new THREE.BoxGeometry(opening.width * 0.88, 0.04, thickness * 0.6),
        centerX,
        yCenter,
        z
      );
    }
  } else {
    const x = opening.wall === 'right'
      ? room.x + room.width - thickness / 2
      : room.x + thickness / 2;

    const centerZ = room.y + opening.offset + opening.width / 2;


    // 前后边框
    addPart(
      new THREE.BoxGeometry(thickness * 0.8, height, frameThickness),
      x,
      yCenter,
      centerZ - opening.width / 2 + frameThickness / 2
    );
    addPart(
      new THREE.BoxGeometry(thickness * 0.8, height, frameThickness),
      x,
      yCenter,
      centerZ + opening.width / 2 - frameThickness / 2
    );

    // 上边框
    addPart(
      new THREE.BoxGeometry(thickness * 0.8, frameThickness, opening.width),
      x,
      sill + height - frameThickness / 2,
      centerZ
    );

    // 下边框（窗才有）
    if (!isDoor) {
      addPart(
        new THREE.BoxGeometry(thickness * 0.8, frameThickness, opening.width),
        x,
        sill + frameThickness / 2,
        centerZ
      );
    }

    if (isDoor) {
      addPart(
        new THREE.BoxGeometry(thickness * 0.55, height * 0.96, opening.width * 0.94),
        x,
        yCenter,
        centerZ,
        fillMat
      );
    } else {
      addPart(
        new THREE.BoxGeometry(thickness * 0.45, height * 0.9, opening.width * 0.92),
        x,
        yCenter,
        centerZ,
        fillMat
      );

      // 窗中竖挺（侧墙方向）
      addPart(
        new THREE.BoxGeometry(thickness * 0.6, height * 0.88, 0.04),
        x,
        yCenter,
        centerZ
      );

      // 窗中横挺
      addPart(
        new THREE.BoxGeometry(thickness * 0.6, 0.04, opening.width * 0.88),
        x,
        yCenter,
        centerZ
      );
    }
  }

  group.userData = { type: 'opening', id: opening.id };
  
  // 为所有子 mesh 设置相同的 userData
  group.traverse(child => {
    if (child.isMesh) {
      child.userData = { type: 'opening', id: opening.id };
    }
  });
  
  return group;
}

function fitCameraToRooms(force = false) {
  if (!controls || !state?.rooms.length) return;
  if (!force && !fitCameraPending) return;
  const bounds = getBounds();
  const center = new THREE.Vector3((bounds.minX + bounds.maxX) / 2, 0.8, (bounds.minY + bounds.maxY) / 2);
  const span = Math.max(bounds.width, bounds.height);
  const distance = Math.max(6, span * 1.35);
  camera.position.set(center.x + distance * 0.95, Math.max(7, distance * 0.82), center.z + distance * 0.95);
  controls.target.copy(center);
  controls.update();
  fitCameraPending = false;
}

async function render3D() {
  if (!scene || !state) return;
  const token = ++render3DToken;
  clearMeshes(roomMeshes);
  clearMeshes(furnitureGroups);
  clearMeshes(openingMeshes);

  state.rooms.forEach(room => {
    const group = new THREE.Group();

    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(room.width, 0.06, room.depth),
      materialFromName('#d8d0bd', '木纹')
    );
    floor.position.set(room.x + room.width / 2, 0.03, room.y + room.depth / 2);
    floor.receiveShadow = true;
    group.add(floor);

    const wallMaterial = materialFromName(room.wall_color || '#d7d8dd', '白色瓷砖');
    const t = 0.08;
    const h = Number(room.height || 3);
    const walls = [
      [room.width, h, t, room.x + room.width / 2, h / 2, room.y],
      [room.width, h, t, room.x + room.width / 2, h / 2, room.y + room.depth],
      [t, h, room.depth, room.x, h / 2, room.y + room.depth / 2],
      [t, h, room.depth, room.x + room.width, h / 2, room.y + room.depth / 2],
    ];

    walls.forEach(([ww, hh, dd, x, yy, z], index) => {
      const wall = new THREE.Mesh(new THREE.BoxGeometry(ww, hh, dd), wallMaterial);
      wall.position.set(x, yy, z);
      wall.castShadow = true;
      wall.receiveShadow = true;
      wall.userData = { type: 'wall', roomId: room.id, wall: ['top', 'bottom', 'left', 'right'][index] };
      group.add(wall);
    });

    scene.add(group);
    roomMeshes.set(room.id, group);
  });

  state.openings.forEach(opening => {
    const room = state.rooms.find(r => r.id === opening.room_id);
    if (!room) return;
    const group = createOpeningMesh(room, opening);
    scene.add(group);
    openingMeshes.set(opening.id, group);
  });

  for (const item of state.furnitures) {
    try {
      const group = await buildFurnitureGroup(item);
      if (token !== render3DToken) return;
      scene.add(group);
      furnitureGroups.set(item.id, group);
    } catch (error) {
      console.warn('家具3D加载失败:', item.type, item.label, error);
    }
  }

  furnitureGroups.forEach((group, id) => {
    group.traverse(child => {
      if (child.material) {
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        materials.forEach(material => {
          if (material && material.emissive) {
            const isSelected = id === selected?.id && selected?.type === 'furniture';
            const isCollision = previewState.collision && previewState.collisionId === id;
            material.emissive.setHex(isCollision ? 0x8f1717 : isSelected ? 0x2b1a10 : 0x000000);
            material.emissiveIntensity = isCollision ? 0.32 : isSelected ? 0.18 : 0;
          }
        });
      }
    });
  });

  fitCameraToRooms();
}

function setThreePointerFromEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
}

function intersectFurnitureFromEvent(event) {
  if (!renderer || !camera || !raycaster) return null;
  setThreePointerFromEvent(event);
  const intersects = raycaster.intersectObjects([...furnitureGroups.values()], true);
  return intersects[0] || null;
}

function intersectOpeningFromEvent(event) {
  if (!renderer || !camera || !raycaster) return null;
  setThreePointerFromEvent(event);
  const intersects = raycaster.intersectObjects([...openingMeshes.values()], true);
  return intersects[0] || null;
}

function threeGroundPoint(event) {
  if (!raycaster) return null;
  setThreePointerFromEvent(event);
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hitPoint = new THREE.Vector3();
  if (!raycaster.ray.intersectPlane(plane, hitPoint)) return null;
  return hitPoint;
}

function threeWallHit(event) {
  if (!raycaster || !state) return null;
  setThreePointerFromEvent(event);
  const intersects = raycaster.intersectObjects([...roomMeshes.values()], true);
  for (const hit of intersects) {
    const data = hit.object?.userData || {};
    if (data.type !== 'wall' || !data.roomId || !data.wall) continue;
    const room = state.rooms.find(r => r.id === data.roomId);
    if (!room) continue;
    const point = hit.point;
    const wall = data.wall;
    const rawOffset = (wall === 'top' || wall === 'bottom') ? point.x - room.x : point.z - room.y;
    return { room, wall, offset: clampWallOffset(room, wall, rawOffset), point };
  }
  return null;
}

function startThreeFurnitureDrag(event, item) {
  const hitPoint = threeGroundPoint(event);
  selected = { type: 'furniture', id: item.id };
  threeDrag.active = true;
  threeDrag.type = 'furniture';
  threeDrag.id = item.id;
  if (isWallFurniture(item)) {
    threeDrag.offsetX = 0;
    threeDrag.offsetY = 0;
  } else {
    if (!hitPoint) return false;
    threeDrag.offsetX = hitPoint.x - item.x;
    threeDrag.offsetY = hitPoint.z - item.y;
  }
  threeDrag.moved = false;
  controls.enabled = false;
  renderer.domElement.style.cursor = 'grabbing';
  syncUI();
  render2D();
  render3D();
  return true;
}

function startThreeOpeningDrag(event, opening) {
  selected = { type: 'opening', id: opening.id };
  threeDrag.active = true;
  threeDrag.type = 'opening';
  threeDrag.id = opening.id;
  threeDrag.moved = false;
  controls.enabled = false;
  renderer.domElement.style.cursor = 'grabbing';
  syncUI();
  render2D();
  render3D();
  return true;
}

function stopThreeFurnitureDrag() {
  threeDrag.active = false;
  threeDrag.id = null;
  threeDrag.type = null;
  threeDrag.offsetX = 0;
  threeDrag.offsetY = 0;
  threeDrag.moved = false;
  previewState.snapLines = [];
  previewState.collision = false;
  if (controls) controls.enabled = true;
  if (renderer?.domElement) renderer.domElement.style.cursor = '';
}

async function commitThreeFurnitureDrag() {
  const item = state?.furnitures.find(f => f.id === threeDrag.id);
  if (!item) {
    stopThreeFurnitureDrag();
    return;
  }
  applyFurnitureLocalPlacement(item);
  const dragId = threeDrag.id;
  stopThreeFurnitureDrag();
  await request(`/api/furniture/${dragId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      label: item.label,
      x: item.x,
      y: item.y,
      width: item.width,
      depth: item.depth,
      rotation: item.rotation,
      room_id: item.room_id,
      color: item.color,
      material: item.material,
      type: item.type,
      placement: item.placement || 'floor',
      wall: item.wall,
      wall_offset: item.wall_offset,
      mount_height: item.mount_height,
    })
  });
}

async function commitThreeOpeningDrag() {
  const opening = state?.openings.find(o => o.id === threeDrag.id);
  if (!opening) {
    stopThreeFurnitureDrag();
    return;
  }
  const dragId = threeDrag.id;
  stopThreeFurnitureDrag();
  await request(`/api/opening/${dragId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      name: opening.name,
      offset: opening.offset,
      width: opening.width,
      height: opening.height,
      sill: opening.sill,
      color: opening.color,
      material: opening.material,
    })
  });
}

function onThreePointerDown(event) {
  if (isFirstPersonMode) return;
  threeClickState.down = true;
  threeClickState.x = event.clientX;
  threeClickState.y = event.clientY;
  if (event.button !== 0) return;
  if (pendingPlacementType) return;

  // 先检测门窗
  const openingHit = intersectOpeningFromEvent(event);
  const openingId = openingHit?.object?.userData?.id;
  const opening = openingId ? state?.openings.find(o => o.id === openingId) : null;
  if (opening) {
    event.preventDefault();
    startThreeOpeningDrag(event, opening);
    return;
  }

  // 再检测家具
  const furnitureHit = intersectFurnitureFromEvent(event);
  const furnitureId = furnitureHit?.object?.userData?.id;
  const item = furnitureId ? state?.furnitures.find(f => f.id === furnitureId) : null;
  if (!item) return;
  event.preventDefault();
  startThreeFurnitureDrag(event, item);
}

function onThreePointerMove(event) {
  if (!renderer || !state) return;
  if (threeDrag.active) {
    if (threeDrag.type === 'furniture') {
      const item = state.furnitures.find(f => f.id === threeDrag.id);
      if (!item) return;
      if (isWallFurniture(item)) {
        const wallHit = threeWallHit(event);
        if (!wallHit) return;
        item.room_id = wallHit.room.id;
        item.wall = wallHit.wall;
        item.wall_offset = +wallHit.offset.toFixed(2);
        item.x = wallHit.point.x;
        item.y = wallHit.point.z;
      } else {
        const hitPoint = threeGroundPoint(event);
        if (!hitPoint) return;
        item.x = +(hitPoint.x - threeDrag.offsetX).toFixed(1);
        item.y = +(hitPoint.z - threeDrag.offsetY).toFixed(1);
        applyFurnitureLocalPlacement(item);
      }
      threeDrag.moved = true;
      syncUI();
      render2D();
      render3D();
      return;
    } else if (threeDrag.type === 'opening') {
      const hitPoint = threeGroundPoint(event);
      if (!hitPoint) return;
      const opening = state.openings.find(o => o.id === threeDrag.id);
      if (!opening) return;
      const room = state.rooms.find(r => r.id === opening.room_id);
      if (!room) return;
      
      // 沿墙体移动门窗
      if (opening.wall === 'top' || opening.wall === 'bottom') {
        // 上墙或下墙，修改横向 offset
        let newOffset = hitPoint.x - room.x - opening.width / 2;
        newOffset = Math.max(0, Math.min(newOffset, room.width - opening.width));
        opening.offset = +newOffset.toFixed(1);
      } else if (opening.wall === 'left' || opening.wall === 'right') {
        // 左墙或右墙，修改纵向 offset
        let newOffset = hitPoint.z - room.y - opening.width / 2;
        newOffset = Math.max(0, Math.min(newOffset, room.depth - opening.width));
        opening.offset = +newOffset.toFixed(1);
      }
      
      threeDrag.moved = true;
      syncUI();
      render2D();
      render3D();
      return;
    }
  }

  if (pendingPlacementType) {
    const meta = getFurnitureMeta(pendingPlacementType);
    if (!meta) return;
    if (meta.wallMount) {
      const wallHit = threeWallHit(event);
      previewState.hoverPlacement = wallHit ? { room: wallHit.room, x: wallHit.point.x, y: wallHit.point.z, wall: wallHit.wall, wall_offset: wallHit.offset, placement: 'wall' } : null;
    } else {
      const hitPoint = threeGroundPoint(event);
      if (!hitPoint) return;
      const temp = { x: hitPoint.x, y: hitPoint.z, width: meta.width, depth: meta.depth, rotation: 0 };
      const room = findRoomForFurniturePlacement(temp.x, temp.y, temp);
      previewState.hoverPlacement = room ? { room, x: temp.x, y: temp.y } : null;
    }
    render2D();
  }
}

async function onThreePointerUp(event) {
  if (!renderer || !state) return;
  if (threeDrag.active) {
    threeClickState.down = false;
    if (threeDrag.type === 'furniture') {
      await commitThreeFurnitureDrag();
    } else if (threeDrag.type === 'opening') {
      await commitThreeOpeningDrag();
    }
    return;
  }

  if (!threeClickState.down) return;
  threeClickState.down = false;
  const moved = Math.hypot(event.clientX - threeClickState.x, event.clientY - threeClickState.y);
  if (moved > 4) return;

  if (pendingPlacementType) {
    const meta = getFurnitureMeta(pendingPlacementType);
    if (!meta) return;
    if (meta.wallMount) {
      const wallHit = threeWallHit(event);
      if (wallHit) await placePendingFurnitureOnWall(wallHit.room.id, wallHit.wall, wallHit.offset);
      return;
    }
    const hitPoint = threeGroundPoint(event);
    if (!hitPoint) return;
    const temp = { x: hitPoint.x, y: hitPoint.z, width: meta.width, depth: meta.depth, rotation: 0 };
    const room = findRoomForFurniturePlacement(temp.x, temp.y, temp);
    if (room) await placePendingFurnitureAt(temp.x, temp.y, room.id);
    return;
  }

  // 先检测门窗
  const openingHit = intersectOpeningFromEvent(event);
  const openingId = openingHit?.object?.userData?.id;
  if (openingId) {
    selected = { type: 'opening', id: openingId };
    syncUI();
    render2D();
    render3D();
    return;
  }

  // 再检测家具
  const furnitureHit = intersectFurnitureFromEvent(event);
  const furnitureId = furnitureHit?.object?.userData?.id;
  if (furnitureId) {
    selected = { type: 'furniture', id: furnitureId };
    syncUI();
    render2D();
    render3D();
    return;
  }

}

async function placePendingFurnitureOnWall(roomId, wall, wallOffset) {
  const meta = getFurnitureMeta(pendingPlacementType);
  const room = state?.rooms?.find(r => r.id === roomId);
  if (!meta || !room || !meta.wallMount) return;
  const offset = clampWallOffset(room, wall, wallOffset);
  const mountHeight = clampMountHeight(room, meta.defaultMountHeight || meta.yOffset || 1.5, 1.5);
  const placement = wallPlacementToWorld(room, wall, offset, mountHeight);
  const data = await request('/api/furniture', {
    method: 'POST',
    body: JSON.stringify({
      type: meta.value,
      room_id: roomId,
      placement: 'wall',
      wall,
      wall_offset: +offset.toFixed(2),
      mount_height: +mountHeight.toFixed(2),
      x: +placement.x.toFixed(2),
      y: +placement.y.toFixed(2),
      width: meta.width,
      depth: meta.depth,
      rotation: placement.rotation,
      color: meta.color,
      material: meta.material,
      label: meta.label,
    })
  });
  if (data.item) {
    selected = { type: 'furniture', id: data.item.id };
    preferredFurnitureType = meta.value;
    pendingPlacementType = null;
    previewState.hoverPlacement = null;
    previewState.snapLines = [];
    previewState.collision = false;
    syncUI();
    render2D();
    render3D();
  }
}

async function placePendingFurnitureAt(x, y, roomId) {
  const meta = getFurnitureMeta(pendingPlacementType);
  if (!meta || !roomId) return;
  const data = await request('/api/furniture', {
    method: 'POST',
    body: JSON.stringify({
      type: meta.value,
      room_id: roomId,
      x: +x.toFixed(1),
      y: +y.toFixed(1),
      width: meta.width,
      depth: meta.depth,
      rotation: 0,
      color: meta.color,
      material: meta.material,
      label: meta.label,
    })
  });
  if (data.item) {
    selected = { type: 'furniture', id: data.item.id };
    preferredFurnitureType = meta.value;
    pendingPlacementType = null;
    previewState.hoverPlacement = null;
    previewState.snapLines = [];
    previewState.collision = false;
    syncUI();
    render2D();
    render3D();
  }
}

el.planCanvas.addEventListener('mousedown', evt => {
  mouseDown = true;
  const point = canvasPoint(evt);

  // 鼠标点击时，取消手势光标的选中状态
  // 这里不需要实际取消选中，因为鼠标点击会重新设置选中状态
  
  if (pendingPlacementType) {
    const room = hitRoom(point.x, point.y);
    const meta = getFurnitureMeta(pendingPlacementType);
    if (room && meta) {
      const v = getViewport();
      const x = fromCanvasX(point.x, v);
      const y = fromCanvasY(point.y, v);
      if (meta.wallMount) {
        const wallHit = nearestWallFromPoint(room, x, y);
        placePendingFurnitureOnWall(room.id, wallHit.wall, wallHit.offset);
      } else {
        placePendingFurnitureAt(x, y, room.id);
      }
      return;
    }
  }

  const furniture = hitFurniture(point.x, point.y);
  if (furniture) {
    selected = { type: 'furniture', id: furniture.id };
    // 只设置选中状态，不立即开始拖动
    // 拖动将在mousemove事件中开始
    syncUI();
    render2D();
    render3D();
    return;
  }

  const opening = hitOpening(point.x, point.y);
  if (opening) {
    selected = { type: 'opening', id: opening.id };
    // 只设置选中状态，不立即开始拖动
    syncUI();
    render2D();
    render3D();
    return;
  }

  const room = hitRoom(point.x, point.y);
  if (room) {
    selected = { type: 'room', id: room.id };
    // 只设置选中状态，不立即开始拖动
    syncUI();
    render2D();
    render3D();
    return;
  }

  // 点击空白区域时，进入画布拖动模式
  drag.mode = 'move';
  drag.id = null;
  drag.kind = 'canvas';
  drag.startX = point.x;
  drag.startY = point.y;
  drag.startPanX = planPanX;
  drag.startPanY = planPanY;

  // 空白区域不强制改选中项，避免一拖动画布就跳选中
  render2D();
  return;
});

el.planCanvas.addEventListener('mousemove', evt => {
  const point = canvasPoint(evt);
  const v = getViewport();
  const rx = fromCanvasX(point.x, v);
  const ry = fromCanvasY(point.y, v);

  if (pendingPlacementType && !drag.mode) {
    const meta = getFurnitureMeta(pendingPlacementType);
    const room = hitRoom(point.x, point.y);
    if (room && meta) {
      if (meta.wallMount) {
        const wallHit = nearestWallFromPoint(room, rx, ry);
        const p = wallPlacementToWorld(room, wallHit.wall, wallHit.offset, meta.defaultMountHeight || meta.yOffset || 1.5);
        previewState.hoverPlacement = { room, x: p.x, y: p.y, wall: wallHit.wall, wall_offset: wallHit.offset, placement: 'wall' };
      } else {
        previewState.hoverPlacement = { room, x: rx, y: ry };
      }
    } else {
      previewState.hoverPlacement = null;
      previewState.snapLines = [];
      previewState.collision = false;
    }
    render2D();
  }

  // 只有在鼠标按下且有选中对象时才开始拖动
  // 注意：这里不需要检查鼠标是否移动，因为mousemove事件本身就表示鼠标在移动
  if (mouseDown && !drag.mode && selected) {
    if (selected?.type === 'furniture') {
      const furniture = state.furnitures.find(f => f.id === selected.id);
      if (furniture) {
        drag.mode = 'move';
        drag.id = furniture.id;
        drag.kind = 'furniture';
        drag.dx = rx - furniture.x;
        drag.dy = ry - furniture.y;
      }
    } else if (selected?.type === 'room') {
      const room = state.rooms.find(r => r.id === selected.id);
      if (room) {
        const edge = roomEdgeHit(room, point.x, point.y);
        drag.mode = edge ? 'resize' : 'move';
        drag.id = room.id;
        drag.kind = 'room';
        drag.edge = edge;
        drag.dx = rx - room.x;
        drag.dy = ry - room.y;
      }
    } else if (selected?.type === 'opening') {
      const opening = state.openings.find(o => o.id === selected.id);
      if (opening) {
        drag.mode = 'move';
        drag.id = opening.id;
        drag.kind = 'opening';
      }
    }
  }

  if (!drag.mode) return;

  if (drag.kind === 'canvas') {
    planPanX = drag.startPanX + (point.x - drag.startX);
    planPanY = drag.startPanY + (point.y - drag.startY);
    clampPlanPan();
    render2D();
    return;
  }

  if (drag.kind === 'room') {
    const room = state.rooms.find(r => r.id === drag.id);
    if (!room) return;
    if (drag.mode === 'move') {
      room.x = +(rx - drag.dx).toFixed(1);
      room.y = +(ry - drag.dy).toFixed(1);
    } else if (drag.edge === 'right') {
      room.width = Math.max(1.6, +(rx - room.x).toFixed(1));
    } else if (drag.edge === 'bottom') {
      room.depth = Math.max(1.6, +(ry - room.y).toFixed(1));
    } else if (drag.edge === 'left') {
      const oldRight = room.x + room.width;
      room.x = +rx.toFixed(1);
      room.width = Math.max(1.6, +(oldRight - room.x).toFixed(1));
    } else if (drag.edge === 'top') {
      const oldBottom = room.y + room.depth;
      room.y = +ry.toFixed(1);
      room.depth = Math.max(1.6, +(oldBottom - room.y).toFixed(1));
    }
    render2D();
    render3D();
    return;
  }

  if (drag.kind === 'furniture') {
    const item = state.furnitures.find(f => f.id === drag.id);
    if (!item) return;
    if (isWallFurniture(item)) {
      const room = hitRoom(point.x, point.y) || state.rooms.find(r => r.id === item.room_id);
      if (room) {
        const wallHit = nearestWallFromPoint(room, rx, ry);
        const safeMountHeight = clampMountHeight(room, item.mount_height || 1.5, 1.5);
        const p = wallPlacementToWorld(room, wallHit.wall, wallHit.offset, safeMountHeight);
        item.room_id = room.id;
        item.wall = wallHit.wall;
        item.wall_offset = +wallHit.offset.toFixed(2);
        item.x = +p.x.toFixed(2);
        item.y = +p.y.toFixed(2);
        item.rotation = p.rotation;
        item.mount_height = +safeMountHeight.toFixed(2);
      }
    } else {
      item.x = +(rx - drag.dx).toFixed(1);
      item.y = +(ry - drag.dy).toFixed(1);
      applyFurnitureLocalPlacement(item);
    }
    syncUI();
    render2D();
    render3D();
    return;
  }

  if (drag.kind === 'opening') {
    const opening = state.openings.find(o => o.id === drag.id);
    const room = opening && state.rooms.find(r => r.id === opening.room_id);
    if (!opening || !room) return;
    if (opening.wall === 'top' || opening.wall === 'bottom') {
      opening.offset = Math.max(0, Math.min(+(rx - room.x - opening.width / 2).toFixed(1), room.width - opening.width));
    } else {
      opening.offset = Math.max(0, Math.min(+(ry - room.y - opening.width / 2).toFixed(1), room.depth - opening.width));
    }
    render2D();
    render3D();
  }
});

window.addEventListener('mouseup', async () => {
  // 重置鼠标按下状态
  mouseDown = false;
  
  // 如果没有拖动，直接返回
  if (!drag.mode) return;
  
  // 保存当前拖动的对象信息
  const dragId = drag.id;
  const dragKind = drag.kind;
  const room = drag.kind === 'room' ? state.rooms.find(r => r.id === drag.id) : null;
  const item = drag.kind === 'furniture' ? state.furnitures.find(f => f.id === drag.id) : null;
  const op = drag.kind === 'opening' ? state.openings.find(o => o.id === drag.id) : null;

  // 立即重置drag状态，避免鼠标移动时继续拖动
  drag.mode = null;
  drag.id = null;
  drag.kind = null;
  drag.edge = null;
  previewState.snapLines = [];
  previewState.collision = false;

  // 如果是平移画布，直接返回
  if (dragKind === 'canvas') {
    return;
  }

  // 执行异步保存操作
  if (dragKind === 'room' && room) {
    await request(`/api/room/${dragId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        x: room.x, y: room.y, width: room.width, depth: room.depth, height: Number(room.height || 3),
        name: room.name, wall_color: room.wall_color,
      })
    });
  } else if (dragKind === 'furniture' && item) {
    applyFurnitureLocalPlacement(item);
    await request(`/api/furniture/${dragId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        label: item.label, x: item.x, y: item.y, width: item.width, depth: item.depth,
        rotation: item.rotation, room_id: item.room_id, color: item.color, material: item.material, type: item.type,
        placement: item.placement || 'floor', wall: item.wall, wall_offset: item.wall_offset, mount_height: item.mount_height,
      })
    });
  } else if (dragKind === 'opening' && op) {
    await request(`/api/opening/${dragId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: op.name, type: op.type, room_id: op.room_id, wall: op.wall, offset: op.offset, width: op.width,
      })
    });
  }

  render2D();
  render3D();
});

el.planCanvas.addEventListener('dblclick', async evt => {
  if (pendingPlacementType) return;
  const point = canvasPoint(evt);
  const room = hitRoom(point.x, point.y);
  if (!room) return;
  // 双击房间不再自动添加沙发
  // 可以在这里添加其他双击房间的逻辑
});

el.planCanvas.addEventListener('mouseleave', () => {
  if (drag.kind === 'canvas') {
    drag.mode = null;
    drag.id = null;
    drag.kind = null;
    drag.edge = null;
  }

  if (!pendingPlacementType) return;
  previewState.hoverPlacement = null;
  previewState.snapLines = [];
  previewState.collision = false;
  render2D();
});

el.planCanvas.addEventListener('wheel', evt => {
  evt.preventDefault();
  const delta = evt.deltaY > 0 ? 0.9 : 1.1;
  planZoom = clamp(+(planZoom * delta).toFixed(3), 0.45, 3.6);
  clampPlanPan();
  render2D();
}, { passive: false });

async function applyRoomForm(isNew = false) {
  const body = JSON.stringify({
    name: el.roomNameInput.value.trim() || '客厅',
    x: parseFloat(el.roomXInput.value || 0),
    y: parseFloat(el.roomYInput.value || 0),
    width: parseFloat(el.roomWidthInput.value || 3),
    depth: parseFloat(el.roomDepthInput.value || 3),
    height: clamp(parseFloat(el.roomHeightInput?.value || 3), 2.2, 6),
    wall_color: el.roomColorInput.value,
  });
  const roomId = selectedRoom()?.id || state.rooms[0]?.id;
  const data = await request(isNew ? '/api/room' : `/api/room/${roomId}`, { method: isNew ? 'POST' : 'PATCH', body });
  if (data.room) selected = { type: 'room', id: data.room.id };
}

async function applyOpeningForm(isNew = false) {
  const openingName = el.openingNameInput.value.trim();
  const inferredType = openingName.includes('窗')
    ? 'window'
    : openingName.includes('门')
      ? 'door'
      : (selectedOpening()?.type || 'door');

  const body = JSON.stringify({
    name: openingName || '',
    type: inferredType,
    room_id: selectedOpening()?.room_id || selectedRoom()?.id || state.rooms[0]?.id,
    wall: el.openingWallSelect.value,
    offset: parseFloat(el.openingOffsetInput.value || 0),
    width: parseFloat(el.openingWidthInput.value || 0.9),
  });

  const id = selectedOpening()?.id;
  const data = await request(
    isNew ? '/api/opening' : `/api/opening/${id}`,
    { method: isNew ? 'POST' : 'PATCH', body }
  );

  if (data.opening) {
    selected = { type: 'opening', id: data.opening.id };
  }

  syncUI();
  render2D();
  render3D();
}


async function addFurnitureFromForm() {
  const roomId = selectedRoom()?.id || state.rooms[0]?.id;
  const type = preferredFurnitureType || 'loungeSofa';
  const data = await request('/api/furniture', {
    method: 'POST',
    body: JSON.stringify({
      type,
      room_id: roomId,
      x: parseFloat(el.furnitureXInput.value || 0),
      y: parseFloat(el.furnitureYInput.value || 0),
      width: parseFloat(el.furnitureWidthInput.value || 1),
      depth: parseFloat(el.furnitureDepthInput.value || 1),
      rotation: parseFloat(el.furnitureRotationInput.value || 0),
      color: el.furnitureColorInput.value,
      material: el.furnitureMaterialInput.value,
      label: el.furnitureLabelInput.value.trim() || undefined,
    })
  });
  if (data.item) {
    preferredFurnitureType = data.item.type || type;
    selected = { type: 'furniture', id: data.item.id };
  }
}

async function applyFurnitureForm() {
  const item = selectedFurniture();
  if (!item) return;
  await request(`/api/furniture/${item.id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      label: el.furnitureLabelInput.value.trim() || item.label,
      // type: el.furnitureTypeSelect.value || item.type,
      // room_id: el.furnitureRoomSelect.value || item.room_id,
      color: el.furnitureColorInput.value,
      material: el.furnitureMaterialInput.value,
      width: parseFloat(el.furnitureWidthInput.value || 1),
      depth: parseFloat(el.furnitureDepthInput.value || 1),
      x: parseFloat(el.furnitureXInput.value || 0),
      y: parseFloat(el.furnitureYInput.value || 0),
      rotation: parseFloat(el.furnitureRotationInput.value || 0),
      placement: item.placement || 'floor',
      wall: item.wall,
      wall_offset: item.wall_offset,
      mount_height: item.mount_height,
    })
  });
}

async function deleteSelectedObject() {
  if (!selected) return;

  if (selected?.type === 'room') {
    const room = selectedRoom();
    if (!room) return;
    await request(`/api/room/${room.id}`, { method: 'DELETE' });
    selected = { type: 'room', id: state.rooms[0]?.id || null };
    return;
  }

  if (selected?.type === 'opening') {
    const opening = selectedOpening();
    if (!opening) return;
    await request(`/api/opening/${opening.id}`, { method: 'DELETE' });
    selected = { type: 'room', id: state.rooms[0]?.id || null };
    return;
  }

  if (selected?.type === 'furniture') {
    const item = selectedFurniture();
    if (!item) return;
    await request(`/api/furniture/${item.id}`, { method: 'DELETE' });
    selected = { type: 'room', id: item.room_id || state.rooms[0]?.id || null };
  }
}

function initSpeechRecognition() {
  if (!el.voiceCommandBtn) return;
  if (!SpeechRecognitionAPI) {
    el.voiceCommandBtn.disabled = true;
    el.voiceCommandBtn.textContent = '语音不可用';
    setMessage('当前浏览器不支持语音识别，请使用 Chrome ', 'info');
    return;
  }

  el.voiceCommandBtn.textContent = `语音输入${VOICE_MODEL_LABEL}`;

  speechRecognition = new SpeechRecognitionAPI();
  speechRecognition.lang = 'zh-CN';
  speechRecognition.continuous = false;
  speechRecognition.interimResults = true;
  speechRecognition.maxAlternatives = 1;

  speechRecognition.onstart = () => {
    isVoiceRecording = true;
    speechFinalText = '';
    if (voiceAutoRunTimer) {
      clearTimeout(voiceAutoRunTimer);
      voiceAutoRunTimer = null;
    }
    el.voiceCommandBtn.textContent = '⏹ 结束录音';
    el.voiceCommandBtn.classList.add('recording');
    setMessage('正在录音，请说出你的装修指令 ', 'info');
  };

  speechRecognition.onresult = event => {
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) speechFinalText += text;
      else interimText += text;
    }
    el.commandInput.value = `${speechFinalText}${interimText}`.trim();
  };

  speechRecognition.onerror = () => {
    isVoiceRecording = false;
    el.voiceCommandBtn.textContent = `语音输入${VOICE_MODEL_LABEL}`;
    el.voiceCommandBtn.classList.remove('recording');
    setMessage('语音识别失败，请重试 ', 'error');
  };

  speechRecognition.onend = () => {
    isVoiceRecording = false;
    el.voiceCommandBtn.textContent = `语音输入${VOICE_MODEL_LABEL}`;    
    el.voiceCommandBtn.classList.remove('recording');
    const text = el.commandInput.value.trim();
    if (!text) {
      setMessage('未识别到语音内容 ', 'info');
      return;
    }
    setMessage(`语音识别完成，${VOICE_MODEL_LABEL} 指令将在 3 秒后执行...`, 'info');
    
    // 获取执行按钮
    const execBtn = document.getElementById('runCommandBtn');
    let countdown = 3;
    
    if (execBtn) {
      execBtn.textContent = `执行指令 (${countdown}s)`;
    }
    
    // 更新倒计时显示
    const countdownInterval = setInterval(() => {
      countdown--;
      if (countdown > 0) {
        if (execBtn) {
          execBtn.textContent = `执行指令 (${countdown}s)`;
        }
      } else {
        clearInterval(countdownInterval);
      }
    }, 1000);
    
    // 3秒后自动执行指令
    voiceAutoRunTimer = setTimeout(() => {
      if (execBtn) {
        execBtn.textContent = '执行指令';
      }
      runVoiceCommand(text);
    }, 3000);
  };
}

function toggleVoiceInput() {
  if (!speechRecognition) {
    setMessage('当前浏览器不支持语音识别，请使用 Chrome ', 'info');
    return;
  }
  if (isVoiceRecording) {
    speechRecognition.stop();
    return;
  }
  try {
    speechRecognition.start();
  } catch {
    setMessage('语音识别启动失败，请稍后重试 ', 'error');
  }
}

// 启动语音录制
function startVoiceRecording() {
  toggleVoiceInput();
}

async function runVoiceCommand(transcript = '') {
  const voiceText = String(transcript || el.commandInput.value || '').trim();
  if (!voiceText) {
    setMessage('没有可发送的语音内容 ', 'info');
    return;
  }

  setMessage(`正在调用 ${VOICE_MODEL_LABEL} 解析语音指令...`, 'info');
  const data = await request('/api/voice-command', {
    method: 'POST',
    body: JSON.stringify({ transcript: voiceText }),
  });

  if (data?.llm_command) {
    el.commandInput.value = data.llm_command;
  } else {
    el.commandInput.value = voiceText;
  }
}

async function runCommand() {
  const command = el.commandInput.value.trim();
  if (!command) {
    setMessage('请输入指令 ', 'info');
    return;
  }
  await request('/api/command', { method: 'POST', body: JSON.stringify({ command }) });
}


function afterStateUpdated() {
}

function bindEvents() {

  el.toggleRoomPanelBtn.onclick = () => toggleSidePanel('room');
  el.toggleOpeningPanelBtn.onclick = () => toggleSidePanel('opening');
  el.toggleFurniturePanelBtn.onclick = () => toggleSidePanel('furniture');
  el.toggleFurnitureEditorPanelBtn.onclick = () => toggleSidePanel('furnitureEditor');

  document.getElementById('runCommandBtn').onclick = runCommand;
  el.undoBtn.onclick = async () => request('/api/undo', { method: 'POST' });
  if (el.voiceCommandBtn) el.voiceCommandBtn.onclick = toggleVoiceInput;
  if (el.gestureToggleBtn) el.gestureToggleBtn.onclick = toggleGestureRecognition;
  if (el.showCommandPanelBtn) el.showCommandPanelBtn.onclick = () => showTopPanel('command');
  if (el.showAIFloorplanPanelBtn) el.showAIFloorplanPanelBtn.onclick = () => showTopPanel('ai');
  if (el.firstPersonBtn) el.firstPersonBtn.onclick = enterFirstPersonMode;
  if (el.editModeBtn) el.editModeBtn.onclick = exitFirstPersonMode;
  
  // 当用户点击输入框时，中断自动执行倒计时
  el.commandInput.onclick = () => {
    if (voiceAutoRunTimer) {
      clearTimeout(voiceAutoRunTimer);
      voiceAutoRunTimer = null;
      const execBtn = document.getElementById('runCommandBtn');
      if (execBtn) {
        execBtn.textContent = '执行指令';
      }
      setMessage('自动执行已取消，点击「执行指令」按钮手动执行 ', 'info');
    }
  };

  el.addRoomBtn.onclick = () => applyRoomForm(true);
  el.applyRoomBtn.onclick = () => applyRoomForm(false);
  el.deleteRoomBtn.onclick = deleteSelectedObject;

  el.addOpeningBtn.onclick = () => applyOpeningForm(true);
  el.applyOpeningBtn.onclick = () => applyOpeningForm(false);
  el.deleteOpeningBtn.onclick = deleteSelectedObject;

  el.addFurnitureBtn.onclick = addFurnitureFromForm;
  el.applyFurnitureBtn.onclick = applyFurnitureForm;
  el.deleteFurnitureBtn.onclick = deleteSelectedObject;

  el.furnitureSearchInput.addEventListener('input', event => {
    librarySearch = event.target.value || '';
    renderFurnitureLibrary();
  });

  el.commandInput.addEventListener('keydown', evt => {
    if ((evt.ctrlKey || evt.metaKey) && evt.key === 'Enter') runCommand();
  });

  window.addEventListener('keydown', event => {
    if (!isFirstPersonMode) return;
    if (['KeyW', 'ArrowUp'].includes(event.code)) firstPersonKeys.forward = true;
    if (['KeyS', 'ArrowDown'].includes(event.code)) firstPersonKeys.backward = true;
    if (['KeyA', 'ArrowLeft'].includes(event.code)) firstPersonKeys.left = true;
    if (['KeyD', 'ArrowRight'].includes(event.code)) firstPersonKeys.right = true;
  });

  window.addEventListener('keyup', event => {
    if (['KeyW', 'ArrowUp'].includes(event.code)) firstPersonKeys.forward = false;
    if (['KeyS', 'ArrowDown'].includes(event.code)) firstPersonKeys.backward = false;
    if (['KeyA', 'ArrowLeft'].includes(event.code)) firstPersonKeys.left = false;
    if (['KeyD', 'ArrowRight'].includes(event.code)) firstPersonKeys.right = false;
  });

  window.addEventListener('resize', () => {
    resizeCanvas();
    render2D();
    resize3DRenderer();
    render3D();
  });
}

function updateGestureUi(active, statusText, actionText = null) {
  if (el.gestureStatusText) {
    el.gestureStatusText.textContent = statusText;
    el.gestureStatusText.classList.toggle('active', !!active);
  }
  if (el.gestureToggleBtn) el.gestureToggleBtn.textContent = active ? '关闭手势识别' : '开启手势识别';
  if (actionText !== null && el.gestureActionText) el.gestureActionText.textContent = actionText;
  if (actionText !== null) gestureState.lastActionText = actionText;
}

function gestureDistance(a, b) {
  return Math.hypot((a.x || 0) - (b.x || 0), (a.y || 0) - (b.y || 0));
}

function gestureClientPoint(landmark) {
  return {
    x: (1 - landmark.x) * window.innerWidth,
    y: landmark.y * window.innerHeight,
  };
}

function getScreenElementAtLandmark(landmark) {
  const pt = gestureClientPoint(landmark);
  return document.elementFromPoint(pt.x, pt.y);
}

function handPinchStrength(hand) {
  return gestureDistance(hand[4], hand[8]);
}

function handIsPinching(hand) {
  return handPinchStrength(hand) < 0.05;
}

function handIndexMiddleSpread(hand) {
  return gestureDistance(hand[8], hand[12]);
}

function fingerExtended(hand, tipIndex, pipIndex) {
  return hand[tipIndex].y < hand[pipIndex].y;
}

function handIsPointing(hand) {
  const indexUp = fingerExtended(hand, 8, 6);
  const middleDown = hand[12].y > hand[10].y;
  const ringDown = hand[16].y > hand[14].y;
  const pinkyDown = hand[20].y > hand[18].y;
  return indexUp && middleDown && ringDown && pinkyDown;
}

function handIsOk(hand) {
  const thumbIndexClose = gestureDistance(hand[4], hand[8]) < 0.05;
  const middleUp = fingerExtended(hand, 12, 10);
  const ringUp = fingerExtended(hand, 16, 14);
  const pinkyUp = fingerExtended(hand, 20, 18);
  return thumbIndexClose && middleUp && ringUp && pinkyUp;
}

// 检测拇指向下手势
function isThumbDownGesture(hand) {
  // 检测拇指是否向下（在MediaPipe中，y轴从上到下，所以向下时y值更大）
  // 要求拇指指尖明显低于拇指第一个关节
  const thumbDown = hand[4].y > hand[3].y + 0.05;
  
  // 检测其他手指是否弯曲（要求所有手指都弯曲）
  const indexFingerBent = hand[8].y > hand[6].y + 0.03;
  const middleFingerBent = hand[12].y > hand[10].y + 0.03;
  const ringFingerBent = hand[16].y > hand[14].y + 0.03;
  const pinkyBent = hand[20].y > hand[18].y + 0.03;
  
  // 要求所有其他手指都弯曲
  return thumbDown && indexFingerBent && middleFingerBent && ringFingerBent && pinkyBent;
}

// 检测正赞手势（拇指向上，其他手指弯曲）
function isThumbUpGesture(hand) {
  // 检测拇指是否向上（在MediaPipe中，y轴从上到下，所以向上时y值更小）
  // 增加阈值，要求拇指更明显地向上，避免误识别
  const thumbUp = hand[4].y < hand[3].y - 0.08;
  
  // 检测其他手指是否弯曲
  const indexFingerBent = hand[8].y > hand[6].y;
  const middleFingerBent = hand[12].y > hand[10].y;
  const ringFingerBent = hand[16].y > hand[14].y;
  const pinkyBent = hand[20].y > hand[18].y;
  
  // 要求拇指向上，其他手指弯曲
  return thumbUp && indexFingerBent && middleFingerBent && ringFingerBent && pinkyBent;
}

// 检测1手势（伸出食指，其他手指弯曲）
function isOneGesture(hand) {
  // 检测食指是否伸直
  const indexFingerExtended = hand[8].y < hand[6].y;
  
  // 检测其他手指是否弯曲
  const thumbBent = hand[4].y > hand[3].y;
  const middleFingerBent = hand[12].y > hand[10].y;
  const ringFingerBent = hand[16].y > hand[14].y;
  const pinkyBent = hand[20].y > hand[18].y;
  
  // 要求食指伸直，其他手指弯曲
  return indexFingerExtended && thumbBent && middleFingerBent && ringFingerBent && pinkyBent;
}

// 检测三指手势（伸出食指、中指、无名指）
function isThreeFingerGesture(hand) {
  // 检测拇指和小指是否弯曲（更宽松的检测）
  const thumbBent = hand[4].y > hand[3].y;
  const pinkyBent = hand[20].y > hand[19].y;
  
  // 检测食指、中指、无名指是否伸直（更宽松的检测）
  const indexFingerExtended = hand[8].y < hand[6].y;
  const middleFingerExtended = hand[12].y < hand[10].y;
  const ringFingerExtended = hand[16].y < hand[14].y;
  
  // 要求拇指和小指弯曲，食指、中指、无名指伸直
  return thumbBent && pinkyBent && indexFingerExtended && middleFingerExtended && ringFingerExtended;
}

// 处理三指手势（撤销操作）
async function gestureHandleThreeFingerUndo(hand) {
  // 检测是否为三指手势
  if (!isThreeFingerGesture(hand)) {
    // 如果不是撤销手势，清除倒计时
    if (gestureState.undoCountdownTimer) {
      clearInterval(gestureState.undoCountdownTimer);
      gestureState.undoCountdownTimer = null;
      gestureState.undoCountdown = 0;
      setGestureAction('等待手势操作');
    }
    return false;
  }

  // 检查是否已经在倒计时中
  if (gestureState.undoCountdownTimer) {
    return true;
  }

  // 开始3秒倒计时
  const countdownSeconds = 3;
  gestureState.undoCountdown = countdownSeconds;
  
  // 显示倒计时信息
  setGestureAction(`🤞 手势：撤销操作将在 ${gestureState.undoCountdown} 秒后执行`);
  
  // 创建倒计时定时器
  gestureState.undoCountdownTimer = setInterval(async () => {
    gestureState.undoCountdown--;
    
    if (gestureState.undoCountdown > 0) {
      // 更新倒计时信息
      setGestureAction(`🤞 手势：撤销操作将在 ${gestureState.undoCountdown} 秒后执行`);
    } else {
      // 倒计时结束，执行撤销操作
      clearInterval(gestureState.undoCountdownTimer);
      gestureState.undoCountdownTimer = null;
      
      // 执行撤销操作
      const response = await fetch('/api/undo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const result = await response.json();
      if (result.ok) {
        setGestureAction('🤞 手势：已撤销上一步操作');
        setMessage('已撤销上一步操作 ', 'success');
        // 重新加载状态
        await loadState();
        syncUI();
        render2D();
        render3D();
        gestureState.lastUndoAt = performance.now();
      } else {
        setGestureAction('🤞 手势：没有可撤销的操作');
        setMessage('没有可撤销的操作 ', 'info');
      }
    }
  }, 1000);

  return true;
}

// 处理正赞手势（语音输入触发）
async function gestureHandleThumbUp(hand) {
  // 检测是否为正赞手势
  if (!isThumbUpGesture(hand)) {
    // 如果不是正赞手势，清除倒计时
    if (gestureState.thumbUpCountdownTimer) {
      clearInterval(gestureState.thumbUpCountdownTimer);
      gestureState.thumbUpCountdownTimer = null;
      gestureState.thumbUpCountdown = 0;
      setGestureAction('等待手势操作');
      // 恢复语音输入按钮状态
      const voiceBtn = document.getElementById('voice-input-btn');
      if (voiceBtn) {
        voiceBtn.textContent = '语音输入';  
      }
    }
    return false;
  }

  // 检查是否已经在倒计时中
  if (gestureState.thumbUpCountdownTimer) {
    return true;
  }

  // 开始2秒倒计时
  const countdownSeconds = 2;
  gestureState.thumbUpCountdown = countdownSeconds;
  
  // 显示倒计时信息
  setGestureAction(`👍 手势：语音输入将在 ${gestureState.thumbUpCountdown} 秒后触发`);
  
  // 更新语音输入按钮状态
  const voiceBtn = document.getElementById('voice-input-btn');
  if (voiceBtn) {
    voiceBtn.textContent = `准备中... ${gestureState.thumbUpCountdown}s`;
  }
  
  // 创建倒计时定时器
  gestureState.thumbUpCountdownTimer = setInterval(() => {
    gestureState.thumbUpCountdown--;
    
    if (gestureState.thumbUpCountdown > 0) {
      // 更新倒计时信息
      setGestureAction(`👍 手势：语音输入将在 ${gestureState.thumbUpCountdown} 秒后触发`);
      // 更新语音输入按钮状态
      if (voiceBtn) {
        voiceBtn.textContent = `准备中... ${gestureState.thumbUpCountdown}s`;
      }
    } else {
      // 倒计时结束，触发语音输入
      clearInterval(gestureState.thumbUpCountdownTimer);
      gestureState.thumbUpCountdownTimer = null;
      
      // 触发语音输入
      startVoiceRecording();
      setGestureAction('👍 手势：已触发语音输入');
      gestureState.lastThumbUpAt = performance.now();
    }
  }, 1000);

  return true;
}

// 用于存储上一帧的指尖位置
let lastIndexTipX = null;
let lastIndexTipY = null;

// 处理1手势（食指伸直，其他手指弯曲）
async function gestureHandleOneGesture(hand) {
  // 检测是否为1手势
  if (!isOneGesture(hand)) {
    // 重置指尖位置，避免下次手势时光标跳动
    lastIndexTipX = null;
    lastIndexTipY = null;
    return false;
  }

  // 显示1手势信息
  setGestureAction('☝️ 1手势：已识别');
  
  // 确保光标可见
  gestureState.cursorVisible = true;
  
  // 获取食指指尖坐标
  const indexTip = hand[8];
  
  // 将指尖坐标转换为蓝图坐标
  const v = getViewport();
  
  // 初始化光标位置（如果是第一次）
  if (gestureState.cursorX === 0 && gestureState.cursorY === 0) {
    gestureState.cursorX = v.cw / 2;
    gestureState.cursorY = v.ch / 2;
  }
  
  // 计算光标位置（基于相对位移）
  if (lastIndexTipX !== null && lastIndexTipY !== null) {
    // 计算指尖移动的距离
    const deltaX = (1 - indexTip.x) - (1 - lastIndexTipX);
    const deltaY = indexTip.y - lastIndexTipY;
    
    // 根据移动距离计算光标移动的距离（可以调整系数来控制灵敏度）
    const cursorDeltaX = deltaX * v.cw * 2;
    const cursorDeltaY = deltaY * v.ch * 2;
    
    // 更新光标位置
    gestureState.cursorX = Math.max(0, Math.min(v.cw, gestureState.cursorX + cursorDeltaX));
    gestureState.cursorY = Math.max(0, Math.min(v.ch, gestureState.cursorY + cursorDeltaY));
  } else {
    // 第一次检测到1手势，初始化指尖位置
    lastIndexTipX = indexTip.x;
    lastIndexTipY = indexTip.y;
  }
  
  // 保存当前指尖位置
  lastIndexTipX = indexTip.x;
  lastIndexTipY = indexTip.y;
  
  // 检测光标是否在家具或房间上
  const furniture = hitFurniture(gestureState.cursorX, gestureState.cursorY);
  const room = hitRoom(gestureState.cursorX, gestureState.cursorY);
  
  // 优先选中家具，然后是房间
  if (furniture) {
    // 只有当选中的对象不同时才更新
    if (selected?.type !== 'furniture' || selected?.id !== furniture.id) {
      selected = { type: 'furniture', id: furniture.id };
      render2D();
      render3D();
    }
  } else if (room) {
    // 只有当选中的对象不同时才更新
    if (selected?.type !== 'room' || selected?.id !== room.id) {
      selected = { type: 'room', id: room.id };
      render2D();
      render3D();
    }
  }
  // 如果光标在空白位置，不取消选中
  
  // 重新渲染2D视图
  render2D();
  
  // 绘制食指指尖圈
  if (gestureState.overlayCtx) {
    const canvas = el.gestureOverlay;
    const ctx2 = gestureState.overlayCtx;
    
    const x = indexTip.x * canvas.width;
    const y = indexTip.y * canvas.height;
    
    // 绘制圈
    ctx2.beginPath();
    ctx2.arc(x, y, 15, 0, 2 * Math.PI);
    ctx2.strokeStyle = '#ff0000';
    ctx2.lineWidth = 3;
    ctx2.stroke();
    
    // 填充
    ctx2.fillStyle = 'rgba(255, 0, 0, 0.2)';
    ctx2.fill();
  }
  
  return true;
}





function setGestureAction(text) {
  updateGestureUi(true, '识别中', text);
}







async function gestureDeleteSelectedObject() {
  if (!selected || !selected.type || !selected.id) return false;

  const deletedType = selected.type;
  const deletedId = selected.id;

  if (deletedType === 'room' && !state?.rooms?.some(r => r.id === deletedId)) return false;
  if (deletedType === 'opening' && !state?.openings?.some(o => o.id === deletedId)) return false;
  if (deletedType === 'furniture' && !state?.furnitures?.some(f => f.id === deletedId)) return false;

  await deleteSelectedObject();

  if (deletedType === 'room') {
    setMessage('手势删除：已删除房间', 'success');
    setGestureAction('👎 手势：删除房间');
  } else if (deletedType === 'opening') {
    setMessage('手势删除：已删除门窗', 'success');
    setGestureAction('👎 手势：删除门窗');
  } else if (deletedType === 'furniture') {
    setMessage('手势删除：已删除家具', 'success');
    setGestureAction('👎 手势：删除家具');
  }

  return true;
}

async function gestureHandleVDelete(hand) {
  // 检测是否为拇指向下手势
  if (!isThumbDownGesture(hand)) {
    // 如果不是删除手势，清除倒计时
    if (gestureState.deleteCountdownTimer) {
      clearInterval(gestureState.deleteCountdownTimer);
      gestureState.deleteCountdownTimer = null;
      gestureState.deleteCountdown = 0;
      setGestureAction('等待手势操作');
    }
    return false;
  }

  // 检查是否已经在倒计时中
  if (gestureState.deleteCountdownTimer) {
    return true;
  }

  // 开始3秒倒计时
  const countdownSeconds = 3;
  gestureState.deleteCountdown = countdownSeconds;
  
  // 显示倒计时信息
  setGestureAction(`👎 手势：删除操作将在 ${gestureState.deleteCountdown} 秒后执行`);
  
  // 创建倒计时定时器
  gestureState.deleteCountdownTimer = setInterval(async () => {
    gestureState.deleteCountdown--;
    
    if (gestureState.deleteCountdown > 0) {
      // 更新倒计时信息
      setGestureAction(`👎 手势：删除操作将在 ${gestureState.deleteCountdown} 秒后执行`);
    } else {
      // 倒计时结束，执行删除操作
      clearInterval(gestureState.deleteCountdownTimer);
      gestureState.deleteCountdownTimer = null;
      
      const deleted = await gestureDeleteSelectedObject();
      if (deleted) {
        gestureState.lastDeleteAt = performance.now();
      } else {
        setGestureAction('👎 手势：没有选中对象可删除');
      }
    }
  }, 1000);

  return true;
}

function gestureResizeFurnitureWithTwoHands(hands) {
  const item = selectedFurniture();
  if (!item) {
    gestureState.lastZoomDistance = null;
    return false;
  }

  if (hands.length < 2) {
    gestureState.lastZoomDistance = null;
    return false;
  }

  const a = hands[0][0];
  const b = hands[1][0];
  const dist = gestureDistance(a, b);

  if (gestureState.lastZoomDistance !== null) {
    const ratio = dist / gestureState.lastZoomDistance;

    if (Math.abs(ratio - 1) > 0.03) {
      const scale = clamp(ratio, 0.92, 1.08);

      item.width = +clamp(item.width * scale, 0.3, 4.5).toFixed(2);
      item.depth = +clamp(item.depth * scale, 0.3, 4.5).toFixed(2);

      applyFurnitureLocalPlacement(item);
      syncUI();
      updateFurnitureEditorInputs(item);
      render2D();
      render3D();

      setGestureAction(scale > 1 ? '双手拉开：正在放大家具' : '双手靠近：正在缩小家具');
    }
  }

  gestureState.lastZoomDistance = dist;
  return true;
}

function gestureThreeGroundPointFromClient(clientX, clientY) {
  if (!renderer || !camera || !raycaster) return null;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hitPoint = new THREE.Vector3();
  if (!raycaster.ray.intersectPlane(plane, hitPoint)) return null;
  return hitPoint;
}

function updateFurnitureEditorInputs(item) {
  if (!item) return;
  if (el.furnitureWidthInput) el.furnitureWidthInput.value = Number(item.width).toFixed(2);
  if (el.furnitureDepthInput) el.furnitureDepthInput.value = Number(item.depth).toFixed(2);
  if (el.furnitureXInput) el.furnitureXInput.value = Number(item.x).toFixed(2);
  if (el.furnitureYInput) el.furnitureYInput.value = Number(item.y).toFixed(2);
}

function gestureMoveSelectedFurniture(hand) {
  const item = selectedFurniture();
  if (!item) return false;
  const pt = gestureClientPoint(hand[8]);
  const overPlan = el.planCanvas?.getBoundingClientRect();
  const overThree = el.threeContainer?.getBoundingClientRect();
  let moved = false;
  if (overPlan && pt.x >= overPlan.left && pt.x <= overPlan.right && pt.y >= overPlan.top && pt.y <= overPlan.bottom) {
    const viewport = getViewport();
    item.x = +fromCanvasX(pt.x - overPlan.left, viewport).toFixed(1);
    item.y = +fromCanvasY(pt.y - overPlan.top, viewport).toFixed(1);
    moved = true;
  } else if (overThree && pt.x >= overThree.left && pt.x <= overThree.right && pt.y >= overThree.top && pt.y <= overThree.bottom) {
    const hit = gestureThreeGroundPointFromClient(pt.x, pt.y);
    if (hit) {
      item.x = +hit.x.toFixed(1);
      item.y = +hit.z.toFixed(1);
      moved = true;
    }
  }
  if (moved) {
    applyFurnitureLocalPlacement(item);
    syncUI();
    updateFurnitureEditorInputs(item);
    render2D();
    render3D();
  }
  return moved;
}



async function gestureCommitFurniture() {
  const item = selectedFurniture();
  if (!item) return;
  await request(`/api/furniture/${item.id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      label: item.label,
      x: item.x,
      y: item.y,
      width: item.width,
      depth: item.depth,
      rotation: item.rotation,
      room_id: item.room_id,
      color: item.color,
      material: item.material,
      type: item.type,
    })
  });
}

async function gestureHandleGrab(hand) {
  const pinching = handIsPinching(hand);

  if (pinching && !gestureState.lastPinch) {
    const item = selectedFurniture();
    if (item) {
      gestureState.pinchDragging = true;
      gestureState.dragFurnitureId = item.id;
      gestureState.openPalmActive = false;
      gestureState.openPalmLastCenterY = null;
      setGestureAction(`捏合开始：抓取 ${item.label}`);
    } else if (pendingPlacementType) {
      const type = pendingPlacementType;
      const meta = getFurnitureMeta(type);
      const pt = gestureClientPoint(hand[8]);
      const planRect = el.planCanvas?.getBoundingClientRect();
      const threeRect = el.threeContainer?.getBoundingClientRect();
      let room = null;
      let x = 0;
      let y = 0;
      if (planRect && pt.x >= planRect.left && pt.x <= planRect.right && pt.y >= planRect.top && pt.y <= planRect.bottom) {
        const viewport = getViewport();
        x = fromCanvasX(pt.x - planRect.left, viewport);
        y = fromCanvasY(pt.y - planRect.top, viewport);
        room = findRoomForFurniturePlacement(x, y, { x, y, width: meta.width, depth: meta.depth, rotation: 0 });
      } else if (threeRect && pt.x >= threeRect.left && pt.x <= threeRect.right && pt.y >= threeRect.top && pt.y <= threeRect.bottom) {
        const hit = gestureThreeGroundPointFromClient(pt.x, pt.y);
        if (hit) {
          x = hit.x;
          y = hit.z;
          room = findRoomForFurniturePlacement(x, y, { x, y, width: meta.width, depth: meta.depth, rotation: 0 });
        }
      }
      if (room) {
        await placePendingFurnitureAt(x, y, room.id);
        gestureState.pinchDragging = true;
        gestureState.dragFurnitureId = selected.id;
        gestureState.openPalmActive = false;
        gestureState.openPalmLastCenterY = null;
        setGestureAction(`捏合开始：已抓取新放置的${meta?.label || '家具'}`);
      }
    }
  }

  if (pinching && gestureState.pinchDragging && selectedFurniture()?.id === gestureState.dragFurnitureId) {
    gestureMoveSelectedFurniture(hand);
    setGestureAction('捏合移动：家具正在跟随移动');
  }

  if (!pinching && gestureState.lastPinch && gestureState.pinchDragging) {
    await gestureCommitFurniture();
    gestureState.pinchDragging = false;
    gestureState.dragFurnitureId = null;
    gestureState.openPalmActive = false;
    gestureState.openPalmLastCenterY = null;
    setGestureAction('松开捏合：家具已放下');
  }

  gestureState.lastPinch = pinching;
  return pinching;
}




async function gestureHandleOk(hands) {
  const okHand = hands.find(hand => handIsOk(hand));
  if (!okHand) return false;
  if (performance.now() - gestureState.lastOkAt < 1200) return true;
  gestureState.lastOkAt = performance.now();
  if (selectedFurniture()) {
    await gestureCommitFurniture();
    setGestureAction('OK 手势：已完成当前家具操作');
    setMessage('手势已完成当前家具操作 ', 'success');
  } else if (pendingPlacementType) {
    pendingPlacementType = null;
    updatePlacementHint();
    renderFurnitureLibrary();
    render2D();
    render3D();
    setGestureAction('OK 手势：已退出待放置状态');
  } else {
    setGestureAction('OK 手势：当前没有可完成的操作');
  }
  return true;
}

function drawGestureOverlay(results) {
  if (!el.gestureOverlay) return;
  const canvas = el.gestureOverlay;
  if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
  }
  if (!gestureState.overlayCtx) gestureState.overlayCtx = canvas.getContext('2d');
  const ctx2 = gestureState.overlayCtx;
  ctx2.clearRect(0, 0, canvas.width, canvas.height);
  if (!results.multiHandLandmarks?.length) return;
  for (const landmarks of results.multiHandLandmarks) {
    if (window.drawConnectors && window.HAND_CONNECTIONS) window.drawConnectors(ctx2, landmarks, window.HAND_CONNECTIONS, { color: '#63a7ff', lineWidth: 3 });
    if (window.drawLandmarks) window.drawLandmarks(ctx2, landmarks, { color: '#ffffff', lineWidth: 1, radius: 3 });
  }
}

async function handleGestureResults(results) {
  drawGestureOverlay(results);
  const hands = results.multiHandLandmarks || [];

  if (!hands.length) {
    gestureState.lastZoomDistance = null;
    gestureState.lastPinch = false;
    gestureState.openPalmActive = false;
    gestureState.openPalmLastCenterY = null;
    if (!gestureState.pinchDragging) updateGestureUi(true, '识别中', '等待识别手势');
    return;
  }

  if (gestureResizeFurnitureWithTwoHands(hands)) return;

  for (const hand of hands) {
    if (await gestureHandleVDelete(hand)) return;
    if (await gestureHandleThreeFingerUndo(hand)) return;
    if (await gestureHandleThumbUp(hand)) return;
    if (await gestureHandleOneGesture(hand)) return;
  }

  if (await gestureHandleOk(hands)) return;

  for (const hand of hands) {
    if (await gestureHandleGrab(hand)) return;
  }



  updateGestureUi(true, '识别中', gestureState.lastActionText || '已检测到手部');
}

async function startGestureRecognition() {
  if (!window.Hands || !el.gestureVideo || !el.gestureOverlay) {
    setMessage('当前页面未成功加载手势识别库 ', 'error');
    return;
  }
  if (gestureState.enabled) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 960, height: 540, facingMode: 'user' }, audio: false });
    gestureState.stream = stream;
    el.gestureVideo.srcObject = stream;
    const hands = new window.Hands({
      locateFile: file => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
    });
    hands.setOptions({
      maxNumHands: 2,
      modelComplexity: 1,
      minDetectionConfidence: 0.65,
      minTrackingConfidence: 0.6,
    });
    hands.onResults(results => {
      handleGestureResults(results);
    });
    gestureState.hands = hands;
    const cameraRunner = new window.Camera(el.gestureVideo, {
      onFrame: async () => {
        if (gestureState.hands) await gestureState.hands.send({ image: el.gestureVideo });
      },
      width: 960,
      height: 540,
    });
    gestureState.camera = cameraRunner;
    await cameraRunner.start();
    gestureState.enabled = true;
    showSidePanel('furniture');
    renderFurnitureLibrary();
    updateGestureUi(true, '识别中', '手势识别已开启');
    setMessage('手势识别已开启，可用双手调家具大小、捏合拖拽、OK 完成操作 ', 'success');
  } catch (error) {
    console.error(error);
    updateGestureUi(false, '开启失败', '无法访问摄像头');
    setMessage('摄像头开启失败，请检查浏览器权限 ', 'error');
  }
}

async function stopGestureRecognition() {
  gestureState.enabled = false;
  gestureState.lastZoomDistance = null;
  gestureState.lastPinch = false;
  gestureState.pinchDragging = false;
  gestureState.dragFurnitureId = null;

  gestureState.openPalmActive = false;
  gestureState.openPalmLastCenterY = null;
  if (gestureState.camera?.stop) gestureState.camera.stop();
  if (gestureState.hands?.close) await gestureState.hands.close();
  gestureState.camera = null;
  gestureState.hands = null;
  if (gestureState.stream) {
    gestureState.stream.getTracks().forEach(track => track.stop());
    gestureState.stream = null;
  }
  if (el.gestureVideo) el.gestureVideo.srcObject = null;
  if (el.gestureOverlay) {
    const ctx2 = el.gestureOverlay.getContext('2d');
    ctx2.clearRect(0, 0, el.gestureOverlay.width, el.gestureOverlay.height);
  }
  updateGestureUi(false, '未开启', '等待手势操作');
  setMessage('手势识别已关闭 ', 'info');
}

async function toggleGestureRecognition() {
  if (gestureState.enabled) {
    await stopGestureRecognition();
  } else {
    await startGestureRecognition();
  }
}


async function init() {
  resizeCanvas();
  bindEvents();
  showTopPanel('command');
  initSpeechRecognition();
  updateGestureUi(false, '未开启', '等待手势操作');
  
  // 导出导入功能
  el.exportImageBtn = document.getElementById('exportImageBtn');
  el.exportJsonBtn = document.getElementById('exportJsonBtn');
  el.importJsonBtn = document.getElementById('importJsonBtn');
  el.importFileInput = document.getElementById('importFileInput');

  // 导出为图片
  el.exportImageBtn.addEventListener('click', () => {
    const canvas = el.planCanvas;
    const link = document.createElement('a');
    link.download = `户型图_${new Date().toISOString().slice(0, 10)}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    setMessage('户型图已导出', 'success');
  });

  // 导出为JSON
  el.exportJsonBtn.addEventListener('click', async () => {
    try {
      const response = await fetch('/api/state');
      const data = await response.json();
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const link = document.createElement('a');
      link.download = `户型配置_${new Date().toISOString().slice(0, 10)}.json`;
      link.href = URL.createObjectURL(blob);
      link.click();
      setMessage('配置文件已导出', 'success');
    } catch (error) {
      console.error('导出JSON失败:', error);
      setMessage('导出配置文件失败', 'error');
    }
  });

  // 导入JSON
  el.importJsonBtn.addEventListener('click', () => {
    el.importFileInput.click();
  });

  el.importFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const jsonData = JSON.parse(event.target.result);
          const response = await fetch('/api/import', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(jsonData)
          });
          const result = await response.json();
          if (result.ok) {
            setMessage('配置文件已导入', 'success');
            // 重新加载状态，等待加载完成
            await loadState();
          } else {
            setMessage(`导入失败: ${result.message}`, 'error');
          }
        } catch (error) {
          console.error('解析JSON失败:', error);
          setMessage('解析配置文件失败', 'error');
        }
      };
      reader.readAsText(file);
    } catch (error) {
      console.error('导入文件失败:', error);
      setMessage('导入配置文件失败', 'error');
    }
  });
  
  await loadState();
  
  // 初始化AI户型模块
  initAIFloorplanModule();
}

init();

// AI户型图功能实现区域开始
// 1. AI生成户型图按钮点击事件
// 2. 上传户型图按钮点击事件
// 3. 保存户型图按钮点击事件
// 4. 应用户型按钮点击事件
// 5. 与后端API的交互逻辑

// 初始化AI户型模块事件监听器
function initAIFloorplanModule() {
  if (!el.aiFloorplanInput || !el.aiGenerateFloorplanBtn) return;

  el.aiFloorplanInput.addEventListener('input', function() {
    const inputValue = this.value.trim();
    el.aiGenerateFloorplanBtn.disabled = !inputValue;
  });

  el.aiGenerateFloorplanBtn.disabled = !el.aiFloorplanInput.value.trim();

  el.aiGenerateFloorplanBtn.addEventListener('click', async () => {
    const prompt = el.aiFloorplanInput.value.trim();
    if (!prompt) {
      setMessage('请输入户型图描述', 'error');
      return;
    }

    el.floorplanStatusText.textContent = '正在生成户型图...';
    try {
      const response = await fetch('/api/ai/generate_floorplan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt: prompt })
      });

      console.log('API响应状态:', response.status);

      const responseText = await response.text();
      let result;

      try {
        result = JSON.parse(responseText);
      } catch (e) {
        console.error('解析接口返回的不是JSON:', responseText.slice(0, 500));
        throw new Error(`解析接口返回异常，HTTP ${response.status}`);
      }

      console.log('API响应结果:', result);
      if (result.ok) {
        const imageUrl =
          result.image_url ||
          result.result?.image_url ||
          result.result?.url ||
          result.result;

        if (!imageUrl || typeof imageUrl !== 'string') {
          throw new Error('后端没有返回有效的户型图图片地址');
        }

        el.floorplanPreview.innerHTML = `
          <img
            src="${imageUrl}"
            alt="生成的户型图"
            class="floorplan-preview-img"
            onload="this.classList.add('loaded')"
            onerror="this.parentElement.innerHTML='<div class=&quot;floorplan-placeholder&quot;>图片加载失败，请重新生成</div>'"
          >
        `;
        el.floorplanStatusText.textContent = '户型图生成成功！';
        setMessage('户型图生成成功', 'success');
      } else {
        el.floorplanStatusText.textContent = '生成失败，请重试';
        setMessage(`生成失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('生成户型图失败:', error);
      el.floorplanStatusText.textContent = '生成失败，请重试';
      setMessage('户型图生成失败', 'error');
    }
  });

  // 上传户型图
  el.uploadFloorplanBtn.addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        try {
          // 使用FileReader预览本地图片
          const reader = new FileReader();
          reader.onload = (event) => {
            // 显示图片，设置样式确保适应预览区不拉伸
            el.floorplanPreview.innerHTML = `<img src="${event.target.result}" alt="上传的户型图" style="max-width: 100%; max-height: 100%; object-fit: contain;">`;
            el.floorplanStatusText.textContent = '户型图已上传成功！';
            setMessage('户型图上传成功', 'success');
          };
          reader.readAsDataURL(file);
        } catch (error) {
          console.error('上传户型图失败:', error);
          el.floorplanStatusText.textContent = '上传失败，请重试';
          setMessage('户型图上传失败', 'error');
        }
      }
    };
    input.click();
  });

  // 保存户型图
  el.saveFloorplanBtn.addEventListener('click', () => {
    const previewContent = el.floorplanPreview.innerHTML;
    if (!previewContent.includes('img')) {
      setMessage('请先生成或上传户型图', 'error');
      return;
    }

    // 提取图片URL
    const imgElement = el.floorplanPreview.querySelector('img');
    if (imgElement) {
      const link = document.createElement('a');
      link.download = `户型图_${new Date().toISOString().slice(0, 10)}.png`;
      link.href = imgElement.src;
      link.click();
      el.floorplanStatusText.textContent = '户型图已保存！';
      setMessage('户型图保存成功', 'success');
    } else {
      setMessage('保存户型图失败', 'error');
    }
  });

  // 应用户型
  el.applyFloorplanBtn.addEventListener('click', async () => {
    console.log('应用户型按钮被点击');
    const previewContent = el.floorplanPreview.innerHTML;
    if (!previewContent.includes('img')) {
      setMessage('请先生成或上传户型图', 'error');
      return;
    }

    el.floorplanStatusText.textContent = '正在解析户型图...';
    try {
      const imgElement = el.floorplanPreview.querySelector('img');
      const imageUrl = imgElement.src;
      
      // 区分本地图片和网络图片
      let image_base64 = '';
      let image_url = '';
      
      if (imageUrl.startsWith('data:image/')) {
        // 本地上传的图片，提取Base64
        console.log('本地图片，提取Base64');
        image_base64 = imageUrl.split(',')[1];
      } else {
        // 网络图片（AI生成），直接传URL
        console.log('网络图片，传递URL');
        image_url = imageUrl;
      }
      
      // 调用后端API解析户型图
      console.log('开始调用API解析户型图');
      const response = await fetch('/api/ai/parse_floorplan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          image_url: image_url,
          image_base64: image_base64
        })
      });
      
      console.log('API响应状态:', response.status);
      const result = await response.json();
      console.log('API响应结果:', result);
      if (result.ok) {
        // 解析结果
        const parseResult = result.result;
        
        // 写入tmp.json文件（模拟）
        try {
          // 这里需要将解析结果转换为与导出格式一致的JSON
          // 标准化导入的数据，确保所有字段都有合理的默认值
          const normalizedRooms = (parseResult.rooms || []).map((room, index) => ({
            id: room.id || `room_${index + 1}`,
            name: room.name || `房间${index + 1}`,
            x: Number(room.x || 0),
            y: Number(room.y || 0),
            width: Number(room.width || 3),
            depth: Number(room.depth || 3),
            height: Number(room.height || 3),
            wall_color: room.wall_color || '#f0efe9',
                      }));

          const normalizedFurnitures = (parseResult.furnitures || []).map((item, index) => ({
            id: item.id || `furniture_${index + 1}`,
            type: item.type || 'loungeSofa',
            label: item.label || '家具',
            room_id: item.room_id || normalizedRooms[0]?.id || null,
            x: Number(item.x || 0),
            y: Number(item.y || 0),
            z: Number(item.z || 0),
            width: Number(item.width || 1),
            depth: Number(item.depth || 1),
            height: Number(item.height || 0.8),
            rotation: Number(item.rotation || 0),
            color: item.color || '#6f7d8c',
            material: item.material || '布艺',
          }));

          const normalizedOpenings = (parseResult.openings || []).map((item, index) => ({
            id: item.id || `opening_${index + 1}`,
            type: item.type || 'door',
            name: item.name || '门窗',
            room_id: item.room_id || normalizedRooms[0]?.id || null,
            wall: item.wall || 'top',
            offset: Number(item.offset || 0),
            width: Number(item.width || 1),
            height: Number(item.height || 2.1),
            sill: Number(item.sill || 0),
            color: item.color || '#8b6a4d',
            material: item.material || '木纹',
          }));

          const floorplanData = {
            rooms: normalizedRooms,
            furnitures: normalizedFurnitures,
            openings: normalizedOpenings,
            options: {
              room_types: ["卧室", "浴室", "客厅", "饭厅", "厨房", "阳台"],
              room_materials: ["木纹", "布艺", "皮质", "绒面", "金属", "石材", "白色瓷砖", "大理石", "原木风", "玻璃", "烤漆", "混凝土", "陶瓷"],
              opening_types: [{ "label": "门", "value": "door" }, { "label": "窗", "value": "window" }],
              walls: [{ "label": "上墙", "value": "top" }, { "label": "右墙", "value": "right" }, { "label": "下墙", "value": "bottom" }, { "label": "左墙", "value": "left" }],
              furniture_catalog: []
            },
            grid_size_m: 0.5,
            show_grid: true,
            message: "户型已导入成功！"
          };
          
          // 导入到2D和3D界面
          // 使用现有的导入逻辑
          const importResponse = await fetch('/api/import', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(floorplanData)
          });
          
          const importResult = await importResponse.json();
          if (importResult.ok) {
            // 重新加载状态，更新2D和3D界面
            await loadState();
            el.floorplanStatusText.textContent = '户型已导入成功！';
            setMessage('户型应用成功', 'success');
          } else {
            el.floorplanStatusText.textContent = '导入失败，请重试';
            setMessage(`导入失败: ${importResult.message}`, 'error');
          }
        } catch (error) {
          console.error('写入tmp.json失败:', error);
          el.floorplanStatusText.textContent = '应用失败，请重试';
          setMessage('户型应用失败', 'error');
        }
      } else {
        el.floorplanStatusText.textContent = '解析失败，请重试';
        setMessage(`解析失败: ${result.message}`, 'error');
      }
    } catch (error) {
      console.error('应用户型失败:', error);
      el.floorplanStatusText.textContent = '应用失败，请重试';
      setMessage('户型应用失败', 'error');
    }
  });
}

// AI户型图功能实现区域结束
