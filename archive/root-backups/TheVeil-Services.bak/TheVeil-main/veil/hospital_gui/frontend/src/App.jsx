import React, { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";

function Panel({ title, children }) {
  return (
    <div style={{
      background: "rgba(17,24,39,0.85)",
      border: "1px solid rgba(31,41,55,0.9)",
      borderRadius: 14,
      padding: 14
    }}>
      <div style={{ fontWeight: 900, marginBottom: 8 }}>{title}</div>
      <div style={{ color: "#9ca3af", fontSize: 13 }}>{children}</div>
    </div>
  );
}

function Box() {
  return (
    <mesh rotation={[0.25, 0.4, 0]}>
      <boxGeometry args={[1.2, 1.2, 1.2]} />
      <meshStandardMaterial />
    </mesh>
  );
}

export default function App() {
  const [perf, setPerf] = useState(null);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const r = await fetch("/api/performance");
        const j = await r.json();
        if (alive) setPerf(j);
      } catch {}
      setTimeout(tick, 1000);
    }
    tick();
    return () => { alive = false; };
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", height: "100%" }}>
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ fontSize: 18, fontWeight: 900 }}>🧠 Veil 3D Dashboard</div>
        <Panel title="Backend Perf (live)">
          {perf ? (
            <div style={{ lineHeight: 1.6 }}>
              CPU: {perf.cpu_percent ?? "—"}%<br />
              RAM: {perf.mem_percent ?? "—"}%<br />
              Load: {perf.load ?? "—"}<br />
            </div>
          ) : "Loading…"}
        </Panel>
        <Panel title="Tip">
          This page is served from FastAPI at <b>/app/</b>.
        </Panel>
      </div>

      <div style={{ height: "100%", borderLeft: "1px solid rgba(31,41,55,0.9)" }}>
        <Canvas camera={{ position: [2.5, 2.0, 2.5], fov: 50 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 6, 5]} intensity={1.2} />
          <Box />
          <OrbitControls />
          <Environment preset="city" />
        </Canvas>
      </div>
    </div>
  );
}
