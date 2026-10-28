import Phaser from "phaser";
import type { ActionType, AssetPack, CanonicalEvent, EpistemicFlow, EpistemicFlowKind, FlowType, InteriorActivity, ReplayV2, RuntimePreferences, SelectionDetail, TruthStatus, VisualAction, VisualFlow, WorldEntity, WorldPoint } from "./types";

const WORLD_WIDTH = 480;
const WORLD_HEIGHT = 270;
const FLOW_COLORS: Record<FlowType, number> = {
  data: 0x2dd4ff,
  paper: 0xeee9d8,
  review: 0xf653d8,
  funding: 0x39f5c8,
  citation: 0xa86bff,
  policy: 0xff617d,
};
const FLOW_STYLE: Record<FlowType, { width: number; cadence: number; echoes: number }> = {
  data: { width: 2, cadence: 2, echoes: 3 },
  paper: { width: 2, cadence: 4, echoes: 1 },
  review: { width: 2, cadence: 3, echoes: 2 },
  funding: { width: 3, cadence: 5, echoes: 3 },
  citation: { width: 1, cadence: 2, echoes: 2 },
  policy: { width: 2, cadence: 6, echoes: 3 },
};
const EPISTEMIC_COLORS: Record<EpistemicFlowKind, number> = {
  manuscript: 0xeee9d8,
  review: 0xf653d8,
  decision: 0xffc857,
  application: 0x2dd4ff,
  award: 0x39f5c8,
};

interface FlowVisual {
  model: VisualFlow;
  graphics: Phaser.GameObjects.Graphics;
  packets: Phaser.GameObjects.Image[];
  curve: Phaser.Curves.QuadraticBezier;
  label: Phaser.GameObjects.Text;
}

interface EpistemicFlowVisual {
  model: EpistemicFlow;
  graphics: Phaser.GameObjects.Graphics;
  packet: Phaser.GameObjects.Image;
  label: Phaser.GameObjects.Text;
}

interface InteriorActivityVisual {
  model: InteriorActivity;
  label: Phaser.GameObjects.Text;
}

interface ActorHud {
  marker: Phaser.GameObjects.Graphics;
  label: Phaser.GameObjects.Text;
}

export interface ArcologySceneOptions {
  key?: string;
  onSelect?: (detail: SelectionDetail) => void;
  onReady?: () => void;
}

function truthAlpha(status: TruthStatus): number {
  if (status === "canonical") return 0.96;
  if (status === "derived") return 0.82;
  return 0.28;
}

function drawPatternedCurve(
  graphics: Phaser.GameObjects.Graphics,
  curve: Phaser.Curves.QuadraticBezier,
  color: number,
  alpha: number,
  flowType: FlowType,
): void {
  const style = FLOW_STYLE[flowType];
  const points = curve.getPoints(48);
  graphics.lineStyle(style.width, color, alpha);
  for (let i = 1; i < points.length; i += 1) {
    const from = points[i - 1];
    const to = points[i];
    if (!from || !to) continue;
    const draw = flowType === "citation" ? i % 2 === 0 : i % style.cadence !== 0;
    if (draw) graphics.lineBetween(Math.round(from.x), Math.round(from.y), Math.round(to.x), Math.round(to.y));
  }
  for (const progress of [0.25, 0.5, 0.75]) {
    const point = curve.getPoint(progress);
    const x = Math.round(point.x);
    const y = Math.round(point.y);
    if (flowType === "data") graphics.fillStyle(color, alpha).fillRect(x - 2, y - 1, 4, 2);
    if (flowType === "paper") graphics.fillStyle(color, alpha).fillRect(x - 1, y - 2, 3, 3);
    if (flowType === "review") graphics.lineStyle(1, color, alpha).strokeRect(x - 2, y - 2, 4, 4);
    if (flowType === "funding") graphics.fillStyle(color, alpha).fillRect(x - 2, y - 2, 4, 4);
    if (flowType === "citation") graphics.fillStyle(color, alpha).fillRect(x - 1, y - 1, 2, 2);
    if (flowType === "policy") {
      graphics.lineStyle(1, color, alpha).strokeRect(x - 3, y - 3, 6, 6);
      graphics.lineBetween(x + 4, y - 2, x + 5, y - 3);
    }
  }
}

function actionFrame(action: ActionType | undefined, cursorMs: number, reducedMotion: boolean): number {
  const phase = reducedMotion ? 0 : Math.floor(cursorMs / (action === "move" ? 180 : 320)) % 2;
  if (action === "move") return 2 + phase;
  if (action) return 4 + phase;
  return reducedMotion ? 0 : Math.floor(cursorMs / 880) % 2;
}

function actionColor(action: ActionType): number {
  if (action === "move") return 0x9ea8c2;
  if (["write", "revise", "publish"].includes(action)) return 0xffc857;
  if (action === "review") return 0xf653d8;
  if (["allocate", "receive"].includes(action)) return 0x39f5c8;
  if (action === "apply") return 0x2dd4ff;
  if (["cite", "read"].includes(action)) return 0xa86bff;
  if (action === "policy") return 0xff617d;
  return 0x2dd4ff;
}

function lerpPoint(start: WorldPoint, end: WorldPoint, progress: number): WorldPoint {
  return {
    x: Math.round(Phaser.Math.Linear(start.x, end.x, progress)),
    y: Math.round(Phaser.Math.Linear(start.y, end.y, progress)),
  };
}

export function pointOnPath(path: WorldPoint[], progress: number): WorldPoint {
  if (path.length < 2) throw new Error("A cinematic path requires at least two points");
  const lengths = path.slice(1).map((point, index) => Math.abs(point.x - path[index]!.x) + Math.abs(point.y - path[index]!.y));
  const total = Math.max(1, lengths.reduce((sum, length) => sum + length, 0));
  let distance = Phaser.Math.Clamp(progress, 0, 1) * total;
  for (let index = 0; index < lengths.length; index += 1) {
    const length = lengths[index]!;
    if (distance <= length || index === lengths.length - 1) {
      return lerpPoint(path[index]!, path[index + 1]!, length === 0 ? 1 : distance / length);
    }
    distance -= length;
  }
  return path.at(-1)!;
}

export class ArcologyScene extends Phaser.Scene {
  readonly replay: ReplayV2;
  readonly assetPack: AssetPack;
  private readonly entities = new Map<string, WorldEntity>();
  private readonly sprites = new Map<string, Phaser.GameObjects.Image>();
  private readonly actionsByActor = new Map<string, VisualAction[]>();
  private readonly currentActions = new Map<string, VisualAction>();
  private readonly actorHuds = new Map<string, ActorHud>();
  private readonly flowVisuals: FlowVisual[] = [];
  private readonly epistemicFlowVisuals: EpistemicFlowVisual[] = [];
  private readonly interiorActivityVisuals: InteriorActivityVisual[] = [];
  private readonly layerVisibility = new Map<FlowType, boolean>();
  private readonly epistemicVisibility = new Map<EpistemicFlowKind, boolean>();
  private cursorMs = 0;
  private followTargetId?: string;
  private followEnabled = false;
  private preferences: RuntimePreferences = { reducedMotion: false, highContrast: false, atmosphere: 0.62 };
  private dragging = false;
  private dragStart?: Phaser.Math.Vector2;
  private minimap?: Phaser.Cameras.Scene2D.Camera;
  private keyMap?: Record<string, Phaser.Input.Keyboard.Key>;
  private rainGraphics?: Phaser.GameObjects.Graphics;
  private interiorGraphics?: Phaser.GameObjects.Graphics;
  private interiorAmbientGraphics?: Phaser.GameObjects.Graphics;
  private stateGraphics?: Phaser.GameObjects.Graphics;
  private activityGraphics?: Phaser.GameObjects.Graphics;
  private interiorsVisible = true;
  private interiorAmbientVisible = true;
  private readonly onSelect: (detail: SelectionDetail) => void;
  private readonly onReady: () => void;

  constructor(replay: ReplayV2, assetPack: AssetPack, options: ArcologySceneOptions = {}) {
    super({ key: options.key ?? "ArcologyScene" });
    this.replay = replay;
    this.assetPack = assetPack;
    this.onSelect = options.onSelect ?? ((detail) => window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail })));
    this.onReady = options.onReady ?? (() => window.dispatchEvent(new CustomEvent("noctiluca:renderer-ready")));
    for (const flowType of Object.keys(FLOW_COLORS) as FlowType[]) this.layerVisibility.set(flowType, true);
    for (const flowKind of Object.keys(EPISTEMIC_COLORS) as EpistemicFlowKind[]) this.epistemicVisibility.set(flowKind, true);
    for (const action of replay.choreography.actions) {
      const rows = this.actionsByActor.get(action.actor_entity_id) ?? [];
      rows.push(action);
      this.actionsByActor.set(action.actor_entity_id, rows);
    }
    for (const rows of this.actionsByActor.values()) rows.sort((a, b) => a.logical_timestamp_ms - b.logical_timestamp_ms);
  }

  preload(): void {
    this.load.setPath("");
    for (const image of this.assetPack.images) {
      if (image.frames) {
        this.load.spritesheet(image.key, image.url, {
          frameWidth: image.frames.frameWidth,
          frameHeight: image.frames.frameHeight,
          endFrame: image.frames.end,
        });
      } else {
        this.load.image(image.key, image.url);
      }
    }
  }

  create(): void {
    this.cameras.main.setBounds(0, 0, WORLD_WIDTH, WORLD_HEIGHT).setRoundPixels(true).setBackgroundColor("#070814");
    this.physics.world.setBounds(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
    this.drawWorldGround();

    const groups = this.replay.canonical.entities;
    const allEntities = [...groups.institutions, ...groups.artifacts, ...groups.researchers, ...this.replay.choreography.workflow_nodes, ...this.replay.choreography.workstations, ...this.replay.ambient.actors];
    for (const entity of allEntities) {
      this.entities.set(entity.id, entity);
      this.createEntity(entity);
    }
    this.createActorHuds();
    for (const flow of this.replay.choreography.flows) this.createFlow(flow);
    for (const flow of this.replay.choreography.epistemic_flows) this.createEpistemicFlow(flow);
    for (const activity of this.replay.choreography.interior_activities) this.createInteriorActivity(activity);
    this.activityGraphics = this.add.graphics().setDepth(10);
    this.interiorGraphics = this.add.graphics().setDepth(8);
    this.interiorAmbientGraphics = this.add.graphics().setDepth(6);
    this.rainGraphics = this.add.graphics().setDepth(15);
    this.stateGraphics = this.add.graphics().setDepth(7);
    this.stateGraphics.setInteractive(
      new Phaser.Geom.Rectangle(0, 0, WORLD_WIDTH, WORLD_HEIGHT),
      (_shape: Phaser.Geom.Rectangle, x: number, y: number) => this.stateMarkerAt(x, y) !== undefined,
    );
    this.stateGraphics.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      const event = this.stateMarkerAt(pointer.worldX, pointer.worldY);
      if (event) this.onSelect({ id: event.id, category: "event" });
    });

    this.minimap = this.cameras.add(368, 8, 104, 62, false, "minimap");
    this.minimap.setBounds(0, 0, WORLD_WIDTH, WORLD_HEIGHT).setZoom(0.216).centerOn(WORLD_WIDTH / 2, WORLD_HEIGHT / 2).setRoundPixels(true);
    this.minimap.setBackgroundColor("rgba(7,8,20,0.9)");
    this.minimap.ignore([...this.actorHuds.values()].flatMap((hud) => [hud.marker, hud.label]));

    this.installPointerControls();
    this.installKeyboardControls();
    this.cameras.main.centerOn(WORLD_WIDTH / 2, WORLD_HEIGHT / 2);
    this.renderFrame();
    this.onReady();
  }

  update(_time: number, delta: number): void {
    this.updateKeyboardPan(delta);
    this.renderFrame();
    this.updateFollowCamera();
  }

  setCursor(milliseconds: number): void {
    this.cursorMs = Math.max(0, Math.min(milliseconds, this.replay.choreography.duration_ms));
    this.renderFrame();
  }

  setLayerVisible(flowType: FlowType, visible: boolean): void {
    this.layerVisibility.set(flowType, visible);
    this.renderFlows();
  }

  setEpistemicVisible(flowKind: EpistemicFlowKind, visible: boolean): void {
    this.epistemicVisibility.set(flowKind, visible);
    this.renderEpistemicFlows();
  }

  setInteriorsVisible(visible: boolean): void {
    this.interiorsVisible = visible;
    for (const station of this.replay.choreography.workstations) this.sprites.get(station.id)?.setVisible(visible);
    this.renderInteriorActivities();
  }

  setInteriorAmbientVisible(visible: boolean): void {
    this.interiorAmbientVisible = visible;
    this.renderInteriorAmbient();
  }

  select(id: string): void {
    const action = this.replay.choreography.actions.find((row) => row.id === id);
    const flow = this.replay.choreography.flows.find((row) => row.id === id);
    const epistemic = this.replay.choreography.epistemic_flows.find((row) => row.id === id);
    const interior = this.replay.choreography.interior_activities.find((row) => row.id === id);
    const event = this.replay.canonical.events.find((row) => row.id === id);
    const researcherIds = new Set(this.replay.canonical.entities.researchers.map((row) => row.id));
    this.followTargetId = action?.actor_entity_id
      ?? [flow?.from_entity_id, flow?.to_entity_id].find((candidate) => candidate && researcherIds.has(candidate))
      ?? [epistemic?.from_entity_id, epistemic?.to_entity_id].find((candidate) => candidate && researcherIds.has(candidate))
      ?? (interior && researcherIds.has(interior.actor_entity_id) ? interior.actor_entity_id : undefined)
      ?? event?.actor_ids.find((candidate) => researcherIds.has(candidate))
      ?? (researcherIds.has(id) ? id : undefined);
    const sprite = this.sprites.get(this.followTargetId ?? id);
    if (sprite && this.followEnabled) this.cameras.main.centerOn(Math.round(sprite.x), Math.round(sprite.y));
  }

  setFollow(enabled: boolean): void {
    this.followEnabled = enabled;
    if (enabled) this.updateFollowCamera();
  }

  setPreferences(preferences: RuntimePreferences): void {
    this.preferences = preferences;
    const atmosphere = Phaser.Math.Clamp(preferences.atmosphere, 0, 1);
    this.cameras.main.setBackgroundColor(preferences.highContrast ? "#000000" : "#070814");
    for (const flowVisual of this.flowVisuals) flowVisual.graphics.setAlpha(preferences.highContrast ? 1 : 0.72 + atmosphere * 0.28);
    this.renderFrame();
  }

  zoomBy(direction: 1 | -1): void {
    const current = Math.round(this.cameras.main.zoom);
    this.cameras.main.setZoom(Phaser.Math.Clamp(current + direction, 1, 3)).setRoundPixels(true);
  }

  private renderFrame(): void {
    if (!this.sys.isActive()) return;
    this.renderActions();
    this.renderActivityEffects();
    this.renderFlows();
    this.renderEpistemicFlows();
    this.renderInteriorActivities();
    this.renderInteriorAmbient();
    this.renderAmbient();
    this.renderInstitutionStates();
  }

  private updateFollowCamera(): void {
    if (!this.followEnabled) return;
    const cue = this.replay.choreography.camera_cues.find((row) =>
      this.cursorMs >= row.logical_timestamp_ms
      && this.cursorMs <= row.logical_timestamp_ms + row.duration_ms
      && (!this.followTargetId || row.target_entity_id === this.followTargetId));
    const targetId = this.followTargetId ?? cue?.target_entity_id;
    const sprite = targetId ? this.sprites.get(targetId) : undefined;
    if (!sprite) return;
    if (cue?.zoom) this.cameras.main.setZoom(Math.round(cue.zoom)).setRoundPixels(true);
    this.cameras.main.centerOn(Math.round(sprite.x), Math.round(sprite.y));
  }

  private drawWorldGround(): void {
    const graphics = this.add.graphics().setDepth(-20);
    graphics.fillStyle(0x070814, 1).fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
    graphics.fillStyle(0x10142a, 1).fillRect(0, 18, WORLD_WIDTH, 60);
    graphics.fillStyle(0x1a2140, 1);
    for (let x = 0; x < WORLD_WIDTH; x += 24) {
      const height = 10 + (x * 7 % 28);
      graphics.fillRect(x, 78 - height, 18, height);
      if (x % 48 === 0) graphics.fillRect(x + 7, 48 - height / 2, 3, 10);
    }
    graphics.fillStyle(0x2a3560, 0.9);
    for (let x = 6; x < WORLD_WIDTH; x += 31) graphics.fillRect(x, 64 - (x % 3) * 5, 2, 3);
    graphics.fillStyle(0x2dd4ff, 0.6);
    for (let x = 15; x < WORLD_WIDTH; x += 47) graphics.fillRect(x, 54 + x % 13, 2, 1);
    graphics.fillStyle(0xf653d8, 0.5);
    for (let x = 38; x < WORLD_WIDTH; x += 83) graphics.fillRect(x, 45 + x % 19, 1, 3);

    graphics.fillStyle(0x0b0e20, 1).fillRect(0, 78, WORLD_WIDTH, 192);
    graphics.lineStyle(1, 0x1a2140, 0.65);
    for (let x = 0; x <= WORLD_WIDTH; x += 16) graphics.lineBetween(x, 78, x, WORLD_HEIGHT);
    for (let y = 78; y <= WORLD_HEIGHT; y += 16) graphics.lineBetween(0, y, WORLD_WIDTH, y);
    graphics.lineStyle(2, 0x2a3560, 0.72);
    graphics.lineBetween(0, 188, WORLD_WIDTH, 188);
    graphics.lineBetween(208, 78, 208, WORLD_HEIGHT);

    this.drawDistrictPlatform(graphics, 68, 107, 112, 65, 0x2dd4ff);
    this.drawDistrictPlatform(graphics, 280, 92, 112, 72, 0xf653d8);
    this.drawDistrictPlatform(graphics, 196, 196, 112, 66, 0x39f5c8);
    this.drawDistrictPlatform(graphics, 366, 188, 108, 74, 0xffc857);

    graphics.lineStyle(3, 0x10142a, 1);
    graphics.lineBetween(176, 143, 281, 132);
    graphics.lineBetween(288, 166, 274, 196);
    graphics.lineBetween(195, 191, 159, 165);
    graphics.lineBetween(307, 222, 367, 222);
    graphics.lineBetween(390, 187, 365, 157);
    graphics.lineStyle(1, 0x46527a, 0.75);
    graphics.lineBetween(176, 141, 281, 130);
    graphics.lineBetween(290, 165, 276, 198);
    graphics.lineBetween(194, 189, 159, 163);
    graphics.lineBetween(307, 220, 367, 220);
    graphics.lineBetween(392, 187, 367, 155);
    graphics.fillStyle(0xffc857, 0.85);
    const conduitLights: Array<[number, number]> = [[182, 139], [210, 136], [238, 133], [266, 130], [287, 172], [282, 185], [185, 182], [174, 173], [320, 218], [344, 218], [378, 174], [387, 184]];
    for (const [x, y] of conduitLights) graphics.fillRect(x, y, 2, 2);

    this.add.text(72, 93, "LAB//01", { fontFamily: "monospace", fontSize: "5px", color: "#2dd4ff" }).setDepth(-5);
    this.add.text(285, 78, "REVIEW//EXCHANGE", { fontFamily: "monospace", fontSize: "5px", color: "#f653d8" }).setDepth(-5);
    this.add.text(201, 182, "CIVIC//LEDGER", { fontFamily: "monospace", fontSize: "5px", color: "#39f5c8" }).setDepth(-5);
    this.add.text(371, 174, "PUBLICATION//SPINE", { fontFamily: "monospace", fontSize: "5px", color: "#ffc857" }).setDepth(-5);
    this.add.text(8, 82, "AMBIENT INFRA // NON-SCIENTIFIC", { fontFamily: "monospace", fontSize: "4px", color: "#6a769a" }).setDepth(-5);
  }

  private drawDistrictPlatform(graphics: Phaser.GameObjects.Graphics, x: number, y: number, width: number, height: number, accent: number): void {
    graphics.fillStyle(0x10142a, 1).fillRect(x, y, width, height);
    graphics.fillStyle(0x1a2140, 1).fillRect(x + 4, y + 4, width - 8, height - 8);
    graphics.lineStyle(1, accent, 0.58).strokeRect(x + 1, y + 1, width - 2, height - 2);
    graphics.fillStyle(accent, 0.8);
    graphics.fillRect(x, y, 7, 2).fillRect(x + width - 7, y, 7, 2);
    graphics.fillRect(x, y + height - 2, 7, 2).fillRect(x + width - 7, y + height - 2, 7, 2);
    graphics.fillStyle(0x46527a, 0.7);
    for (let dx = x + 8; dx < x + width - 6; dx += 12) graphics.fillRect(dx, y + height - 5, 6, 1);
  }

  private createEntity(entity: WorldEntity): void {
    if (!this.textures.exists(entity.asset_key)) {
      if (entity.entity_type === "ambient_actor") return;
      window.dispatchEvent(new CustomEvent("noctiluca:asset-missing", { detail: { key: entity.asset_key, entityId: entity.id } }));
      return;
    }
    const asset = this.assetPack.images.find((image) => image.key === entity.asset_key);
    const sprite: Phaser.GameObjects.Image = asset?.frames
      ? this.add.sprite(Math.round(entity.x), Math.round(entity.y), entity.asset_key, 0)
      : this.add.image(Math.round(entity.x), Math.round(entity.y), entity.asset_key);
    const depth = entity.entity_type === "institution" ? 2 : entity.entity_type === "workstation" ? 5 : entity.entity_type === "workflow_node" ? 6 : entity.entity_type === "ambient_actor" ? 6 : 9;
    sprite.setOrigin(0.5, 1).setDepth(depth);
    if (asset) sprite.setDisplaySize(Math.round(asset.width), Math.round(asset.height));
    sprite.setInteractive({ useHandCursor: true });
    sprite.on("pointerdown", () => {
      const action = this.currentActions.get(entity.id);
      this.onSelect({ id: action?.id ?? entity.id, category: action ? "action" : "entity" });
    });
    sprite.setData("truth_status", entity.truth_status);
    this.sprites.set(entity.id, sprite);
  }

  private createActorHuds(): void {
    for (const researcher of this.replay.canonical.entities.researchers) {
      const marker = this.add.graphics().setDepth(11);
      const label = this.add.text(researcher.x, researcher.y - 38, "", {
        fontFamily: "monospace",
        fontSize: "5px",
        color: "#2dd4ff",
        backgroundColor: "#070814",
        padding: { x: 2, y: 1 },
      }).setOrigin(0.5, 1).setDepth(12).setVisible(false).setInteractive({ useHandCursor: true });
      label.on("pointerdown", () => {
        const action = this.currentActions.get(researcher.id);
        if (action) this.onSelect({ id: action.id, category: "action" });
      });
      this.actorHuds.set(researcher.id, { marker, label });
    }
  }

  private renderActions(): void {
    for (const researcher of this.replay.canonical.entities.researchers) {
      const sprite = this.sprites.get(researcher.id);
      const hud = this.actorHuds.get(researcher.id);
      if (!sprite || !hud) continue;
      const rows = this.actionsByActor.get(researcher.id) ?? [];
      const active = rows.find((action) => this.cursorMs >= action.logical_timestamp_ms && this.cursorMs <= action.logical_timestamp_ms + action.duration_ms);
      const completed = rows.filter((action) => this.cursorMs > action.logical_timestamp_ms + action.duration_ms).at(-1);
      const progress = active ? Phaser.Math.Clamp((this.cursorMs - active.logical_timestamp_ms) / Math.max(1, active.duration_ms), 0, 1) : 1;
      const position = active ? pointOnPath(active.path, progress) : completed?.end ?? { x: researcher.x, y: researcher.y };
      sprite.setPosition(position.x, position.y).setDepth(9 + position.y / 1000);
      if (sprite instanceof Phaser.GameObjects.Sprite) sprite.setFrame(actionFrame(active?.action_type, this.cursorMs, this.preferences.reducedMotion));
      hud.marker.clear();
      hud.label.setVisible(Boolean(active));
      if (active) {
        this.currentActions.set(researcher.id, active);
        const color = actionColor(active.action_type);
        hud.marker.lineStyle(1, color, 0.9);
        hud.marker.strokeRect(position.x - 14, position.y - 34, 28, 36);
        hud.marker.fillStyle(color, 0.9).fillRect(position.x - 14, position.y - 34, 4, 1).fillRect(position.x + 10, position.y - 34, 4, 1);
        hud.label.setText(`◇ ${active.action_type.toUpperCase()} // DERIVED`).setPosition(position.x, position.y - 36);
      } else {
        this.currentActions.delete(researcher.id);
      }
    }
  }

  private renderActivityEffects(): void {
    if (!this.activityGraphics) return;
    const graphics = this.activityGraphics;
    graphics.clear();
    for (const [actorId, action] of this.currentActions) {
      const sprite = this.sprites.get(actorId);
      if (!sprite) continue;
      const x = Math.round(sprite.x);
      const y = Math.round(sprite.y);
      const localTime = Math.max(0, this.cursorMs - action.logical_timestamp_ms);
      const phase = this.preferences.reducedMotion ? 0 : Math.floor(localTime / 220) % 3;
      if (action.action_type === "move") {
        graphics.fillStyle(0x9ea8c2, 0.58);
        graphics.fillRect(x - 7 - phase * 2, y - 1, 2, 1);
        graphics.fillRect(x - 12 - phase * 2, y + 1, 2, 1);
      } else if (action.action_type === "experiment") {
        graphics.lineStyle(1, 0x2dd4ff, 0.95).strokeRect(x - 14, y - 23, 8, 11);
        graphics.fillStyle(phase === 1 ? 0xb7f34a : 0x39f5c8, 0.9).fillRect(x - 12, y - 18 - phase, 4, 4 + phase);
        graphics.lineStyle(1, 0x2dd4ff, 0.75).lineBetween(x - 6, y - 20, x + 5, y - 25 + phase);
      } else if (["write", "revise", "review", "publish"].includes(action.action_type)) {
        const accent = action.action_type === "review" ? 0xf653d8 : action.action_type === "publish" ? 0xffc857 : 0xeee9d8;
        graphics.fillStyle(0x10142a, 0.96).fillRect(x + 7, y - 23, 11, 10);
        graphics.lineStyle(1, accent, 0.92).strokeRect(x + 7, y - 23, 11, 10);
        for (let row = 0; row < 3; row += 1) graphics.fillStyle(accent, row === phase ? 1 : 0.42).fillRect(x + 9, y - 21 + row * 3, 6 + (row % 2), 1);
        if (action.action_type === "publish") {
          graphics.fillStyle(0xeee9d8, 0.9).fillRect(x - 14, y - 21, 5, 7).fillRect(x - 12, y - 24, 5, 7);
          graphics.fillStyle(0x4f7cff, 0.85).fillRect(x - 11, y - 22, 3, 1);
        }
      } else if (action.action_type === "apply") {
        graphics.fillStyle(0x10142a, 0.96).fillRect(x + 7, y - 25, 12, 13);
        graphics.lineStyle(1, 0x2dd4ff, 0.94).strokeRect(x + 7, y - 25, 12, 13);
        for (let row = 0; row < 3; row += 1) {
          graphics.fillStyle(row === phase ? 0x39f5c8 : 0x4f7cff, row === phase ? 1 : 0.58).fillRect(x + 9, y - 22 + row * 3, 2, 2);
          graphics.fillStyle(0xeee9d8, 0.78).fillRect(x + 13, y - 21 + row * 3, 4, 1);
        }
      } else if (["allocate", "receive"].includes(action.action_type)) {
        graphics.lineStyle(1, 0x39f5c8, 0.92).strokeRect(x - 15, y - 24, 10, 12);
        for (let column = 0; column < 3; column += 1) {
          const height = 3 + ((column + phase) % 3) * 2;
          graphics.fillStyle(0x39f5c8, 0.86).fillRect(x - 13 + column * 3, y - 14 - height, 2, height);
        }
      } else if (["cite", "read"].includes(action.action_type)) {
        graphics.lineStyle(1, 0xa86bff, 0.9);
        graphics.strokeRect(x - 15 - phase, y - 25 - phase, 7 + phase * 2, 10 + phase * 2);
        graphics.fillStyle(0xa86bff, 0.9).fillRect(x - 11, y - 21, 2, 2);
      } else if (action.action_type === "policy") {
        graphics.lineStyle(1, 0xff617d, 0.9);
        for (let ring = 0; ring < 3; ring += 1) {
          const size = 7 + ring * 5 + phase * 2;
          graphics.strokeRect(x - Math.floor(size / 2), y - 21 - Math.floor(size / 2), size, size);
        }
      }
    }
  }

  private createFlow(flow: VisualFlow): void {
    const from = this.entities.get(flow.from_entity_id);
    const to = this.entities.get(flow.to_entity_id);
    if (!from || !to) return;
    const flowIndex = this.replay.choreography.flows.indexOf(flow);
    const arcBias = flowIndex % 2 === 0 ? -1 : 1;
    const midpoint = new Phaser.Math.Vector2(
      Math.round((from.x + to.x) / 2 + arcBias * (8 + flowIndex * 2)),
      Math.round((from.y + to.y) / 2 - Math.min(72, Math.abs(from.x - to.x) * 0.2 + 22 + flowIndex * 2)),
    );
    const curve = new Phaser.Curves.QuadraticBezier(
      new Phaser.Math.Vector2(Math.round(from.x), Math.round(from.y - 22)),
      midpoint,
      new Phaser.Math.Vector2(Math.round(to.x), Math.round(to.y - 22)),
    );
    const graphics = this.add.graphics().setDepth(5).setInteractive(
      new Phaser.Geom.Rectangle(Math.min(from.x, to.x) - 16, Math.min(from.y, to.y) - 96, Math.abs(to.x - from.x) + 32 || 48, Math.abs(to.y - from.y) + 120),
      Phaser.Geom.Rectangle.Contains,
    );
    graphics.on("pointerdown", () => this.onSelect({ id: flow.id, category: "flow" }));
    const packetKey = `flow_${flow.flow_type}`;
    const packetAsset = this.assetPack.images.find((image) => image.key === packetKey);
    const packets: Phaser.GameObjects.Image[] = [];
    if (this.textures.exists(packetKey) && packetAsset) {
      for (let i = 0; i < FLOW_STYLE[flow.flow_type].echoes; i += 1) {
        const packet = this.add.image(from.x, from.y, packetKey).setDepth(13 - i * 0.1).setDisplaySize(packetAsset.width, packetAsset.height).setInteractive({ useHandCursor: true });
        packet.setAlpha(i === 0 ? 1 : 0.54 - i * 0.12);
        packet.on("pointerdown", () => this.onSelect({ id: flow.id, category: "flow" }));
        packets.push(packet);
      }
    } else {
      window.dispatchEvent(new CustomEvent("noctiluca:asset-missing", { detail: { key: packetKey, entityId: flow.id } }));
    }
    const label = this.add.text(from.x, from.y, "", {
      fontFamily: "monospace",
      fontSize: "5px",
      color: `#${FLOW_COLORS[flow.flow_type].toString(16).padStart(6, "0")}`,
      backgroundColor: "#070814",
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 1).setDepth(14).setVisible(false).setInteractive({ useHandCursor: true });
    label.on("pointerdown", () => this.onSelect({ id: flow.id, category: "flow" }));
    this.flowVisuals.push({ model: flow, graphics, packets, curve, label });
  }

  private renderFlows(): void {
    for (const visual of this.flowVisuals) {
      const { model, graphics, packets, curve, label } = visual;
      graphics.clear();
      const layerVisible = this.layerVisibility.get(model.flow_type) !== false;
      const elapsed = this.cursorMs - model.logical_timestamp_ms;
      const active = elapsed >= 0 && elapsed <= model.duration_ms;
      const residual = elapsed > model.duration_ms && elapsed <= model.duration_ms + 1_800;
      const visible = layerVisible && (active || residual);
      graphics.setVisible(visible);
      label.setVisible(visible && active);
      for (const packet of packets) packet.setVisible(visible && active);
      if (!visible) continue;
      const color = FLOW_COLORS[model.flow_type];
      const residualAlpha = residual ? 1 - (elapsed - model.duration_ms) / 1_800 : 1;
      drawPatternedCurve(graphics, curve, color, truthAlpha(model.truth_status) * residualAlpha, model.flow_type);
      const target = curve.getPoint(1);
      graphics.lineStyle(1, color, 0.9 * residualAlpha).strokeRect(Math.round(target.x) - 5, Math.round(target.y) - 5, 10, 10);
      if (model.flow_type === "policy" && active) {
        graphics.strokeRect(Math.round(target.x) - 9, Math.round(target.y) - 9, 18, 18);
        graphics.strokeRect(Math.round(target.x) - 13, Math.round(target.y) - 13, 26, 26);
      }
      if (active) {
        const rawProgress = model.duration_ms === 0 ? 1 : elapsed / model.duration_ms;
        const leadProgress = this.preferences.reducedMotion ? 0.5 : Phaser.Math.Clamp(rawProgress, 0, 1);
        packets.forEach((packet, index) => {
          const progress = this.preferences.reducedMotion && index > 0 ? -1 : leadProgress - index * 0.08;
          packet.setVisible(progress >= 0);
          if (progress >= 0) {
            const point = curve.getPoint(Phaser.Math.Clamp(progress, 0, 1));
            packet.setPosition(Math.round(point.x), Math.round(point.y));
          }
        });
        const labelPoint = curve.getPoint(leadProgress);
        label.setText(`${model.label}\nDERIVED · ${model.derived_from_event_ids.length} EVENT`).setPosition(Math.round(labelPoint.x), Math.round(labelPoint.y - 8));
      }
    }
  }

  private createEpistemicFlow(flow: EpistemicFlow): void {
    const graphics = this.add.graphics().setDepth(7);
    const asset = this.assetPack.images.find((image) => image.key === flow.packet_asset_key);
    if (!asset || !this.textures.exists(flow.packet_asset_key)) {
      window.dispatchEvent(new CustomEvent("noctiluca:asset-missing", { detail: { key: flow.packet_asset_key, entityId: flow.id } }));
    }
    const packet = this.add.image(flow.path[0]!.x, flow.path[0]!.y, flow.packet_asset_key)
      .setDepth(14)
      .setDisplaySize(asset?.width ?? 10, asset?.height ?? 10)
      .setInteractive({ useHandCursor: true });
    packet.on("pointerdown", () => this.onSelect({ id: flow.id, category: "epistemic" }));
    const label = this.add.text(flow.path[0]!.x, flow.path[0]!.y, "", {
      fontFamily: "monospace",
      fontSize: "5px",
      color: `#${EPISTEMIC_COLORS[flow.flow_kind].toString(16).padStart(6, "0")}`,
      backgroundColor: "#070814",
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 1).setDepth(15).setInteractive({ useHandCursor: true });
    label.on("pointerdown", () => this.onSelect({ id: flow.id, category: "epistemic" }));
    this.epistemicFlowVisuals.push({ model: flow, graphics, packet, label });
  }

  private renderEpistemicFlows(): void {
    for (const visual of this.epistemicFlowVisuals) {
      const { model, graphics, packet, label } = visual;
      graphics.clear();
      const elapsed = this.cursorMs - model.logical_timestamp_ms;
      const active = elapsed >= 0 && elapsed <= model.duration_ms;
      const residual = elapsed > model.duration_ms && elapsed <= model.duration_ms + 1_200;
      const visible = this.epistemicVisibility.get(model.flow_kind) !== false && (active || residual);
      graphics.setVisible(visible);
      packet.setVisible(visible && active);
      label.setVisible(visible && active);
      if (!visible) continue;
      const color = EPISTEMIC_COLORS[model.flow_kind];
      const alpha = (residual ? 1 - (elapsed - model.duration_ms) / 1_200 : 1) * 0.92;
      graphics.lineStyle(model.flow_kind === "award" ? 3 : 2, color, alpha);
      for (let index = 1; index < model.path.length; index += 1) {
        const from = model.path[index - 1]!;
        const to = model.path[index]!;
        graphics.lineBetween(from.x, from.y, to.x, to.y);
        graphics.fillStyle(color, alpha).fillRect(from.x - 1, from.y - 1, 3, 3);
      }
      const target = model.path.at(-1)!;
      graphics.lineStyle(1, color, alpha).strokeRect(target.x - 6, target.y - 6, 12, 12);
      graphics.strokeRect(target.x - 9, target.y - 9, 18, 18);
      if (!active) continue;
      const progress = this.preferences.reducedMotion ? 0.58 : Phaser.Math.Clamp(elapsed / Math.max(1, model.duration_ms), 0, 1);
      const position = pointOnPath(model.path, progress);
      packet.setPosition(position.x, position.y);
      label.setText(`${model.flow_kind.toUpperCase()} // ${model.derived_from_event_ids.length} EVENT${model.derived_from_event_ids.length === 1 ? "" : "S"}\nDERIVED ROUTE`).setPosition(position.x, position.y - 9);
    }
  }

  private createInteriorActivity(activity: InteriorActivity): void {
    const station = this.replay.choreography.workstations.find((row) => row.id === activity.workstation_id);
    if (!station) return;
    const label = this.add.text(station.x, station.y - 27, "", {
      fontFamily: "monospace",
      fontSize: "5px",
      color: "#eee9d8",
      backgroundColor: "#070814",
      padding: { x: 2, y: 1 },
    }).setOrigin(0.5, 1).setDepth(16).setVisible(false).setInteractive({ useHandCursor: true });
    label.on("pointerdown", () => this.onSelect({ id: activity.id, category: "interior" }));
    this.interiorActivityVisuals.push({ model: activity, label });
  }

  private renderInteriorActivities(): void {
    if (!this.interiorGraphics) return;
    this.interiorGraphics.clear();
    for (const visual of this.interiorActivityVisuals) {
      const { model, label } = visual;
      const active = this.interiorsVisible && this.cursorMs >= model.logical_timestamp_ms && this.cursorMs <= model.logical_timestamp_ms + model.duration_ms;
      label.setVisible(active);
      if (!active) continue;
      const station = this.entities.get(model.workstation_id);
      if (!station) continue;
      const color = actionColor(model.activity_type);
      const progress = Phaser.Math.Clamp((this.cursorMs - model.logical_timestamp_ms) / Math.max(1, model.duration_ms), 0, 1);
      this.interiorGraphics.lineStyle(1, color, 0.96).strokeRect(station.x - 18, station.y - 27, 36, 29);
      this.interiorGraphics.fillStyle(0x070814, 0.9).fillRect(station.x - 16, station.y + 3, 32, 3);
      this.interiorGraphics.fillStyle(color, 0.94).fillRect(station.x - 16, station.y + 3, Math.round(32 * progress), 3);
      this.interiorGraphics.fillStyle(color, 0.9).fillRect(station.x - 18, station.y - 27, 5, 2).fillRect(station.x + 13, station.y - 27, 5, 2);
      label.setText(`${model.activity_type.toUpperCase()} // ${model.derived_from_event_ids.length} CANONICAL\nINSTITUTION INTERIOR · DERIVED`).setPosition(station.x, station.y - 28);
    }
  }

  private renderInteriorAmbient(): void {
    if (!this.interiorAmbientGraphics) return;
    const graphics = this.interiorAmbientGraphics;
    graphics.clear();
    if (!this.interiorAmbientVisible) return;
    const flicker = this.replay.ambient.effects.some((effect) => effect.kind === "interior-console-flicker");
    const vapor = this.replay.ambient.effects.some((effect) => effect.kind === "break-room-vapor");
    const phase = this.preferences.reducedMotion ? 0 : Math.floor(this.cursorMs / 280) % 3;
    if (flicker) {
      for (const [index, station] of this.replay.choreography.workstations.entries()) {
        const color = index % 2 === phase % 2 ? 0x2dd4ff : 0xf653d8;
        graphics.fillStyle(color, 0.34).fillRect(station.x - 8 + (index % 3) * 3, station.y - 18, 2, 1);
      }
    }
    if (vapor) {
      graphics.fillStyle(0x9ea8c2, 0.22);
      for (const [x, y] of [[184, 181], [187, 178], [190, 175]] as Array<[number, number]>) {
        graphics.fillRect(x + phase, y - phase, 2, 2);
      }
      graphics.fillStyle(0xeee9d8, 0.35).fillRect(182, 183, 10, 2);
    }
  }

  private renderAmbient(): void {
    if (this.rainGraphics) {
      this.rainGraphics.clear();
      const rain = this.replay.ambient.effects.find((effect) => effect.kind === "rain");
      if (rain && this.preferences.atmosphere > 0.12) {
        const motion = this.preferences.reducedMotion ? 37 : Math.floor(this.cursorMs / 70);
        const alpha = 0.06 + this.preferences.atmosphere * 0.18;
        this.rainGraphics.lineStyle(1, this.preferences.highContrast ? 0x9ea8c2 : 0x2dd4ff, alpha);
        for (let i = 0; i < 52; i += 1) {
          const x = (i * 83 + 17) % WORLD_WIDTH;
          const y = (i * 47 + motion * 3) % WORLD_HEIGHT;
          this.rainGraphics.lineBetween(x, y, x - 2, y + 5);
        }
      }
    }
    for (const actor of this.replay.ambient.actors) {
      const sprite = this.sprites.get(actor.id);
      if (!sprite || !actor.path || actor.path.length < 2) continue;
      const progress = this.preferences.reducedMotion ? 0.36 : (this.cursorMs % Math.max(1, actor.duration_ms)) / Math.max(1, actor.duration_ms);
      const scaled = progress * (actor.path.length - 1);
      const index = Math.min(actor.path.length - 2, Math.floor(scaled));
      const from = actor.path[index]!;
      const to = actor.path[index + 1]!;
      const point = lerpPoint(from, to, scaled - index);
      sprite.setPosition(point.x, point.y).setAlpha(0.44 + this.preferences.atmosphere * 0.34);
    }
  }

  private renderInstitutionStates(): void {
    if (!this.stateGraphics) return;
    this.stateGraphics.clear();
    const accepted = this.eventByType("paper.decided");
    const funded = this.eventByType("resource.changed");
    const policy = this.eventByType("policy.changed");
    if (accepted && this.cursorMs >= accepted.logical_timestamp_ms) {
      this.stateGraphics.fillStyle(0xeee9d8, 0.92).fillRect(439, 174, 7, 9);
      this.stateGraphics.fillStyle(0x4f7cff, 0.9).fillRect(441, 176, 5, 2);
    }
    if (funded && this.cursorMs >= funded.logical_timestamp_ms) {
      this.stateGraphics.lineStyle(1, 0x39f5c8, 0.95).strokeRect(92, 90, 16, 11);
      this.stateGraphics.fillStyle(0x39f5c8, 0.9).fillRect(95, 94, 3, 4).fillRect(101, 91, 3, 7);
    }
    if (policy && this.cursorMs >= policy.logical_timestamp_ms) {
      this.stateGraphics.lineStyle(1, 0xff617d, 0.82).strokeRect(304, 83, 60, 5);
      for (let x = 307; x < 361; x += 7) this.stateGraphics.fillStyle(0xff617d, 0.8).fillRect(x, 85, 3, 1);
    }
  }

  private eventByType(type: string): CanonicalEvent | undefined {
    return this.replay.canonical.events.find((event) => event.kind === type);
  }

  private stateMarkerAt(x: number, y: number): CanonicalEvent | undefined {
    const accepted = this.eventByType("paper.decided");
    if (accepted && this.cursorMs >= accepted.logical_timestamp_ms && x >= 435 && x <= 451 && y >= 170 && y <= 188) return accepted;
    const funded = this.eventByType("resource.changed");
    if (funded && this.cursorMs >= funded.logical_timestamp_ms && x >= 88 && x <= 112 && y >= 86 && y <= 105) return funded;
    const policy = this.eventByType("policy.changed");
    if (policy && this.cursorMs >= policy.logical_timestamp_ms && x >= 300 && x <= 368 && y >= 79 && y <= 92) return policy;
    return undefined;
  }

  private installPointerControls(): void {
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      if (pointer.leftButtonDown()) {
        this.dragging = true;
        this.dragStart = new Phaser.Math.Vector2(pointer.x, pointer.y);
      }
    });
    this.input.on("pointermove", (pointer: Phaser.Input.Pointer) => {
      if (!this.dragging || !this.dragStart || !pointer.isDown) return;
      const dx = pointer.x - this.dragStart.x;
      const dy = pointer.y - this.dragStart.y;
      this.cameras.main.scrollX -= Math.round(dx / this.cameras.main.zoom);
      this.cameras.main.scrollY -= Math.round(dy / this.cameras.main.zoom);
      this.dragStart.set(pointer.x, pointer.y);
    });
    this.input.on("pointerup", () => { this.dragging = false; this.dragStart = undefined; });
    this.input.on("wheel", (_pointer: Phaser.Input.Pointer, _objects: Phaser.GameObjects.GameObject[], _dx: number, dy: number) => this.zoomBy(dy < 0 ? 1 : -1));
  }

  private installKeyboardControls(): void {
    const keyboard = this.input.keyboard;
    if (!keyboard) return;
    this.keyMap = keyboard.addKeys({
      left: Phaser.Input.Keyboard.KeyCodes.LEFT,
      right: Phaser.Input.Keyboard.KeyCodes.RIGHT,
      up: Phaser.Input.Keyboard.KeyCodes.UP,
      down: Phaser.Input.Keyboard.KeyCodes.DOWN,
      a: Phaser.Input.Keyboard.KeyCodes.A,
      d: Phaser.Input.Keyboard.KeyCodes.D,
      w: Phaser.Input.Keyboard.KeyCodes.W,
      s: Phaser.Input.Keyboard.KeyCodes.S,
      plus: Phaser.Input.Keyboard.KeyCodes.PLUS,
      minus: Phaser.Input.Keyboard.KeyCodes.MINUS,
    }) as Record<string, Phaser.Input.Keyboard.Key>;
    keyboard.on("keydown-PLUS", () => this.zoomBy(1));
    keyboard.on("keydown-MINUS", () => this.zoomBy(-1));
  }

  private updateKeyboardPan(delta: number): void {
    if (!this.keyMap) return;
    const speed = Math.max(2, Math.round(delta * 0.18 / this.cameras.main.zoom));
    if (this.keyMap.left?.isDown || this.keyMap.a?.isDown) this.cameras.main.scrollX -= speed;
    if (this.keyMap.right?.isDown || this.keyMap.d?.isDown) this.cameras.main.scrollX += speed;
    if (this.keyMap.up?.isDown || this.keyMap.w?.isDown) this.cameras.main.scrollY -= speed;
    if (this.keyMap.down?.isDown || this.keyMap.s?.isDown) this.cameras.main.scrollY += speed;
  }
}

export const arcologyConfig = (scene: ArcologyScene, parent = "phaser-root"): Phaser.Types.Core.GameConfig => ({
  type: Phaser.AUTO,
  parent,
  width: 480,
  height: 270,
  backgroundColor: "#070814",
  pixelArt: true,
  antialias: false,
  roundPixels: true,
  physics: { default: "arcade", arcade: { debug: false } },
  render: { antialias: false, pixelArt: true, roundPixels: true },
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH, width: 480, height: 270 },
  scene,
});
