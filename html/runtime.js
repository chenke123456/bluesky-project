const POLL_INTERVAL_MS = 650;
const REACT_VERSION = "19.2.8";
const THREE_VERSION = "0.185.1";

const rootElement = document.getElementById("bluenode-runtime");
const params = new URLSearchParams(window.location.search);
const legacyStream = params.get("stream") || "";
const uiStream = params.get("ui") || legacyStream || "BlueNode/ui";
const dataStream = params.get("data") || (legacyStream ? legacyStream : "BlueNode/data");
const debugEnabled = params.get("debug") !== "0";

let refreshBusy = false;
let lastSignature = "";
let reactRuntime = null;
let threePromise = null;
let orbitControlsPromise = null;
const appState = {
  selectedEntity: null,
  ui: null,
  dataContext: null,
  meta: null,
};

function normalizeColor(value) {
  if (!value) return null;
  const text = String(value).trim();
  // Color names are resolved once in Python COLOR_MAP. Runtime only consumes
  // concrete CSS / Three.js color values, so there is no second legacy palette.
  if (/^#[0-9a-fA-F]{3,8}$/.test(text) || /^(rgb|hsl)a?\(/i.test(text)) return text;
  return null;
}

function effectiveBackendRuleColor(backendEntity) {
  // Entity-instancer overrides live in the effective entity rules.  Read those
  // rules directly so rendering does not depend on World having copied the
  // value into appearance.color first.  Last rule wins, matching Python.
  const sources = [];
  if (Array.isArray(backendEntity?.rules)) sources.push(...backendEntity.rules);
  else {
    if (Array.isArray(backendEntity?.properties)) sources.push(...backendEntity.properties);
    if (Array.isArray(backendEntity?.methods)) sources.push(...backendEntity.methods);
  }

  for (let index = sources.length - 1; index >= 0; index -= 1) {
    const rule = sources[index];
    if (!rule || typeof rule !== "object") continue;
    const isColor = rule.rule_type === "color" || rule.rule_type === "appearance.color" || rule.name === "颜色规则";
    if (!isColor) continue;
    const compiled = normalizeColor(rule?.params?.color);
    if (compiled) return compiled;
  }
  return null;
}

function resolvedBackendColor(backendEntity, viewerColor = null) {
  const ruleColor = effectiveBackendRuleColor(backendEntity);
  const entityColor = normalizeColor(backendEntity?.appearance?.color);
  const source = backendEntity?.appearance?.color_source;

  // Strict priority:
  // effective instance/entity color rule > explicit backend appearance >
  // viewer fallback > backend type default > neutral fallback.
  if (ruleColor) return ruleColor;
  if (entityColor && source !== "default") return entityColor;
  return viewerColor || entityColor || "#8b949e";
}


// Renderer-level visual fallback only. World does not define entity geometry.
const DEFAULT_RENDER_SIZE = {
  house: { x: 4.0, y: 2.5, z: 4.0 },
  room: { x: 3.0, y: 2.4, z: 3.0 },
  human: { x: 0.6, y: 1.8, z: 0.6 },
  machine: { x: 1.6, y: 1.6, z: 1.6 },
  device: { x: 0.9, y: 0.9, z: 0.9 },
  furniture: { x: 1.6, y: 1.0, z: 1.2 },
  door: { x: 1.0, y: 2.1, z: 0.2 },
  wall: { x: 3.0, y: 2.4, z: 0.2 },
  plant: { x: 0.8, y: 1.2, z: 0.8 },
  animal: { x: 1.0, y: 0.8, z: 1.4 },
  custom: { x: 1.0, y: 1.0, z: 1.0 },
};

function numeric(value, fallback = 0) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback;
}

function backendRuleSources(entity) {
  if (Array.isArray(entity?.rules) && entity.rules.length) return entity.rules;
  const sources = [];
  if (Array.isArray(entity?.properties)) sources.push(...entity.properties);
  if (Array.isArray(entity?.methods)) sources.push(...entity.methods);
  return sources;
}

function backendLastRule(entity, ruleType, ruleName) {
  const sources = backendRuleSources(entity);
  for (let index = sources.length - 1; index >= 0; index -= 1) {
    const rule = sources[index];
    if (!rule || typeof rule !== "object") continue;
    if (rule.rule_type === ruleType || rule.name === ruleName) return rule;
  }
  return null;
}

function backendPositionVector3(entity) {
  const rule = backendLastRule(entity, "position.3d", "三维位置规则");
  const vector = rule?.params?.vector;
  if (!vector || typeof vector !== "object") return null;
  return {
    x: numeric(vector.x, 0),
    y: numeric(vector.y, 0),
    z: numeric(vector.z, 0),
  };
}

// Three.js-facing selector input is compiled at render time from rules only.
// Entity name/category/geometry never supplies a missing draw or size rule.
function renderSpecFromRules(entity) {
  const drawRule = backendLastRule(entity, "geometry.draw", "绘制规则");
  const sizeRule = backendLastRule(entity, "geometry.size", "尺寸规则");
  if (!drawRule || !sizeRule) return null;

  const draw = drawRule.params && typeof drawRule.params === "object" ? { ...drawRule.params } : {};
  const size = sizeRule.params && typeof sizeRule.params === "object" ? { ...sizeRule.params } : {};
  const shape = String(draw.shape || "");
  const sizeShape = String(size.shape || size.for_shape || "");
  if (!shape || (sizeShape && sizeShape !== shape)) return null;

  delete draw.part_name;
  delete size.part_name;
  delete size.shape;
  delete size.for_shape;
  return { draw, size };
}

function renderSpecEnvelope(entity) {
  const spec = renderSpecFromRules(entity);
  const draw = spec?.draw;
  const size = spec?.size;
  if (!draw || !size) return null;

  const shape = String(draw.shape || "");
  const axis = String(draw.axis || "X").toUpperCase();
  const diameter = Math.max(0.05, numeric(size.diameter, 1));
  let primary = null;

  if (shape === "shell") primary = Math.max(0.05, numeric(size.length, 1));
  else if (shape === "head") primary = Math.max(0.03, numeric(size.depth, diameter * 0.25));
  else if (shape === "tube_sheet" || shape === "baffle") primary = Math.max(0.015, numeric(size.thickness, 0.08));
  else return null;

  if (axis === "Y") return { x: diameter, y: primary, z: diameter };
  if (axis === "Z") return { x: diameter, y: diameter, z: primary };
  return { x: primary, y: diameter, z: diameter };
}

function resolvedEntitySize(entity) {
  // Three.js 尺寸优先且只从 geometry.size 规则推导；实体自身 size 仅作为
  // 非规则对象的布局元数据，不参与几何选择。
  const fromRules = renderSpecEnvelope(entity);
  if (fromRules) return fromRules;

  const explicit = entity?.size;
  if (explicit && typeof explicit === "object") {
    return {
      x: Math.max(0.05, numeric(explicit.x ?? explicit.width, 1)),
      y: Math.max(0.05, numeric(explicit.y ?? explicit.height, 1)),
      z: Math.max(0.05, numeric(explicit.z ?? explicit.depth, 1)),
    };
  }

  const type = entity?.entity_type || entity?.type || entity?.name || "custom";
  return { ...(DEFAULT_RENDER_SIZE[type] || DEFAULT_RENDER_SIZE.custom) };
}

function readPluginManifest() {
  const element = document.getElementById("bluenode-plugin-manifest");
  if (!element) return null;
  try {
    const value = JSON.parse(element.textContent || "{}");
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

const pluginManifest = readPluginManifest();

function pluginEnabled(name) {
  // /bluenode/live is a generic development shell and may not have a manifest.
  // Generated /bluenode/site pages always receive a manifest from BlueHtmlOutputNode.
  if (!pluginManifest) return true;
  return pluginManifest[name] === true;
}

function stableSignature(value) {
  try { return JSON.stringify(value); } catch { return String(Date.now()); }
}

async function fetchStream(stream) {
  const url = new URL("/bluenode/live-data", window.location.origin);
  url.searchParams.set("stream", stream);
  url.searchParams.set("_t", String(Date.now()));
  const response = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
  const payload = await response.json();
  if (!response.ok || !payload.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function loadReact() {
  if (!pluginEnabled("react")) throw new Error("React plugin is not enabled for this page");
  if (reactRuntime) return reactRuntime;
  const React = await import(`https://esm.sh/react@${REACT_VERSION}`);
  const ReactDOMClient = await import(`https://esm.sh/react-dom@${REACT_VERSION}/client?deps=react@${REACT_VERSION}`);
  reactRuntime = { React, createRoot: ReactDOMClient.createRoot, root: null };
  return reactRuntime;
}

async function loadThree() {
  if (!pluginEnabled("three")) throw new Error("Three.js plugin is not enabled for this page");
  if (!threePromise) {
    // Three.js 与 OrbitControls 都走同一个 esm.sh 版本，避免出现两份 Three 实例。
    threePromise = import(`https://esm.sh/three@${THREE_VERSION}`);
  }
  return threePromise;
}

async function loadOrbitControls() {
  if (!orbitControlsPromise) {
    orbitControlsPromise = import(`https://esm.sh/three@${THREE_VERSION}/examples/jsm/controls/OrbitControls.js?deps=three@${THREE_VERSION}`);
  }
  return orbitControlsPromise;
}

function rulesFor(entity, ui, type) {
  const ids = new Set(entity.rules || []);
  return (ui.rules || []).filter(rule => ids.has(rule.id) && rule.rule_type === type);
}

function globalRulesFor(ui, type) {
  const ids = new Set(ui?.global_rules || []);
  return (ui?.rules || []).filter(rule => ids.has(rule.id) && rule.rule_type === type);
}

function globalRuleParams(ui, type) {
  const rules = globalRulesFor(ui, type);
  const rule = rules.length ? rules[rules.length - 1] : null;
  return rule?.params && typeof rule.params === "object" ? rule.params : {};
}

function firstOption(entity, ui, type) {
  const rule = rulesFor(entity, ui, type)[0];
  // Color rules are compiled by Python from COLOR_MAP into params.color (HEX).
  // Prefer that canonical value instead of passing the Chinese color label to runtime.
  if (type === "appearance.color" && rule?.params?.color) return rule.params.color;
  return rule?.options?.[0] ?? null;
}

function cameraRuleParams(entity, ui) {
  const rule = rulesFor(entity, ui, "view.camera")[0];
  const params = rule?.params && typeof rule.params === "object" ? rule.params : {};
  const number = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const position = params.position && typeof params.position === "object" ? params.position : { x: 9, y: 7, z: 11 };
  const target = params.target && typeof params.target === "object" ? params.target : { x: 0, y: 0, z: 0 };
  return {
    projection: params.projection === "orthographic" ? "orthographic" : "perspective",
    position: { x: number(position.x, 9), y: number(position.y, 7), z: number(position.z, 11) },
    target: { x: number(target.x, 0), y: number(target.y, 0), z: number(target.z, 0) },
    fov: Math.min(120, Math.max(10, number(params.fov, 45))),
    orbit: params.orbit !== false,
    pan: params.pan !== false,
    zoom: params.zoom !== false,
    minDistance: Math.max(0.05, number(params.min_distance, 1)),
    maxDistance: Math.max(0.1, number(params.max_distance, 50)),
    rotateSpeed: Math.max(0, number(params.rotate_speed, 1)),
    panSpeed: Math.max(0, number(params.pan_speed, 1)),
    zoomSpeed: Math.max(0, number(params.zoom_speed, 1)),
  };
}

function ruleParams(entity, ui, type) {
  const rule = rulesFor(entity, ui, type)[0];
  if (!rule) return {};
  if (rule.params && typeof rule.params === "object") return rule.params;
  // Compatibility with older movement rules that only carried `options`.
  if (type === "behavior.move") {
    const options = rule.options || [];
    return {
      mode: options[0] || "平移",
      direction: options[1] || "向右",
      distance: options[2] || "50px",
      speed: options[3] || "100px/s",
      space: options[4] || "本地空间",
      loop: options[5] || "单次",
    };
  }
  return {};
}

function uiPositionVector2(entity, ui) {
  const params = ruleParams(entity, ui, "layout.position.2d");
  const vector = params?.vector;
  if (!vector || typeof vector !== "object") return null;
  return { x: numeric(vector.x, 0), y: numeric(vector.y, 0) };
}

function controlLayoutStyle(entity, ui) {
  const params = ruleParams(entity, ui, "layout.controls");
  if (!params || !Object.keys(params).length) return {};

  const mode = String(params.mode || "column");
  const gap = String(params.gap || "12px");
  const justify = String(params.justify || "flex-start");
  const align = String(params.align || "stretch");
  const wrap = String(params.wrap || "wrap");
  const style = { gap };

  if (mode === "grid") {
    const rawColumns = Math.floor(numeric(params.columns, 0));
    const columns = rawColumns > 0 ? Math.max(1, Math.min(12, rawColumns)) : 0;
    style.display = "grid";
    style.gridTemplateColumns = columns > 0
      ? `repeat(${columns}, minmax(0, 1fr))`
      : "repeat(auto-fit, minmax(180px, 1fr))";
    style.justifyContent = justify;
    style.alignItems = align;
    return style;
  }

  if (mode === "free") {
    style.display = "block";
    return style;
  }

  style.display = "flex";
  style.flexDirection = mode === "row" ? "row" : "column";
  style.justifyContent = justify;
  style.alignItems = align;
  style.flexWrap = wrap;
  return style;
}


function websiteLayoutStyle(params) {
  if (!params || !Object.keys(params).length) return {};

  const mode = String(params.mode || "column");
  const gap = String(params.gap || "12px");
  const justify = String(params.justify || "flex-start");
  const align = String(params.align || "stretch");
  const wrap = String(params.wrap || "wrap");
  const rawColumns = Math.floor(numeric(params.columns, 0));
  const columns = rawColumns > 0 ? Math.max(1, Math.min(12, rawColumns)) : 0;

  // 布局规则是纯网站规则。这里用明确 if 分发，不交给 Three.js。
  if (mode === "column") {
    return {
      display: "flex",
      flexDirection: "column",
      justifyContent: justify,
      alignItems: align,
      flexWrap: wrap,
      gap,
    };
  }

  if (mode === "row") {
    return {
      display: "flex",
      flexDirection: "row",
      justifyContent: justify,
      alignItems: align,
      flexWrap: wrap,
      gap,
    };
  }

  if (mode === "grid") {
    return {
      display: "grid",
      gridTemplateColumns: columns > 0
        ? `repeat(${columns}, minmax(0, 1fr))`
        : "repeat(auto-fit, minmax(220px, 1fr))",
      justifyContent: justify,
      alignItems: align,
      gap,
    };
  }

  if (mode === "split") {
    return {
      display: "grid",
      gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
      alignItems: align,
      gap,
    };
  }

  if (mode === "main_aside") {
    return {
      display: "grid",
      gridTemplateColumns: "minmax(0, 2fr) minmax(220px, 1fr)",
      alignItems: align,
      gap,
    };
  }

  if (mode === "aside_main") {
    return {
      display: "grid",
      gridTemplateColumns: "minmax(220px, 1fr) minmax(0, 2fr)",
      alignItems: align,
      gap,
    };
  }

  if (mode === "header_main") {
    return {
      display: "grid",
      gridTemplateColumns: "minmax(0, 1fr)",
      gridAutoRows: "max-content",
      alignItems: align,
      gap,
    };
  }

  if (mode === "header_split") {
    return {
      display: "grid",
      gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
      gridAutoRows: "max-content",
      alignItems: align,
      gap,
    };
  }

  if (mode === "dashboard") {
    return {
      display: "grid",
      gridTemplateColumns: columns > 0
        ? `repeat(${columns}, minmax(0, 1fr))`
        : "repeat(3, minmax(0, 1fr))",
      gridAutoRows: "minmax(120px, auto)",
      gridAutoFlow: "dense",
      alignItems: align,
      gap,
    };
  }

  if (mode === "free") {
    return {
      display: "block",
      position: "relative",
      minHeight: "70vh",
    };
  }

  return {};
}

function websiteLayoutItemStyle(params, index, total) {
  const mode = String(params?.mode || "column");

  if (mode === "main_aside") {
    if (index === 0) return { gridColumn: "1", gridRow: `1 / span ${Math.max(1, total - 1)}` };
    return { gridColumn: "2" };
  }

  if (mode === "aside_main") {
    if (index === 0) return { gridColumn: "2", gridRow: `1 / span ${Math.max(1, total - 1)}` };
    return { gridColumn: "1" };
  }

  if (mode === "header_main") {
    if (index === 0) return { gridColumn: "1 / -1" };
    return { gridColumn: "1 / -1" };
  }

  if (mode === "header_split") {
    if (index === 0) return { gridColumn: "1 / -1" };
    return {};
  }

  if (mode === "dashboard") {
    const columns = Math.max(1, Math.floor(numeric(params?.columns, 3)) || 3);
    if (index === 0 && columns >= 2 && total > 2) {
      return { gridColumn: "span 2", gridRow: "span 2" };
    }
    return {};
  }

  return {};
}

function numberFromUnit(value, fallback) {
  const match = String(value ?? "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : fallback;
}

function movementVector(direction, distance) {
  const d = Math.max(0, numberFromUnit(distance, 50));
  const vectors = {
    "向左": [-d, 0, 0], "X负": [-d, 0, 0],
    "向右": [d, 0, 0], "X正": [d, 0, 0],
    "向上": [0, -d, 0], "Y负": [0, -d, 0],
    "向下": [0, d, 0], "Y正": [0, d, 0],
    "Z正": [0, 0, d], "Z负": [0, 0, -d],
  };
  if (direction === "随机") {
    const angle = Math.random() * Math.PI * 2;
    return [Math.cos(angle) * d, Math.sin(angle) * d, 0];
  }
  return vectors[direction] || [d, 0, 0];
}

function movementAnimation(entity, ui) {
  const params = ruleParams(entity, ui, "behavior.move");
  if (!Object.keys(params).length) return null;
  const distance = Math.max(0, numberFromUnit(params.distance, 50));
  const speed = Math.max(0, numberFromUnit(params.speed, 100));
  if (params.speed === "停止" || speed <= 0 || distance <= 0) return null;

  const [x, y, z] = movementVector(params.direction, params.distance);
  const transform = (tx, ty, tz) => `translate3d(${tx}px, ${ty}px, ${tz}px)`;
  let keyframes;
  if (params.mode === "轨道") {
    const r = distance;
    keyframes = [
      { transform: transform(0, 0, 0) },
      { transform: transform(r, r, 0) },
      { transform: transform(0, r * 2, 0) },
      { transform: transform(-r, r, 0) },
      { transform: transform(0, 0, 0) },
    ];
  } else {
    keyframes = [
      { transform: transform(0, 0, 0) },
      { transform: transform(x, y, z) },
    ];
  }

  const oneWayMs = Math.max(16, (distance / speed) * 1000);
  const loop = params.loop || (params.mode === "往返" ? "往返循环" : "单次");
  return {
    params,
    keyframes,
    options: {
      duration: params.mode === "轨道" ? oneWayMs * 4 : oneWayMs,
      iterations: loop === "单次" ? 1 : Infinity,
      direction: loop === "往返循环" || params.mode === "往返" ? "alternate" : "normal",
      easing: "linear",
      fill: loop === "单次" ? "forwards" : "none",
    },
  };
}

function projection(entity) {
  return entity?.view?.component || "react.Card";
}

function styleFromRules(entity, ui) {
  const style = {};
  const color = normalizeColor(firstOption(entity, ui, "appearance.color"));
  if (color) {
    style.borderColor = color;
    if (entity?.role === "action") style.background = color;
  }

  const sizeRule = rulesFor(entity, ui, "layout.size")[0];
  const sizeOptions = sizeRule?.options || [];
  const width = sizeOptions[0];
  const height = sizeOptions[1];
  if (width && width !== "自动") style.width = width;
  if (height && height !== "自动") style.height = height;

  const material = firstOption(entity, ui, "appearance.material");
  if (material === "玻璃") {
    style.background = "rgba(255,255,255,.06)";
    style.backdropFilter = "blur(12px)";
  } else if (material === "金属") {
    style.background = "linear-gradient(145deg,#252a32,#15181e)";
  } else if (material === "木材") {
    style.background = "linear-gradient(145deg,#2c211b,#171311)";
  }
  return style;
}

function classFromRules(entity, ui) {
  const classes = ["bn-component"];
  const topology = firstOption(entity, ui, "layout.topology");
  if (topology === "网格") classes.push("bn-layout-grid");
  else if (topology === "放射状" || topology === "环状") classes.push("bn-layout-radial");
  else if (topology === "线性" || topology === "树状") classes.push("bn-layout-linear");

  const load = firstOption(entity, ui, "layout.load");
  if (load === "轻载") classes.push("bn-load-light");
  else if (load === "中载") classes.push("bn-load-medium");
  else if (load === "重载") classes.push("bn-load-heavy");

  const stability = firstOption(entity, ui, "state.stability");
  if (stability === "锁定") classes.push("bn-state-locked");
  else if (stability === "不稳定" || stability === "临界") classes.push("bn-state-unstable");
  if (appState.selectedEntity === entity.id) classes.push("bn-selected");
  return classes.join(" ");
}

function shouldDisable(entity, ui) {
  return firstOption(entity, ui, "behavior.conduction") === "禁止传导" ||
    firstOption(entity, ui, "state.stability") === "锁定";
}

function emitAction(entity, ui, eventName = "click") {
  const conduction = firstOption(entity, ui, "behavior.conduction") || "信号传导";
  const collision = firstOption(entity, ui, "behavior.collision");
  const detail = {
    entity,
    event: eventName,
    rule: { conduction, collision },
    state: { selectedEntity: appState.selectedEntity },
    streams: { ui: uiStream, data: dataStream },
  };
  window.dispatchEvent(new CustomEvent("bluenode:action", { detail }));
}

function selectEntity(entity, ui) {
  appState.selectedEntity = entity.id;
  emitAction(entity, ui, "select");
  renderCurrent();
}

function summarizeData(dataContext) {
  const meta = dataContext?.meta || {};
  return {
    count: meta.entity_count || 0,
    objects: meta.json_object_count || 0,
    types: Object.entries(meta.type_counts || {}),
  };
}

function businessEntities(dataContext) {
  return Array.isArray(dataContext?.entities) ? dataContext.entities : [];
}

function ruleRenderSummary(dataContext) {
  const entities = businessEntities(dataContext);
  const renderable = entities.filter(item => item?.renderable !== false && !!renderSpecFromRules(item));
  const positioned3d = entities.filter(item => !!backendPositionVector3(item));
  const moving = entities.filter(item => Object.keys(backendMovementParams(item)).length > 0);
  const withDrawRule = entities.filter(item => !!backendLastRule(item, "geometry.draw", "绘制规则"));
  const withSizeRule = entities.filter(item => !!backendLastRule(item, "geometry.size", "尺寸规则"));
  return {
    entities,
    renderable,
    positioned3d,
    moving,
    withDrawRule,
    withSizeRule,
  };
}

function readableShape(entity) {
  const spec = renderSpecFromRules(entity);
  const shape = String(spec?.draw?.shape || "");
  const labels = {
    shell: "筒体",
    head: "封头",
    tube_sheet: "管板",
    baffle: "折流板",
  };
  return labels[shape] || shape || "未配置绘图规则";
}

function readableMovement(entity) {
  const movement = backendMovementParams(entity);
  if (!Object.keys(movement).length) return "静止";
  if (movement.mode === "旋转") {
    const direction = movement.rotation_direction || movement.direction || "旋转";
    const speed = movement.angular_speed || movement.speed || "-";
    return `${direction} · ${speed}`;
  }
  return `${movement.mode || "移动"} · ${movement.direction || "-"} · ${movement.speed || "-"}`;
}

function backendMethodRule(entity, ruleType) {
  const methods = Array.isArray(entity?.methods) ? entity.methods : [];
  const rules = Array.isArray(entity?.rules) ? entity.rules : [];
  return [...methods, ...rules].find(rule => {
    if (!rule || typeof rule !== "object") return false;
    return rule.rule_type === ruleType ||
      (ruleType === "move" && (rule.name === "移动规则" || rule.rule_type === "behavior.move"));
  }) || null;
}

function backendMovementParams(entity) {
  const rule = backendMethodRule(entity, "move");
  if (!rule) return {};
  if (rule.params && typeof rule.params === "object") return rule.params;
  const options = Array.isArray(rule.options) ? rule.options : [];
  return {
    mode: options[0] || "平移",
    direction: options[1] || "向右",
    distance: options[2] || "50px",
    speed: options[3] || "100px/s",
    space: options[4] || "本地空间",
    loop: options[5] || "单次",
  };
}

// Canonical rule-driven selector. It consumes geometry.draw + geometry.size
// directly from backend rules. Entity identity never creates geometry.
function createObjectFromRuleSelector(THREE, entity, material) {
  const spec = renderSpecFromRules(entity);
  const draw = spec?.draw;
  const size = spec?.size;
  if (!draw || typeof draw !== 'object' || !size || typeof size !== 'object') return null;

  const shape = String(draw.shape || '');
  if (!['shell', 'head', 'tube_sheet', 'baffle'].includes(shape)) return null;

  const axis = String(draw.axis || 'X').toUpperCase();
  const segments = Math.max(8, Math.floor(numeric(draw.segments, 64)));
  const group = new THREE.Group();

  const orientFromX = object => {
    if (axis === 'Y') object.rotation.z += Math.PI / 2;
    else if (axis === 'Z') object.rotation.y -= Math.PI / 2;
    object.userData.renderSpecBaseRotation = {
      x: object.rotation.x, y: object.rotation.y, z: object.rotation.z,
    };
    return object;
  };

  const diameter = Math.max(0.05, numeric(size.diameter, 1));
  const radius = diameter * 0.5;

  if (shape === 'shell') {
    const length = Math.max(0.05, numeric(size.length, 1));
    const wall = Math.max(0, numeric(size.wall_thickness, 0));
    const openEnded = draw.open_ended !== false;

    if (!openEnded) {
      const geometry = new THREE.CylinderGeometry(radius, radius, length, segments, 1, false);
      geometry.rotateZ(Math.PI / 2);
      group.add(new THREE.Mesh(geometry, material));
      orientFromX(group);
      return group;
    }

    const outerGeometry = new THREE.CylinderGeometry(radius, radius, length, segments, 1, true);
    outerGeometry.rotateZ(Math.PI / 2);
    group.add(new THREE.Mesh(outerGeometry, material));

    // If wall thickness is provided, render an inner wall and annular end faces.
    // Without thickness, the open surface remains a lightweight visual shell.
    const innerRadius = Math.max(0, radius - wall);
    if (wall > 0 && innerRadius > 0.001) {
      const innerMaterial = material.clone();
      innerMaterial.side = THREE.BackSide;
      const innerGeometry = new THREE.CylinderGeometry(innerRadius, innerRadius, length, segments, 1, true);
      innerGeometry.rotateZ(Math.PI / 2);
      group.add(new THREE.Mesh(innerGeometry, innerMaterial));

      const edgeMaterial = material.clone();
      edgeMaterial.side = THREE.DoubleSide;
      for (const x of [-length / 2, length / 2]) {
        const ringGeometry = new THREE.RingGeometry(innerRadius, radius, segments);
        ringGeometry.rotateY(Math.PI / 2);
        const ring = new THREE.Mesh(ringGeometry, edgeMaterial);
        ring.position.x = x;
        group.add(ring);
      }
    }

    orientFromX(group);
    return group;
  }

  if (shape === 'head') {
    const depth = Math.max(0.03, numeric(size.depth, diameter * 0.25));
    const thickness = Math.max(0, numeric(size.thickness, 0));
    const side = draw.side === 'left' ? 'left' : 'right';
    const makeHeadGeometry = () => {
      const geometry = new THREE.SphereGeometry(1, segments, Math.max(12, Math.floor(segments / 2)), 0, Math.PI * 2, 0, Math.PI / 2);
      geometry.rotateZ(side === 'left' ? Math.PI / 2 : -Math.PI / 2);
      return geometry;
    };
    const axialOffset = side === 'left' ? depth / 2 : -depth / 2;
    const mesh = new THREE.Mesh(makeHeadGeometry(), material);
    mesh.scale.set(depth, radius, radius);
    mesh.position.x = axialOffset;
    group.add(mesh);

    // Approximate wall thickness with a back-facing inner ellipsoidal surface
    // plus an annular edge at the tangent plane.
    const innerRadius = radius - thickness;
    const innerDepth = depth - thickness;
    if (thickness > 0 && innerRadius > 0.001 && innerDepth > 0.001) {
      const innerMaterial = material.clone();
      innerMaterial.side = THREE.BackSide;
      const inner = new THREE.Mesh(makeHeadGeometry(), innerMaterial);
      inner.scale.set(innerDepth, innerRadius, innerRadius);
      inner.position.x = axialOffset;
      group.add(inner);

      const rimMaterial = material.clone();
      rimMaterial.side = THREE.DoubleSide;
      const rimGeometry = new THREE.RingGeometry(innerRadius, radius, segments);
      rimGeometry.rotateY(Math.PI / 2);
      const rim = new THREE.Mesh(rimGeometry, rimMaterial);
      rim.position.x = axialOffset;
      group.add(rim);
    }

    orientFromX(group);
    return group;
  }

  if (shape === 'tube_sheet') {
    const thickness = Math.max(0.015, numeric(size.thickness, 0.08));
    const geometry = new THREE.CylinderGeometry(radius, radius, thickness, segments);
    geometry.rotateZ(Math.PI / 2);
    group.add(new THREE.Mesh(geometry, material));

    if (draw.show_holes !== false) {
      const tubeCount = Math.max(1, Math.floor(numeric(size.tube_count, 19)));
      const tubeDiameter = Math.max(0.005, numeric(size.tube_diameter, diameter * 0.05));
      const holeMaterial = new THREE.MeshStandardMaterial({ color: 0x15191f, roughness: 0.7, metalness: 0.15 });
      const holeRadius = tubeDiameter * 0.52;
      const points = [[0, 0]];
      const rings = tubeCount <= 7 ? 1 : tubeCount <= 19 ? 2 : tubeCount <= 37 ? 3 : 4;
      for (let ring = 1; ring <= rings && points.length < tubeCount; ring += 1) {
        const count = ring * 6;
        const rr = radius * Math.min(0.78, 0.27 + (ring - 1) * 0.18);
        for (let i = 0; i < count && points.length < tubeCount; i += 1) {
          const angle = (i / count) * Math.PI * 2;
          points.push([Math.cos(angle) * rr, Math.sin(angle) * rr]);
        }
      }
      for (const [y, z] of points.slice(0, tubeCount)) {
        const holeGeometry = new THREE.CylinderGeometry(holeRadius, holeRadius, thickness * 1.12, Math.min(24, segments));
        holeGeometry.rotateZ(Math.PI / 2);
        const hole = new THREE.Mesh(holeGeometry, holeMaterial);
        hole.position.set(0, y, z);
        group.add(hole);
      }
    }

    orientFromX(group);
    return group;
  }

  if (shape === 'baffle') {
    const thickness = Math.max(0.015, numeric(size.thickness, 0.05));
    const cutRatio = Math.min(0.45, Math.max(0.05, numeric(size.cut_ratio, 0.25)));
    const chordY = radius * (1 - 2 * cutRatio);
    const alpha = Math.asin(Math.max(-0.999, Math.min(0.999, chordY / radius)));
    const start = Math.PI - alpha;
    const end = Math.PI * 2 + alpha;
    const baffleShape = new THREE.Shape();
    baffleShape.moveTo(radius * Math.cos(start), radius * Math.sin(start));
    baffleShape.absarc(0, 0, radius, start, end, false);
    baffleShape.closePath();
    const geometry = new THREE.ExtrudeGeometry(baffleShape, {
      depth: thickness,
      bevelEnabled: false,
      curveSegments: segments,
    });
    geometry.translate(0, 0, -thickness / 2);
    geometry.rotateY(Math.PI / 2);
    const mesh = new THREE.Mesh(geometry, material);
    if (draw.cut_direction === 'bottom') mesh.rotation.x = Math.PI;
    group.add(mesh);
    orientFromX(group);
    return group;
  }

  return null;
}

function createRegistry(React) {
  const h = React.createElement;
  const { useEffect, useRef, useState } = React;

  function useMovement(entity, ui) {
    const ref = useRef(null);
    const signature = stableSignature(rulesFor(entity, ui, "behavior.move"));
    useEffect(() => {
      const element = ref.current;
      const spec = movementAnimation(entity, ui);
      if (!element || !spec || typeof element.animate !== "function") return undefined;
      element.dataset.bnMoveSpace = spec.params.space || "本地空间";
      element.dataset.bnMoveMode = spec.params.mode || "平移";
      const animation = element.animate(spec.keyframes, spec.options);
      return () => animation.cancel();
    }, [entity.id, signature]);
    return ref;
  }

  function Frame({ entity, ui, children, className = "", onClick }) {
    const movementRef = useMovement(entity, ui);
    return h("div", {
      ref: movementRef,
      className: `${classFromRules(entity, ui)} ${className}`.trim(),
      style: styleFromRules(entity, ui),
      "data-bn-id": entity.id,
      "data-bn-component": projection(entity),
      onClick: onClick || (() => selectEntity(entity, ui)),
    }, children);
  }

  function Header({ entity }) {
    return h("div", { className: "bn-title-row" },
      h("strong", null, entity.label),
      h("span", { className: "bn-badge" }, entity.entity_type)
    );
  }

  function DataSummary({ dataContext }) {
    const summary = summarizeData(dataContext);
    return h("div", { className: "bn-summary" },
      h("div", { className: "bn-badge-row" },
        h("span", { className: "bn-badge" }, `entities ${summary.count}`),
        h("span", { className: "bn-badge" }, `objects ${summary.objects}`)
      ),
      summary.types.length
        ? h("div", { className: "bn-badge-row" }, summary.types.map(([name, count]) =>
            h("span", { key: name, className: "bn-badge" }, `${name} ${count}`)))
        : h("span", { className: "bn-meta" }, "暂无业务实体")
    );
  }

  function Page({ entity, ui, children }) {
    return h(Frame, { entity, ui, className: "bn-page" }, children);
  }

  function Panel({ entity, ui, dataContext, children }) {
    const summary = ruleRenderSummary(dataContext);
    return h(Frame, { entity, ui, className: "bn-panel" },
      h(Header, { entity }),
      h("div", { className: "bn-section-title" }, "后端实体"),
      summary.entities.length
        ? summary.entities.map((item, index) => {
            const spec = renderSpecFromRules(item);
            return h("div", { key: item.id || item.entity_name || index, className: "bn-data-row" },
              h("span", null, item.entity_name || item.entity_item || `实体 ${index + 1}`),
              h("span", { className: spec ? "bn-badge" : "bn-meta" }, spec ? readableShape(item) : "缺少绘图/尺寸规则")
            );
          })
        : h("div", { className: "bn-meta" }, "后端已连接，当前没有业务实体"),
      h("div", { className: "bn-section-title" }, "规则状态"),
      h("div", { className: "bn-data-row" },
        h("span", null, "绘图规则 geometry.draw"),
        h("span", { className: "bn-badge" }, String(summary.withDrawRule.length))
      ),
      h("div", { className: "bn-data-row" },
        h("span", null, "尺寸规则 geometry.size"),
        h("span", { className: "bn-badge" }, String(summary.withSizeRule.length))
      ),
      h("div", { className: "bn-data-row" },
        h("span", null, "三维位置规则 position.3d"),
        h("span", { className: "bn-badge" }, String(summary.positioned3d.length))
      ),
      children ? h("div", { className: "bn-child-layout", style: controlLayoutStyle(entity, ui) }, children) : null
    );
  }

  function Card({ entity, ui, dataContext, children }) {
    const summary = ruleRenderSummary(dataContext);
    return h(Frame, { entity, ui, className: "bn-card" },
      h(Header, { entity }),
      h("div", { className: "bn-section-title" }, "三维渲染数据"),
      summary.renderable.length
        ? summary.renderable.map((item, index) => h("div", { key: item.id || index, className: "bn-data-row" },
            h("span", null, item.entity_name || item.entity_item || `实体 ${index + 1}`),
            h("span", { className: "bn-badge" }, readableShape(item))
          ))
        : h("div", { className: "bn-meta" }, summary.entities.length
            ? "已收到实体，但还没有同时配置绘图规则和尺寸规则"
            : "等待后端实体数据…"),
      h("div", { className: "bn-metric-grid" },
        h("div", { className: "bn-metric" }, h("strong", null, String(summary.entities.length)), h("span", null, "实体")),
        h("div", { className: "bn-metric" }, h("strong", null, String(summary.renderable.length)), h("span", null, "可渲染")),
        h("div", { className: "bn-metric" }, h("strong", null, String(summary.positioned3d.length)), h("span", null, "三维位置"))
      ),
      children ? h("div", { className: "bn-child-layout", style: controlLayoutStyle(entity, ui) }, children) : null
    );
  }

  function Button({ entity, ui }) {
    const movementRef = useMovement(entity, ui);
    return h("button", {
      ref: movementRef,
      type: "button",
      disabled: shouldDisable(entity, ui),
      className: `bn-button ${classFromRules(entity, ui)}`,
      style: styleFromRules(entity, ui),
      "data-bn-id": entity.id,
      "data-bn-component": projection(entity),
      onClick: event => {
        event.stopPropagation();
        appState.selectedEntity = entity.id;
        emitAction(entity, ui, "click");
        renderCurrent();
      },
    }, entity.label);
  }

  function Divider({ entity, ui }) {
    return h(Frame, { entity, ui }, h("div", { className: "bn-divider", title: entity.label }));
  }

  function Control({ entity, ui }) {
    const [value, setValue] = useState(50);
    return h(Frame, { entity, ui, className: "bn-control" },
      h(Header, { entity }),
      h("input", {
        className: "bn-range",
        type: "range",
        min: 0,
        max: 100,
        value,
        disabled: shouldDisable(entity, ui),
        onClick: event => event.stopPropagation(),
        onChange: event => {
          setValue(Number(event.target.value));
          emitAction(entity, ui, "change");
        },
      }),
      h("div", { className: "bn-meta" }, `value ${value}`)
    );
  }

  function Person({ entity, ui }) {
    return h(Frame, { entity, ui, className: "bn-person" },
      h("span", null, entity.label),
      h("span", { className: "bn-badge" }, "person")
    );
  }

  function Status({ entity, ui, dataContext }) {
    const summary = ruleRenderSummary(dataContext);
    // renderCurrent() only mounts the React tree after dataContext exists, so
    // this is a backend-stream connection state, not a geometry-type test.
    const connected = !!dataContext;
    return h(Frame, { entity, ui, className: "bn-status" },
      h("div", { className: "bn-status-main" },
        h("div", null,
          h("div", { className: "bn-eyebrow" }, "BlueNode Rule Renderer"),
          h("strong", { className: "bn-status-title" }, "规则驱动三维系统")
        ),
        h("span", { className: `bn-state-pill ${connected ? "is-ready" : "is-waiting"}` }, connected ? "数据已连接" : "等待后端数据")
      ),
      h("div", { className: "bn-meta" }, connected
        ? `已接收 ${summary.entities.length} 个实体，可渲染 ${summary.renderable.length} 个。Three.js 只读取绘图规则、尺寸规则和三维位置规则。`
        : "请运行 BlueNode/data 后端输出。")
    );
  }

  function Decoration({ entity, ui }) {
    return h(Frame, { entity, ui }, h("span", { className: "bn-decoration" }, entity.label));
  }

  function Indicator({ entity, ui }) {
    return h(Frame, { entity, ui },
      h("div", { className: "bn-indicator", role: "progressbar", "aria-label": entity.label },
        h("div", { className: "bn-indicator-fill" }, entity.label)
      )
    );
  }

  function ThreeViewer({ entity, ui, dataContext }) {
    const hostRef = useRef(null);
    const [error, setError] = useState("");

    useEffect(() => {
      let disposed = false;
      let cleanup = () => {};
      (async () => {
        try {
          setError("");
          const THREE = await loadThree();
          if (disposed || !hostRef.current) return;
          const host = hostRef.current;
          host.replaceChildren();

          const scene = new THREE.Scene();
          const cameraSpec = cameraRuleParams(entity, ui);
          let camera;
          if (cameraSpec.projection === "orthographic") {
            camera = new THREE.OrthographicCamera(-6, 6, 6, -6, 0.1, 1000);
          } else {
            camera = new THREE.PerspectiveCamera(cameraSpec.fov, 1, 0.1, 1000);
          }
          camera.position.set(cameraSpec.position.x, cameraSpec.position.y, cameraSpec.position.z);
          camera.lookAt(cameraSpec.target.x, cameraSpec.target.y, cameraSpec.target.z);

          const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
          renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
          host.appendChild(renderer.domElement);

          const { OrbitControls } = await loadOrbitControls();
          if (disposed) return;
          const controls = new OrbitControls(camera, renderer.domElement);
          controls.target.set(cameraSpec.target.x, cameraSpec.target.y, cameraSpec.target.z);
          controls.enableRotate = cameraSpec.orbit;
          controls.enablePan = cameraSpec.pan;
          controls.enableZoom = cameraSpec.zoom;
          controls.minDistance = Math.min(cameraSpec.minDistance, cameraSpec.maxDistance);
          controls.maxDistance = Math.max(cameraSpec.minDistance, cameraSpec.maxDistance);
          controls.rotateSpeed = cameraSpec.rotateSpeed;
          controls.panSpeed = cameraSpec.panSpeed;
          controls.zoomSpeed = cameraSpec.zoomSpeed;
          controls.enableDamping = true;
          controls.dampingFactor = 0.08;
          controls.update();

          scene.add(new THREE.HemisphereLight(0xffffff, 0x30343b, 2.2));
          const directional = new THREE.DirectionalLight(0xffffff, 2.5);
          directional.position.set(5, 8, 6);
          scene.add(directional);
          scene.add(new THREE.GridHelper(20, 20, 0x334155, 0x1f2937));

          const group = new THREE.Group();
          scene.add(group);
          const backendEntities = Array.isArray(dataContext?.entities)
            ? dataContext.entities.filter(item => item?.renderable !== false)
            : [];
          const renderableEntities = backendEntities.filter(item => !!renderSpecFromRules(item));

          if (!backendEntities.length) {
            host.innerHTML = '<div class="bn-three-fallback"><strong>3D 视图等待后端实体</strong><span>请先运行 BlueNode/data。Three.js 只负责选择器和渲染器。</span></div>';
            return;
          }

          if (!renderableEntities.length) {
            host.innerHTML = '<div class="bn-three-fallback"><strong>后端数据已连接</strong><span>当前实体缺少完整的绘图规则 geometry.draw 或尺寸规则 geometry.size，因此没有可渲染三维对象。</span></div>';
            return;
          }

          const number = numeric;
          // A color rule attached to the website 3D View is only a renderer-level
          // fallback. Effective entity/instance color rules have higher priority.
          const viewerColor = normalizeColor(firstOption(entity, ui, "appearance.color"));
          for (const backendEntity of renderableEntities) {
            const size = resolvedEntitySize(backendEntity);
            const sx = size.x;
            const sy = size.y;
            const sz = size.z;
            const material = new THREE.MeshStandardMaterial({
              color: resolvedBackendColor(backendEntity, viewerColor),
              roughness: numeric(backendEntity?.appearance?.roughness, 0.5),
              metalness: numeric(backendEntity?.appearance?.metalness, 0.35),
            });
            // 规则是唯一的三维几何来源。绘图规则和尺寸规则必须同时存在。
            // Selector 只读取 geometry.draw / geometry.size；缺一则该实体不生成 Mesh。
            const mesh = createObjectFromRuleSelector(THREE, backendEntity, material);
            if (!mesh) continue;
            const positionRule = backendPositionVector3(backendEntity);
            const position = positionRule || backendEntity.transform?.position || {};
            const rotation = backendEntity.transform?.rotation || {};
            if (positionRule) {
              // 三维位置规则表示 Mesh 的世界坐标矢量，直接使用 (x, y, z)。
              mesh.position.set(number(position.x), number(position.y), number(position.z));
            } else {
              // 旧 transform 路径保留原有“落地”偏移，兼容旧工作流。
              mesh.position.set(number(position.x), number(position.y) + sy / 2, number(position.z));
            }
            const baseRotation = mesh.userData?.renderSpecBaseRotation || { x: 0, y: 0, z: 0 };
            mesh.rotation.set(
              number(baseRotation.x) + number(rotation.x),
              number(baseRotation.y) + number(rotation.y),
              number(baseRotation.z) + number(rotation.z)
            );
            mesh.userData.entity = backendEntity;
            mesh.userData.selectable = backendEntity.interaction?.selectable !== false;
            mesh.userData.movement = backendMovementParams(backendEntity);
            group.add(mesh);
          }

          let animationFrame = 0;
          let lastFrameTime = performance.now();
          const animate = now => {
            const dt = Math.min(0.05, Math.max(0, (now - lastFrameTime) / 1000));
            lastFrameTime = now;
            for (const mesh of group.children) {
              const movement = mesh.userData?.movement || {};
              if (movement.mode !== "旋转") continue;
              const speed = Math.max(0, numberFromUnit(movement.angular_speed || movement.speed, 90));
              if (!speed) continue;
              const sign = movement.rotation_direction === "顺时针" || movement.direction === "顺时针" ? -1 : 1;
              const radians = THREE.MathUtils.degToRad(speed) * dt * sign;
              const axis = movement.rotation_axis || "Z轴";
              if (axis === "X轴") mesh.rotation.x += radians;
              else if (axis === "Y轴") mesh.rotation.y += radians;
              else mesh.rotation.z += radians;
            }
            controls.update();
            renderer.render(scene, camera);
            animationFrame = requestAnimationFrame(animate);
          };

          const resize = () => {
            const width = Math.max(host.clientWidth, 1);
            const height = Math.max(host.clientHeight, 1);
            renderer.setSize(width, height, false);
            if (camera.isPerspectiveCamera) {
              camera.aspect = width / height;
            } else if (camera.isOrthographicCamera) {
              const halfHeight = 6;
              const halfWidth = halfHeight * (width / height);
              camera.left = -halfWidth;
              camera.right = halfWidth;
              camera.top = halfHeight;
              camera.bottom = -halfHeight;
            }
            camera.updateProjectionMatrix();
            controls.update();
            renderer.render(scene, camera);
          };
          resize();
          const observer = new ResizeObserver(resize);
          observer.observe(host);
          animationFrame = requestAnimationFrame(animate);

          cleanup = () => {
            cancelAnimationFrame(animationFrame);
            observer.disconnect();
            controls.dispose();
            group.traverse(object => {
              if (object.geometry) object.geometry.dispose?.();
              if (object.material) object.material.dispose?.();
            });
            renderer.dispose();
            renderer.domElement.remove();
          };
        } catch (err) {
          setError(String(err?.message || err));
        }
      })();
      return () => { disposed = true; cleanup(); };
    }, [stableSignature(dataContext?.entities || []), stableSignature(entity.rules || [])]);

    return h(Frame, { entity, ui, className: "bn-viewer" },
      h("div", { className: "bn-viewer-label" },
        h("strong", null, "3D 实体视图"),
        h("span", null, "实体几何 / 状态 → Three.js")
      ),
      h("div", { ref: hostRef, className: "bn-three-host" }),
      error ? h("div", { className: "bn-error" }, `Three.js: ${error}`) : null
    );
  }

  return {
    "react.Page": Page,
    "react.Panel": Panel,
    "react.Card": Card,
    "react.Button": Button,
    "react.Divider": Divider,
    "react.Control": Control,
    "react.Person": Person,
    "react.Status": Status,
    "react.Decoration": Decoration,
    "react.Indicator": Indicator,
    "three.Viewer": ThreeViewer,
  };
}

function createReactApp(React, registry, ui, dataContext, meta) {
  const h = React.createElement;
  const byId = new Map((ui.entities || []).map(entity => [entity.id, entity]));
  const children = new Map();
  for (const relation of ui.relations || []) {
    if (relation.type !== "contains") continue;
    if (!children.has(relation.from)) children.set(relation.from, []);
    children.get(relation.from).push(relation.to);
  }
  const rootEntity = byId.get(ui.root_id) || null;

  function renderEntity(entity, key = entity.id) {
    const componentKey = projection(entity);
    const Component = registry[componentKey] || registry["react.Card"];
    const childIds = children.get(entity.id) || [];
    const childNodes = childIds.map(id => byId.get(id)).filter(Boolean).map(child => renderEntity(child));
    const content = h(Component, { entity, ui, dataContext, meta }, childNodes.length ? childNodes : undefined);
    const position2D = uiPositionVector2(entity, ui);
    if (!position2D) return h(React.Fragment, { key }, content);
    // 二维位置矢量以像素作为 UI 平面单位，并相对正常布局位置偏移。
    return h("div", {
      key,
      className: "bn-position-vector-2d",
      style: { position: "relative", left: `${position2D.x}px`, top: `${position2D.y}px` },
    }, content);
  }

  function Region({ name }) {
    const entities = (ui.entities || []).filter(entity => entity.id !== ui.root_id && (entity.region || "auto") === name);
    // 页面实体上的“布局规则”控制各区域内的网站控件排列。
    // 非页面容器如果未来拥有显式 contains 关系，则由 Panel/Card 的 child layout 使用同一规则。
    const layoutStyle = rootEntity ? controlLayoutStyle(rootEntity, ui) : {};
    return h("div", { className: `bn-region bn-region-${name}`, style: layoutStyle }, entities.map(entity => renderEntity(entity)));
  }

  function App() {
    if (!(ui.entities || []).length) {
      return h("div", { className: "bn-empty-ui" },
        h("div", { className: "bn-empty-ui-card" },
          h("strong", null, "UI 数据为空"),
          h("p", null, "当前 BlueNode/ui 没有收到“网站”实体，所以页面不会生成组件。"),
          h("div", { className: "bn-empty-steps" },
            h("span", null, "1. 运行 UI 网页输出节点"),
            h("span", null, "2. 确认实体种类 = 网站"),
            h("span", null, "3. UI 输出前缀 = BlueNode/ui")
          )
        )
      );
    }
    const layoutParams = globalRuleParams(ui, "layout.controls");
    const hasLayoutRule = Object.keys(layoutParams).length > 0;

    let shell;
    if (hasLayoutRule) {
      // RulePack 顶层出现布局规则时，由 JS 直接接管网站控件布局。
      // Entity 仍然只是 Entity；这里不把布局规则写回实体。
      const rootChildIds = rootEntity ? (children.get(rootEntity.id) || []) : [];
      const layoutEntities = rootChildIds.length
        ? rootChildIds.map(id => byId.get(id)).filter(Boolean)
        : (ui.entities || []).filter(entity => entity.id !== ui.root_id);
      const total = layoutEntities.length;
      const layoutNodes = layoutEntities.map((entity, index) => h(
        "div",
        {
          key: entity.id,
          className: `bn-layout-item bn-layout-item-${String(layoutParams.mode || "column")}`,
          style: websiteLayoutItemStyle(layoutParams, index, total),
        },
        renderEntity(entity, `${entity.id}:layout`)
      ));
      shell = h(
        "div",
        {
          className: `bn-shell bn-shell-rule bn-shell-${String(layoutParams.mode || "column")}`,
          style: websiteLayoutStyle(layoutParams),
          "data-bn-layout": String(layoutParams.mode || "column"),
        },
        layoutNodes
      );
    } else {
      // 没有布局规则时保留原来的默认网站布局，保证旧工作流可继续运行。
      const pageChildren = ["top", "left", "center", "right", "bottom", "auto", "overlay"]
        .map(name => h(Region, { key: name, name }));
      shell = h("div", { className: "bn-shell" }, pageChildren);
    }

    if (rootEntity) {
      const PageComponent = registry[projection(rootEntity)] || registry["react.Page"];
      return h(PageComponent, { entity: rootEntity, ui, dataContext, meta }, shell);
    }
    return shell;
  }

  return h(App);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderRuntimeError(error) {
  rootElement.innerHTML = `<div class="bn-waiting">React Runtime 无法加载：${escapeHtml(error?.message || error)}</div>`;
}

async function renderCurrent() {
  const { ui, dataContext, meta } = appState;
  if (!ui || !dataContext) return;
  try {
    const runtime = await loadReact();
    const registry = createRegistry(runtime.React);
    if (!runtime.root) runtime.root = runtime.createRoot(rootElement);
    runtime.root.render(createReactApp(runtime.React, registry, ui, dataContext, meta));
  } catch (error) {
    renderRuntimeError(error);
  }
}

async function refresh() {
  if (refreshBusy) return;
  refreshBusy = true;
  try {
    const [uiPayload, dataPayload] = await Promise.all([
      fetchStream(uiStream),
      fetchStream(dataStream),
    ]);

    const ui = uiPayload.ui_model;
    const dataContext = dataPayload.data_context;
    const signature = stableSignature([
      uiPayload.updated_at,
      dataPayload.updated_at,
      ui?.meta,
      dataContext?.meta,
      dataContext?.entities,
      dataContext?.rules,
      ui?.entities,
      ui?.rules,
    ]);

    if (signature !== lastSignature) {
      lastSignature = signature;
      appState.ui = ui;
      appState.dataContext = dataContext;
      appState.meta = {
        uiStream,
        dataStream,
        uiUpdatedAt: uiPayload.updated_at,
        dataUpdatedAt: dataPayload.updated_at,
        plugins: pluginManifest || { react: true, three: true },
      };
      document.title = uiPayload.title || dataPayload.title || "BlueNode UI Runtime";
      await renderCurrent();
    }
  } catch (error) {
    if (!appState.ui) {
      rootElement.innerHTML = `<div class="bn-waiting">等待 UI/Data 工作流输出…<div class="bn-meta">${escapeHtml(error?.message || error)}</div></div>`;
    }
  } finally {
    refreshBusy = false;
  }
}

if (debugEnabled) {
  const status = document.createElement("div");
  status.className = "bn-runtime-status";
  const enabled = pluginManifest
    ? Object.entries(pluginManifest).filter(([, value]) => value).map(([name]) => name).join(" + ")
    : "react + three (dev shell)";
  status.textContent = `UI ${uiStream} · DATA ${dataStream} · ${enabled}`;
  document.body.appendChild(status);
}

window.BlueNodeRuntime = {
  refresh,
  getState: () => ({ ...appState }),
  streams: { ui: uiStream, data: dataStream },
  plugins: pluginManifest,
};

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
