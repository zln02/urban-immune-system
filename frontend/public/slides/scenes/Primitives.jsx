// Primitives.jsx — shared deck primitives
// Design constraints: Helvetica Neue; white + single accent color (cyan);
// no gradient text; graphics and text strictly separated (text on solid
// dark plates or clear space with high contrast).

const ACCENT = 'var(--accent, #22E3FF)';
const ACCENT_DIM = 'var(--accent-dim, rgba(34,227,255,0.5))';
const WHITE = 'var(--ink, #FFFFFF)';
const WHITE_70 = 'var(--ink-70, rgba(255,255,255,0.7))';
const WHITE_45 = 'var(--ink-45, rgba(255,255,255,0.45))';
const WHITE_15 = 'var(--ink-15, rgba(255,255,255,0.15))';
const INK = '#05070B';

const FONT = '"Helvetica Neue", Helvetica, "Pretendard", Arial, sans-serif';

const TYPE = {
  eyebrow: { fontSize: 22, fontWeight: 500, letterSpacing: '0.32em', textTransform: 'uppercase', color: ACCENT },
  titleXL: { fontSize: 120, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.02, color: WHITE },
  title:   { fontSize: 88,  fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.05, color: WHITE },
  subtitle:{ fontSize: 36,  fontWeight: 400, letterSpacing: '-0.005em', lineHeight: 1.35, color: WHITE_70 },
  body:    { fontSize: 28,  fontWeight: 400, letterSpacing: '-0.003em', lineHeight: 1.5,  color: WHITE },
  bodyDim: { fontSize: 28,  fontWeight: 400, letterSpacing: '-0.003em', lineHeight: 1.5,  color: WHITE_70 },
  small:   { fontSize: 22,  fontWeight: 400, letterSpacing: '-0.002em', lineHeight: 1.5,  color: WHITE_70 },
  mega:    { fontSize: 240, fontWeight: 700, letterSpacing: '-0.05em',  lineHeight: 0.9,  color: WHITE, fontFeatureSettings: '"lnum"' },
  megaAccent:{ fontSize: 240, fontWeight: 700, letterSpacing: '-0.05em',lineHeight: 0.9,  color: ACCENT, fontFeatureSettings: '"lnum"' },
  label:   { fontSize: 18,  fontWeight: 500, letterSpacing: '0.18em',  textTransform: 'uppercase', color: WHITE_45 },
};

// Fade + slide line of text. keepMounted so exit eases gracefully.
function Line({ children, x, y, delay = 0, style = {}, align = 'left', width }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const appear = Math.min(1, t / 0.55);
  const eased = Easing.easeOutCubic(Math.max(0, Math.min(1, appear)));
  const ty = (1 - eased) * 24;
  return (
    <div style={{
      position: 'absolute',
      left: x, top: y,
      width,
      transform: align === 'center' ? `translate(-50%, ${ty}px)` : `translateY(${ty}px)`,
      textAlign: align,
      opacity: eased,
      fontFamily: FONT,
      willChange: 'transform, opacity',
      ...style,
    }}>
      {children}
    </div>
  );
}

// Thin rule that draws itself in horizontally
function Rule({ x, y, width, delay = 0, color = WHITE_15, thickness = 1 }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.7)));
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      width: width * p, height: thickness, background: color,
      transformOrigin: 'left center',
    }} />
  );
}

// Corner marks — tiny + small, to frame the slide
function CornerMarks({ delay = 0, accent = false }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  const color = accent ? ACCENT : WHITE_45;
  const S = 28, T = 1.5;
  const mark = (x, y, rot) => (
    <div style={{ position:'absolute', left:x, top:y, width:S, height:S, transform:`rotate(${rot}deg)`, opacity:p }}>
      <div style={{ position:'absolute', left:0, top:0, width:S, height:T, background:color }} />
      <div style={{ position:'absolute', left:0, top:0, width:T, height:S, background:color }} />
    </div>
  );
  return (
    <>
      {mark(60, 60, 0)}
      {mark(1920-60-S, 60, 90)}
      {mark(60, 1080-60-S, 270)}
      {mark(1920-60-S, 1080-60-S, 180)}
    </>
  );
}

// Slide chrome — top/bottom meta
function Chrome({ index, total = 27, label }) {
  return (
    <>
      <Line x={60} y={40} style={{ ...TYPE.label, color: WHITE_45 }}>URBAN IMMUNE SYSTEM</Line>
      <Line x={1860} y={40} style={{ ...TYPE.label, color: ACCENT, textAlign: 'right' }} width={0}>
        <div style={{ position:'absolute', right:0, top:0, whiteSpace:'nowrap' }}>{String(index).padStart(2,'0')} / {String(total).padStart(2,'0')}</div>
      </Line>
      <Line x={60} y={1020} style={{ ...TYPE.label, color: WHITE_45 }}>{label}</Line>
      <Line x={1860} y={1020} style={{ ...TYPE.label, color: WHITE_45, textAlign: 'right' }} width={0}>
        <div style={{ position:'absolute', right:0, top:0, whiteSpace:'nowrap' }}>CAPSTONE · 2026.05.07</div>
      </Line>
    </>
  );
}

// Animated ring (abstract motif) — strokes itself in via SVG dashoffset
function Ring({ cx, cy, r, thickness = 2, color = ACCENT, delay = 0, dur = 1.2, dashed = false }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / dur)));
  const C = 2 * Math.PI * r;
  return (
    <svg style={{ position:'absolute', left:0, top:0, width:1920, height:1080, pointerEvents:'none', overflow:'visible' }}>
      <circle
        cx={cx} cy={cy} r={r}
        fill="none" stroke={color} strokeWidth={thickness}
        strokeDasharray={dashed ? "3 8" : `${C}`}
        strokeDashoffset={dashed ? 0 : C * (1 - p)}
        opacity={dashed ? p * 0.6 : 1}
      />
    </svg>
  );
}

// Pulsing dot
function Pulse({ x, y, r = 6, color = ACCENT, delay = 0 }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const phase = (Math.sin(t * 2.8) + 1) * 0.5;
  const appear = Math.min(1, t / 0.3);
  return (
    <svg style={{ position:'absolute', left:0, top:0, width:1920, height:1080, pointerEvents:'none' }}>
      <circle cx={x} cy={y} r={r + phase * 4} fill={color} opacity={0.25 * appear} />
      <circle cx={x} cy={y} r={r} fill={color} opacity={appear} />
    </svg>
  );
}

// Stat block — giant number with label plate underneath
function Stat({ x, y, value, label, color = WHITE, delay = 0, size = 240 }) {
  return (
    <>
      <Line x={x} y={y} delay={delay} style={{ ...TYPE.mega, fontSize: size, color }}>{value}</Line>
      <Line x={x} y={y + size * 0.95} delay={delay + 0.15} style={TYPE.label}>{label}</Line>
    </>
  );
}

// Dark text plate — ensures readability over shader
function Plate({ x, y, width, height, children, opacity = 0.55, delay = 0, border = true }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      position: 'absolute',
      left: x, top: y, width, height,
      background: `rgba(5,7,11,${opacity})`,
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      border: border ? `1px solid rgba(255,255,255,0.08)` : 'none',
      opacity: p,
      transform: `translateY(${(1-p)*12}px)`,
      boxSizing: 'border-box',
    }}>
      {children}
    </div>
  );
}

// Scanner progress bar
function Bar({ x, y, width, pct, color = ACCENT, label, value, delay = 0 }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.9)));
  return (
    <div style={{ position:'absolute', left:x, top:y, width, fontFamily:FONT }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:10, color: WHITE, fontSize: 24, fontWeight:500 }}>
        <span>{label}</span><span style={{ color, fontFeatureSettings:'"lnum"' }}>{value}</span>
      </div>
      <div style={{ height: 4, background: WHITE_15, position:'relative', overflow:'hidden' }}>
        <div style={{ height:'100%', width:`${pct * p}%`, background: color }} />
      </div>
    </div>
  );
}

window.Primitives = { ACCENT, ACCENT_DIM, WHITE, WHITE_70, WHITE_45, WHITE_15, INK, FONT, TYPE,
  Line, Rule, CornerMarks, Chrome, Ring, Pulse, Stat, Plate, Bar };
