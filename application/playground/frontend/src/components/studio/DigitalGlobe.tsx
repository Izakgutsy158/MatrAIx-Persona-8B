/**
 * Digital-twin Earth for Home: persona-cloud continents, HUD grid,
 * pulsing hubs, and data packets along innovation corridors.
 * Two palettes: muted slate-blue on dark, ink-on-paper on light.
 */
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useIsLightTheme } from "../../hooks/useIsLightTheme";

/**
 * Cloudless Blue Marble: land/ocean split by color, so lowland plains
 * (Amazon basin, Ganges plain, …) are kept — unlike an elevation map.
 */
const EARTH_URL = "/earth/day.jpg";

/** Same axes as the land point-cloud: north up, negative z so east is right. */
function latLonToVec3(latDeg: number, lonDeg: number): THREE.Vector3 {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const cl = Math.cos(lat);
  return new THREE.Vector3(
    cl * Math.cos(lon),
    Math.sin(lat),
    -cl * Math.sin(lon),
  );
}

/** Global AI / innovation hub cities: [lat, lon]. */
const CITIES: Record<string, [number, number]> = {
  sanFrancisco: [37.77, -122.42],
  seattle: [47.61, -122.33],
  toronto: [43.65, -79.38],
  newYork: [40.71, -74.01],
  london: [51.51, -0.13],
  paris: [48.86, 2.35],
  telAviv: [32.09, 34.78],
  bangalore: [12.97, 77.59],
  singapore: [1.35, 103.82],
  shenzhen: [22.54, 114.06],
  beijing: [39.9, 116.41],
  seoul: [37.57, 126.98],
  tokyo: [35.68, 139.69],
};

/** Innovation corridor: a ring linking the hubs around the globe. */
const CITY_LINKS: Array<[keyof typeof CITIES, keyof typeof CITIES]> = [
  ["seattle", "sanFrancisco"],
  ["sanFrancisco", "newYork"],
  ["toronto", "newYork"],
  ["newYork", "london"],
  ["london", "paris"],
  ["paris", "telAviv"],
  ["telAviv", "bangalore"],
  ["bangalore", "singapore"],
  ["singapore", "shenzhen"],
  ["shenzhen", "beijing"],
  ["beijing", "seoul"],
  ["seoul", "tokyo"],
  ["tokyo", "sanFrancisco"],
];

interface GlobePalette {
  coreDeep: number;
  coreMid: number;
  coreLit: number;
  gridColor: number;
  gridStrength: number;
  atmosColor: number;
  atmosStrength: number;
  landColor: number;
  landHot: number;
  landOpacity: number;
  latticeColor: number;
  latticeOpacity: number;
  markerColor: number;
  markerHaloColor: number;
  markerHaloOpacity: number;
  arcColor: number;
  arcOpacity: number;
  packetColor: number;
  ringColor: number;
  ringOpacity: number;
  scanColor: number;
  /** Additive glow reads well on dark; normal blending on light. */
  glowBlending: THREE.Blending;
}

/** Dark: black body + white land / cities / edges. */
const DARK_PALETTE: GlobePalette = {
  coreDeep: 0x05070b,
  coreMid: 0x0b1219,
  coreLit: 0x16202b,
  gridColor: 0xc8d4de,
  gridStrength: 0.16,
  atmosColor: 0xd0d8e0,
  atmosStrength: 0.4,
  landColor: 0xd8e4ee,
  landHot: 0xffffff,
  landOpacity: 0.92,
  latticeColor: 0x3c4d5e,
  latticeOpacity: 0.32,
  markerColor: 0xffffff,
  markerHaloColor: 0xa8b8c4,
  markerHaloOpacity: 0.2,
  arcColor: 0xc0ccd6,
  arcOpacity: 0.48,
  packetColor: 0xffffff,
  ringColor: 0xa8b4c0,
  ringOpacity: 0.35,
  scanColor: 0xffffff,
  glowBlending: THREE.AdditiveBlending,
};

/** Light: white body + ink land / cities / edges (mirror of dark). */
const LIGHT_PALETTE: GlobePalette = {
  coreDeep: 0xc8d0d8,
  coreMid: 0xe4e9ee,
  coreLit: 0xf7f9fb,
  gridColor: 0x1a222c,
  gridStrength: 0.22,
  atmosColor: 0x6a7682,
  atmosStrength: 0.28,
  landColor: 0x121820,
  landHot: 0x05080c,
  landOpacity: 0.95,
  latticeColor: 0x8a96a2,
  latticeOpacity: 0.45,
  markerColor: 0x0a1016,
  markerHaloColor: 0x2a3440,
  markerHaloOpacity: 0.18,
  arcColor: 0x1a222c,
  arcOpacity: 0.55,
  packetColor: 0x0a1016,
  ringColor: 0x2a3440,
  ringOpacity: 0.42,
  scanColor: 0x0a1016,
  glowBlending: THREE.NormalBlending,
};

function sampleLandPoints(
  image: HTMLImageElement,
  count: number,
): { positions: Float32Array; phases: Float32Array } {
  const w = 1024;
  const h = 512;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(image, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);

  const positions: number[] = [];
  const phases: number[] = [];
  let attempts = 0;
  const maxAttempts = count * 40;

  while (positions.length / 3 < count && attempts < maxAttempts) {
    attempts += 1;
    const u = Math.random();
    const v = Math.random();
    const lat = Math.asin(2 * v - 1);
    const lon = u * Math.PI * 2 - Math.PI;
    const x = Math.floor(u * w);
    const y = Math.floor((1 - (lat / Math.PI + 0.5)) * h);
    const idx =
      (Math.min(h - 1, Math.max(0, y)) * w + Math.min(w - 1, Math.max(0, x))) * 4;
    const r8 = data[idx];
    const g8 = data[idx + 1];
    const b8 = data[idx + 2];
    const isOcean = b8 > r8 + 14 && b8 > g8 + 8;
    if (isOcean) continue;

    const r = 1.001;
    const cl = Math.cos(lat);
    positions.push(
      r * cl * Math.cos(lon),
      r * Math.sin(lat),
      -r * cl * Math.sin(lon),
    );
    phases.push(Math.random() * Math.PI * 2);
  }

  return {
    positions: new Float32Array(positions),
    phases: new Float32Array(phases),
  };
}

function makeLatLonGrid(
  latStep: number,
  lonStep: number,
  radius: number,
): THREE.BufferGeometry {
  const pts: number[] = [];
  const pushSeg = (a: THREE.Vector3, b: THREE.Vector3) => {
    pts.push(a.x, a.y, a.z, b.x, b.y, b.z);
  };
  for (let lat = -80; lat <= 80; lat += latStep) {
    const latR = (lat * Math.PI) / 180;
    const r = Math.cos(latR) * radius;
    const y = Math.sin(latR) * radius;
    for (let i = 0; i < 128; i++) {
      const t0 = (i / 128) * Math.PI * 2;
      const t1 = ((i + 1) / 128) * Math.PI * 2;
      pushSeg(
        new THREE.Vector3(Math.cos(t0) * r, y, Math.sin(t0) * r),
        new THREE.Vector3(Math.cos(t1) * r, y, Math.sin(t1) * r),
      );
    }
  }
  for (let lon = 0; lon < 360; lon += lonStep) {
    const lonR = (lon * Math.PI) / 180;
    for (let i = 0; i < 64; i++) {
      const lat0 = (-Math.PI / 2 + (i / 64) * Math.PI) * 0.92;
      const lat1 = (-Math.PI / 2 + ((i + 1) / 64) * Math.PI) * 0.92;
      pushSeg(
        new THREE.Vector3(
          Math.cos(lonR) * Math.cos(lat0) * radius,
          Math.sin(lat0) * radius,
          Math.sin(lonR) * Math.cos(lat0) * radius,
        ),
        new THREE.Vector3(
          Math.cos(lonR) * Math.cos(lat1) * radius,
          Math.sin(lat1) * radius,
          Math.sin(lonR) * Math.cos(lat1) * radius,
        ),
      );
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  return geo;
}

export function DigitalGlobe({ className = "" }: { className?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const isLight = useIsLightTheme();

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const palette = isLight ? LIGHT_PALETTE : DARK_PALETTE;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 20);
    // Pull back so orbit rings clear the canvas edge (avoids a square crop).
    camera.position.set(0, 0, 3.55);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.setClearAlpha(0);
    host.appendChild(renderer.domElement);
    renderer.domElement.style.background = "transparent";

    const root = new THREE.Group();
    root.rotation.z = -0.18;
    root.rotation.x = 0.22;
    scene.add(root);

    const coreUniforms = {
      lightDir: { value: new THREE.Vector3(-0.6, 0.5, 0.62).normalize() },
      deep: { value: new THREE.Color(palette.coreDeep) },
      mid: { value: new THREE.Color(palette.coreMid) },
      lit: { value: new THREE.Color(palette.coreLit) },
      gridColor: { value: new THREE.Color(palette.gridColor) },
      gridStrength: { value: palette.gridStrength },
      time: { value: 0 },
    };

    // Digital-twin core: shaded sphere + UV lat/lon grid + soft scan wash
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.98, 96, 96),
      new THREE.ShaderMaterial({
        uniforms: coreUniforms,
        vertexShader: `
          varying vec3 vNormalW;
          varying vec2 vUv;
          varying vec3 vPos;
          void main() {
            vNormalW = normalize(mat3(modelMatrix) * normal);
            vUv = uv;
            vPos = position;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 lightDir;
          uniform vec3 deep;
          uniform vec3 mid;
          uniform vec3 lit;
          uniform vec3 gridColor;
          uniform float gridStrength;
          uniform float time;
          varying vec3 vNormalW;
          varying vec2 vUv;
          varying vec3 vPos;
          void main() {
            // Ambient fill so the night side stays readable (no crushed black).
            float ndl = clamp(dot(normalize(vNormalW), normalize(lightDir)), 0.0, 1.0);
            float litAmt = 0.28 + 0.72 * ndl;
            vec3 color = mix(deep, mid, smoothstep(0.0, 0.6, litAmt));
            color = mix(color, lit, smoothstep(0.4, 1.0, litAmt) * 0.85);

            // Lat/lon HUD lines (digital twin surface)
            float latLines = abs(fract(vUv.y * 18.0) - 0.5);
            float lonLines = abs(fract(vUv.x * 36.0) - 0.5);
            float grid =
              smoothstep(0.045, 0.0, latLines) * 0.55 +
              smoothstep(0.03, 0.0, lonLines) * 0.85;
            float majorLat = smoothstep(0.012, 0.0, abs(fract(vUv.y * 6.0) - 0.5));
            float majorLon = smoothstep(0.008, 0.0, abs(fract(vUv.x * 8.0) - 0.5));
            grid = max(grid, (majorLat + majorLon) * 0.9);

            float scan = smoothstep(0.08, 0.0, abs(fract(vUv.y * 0.5 + time * 0.04) - 0.5));
            color += gridColor * (grid * gridStrength + scan * gridStrength * 0.55);

            gl_FragColor = vec4(color, 1.0);
          }
        `,
      }),
    );
    root.add(core);

    // Single soft limb haze — pale, thin, no cyan bloom.
    const atmos = new THREE.Mesh(
      new THREE.SphereGeometry(1.08, 64, 64),
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: palette.glowBlending,
        side: THREE.BackSide,
        uniforms: {
          color: { value: new THREE.Color(palette.atmosColor) },
          strength: { value: palette.atmosStrength },
        },
        vertexShader: `
          varying vec3 vNormal;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 color;
          uniform float strength;
          varying vec3 vNormal;
          void main() {
            float f = max(0.0, 0.62 - dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)));
            float i = pow(f, 2.8) * strength;
            gl_FragColor = vec4(color, i);
          }
        `,
      }),
    );
    root.add(atmos);

    // Wireframe lat/lon cage — twin scaffold over the oceans
    const gridGeo = makeLatLonGrid(30, 30, 1.012);
    // Very faint scaffold only — reference twin is mostly point-cloud.
    const gridMat = new THREE.LineBasicMaterial({
      color: palette.ringColor,
      transparent: true,
      opacity: palette.ringOpacity * 0.28,
      depthWrite: false,
    });
    const gridLines = new THREE.LineSegments(gridGeo, gridMat);
    root.add(gridLines);

    const landUniforms = {
      uColor: { value: new THREE.Color(palette.landColor) },
      uHot: { value: new THREE.Color(palette.landHot) },
      uOpacity: { value: palette.landOpacity },
      uTime: { value: 0 },
      // Light mode needs larger dots — ink on paper reads thinner than additive white.
      uSize: { value: isLight ? 0.022 : 0.014 },
    };

    const landMat = new THREE.ShaderMaterial({
      uniforms: landUniforms,
      transparent: true,
      depthWrite: false,
      blending: palette.glowBlending,
      vertexShader: `
        attribute float aPhase;
        uniform float uTime;
        uniform float uSize;
        varying float vPulse;
        void main() {
          vPulse = 0.55 + 0.45 * sin(uTime * 1.7 + aPhase);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = uSize * (280.0 / -mv.z) * (0.8 + 0.45 * vPulse);
          gl_Position = projectionMatrix * mv;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform vec3 uHot;
        uniform float uOpacity;
        varying float vPulse;
        void main() {
          vec2 c = gl_PointCoord - vec2(0.5);
          float d = length(c);
          if (d > 0.5) discard;
          float soft = smoothstep(0.5, 0.12, d);
          vec3 col = mix(uColor, uHot, vPulse * 0.55);
          gl_FragColor = vec4(col, uOpacity * soft * (0.7 + 0.3 * vPulse));
        }
      `,
    });
    let points: THREE.Points | null = null;

    // Sparse ocean lattice — sensor mesh feel
    const latticeCount = 7000;
    const latticePos = new Float32Array(latticeCount * 3);
    for (let i = 0; i < latticeCount; i++) {
      const y = 1 - (i / (latticeCount - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = Math.PI * (3 - Math.sqrt(5)) * i;
      latticePos[i * 3] = r * Math.cos(th) * 0.993;
      latticePos[i * 3 + 1] = y * 0.993;
      latticePos[i * 3 + 2] = r * Math.sin(th) * 0.993;
    }
    const latticeGeo = new THREE.BufferGeometry();
    latticeGeo.setAttribute("position", new THREE.BufferAttribute(latticePos, 3));
    const latticeMat = new THREE.PointsMaterial({
      size: 0.0055,
      color: palette.latticeColor,
      transparent: true,
      opacity: palette.latticeOpacity,
      depthWrite: false,
      blending: palette.glowBlending,
      sizeAttenuation: true,
    });
    root.add(new THREE.Points(latticeGeo, latticeMat));

    const cityDirs = new Map(
      Object.entries(CITIES).map(([name, [lat, lon]]) => [
        name,
        latLonToVec3(lat, lon),
      ]),
    );

    const markerGeo = new THREE.SphereGeometry(0.012, 12, 12);
    const markerMat = new THREE.MeshBasicMaterial({
      color: palette.markerColor,
      transparent: true,
      opacity: 0.95,
    });
    const hubHalos: THREE.Mesh[] = [];
    for (const dir of cityDirs.values()) {
      const m = new THREE.Mesh(markerGeo, markerMat);
      m.position.copy(dir).multiplyScalar(1.018);
      root.add(m);
      const haloDot = new THREE.Mesh(
        new THREE.SphereGeometry(0.045, 14, 14),
        new THREE.MeshBasicMaterial({
          color: palette.markerHaloColor,
          transparent: true,
          opacity: palette.markerHaloOpacity,
          depthWrite: false,
          blending: palette.glowBlending,
        }),
      );
      haloDot.position.copy(m.position);
      root.add(haloDot);
      hubHalos.push(haloDot);
    }

    const arcMat = new THREE.LineBasicMaterial({
      color: palette.arcColor,
      transparent: true,
      opacity: palette.arcOpacity,
    });
    const arcs: THREE.Line[] = [];
    const arcCurves: THREE.QuadraticBezierCurve3[] = [];
    for (const [from, to] of CITY_LINKS) {
      const a = cityDirs.get(from)!.clone().multiplyScalar(1.018);
      const b = cityDirs.get(to)!.clone().multiplyScalar(1.018);
      const apex = 1.07 + 0.52 * (a.angleTo(b) / Math.PI);
      const mid = a
        .clone()
        .add(b)
        .multiplyScalar(0.5)
        .normalize()
        .multiplyScalar(apex);
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      arcCurves.push(curve);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(56)),
        arcMat,
      );
      root.add(line);
      arcs.push(line);
    }

    // Data packets traveling the corridors — persona traffic
    const packetGeo = new THREE.SphereGeometry(0.009, 8, 8);
    const packetMat = new THREE.MeshBasicMaterial({
      color: palette.packetColor,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
      blending: palette.glowBlending,
    });
    type Packet = {
      mesh: THREE.Mesh;
      curveIndex: number;
      t: number;
      speed: number;
    };
    const packets: Packet[] = [];
    for (let i = 0; i < arcCurves.length; i++) {
      for (let k = 0; k < 2; k++) {
        const mesh = new THREE.Mesh(packetGeo, packetMat);
        root.add(mesh);
        packets.push({
          mesh,
          curveIndex: i,
          t: (i * 0.17 + k * 0.48) % 1,
          speed: 0.08 + (i % 5) * 0.012 + k * 0.02,
        });
      }
    }

    // Thin accent latitude rings
    const ringMat = new THREE.LineBasicMaterial({
      color: palette.ringColor,
      transparent: true,
      opacity: palette.ringOpacity,
    });
    const accentRings: THREE.Line[] = [];
    for (const lat of [-0.52, 0, 0.52]) {
      const pts: THREE.Vector3[] = [];
      for (let i = 0; i <= 128; i++) {
        const t = (i / 128) * Math.PI * 2;
        const r = Math.cos(lat);
        pts.push(
          new THREE.Vector3(
            Math.cos(t) * r,
            Math.sin(lat),
            Math.sin(t) * r,
          ).multiplyScalar(1.02),
        );
      }
      const ring = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        ringMat,
      );
      root.add(ring);
      accentRings.push(ring);
    }

    // Scanning latitude band (persona-density sweep)
    const scanGeo = new THREE.TorusGeometry(1.04, 0.004, 8, 128);
    const scanMat = new THREE.MeshBasicMaterial({
      color: palette.scanColor,
      transparent: true,
      opacity: isLight ? 0.7 : 0.65,
      depthWrite: false,
      blending: palette.glowBlending,
    });
    const scanRing = new THREE.Mesh(scanGeo, scanMat);
    scanRing.rotation.x = Math.PI / 2;
    root.add(scanRing);

    const loader = new THREE.ImageLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(
      EARTH_URL,
      (image) => {
        const { positions, phases } = sampleLandPoints(image, 36000);
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        geo.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
        points = new THREE.Points(geo, landMat);
        root.add(points);
      },
      undefined,
      () => {
        const fallbackPos: number[] = [];
        const fallbackPhase: number[] = [];
        for (let i = 0; i < 4000; i++) {
          const y = 1 - (i / 3999) * 2;
          const r = Math.sqrt(1 - y * y);
          const th = Math.PI * (3 - Math.sqrt(5)) * i;
          if (Math.sin(th * 2.1) * Math.cos(y * 3) < 0.1) continue;
          fallbackPos.push(r * Math.cos(th), y, r * Math.sin(th));
          fallbackPhase.push(Math.random() * Math.PI * 2);
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute(
          "position",
          new THREE.Float32BufferAttribute(fallbackPos, 3),
        );
        geo.setAttribute(
          "aPhase",
          new THREE.Float32BufferAttribute(fallbackPhase, 1),
        );
        points = new THREE.Points(geo, landMat);
        root.add(points);
      },
    );

    const setSize = () => {
      const w = Math.max(1, host.clientWidth);
      const h = Math.max(1, host.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.display = "block";
    };
    setSize();
    const ro = new ResizeObserver(setSize);
    ro.observe(host);

    let raf = 0;
    let t0 = performance.now();
    const tick = (now: number) => {
      const t = (now - t0) / 1000;
      root.rotation.y += 0.0015;

      coreUniforms.time.value = t;
      landUniforms.uTime.value = t;

      // Latitude scan sweeps pole-to-pole
      const scanLat = Math.sin(t * 0.35) * 0.85;
      scanRing.position.y = scanLat;
      const scanR = Math.cos(scanLat) * 1.04;
      scanRing.scale.set(scanR / 1.04, scanR / 1.04, 1);

      for (let i = 0; i < hubHalos.length; i++) {
        const pulse = 0.55 + 0.45 * Math.sin(t * 2.2 + i * 0.7);
        const mat = hubHalos[i].material as THREE.MeshBasicMaterial;
        mat.opacity = palette.markerHaloOpacity * (0.65 + 0.55 * pulse);
        hubHalos[i].scale.setScalar(0.85 + 0.35 * pulse);
      }

      for (const p of packets) {
        p.t = (p.t + p.speed * 0.016) % 1;
        const pos = arcCurves[p.curveIndex].getPoint(p.t);
        p.mesh.position.copy(pos);
        const glow = 0.55 + 0.45 * Math.sin(t * 4 + p.t * 12);
        p.mesh.scale.setScalar(0.7 + 0.55 * glow);
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.dispose();
      core.geometry.dispose();
      (core.material as THREE.Material).dispose();
      atmos.geometry.dispose();
      (atmos.material as THREE.Material).dispose();
      gridGeo.dispose();
      gridMat.dispose();
      markerGeo.dispose();
      markerMat.dispose();
      for (const h of hubHalos) {
        h.geometry.dispose();
        (h.material as THREE.Material).dispose();
      }
      arcMat.dispose();
      ringMat.dispose();
      landMat.dispose();
      latticeGeo.dispose();
      latticeMat.dispose();
      packetGeo.dispose();
      packetMat.dispose();
      scanGeo.dispose();
      scanMat.dispose();
      points?.geometry.dispose();
      for (const line of arcs) line.geometry.dispose();
      for (const ring of accentRings) ring.geometry.dispose();
      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement);
      }
    };
  }, [isLight]);

  return <div ref={hostRef} className={`h-full w-full ${className}`} aria-hidden />;
}
