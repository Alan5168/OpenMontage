import { registerRoot } from "remotion";
import { TriptychDemoRoot } from "./KitRoot.triptych-demo";

// Entry for the CP3 Triptych A/B demo (isolated from the main kit entry so the
// shipped compositions stay untouched). Renders cp1-co-triptych-demo only.
registerRoot(TriptychDemoRoot);
