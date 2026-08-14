import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type HeroTitleProps = {
  title: string;
  subtitle?: string;
  fontSize?: number;
};

export const HeroTitle: React.FC<HeroTitleProps> = ({
  title,
  subtitle,
  fontSize = 72,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const isCjk = /[\u3400-\u9fff]/.test(title);

  if (isCjk) {
    const subtitleSpring = spring({
      frame: frame - 8,
      fps,
      config: { damping: 20 },
    });
    return (
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          background:
            "radial-gradient(ellipse at center, rgba(15,23,42,0.35) 0%, rgba(15,23,42,0.55) 100%)",
        }}
      >
        <div style={{ textAlign: "center", maxWidth: "85%" }}>
          <div
            style={{
              fontSize,
              fontWeight: 800,
              fontFamily:
                "system-ui, 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif",
              lineHeight: 1.2,
              color: "#F8FAFC",
              whiteSpace: "pre-line",
              overflowWrap: "break-word",
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{
                marginTop: 20,
                opacity: subtitleSpring,
                fontSize: 28,
                fontWeight: 400,
                color: "#A78BFA",
                fontFamily:
                  "system-ui, 'PingFang SC', 'Microsoft YaHei', sans-serif",
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      </AbsoluteFill>
    );
  }

  // Latin titles keep letter-by-letter spring
  const titleChars = title.split("");

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        background:
          "radial-gradient(ellipse at center, rgba(15,23,42,0.35) 0%, rgba(15,23,42,0.55) 100%)",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: "85%" }}>
        {/* Main title with per-character spring */}
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            fontFamily: "Space Grotesk, Inter, system-ui, sans-serif",
            lineHeight: 1.2,
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 0,
          }}
        >
          {titleChars.map((char, i) => {
            const delay = i * 1.2;
            const charSpring = spring({
              frame: frame - delay,
              fps,
              config: { damping: 12, stiffness: 150 },
            });

            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  opacity: charSpring,
                  transform: `translateY(${interpolate(charSpring, [0, 1], [30, 0])}px)`,
                  color: i < 8 ? "#22D3EE" : "#F8FAFC", // Accent first word
                  whiteSpace: char === " " ? "pre" : undefined,
                  minWidth: char === " " ? "0.3em" : undefined,
                }}
              >
                {char}
              </span>
            );
          })}
        </div>

        {/* Subtitle */}
        {subtitle && (
          <div
            style={{
              marginTop: 20,
              opacity: spring({
                frame: frame - titleChars.length * 1.2 - 5,
                fps,
                config: { damping: 20 },
              }),
              fontSize: 28,
              fontWeight: 400,
              color: "#A78BFA",
              fontFamily: "Space Grotesk, Inter, system-ui, sans-serif",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            {subtitle}
          </div>
        )}

        {/* Animated underline */}
        <div
          style={{
            margin: "24px auto 0",
            height: 3,
            backgroundColor: "#22D3EE",
            borderRadius: 2,
            width: interpolate(
              spring({
                frame: frame - 15,
                fps,
                config: { damping: 15, stiffness: 60 },
              }),
              [0, 1],
              [0, 400]
            ),
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
