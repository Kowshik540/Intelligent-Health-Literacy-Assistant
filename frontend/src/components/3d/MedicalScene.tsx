import {
  Float,
  OrbitControls,
  Stars,
} from "@react-three/drei";

import MedicalHeart from "./MedicalHeart";
import ScanRings from "./ScanRings";
import EvidenceParticles from "./EvidenceParticles";

export default function MedicalScene() {
  return (
    <>
      <ambientLight intensity={1.7} />

      <directionalLight
        position={[4, 5, 5]}
        intensity={2.6}
        color="#ffffff"
      />

      <pointLight
        position={[0, 1, 2]}
        intensity={4.5}
        color="#59bbd8"
      />

      <pointLight
        position={[-3, -2, -1.5]}
        intensity={2.2}
        color="#2779a8"
      />

      <Float
        speed={1.4}
        rotationIntensity={0.16}
        floatIntensity={0.32}
      >
        <MedicalHeart />
      </Float>

      <ScanRings />
      <EvidenceParticles />

      <Stars
        radius={30}
        depth={15}
        count={550}
        factor={1}
        saturation={0}
        fade
      />

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.32}
      />
    </>
  );
}