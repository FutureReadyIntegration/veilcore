import React from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";

function Box() {
  return (
    <mesh rotation={[0.25, 0.4, 0]}>
      <boxGeometry args={[1.2, 1.2, 1.2]} />
      <meshStandardMaterial />
    </mesh>
  );
}

export default function Scene3D() {
  return (
    <Canvas camera={{ position: [2.5, 2.0, 2.5], fov: 50 }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 6, 5]} intensity={1.2} />
      <Box />
      <OrbitControls />
      <Environment preset="city" />
    </Canvas>
  );
}
