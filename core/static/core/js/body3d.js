/* AstroPulse optional 3D body view.
 *
 * The 2D SVG body map is the primary view and stays in the document at all
 * times. This module only builds a Three.js scene after the user presses the
 * "3D view" toggle, using the locally vendored Three.js build and the local
 * .glb model. Nothing is downloaded from the network.
 *
 * Severity colours come from the CSS custom property that app.css sets on the
 * SVG region groups, so no severity thresholds or clinical values live here.
 * Severity is always icon + text + colour, never colour alone.
 *
 * Style note: block comments only. The offline safety test treats
 * "slash slash" followed by a letter as a protocol-relative URL.
 */

const REGION_GEOMETRY = [
  { id: "head", points: [[0, 4.16, 0.24]], radius: 0.3 },
  { id: "chest", points: [[0.18, 3.33, 0.3]], radius: 0.28 },
  {
    id: "lungs",
    points: [
      [-0.4, 3.22, 0.21],
      [0.4, 3.22, 0.21],
    ],
    radius: 0.25,
  },
  { id: "torso", points: [[0, 2.68, 0.26]], radius: 0.32 },
  {
    id: "legs",
    points: [
      [-0.25, 1.43, 0.19],
      [0.25, 1.43, 0.19],
    ],
    radius: 0.35,
  },
];

const toggle = document.querySelector("[data-view-toggle]");
const mount = document.getElementById("body3d");
const svgMap = document.getElementById("bodymap");
const statusLine = document.getElementById("view3d-status");

let cleanup = null;
let active = false;
let busy = false;

function announce(text) {
  if (statusLine) {
    statusLine.textContent = text;
  }
}

function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function supportsWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl2") || canvas.getContext("webgl")
    );
  } catch (error) {
    return false;
  }
}

function regionMeta(id) {
  const group = document.getElementById("bm-" + id);
  if (!group) {
    return { label: id, word: id, color: "#9AA5B8" };
  }
  const severityClass = Array.from(group.classList).find((name) =>
    name.startsWith("sev-")
  );
  const severity = severityClass ? severityClass.slice(4) : "gray";
  const aria = group.getAttribute("aria-label") || "";
  const parts = aria.split(" — ");
  const label = (parts[0] || id).trim();
  const wordMatch = /\(([^)]+)\)\s*$/.exec(parts[1] || "");
  const word = wordMatch ? wordMatch[1] : severity;
  const color =
    getComputedStyle(group).getPropertyValue("--region-color").trim() ||
    "#9AA5B8";
  const icon = group.querySelector(".bm-label svg");
  return {
    label,
    word,
    severity,
    color,
    icon: icon ? icon.cloneNode(true) : null,
    textColor: getComputedStyle(group).color,
  };
}

function buildLabel(id, meta) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "body3d-label";
  button.dataset.region = id;
  button.style.color = meta.textColor || "";
  button.setAttribute("aria-label", meta.label + ": " + meta.word);

  if (meta.icon) {
    const iconWrap = document.createElement("span");
    iconWrap.className = "sev-icon";
    iconWrap.setAttribute("aria-hidden", "true");
    iconWrap.appendChild(meta.icon);
    button.appendChild(iconWrap);
  }

  const text = document.createElement("span");
  const name = document.createElement("strong");
  name.textContent = meta.label;
  const value = document.createElement("small");
  value.textContent = meta.word;
  text.append(name, " ", value);
  button.appendChild(text);

  button.addEventListener("click", () => selectRegion(id));
  return button;
}

function selectRegion(id) {
  const group = document.getElementById("bm-" + id);
  if (!group) {
    return;
  }
  group.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}

async function enable(onFatal) {
  if (!mount) {
    return;
  }
  if (!supportsWebGL()) {
    throw new Error("webgl-unavailable");
  }

  const THREE = await import("three");
  const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
  const { OrbitControls } = await import(
    "three/addons/controls/OrbitControls.js"
  );

  const viewport = document.createElement("div");
  viewport.className = "body3d-viewport";

  const loading = document.createElement("div");
  loading.className = "model-loading";
  loading.textContent = "Loading local body model…";
  viewport.appendChild(loading);

  const badge = document.createElement("span");
  badge.className = "simulated-map-badge";
  badge.textContent = "SIMULATED";
  viewport.appendChild(badge);

  const resetButton = document.createElement("button");
  resetButton.type = "button";
  resetButton.className = "reset-view";
  resetButton.textContent = "Reset view";
  viewport.appendChild(resetButton);

  const labelLayer = document.createElement("div");
  labelLayer.className = "body3d-labels";
  viewport.appendChild(labelLayer);

  const toolbar = document.createElement("div");
  toolbar.className = "body3d-toolbar";
  const hint = document.createElement("p");
  hint.className = "body3d-hint";
  hint.textContent = "Drag to orbit. Scroll or pinch to zoom.";
  toolbar.appendChild(hint);

  mount.replaceChildren(viewport, toolbar);

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (error) {
    throw new Error("webgl-unavailable");
  }

  const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 100);
  camera.position.set(0, 2.35, 7.2);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 2.3, 0);
  controls.enableDamping = !reducedMotion();
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
  renderer.domElement.className = "body3d-canvas";
  renderer.domElement.setAttribute("aria-hidden", "true");
  viewport.prepend(renderer.domElement);

  const scene = new THREE.Scene();
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

  const hitMaterial = new THREE.MeshBasicMaterial({
    transparent: true,
    opacity: 0.001,
    depthWrite: false,
  });

  const targets = new Map();
  const rings = new Map();
  const labels = new Map();
  const labelMeta = new Map();

  REGION_GEOMETRY.forEach((region) => {
    labelMeta.set(region.id, regionMeta(region.id));

    const regionTargets = [];
    region.points.forEach((point) => {
      const hit = new THREE.Mesh(
        new THREE.SphereGeometry(region.radius, 18, 12),
        hitMaterial.clone()
      );
      hit.position.set(point[0], point[1], point[2]);
      hit.userData.region = region.id;
      scene.add(hit);
      regionTargets.push(hit);
    });
    targets.set(region.id, regionTargets);

    const color = labelMeta.get(region.id).color;
    const regionRings = [];
    region.points.forEach((point) => {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(region.radius * 0.72, 0.022, 10, 48),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(color),
          transparent: true,
          opacity: 0.8,
          depthTest: false,
        })
      );
      ring.position.set(point[0], point[1], point[2] + 0.02);
      ring.renderOrder = 4;
      scene.add(ring);
      regionRings.push(ring);
    });
    rings.set(region.id, regionRings);
  });

  REGION_GEOMETRY.forEach((region) => {
    const label = buildLabel(region.id, labelMeta.get(region.id));
    labelLayer.appendChild(label);
    labels.set(region.id, label);
  });

  const loader = new GLTFLoader();
  const modelUrl = mount.dataset.modelUrl;

  loader.load(
    modelUrl,
    (gltf) => {
      gltf.scene.traverse((child) => {
        if (child.isMesh) {
          if (child.material) {
            const old = Array.isArray(child.material)
              ? child.material
              : [child.material];
            old.forEach((material) => material.dispose());
          }
          child.material = new THREE.MeshStandardMaterial({
            color: 0xc6ccd8,
            roughness: 0.72,
            metalness: 0.03,
          });
        }
      });
      scene.add(gltf.scene);
      loading.remove();
    },
    undefined,
    () => {
      onFatal("3D model could not be loaded. Accessible body map shown.");
    }
  );

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  const pick = (event) => {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    raycaster.setFromCamera(pointer, camera);
    const everything = Array.from(targets.values()).flat();
    const hit = raycaster
      .intersectObjects(everything, false)
      .find((result) => result.object.userData.region);
    return hit ? hit.object.userData.region : null;
  };

  let hovered = null;

  const onMove = (event) => {
    hovered = pick(event);
    renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
  };

  const onClick = (event) => {
    const region = pick(event);
    if (region) {
      selectRegion(region);
    }
  };

  renderer.domElement.addEventListener("pointermove", onMove);
  renderer.domElement.addEventListener("click", onClick);

  const resize = () => {
    const width = viewport.clientWidth;
    const height = viewport.clientHeight;
    if (!width || !height) {
      return;
    }
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  };

  const observer = new ResizeObserver(resize);
  observer.observe(viewport);
  resize();

  const resetView = () => {
    camera.position.set(0, 2.35, 7.2);
    controls.target.set(0, 2.3, 0);
    controls.update();
  };
  resetButton.addEventListener("click", resetView);

  const centers = new Map(
    REGION_GEOMETRY.map((region) => {
      const center = region.points
        .reduce(
          (sum, point) => sum.add(new THREE.Vector3(point[0], point[1], point[2])),
          new THREE.Vector3()
        )
        .multiplyScalar(1 / region.points.length);
      return [region.id, center];
    })
  );

  let frame = 0;
  let disposed = false;

  const render = () => {
    if (disposed) {
      return;
    }
    frame = requestAnimationFrame(render);
    controls.update();

    REGION_GEOMETRY.forEach((region) => {
      const activeRegion = region.id === hovered;
      rings.get(region.id).forEach((ring) => {
        ring.material.opacity = activeRegion ? 1 : 0.72;
      });

      const label = labels.get(region.id);
      const center = centers.get(region.id);
      if (!label || !center) {
        return;
      }
      const toCamera = camera.position.clone().sub(center).normalize();
      const facing = toCamera.dot(new THREE.Vector3(0, 0, 1)) > 0.12;
      const projected = center.clone().project(camera);
      label.style.setProperty(
        "--label-x",
        ((projected.x * 0.5 + 0.5) * 100).toFixed(2) + "%"
      );
      label.style.setProperty(
        "--label-y",
        ((-projected.y * 0.5 + 0.5) * 100).toFixed(2) + "%"
      );
      label.hidden = !facing || projected.z > 1;
    });

    renderer.render(scene, camera);
  };

  render();

  return function teardown() {
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    renderer.domElement.removeEventListener("pointermove", onMove);
    renderer.domElement.removeEventListener("click", onClick);
    resetButton.removeEventListener("click", resetView);
    controls.dispose();
    renderer.dispose();
    hitMaterial.dispose();
    scene.traverse((object) => {
      if (!object.isMesh) {
        return;
      }
      if (object.geometry) {
        object.geometry.dispose();
      }
      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];
      materials.forEach((material) => {
        if (!material) {
          return;
        }
        Object.keys(material).forEach((name) => {
          const value = material[name];
          if (value && value.isTexture) {
            value.dispose();
          }
        });
        material.dispose();
      });
    });
    mount.replaceChildren();
  };
}

function failToSvg(message) {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  active = false;
  if (toggle) {
    toggle.setAttribute("aria-pressed", "false");
    toggle.disabled = true;
    toggle.textContent = "3D view unavailable";
  }
  if (svgMap) {
    svgMap.hidden = false;
  }
  if (mount) {
    mount.hidden = true;
  }
  announce(message);
}

async function turnOn() {
  if (busy) {
    return;
  }
  busy = true;
  try {
    cleanup = await enable(failToSvg);
    active = true;
    toggle.setAttribute("aria-pressed", "true");
    if (svgMap) {
      svgMap.hidden = true;
    }
    announce("3D view shown.");
  } catch (error) {
    failToSvg("3D view unavailable. Accessible body map shown.");
  } finally {
    busy = false;
  }
}

function turnOff() {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  active = false;
  toggle.setAttribute("aria-pressed", "false");
  if (svgMap) {
    svgMap.hidden = false;
  }
  if (mount) {
    mount.hidden = true;
  }
  announce("Accessible body map shown.");
}

if (toggle && mount) {
  toggle.hidden = false;
  if (!supportsWebGL()) {
    toggle.disabled = true;
    toggle.textContent = "3D view unavailable";
  } else {
    toggle.addEventListener("click", () => {
      if (active) {
        turnOff();
      } else {
        mount.hidden = false;
        turnOn();
      }
    });
  }
}
