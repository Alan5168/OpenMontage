import {ThreeCanvas} from "@remotion/three";
import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const COLORS = ["#6EE7F9", "#8B5CF6", "#F472B6"] as const;

const clamp = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};

const LayerStack: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const reveal = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 95, mass: 1},
  });
  const settle = spring({
    frame: frame - 18,
    fps,
    config: {damping: 22, stiffness: 80, mass: 1},
  });
  const turn = interpolate(
    frame,
    [0, durationInFrames - 1],
    [-0.46, 0.34],
    {...clamp, easing: Easing.inOut(Easing.cubic)},
  );
  const float = Math.sin((frame / fps) * Math.PI * 1.2) * 0.08;

  return (
    <group
      position={[0, -0.2 + float, 0]}
      rotation={[-0.28 + settle * 0.08, turn, -0.08]}
      scale={[0.82 + reveal * 0.18, 0.82 + reveal * 0.18, 0.82 + reveal * 0.18]}
    >
      {COLORS.map((color, index) => {
        const separation = interpolate(reveal, [0, 1], [0.08, 0.72]);
        const y = (index - 1) * separation;

        return (
          <group key={color} position={[0, y, 0]}>
            <mesh>
              <boxGeometry args={[5.2 - index * 0.34, 0.28, 3.15 - index * 0.2]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={0.16}
                metalness={0.42}
                roughness={0.28}
              />
            </mesh>
            <mesh scale={[1.012, 1.08, 1.012]}>
              <boxGeometry args={[5.2 - index * 0.34, 0.28, 3.15 - index * 0.2]} />
              <meshBasicMaterial color="#EAFBFF" wireframe transparent opacity={0.18} />
            </mesh>
          </group>
        );
      })}

      <mesh position={[0, 0, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.55, 0.025, 12, 96]} />
        <meshBasicMaterial color="#FFFFFF" transparent opacity={0.35} />
      </mesh>
    </group>
  );
};

export const ThreeJsSmoke: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();

  const copyIn = interpolate(frame, [8, 28], [0, 1], clamp);
  const ruleWidth = interpolate(frame, [18, 48], [0, 420], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const exit = interpolate(frame, [durationInFrames - 12, durationInFrames - 1], [1, 0], clamp);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#050711",
        color: "#F8FAFC",
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        opacity: exit,
      }}
    >
      <ThreeCanvas
        width={width}
        height={height}
        camera={{fov: 34, position: [0, 0.3, 11]}}
        dpr={1}
        gl={{antialias: true, preserveDrawingBuffer: true}}
        style={{position: "absolute", inset: 0}}
      >
        <color attach="background" args={["#050711"]} />
        <fog attach="fog" args={["#050711", 9, 18]} />
        <ambientLight intensity={0.72} />
        <directionalLight position={[5, 7, 8]} intensity={3.2} color="#DDFBFF" />
        <pointLight position={[-5, -2, 5]} intensity={35} distance={14} color="#8B5CF6" />
        <pointLight position={[4, 1, 3]} intensity={24} distance={12} color="#22D3EE" />
        <LayerStack />
      </ThreeCanvas>

      <AbsoluteFill
        style={{
          justifyContent: "space-between",
          padding: "132px 96px 118px",
          pointerEvents: "none",
        }}
      >
        <div style={{opacity: copyIn, transform: `translateY(${(1 - copyIn) * 28}px)`}}>
          <div
            style={{
              color: "#6EE7F9",
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "0.28em",
              textTransform: "uppercase",
            }}
          >
            OpenMontage / Runtime Probe
          </div>
          <div
            style={{
              fontSize: 94,
              fontWeight: 760,
              letterSpacing: "-0.055em",
              lineHeight: 0.94,
              marginTop: 22,
              maxWidth: 820,
            }}
          >
            THREE.JS
            <br />
            READY
          </div>
          <div style={{height: 3, width: ruleWidth, background: "#F472B6", marginTop: 34}} />
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            opacity: copyIn,
          }}
        >
          <div style={{fontSize: 25, lineHeight: 1.5, color: "#A7B1C2"}}>
            deterministic frame clock
            <br />
            Remotion + React Three Fiber
          </div>
          <div
            style={{
              border: "1px solid rgba(110,231,249,0.45)",
              borderRadius: 999,
              color: "#DDFBFF",
              fontSize: 21,
              fontWeight: 650,
              letterSpacing: "0.12em",
              padding: "14px 22px",
              textTransform: "uppercase",
            }}
          >
            1080 × 1920
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
