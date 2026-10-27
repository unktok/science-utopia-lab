import Phaser from "phaser";
import type { AssetPack, FlowType, ReplayV2, RuntimePreferences, SelectionDetail, TruthStatus, VisualFlow, WorldEntity } from "./types";

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

interface FlowVisual {
  model: VisualFlow;
  graphics: Phaser.GameObjects.Graphics;
  packet?: Phaser.GameObjects.Image;
  curve: Phaser.Curves.QuadraticBezier;
}

const dispatchSelection = (detail: SelectionDetail): void => {
  window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail }));
};

function drawDashedCurve(graphics: Phaser.GameObjects.Graphics, curve: Phaser.Curves.QuadraticBezier, color: number, alpha: number, dotted: boolean): void {
  const points = curve.getPoints(28);
  graphics.lineStyle(dotted ? 1 : 2, color, alpha);
  for (let i = 1; i < points.length; i += 1) {
    const from = points[i - 1];
    const to = points[i];
    if (!from || !to) continue;
    const draw = dotted ? i % 3 === 0 : i % 3 !== 0;
    if (draw) graphics.lineBetween(Math.round(from.x), Math.round(from.y), Math.round(to.x), Math.round(to.y));
  }
}

function truthAlpha(status: TruthStatus): number {
  if (status === "canonical") return 0.95;
  if (status === "derived") return 0.78;
  return 0.28;
}

export class ArcologyScene extends Phaser.Scene {
  readonly replay: ReplayV2;
  readonly assetPack: AssetPack;
  private readonly entities = new Map<string, WorldEntity>();
  private readonly sprites = new Map<string, Phaser.GameObjects.Image>();
  private readonly flowVisuals: FlowVisual[] = [];
  private readonly layerVisibility = new Map<FlowType, boolean>();
  private cursorMs = 0;
  private selectedId?: string;
  private followEnabled = false;
  private preferences: RuntimePreferences = { reducedMotion: false, highContrast: false, atmosphere: 0.62 };
  private dragging = false;
  private dragStart?: Phaser.Math.Vector2;
  private minimap?: Phaser.Cameras.Scene2D.Camera;
  private keyMap?: Record<string, Phaser.Input.Keyboard.Key>;

  constructor(replay: ReplayV2, assetPack: AssetPack) {
    super({ key: "ArcologyScene" });
    this.replay = replay;
    this.assetPack = assetPack;
    for (const flowType of Object.keys(FLOW_COLORS) as FlowType[]) this.layerVisibility.set(flowType, true);
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
    const allEntities = [...groups.institutions, ...groups.artifacts, ...groups.researchers, ...this.replay.ambient.actors];
    for (const entity of allEntities) {
      this.entities.set(entity.id, entity);
      this.createEntity(entity);
    }
    for (const flow of this.replay.choreography.flows) this.createFlow(flow);

    this.minimap = this.cameras.add(368, 8, 104, 62, false, "minimap");
    this.minimap.setBounds(0, 0, WORLD_WIDTH, WORLD_HEIGHT).setZoom(0.216).centerOn(WORLD_WIDTH / 2, WORLD_HEIGHT / 2).setRoundPixels(true);
    this.minimap.setBackgroundColor("rgba(7,8,20,0.88)");

    this.installPointerControls();
    this.installKeyboardControls();
    this.cameras.main.centerOn(WORLD_WIDTH / 2, WORLD_HEIGHT / 2);
    window.dispatchEvent(new CustomEvent("noctiluca:renderer-ready"));
  }

  update(_time: number, delta: number): void {
    this.updateKeyboardPan(delta);
    this.renderFlows();
    if (this.followEnabled && this.selectedId) {
      const sprite = this.sprites.get(this.selectedId);
      if (sprite) this.cameras.main.centerOn(Math.round(sprite.x), Math.round(sprite.y));
    }
  }

  setCursor(milliseconds: number): void {
    this.cursorMs = Math.max(0, Math.min(milliseconds, this.replay.choreography.duration_ms));
  }

  setLayerVisible(flowType: FlowType, visible: boolean): void {
    this.layerVisibility.set(flowType, visible);
  }

  select(id: string): void {
    this.selectedId = id;
    const sprite = this.sprites.get(id);
    if (sprite && this.followEnabled) this.cameras.main.centerOn(Math.round(sprite.x), Math.round(sprite.y));
  }

  setFollow(enabled: boolean): void {
    this.followEnabled = enabled;
  }

  setPreferences(preferences: RuntimePreferences): void {
    this.preferences = preferences;
    const atmosphere = Phaser.Math.Clamp(preferences.atmosphere, 0, 1);
    this.cameras.main.setBackgroundColor(preferences.highContrast ? "#000000" : "#070814");
    for (const flowVisual of this.flowVisuals) flowVisual.graphics.setAlpha(preferences.highContrast ? 1 : 0.7 + atmosphere * 0.3);
    for (const sprite of this.sprites.values()) {
      if (sprite instanceof Phaser.GameObjects.Sprite && sprite.anims.isPlaying) {
        if (preferences.reducedMotion) sprite.anims.pause();
        else sprite.anims.resume();
      }
    }
  }

  zoomBy(direction: 1 | -1): void {
    const current = Math.round(this.cameras.main.zoom);
    this.cameras.main.setZoom(Phaser.Math.Clamp(current + direction, 1, 3)).setRoundPixels(true);
  }

  private drawWorldGround(): void {
    const graphics = this.add.graphics().setDepth(-20);
    graphics.fillStyle(0x070814, 1).fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
    graphics.lineStyle(1, 0x1a2140, 0.55);
    for (let x = 0; x <= WORLD_WIDTH; x += 16) graphics.lineBetween(x, 0, x, WORLD_HEIGHT);
    for (let y = 0; y <= WORLD_HEIGHT; y += 16) graphics.lineBetween(0, y, WORLD_WIDTH, y);
    graphics.lineStyle(2, 0x2a3560, 0.6);
    for (let x = 0; x <= WORLD_WIDTH; x += 160) graphics.lineBetween(x, 0, x, WORLD_HEIGHT);
    for (let y = 0; y <= WORLD_HEIGHT; y += 160) graphics.lineBetween(0, y, WORLD_WIDTH, y);
  }

  private createEntity(entity: WorldEntity): void {
    if (!this.textures.exists(entity.asset_key)) {
      if (entity.entity_type === "ambient_actor") return;
      window.dispatchEvent(new CustomEvent("noctiluca:asset-missing", { detail: { key: entity.asset_key, entityId: entity.id } }));
      return;
    }
    const asset = this.assetPack.images.find((image) => image.key === entity.asset_key);
    const animationKey = `idle_${entity.asset_key}`;
    let sprite: Phaser.GameObjects.Image;
    if (asset?.frames) {
      const animated = this.add.sprite(Math.round(entity.x), Math.round(entity.y), entity.asset_key);
      if (!this.anims.exists(animationKey)) {
        this.anims.create({
          key: animationKey,
          frames: this.anims.generateFrameNumbers(entity.asset_key, { start: 0, end: asset.frames.end }),
          frameRate: entity.entity_type === "researcher" ? 4 : 2,
          repeat: -1,
        });
      }
      animated.play(animationKey);
      sprite = animated;
    } else {
      sprite = this.add.image(Math.round(entity.x), Math.round(entity.y), entity.asset_key);
    }
    sprite.setOrigin(0.5, 1).setDepth(entity.entity_type === "institution" ? 2 : 8);
    if (asset) sprite.setDisplaySize(Math.round(asset.width), Math.round(asset.height));
    sprite.setInteractive({ useHandCursor: true });
    sprite.on("pointerdown", () => dispatchSelection({ id: entity.id, category: "entity" }));
    sprite.setData("truth_status", entity.truth_status);
    this.sprites.set(entity.id, sprite);
  }

  private createFlow(flow: VisualFlow): void {
    const from = this.entities.get(flow.from_entity_id);
    const to = this.entities.get(flow.to_entity_id);
    if (!from || !to) return;
    const midpoint = new Phaser.Math.Vector2(
      Math.round((from.x + to.x) / 2),
      Math.round((from.y + to.y) / 2 - Math.min(64, Math.abs(from.x - to.x) * 0.18 + 18)),
    );
    const curve = new Phaser.Curves.QuadraticBezier(
      new Phaser.Math.Vector2(Math.round(from.x), Math.round(from.y - 18)),
      midpoint,
      new Phaser.Math.Vector2(Math.round(to.x), Math.round(to.y - 18)),
    );
    const graphics = this.add.graphics().setDepth(4).setInteractive(
      new Phaser.Geom.Rectangle(Math.min(from.x, to.x), Math.min(from.y, to.y) - 80, Math.abs(to.x - from.x) || 32, Math.abs(to.y - from.y) + 96),
      Phaser.Geom.Rectangle.Contains,
    );
    graphics.on("pointerdown", () => dispatchSelection({ id: flow.id, category: "flow" }));
    const packetKey = `flow_${flow.flow_type}`;
    const packetAsset = this.assetPack.images.find((image) => image.key === packetKey);
    const packet = this.textures.exists(packetKey) ? this.add.image(from.x, from.y, packetKey).setDepth(9).setInteractive({ useHandCursor: true }) : undefined;
    if (packet && packetAsset) packet.setDisplaySize(packetAsset.width, packetAsset.height);
    packet?.on("pointerdown", () => dispatchSelection({ id: flow.id, category: "flow" }));
    if (!packet) window.dispatchEvent(new CustomEvent("noctiluca:asset-missing", { detail: { key: packetKey, entityId: flow.id } }));
    this.flowVisuals.push({ model: flow, graphics, packet, curve });
  }

  private renderFlows(): void {
    for (const visual of this.flowVisuals) {
      const { model, graphics, packet, curve } = visual;
      graphics.clear();
      const visible = this.layerVisibility.get(model.flow_type) !== false;
      const active = this.cursorMs >= model.logical_timestamp_ms && this.cursorMs <= model.logical_timestamp_ms + model.duration_ms;
      graphics.setVisible(visible && (active || this.cursorMs >= model.logical_timestamp_ms));
      packet?.setVisible(visible && active);
      if (!visible) continue;
      const color = FLOW_COLORS[model.flow_type];
      drawDashedCurve(graphics, curve, color, truthAlpha(model.truth_status), model.truth_status === "ambient");
      if (packet && active) {
        const rawProgress = model.duration_ms === 0 ? 1 : (this.cursorMs - model.logical_timestamp_ms) / model.duration_ms;
        const progress = this.preferences.reducedMotion ? 0.5 : Phaser.Math.Clamp(rawProgress, 0, 1);
        const point = curve.getPoint(progress);
        packet.setPosition(Math.round(point.x), Math.round(point.y));
      }
    }
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

export const arcologyConfig = (scene: ArcologyScene): Phaser.Types.Core.GameConfig => ({
  type: Phaser.AUTO,
  parent: "phaser-root",
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
