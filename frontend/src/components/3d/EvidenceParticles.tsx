import { useMemo } from "react";

export default function EvidenceParticles() {
  const points = useMemo(
    () =>
      Array.from({ length: 18 }, (_, index) => {
        const angle =
          (index / 18) * Math.PI * 2;

        const radius = 2.2;

        return [
          Math.cos(angle) * radius,
          Math.sin(angle) * radius,
          Math.sin(angle * 2) * 0.25,
        ] as [number, number, number];
      }),
    []
  );

  return (
    <>
      {points.map((position, index) => (
        <mesh
          key={index}
          position={position}
        >
          <sphereGeometry
            args={[0.022, 12, 12]}
          />

          <meshBasicMaterial
            color="#2779a8"
            transparent
            opacity={0.55}
          />
        </mesh>
      ))}
    </>
  );
}