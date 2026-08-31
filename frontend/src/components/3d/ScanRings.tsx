import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";

export default function ScanRings() {
  const ring = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (ring.current) {
      ring.current.rotation.z += delta * 0.07;
      ring.current.rotation.x += delta * 0.02;
    }
  });

  return (
    <group ref={ring}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry
          args={[1.65, 0.011, 16, 100]}
        />
        <meshBasicMaterial
          color="#59bbd8"
          transparent
          opacity={0.4}
        />
      </mesh>

      <mesh rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry
          args={[1.92, 0.007, 16, 100]}
        />
        <meshBasicMaterial
          color="#2779a8"
          transparent
          opacity={0.18}
        />
      </mesh>

      <mesh rotation={[0.7, 0.3, 0]}>
        <torusGeometry
          args={[2.16, 0.006, 16, 100]}
        />
        <meshBasicMaterial
          color="#2779a8"
          transparent
          opacity={0.25}
        />
      </mesh>
    </group>
  );
}