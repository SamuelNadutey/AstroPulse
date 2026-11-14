import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Page = "today" | "checkin" | "trends" | "relay" | "progress";
type Status = "normal" | "watch" | "concern" | "contact" | "insufficient";
type Scenario = "Calm Week" | "Drift Day 6" | "Fever Blackout" | "Isolation Mood";
type Region = "head" | "chest" | "lungs" | "torso" | "legs";
type IndicatorKey = "heart" | "sleep" | "temp" | "mood" | "exercise" | "oxygen";

type Indicator = {
  key: IndicatorKey;
  label: string;
  short: string;
  value: string;
  unit: string;
  status: Status;
  region: Region;
  source: "Device" | "Self-report";
  reason: string;
  change: string;
  values: number[];
  baseline: string;
};

const statusMeta: Record<Status, { label: string; symbol: string }> = {
  normal: { label: "Normal", symbol: "✓" },
  watch: { label: "Watch", symbol: "!" },
  concern: { label: "Concern", symbol: "↑" },
  contact: { label: "Contact ground", symbol: "!" },
  insufficient: { label: "Not enough data", symbol: "·" },
};

const scenarioCopy: Record<Scenario, string> = {
  "Calm Week": "Stable readings across the current reference period.",
  "Drift Day 6": "Heart rate rises while sleep gradually reduces from day six.",
  "Fever Blackout": "Temperature change while ground communication is unavailable.",
  "Isolation Mood": "Mood and activity gradually reduce during isolation.",
};

const baseValues: Record<IndicatorKey, number[]> = {
  heart: [65, 66, 64, 67, 66, 65, 67, 66, 68, 67, 66, 68, 67, 68],
  sleep: [7.6, 7.4, 7.8, 7.2, 7.5, 7.7, 7.3, 7.5, 7.4, 7.6, 7.3, 7.5, 7.4, 7.5],
  temp: [36.7, 36.6, 36.7, 36.8, 36.6, 36.7, 36.7, 36.8, 36.7, 36.6, 36.7, 36.8, 36.7, 36.7],
  mood: [4, 4, 5, 4, 4, 4, 5, 4, 4, 5, 4, 4, 4, 4],
  exercise: [48, 52, 45, 50, 55, 47, 51, 49, 53, 46, 50, 52, 48, 50],
  oxygen: [98, 98, 97, 98, 98, 97, 98, 98, 97, 98, 98, 98, 97, 98],
};

function buildIndicators(scenario: Scenario): Indicator[] {
  const values = Object.fromEntries(
    Object.entries(baseValues).map(([key, list]) => [key, [...list]]),
  ) as Record<IndicatorKey, number[]>;
  const statuses: Partial<Record<IndicatorKey, Status>> = {};
  const reasons: Partial<Record<IndicatorKey, string>> = {};

  if (scenario === "Drift Day 6") {
    values.heart = [65, 66, 64, 67, 66, 68, 69, 70, 71, 72, 73, 74, 75, 76];
    values.sleep = [7.6, 7.5, 7.8, 7.4, 7.5, 7.1, 6.9, 6.8, 6.6, 6.4, 6.2, 6.1, 5.9, 5.8];
    statuses.heart = "concern";
    statuses.sleep = "watch";
    reasons.heart = "Gradual upward drift across nine readings.";
    reasons.sleep = "Gradual reduction from your established personal pattern.";
  }
  if (scenario === "Fever Blackout") {
    values.temp = [36.7, 36.7, 36.6, 36.8, 36.7, 36.7, 36.8, 36.9, 37, 37.2, 37.5, 37.8, 38, 38.2];
    statuses.temp = "contact";
    reasons.temp = "Sustained upward change flagged by the demonstration scenario.";
  }
  if (scenario === "Isolation Mood") {
    values.mood = [5, 4, 5, 4, 4, 4, 4, 3, 3, 3, 3, 2, 2, 2];
    values.exercise = [54, 52, 50, 53, 48, 46, 44, 40, 38, 35, 32, 29, 25, 22];
    statuses.mood = "concern";
    statuses.exercise = "watch";
    reasons.mood = "Gradual reduction across the recent reference period.";
    reasons.exercise = "Activity is trending below your recent pattern.";
  }

  const specs: Array<Omit<Indicator, "value" | "status" | "reason" | "change" | "values">> = [
    {
      key: "heart",
      label: "Resting heart rate",
      short: "Heart rate",
      unit: "bpm",
      region: "chest",
      source: "Device",
      baseline: "65–69 bpm",
    },
    {
      key: "sleep",
      label: "Sleep",
      short: "Sleep",
      unit: "hours",
      region: "head",
      source: "Self-report",
      baseline: "7.2–7.8 hours",
    },
    {
      key: "temp",
      label: "Body temperature",
      short: "Temperature",
      unit: "°C",
      region: "torso",
      source: "Device",
      baseline: "Personal range set",
    },
    {
      key: "mood",
      label: "Mood & stress",
      short: "Mood",
      unit: "/ 5",
      region: "head",
      source: "Self-report",
      baseline: "4–5 / 5",
    },
    {
      key: "exercise",
      label: "Exercise",
      short: "Exercise",
      unit: "min",
      region: "legs",
      source: "Self-report",
      baseline: "45–55 min",
    },
    {
      key: "oxygen",
      label: "Blood oxygen",
      short: "SpO₂",
      unit: "%",
      region: "lungs",
      source: "Device",
      baseline: "Personal range set",
    },
  ];

  return specs.map((spec) => {
    const list = values[spec.key];
    const current = list[list.length - 1];
    const previous = list[list.length - 2];
    const delta = Math.round((current - previous) * 10) / 10;
    return {
      ...spec,
      values: list,
      value: String(current),
      status: statuses[spec.key] ?? "normal",
      reason: reasons[spec.key] ?? "Reading is consistent with your 14-day personal pattern.",
      change: delta === 0 ? "No change" : `${delta > 0 ? "+" : ""}${delta} since yesterday`,
    };
  });
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  const paths: Record<string, ReactNode> = {
    pulse: (
      <>
        <path d="M3 12h4l2-5 3 10 2.5-6 1.5 3h5" />
        <circle cx="12" cy="12" r="9" />
      </>
    ),
    grid: (
      <>
        <rect x="4" y="4" width="6" height="6" rx="1" />
        <rect x="14" y="4" width="6" height="6" rx="1" />
        <rect x="4" y="14" width="6" height="6" rx="1" />
        <rect x="14" y="14" width="6" height="6" rx="1" />
      </>
    ),
    check: (
      <>
        <path d="M5 12.5 9.5 17 19 7.5" />
        <rect x="3" y="3" width="18" height="18" rx="5" />
      </>
    ),
    trend: (
      <>
        <path d="m4 17 5-5 4 3 7-8" />
        <path d="M15 7h5v5" />
      </>
    ),
    relay: (
      <>
        <path d="M8 16a5 5 0 0 1 8 0" />
        <path d="M5 13a9 9 0 0 1 14 0" />
        <circle cx="12" cy="19" r="1.5" />
      </>
    ),
    progress: (
      <>
        <path d="M5 20V10M12 20V4M19 20v-7" />
      </>
    ),
    shield: (
      <>
        <path d="M12 3 5 6v5c0 4.6 2.8 8 7 10 4.2-2 7-5.4 7-10V6l-7-3Z" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    chevron: <path d="m9 18 6-6-6-6" />,
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m14 7 5 5-5 5" />
      </>
    ),
    moon: <path d="M19 15.5A8 8 0 0 1 8.5 5a8 8 0 1 0 10.5 10.5Z" />,
    heart: (
      <>
        <path d="M20 8.5c0 5-8 10-8 10s-8-5-8-10A4.5 4.5 0 0 1 12 5.7 4.5 4.5 0 0 1 20 8.5Z" />
        <path d="M8 11h2l1-2 2 4 1-2h2" />
      </>
    ),
    temp: (
      <>
        <path d="M9 14.8V5a3 3 0 0 1 6 0v9.8a5 5 0 1 1-6 0Z" />
        <path d="M12 8v8" />
      </>
    ),
    mood: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M8.5 14.5a5 5 0 0 0 7 0M9 9h.01M15 9h.01" />
      </>
    ),
    activity: (
      <>
        <path d="m8 5 3 2-2 4 4 2 2 6" />
        <circle cx="13" cy="4" r="2" />
        <path d="m9 11-4 4m8-2 4-3" />
      </>
    ),
    oxygen: (
      <>
        <path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11Z" />
        <path d="M9.5 14.5h5" />
      </>
    ),
    lock: (
      <>
        <rect x="5" y="10" width="14" height="11" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
        <path d="M5 20h14" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5M12 8h.01" />
      </>
    ),
    close: (
      <>
        <path d="m6 6 12 12M18 6 6 18" />
      </>
    ),
    menu: (
      <>
        <path d="M4 7h16M4 12h16M4 17h16" />
      </>
    ),
  };
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" {...common}>
      {paths[name] ?? paths.info}
    </svg>
  );
}

function StatusPill({ status, compact = false }: { status: Status; compact?: boolean }) {
  const meta = statusMeta[status];
  return (
    <span className={`status-pill status-${status} ${compact ? "compact" : ""}`}>
      {meta.label}
    </span>
  );
}

function Sparkline({
  values,
  status,
  projected = false,
  height = 64,
}: {
  values: number[];
  status: Status;
  projected?: boolean;
  height?: number;
}) {
  const width = 260;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map(
      (v, i) =>
        `${(i / (values.length - 1)) * width},${height - 8 - ((v - min) / span) * (height - 16)}`,
    )
    .join(" ");
  const last = values[values.length - 1];
  const delta = values.length > 4 ? (last - values[values.length - 4]) / 3 : 0;
  const forecast = [1, 2, 3, 4]
    .map(
      (n, i) =>
        `${width + (i + 1) * 28},${Math.max(8, Math.min(height - 8, height - 8 - ((last + delta * n - min) / span) * (height - 16)))}`,
    )
    .join(" ");
  return (
    <svg
      className={`sparkline chart-${status}`}
      viewBox={`0 0 ${projected ? 380 : width} ${height}`}
      preserveAspectRatio="none"
      aria-label="Historical trend chart"
    >
      <line
        className="chart-grid"
        x1="0"
        y1={height - 8}
        x2={projected ? 380 : width}
        y2={height - 8}
      />
      <polyline points={points} />
      {projected && (
        <>
          <line className="forecast-divider" x1={width + 12} y1="0" x2={width + 12} y2={height} />
          <polyline
            className="forecast-line"
            points={`${width},${height - 8 - ((last - min) / span) * (height - 16)} ${forecast}`}
          />
        </>
      )}
    </svg>
  );
}

function SectionTitle({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
      </div>
      {action}
    </div>
  );
}

function FlatBodyMap({
  selected,
  onSelect,
  indicators,
}: {
  selected: Region;
  onSelect: (r: Region) => void;
  indicators: Indicator[];
}) {
  const regionStatus = (region: Region) => {
    const severity: Status[] = ["insufficient", "normal", "watch", "concern", "contact"];
    return (
      indicators
        .filter((i) => i.region === region)
        .sort((a, b) => severity.indexOf(b.status) - severity.indexOf(a.status))[0]?.status ??
      "insufficient"
    );
  };
  const regions: Array<{ id: Region; label: string; y: number }> = [
    { id: "head", label: "Head", y: 42 },
    { id: "chest", label: "Chest", y: 107 },
    { id: "lungs", label: "Lungs", y: 146 },
    { id: "torso", label: "Torso", y: 203 },
    { id: "legs", label: "Legs", y: 315 },
  ];
  return (
    <div className="body-map-wrap">
      <svg
        className="body-map"
        viewBox="0 0 340 420"
        role="img"
        aria-label="Interactive body health map"
      >
        <defs>
          <linearGradient id="bodyFill" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#dbe5e2" />
            <stop offset="1" stopColor="#a7b8b4" />
          </linearGradient>
        </defs>
        <circle cx="168" cy="43" r="30" fill="url(#bodyFill)" />
        <path
          d="M135 80Q168 70 201 80L222 170 202 258 194 400H163L155 270 145 400H114L116 258 97 170Z"
          fill="url(#bodyFill)"
        />
        <path
          d="m104 91-24 31-21 105 25 6 34-105M201 91l24 31 21 105-25 6-34-105"
          fill="none"
          stroke="#b7c5c1"
          strokeWidth="25"
          strokeLinecap="round"
        />
        <path
          d="M148 114c-17-13-35 2-30 22 5 18 25 28 30 31ZM154 114c17-13 35 2 30 22-5 18-25 28-30 31Z"
          fill="#657b76"
          opacity=".46"
        />
        {regions.map((r, index) => {
          const side = index % 2 === 0 ? 1 : -1;
          const x = side === 1 ? 270 : 65;
          return (
            <g
              key={r.id}
              className={`map-region status-stroke-${regionStatus(r.id)} ${selected === r.id ? "selected" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={`${r.label}, ${statusMeta[regionStatus(r.id)].label}`}
              onClick={() => onSelect(r.id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(r.id)}
            >
              <path d={`M168 ${r.y} L${x} ${r.y} L${side === 1 ? 292 : 43} ${r.y}`} />
              <circle cx="168" cy={r.y} r="9" />
              <rect x={side === 1 ? 272 : 4} y={r.y - 15} width="64" height="30" rx="15" />
              <text x={side === 1 ? 304 : 36} y={r.y + 4} textAnchor="middle">
                {r.label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="map-hint">
        <span className="pulse-dot" /> Select a region to inspect
      </p>
    </div>
  );
}

const bodyRegions: Array<{
  id: Region;
  label: string;
  points: Array<[number, number, number]>;
  radius: number;
}> = [
  { id: "head", label: "Head", points: [[0, 4.16, 0.24]], radius: 0.3 },
  { id: "chest", label: "Chest", points: [[0.18, 3.33, 0.3]], radius: 0.28 },
  {
    id: "lungs",
    label: "Lungs",
    points: [
      [-0.4, 3.22, 0.21],
      [0.4, 3.22, 0.21],
    ],
    radius: 0.25,
  },
  { id: "torso", label: "Torso", points: [[0, 2.68, 0.26]], radius: 0.32 },
  {
    id: "legs",
    label: "Legs",
    points: [
      [-0.25, 1.43, 0.19],
      [0.25, 1.43, 0.19],
    ],
    radius: 0.35,
  },
];

const severity: Status[] = ["insufficient", "normal", "watch", "concern", "contact"];
const statusColors: Record<Status, string> = {
  insufficient: "#9AA5B8",
  normal: "#2BC4A0",
  watch: "#F0E442",
  concern: "#F0A030",
  contact: "#FF7A6B",
};

function StatusMarker({ status }: { status: Status }) {
  return (
    <span className={`map-status-marker marker-${status}`} aria-hidden="true">
      <span>{statusMeta[status].symbol}</span>
    </span>
  );
}

function BodyMap3D({
  selected,
  onSelect,
  indicators,
}: {
  selected: Region;
  onSelect: (r: Region) => void;
  indicators: Indicator[];
}) {
  const mountRef = useRef<HTMLDivElement>(null);
  const labelsRef = useRef<Record<string, HTMLButtonElement | null>>({});
  const selectRef = useRef(onSelect);
  const selectedRef = useRef(selected);
  const hoveredRef = useRef<Region | null>(null);
  const sceneRef = useRef<{
    camera: THREE.PerspectiveCamera;
    controls: OrbitControls;
    rings: Map<Region, THREE.Mesh[]>;
    targets: Map<Region, THREE.Object3D[]>;
  } | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hovered, setHovered] = useState<Region | null>(null);
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    hoveredRef.current = hovered;
  }, [hovered]);

  const regionStatus = (region: Region) =>
    indicators
      .filter((i) => i.region === region)
      .sort((a, b) => severity.indexOf(b.status) - severity.indexOf(a.status))[0]?.status ??
    "insufficient";

  const statuses = useMemo(
    () =>
      Object.fromEntries(bodyRegions.map((r) => [r.id, regionStatus(r.id)])) as Record<
        Region,
        Status
      >,
    [indicators],
  );

  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    selectedRef.current = selected;
    setAnnouncement(
      `${bodyRegions.find((r) => r.id === selected)?.label} selected. ${statusMeta[statuses[selected]].label}.`,
    );
    const setup = sceneRef.current;
    if (!setup) return;
    const region = bodyRegions.find((r) => r.id === selected);
    if (!region) return;
    const center = region.points
      .reduce((sum, point) => sum.add(new THREE.Vector3(...point)), new THREE.Vector3())
      .multiplyScalar(1 / region.points.length);
    const destination = new THREE.Vector3(center.x, center.y + 0.05, center.z + 4.4);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fromPosition = setup.camera.position.clone();
    const fromTarget = setup.controls.target.clone();
    const start = performance.now();
    const duration = reduced ? 0 : 520;
    const move = (now: number) => {
      const raw = duration === 0 ? 1 : Math.min(1, (now - start) / duration);
      const t = 1 - Math.pow(1 - raw, 3);
      setup.camera.position.lerpVectors(fromPosition, destination, t);
      setup.controls.target.lerpVectors(fromTarget, center, t);
      setup.controls.update();
      if (raw < 1) requestAnimationFrame(move);
    };
    requestAnimationFrame(move);
  }, [selected, statuses]);

  useEffect(() => {
    const setup = sceneRef.current;
    if (!setup) return;
    setup.rings.forEach((rings, id) => {
      rings.forEach((ring) => {
        const material = ring.material as THREE.MeshBasicMaterial;
        material.color.set(statusColors[statuses[id]]);
      });
    });
  }, [statuses]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setWebglFailed(true);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 100);
    camera.position.set(0, 2.35, 7.2);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 2.3, 0);
    controls.enableDamping = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    controls.dampingFactor = 0.07;
    controls.enablePan = false;
    controls.minDistance = 3.2;
    controls.maxDistance = 9;
    controls.minPolarAngle = Math.PI * 0.28;
    controls.maxPolarAngle = Math.PI * 0.68;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.7;
    controls.update();

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x0e1420, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.className = "body-canvas";
    renderer.domElement.setAttribute("aria-hidden", "true");
    mount.prepend(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xd9e6ff, 0x182031, 1.7));
    const key = new THREE.DirectionalLight(0xe8f2ff, 3.2);
    key.position.set(3.5, 5.5, 5);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x6cb4ff, 1.8);
    fill.position.set(-4, 3, 3);
    scene.add(fill);
    const rim = new THREE.DirectionalLight(0x9fb7dc, 2.4);
    rim.position.set(2, 4, -4);
    scene.add(rim);

    const targets = new Map<Region, THREE.Object3D[]>();
    const rings = new Map<Region, THREE.Mesh[]>();
    const hitMaterial = new THREE.MeshBasicMaterial({
      transparent: true,
      opacity: 0.001,
      depthWrite: false,
    });
    bodyRegions.forEach((region) => {
      const regionTargets: THREE.Object3D[] = [];
      const regionRings: THREE.Mesh[] = [];
      region.points.forEach((point) => {
        const hit = new THREE.Mesh(
          new THREE.SphereGeometry(region.radius, 18, 12),
          hitMaterial.clone(),
        );
        hit.position.set(...point);
        hit.userData.region = region.id;
        scene.add(hit);
        regionTargets.push(hit);

        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(region.radius * 0.72, 0.022, 10, 48),
          new THREE.MeshBasicMaterial({
            color: statusColors[statuses[region.id]],
            transparent: true,
            opacity: 0.8,
            depthTest: false,
          }),
        );
        ring.position.set(point[0], point[1], point[2] + 0.02);
        ring.renderOrder = 4;
        scene.add(ring);
        regionRings.push(ring);
      });
      targets.set(region.id, regionTargets);
      rings.set(region.id, regionRings);
    });
    sceneRef.current = { camera, controls, rings, targets };

    const loader = new GLTFLoader();
    loader.load(
      "/models/astropulse_body.glb",
      (gltf) => {
        gltf.scene.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.material = new THREE.MeshStandardMaterial({
              color: 0xc6ccd8,
              roughness: 0.72,
              metalness: 0.03,
            });
          }
        });
        scene.add(gltf.scene);
        setLoading(false);
      },
      undefined,
      () => setWebglFailed(true),
    );

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const setPointer = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      return raycaster
        .intersectObjects([...targets.values()].flat(), false)
        .find((hit) => hit.object.userData.region)?.object.userData.region as Region | undefined;
    };
    const onMove = (event: PointerEvent) => {
      const region = setPointer(event) ?? null;
      setHovered(region);
      renderer.domElement.style.cursor = region ? "pointer" : "grab";
    };
    const onClick = (event: PointerEvent) => {
      const region = setPointer(event);
      if (region) selectRef.current(region);
    };
    renderer.domElement.addEventListener("pointermove", onMove);
    renderer.domElement.addEventListener("click", onClick);

    const resize = () => {
      const { width, height } = mount.getBoundingClientRect();
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    let frame = 0;
    const render = () => {
      frame = requestAnimationFrame(render);
      controls.update();
      rings.forEach((regionRings, id) => {
        regionRings.forEach((ring) => {
          const active = id === selectedRef.current || id === hoveredRef.current;
          (ring.material as THREE.MeshBasicMaterial).opacity = active ? 1 : 0.72;
        });
      });
      bodyRegions.forEach((region) => {
        const label = labelsRef.current[region.id];
        const objects = targets.get(region.id);
        if (!label || !objects) return;
        const center = objects
          .reduce((sum, object) => sum.add(object.position), new THREE.Vector3())
          .multiplyScalar(1 / objects.length);
        const toCamera = camera.position.clone().sub(center).normalize();
        const facing = toCamera.dot(new THREE.Vector3(0, 0, 1)) > 0.12;
        const projected = center.clone().project(camera);
        label.style.setProperty("--label-x", `${(projected.x * 0.5 + 0.5) * 100}%`);
        label.style.setProperty("--label-y", `${(-projected.y * 0.5 + 0.5) * 100}%`);
        label.dataset.side = projected.x > 0 ? "right" : "left";
        label.hidden = !facing || projected.z > 1;
      });
      renderer.render(scene, camera);
    };
    render();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointermove", onMove);
      renderer.domElement.removeEventListener("click", onClick);
      controls.dispose();
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material.dispose());
        }
      });
      renderer.domElement.remove();
      sceneRef.current = null;
    };
  }, []);

  const resetView = () => {
    const setup = sceneRef.current;
    if (!setup) return;
    setup.camera.position.set(0, 2.35, 7.2);
    setup.controls.target.set(0, 2.3, 0);
    setup.controls.update();
  };

  if (webglFailed) {
    return (
      <div className="webgl-fallback">
        <p>3D view unavailable. Accessible body map shown.</p>
        <FlatBodyMap selected={selected} onSelect={onSelect} indicators={indicators} />
      </div>
    );
  }

  return (
    <div className="body-3d-shell">
      <div className="body-viewport" ref={mountRef}>
        {loading && <div className="model-loading">Loading local body model…</div>}
        <span className="simulated-map-badge">SIMULATED</span>
        <button className="reset-view" onClick={resetView}>
          Reset view
        </button>
        {bodyRegions.map((region) => (
          <button
            key={region.id}
            ref={(node) => {
              labelsRef.current[region.id] = node;
            }}
            className={`body-label status-label-${statuses[region.id]} ${selected === region.id ? "selected" : ""}`}
            onClick={() => onSelect(region.id)}
            onPointerEnter={() => setHovered(region.id)}
            onPointerLeave={() => setHovered(null)}
            aria-label={`${region.label}: ${statusMeta[statuses[region.id]].label}`}
          >
            <StatusMarker status={statuses[region.id]} />
            <span>
              <strong>{region.label}</strong>
              <small>{statusMeta[statuses[region.id]].label}</small>
            </span>
          </button>
        ))}
        <div className="orbit-instruction">Drag to orbit · Scroll or pinch to zoom</div>
      </div>
      <div className="region-button-list" aria-label="Body regions">
        {bodyRegions.map((region) => (
          <button
            key={region.id}
            className={selected === region.id ? "selected" : ""}
            onClick={() => onSelect(region.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(region.id);
              }
            }}
          >
            <StatusMarker status={statuses[region.id]} />
            <span>{region.label}</span>
            <small>{statusMeta[statuses[region.id]].label}</small>
          </button>
        ))}
      </div>
      <div className="map-legend" aria-label="Health status legend">
        {(Object.keys(statusMeta) as Status[]).map((status) => (
          <span key={status}>
            <StatusMarker status={status} />
            {statusMeta[status].label}
          </span>
        ))}
      </div>
      <div className="sr-only" aria-live="polite">
        {announcement}
      </div>
    </div>
  );
}

function Dashboard({
  indicators,
  scenario,
  environment,
  blackout,
  setPage,
}: {
  indicators: Indicator[];
  scenario: Scenario;
  environment: string;
  blackout: boolean;
  setPage: (p: Page) => void;
}) {
  const [region, setRegion] = useState<Region>("head");
  const selected = indicators.filter((i) => i.region === region);
  const concernCount = indicators.filter((i) =>
    ["watch", "concern", "contact"].includes(i.status),
  ).length;
  const primaryStatus: Status = indicators.some((i) => i.status === "contact")
    ? "contact"
    : indicators.some((i) => i.status === "concern")
      ? "concern"
      : concernCount
        ? "watch"
        : "normal";
  return (
    <>
      {blackout && (
        <div className="blackout-banner">
          <div className="blackout-icon">
            <Icon name="relay" />
          </div>
          <div>
            <strong>Communication blackout active</strong>
            <span>Ground relay unavailable. Records continue to save on this device.</span>
          </div>
          <span className="queue-count">{concernCount || 1} queued</span>
        </div>
      )}
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Mission day 42 · {environment}</p>
          <h1>
            {primaryStatus === "normal"
              ? "All signals steady."
              : primaryStatus === "contact"
                ? "A signal needs ground review."
                : "A pattern needs your attention."}
          </h1>
          <p className="hero-sub">
            {concernCount
              ? `${concernCount} indicator${concernCount > 1 ? "s are" : " is"} outside your usual pattern.`
              : "Your six health indicators are consistent with your recent personal pattern."}{" "}
            Data is stored locally.
          </p>
          <div className="hero-actions">
            <button className="button primary" onClick={() => setPage("checkin")}>
              <Icon name="plus" /> Begin today’s check-in
            </button>
            <span className="last-check">
              <Icon name="check" /> Last check-in today, 07:40
            </span>
          </div>
        </div>
        <div className="orbit-status">
          <div className="orbit-ring">
            <span className="orbit-value">{concernCount || 6}</span>
            <span>{concernCount ? "signals to review" : "signals steady"}</span>
          </div>
          <StatusPill status={primaryStatus} />
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="panel body-panel">
          <SectionTitle eyebrow="Interactive 3D body map" title="Where signals live" />
          <BodyMap3D selected={region} onSelect={setRegion} indicators={indicators} />
        </section>
        <section className="panel region-panel">
          <div className="region-head">
            <div>
              <p className="eyebrow">Selected region</p>
              <h2>{region.charAt(0).toUpperCase() + region.slice(1)}</h2>
            </div>
            <span className="region-index">
              {selected.length} signal{selected.length > 1 ? "s" : ""}
            </span>
          </div>
          <div className="region-signals">
            {selected.map((item) => (
              <div className="region-card" key={item.key}>
                <div className="indicator-icon">
                  <Icon name={item.key === "sleep" ? "moon" : item.key} />
                </div>
                <div className="region-card-main">
                  <div className="region-card-top">
                    <span>{item.label}</span>
                    <StatusPill status={item.status} compact />
                  </div>
                  <div className="reading">
                    <strong>{item.value}</strong> <span>{item.unit}</span>
                  </div>
                  <p>{item.reason}</p>
                  <div className="micro-meta">
                    <span>{item.source}</span>
                    <span>{item.change}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <button className="text-button" onClick={() => setPage("trends")}>
            Open full history <Icon name="arrow" />
          </button>
        </section>
      </div>

      <section className="signals-section">
        <SectionTitle
          eyebrow="Six-signal overview"
          title="Today’s readings"
          action={<span className="sim-label">SIMULATED · {scenario}</span>}
        />
        <div className="signal-grid">
          {indicators.map((item) => (
            <button className="signal-card" key={item.key} onClick={() => setPage("trends")}>
              <div className="signal-top">
                <span className="indicator-icon small">
                  <Icon name={item.key === "sleep" ? "moon" : item.key} />
                </span>
                <StatusPill status={item.status} compact />
              </div>
              <span className="signal-name">{item.label}</span>
              <div className="signal-reading">
                <strong>{item.value}</strong>
                <span>{item.unit}</span>
              </div>
              <Sparkline values={item.values.slice(-7)} status={item.status} height={42} />
              <span className="signal-foot">
                {item.change}
                <Icon name="chevron" size={16} />
              </span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function CheckIn({
  environment,
  setEnvironment,
  blackout,
  setBlackout,
  onComplete,
}: {
  environment: string;
  setEnvironment: (s: string) => void;
  blackout: boolean;
  setBlackout: (v: boolean) => void;
  onComplete: () => void;
}) {
  const [form, setForm] = useState({
    sleep: "7.5",
    mood: "4",
    exercise: "50",
    heart: "68",
    temp: "36.7",
    oxygen: "98",
    note: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const update = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    ["sleep", "mood", "exercise", "heart", "temp", "oxygen"].forEach((key) => {
      if (
        form[key as keyof typeof form] === "" ||
        Number.isNaN(Number(form[key as keyof typeof form]))
      )
        next[key] = "Enter a numeric reading.";
    });
    if (+form.mood < 1 || +form.mood > 5) next.mood = "Choose a value from 1 to 5.";
    setErrors(next);
    if (!Object.keys(next).length) {
      localStorage.setItem(
        "astropulse-last-checkin",
        JSON.stringify({ ...form, environment, blackout, date: new Date().toISOString() }),
      );
      onComplete();
    }
  };
  const fields = [
    {
      key: "sleep",
      label: "Sleep duration",
      unit: "hours",
      source: "Self-report",
      icon: "moon",
      step: ".1",
    },
    {
      key: "mood",
      label: "Mood & stress",
      unit: "out of 5",
      source: "Self-report",
      icon: "mood",
      step: "1",
    },
    {
      key: "exercise",
      label: "Exercise duration",
      unit: "minutes",
      source: "Self-report",
      icon: "activity",
      step: "1",
    },
    {
      key: "heart",
      label: "Resting heart rate",
      unit: "bpm",
      source: "Device measurement",
      icon: "heart",
      step: "1",
    },
    {
      key: "temp",
      label: "Body temperature",
      unit: "°C",
      source: "Device measurement",
      icon: "temp",
      step: ".1",
    },
    {
      key: "oxygen",
      label: "Blood oxygen",
      unit: "%",
      source: "Device measurement",
      icon: "oxygen",
      step: "1",
    },
  ];
  return (
    <div className="page-narrow">
      <SectionTitle
        eyebrow="Daily health record"
        title="Today’s check-in"
        action={
          <span className="privacy-chip">
            <Icon name="lock" /> Saved on this device
          </span>
        }
      />
      <p className="page-intro">
        Take a quiet moment to record how you are doing. This usually takes two minutes.
      </p>
      <form onSubmit={submit}>
        <section className="panel context-panel">
          <div className="form-section-head">
            <span>01</span>
            <div>
              <h3>Mission context</h3>
              <p>Questions and equipment notes adapt to your environment.</p>
            </div>
          </div>
          <div className="environment-options">
            {["Space Station", "Transit", "Rover", "Surface Base"].map((item) => (
              <button
                type="button"
                className={environment === item ? "selected" : ""}
                onClick={() => setEnvironment(item)}
                key={item}
              >
                <Icon name={item === "Rover" ? "activity" : "pulse"} />
                {item}
                <span className="radio-dot" />
              </button>
            ))}
          </div>
          <label className="toggle-row">
            <div>
              <strong>Communication blackout</strong>
              <span>Ground contact is currently unavailable</span>
            </div>
            <input
              type="checkbox"
              checked={blackout}
              onChange={(e) => setBlackout(e.target.checked)}
            />
            <span className="toggle" />
          </label>
          {blackout && (
            <div className="inline-note amber">
              <Icon name="relay" />
              <span>
                Your check-in will remain fully available and will be queued locally for later
                relay.
              </span>
            </div>
          )}
        </section>

        <section className="panel readings-panel">
          <div className="form-section-head">
            <span>02</span>
            <div>
              <h3>Six health signals</h3>
              <p>Review device readings and add your self-reported information.</p>
            </div>
          </div>
          <div className="form-grid">
            {fields.map((field) => (
              <label
                className={`field-card ${errors[field.key] ? "has-error" : ""}`}
                key={field.key}
              >
                <span className="field-icon">
                  <Icon name={field.icon} />
                </span>
                <span className="field-copy">
                  <strong>{field.label}</strong>
                  <small>{field.source}</small>
                </span>
                <span className="input-wrap">
                  <input
                    aria-label={field.label}
                    inputMode="decimal"
                    type="number"
                    step={field.step}
                    value={form[field.key as keyof typeof form]}
                    onChange={(e) => update(field.key, e.target.value)}
                  />
                  <em>{field.unit}</em>
                </span>
                {errors[field.key] && <span className="field-error">{errors[field.key]}</span>}
              </label>
            ))}
          </div>
          <div className="safe-note">
            <Icon name="info" />
            <p>
              <strong>Interpretation uses your personal pattern.</strong> AstroPulse does not apply
              unverified clinical thresholds. A baseline requires at least five readings within a
              14-day window.
            </p>
          </div>
        </section>

        <section className="panel note-panel">
          <div className="form-section-head">
            <span>03</span>
            <div>
              <h3>Personal note</h3>
              <p>Optional context can make later patterns easier to understand.</p>
            </div>
          </div>
          <textarea
            value={form.note}
            onChange={(e) => update("note", e.target.value)}
            placeholder="Anything affecting today’s readings, routine, or how you feel?"
            maxLength={280}
          />
          <span className="char-count">{form.note.length} / 280</span>
        </section>
        <div className="form-submit">
          <p>
            <Icon name="shield" /> Nothing is transmitted automatically.
          </p>
          <button className="button primary large" type="submit">
            Complete check-in <Icon name="arrow" />
          </button>
        </div>
      </form>
    </div>
  );
}

function Trends({ indicators }: { indicators: Indicator[] }) {
  const [active, setActive] = useState<IndicatorKey>("heart");
  const [table, setTable] = useState(false);
  const item = indicators.find((i) => i.key === active)!;
  return (
    <>
      <SectionTitle
        eyebrow="Personal history"
        title="Patterns, not snapshots"
        action={
          <button className="button ghost" onClick={() => setTable(!table)}>
            {table ? "Show chart" : "Readable data view"}
          </button>
        }
      />
      <p className="page-intro">
        Fourteen-day reference window · baseline available after five readings · all forecasts are
        uncertain projections.
      </p>
      <div className="trend-layout">
        <aside className="trend-list panel">
          {indicators.map((i) => (
            <button
              key={i.key}
              className={active === i.key ? "active" : ""}
              onClick={() => setActive(i.key)}
            >
              <span className="indicator-icon small">
                <Icon name={i.key === "sleep" ? "moon" : i.key} />
              </span>
              <span>
                <strong>{i.short}</strong>
                <small>
                  {i.value} {i.unit}
                </small>
              </span>
              <StatusPill status={i.status} compact />
            </button>
          ))}
        </aside>
        <section className="panel chart-panel">
          <div className="chart-head">
            <div>
              <span className="source-label">{item.source}</span>
              <h2>{item.label}</h2>
            </div>
            <StatusPill status={item.status} />
          </div>
          <div className="chart-reading">
            <strong>{item.value}</strong>
            <span>{item.unit}</span>
            <em>{item.change}</em>
          </div>
          {table ? (
            <div className="data-table" role="table" aria-label={`${item.label} underlying data`}>
              <div role="row">
                <strong>Date</strong>
                <strong>Reading</strong>
                <strong>Context</strong>
              </div>
              {item.values.slice(-7).map((v, i) => (
                <div role="row" key={i}>
                  <span>Mission day {36 + i}</span>
                  <span>
                    {v} {item.unit}
                  </span>
                  <span>{i === 6 ? "Current" : "Recorded"}</span>
                </div>
              ))}
            </div>
          ) : (
            <>
              <div className="large-chart">
                <div className="baseline-band">
                  <span>Personal baseline</span>
                </div>
                <Sparkline values={item.values} status={item.status} projected height={210} />
              </div>
              <div className="chart-legend">
                <span>
                  <i className="solid-line" />
                  Recorded readings
                </span>
                <span>
                  <i className="dash-line" />
                  Uncertain 4-day projection
                </span>
                <span>
                  <i className="band-line" />
                  Personal baseline band
                </span>
              </div>
            </>
          )}
          <div className="interpretation">
            <div>
              <p className="eyebrow">What this pattern says</p>
              <h3>{item.reason}</h3>
              <p>
                {item.status === "normal"
                  ? "No meaningful directional change is visible in this demonstration period."
                  : "The change appears gradual rather than sudden. Continue to observe the next readings."}
              </p>
            </div>
            <div className="baseline-card">
              <span>14-day personal baseline</span>
              <strong>{item.baseline}</strong>
              <small>Based on simulated history</small>
            </div>
          </div>
        </section>
      </div>
      {item.status !== "normal" && <Guidance item={item} />}
    </>
  );
}

function Guidance({ item }: { item: Indicator }) {
  return (
    <section className="guidance panel">
      <SectionTitle eyebrow="Decision support" title="Guidance for this signal" />
      <div className="guidance-grid">
        <article>
          <span>01</span>
          <h3>Status & reason</h3>
          <p>{item.reason}</p>
        </article>
        <article>
          <span>02</span>
          <h3>Likely contributors</h3>
          <p>No verified contributor guidance is loaded for this demonstration.</p>
        </article>
        <article>
          <span>03</span>
          <h3>What you can do</h3>
          <p>Follow your current mission procedures. Approved action guidance is not loaded.</p>
        </article>
        <article>
          <span>04</span>
          <h3>Measure again in</h3>
          <p>No verified remeasurement interval is available. Use mission procedures.</p>
        </article>
        <article>
          <span>05</span>
          <h3>When to contact ground</h3>
          <p>
            Refer to verified mission procedures; this prototype does not invent escalation rules.
          </p>
        </article>
        <article>
          <span>06</span>
          <h3>Sources</h3>
          <p>Verified project-team sources have not yet been connected.</p>
        </article>
      </div>
    </section>
  );
}

function Relay({
  indicators,
  environment,
  blackout,
}: {
  indicators: Indicator[];
  environment: string;
  blackout: boolean;
}) {
  const flagged = indicators.filter((i) => i.status !== "normal");
  const [resolved, setResolved] = useState<string[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [actions, setActions] = useState<string[]>(() =>
    JSON.parse(localStorage.getItem("astropulse-actions") || "[]"),
  );
  const [action, setAction] = useState("");
  const [showExport, setShowExport] = useState(false);
  const addAction = () => {
    if (!action.trim()) return;
    const next = [...actions, action.trim()];
    setActions(next);
    setAction("");
    localStorage.setItem("astropulse-actions", JSON.stringify(next));
  };
  const summary = `ASTROPULSE GROUND RELAY — SIMULATED
Reporting period: Mission day 42
Environment: ${environment}
Communication: ${blackout ? "Blackout — queued locally" : "Available"}

FLAGGED INDICATORS
${flagged.length ? flagged.map((i) => `- ${i.label}: ${statusMeta[i.status].label}. ${i.reason}${notes[i.key] ? ` Note: ${notes[i.key]}` : ""}`).join("\n") : "- No indicators currently flagged."}

ACTIONS RECORDED
${actions.length ? actions.map((a) => `- ${a}`).join("\n") : "- No actions recorded."}

UNRESOLVED
${
  flagged
    .filter((i) => !resolved.includes(i.key))
    .map((i) => `- ${i.label}`)
    .join("\n") || "- None"
}

Decision support, not a diagnosis.
Generated locally. Export was explicitly requested by the user.`;
  const download = () => {
    const blob = new Blob([summary], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "astropulse-relay-summary.txt";
    a.click();
    URL.revokeObjectURL(url);
    setShowExport(false);
  };
  return (
    <>
      <SectionTitle
        eyebrow="Ground relay"
        title="Concerns stay queued until you choose"
        action={
          <span className={`connection-chip ${blackout ? "offline" : ""}`}>
            <span />
            {blackout ? "Blackout · local only" : "Ground link available"}
          </span>
        }
      />
      <p className="page-intro">
        Review, annotate, and resolve concerns. AstroPulse never sends health information
        automatically.
      </p>
      <div className="relay-layout">
        <section>
          <div className="relay-heading">
            <h2>Flagged signals</h2>
            <span>{flagged.filter((i) => !resolved.includes(i.key)).length} open</span>
          </div>
          {flagged.length ? (
            flagged.map((item) => (
              <article
                className={`panel concern-card ${resolved.includes(item.key) ? "resolved" : ""}`}
                key={item.key}
              >
                <div className="concern-main">
                  <span className="indicator-icon">
                    <Icon name={item.key === "sleep" ? "moon" : item.key} />
                  </span>
                  <div>
                    <div className="concern-title">
                      <h3>{item.label}</h3>
                      <StatusPill status={item.status} />
                    </div>
                    <p>{item.reason}</p>
                    <span className="concern-reading">
                      {item.value} {item.unit} · {item.change}
                    </span>
                  </div>
                </div>
                <label>
                  <span>Private relay note</span>
                  <textarea
                    value={notes[item.key] || ""}
                    onChange={(e) => setNotes({ ...notes, [item.key]: e.target.value })}
                    placeholder="Add context for ground support…"
                  />
                </label>
                <button
                  className="button ghost"
                  onClick={() =>
                    setResolved((r) =>
                      r.includes(item.key) ? r.filter((x) => x !== item.key) : [...r, item.key],
                    )
                  }
                >
                  <Icon name="check" />
                  {resolved.includes(item.key) ? "Reopen concern" : "Mark resolved"}
                </button>
              </article>
            ))
          ) : (
            <div className="panel empty-state">
              <Icon name="check" size={30} />
              <h3>No signals are currently flagged</h3>
              <p>New concerns will appear here for review.</p>
            </div>
          )}
        </section>
        <aside>
          <section className="panel action-log">
            <h2>Action log</h2>
            <p>Record participation only—not health outcomes.</p>
            <div className="action-input">
              <input
                value={action}
                onChange={(e) => setAction(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addAction()}
                placeholder="Action taken…"
              />
              <button onClick={addAction} aria-label="Add action">
                <Icon name="plus" />
              </button>
            </div>
            <ul>
              {actions.map((a, i) => (
                <li key={i}>
                  <Icon name="check" />
                  <span>{a}</span>
                  <small>Today</small>
                </li>
              ))}
            </ul>
          </section>
          <section className="export-card">
            <Icon name="lock" />
            <h2>Plain-text relay</h2>
            <p>Preview a local summary before choosing to export it from this device.</p>
            <button className="button light" onClick={() => setShowExport(true)}>
              <Icon name="download" /> Review export
            </button>
          </section>
        </aside>
      </div>
      {showExport && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Review relay export"
        >
          <div className="modal">
            <div className="modal-head">
              <div>
                <p className="eyebrow">Explicit export</p>
                <h2>Review relay summary</h2>
              </div>
              <button onClick={() => setShowExport(false)} aria-label="Close">
                <Icon name="close" />
              </button>
            </div>
            <pre>{summary}</pre>
            <div className="modal-actions">
              <button className="button ghost" onClick={() => setShowExport(false)}>
                Cancel
              </button>
              <button className="button primary" onClick={download}>
                <Icon name="download" /> Export .txt file
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Progress() {
  const actions: string[] = JSON.parse(localStorage.getItem("astropulse-actions") || "[]");
  const days = [
    { d: "M", done: true },
    { d: "T", done: true },
    { d: "W", done: true },
    { d: "T", done: false },
    { d: "F", done: true },
    { d: "S", done: true },
    { d: "S", done: false },
  ];
  return (
    <>
      <SectionTitle eyebrow="Mission rhythm" title="Consistency builds useful context" />
      <p className="page-intro">
        Progress reflects check-ins and recorded actions only. Health outcomes never affect your
        score.
      </p>
      <div className="progress-hero">
        <div>
          <span className="big-number">5</span>
          <div>
            <strong>day streak</strong>
            <small>Current check-in rhythm</small>
          </div>
        </div>
        <p>
          Five recent check-ins give your personal pattern more context. Missing a day simply means
          you can continue when ready.
        </p>
      </div>
      <div className="stat-grid">
        <div className="panel stat">
          <span>Longest streak</span>
          <strong>
            11 <small>days</small>
          </strong>
          <p>Personal best this mission</p>
        </div>
        <div className="panel stat">
          <span>This week</span>
          <strong>
            5 <small>of 7</small>
          </strong>
          <p>Check-ins completed</p>
        </div>
        <div className="panel stat">
          <span>Actions logged</span>
          <strong>{actions.length || 3}</strong>
          <p>Participation actions recorded</p>
        </div>
      </div>
      <section className="panel weekly-panel">
        <SectionTitle
          eyebrow="Current week"
          title="Your check-in rhythm"
          action={<span className="neutral-chip">71% complete</span>}
        />
        <div className="week-track">
          {days.map((day, i) => (
            <div className={day.done ? "done" : ""} key={i}>
              <span>{day.done ? <Icon name="check" /> : i === 6 ? "—" : "·"}</span>
              <strong>{day.d}</strong>
              <small>{i === 6 ? "Upcoming" : day.done ? "Complete" : "No entry"}</small>
            </div>
          ))}
          <div className="track-line">
            <i style={{ width: "71%" }} />
          </div>
        </div>
      </section>
      <section className="progress-principle">
        <Icon name="shield" size={28} />
        <div>
          <h3>Participation, never performance</h3>
          <p>
            AstroPulse acknowledges the habit of checking in and recording actions. It never rewards
            “good” readings or penalises difficult health days.
          </p>
        </div>
      </section>
    </>
  );
}

function App() {
  const [page, setPage] = useState<Page>("today");
  const [scenario, setScenario] = useState<Scenario>("Drift Day 6");
  const [environment, setEnvironment] = useState("Space Station");
  const [blackout, setBlackout] = useState(false);
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [toast, setToast] = useState("");
  const indicators = useMemo(() => buildIndicators(scenario), [scenario]);

  useEffect(() => {
    if (scenario === "Fever Blackout") setBlackout(true);
    else setBlackout(false);
  }, [scenario]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    setMobileNav(false);
  }, [page]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  const nav: Array<{ page: Page; label: string; icon: string }> = [
    { page: "today", label: "Today", icon: "grid" },
    { page: "checkin", label: "Check-in", icon: "check" },
    { page: "trends", label: "Trends", icon: "trend" },
    { page: "relay", label: "Ground relay", icon: "relay" },
    { page: "progress", label: "Progress", icon: "progress" },
  ];
  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setPage("today")} aria-label="AstroPulse home">
          <span className="brand-mark">
            <Icon name="pulse" size={24} />
          </span>
          <span>
            <strong>ASTRO</strong>PULSE
          </span>
        </button>
        <div className="topbar-status">
          <span className="local-status">
            <i /> LOCAL SYSTEM
          </span>
          <span className="mission-time">MD 042&nbsp;&nbsp;·&nbsp;&nbsp;14:32 UTC</span>
        </div>
        <button
          className="mobile-menu"
          onClick={() => setMobileNav(!mobileNav)}
          aria-label="Toggle menu"
        >
          <Icon name="menu" />
        </button>
      </header>
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <nav aria-label="Main navigation">
          <p>MISSION HEALTH</p>
          {nav.map((item) => (
            <button
              key={item.page}
              className={page === item.page ? "active" : ""}
              onClick={() => setPage(item.page)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.page === "relay" && indicators.some((i) => i.status !== "normal") && (
                <em>{indicators.filter((i) => i.status !== "normal").length}</em>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="scenario-control">
            <p>DEMONSTRATION</p>
            <button className="scenario-button" onClick={() => setScenarioOpen(!scenarioOpen)}>
              <span>
                <small>SIMULATED</small>
                <strong>{scenario}</strong>
              </span>
              <Icon name="chevron" />
            </button>
            {scenarioOpen && (
              <div className="scenario-menu">
                {(Object.keys(scenarioCopy) as Scenario[]).map((s) => (
                  <button
                    className={scenario === s ? "active" : ""}
                    key={s}
                    onClick={() => {
                      setScenario(s);
                      setScenarioOpen(false);
                    }}
                  >
                    <strong>{s}</strong>
                    <span>{scenarioCopy[s]}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="privacy-note">
            <Icon name="lock" />
            <span>
              <strong>Device-only storage</strong>
              <small>No automatic transmission</small>
            </span>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <div className="sim-strip">
          <span>SIMULATED DATA</span>
          <p>{scenarioCopy[scenario]}</p>
        </div>
        {page === "today" && (
          <Dashboard
            indicators={indicators}
            scenario={scenario}
            environment={environment}
            blackout={blackout}
            setPage={setPage}
          />
        )}
        {page === "checkin" && (
          <CheckIn
            environment={environment}
            setEnvironment={setEnvironment}
            blackout={blackout}
            setBlackout={setBlackout}
            onComplete={() => {
              setToast("Check-in saved locally");
              setPage("today");
            }}
          />
        )}
        {page === "trends" && <Trends indicators={indicators} />}
        {page === "relay" && (
          <Relay indicators={indicators} environment={environment} blackout={blackout} />
        )}
        {page === "progress" && <Progress />}
        <footer>
          <span>ASTROPULSE · OFFLINE-FIRST MISSION HEALTH</span>
          <strong>Decision support, not a diagnosis.</strong>
          <span>Records remain on this device</span>
        </footer>
      </main>
      {toast && (
        <div className="toast">
          <Icon name="check" />
          <span>
            <strong>{toast}</strong>
            <small>Nothing was transmitted.</small>
          </span>
        </div>
      )}
    </div>
  );
}

export default App;
