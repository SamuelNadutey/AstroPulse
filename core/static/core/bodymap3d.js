(function () {
  "use strict";

  const root = document.querySelector("[data-bodymap-widget]");
  const library = window.AstroBody;
  if (!root || !library) return;

  const { THREE, GLTFLoader, OrbitControls } = library;
  const stage = root.querySelector("[data-three-stage]");
  const svgFallback = root.querySelector("[data-svg-fallback]");
  const fallbackNote = root.querySelector("[data-webgl-fallback]");
  const mount = root.querySelector("[data-three-canvas]");
  const loading = root.querySelector("[data-three-loading]");
  const announcement = root.querySelector("[data-bodymap-announcement]");
  const statusNode = document.getElementById("body-region-data");
  if (!stage || !svgFallback || !mount || !statusNode) return;

  let regions;
  try {
    regions = JSON.parse(statusNode.textContent);
  } catch (_) {
    return;
  }
  if (!Array.isArray(regions) || !regions.length) return;

  const statusOrder = ["gray", "green", "yellow", "orange", "red"];
  const statusColors = {
    gray: "--status-insufficient",
    green: "--status-normal",
    yellow: "--status-watch",
    orange: "--status-concern",
    red: "--status-contact",
  };
  const regionShapes = {
    head: { points: [[0, 4.16, 0.24]], radius: 0.3 },
    chest: { points: [[0.18, 3.33, 0.3]], radius: 0.28 },
    lungs: { points: [[-0.4, 3.22, 0.21], [0.4, 3.22, 0.21]], radius: 0.25 },
    torso: { points: [[0, 2.68, 0.26]], radius: 0.32 },
    legs: { points: [[-0.25, 1.43, 0.19], [0.25, 1.43, 0.19]], radius: 0.35 },
  };
  const computed = getComputedStyle(document.documentElement);
  regions.forEach(function (region) {
    region.color = computed.getPropertyValue(statusColors[region.severity] || statusColors.gray).trim();
  });

  let renderer;
  let controls;
  let scene;
  let camera;
  let resizeObserver;
  let animationFrame = 0;
  let cameraAnimationFrame = 0;
  let activeRegion = null;
  let dragged = false;
  let pointerStart = null;
  const ringMeshes = new Map();
  const hitMeshes = [];
  const labels = new Map();

  function cleanUp() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    if (cameraAnimationFrame) cancelAnimationFrame(cameraAnimationFrame);
    if (resizeObserver) resizeObserver.disconnect();
    if (controls) controls.dispose();
    if (scene) {
      scene.traverse(function (object) {
        if (!(object instanceof THREE.Mesh)) return;
        object.geometry.dispose();
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(function (material) { material.dispose(); });
      });
    }
    if (renderer) {
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.dispose();
      renderer.domElement.remove();
    }
    renderer = null;
    controls = null;
    camera = null;
    scene = null;
    resizeObserver = null;
  }

  function failToSvg() {
    cleanUp();
    stage.hidden = true;
    svgFallback.hidden = false;
    if (fallbackNote) fallbackNote.hidden = false;
  }

  function makeStatusMarker(region) {
    const marker = document.createElement("span");
    marker.className = "body3d-status-marker marker-" + region.severity;
    marker.setAttribute("aria-hidden", "true");
    const mark = document.createElement("span");
    mark.className = "body3d-status-shape";
    if (region.severity === "red") mark.textContent = "!";
    marker.appendChild(mark);
    return marker;
  }

  function createLabels() {
    const left = stage.querySelector('[data-label-gutter="left"]');
    const right = stage.querySelector('[data-label-gutter="right"]');
    regions.forEach(function (region) {
      const label = document.createElement("button");
      label.type = "button";
      label.className = "body3d-label";
      label.dataset.region = region.name;
      label.setAttribute("aria-label", region.label + ": " + region.word);
      const copy = document.createElement("span");
      copy.className = "body3d-label-copy";
      const name = document.createElement("strong");
      name.textContent = region.label;
      const status = document.createElement("small");
      status.textContent = region.word;
      copy.append(name, status);
      label.append(makeStatusMarker(region), copy);
      (left && right ? left : stage).appendChild(label);
      labels.set(region.name, label);
    });
  }

  function announce(region) {
    if (!announcement || !region) return;
    announcement.textContent = region.label + " selected. " + region.word + ".";
  }

  function focusRegion(regionName) {
    const geometry = regionShapes[regionName];
    if (!geometry || !camera || !controls) return;
    if (cameraAnimationFrame) cancelAnimationFrame(cameraAnimationFrame);
    const center = geometry.points.reduce(function (sum, point) {
      return sum.add(new THREE.Vector3(point[0], point[1], point[2]));
    }, new THREE.Vector3()).multiplyScalar(1 / geometry.points.length);
    const destination = new THREE.Vector3(center.x, center.y + 0.05, center.z + 4.4);
    const fromPosition = camera.position.clone();
    const fromTarget = controls.target.clone();
    const start = performance.now();
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 520;
    function move(now) {
      const raw = duration ? Math.min(1, (now - start) / duration) : 1;
      const eased = 1 - Math.pow(1 - raw, 3);
      camera.position.lerpVectors(fromPosition, destination, eased);
      controls.target.lerpVectors(fromTarget, center, eased);
      controls.update();
      if (raw < 1) cameraAnimationFrame = requestAnimationFrame(move);
      else cameraAnimationFrame = 0;
    }
    if (duration) cameraAnimationFrame = requestAnimationFrame(move);
    else move(start);
  }

  function clickRegion(regionName) {
    const region = regions.find(function (item) { return item.name === regionName; });
    if (!region) return;
    activeRegion = regionName;
    announce(region);
    const regionButton = root.querySelector('.region-select[data-region="' + regionName + '"]');
    if (regionButton) regionButton.click();
  }

  root.addEventListener("click", function (event) {
    const control = event.target.closest("[data-region]");
    if (!control || !root.contains(control)) return;
    const regionName = control.dataset.region;
    if (control.classList.contains("body3d-label")) {
      event.preventDefault();
      clickRegion(regionName);
      return;
    }
    const region = regions.find(function (item) { return item.name === regionName; });
    if (region) {
      activeRegion = regionName;
      announce(region);
      focusRegion(regionName);
    }
  });

  function updateMarkerAppearance() {
    ringMeshes.forEach(function (rings, regionName) {
      rings.forEach(function (ring) {
        const material = ring.material;
        material.opacity = activeRegion === regionName ? 1 : 0.72;
      });
    });
  }

  function onPointerDown(event) {
    dragged = false;
    pointerStart = [event.clientX, event.clientY];
  }

  function pickRegion(event) {
    const bounds = renderer.domElement.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return null;
    const pointer = new THREE.Vector2(
      ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
      -((event.clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(pointer, camera);
    const intersection = raycaster.intersectObjects(hitMeshes, false).find(function (hit) {
      return hit.object.userData.region;
    });
    return intersection ? intersection.object.userData.region : null;
  }

  function onPointerMove(event) {
    if (pointerStart && Math.hypot(event.clientX - pointerStart[0], event.clientY - pointerStart[1]) > 5) dragged = true;
    const regionName = pickRegion(event);
    renderer.domElement.style.cursor = regionName ? "pointer" : "grab";
    if (regionName && !dragged) {
      const label = labels.get(regionName);
      if (label) label.classList.add("hovered");
    } else {
      labels.forEach(function (label) { label.classList.remove("hovered"); });
    }
  }

  function onPointerUp(event) {
    if (!dragged) {
      const regionName = pickRegion(event);
      if (regionName) clickRegion(regionName);
    }
    pointerStart = null;
  }

  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0xffffff, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.className = "body3d-canvas-element";
    renderer.domElement.setAttribute("aria-hidden", "true");
    mount.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(31, 1, 0.1, 100);
    camera.position.set(0, 2.35, 7.2);
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 2.3, 0);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    controls.enableDamping = !reducedMotion;
    controls.dampingFactor = 0.07;
    controls.enablePan = false;
    controls.minDistance = 3.2;
    controls.maxDistance = 9;
    controls.minPolarAngle = Math.PI * 0.28;
    controls.maxPolarAngle = Math.PI * 0.68;
    controls.rotateSpeed = 0.65;
    controls.zoomSpeed = 0.7;
    controls.update();

    scene.add(new THREE.HemisphereLight(0xd9e6ff, 0x182031, 1.7));
    const keyLight = new THREE.DirectionalLight(0xe8f2ff, 3.2);
    keyLight.position.set(3.5, 5.5, 5);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x6cb4ff, 1.8);
    fillLight.position.set(-4, 3, 3);
    scene.add(fillLight);
    const rimLight = new THREE.DirectionalLight(0x9fb7dc, 2.4);
    rimLight.position.set(2, 4, -4);
    scene.add(rimLight);

    regions.forEach(function (region) {
      const geometry = regionShapes[region.name];
      if (!geometry) return;
      const hitSpheres = [];
      const rings = [];
      geometry.points.forEach(function (point) {
        const sphere = new THREE.Mesh(
          new THREE.SphereGeometry(geometry.radius, 18, 12),
          new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.001, depthWrite: false }),
        );
        sphere.position.set(point[0], point[1], point[2]);
        sphere.userData.region = region.name;
        sphere.userData.regionPoint = true;
        scene.add(sphere);
        hitSpheres.push(sphere);
        hitMeshes.push(sphere);

        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(geometry.radius * 0.72, 0.022, 10, 48),
          new THREE.MeshBasicMaterial({ color: region.color || "#6b7a75", transparent: true, opacity: 0.72, depthTest: false }),
        );
        ring.position.set(point[0], point[1], point[2] + 0.02);
        ring.renderOrder = 4;
        scene.add(ring);
        rings.push(ring);
      });
      ringMeshes.set(region.name, rings);
    });
    createLabels();

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup", onPointerUp);

    const loader = new GLTFLoader();
    loader.load(root.dataset.modelUrl, function (gltf) {
      gltf.scene.traverse(function (child) {
        if (child instanceof THREE.Mesh) {
          child.material = new THREE.MeshStandardMaterial({ color: 0xc6ccd8, roughness: 0.72, metalness: 0.03 });
        }
      });
      scene.add(gltf.scene);
      stage.hidden = false;
      svgFallback.hidden = true;
      if (loading) loading.hidden = true;
      if (window.htmx) window.htmx.process(stage);

      function resize() {
        const bounds = mount.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        renderer.setSize(bounds.width, bounds.height, false);
        camera.aspect = bounds.width / bounds.height;
        camera.updateProjectionMatrix();
      }
      if ("ResizeObserver" in window) {
        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(stage);
      } else {
        window.addEventListener("resize", resize);
      }
      resize();

      function updateLabelPositions() {
        const groups = { left: [], right: [] };
        regions.forEach(function (region) {
          const geometry = regionShapes[region.name];
          const label = labels.get(region.name);
          if (!geometry || !label) return;
          const center = geometry.points.reduce(function (sum, point) {
            return sum.add(new THREE.Vector3(point[0], point[1], point[2]));
          }, new THREE.Vector3()).multiplyScalar(1 / geometry.points.length);
          const projected = center.clone().project(camera);
          const viewPoint = center.clone().sub(camera.position).normalize();
          const facing = viewPoint.dot(new THREE.Vector3(0, 0, -1)) < -0.12;
          const side = projected.x < 0 ? "left" : "right";
          const targetY = (projected.y * -0.5 + 0.5) * stage.clientHeight;
          label.dataset.side = side;
          label.hidden = !facing || projected.z < -1 || projected.z > 1;
          const gutter = stage.querySelector('[data-label-gutter="' + side + '"]');
          if (gutter && label.parentElement !== gutter) gutter.appendChild(label);
          groups[side].push({ label, targetY });
        });
        Object.keys(groups).forEach(function (side) {
          const items = groups[side].filter(function (item) { return !item.label.hidden; }).sort(function (a, b) { return a.targetY - b.targetY; });
          const gutter = stage.querySelector('[data-label-gutter="' + side + '"]');
          if (!gutter) return;
          const height = gutter.clientHeight || stage.clientHeight;
          const gap = 58;
          items.forEach(function (item, index) {
            const min = 25 + index * gap;
            const max = Math.max(min, height - 34 - (items.length - index - 1) * gap);
            const y = Math.max(min, Math.min(max, item.targetY));
            item.label.style.top = y + "px";
          });
        });
      }

      function animate() {
        animationFrame = requestAnimationFrame(animate);
        controls.update();
        updateMarkerAppearance();
        updateLabelPositions();
        renderer.render(scene, camera);
      }
      animate();
    }, undefined, failToSvg);

    stage.querySelector("[data-reset-view]").addEventListener("click", function () {
      if (cameraAnimationFrame) cancelAnimationFrame(cameraAnimationFrame);
      cameraAnimationFrame = 0;
      camera.position.set(0, 2.35, 7.2);
      controls.target.set(0, 2.3, 0);
      controls.update();
    });
  } catch (_) {
    failToSvg();
  }
})();
