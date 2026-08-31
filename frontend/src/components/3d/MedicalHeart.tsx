import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

export default function MedicalHeart() {
  const group = useRef<THREE.Group>(null);
  const core = useRef<THREE.Mesh>(null);

  const geometry = useMemo(() => {
    const shape = new THREE.Shape();

    shape.moveTo(0, -0.9);
    shape.bezierCurveTo(-1.8, -0.1, -1.25, 1.45, 0, 0.8);
    shape.bezierCurveTo(1.25, 1.45, 1.8, -0.1, 0, -0.9);

    return new THREE.ExtrudeGeometry(shape, {
      depth: 0.45,
      bevelEnabled: true,
      bevelSegments: 6,
      bevelSize: 0.09,
      bevelThickness: 0.09,
      curveSegments: 32,
    });
  }, []);

  useFrame((state, delta) => {
    const time = state.clock.elapsedTime;

    if (group.current) {
      group.current.rotation.y += delta * 0.16;
      group.current.rotation.z =
        Math.sin(time * 0.6) * 0.035;
    }

    if (core.current) {
      const material =
        core.current.material as THREE.MeshPhysicalMaterial;

      material.emissiveIntensity =
        0.45 + Math.sin(time * 2) * 0.14;
    }
  });

  return (
    <group ref={group} scale={0.82}>
      <mesh ref={core} geometry={geometry}>
        <meshPhysicalMaterial
          color="#eef6fb"
          emissive="#59bbd8"
          emissiveIntensity={0.35}
          metalness={0.05}
          roughness={0.15}
          transmission={0.5}
          thickness={1.1}
          ior={1.35}
          clearcoat={1}
          clearcoatRoughness={0.1}
          transparent
          opacity={0.96}
        />
      </mesh>

      <mesh
        position={[0, 0, 0.32]}
        scale={0.62}
      >
        <sphereGeometry args={[0.45, 32, 32]} />

        <meshPhysicalMaterial
          color="#ffffff"
          emissive="#59bbd8"
          emissiveIntensity={0.45}
          transparent
          opacity={0.35}
          roughness={0.05}
        />
      </mesh>
    </group>
  );
}