# Three.js readiness probe

This directory proves that the existing Remotion composer can render deterministic
React Three Fiber scenes through `@remotion/three`. It is an engineering smoke test,
not a stock creative template.

## Verify the runtime

```bash
npm run typecheck:three
npm run verify:three:still
npm run verify:three:video
```

Both render commands write to fixed, ignored paths under `out/`, so repeated checks
overwrite prior probes instead of accumulating project artifacts.

The commands explicitly select Chromium's `angle` backend. Headless Chromium does
not create a WebGL2 context reliably on this Mac with Remotion's default GL setting.

## Production boundary

- Use this route only for a shot whose meaning depends on spatial depth, an exploded
  object, a 3D camera move, or a layered system model.
- Hand-author the production scene in the approved atelier project. Do not import
  `ThreeJsSmoke` as a reusable visual template.
- Drive every animated value from Remotion's `useCurrentFrame()` or `spring()`.
  Never use `useFrame()`, `requestAnimationFrame`, CSS animation, or CSS transition.
- Use `<ThreeCanvas width={width} height={height}>`; read
  `.agents/skills/remotion-best-practices/rules/3d.md` and the relevant
  `.claude/skills/threejs-*/SKILL.md` before authoring.
