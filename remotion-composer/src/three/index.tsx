import React from "react";
import {Composition, registerRoot} from "remotion";
import {ThreeJsSmoke} from "./ThreeJsSmoke";

const ThreeJsSmokeRoot: React.FC = () => {
  return (
    <Composition
      id="ThreeJsSmoke"
      component={ThreeJsSmoke}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};

registerRoot(ThreeJsSmokeRoot);
