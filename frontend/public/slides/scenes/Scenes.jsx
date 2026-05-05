// Scenes.jsx — all 16 animated scenes for Urban Immune System deck.
// Each scene is a Sprite with duration SCENE_DUR, composed of primitives.

const { ACCENT, ACCENT_DIM, WHITE, WHITE_70, WHITE_45, WHITE_15, FONT, TYPE,
  Line, Rule, CornerMarks, Chrome, Ring, Pulse, Stat, Plate, Bar } = window.Primitives;

const SCENE_DUR = 7.5; // seconds per scene

// ----- S01 Cover -----
function S01() {
  const { localTime } = useSprite();
  return (
    <>
      <CornerMarks delay={0.2} accent />
      <Chrome index={1} label="01 · COVER" />
      {/* Central orbital rings motif */}
      <Ring cx={960} cy={540} r={380} thickness={1.5} color={ACCENT} delay={0.2} dur={2.0} />
      <Ring cx={960} cy={540} r={240} thickness={1} color={ACCENT_DIM} delay={0.6} dur={1.8} />
      <Ring cx={960} cy={540} r={520} thickness={1} color="rgba(255,255,255,0.15)" delay={1.0} dashed />
      {/* Three orbiting nodes (the 3 layers) */}
      <OrbitNode cx={960} cy={540} r={380} angle={-90} color={ACCENT} delay={1.4} />
      <OrbitNode cx={960} cy={540} r={380} angle={30} color={ACCENT} delay={1.6} />
      <OrbitNode cx={960} cy={540} r={380} angle={150} color={ACCENT} delay={1.8} />

      <Line x={120} y={180} delay={0.1} style={TYPE.eyebrow}>CAPSTONE · MID-TERM · 2026</Line>
      <Line x={120} y={720} delay={0.4} style={{ ...TYPE.titleXL, fontSize: 130 }}>URBAN IMMUNE</Line>
      <Line x={120} y={870} delay={0.6} style={{ ...TYPE.titleXL, fontSize: 130, color: ACCENT }}>SYSTEM</Line>

      <Line x={120} y={1000} delay={1.0} style={{ ...TYPE.small, color: WHITE_70 }}>
        동신대학교 컴퓨터공학과 · 5인 팀 · B2G 감염병 조기경보
      </Line>
    </>
  );
}

function OrbitNode({ cx, cy, r, angle, color, delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const appear = Easing.easeOutBack(Math.min(1, t / 0.6));
  const spin = t * 6; // degrees
  const a = (angle + spin) * Math.PI / 180;
  const x = cx + Math.cos(a) * r;
  const y = cy + Math.sin(a) * r;
  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none' }}>
      <circle cx={x} cy={y} r={8 * appear} fill={color} />
      <circle cx={x} cy={y} r={18 * appear} fill={color} opacity={0.2} />
    </svg>
  );
}

// ----- S02 Problem — "2 weeks late" -----
function S02() {
  return (
    <>
      <Chrome index={2} label="02 · PROBLEM" />
      <Line x={120} y={140} style={TYPE.eyebrow}>문제</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1400}>병원에 가야 시작되는 감시,</Line>
      <Line x={120} y={310} delay={0.3} style={{ ...TYPE.title, color: ACCENT }} width={1400}>우리는 항상 2주 늦는다.</Line>

      {/* Timeline bar motif */}
      <Line x={120} y={520} delay={0.6} style={TYPE.label}>기존 감시 체인 · 누적 지연</Line>
      <TimelineBar x={120} y={580} delay={0.8} />

      <Stat x={120} y={800} value="14+" label="일 · 병원 기반 지연" color={ACCENT} delay={1.4} size={180} />
      <Line x={660} y={820} delay={1.6} style={{ ...TYPE.subtitle, color: WHITE }} width={1180}>
        증상 → 병원 → 진단 → 보건소 → 질병관리청.<br/>
        뉴스가 도달할 즈음엔, 지역 확산은 이미 시작됐다.
      </Line>
    </>
  );
}

function TimelineBar({ x, y, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 1.4)));
  const stages = [
    { label: '증상', days: 3, w: 150 },
    { label: '병원 · 진단', days: 2, w: 170 },
    { label: '보건소 보고', days: 4, w: 200 },
    { label: '질병관리청 집계', days: 5, w: 240 },
  ];
  let offset = 0;
  return (
    <>
      <div style={{ position:'absolute', left:x, top:y, width: 760 * p, height: 2, background: WHITE_15 }} />
      {stages.map((s, i) => {
        const segP = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - i*0.25) / 0.6)));
        const node = (
          <React.Fragment key={i}>
            <div style={{ position:'absolute', left:x+offset, top:y-6, width: s.w * segP, height: 14, background: i === stages.length-1 ? ACCENT : 'rgba(255,255,255,0.3)' }} />
            <div style={{ position:'absolute', left:x+offset, top:y+30, color: WHITE, fontFamily: FONT, fontSize: 22, fontWeight: 500, opacity: segP }}>{s.label}</div>
            <div style={{ position:'absolute', left:x+offset, top:y+62, color: WHITE_45, fontFamily: FONT, fontSize: 20, opacity: segP }}>{s.days}일</div>
          </React.Fragment>
        );
        offset += s.w + 20;
        return node;
      })}
    </>
  );
}

// ----- S03 3-Layer -----
function S03() {
  return (
    <>
      <Chrome index={3} label="03 · SOLUTION" />
      <Line x={120} y={140} style={TYPE.eyebrow}>해법</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>세 가지 흔적을 먼저 읽는다.</Line>
      <Line x={120} y={330} delay={0.3} style={TYPE.subtitle} width={1500}>
        시민이 평소에 남기는 생활 신호 — 약국 · 하수 · 검색.
      </Line>

      <LayerCard x={120}  y={500} delay={0.7} name="약국 OTC"   source="네이버 쇼핑인사이트 · 130건" lead="−2주" />
      <LayerCard x={720}  y={500} delay={0.9} name="하수 바이러스" source="질병관리청 KOWAS · 952건"    lead="−3주" hero />
      <LayerCard x={1320} y={500} delay={1.1} name="검색 트렌드" source="네이버 데이터랩 · 130건"   lead="−1주" />
    </>
  );
}

function LayerCard({ x, y, delay, name, source, lead, hero }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.7)));
  const numAppear = Easing.easeOutCubic(Math.max(0, Math.min(1, (t - 0.3) / 0.6)));
  return (
    <div style={{
      position:'absolute', left:x, top:y, width: 480, height: 440,
      border: `1px solid ${hero ? ACCENT : WHITE_15}`,
      background: `rgba(5,7,11,${hero ? 0.65 : 0.45})`,
      backdropFilter:'blur(8px)',
      opacity: p, transform:`translateY(${(1-p)*20}px)`,
      padding: 36, boxSizing:'border-box', fontFamily: FONT,
    }}>
      <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45 }}>0{name==='약국 OTC'?1:name==='하수 바이러스'?2:3}</div>
      <div style={{ marginTop: 14, ...TYPE.body, fontSize: 40, fontWeight: 600, color: WHITE }}>{name}</div>
      <div style={{ marginTop: 6, ...TYPE.small, color: WHITE_70 }}>{source}</div>
      <div style={{ position:'absolute', left: 36, bottom: 36, opacity: numAppear }}>
        <div style={{ fontSize: 130, fontWeight: 700, color: hero ? ACCENT : WHITE, letterSpacing:'-0.05em', lineHeight: 0.9, fontFeatureSettings:'"lnum"' }}>{lead}</div>
        <div style={{ marginTop: 10, ...TYPE.small }}>병원 기록 대비 선행</div>
      </div>
    </div>
  );
}

// ----- S04 Cross-validate -----
function S04() {
  return (
    <>
      <Chrome index={4} label="04 · CROSS-VALIDATION" />
      <Line x={120} y={140} style={TYPE.eyebrow}>왜 3개인가</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>하나만 오르면 무시,</Line>
      <Line x={120} y={310} delay={0.3} style={{ ...TYPE.title, color: ACCENT }} width={1700}>같이 오를 때만 경보.</Line>

      {/* Left: failure */}
      <Plate x={120} y={480} width={820} height={480} delay={0.7}>
        <div style={{ padding: 40, position: 'relative', height: '100%', boxSizing: 'border-box', fontFamily: FONT }}>
          <div style={{ ...TYPE.label }}>2013 · 실패 사례</div>
          <div style={{ fontSize: 38, fontWeight: 700, marginTop: 10, color: WHITE, letterSpacing: '-0.02em' }}>Google Flu Trends</div>
          <div style={{ fontSize: 17, marginTop: 8, color: WHITE_70, lineHeight: 1.5, maxWidth: 700 }}>
            검색 단일 신호로 독감 예측 — 뉴스·알고리즘 변화에 흔들려
            <span style={{ color: '#ef4444', fontWeight: 700 }}> 실제 발생의 2배 과대예측</span> 후 서비스 종료.
          </div>

          <GoogleFluComparison delay={1.0} />

          <div style={{
            position: 'absolute', left: 40, bottom: 20,
            fontSize: 14, color: WHITE_45, fontStyle: 'italic',
          }}>
            출처: Lazer et al. (2014) <span style={{ color: WHITE_70 }}>Science</span>
          </div>
        </div>
      </Plate>

      {/* Right: our design — venn diagram + rule + result */}
      <Plate x={980} y={480} width={820} height={480} delay={1.0}>
        <div style={{ padding: 48, fontFamily: FONT, position: 'relative', height: '100%', boxSizing: 'border-box' }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>OUR DESIGN</div>
          <div style={{ fontSize: 44, fontWeight: 600, marginTop: 14, color: WHITE, letterSpacing: '-0.02em' }}>3-Layer Ensemble</div>
          <div style={{ ...TYPE.small, marginTop: 12, maxWidth: 360, color: WHITE_70 }}>
            약국·하수·검색 — 셋이 같이 오를 때만 경보.
          </div>

          {/* 룰 박스 — 게이트 B 핵심 한 줄 */}
          <div style={{
            position: 'absolute', left: 48, bottom: 124,
            padding: '14px 18px',
            background: 'rgba(34,227,255,0.08)',
            borderLeft: `2px solid ${ACCENT}`,
            maxWidth: 420,
          }}>
            <div style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>핵심 룰</div>
            <div style={{ marginTop: 6, fontSize: 19, color: WHITE, fontWeight: 500, lineHeight: 1.4 }}>
              2개 이상 계층이 동시에 30점 이상 → YELLOW
            </div>
          </div>

          {/* 결과 수치 */}
          <div style={{ position: 'absolute', left: 48, bottom: 48 }}>
            <div style={{ ...TYPE.label, color: WHITE_45 }}>결과</div>
            <div style={{ marginTop: 6, fontSize: 22, color: WHITE, fontWeight: 600, fontFeatureSettings: '"lnum"' }}>
              오경보 <span style={{ color: WHITE_45, textDecoration: 'line-through' }}>0.602</span>
              <span style={{ margin: '0 10px', color: ACCENT }}>→</span>
              <span style={{ color: ACCENT }}>0.206</span>
            </div>
          </div>
        </div>
        <VennMotif cx={980+620} cy={480+260} delay={1.4} />
      </Plate>
    </>
  );
}

// 단순 비교 막대 — "실제 1× vs Google 2× 과대예측" 직관적 시각화
function GoogleFluComparison({ delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const cdcP   = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.8)));
  const googP  = Easing.easeOutCubic(Math.max(0, Math.min(1, (t - 0.4) / 1.0)));
  const labelP = Easing.easeOutCubic(Math.max(0, Math.min(1, (t - 1.2) / 0.5)));

  return (
    <div style={{
      position: 'absolute', left: 40, bottom: 90, right: 40,
      fontFamily: FONT,
    }}>
      {/* CDC 실측 — 1× */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <div style={{ width: 110, fontSize: 14, color: WHITE_70 }}>CDC 실측</div>
        <div style={{ flex: 1, height: 26, background: 'rgba(255,255,255,0.06)', position: 'relative' }}>
          <div style={{
            position: 'absolute', left: 0, top: 0, bottom: 0,
            width: `${50 * cdcP}%`,
            background: WHITE_70,
            transition: 'none',
          }} />
        </div>
        <div style={{ width: 50, fontSize: 18, color: WHITE, fontWeight: 600, textAlign: 'right', opacity: cdcP }}>1×</div>
      </div>

      {/* Google 예측 — 2× (빨강·강조) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
        <div style={{ width: 110, fontSize: 14, color: '#ef4444', fontWeight: 600 }}>Google 예측</div>
        <div style={{ flex: 1, height: 26, background: 'rgba(255,255,255,0.06)', position: 'relative' }}>
          <div style={{
            position: 'absolute', left: 0, top: 0, bottom: 0,
            width: `${100 * googP}%`,
            background: '#ef4444',
          }} />
        </div>
        <div style={{ width: 50, fontSize: 22, color: '#ef4444', fontWeight: 800, textAlign: 'right', opacity: googP }}>2×</div>
      </div>

      {/* 메시지 한 줄 */}
      <div style={{
        marginTop: 10, padding: '10px 14px',
        background: 'rgba(239,68,68,0.10)', borderLeft: `2px solid #ef4444`,
        fontSize: 14, color: WHITE, lineHeight: 1.5,
        opacity: labelP, transform: `translateY(${(1-labelP)*6}px)`,
      }}>
        <span style={{ color: '#ef4444', fontWeight: 700 }}>핵심 교훈</span>
        <span style={{ color: WHITE_45, margin: '0 6px' }}>—</span>
        단일 신호는 외부 변동(뉴스·알고리즘)에 그대로 흔들린다.
      </div>
    </div>
  );
}

function GoogleFluChart({ delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 1.4)));
  // 절대 위치 — Plate 안 padding 안쪽 좌하단
  const W = 360, H = 170;
  // CDC 실측 (정상 곡선) vs Google 과대예측 (큰 봉우리)
  const cdc = [], goog = [];
  const n = 40;
  for (let i = 0; i < n; i++) {
    const x = i / (n - 1);
    // CDC: 단일 봉우리 30~55
    const cy_ = 0.55 + 0.32 * Math.exp(-Math.pow((x - 0.55) * 4.0, 2));
    // Google: 같은 시기 폭주 (약 2배)
    const gy = 0.45 + 0.62 * Math.exp(-Math.pow((x - 0.55) * 4.0, 2)) + 0.04 * Math.sin(x * 12);
    cdc.push([x * W, H - cy_ * H]);
    goog.push([x * W, H - Math.min(0.95, gy) * H]);
  }
  const visible = Math.max(2, Math.floor(n * p));
  const path = (pts) => pts.slice(0, visible).map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt[0].toFixed(1)} ${pt[1].toFixed(1)}`).join(' ');

  return (
    <div style={{
      position: 'absolute', left: 48, bottom: 80, width: W + 8, height: H + 40,
      fontFamily: FONT,
    }}>
      <svg width={W} height={H + 24} style={{ overflow: 'visible' }}>
        {/* 격자 */}
        <line x1={0} y1={H} x2={W} y2={H} stroke={WHITE_15} strokeWidth={0.8} />
        <line x1={0} y1={0} x2={0} y2={H} stroke={WHITE_15} strokeWidth={0.8} />

        {/* CDC 실측 — 흰색 */}
        <path d={path(cdc)} stroke={WHITE_70} strokeWidth={1.6} fill="none" />
        {/* Google 과대 — accent (마젠타 톤 강조용 — 빨강 사용) */}
        <path d={path(goog)} stroke="#ef4444" strokeWidth={2.0} fill="none" />

        {/* 봉우리에 2× 라벨 */}
        {p > 0.6 && (
          <>
            <line x1={W * 0.55} y1={H - 0.32 * H} x2={W * 0.55} y2={H - Math.min(0.95, 0.62 + 0.45) * H}
              stroke="#ef4444" strokeWidth={0.8} strokeDasharray="3 3" opacity={0.6} />
            <text x={W * 0.55 + 8} y={H - 0.55 * H}
              fill="#ef4444" fontSize={28} fontWeight={700}
              fontFamily='"Helvetica Neue", sans-serif'>2×</text>
          </>
        )}
      </svg>

      {/* 범례 */}
      <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 14, height: 2, background: WHITE_70 }} />
          <span style={{ color: WHITE_70 }}>CDC 실측</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 14, height: 2, background: '#ef4444' }} />
          <span style={{ color: '#ef4444', fontWeight: 600 }}>Google 예측</span>
        </div>
        <div style={{ marginLeft: 'auto', color: WHITE_45, fontFamily: CODE_FONT, fontSize: 10 }}>2012-13 시즌</div>
      </div>
    </div>
  );
}

function VennMotif({ cx, cy, delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 1.0)));
  // 3원 라벨 (약국 / 하수 / 검색)
  const labels = [
    { x: cx - 70, y: cy - 110, text: '약국' },
    { x: cx + 70, y: cy - 110, text: '하수' },
    { x: cx,      y: cy + 110, text: '검색' },
  ];
  return (
    <svg style={{ position:'absolute', left:0, top:0, width:1920, height:1080, pointerEvents:'none', overflow:'visible' }}>
      <circle cx={cx-50} cy={cy-30} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      <circle cx={cx+50} cy={cy-30} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      <circle cx={cx}    cy={cy+50} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      {/* 교집합 강조 점 */}
      <circle cx={cx}    cy={cy+8}  r={8*p}  fill={ACCENT} />
      {/* 라벨 */}
      {labels.map((l, i) => (
        <text key={i} x={l.x} y={l.y}
          fill={WHITE} opacity={p}
          fontFamily='"Helvetica Neue", Helvetica, sans-serif'
          fontSize={20} fontWeight={500}
          textAnchor="middle" dominantBaseline="middle">
          {l.text}
        </text>
      ))}
      {/* 교집합 라벨 */}
      <text x={cx} y={cy+8}
        fill="#05070B" opacity={p}
        fontFamily='"Helvetica Neue", Helvetica, sans-serif'
        fontSize={11} fontWeight={700}
        textAnchor="middle" dominantBaseline="middle">
        ALERT
      </text>
    </svg>
  );
}

// ----- S05 Architecture (단일 가로 흐름 · 6단계 · 좌우 패딩 균등) -----
// 캔버스 1920, 좌우 패딩 100 → 활용 폭 1720. 노드 6 × 240 + gap 5 × 56 = 1720 정확히.
const NODE_W = 240;
const NODE_H = 100;
const NODE_Y = 530;

function S05() {
  // 6단계 단일 가로 흐름 (좌→우)
  const nodes = [
    { label: '입력 · 3계층',         sub: '약국 · 하수 · 검색',          x: 100,  y: NODE_Y },
    { label: 'Kafka',                 sub: '실시간 메시지 큐 (7일 보관)', x: 396,  y: NODE_Y },
    { label: 'TimescaleDB',           sub: '시계열 DB (주 단위 자동분할)',x: 692,  y: NODE_Y },
    { label: '앙상블 · 게이트 B',     sub: '가중평균 35·40·25 + 차단룰',  x: 988,  y: NODE_Y, accent: true, hero: true },
    { label: 'AI 추론',               sub: '예측 + 이상탐지 + 챗봇',     x: 1284, y: NODE_Y },
    { label: 'Dashboard · 경보',      sub: '실시간 화면 · 4단계 알림',   x: 1580, y: NODE_Y, accent: true },
  ];

  const groups = [
    { label: '01 · INGEST',          x: 100,  width: 240 },
    { label: '02 · STORE · ENSEMBLE', x: 396,  width: 832 },
    { label: '03 · SERVE',           x: 1284, width: 536 },
  ];

  return (
    <>
      <Chrome index={5} label="05 · ARCHITECTURE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>시스템 구조 · 6 단계 흐름</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>데이터는 왼쪽에서,</Line>
      <Line x={120} y={310} delay={0.3} style={{ ...TYPE.title, color: ACCENT }} width={1700}>경보는 오른쪽으로 흐른다.</Line>

      <ArchGroups groups={groups} y={460} delay={0.5} />
      <ArchDiagram nodes={nodes} delay={0.7} />
      <FlowParticles delay={1.5} />
      <AlertDots cx={1580} cy={650} delay={1.9} />
      <ArchFooter delay={2.1} />
    </>
  );
}

// 흐르는 점 — 좌→우 데이터가 실제로 시뮬레이션 되는 느낌
function FlowParticles({ delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  // 화살표 5개 영역 (노드 6개 사이): x 시작·끝, y(=NODE_Y + NODE_H/2 = 580)
  const segs = [
    { x1: 340, x2: 396 },
    { x1: 636, x2: 692 },
    { x1: 932, x2: 988 },
    { x1: 1228, x2: 1284 },
    { x1: 1524, x2: 1580 },
  ];
  const y = NODE_Y + NODE_H / 2; // 580
  // 점이 1.2초 주기로 좌→우 반복
  const period = 1.2;
  const phase = (t % period) / period;
  return (
    <svg style={{ position: 'absolute', inset: 0, width: 1920, height: 1080, pointerEvents: 'none', overflow: 'visible' }}>
      {segs.map((s, i) => {
        // 각 세그먼트마다 0.05 phase 어긋나게
        const local = (phase + i * 0.05) % 1;
        const x = s.x1 + (s.x2 - s.x1) * local;
        const fade = Math.sin(local * Math.PI); // 가운데에서 가장 진함
        return (
          <circle key={i} cx={x} cy={y} r={3.5}
            fill={ACCENT} opacity={fade * 0.85} />
        );
      })}
    </svg>
  );
}

function ArchGroups({ groups, y, delay }) {
  const { localTime } = useSprite();
  return (
    <>
      {groups.map((g, i) => {
        const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - i * 0.08) / 0.5)));
        return (
          <div key={i} style={{
            position: 'absolute', left: g.x, top: y, width: g.width,
            opacity: p, transform: `translateY(${(1-p)*-6}px)`,
          }}>
            <div style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>{g.label}</div>
            <div style={{ marginTop: 6, height: 1, background: ACCENT, opacity: 0.4 }} />
          </div>
        );
      })}
    </>
  );
}

function ArchDiagram({ nodes, delay }) {
  const { localTime } = useSprite();
  return (
    <>
      {nodes.map((n, i) => {
        const t = Math.max(0, localTime - delay - i * 0.08);
        const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.5)));
        const isAccent = !!n.accent;
        const isHero = !!n.hero;
        const w = n.w || NODE_W;
        return (
          <div key={i} style={{
            position:'absolute', left: n.x, top: n.y,
            width: w, height: NODE_H,
            padding: '12px 16px',
            boxSizing: 'border-box',
            border: `1px solid ${isAccent ? ACCENT : WHITE_15}`,
            background: isAccent
              ? (isHero ? 'rgba(34,227,255,0.16)' : ACCENT)
              : 'rgba(5,7,11,0.72)',
            color: isAccent && !isHero ? '#05070B' : WHITE,
            fontFamily: FONT,
            opacity: p, transform:`translateY(${(1-p)*10}px)`,
            textAlign: 'left',
            boxShadow: isHero ? `0 0 18px rgba(34,227,255,0.22)` : 'none',
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
          }}>
            <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{n.label}</div>
            <div style={{
              fontSize: 13, marginTop: 3,
              color: isAccent && !isHero ? 'rgba(5,7,11,0.7)' : WHITE_70,
              fontFamily: CODE_FONT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>{n.sub}</div>
          </div>
        );
      })}
      <ArchLines delay={delay + 0.5} />
    </>
  );
}

// 노드 박스 가장자리 좌표 헬퍼 (x, y는 박스 좌상단)
const RIGHT = (n) => n.x + (n.w || NODE_W);
const LEFT = (n) => n.x;
const MIDY = (n) => n.y + NODE_H / 2;

function ArchLines({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 1.0)));

  // 6단계 단일 가로 흐름 (y=580 일직선)
  // 노드 우측 끝 / 다음 노드 좌측: 340→396 / 636→692 / 932→988 / 1228→1284 / 1524→1580
  const Y = 580;
  const lines = [
    [340,  Y, 396,  Y, 'JSON · 정규화 0~100'],
    [636,  Y, 692,  Y, '주 단위 INSERT'],
    [932,  Y, 988,  Y, 'weekly snapshot'],
    [1228, Y, 1284, Y, 'composite + 5피처'],
    [1524, Y, 1580, Y, '예측 + 경보'],
  ];

  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none', overflow: 'visible' }}>
      {lines.map(([x1,y1,x2,y2,label], i) => {
        const ex = x1 + (x2-x1)*p;
        const ey = y1 + (y2-y1)*p;
        // 화살표 머리 polygon (도착 도달 시)
        const arrived = p > 0.97;
        const dx = x2 - x1, dy = y2 - y1;
        const len = Math.hypot(dx, dy) || 1;
        const ux = dx / len, uy = dy / len;
        const ax = x2 - 8 * ux, ay = y2 - 8 * uy;
        const wx = -uy * 4, wy = ux * 4; // 수직 벡터
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={ex} y2={ey}
              stroke={ACCENT} strokeWidth={1.3} opacity={0.7}
              strokeDasharray="5 5" />
            {arrived && (
              <polygon
                points={`${x2},${y2} ${ax+wx},${ay+wy} ${ax-wx},${ay-wy}`}
                fill={ACCENT} opacity={0.85} />
            )}
            {label && p > 0.85 && (
              <text x={(x1+x2)/2}
                y={y1 === y2 ? (y1 - NODE_H/2 - 14) : (Math.min(y1, y2) - 14)}
                fill={ACCENT} opacity={0.9}
                fontFamily={CODE_FONT} fontSize={12}
                textAnchor="middle">{label}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function AlertDots({ cx, cy, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  const dots = [
    { c: '#22c55e', label: 'GREEN' },
    { c: '#eab308', label: 'YELLOW' },
    { c: '#f97316', label: 'ORANGE' },
    { c: '#ef4444', label: 'RED' },
  ];
  // Dashboard 노드 (x=1580, w=240) 아래 정렬 — 폭 240
  return (
    <div style={{
      position: 'absolute', left: cx, top: cy, width: 240,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: CODE_FONT, fontSize: 11,
      opacity: p, transform: `translateY(${(1-p)*6}px)`,
    }}>
      {dots.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: d.c, display: 'inline-block' }} />
          <span style={{ color: WHITE_70, letterSpacing: '0.08em' }}>{d.label}</span>
        </div>
      ))}
    </div>
  );
}

function ArchFooter({ delay }) {
  const cells = [
    { tag: 'INGEST',   text: '수집·정규화·적재 = 데이터 우체통 + 시계열 DB' },
    { tag: 'ENSEMBLE', text: '앙상블 + 게이트 B = 단일신호 차단 룰을 코드로 강제' },
    { tag: 'SERVE',    text: 'TFT 7·14·21d · AE 99p · RAG Claude + Qdrant top-5' },
  ];
  // 좌우 패딩 100 균등, gap 24
  return (
    <div style={{
      position: 'absolute', left: 100, top: 800, right: 100,
      display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24,
    }}>
      {cells.map((c, i) => <ArchFooterCell key={i} {...c} delay={delay + i * 0.12} />)}
    </div>
  );
}

function ArchFooterCell({ tag, text, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      padding: '14px 18px',
      background: 'rgba(5,7,11,0.55)',
      borderLeft: `2px solid ${ACCENT}`,
      opacity: p, transform: `translateY(${(1-p)*10}px)`,
      fontFamily: FONT,
    }}>
      <div style={{ ...TYPE.label, color: ACCENT, fontSize: 12 }}>{tag}</div>
      <div style={{ marginTop: 6, fontSize: 16, color: WHITE_70, lineHeight: 1.45 }}>{text}</div>
    </div>
  );
}

// ----- S06 Original proposal -----
function S06() {
  return (
    <>
      <Chrome index={6} label="06 · ORIGINAL PROPOSAL" />
      <Line x={120} y={140} style={TYPE.eyebrow}>공모전 시점 · 2026.03</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>공모전 제안서의 수치.</Line>

      <Plate x={120} y={400} width={820} height={560} delay={0.5}>
        <div style={{ padding: 56 }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>🏆 한국능률협회 (KMA)</div>
          <div style={{ ...TYPE.label, color: ACCENT, marginTop: 6 }}>AI 아이디어 공모전 · 대상 1위</div>
          <div style={{ marginTop: 28, ...TYPE.body, fontSize: 36, color: WHITE }}>3-Layer Ensemble v0.1</div>
          <div style={{ marginTop: 18, ...TYPE.subtitle, fontSize: 26, maxWidth: 640 }}>
            제안 단계의 단일 임계값 최적화 수치.<br/>
            다음 장에서 엄격한 재측정 결과로 정정.
          </div>
        </div>
      </Plate>

      <Plate x={980} y={400} width={820} height={560} delay={0.8}>
        <div style={{ padding: 56, fontFamily: FONT }}>
          <ProposalRow label="F1-Score" value="0.71" delay={1.0} />
          <ProposalRow label="오경보" value="0건" delay={1.2} />
          <ProposalRow label="선행 시간" value="14일" delay={1.4} />
          <ProposalRow label="검증 태스크" value="단일 holdout" delay={1.6} dim />
          <ProposalRow label="재현 스크립트" value="없음" delay={1.8} dim />
        </div>
      </Plate>
    </>
  );
}
function ProposalRow({ label, value, delay, dim }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      display:'flex', justifyContent:'space-between', alignItems:'baseline',
      padding: '18px 0', borderBottom:`1px solid ${WHITE_15}`,
      opacity: p,
    }}>
      <span style={{ fontSize: 26, color: WHITE_70, fontWeight: 400 }}>{label}</span>
      <span style={{ fontSize: 42, color: dim ? WHITE_45 : WHITE, fontWeight: 600, fontFeatureSettings:'"lnum"' }}>{value}</span>
    </div>
  );
}

// ----- S07 Honest correction -----
function S07() {
  return (
    <>
      <Chrome index={7} label="07 · HONEST CORRECTION" />
      <Line x={120} y={140} style={TYPE.eyebrow}>솔직한 정정</Line>

      <Line x={120} y={290} delay={0.2} style={{ ...TYPE.mega, fontSize: 200, color: WHITE_45 }}>0.71</Line>
      <ArrowSweep delay={1.0} />
      <Line x={1100} y={290} delay={1.4} style={{ ...TYPE.mega, fontSize: 200, color: ACCENT }}>0.882</Line>

      <Line x={120} y={560} delay={0.3} style={TYPE.label}>공모전 수치 · 단일 holdout</Line>
      <Line x={1100} y={560} delay={1.5} style={{ ...TYPE.label, color: ACCENT }}>Walk-forward · 재현 가능</Line>

      <Plate x={120} y={720} width={1680} height={220} delay={1.8}>
        <div style={{ padding: '48px 56px', fontFamily: FONT }}>
          <div style={{ fontSize: 44, fontWeight: 600, color: WHITE, letterSpacing:'-0.02em' }}>
            D-7 Precision <span style={{ color: ACCENT }}>1.000</span>은 양성 예측이 희소했던 결과 — 17지역 5-fold로 확장 후 <span style={{ color: ACCENT }}>F1 0.882 · Recall 0.837 · MCC 0.595</span> 안정화.
          </div>
          <div style={{ marginTop: 16, fontSize: 28, color: WHITE_70 }}>
            수치를 지키는 것보다 <span style={{ color: ACCENT }}>재현 가능성</span>이 B2G의 본질이다.
          </div>
        </div>
      </Plate>
    </>
  );
}

function ArrowSweep({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none' }}>
      <line x1={620} y1={400} x2={620 + 420*p} y2={400} stroke={ACCENT} strokeWidth={2} />
      {p > 0.95 && <polygon points={`${1040},${400} ${1020},${390} ${1020},${410}`} fill={ACCENT} />}
    </svg>
  );
}

// ----- S08 Scope changes -----
function S08() {
  const removed = ['GKE 프로덕션 클러스터', 'Next.js 상용 배포', '"F1 0.71·오경보 0" 주장', '질병관리청 실연동', '다국어 i18n', '모바일 앱', '멀티리전 스케일링'];
  const added   = [
    '17지역 walk-forward 백테스트 + 재현 스크립트',
    '교차검증 게이트 B — 단일신호 차단 코드 강제',
    'KOWAS PDF 픽셀 RGB 자동 파서 · 72 PDF',
    'Granger 인과검정 + CCF 리포트 (p=0.021)',
    'TFT 70K params 실데이터 + Attention top-3',
    'RAG 9섹션 KDCA 표준 (Claude + Qdrant 17 docs)',
    'Next.js 17지역 지도 + SSE 실시간 리포트',
    'pytest 128 + GitHub Actions CI 통과',
  ];
  return (
    <>
      <Chrome index={8} label="08 · SCOPE DELTA" />
      <Line x={120} y={140} style={TYPE.eyebrow}>범위 변경</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>뺀 것과 추가한 것.</Line>

      <Plate x={120} y={380} width={820} height={580} delay={0.5}>
        <div style={{ padding: 44, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: WHITE_45 }}>── REMOVED · 7</div>
          <div style={{ marginTop: 28 }}>
            {removed.map((it, i) => <ScopeItem key={i} text={it} delay={0.8 + i*0.08} strike />)}
          </div>
        </div>
      </Plate>

      <Plate x={980} y={380} width={820} height={580} delay={0.7}>
        <div style={{ padding: 44, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>++ ADDED · 8</div>
          <div style={{ marginTop: 28 }}>
            {added.map((it, i) => <ScopeItem key={i} text={it} delay={1.0 + i*0.08} accent />)}
          </div>
        </div>
      </Plate>
    </>
  );
}
function ScopeItem({ text, delay, accent, strike }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      fontSize: 24, padding: '10px 0', color: strike ? WHITE_45 : WHITE, fontWeight: 400,
      opacity: p, transform: `translateX(${(1-p)*-12}px)`,
      textDecoration: strike ? 'line-through' : 'none', textDecorationColor: WHITE_15,
    }}>
      <span style={{ color: accent ? ACCENT : WHITE_45, marginRight: 14, fontFeatureSettings:'"lnum"' }}>
        {String(0).padStart(2,'0')}
      </span>
      {text}
    </div>
  );
}

// (S09 Module Progress 제거 — 2026-05-05 다이어트, 검증 라인은 S11 하단으로 흡수)

// ----- S10 Demo (강화 — 진짜 대시보드 mock UI + STACK) -----
function S10() {
  return (
    <>
      <Chrome index={10} label="10 · DEMO" />
      <Line x={120} y={140} style={TYPE.eyebrow}>데모 · 김나영</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>Next.js 대시보드.</Line>

      {/* 좌측 — 진짜 대시보드 모형 (1020×580) */}
      <DashboardMock x={120} y={380} width={1020} height={580} delay={0.4} />

      {/* 우측 — 기술 스택 + 왜 이 방식 */}
      <Plate x={1180} y={380} width={620} height={580} delay={0.6}>
        <div style={{ padding: 32, fontFamily: FONT, height: '100%', boxSizing: 'border-box', position: 'relative' }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>STACK</div>

          <div style={{ marginTop: 14 }}>
            <StackRow tech="Next.js 14"  reason="App Router · SSR로 SEO + CSR 전환 빠름" delay={1.0} />
            <StackRow tech="Deck.gl v9"  reason="17개 시·도 위·경도 3D 히트맵" delay={1.15} hero />
            <StackRow tech="SSE"         reason="단방향 실시간 충분 · WebSocket 과잉" delay={1.30} hero />
            <StackRow tech="SWR"         reason="60s revalidateOnFocus · 캐시 자동" delay={1.45} />
            <StackRow tech="Recharts"    reason="시계열·반응형 SVG · 가벼움" delay={1.60} />
            <StackRow tech="Tailwind"    reason="globals.css 색상 토큰 + 반응형" delay={1.75} />
          </div>

          <div style={{ position: 'absolute', left: 32, right: 32, bottom: 28, paddingTop: 18, borderTop: `1px solid ${WHITE_15}` }}>
            <div style={{ ...TYPE.label, color: WHITE_45, fontSize: 12 }}>WHY THIS WAY</div>
            <div style={{ marginTop: 8, fontSize: 17, color: WHITE_70, lineHeight: 1.45 }}>
              17지역 즉시 인지 → 3D 히트맵 · 실시간 리포트 → SSE 스트리밍 ·
              <span style={{ color: ACCENT }}> B2G 신뢰성 = 출처 + 면책 강제</span>
            </div>
          </div>
        </div>
      </Plate>
    </>
  );
}

function StackRow({ tech, reason, delay, hero }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      display: 'flex', gap: 14, alignItems: 'baseline',
      padding: '9px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-8}px)`,
    }}>
      <span style={{
        width: 110, flexShrink: 0,
        fontSize: 16, fontFamily: CODE_FONT,
        color: hero ? ACCENT : WHITE, fontWeight: hero ? 700 : 600,
      }}>{tech}</span>
      <span style={{ fontSize: 15, color: WHITE_70, lineHeight: 1.4 }}>{reason}</span>
    </div>
  );
}
// =============================================================================
// DashboardMock — Next.js 대시보드 풀 mock (헤더 · 사이드바 · 지도 · KPI · 알림)
// =============================================================================
function DashboardMock({ x, y, width, height, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width, height,
      background: '#0B0F18',
      border: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateY(${(1-p)*12}px)`,
      fontFamily: FONT, overflow: 'hidden',
      boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
    }}>
      <DashHeader delay={delay + 0.2} />
      <DashBody delay={delay + 0.4} />
    </div>
  );
}

function DashHeader({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  const blink = (Math.sin(localTime * 4) + 1) / 2;
  return (
    <div style={{
      position: 'relative', height: 44,
      background: 'linear-gradient(90deg, #0E1320 0%, #0B0F18 100%)',
      borderBottom: `1px solid ${WHITE_15}`,
      display: 'flex', alignItems: 'center', padding: '0 18px',
      gap: 16, opacity: p,
    }}>
      <div style={{
        width: 26, height: 26, background: ACCENT, color: '#05070B',
        display: 'grid', placeItems: 'center',
        fontSize: 11, fontWeight: 800, letterSpacing: '0.5px',
      }}>UIS</div>
      <div style={{ fontSize: 13, color: WHITE, fontWeight: 600 }}>Urban Immune System</div>
      <div style={{ fontSize: 11, color: WHITE_45, fontFamily: CODE_FONT }}>v0.4.2 · 2025-W49</div>

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: '#22c55e', opacity: 0.5 + blink*0.5,
          boxShadow: `0 0 ${4+blink*4}px #22c55e`,
        }} />
        <span style={{ fontSize: 11, color: WHITE_70, fontFamily: CODE_FONT, letterSpacing: '0.06em' }}>LIVE · 17 sido</span>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        {['전국', '지역', '트렌드', '이상탐지', '리포트'].map((t, i) => (
          <span key={i} style={{
            fontSize: 11, padding: '5px 9px',
            color: i === 0 ? ACCENT : WHITE_70,
            background: i === 0 ? 'rgba(34,227,255,0.1)' : 'transparent',
            border: `1px solid ${i === 0 ? ACCENT : 'transparent'}`,
            letterSpacing: '0.04em',
          }}>{t}</span>
        ))}
      </div>
    </div>
  );
}

function DashBody({ delay }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 0, height: 'calc(100% - 44px)' }}>
      <DashMapPanel delay={delay} />
      <DashRightCol delay={delay + 0.15} />
    </div>
  );
}

function DashMapPanel({ delay }) {
  return (
    <div style={{ position: 'relative', padding: '14px 16px', borderRight: `1px solid ${WHITE_15}` }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 13, color: WHITE, fontWeight: 600 }}>전국 위험도 · 17개 시·도</div>
          <div style={{ fontSize: 10, color: WHITE_45, fontFamily: CODE_FONT, marginTop: 2 }}>Deck.gl heatmap · weekly · 2025-W49</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 9, fontFamily: CODE_FONT }}>
          {[
            { c: '#22c55e', l: 'GREEN' },
            { c: '#eab308', l: 'YELLOW' },
            { c: '#f97316', l: 'ORANGE' },
            { c: '#ef4444', l: 'RED' },
          ].map((it, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: it.c }} />
              <span style={{ color: WHITE_70 }}>{it.l}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ position: 'relative', marginTop: 10, height: 320 }}>
        <SidoMap delay={delay} />
      </div>

      <DashTrendChart delay={delay + 0.6} />
    </div>
  );
}

// 17 시·도 약식 좌표 (1020 폭의 좌측 패널 기준 — 패널 내 픽셀)
const SIDO = [
  { name: '서울',  x: 360, y: 90,  level: 2 },
  { name: '인천',  x: 318, y: 92,  level: 2 },
  { name: '경기',  x: 372, y: 105, level: 1 },
  { name: '강원',  x: 470, y: 90,  level: 0 },
  { name: '충북',  x: 405, y: 145, level: 1 },
  { name: '세종',  x: 380, y: 165, level: 1 },
  { name: '대전',  x: 392, y: 180, level: 0 },
  { name: '충남',  x: 340, y: 165, level: 0 },
  { name: '경북',  x: 488, y: 165, level: 1 },
  { name: '전북',  x: 348, y: 215, level: 0 },
  { name: '대구',  x: 478, y: 200, level: 1 },
  { name: '울산',  x: 522, y: 215, level: 0 },
  { name: '경남',  x: 460, y: 240, level: 0 },
  { name: '광주',  x: 322, y: 252, level: 0 },
  { name: '전남',  x: 332, y: 275, level: 0 },
  { name: '부산',  x: 510, y: 248, level: 3 },
  { name: '제주',  x: 322, y: 320, level: 2 },
];
const LVL_COLORS = ['#22c55e', '#eab308', '#f97316', '#ef4444'];

function SidoMap({ delay }) {
  const { localTime } = useSprite();
  return (
    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} viewBox="0 0 700 340" preserveAspectRatio="xMidYMid meet">
      {/* 배경 그리드 */}
      <g opacity={0.15}>
        {Array.from({ length: 14 }).map((_, i) => (
          <line key={`v${i}`} x1={i*50} y1={0} x2={i*50} y2={340} stroke={WHITE_15} strokeWidth={0.5} />
        ))}
        {Array.from({ length: 7 }).map((_, i) => (
          <line key={`h${i}`} x1={0} y1={i*50} x2={700} y2={i*50} stroke={WHITE_15} strokeWidth={0.5} />
        ))}
      </g>

      {SIDO.map((s, i) => {
        const t = Math.max(0, localTime - delay - i * 0.04);
        const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.4)));
        const c = LVL_COLORS[s.level];
        const isHot = s.level >= 2;
        const pulse = isHot ? (Math.sin(localTime * 3 + i) + 1) / 2 : 0;
        return (
          <g key={i} opacity={p}>
            {isHot && (
              <circle cx={s.x} cy={s.y} r={14 + pulse * 8}
                fill={c} opacity={0.18 + pulse * 0.15} />
            )}
            <circle cx={s.x} cy={s.y} r={s.level >= 2 ? 8 : 5} fill={c} opacity={0.95} />
            <text x={s.x + 12} y={s.y + 4}
              fill={isHot ? c : WHITE_70} fontSize={10} fontWeight={isHot ? 700 : 500}
              fontFamily='"Helvetica Neue", Helvetica, sans-serif'>{s.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

function DashTrendChart({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  // 26주 곡선 mock
  const W = 660, H = 78;
  const pts = Array.from({ length: 26 }).map((_, i) => {
    const t = i / 25;
    // 겨울 피크 시뮬레이션
    const y = 30 + 50 * Math.exp(-Math.pow((t - 0.7) * 3.5, 2)) + Math.sin(i * 0.7) * 4;
    return { x: t * W, y: H - (y / 100) * H };
  });
  const visible = Math.floor(pts.length * p);
  const path = pts.slice(0, Math.max(2, visible)).map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(' ');
  return (
    <div style={{ marginTop: 12, padding: '10px 12px', background: 'rgba(5,7,11,0.5)', border: `1px solid ${WHITE_15}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ fontSize: 11, color: WHITE, fontWeight: 600 }}>composite_score (서울특별시 · 26주)</div>
        <div style={{ fontSize: 10, color: ACCENT, fontFamily: CODE_FONT }}>Recharts · weekly</div>
      </div>
      <svg width={W} height={H + 8} style={{ marginTop: 6, display: 'block' }}>
        {/* 임계 라인 */}
        <line x1={0} y1={H * 0.45} x2={W} y2={H * 0.45} stroke="#eab308" strokeWidth={0.5} strokeDasharray="3 3" opacity={0.6} />
        <line x1={0} y1={H * 0.25} x2={W} y2={H * 0.25} stroke="#ef4444" strokeWidth={0.5} strokeDasharray="3 3" opacity={0.6} />
        <path d={path} stroke={ACCENT} strokeWidth={1.5} fill="none" />
        {visible > 1 && (
          <circle cx={pts[visible-1].x} cy={pts[visible-1].y} r={3} fill={ACCENT} />
        )}
      </svg>
    </div>
  );
}

function DashRightCol({ delay }) {
  return (
    <div style={{ padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      <KpiCard label="현재 위험도" value="42.7" sub="composite · 전주 +8.4%" color="#eab308" delay={delay} />
      <KpiCard label="14일 예측" value="58.1" sub="TFT · 95% CI 51~65" color={ACCENT} delay={delay + 0.1} />
      <ReportPreview delay={delay + 0.2} />
      <AnomalyTag delay={delay + 0.3} />
    </div>
  );
}

function KpiCard({ label, value, sub, color, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      padding: '10px 12px',
      background: 'rgba(5,7,11,0.55)',
      border: `1px solid ${WHITE_15}`,
      borderLeft: `3px solid ${color}`,
      opacity: p, transform: `translateX(${(1-p)*8}px)`,
    }}>
      <div style={{ fontSize: 10, color: WHITE_45, letterSpacing: '0.12em', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color, marginTop: 4, letterSpacing: '-0.02em', fontFeatureSettings: '"lnum"' }}>{value}</div>
      <div style={{ fontSize: 10, color: WHITE_70, marginTop: 2, fontFamily: CODE_FONT }}>{sub}</div>
    </div>
  );
}

function ReportPreview({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  // 텍스트가 한 글자씩 나타나는 SSE 효과
  const total = 84;
  const chars = Math.floor(total * Math.min(1, (localTime - delay - 0.3) / 1.5));
  const text = "서울특별시 위험등급 주의(YELLOW). 약국 OTC와 검색 트렌드 동시 상승…";
  return (
    <div style={{
      padding: '10px 12px',
      background: 'rgba(5,7,11,0.55)', border: `1px solid ${WHITE_15}`,
      opacity: p,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ fontSize: 10, color: ACCENT, letterSpacing: '0.12em', textTransform: 'uppercase' }}>AI Report · SSE</div>
        <div style={{ fontSize: 9, color: WHITE_45, fontFamily: CODE_FONT }}>Claude 4.6</div>
      </div>
      <div style={{ marginTop: 6, fontSize: 11, color: WHITE_70, lineHeight: 1.5, minHeight: 56 }}>
        {text.slice(0, chars)}
        {chars < text.length && <span style={{ color: ACCENT, marginLeft: 1 }}>▍</span>}
      </div>
      <div style={{ marginTop: 4, fontSize: 9, color: WHITE_45, fontFamily: CODE_FONT }}>
        [1] WHO · [2] ECDC · [3] KDCA
      </div>
    </div>
  );
}

function AnomalyTag({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  const pulse = (Math.sin(localTime * 2.5) + 1) / 2;
  return (
    <div style={{
      padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 8,
      background: `rgba(239,68,68,${0.1 + pulse*0.06})`,
      border: `1px solid #ef4444`,
      opacity: p,
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%', background: '#ef4444',
        boxShadow: `0 0 ${4+pulse*4}px #ef4444`, flexShrink: 0,
      }} />
      <div>
        <div style={{ fontSize: 11, color: '#fff', fontWeight: 700 }}>이상탐지 · 부산</div>
        <div style={{ fontSize: 9, color: WHITE_70, marginTop: 2 }}>재구성오차 0.78 (99p ↑)</div>
      </div>
    </div>
  );
}

function MapMotif({ delay }) {
  const { localTime } = useSprite();
  // Grid of dots representing regions
  const cols = 20, rows = 10;
  const cx = 960, cy = 670;
  const spacing = 38;
  const hotspots = [[-5,-2], [3,2], [-1,0], [6,-3]];
  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none' }}>
      {Array.from({length: cols*rows}).map((_, i) => {
        const c = i % cols - cols/2, r = Math.floor(i / cols) - rows/2;
        const t = Math.max(0, localTime - delay - (Math.abs(c) + Math.abs(r)) * 0.03);
        const p = Math.min(1, t / 0.4);
        const isHot = hotspots.some(([hc,hr]) => hc===c && hr===r);
        const pulse = isHot ? (Math.sin(localTime * 3 + i) + 1)/2 : 0;
        return (
          <circle key={i}
            cx={cx + c*spacing} cy={cy + r*spacing}
            r={isHot ? 4 + pulse*3 : 2}
            fill={isHot ? ACCENT : WHITE_45}
            opacity={p * (isHot ? 1 : 0.4)} />
        );
      })}
    </svg>
  );
}

// =============================================================================
// S10A — Phase 2 자동 통합 (이메일·연락처 mock UI · 발표 임팩트)
// =============================================================================
function S10A() {
  return (
    <>
      <Chrome index="10A" label="10A · AUTO-DISPATCH (PHASE 2)" />
      <Line x={120} y={140} style={TYPE.eyebrow}>경보 → 자동 발송 · Phase 2 미리보기</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>관제실은 이렇게 동작한다.</Line>

      <Plate x={120} y={350} width={1080} height={620} delay={0.5}>
        <div style={{ padding: 28, fontFamily: FONT, height: '100%', boxSizing: 'border-box', position: 'relative' }}>
          <AlertModal delay={0.9} />
        </div>
      </Plate>

      <Plate x={1240} y={350} width={560} height={620} delay={0.7}>
        <div style={{ padding: 28, fontFamily: FONT, height: '100%', boxSizing: 'border-box', position: 'relative' }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>수신 채널 · 부처 디렉토리</div>
          <div style={{ ...TYPE.small, fontSize: 13, color: WHITE_70, marginTop: 4 }}>
            경보 레벨별 자동 라우팅 + 어댑터 레이어
          </div>

          <div style={{ marginTop: 18 }}>
            <ContactRow org="질병관리청 (KDCA)"      dept="감염병관리과 · 역학조사과" channel="이메일 · 관제 API" delay={1.1} hero />
            <ContactRow org="서울시 시민건강국"        dept="감염병관리팀"             channel="이메일 · 팩스"     delay={1.3} />
            <ContactRow org="경기도 감염병관리지원단"  dept="역학조사 분야"             channel="이메일 · 관제 API" delay={1.5} />
            <ContactRow org="KCDC 위기소통담당관"      dept="긴급 브리핑 채널"         channel="이메일 · SMS"      delay={1.7} />
            <ContactRow org="WHO 협력센터"             dept="국제 보고 채널"           channel="API (Phase 5)"     delay={1.9} dim />
          </div>

          <div style={{ position: 'absolute', left: 28, right: 28, bottom: 28, paddingTop: 14, borderTop: `1px solid ${WHITE_15}` }}>
            <div style={{ ...TYPE.label, color: WHITE_45, fontSize: 12 }}>경보 라우팅 정책</div>
            <div style={{ marginTop: 6, fontSize: 13, color: WHITE_70, lineHeight: 1.5 }}>
              <span style={{ color: '#eab308', fontWeight: 700 }}>YELLOW</span> 부처 1 ·
              <span style={{ color: '#f97316', fontWeight: 700, marginLeft: 6 }}>ORANGE</span> 부처 3 ·
              <span style={{ color: '#ef4444', fontWeight: 700, marginLeft: 6 }}>RED</span> 전체 + KCDC 위기실
            </div>
          </div>
        </div>
      </Plate>

      <Plate x={120} y={985} width={1680} height={50} delay={2.1} opacity={0.4}>
        <div style={{ padding: '12px 28px', fontFamily: FONT, fontSize: 16, color: WHITE_70, display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ ...TYPE.label, color: ACCENT, fontSize: 12 }}>STATUS</span>
          <span><span style={{ color: ACCENT, fontWeight: 700 }}>Phase 2 (2026 H2)</span> 구현 예정 · 부처별 어댑터 레이어 (이메일·팩스·관제 API 추상화)</span>
        </div>
      </Plate>
    </>
  );
}

function AlertModal({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  const pulse = (Math.sin(localTime * 3) + 1) / 2;
  return (
    <div style={{ opacity: p, transform: `translateY(${(1-p)*16}px) scale(${0.96 + 0.04*p})` }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        padding: '14px 18px',
        background: `rgba(239,68,68,${0.18 + pulse*0.08})`,
        border: `1px solid #ef4444`, marginBottom: 12,
      }}>
        <div style={{
          width: 12, height: 12, borderRadius: '50%', background: '#ef4444',
          boxShadow: `0 0 ${8+pulse*8}px #ef4444`,
        }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', letterSpacing: '-0.01em' }}>RED 경보 발령</div>
          <div style={{ fontSize: 14, color: WHITE_70, marginTop: 3 }}>서울특별시 · 2025-W49 · 종합점수 78.4 / 100</div>
        </div>
        <div style={{
          fontSize: 11, fontFamily: CODE_FONT, color: '#ef4444',
          padding: '4px 8px', border: `1px solid #ef4444`, letterSpacing: '0.1em',
        }}>SEV · CRITICAL</div>
      </div>

      <div style={{
        padding: '14px 18px', marginBottom: 12,
        background: 'rgba(5,7,11,0.6)', borderLeft: `2px solid ${ACCENT}`,
      }}>
        <div style={{ ...TYPE.label, color: ACCENT, fontSize: 12 }}>리포트 미리보기</div>
        <div style={{ marginTop: 8, fontSize: 15, color: WHITE, lineHeight: 1.5 }}>
          서울특별시 인플루엔자 위험등급 <span style={{ color: '#ef4444', fontWeight: 700 }}>심각</span>으로 격상.
          OTC 65 / 하수 71 / 검색 88. 3계층 모두 임계 초과. 역학조사관 즉시 출동 권고.
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ ...TYPE.label, color: ACCENT, fontSize: 12, marginBottom: 8 }}>자동 발송 결과 · 2025-12-08 09:14:03 KST</div>
        <DispatchRow target="KDCA 역학조사과"      channel="이메일 + 관제 API" status="✓ 전송"    delay={delay + 0.4} />
        <DispatchRow target="서울시 시민건강국"     channel="이메일 + 팩스"      status="✓ 전송"    delay={delay + 0.55} />
        <DispatchRow target="KCDC 위기소통담당관"  channel="이메일 + SMS"       status="✓ 전송"    delay={delay + 0.70} />
        <DispatchRow target="WHO 협력센터"         channel="국제 보고 API"      status="○ Phase 5" delay={delay + 0.85} dim />
      </div>

      <div style={{
        padding: '10px 14px',
        background: 'rgba(34,227,255,0.06)', borderLeft: `2px solid ${ACCENT}`,
        fontSize: 13, color: WHITE_70,
      }}>
        <span style={{ color: ACCENT, fontWeight: 600, fontFamily: CODE_FONT, marginRight: 8 }}>ATTACHED</span>
        alert_report.pdf (4쪽 · KDCA 9섹션 · 출처 5건) · timeline_chart.png · regional_map.png
      </div>
    </div>
  );
}

function DispatchRow({ target, channel, status, delay, dim }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  const sent = status.startsWith('✓');
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1.6fr 1.4fr 1fr', gap: 12,
      padding: '8px 12px', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-8}px)`,
    }}>
      <span style={{ fontSize: 14, color: dim ? WHITE_45 : WHITE, fontWeight: 500 }}>{target}</span>
      <span style={{ fontSize: 13, color: WHITE_70, fontFamily: CODE_FONT }}>{channel}</span>
      <span style={{
        fontSize: 13, fontWeight: 700, fontFamily: CODE_FONT, textAlign: 'right',
        color: dim ? WHITE_45 : (sent ? ACCENT : WHITE_70),
      }}>{status}</span>
    </div>
  );
}

function ContactRow({ org, dept, channel, delay, hero, dim }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      padding: '11px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-8}px)`,
    }}>
      <div style={{ fontSize: 16, fontWeight: 600, color: hero ? ACCENT : (dim ? WHITE_45 : WHITE) }}>{org}</div>
      <div style={{ fontSize: 13, color: WHITE_70, marginTop: 3 }}>{dept}</div>
      <div style={{ fontSize: 12, color: WHITE_45, marginTop: 3, fontFamily: CODE_FONT }}>{channel}</div>
    </div>
  );
}

// ----- S11 Metrics — 17지역 백테스트 + Granger -----
function S11() {
  return (
    <>
      <Chrome index={11} label="11 · MEASURED" />
      <Line x={120} y={140} style={TYPE.eyebrow}>실측 성능 · 17지역 백테스트</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>숫자를 있는 그대로.</Line>

      {/* 좌측: 평균 6.47주 mega + 지역별 lead 막대 + 메트릭 5개 */}
      <Plate x={120} y={340} width={1120} height={600} delay={0.5}>
        <div style={{ padding: 32, fontFamily: FONT, position: 'relative', height: '100%', boxSizing: 'border-box' }}>
          {/* 상단 — mega + LeadDistribution 그리드 */}
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 28, alignItems: 'center' }}>
            <div>
              <Line x={0} y={0} delay={0.9} style={{ position: 'static', ...TYPE.mega, fontSize: 150, color: ACCENT }}>6.47</Line>
              <div style={{ fontSize: 22, color: WHITE, fontWeight: 600, letterSpacing: '-0.01em', marginTop: 4 }}>주 선행 평균</div>
              <div style={{ ...TYPE.small, fontSize: 16, color: WHITE_70, marginTop: 4 }}>임상 확진 피크보다 6.47주 전 YELLOW</div>
            </div>
            <LeadDistribution delay={1.1} />
          </div>

          {/* 하단 — 메트릭 5개 */}
          <div style={{ marginTop: 14 }}>
            <MetricRow label="F1-Score · 종합 정확도"           values={['0.882']} delay={1.4} accent />
            <MetricRow label="Precision · 경보 신뢰도"          values={['0.949']} delay={1.55} />
            <MetricRow label="Recall · 놓침 방지율"             values={['0.837']} delay={1.70} />
            <MetricRow label="AUC-ROC · 위험·정상 구분력"       values={['0.931']} delay={1.85} />
            <MetricRow label="오경보율 (게이트 ON · 가짜경보)"  values={['0.206']} delay={2.00} accent header />
          </div>

          <div style={{ position: 'absolute', left: 32, right: 32, bottom: 18, ...TYPE.small, fontSize: 14, color: WHITE_45 }}>
            17개 시·도 walk-forward · gap=4주 · 분석창 26주 · 게이트 OFF 시 FAR 0.602
          </div>
        </div>
      </Plate>

      {/* 우측: Top 5 지역 + Granger */}
      <Plate x={1280} y={360} width={520} height={560} delay={0.7}>
        <div style={{ padding: 36, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>Top 5 — 가장 빨리 잡은 지역</div>
          <div style={{ marginTop: 18 }}>
            <RegionRow region="세종특별자치시" lead="9주" delay={1.0} />
            <RegionRow region="부산광역시"     lead="8주" delay={1.15} />
            <RegionRow region="제주특별자치도" lead="8주" delay={1.30} />
            <RegionRow region="서울특별시"     lead="7주" delay={1.45} />
            <RegionRow region="경기도"         lead="6주" delay={1.60} />
          </div>

          <div style={{ marginTop: 28, paddingTop: 20, borderTop: `1px solid ${WHITE_15}` }}>
            <div style={{ ...TYPE.label, color: ACCENT }}>Granger 인과검정</div>
            <div style={{ marginTop: 14 }}>
              <GrangerRow label="Composite" p="0.021" delay={1.85} />
              <GrangerRow label="L3 검색"    p="0.007" delay={2.00} />
              <GrangerRow label="CCF max"    p="0.601" delay={2.15} />
            </div>
            <div style={{ marginTop: 16, ...TYPE.small, fontSize: 17, color: WHITE_70 }}>
              p &lt; 0.05 — 통계적으로 유의한 선행성
            </div>
          </div>
        </div>
      </Plate>

      {/* 하단 재현 명령 + 검증 배지 — Chrome footer(y=1020) 침범 방지 */}
      <Plate x={120} y={945} width={1680} height={50} delay={2.3} opacity={0.4}>
        <div style={{ padding: '10px 28px', fontFamily: FONT, fontSize: 15, color: WHITE_70, display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>재현</span>
          <span style={{ fontFamily: CODE_FONT, fontSize: 16, color: ACCENT }}>$ python -m ml.reproduce_validation</span>
          <span style={{ color: WHITE_45 }}>·</span>
          <span style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>검증</span>
          <span>pytest 128 통과 · RAG 시드 20건 · KOWAS 17지역 적재 완료</span>
        </div>
      </Plate>
    </>
  );
}

function LeadDistribution({ delay }) {
  const { localTime } = useSprite();
  // 17지역 lead 분포: 9·8·8·7·6·6·6·6·5·5·4·4·4·3·3·3·2 (실제 backtest 기반 추정)
  const leads = [9, 8, 8, 7, 6, 6, 6, 6, 5, 5, 4, 4, 4, 3, 3, 3, 2];
  const max = 9;
  const W = 460, H = 56;
  const barW = W / leads.length - 4;
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ ...TYPE.label, fontSize: 12, color: WHITE_45 }}>지역별 lead (주) · 17 시·도</div>
      <svg width={W} height={H + 18} style={{ marginTop: 6, display: 'block' }}>
        {leads.map((v, i) => {
          const t = Math.max(0, localTime - delay - i * 0.04);
          const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.4)));
          const h = (v / max) * H * p;
          const x = i * (barW + 4);
          const isHero = v >= 7;
          return (
            <g key={i}>
              <rect x={x} y={H - h} width={barW} height={h}
                fill={isHero ? ACCENT : WHITE_70} opacity={isHero ? 0.9 : 0.45} />
              {p > 0.95 && (isHero || v <= 3) && (
                <text x={x + barW/2} y={H + 12}
                  fill={isHero ? ACCENT : WHITE_45}
                  fontSize={10} fontFamily={CODE_FONT}
                  textAnchor="middle">{v}</text>
              )}
            </g>
          );
        })}
        {/* 평균선 */}
        <line x1={0} y1={H - (5.9/max)*H} x2={W} y2={H - (5.9/max)*H}
          stroke={ACCENT} strokeWidth={1} strokeDasharray="3 3" opacity={0.6} />
      </svg>
    </div>
  );
}

function MetricRow({ label, values, delay, accent, header, dim }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      display:'flex', justifyContent:'space-between', alignItems:'baseline',
      padding:'13px 0', borderBottom: header ? `2px solid ${ACCENT}` : `1px solid ${WHITE_15}`,
      opacity: p, fontFeatureSettings:'"lnum"',
    }}>
      <span style={{ fontSize: 24, color: accent ? ACCENT : (dim ? WHITE_45 : WHITE), fontWeight: accent ? 700 : 500 }}>{label}</span>
      <span style={{ fontSize: 36, color: accent ? ACCENT : (dim ? WHITE_45 : WHITE), fontWeight: 600 }}>{values[0]}</span>
    </div>
  );
}

function RegionRow({ region, lead, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      display:'flex', justifyContent:'space-between', alignItems:'baseline',
      padding:'12px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-8}px)`,
    }}>
      <span style={{ fontSize: 19, color: WHITE, fontWeight: 500 }}>{region}</span>
      <span style={{ fontSize: 22, color: ACCENT, fontWeight: 700, fontFeatureSettings:'"lnum"' }}>{lead}</span>
    </div>
  );
}

function GrangerRow({ label, p, delay }) {
  const { localTime } = useSprite();
  const pp = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', padding:'10px 0', opacity: pp }}>
      <span style={{ fontSize: 19, color: WHITE }}>{label}</span>
      <span style={{ fontSize: 22, color: ACCENT, fontWeight: 600, fontFeatureSettings:'"lnum"' }}>p={p}</span>
    </div>
  );
}

// ----- S12 Competitive landscape (2026-05-05 4-quadrant 통합 — S12B 흡수) -----
function S12() {
  const quadrants = [
    {
      pos: 'tl',
      title: 'BlueDot',
      tag: '글로벌 · 민간',
      bullets: ['뉴스·SNS 텍스트 NLP', '9일 선행 (COVID-19)', '운영비 $$$$ · 2014~'],
      tone: 'mid',
    },
    {
      pos: 'tr',
      title: 'HealthMap',
      tag: '美 보스턴소아병원 · 2006~',
      bullets: ['자동 뉴스 스크래핑', '의료 raw 데이터 0', 'SMS 신고 · 부분 단일 신호'],
      tone: 'mid',
    },
    {
      pos: 'bl',
      title: '한국 KCDC ILINet',
      tag: '질병관리청 · 2008~',
      bullets: ['임상 신고 후행 (~2주)', '국가 표본감시 · AI 통합 0건', '2026.03 전략 심포지엄 단계'],
      tone: 'warm',
    },
    {
      pos: 'br',
      title: '★ Urban Immune System',
      tag: '한국 · 캡스톤 · 2026',
      bullets: ['3-Layer 정량 신호 (OTC·하수·검색)', '6.47주 선행 · 게이트 B 교차검증', '한국 first-mover · KIPRIS 미확인'],
      tone: 'hero',
    },
  ];
  return (
    <>
      <Chrome index={12} label="12 · COMPETITIVE LANDSCAPE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>선행 사례 · 자체 조사 — 외부 자문 직전</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>이미 누가, 우리는 어디에 서 있나.</Line>

      <div style={{ position: 'absolute', left: 120, top: 320, right: 120, display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 28, height: 600 }}>
        {quadrants.map((q, i) => <QuadCard key={i} {...q} delay={0.5 + i * 0.18} />)}
      </div>

      <Line x={120} y={950} delay={1.6} style={{ ...TYPE.small, color: WHITE_45 }}>
        KIPRIS 검색 — 3계층(OTC+하수+검색) 동시 결합 특허 미확인 · KDCA·환경부 운영과는 보완 관계.
      </Line>
    </>
  );
}

function QuadCard({ title, tag, bullets, tone, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  const isHero = tone === 'hero';
  const accentColor = isHero ? ACCENT : (tone === 'warm' ? '#F4A261' : WHITE_45);
  return (
    <div style={{
      opacity: p, transform: `translateY(${(1-p)*14}px)`, fontFamily: FONT,
      border: `1px solid ${isHero ? ACCENT : WHITE_15}`,
      background: isHero ? 'rgba(34,227,255,0.08)' : 'rgba(5,7,11,0.45)',
      padding: '24px 28px', boxSizing: 'border-box', position: 'relative',
    }}>
      <div style={{ ...TYPE.label, color: accentColor, fontFamily: CODE_FONT, fontSize: 12 }}>{tag}</div>
      <div style={{
        fontSize: isHero ? 32 : 26, color: isHero ? ACCENT : WHITE,
        fontWeight: isHero ? 700 : 600, marginTop: 10, letterSpacing: '-0.01em',
      }}>{title}</div>
      <div style={{ marginTop: 18 }}>
        {bullets.map((b, i) => {
          const ip = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - 0.35 - i * 0.1) / 0.4)));
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'baseline', gap: 10,
              padding: '8px 0', opacity: ip,
            }}>
              <span style={{ width: 5, height: 5, background: accentColor, flexShrink: 0, marginTop: 8 }} />
              <span style={{ fontSize: 16, color: isHero ? WHITE : WHITE_70, lineHeight: 1.45 }}>{b}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ----- S13 Legal -----
function S13() {
  return (
    <>
      <Chrome index={13} label="13 · LEGAL" />
      <Line x={120} y={140} style={TYPE.eyebrow}>법·규제 · 박정빈</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>정부 납품 통과 조건.</Line>

      <LegalCard x={120}  y={400} delay={0.5} title="ISMS-P 인증"      sub="정보보호 관리체계"   pct={25}   color={WHITE} />
      <LegalCard x={980}  y={400} delay={0.7} title="개인정보보호법"   sub="가명처리 · 시도집계" pct={55}   color={ACCENT} />
      <LegalCard x={120}  y={700} delay={0.9} title="네이버 API 재판매"sub="집계 지표로만 저장"  badge="해결 중" />
      <LegalCard x={980}  y={700} delay={1.1} title="의료기기법 (SaMD)" sub="진단 대체 아님 · 경보 지표" badge="비해당" good />
    </>
  );
}
function LegalCard({ x, y, delay, title, sub, pct, color, badge, good }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  const numP = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - 0.3) / 0.6)));
  return (
    <div style={{
      position:'absolute', left:x, top:y, width: 820, height: 260,
      background:'rgba(5,7,11,0.55)', backdropFilter:'blur(8px)',
      border:`1px solid ${WHITE_15}`, padding: 40, boxSizing:'border-box',
      fontFamily: FONT, opacity: p, transform:`translateY(${(1-p)*14}px)`,
    }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline' }}>
        <div>
          <div style={{ fontSize: 32, fontWeight: 600, color: WHITE }}>{title}</div>
          <div style={{ marginTop: 8, ...TYPE.small, color: WHITE_70 }}>{sub}</div>
        </div>
        {pct != null ? (
          <div style={{ fontSize: 84, fontWeight: 700, color, letterSpacing:'-0.04em', fontFeatureSettings:'"lnum"', opacity: numP }}>
            {Math.round(pct * numP)}%
          </div>
        ) : (
          <div style={{
            padding: '10px 20px', border: `1px solid ${good ? ACCENT : WHITE_45}`,
            color: good ? ACCENT : WHITE, fontSize: 20, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 500,
          }}>{badge}</div>
        )}
      </div>
      {pct != null && (
        <div style={{ marginTop: 42, height: 3, background: WHITE_15 }}>
          <div style={{ height: '100%', width: `${pct * numP}%`, background: color }} />
        </div>
      )}
    </div>
  );
}

// ----- S14 Vision 2027 -----
function S14() {
  return (
    <>
      <Chrome index={14} label="14 · 2027 VISION" />
      <Line x={120} y={140} style={TYPE.eyebrow}>최종 제품 비전 · Phase 5 · 2027</Line>
      <Line x={120} y={240} delay={0.1} style={TYPE.title} width={1700}>인플루엔자는 검증 대상,</Line>
      <Line x={120} y={350} delay={0.3} style={{ ...TYPE.title, color: ACCENT }} width={1700}>다음 팬데믹이 진짜 타깃.</Line>

      {/* Radar motif */}
      <RadarMotif cx={450} cy={720} r={220} delay={0.8} />

      <Plate x={780} y={540} width={1020} height={380} delay={0.6}>
        <div style={{ padding: 40, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>타깃 고객 · 3</div>
          <div style={{ marginTop: 28 }}>
            <CustRow name="질병관리청 (KDCA)" desc="국가 감시 보조 · 국가 R&D" delay={1.0} />
            <CustRow name="서울시 · 광역자치단체" desc="지자체 SaaS · 보건환경연구원" delay={1.2} />
            <CustRow name="WHO 협력센터" desc="국제 벤치마크 · 모델 이식" delay={1.4} />
          </div>
        </div>
      </Plate>
    </>
  );
}
function RadarMotif({ cx, cy, r, delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const sweep = (t * 60) % 360;
  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none' }}>
      {[0.33, 0.66, 1.0].map((k, i) => (
        <circle key={i} cx={cx} cy={cy} r={r*k} fill="none" stroke={ACCENT} strokeWidth={1} opacity={0.25} />
      ))}
      <line x1={cx} y1={cy-r} x2={cx} y2={cy+r} stroke={ACCENT} strokeWidth={1} opacity={0.2} />
      <line x1={cx-r} y1={cy} x2={cx+r} y2={cy} stroke={ACCENT} strokeWidth={1} opacity={0.2} />
      <g transform={`rotate(${sweep} ${cx} ${cy})`}>
        <line x1={cx} y1={cy} x2={cx} y2={cy-r} stroke={ACCENT} strokeWidth={2} />
      </g>
      {/* anomaly blips */}
      <circle cx={cx + 80} cy={cy - 60} r={7} fill={ACCENT} />
      <circle cx={cx - 120} cy={cy + 40} r={5} fill={ACCENT} opacity={0.7} />
      <circle cx={cx + 40} cy={cy + 130} r={4} fill={ACCENT} opacity={0.5} />
    </svg>
  );
}
function CustRow({ name, desc, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ padding: '16px 0', borderBottom: `1px solid ${WHITE_15}`, opacity: p, transform:`translateX(${(1-p)*-10}px)` }}>
      <div style={{ fontSize: 28, color: WHITE, fontWeight: 600 }}>{name}</div>
      <div style={{ ...TYPE.small, color: WHITE_70, marginTop: 4 }}>{desc}</div>
    </div>
  );
}

// ----- S15 Roadmap -----
// =============================================================================
// S15 — ROADMAP TO FINAL (2026-05-05 갈아엎음): 5/7 → 6/9~14 6주 plan
// =============================================================================
function S15() {
  const sections = [
    {
      tag: 'WEEK 1-2',
      date: '5/8 ~ 5/21',
      title: '운영 안정성',
      tone: 'warm',
      items: [
        'Kafka Consumer 실연결 (InMemory → KRaft)',
        '전처리 모듈 분리 (pipeline/features.py)',
        '알람 신뢰도 점수 (binary → 0~1 score)',
      ],
    },
    {
      tag: 'WEEK 3-4',
      date: '5/22 ~ 6/4',
      title: '일반화 입증',
      tone: 'mid',
      items: [
        'HIRA OpenAPI · L1 지역 분리',
        '다질환 확장 · 코로나·노로 검증',
        'AE threshold 튜닝 · FAR < 0.15',
      ],
    },
    {
      tag: 'WEEK 5-6',
      date: '6/5 ~ 6/9',
      title: '최종 검증',
      tone: 'cool',
      items: [
        '시즌 추가 검증 · 2022-23, 2023-24 백테스트',
        'K8s 다중 노드 · GKE 3 node',
        '광역지자체 PoC MOU 시도',
      ],
    },
  ];
  const targets = [
    { metric: 'F1', target: '> 0.90', baseline: '현 0.882', hero: true },
    { metric: 'FAR', target: '< 0.15', baseline: '현 0.206', hero: true },
    { metric: 'Multi-disease', target: '2종 검증', baseline: '현 인플루엔자 1종' },
    { metric: 'PoC MOU', target: '광역지자체 1건 시도', baseline: '신규' },
  ];
  return (
    <>
      <Chrome index={15} label="15 · ROADMAP TO FINAL" />
      <Line x={120} y={140} style={TYPE.eyebrow}>ROADMAP TO FINAL — 5/7 ▶ 6/9~14 (6주)</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>중간발표 → 최종발표 6주.</Line>

      <div style={{ position: 'absolute', left: 120, top: 320, right: 120, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 28 }}>
        {sections.map((s, i) => <RoadmapSection key={i} section={s} delay={0.5 + i * 0.25} />)}
      </div>

      <Plate x={120} y={780} width={1680} height={200} delay={1.6}>
        <div style={{ padding: '22px 32px', fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>FINAL TARGETS · 6/9~14</div>
          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
            {targets.map((t, i) => <TargetCard key={i} {...t} delay={1.95 + i * 0.12} />)}
          </div>
        </div>
      </Plate>
    </>
  );
}

function RoadmapSection({ section, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  const tone = section.tone === 'warm' ? '#F4A261' : section.tone === 'mid' ? '#E9C46A' : ACCENT;
  return (
    <div style={{
      opacity: p, transform: `translateY(${(1-p)*16}px)`, fontFamily: FONT,
      border: `1px solid ${WHITE_15}`, borderTop: `3px solid ${tone}`,
      background: 'rgba(5,7,11,0.45)', padding: '24px 26px', height: 420, boxSizing: 'border-box',
    }}>
      <div style={{ ...TYPE.label, color: tone, fontFamily: CODE_FONT, fontSize: 13 }}>{section.tag}</div>
      <div style={{ fontSize: 14, color: WHITE_45, marginTop: 6, fontFamily: CODE_FONT }}>{section.date}</div>
      <div style={{ fontSize: 30, color: WHITE, fontWeight: 600, marginTop: 18, letterSpacing: '-0.01em' }}>{section.title}</div>
      <div style={{ marginTop: 22 }}>
        {section.items.map((it, i) => {
          const ip = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - 0.3 - i * 0.12) / 0.4)));
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'baseline', gap: 12,
              padding: '12px 0', borderBottom: `1px solid ${WHITE_15}`,
              opacity: ip, transform: `translateX(${(1-ip)*-8}px)`,
            }}>
              <span style={{ width: 6, height: 6, background: tone, flexShrink: 0, marginTop: 7 }} />
              <span style={{ fontSize: 17, color: WHITE, lineHeight: 1.4 }}>{it}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TargetCard({ metric, target, baseline, hero, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      opacity: p, transform: `translateY(${(1-p)*8}px)`,
      borderLeft: `2px solid ${hero ? ACCENT : WHITE_45}`, paddingLeft: 14,
    }}>
      <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45, fontSize: 11, fontFamily: CODE_FONT }}>{metric}</div>
      <div style={{
        fontSize: hero ? 24 : 20, color: hero ? ACCENT : WHITE,
        fontWeight: hero ? 700 : 600, marginTop: 6, fontFeatureSettings: '"lnum"',
      }}>{target}</div>
      <div style={{ fontSize: 13, color: WHITE_45, marginTop: 4 }}>{baseline}</div>
    </div>
  );
}

// ----- S16 Team & Q&A -----
function S16() {
  const team = [
    ['박진영', 'PM · AI'],
    ['이경준', '백엔드 · DB'],
    ['이우형', '데이터 엔지니어'],
    ['김나영', '프런트엔드'],
    ['박정빈', 'DevOps · QA · 법'],
  ];
  const risks = ['네이버 API 정책 변경', '하수 데이터 품질 · 지역 편차', '6일 · TFT 실학습 완료 압박'];
  return (
    <>
      <Chrome index={16} label="16 · TEAM & Q&A" />
      <Line x={120} y={140} style={TYPE.eyebrow}>팀 · 리스크 · Q&A</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>팀원 소개</Line>

      <Plate x={120} y={380} width={1060} height={580} delay={0.5}>
        <div style={{ padding: 48, fontFamily: FONT }}>
          <div style={{ ...TYPE.label }}>5명 · Claude Code 에이전트 병렬 협업</div>
          <div style={{ marginTop: 24 }}>
            {team.map((m, i) => <TeamRow key={i} name={m[0]} role={m[1]} delay={0.9 + i*0.12} />)}
          </div>
        </div>
      </Plate>

      <Plate x={1220} y={380} width={580} height={280} delay={0.7}>
        <div style={{ padding: 36, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>RISKS · 3</div>
          {risks.map((r, i) => (
            <RiskItem key={i} text={r} delay={1.1 + i*0.14} />
          ))}
        </div>
      </Plate>

      <Plate x={1220} y={680} width={580} height={280} delay={0.9} opacity={0.7}>
        <div style={{ padding: 28, fontFamily: FONT, display: 'grid', gridTemplateColumns: '180px 1fr', gap: 18, alignItems: 'center', height: '100%', boxSizing: 'border-box' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 80, fontWeight: 700, color: WHITE, letterSpacing: '-0.05em', lineHeight: 1 }}>Q <span style={{ color: ACCENT }}>&</span> A</div>
            <div style={{ ...TYPE.small, fontSize: 13, color: WHITE_70, marginTop: 8 }}>전원 답변 · 5분</div>
          </div>
          <div>
            <div style={{ ...TYPE.label, color: ACCENT, fontSize: 11 }}>예상 질문 — 보안</div>
            <div style={{ marginTop: 8, fontSize: 13, color: WHITE_70, lineHeight: 1.55 }}>
              · K8s <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>runAsNonRoot</span><br/>
              · 가명처리 — 시도 단위 집계<br/>
              · Kafka <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>acks=all retries=3</span><br/>
              · API 키 <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>.env</span> + Pydantic 검증
            </div>
          </div>
        </div>
      </Plate>
    </>
  );
}
function TeamRow({ name, role, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ display:'flex', justifyContent:'space-between', padding: '16px 0', borderBottom: `1px solid ${WHITE_15}`, opacity: p, transform:`translateX(${(1-p)*-10}px)` }}>
      <span style={{ fontSize: 28, color: WHITE, fontWeight: 600 }}>{name}</span>
      <span style={{ fontSize: 24, color: ACCENT }}>{role}</span>
    </div>
  );
}
function RiskItem({ text, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ fontSize: 22, color: WHITE, padding: '12px 0', opacity: p }}>
      <span style={{ color: ACCENT, marginRight: 12 }}>—</span>{text}
    </div>
  );
}

// =============================================================================
// SourceCard — "왜 이 데이터인가" 카드. 출처·역할·확장경로 3단.
// =============================================================================
function SourceCard({ x, y, delay, idx, name, source, role, expand, hero }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 0.7)));
  return (
    <div style={{
      position:'absolute', left:x, top:y, width: 540, height: 540,
      border: `1px solid ${hero ? ACCENT : WHITE_15}`,
      background: `rgba(5,7,11,${hero ? 0.65 : 0.5})`,
      backdropFilter:'blur(8px)',
      opacity: p, transform:`translateY(${(1-p)*20}px)`,
      padding: 36, boxSizing:'border-box', fontFamily: FONT,
    }}>
      <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45 }}>0{idx}</div>
      <div style={{ marginTop: 14, fontSize: 38, fontWeight: 700, color: WHITE, letterSpacing:'-0.02em' }}>{name}</div>
      <div style={{ marginTop: 6, fontSize: 18, color: WHITE_70 }}>{source}</div>

      <div style={{ marginTop: 32, paddingTop: 18, borderTop: `1px solid ${WHITE_15}` }}>
        <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45 }}>역할</div>
        <div style={{ marginTop: 10, fontSize: 20, color: WHITE, fontWeight: 500, lineHeight: 1.5 }}>{role}</div>
      </div>

      <div style={{ position:'absolute', left: 36, right: 36, bottom: 36 }}>
        <div style={{ ...TYPE.label, color: WHITE_45 }}>확장 가능성</div>
        <div style={{ marginTop: 10, fontSize: 17, color: WHITE_70, lineHeight: 1.5 }}>{expand}</div>
      </div>
    </div>
  );
}

// =============================================================================
// S05A — 왜 이 3개 데이터인가 + 확장성
// =============================================================================
function S05A() {
  return (
    <>
      <Chrome index="05A" label="05A · DATA RATIONALE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>데이터 선택 근거 · 확장성</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>왜 이 셋이고, 어떻게 늘릴까.</Line>

      <SourceCard x={120}  y={340} delay={0.5} idx={1}
        name="약국 OTC"
        source="네이버 쇼핑인사이트 · cid 50000167"
        role="시민이 돈을 쓴 행동. 가짜 신호 적음."
        expand="약국 POS · 식약처 의약품관리종합정보망" />
      <SourceCard x={690}  y={340} delay={0.7} idx={2} hero
        name="하수 바이러스"
        source="질병관리청 KOWAS · PDF 픽셀 추출"
        role="무증상자도 잡힘. 가장 객관적·가장 빠름."
        expand="자체 펌프장 직접 측정 · 하수환경공단 협력" />
      <SourceCard x={1260} y={340} delay={0.9} idx={3}
        name="검색 트렌드"
        source="네이버 데이터랩 (DataLab API)"
        role="불안의 표면화. 가장 빠르되 잡음 많음."
        expand="구글 트렌드 · 카카오 검색 · X 키워드" />

      <Plate x={120} y={920} width={1680} height={60} delay={1.5} opacity={0.4}>
        <div style={{ padding: '14px 32px', fontFamily: FONT, fontSize: 18, color: WHITE_70 }}>
          <span style={{ color: ACCENT, fontWeight: 600, marginRight: 14 }}>코드 한 줄로 확장</span>
          새 질병 → <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>PATHOGEN_COLOR_RANGES</span> 추가 ·
          새 지역 → <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>SIDO_ALL</span> 교체 ·
          새 신호층 → <span style={{ color: ACCENT, fontFamily: CODE_FONT }}>w4</span> 가중치 추가
        </div>
      </Plate>
    </>
  );
}

// =============================================================================
// CodeBox — 코드 슬라이드 공용 박스. Plate 위에 monospace 라인을 페이드인 한다.
// 디자인 언어 유지: Plate + WHITE_15 보더 + ACCENT 하이라이트 줄.
// =============================================================================

const CODE_FONT = '"JetBrains Mono", "Menlo", "Consolas", monospace';

function CodeLine({ children, hi, dim, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.35)));
  return (
    <div style={{
      fontFamily: CODE_FONT,
      fontSize: 22,
      lineHeight: 1.5,
      color: hi ? ACCENT : (dim ? WHITE_45 : WHITE_70),
      fontWeight: hi ? 600 : 400,
      letterSpacing: 0,
      whiteSpace: 'pre',
      opacity: p,
      transform: `translateX(${(1-p)*-8}px)`,
      background: hi ? 'rgba(34,227,255,0.08)' : 'transparent',
      padding: hi ? '3px 10px' : '3px 10px',
      margin: '0 -10px',
      borderLeft: hi ? `2px solid ${ACCENT}` : '2px solid transparent',
    }}>
      {children}
    </div>
  );
}

function CodeBox({ x, y, width, height, file, lines, delay = 0.5 }) {
  return (
    <Plate x={x} y={y} width={width} height={height} delay={delay}>
      <div style={{ padding: 32, height: '100%', boxSizing: 'border-box', fontFamily: FONT, overflow: 'hidden' }}>
        <div style={{ ...TYPE.label, color: ACCENT, fontSize: 16 }}>{file}</div>
        <div style={{ marginTop: 18 }}>
          {lines.map((ln, i) => (
            <CodeLine key={i} hi={ln.hi} dim={ln.dim} delay={delay + 0.4 + i * 0.08}>
              {ln.t}
            </CodeLine>
          ))}
        </div>
      </div>
    </Plate>
  );
}

function TrapPanel({ x, y, width, height, trap, fix, result, delay = 0.7 }) {
  const { localTime } = useSprite();
  return (
    <div style={{ position: 'absolute', left: x, top: y, width, height, fontFamily: FONT, boxSizing: 'border-box' }}>
      <TrapRow icon="✕" label="표준 방법의 한계" text={trap} color={WHITE_45} delay={delay} />
      <TrapRow icon="✓" label="우리 처리" text={fix} color={WHITE} delay={delay + 0.35} />
      <TrapRow icon="◆" label="결과 수치" text={result} color={ACCENT} delay={delay + 0.7} hero />
    </div>
  );
}

function TrapRow({ icon, label, text, color, delay, hero }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      padding: '24px 0',
      borderBottom: `1px solid ${WHITE_15}`,
      opacity: p,
      transform: `translateY(${(1-p)*12}px)`,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <span style={{ fontSize: 28, color, fontWeight: 700, width: 28, textAlign: 'center' }}>{icon}</span>
        <span style={{ ...TYPE.label, color, opacity: 0.8 }}>{label}</span>
      </div>
      <div style={{
        marginTop: 10,
        marginLeft: 44,
        fontSize: hero ? 32 : 26,
        color,
        fontWeight: hero ? 600 : 400,
        lineHeight: 1.35,
        letterSpacing: '-0.01em',
      }}>
        {text}
      </div>
    </div>
  );
}

// =============================================================================
// S07A — 데이터 수집 (의도적 분리)
// =============================================================================
function S07A() {
  const lines = [
    { t: '# pipeline/collectors/otc_collector.py' , dim: true },
    { t: 'OTC_KEYWORDS = ["감기약","해열제",' },
    { t: '                "종합감기약","타이레놀","판콜"]', hi: true },
    { t: '' },
    { t: '# pipeline/collectors/search_collector.py', dim: true },
    { t: 'SEARCH_KEYWORDS = ["독감 증상","고열 원인",' },
    { t: '                   "타미플루","몸살 원인"]', hi: true },
    { t: '' },
    { t: '# pipeline/collectors/kowas_parser.py', dim: true },
    { t: 'PATHOGEN_COLOR_RANGES = {' },
    { t: '  "influenza": {"r":(210,255),"g":(140,200),', hi: true },
    { t: '                "b":(100,170)}}    # PDF 픽셀 RGB', hi: true },
  ];
  return (
    <>
      <Chrome index="07A" label="07A · DATA COLLECTION" />
      <Line x={120} y={140} style={TYPE.eyebrow}>① 데이터 수집 — 의도적 분리</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>같은 키워드를 섞지 않는다.</Line>

      <CodeBox x={120} y={380} width={920} height={580} delay={0.5}
        file="3 collectors · 의도별 분리" lines={lines} />

      <TrapPanel x={1080} y={380} width={720} height={580} delay={0.9}
        trap="키워드 한 통에 섞으면 구매 의도와 증상 불안이 뒤섞여 신호가 무뎌진다."
        fix="L1=구매(약), L3=증상검색을 의도적 분리. L2는 KOWAS PDF 그래프 RGB 픽셀로 직접 측정. KOWAS는 API 비공개라 Selenium으로 PDF 자동 다운로드 (72개 자동 수집)."
        result="L1 130 · L2 952 · L3 130 건/주 — 17지역 26주 누적" />
    </>
  );
}

// =============================================================================
// (S07A2 + ERMini + ERTable 제거 — 2026-05-05 다이어트, S07A 에 한 줄 흡수)
// =============================================================================

// =============================================================================
// S07B — 앙상블·교차검증 게이트 (★ 최강)
// =============================================================================
function S07B() {
  const lines = [
    { t: '# pipeline/scorer.py', dim: true },
    { t: '_CROSS_VALIDATION_MIN_LAYERS = 2', hi: true },
    { t: '_CROSS_VALIDATION_LAYER_THRESHOLD = 30.0', hi: true },
    { t: '' },
    { t: 'def determine_alert_level(composite, l1, l2, l3):' },
    { t: '    raw = "RED"    if composite >= 75 else \\' },
    { t: '          "ORANGE" if composite >= 55 else \\' },
    { t: '          "YELLOW" if composite >= 30 else "GREEN"' },
    { t: '    if raw == "GREEN": return "GREEN"' },
    { t: '' },
    { t: '    above = sum(1 for v in (l1,l2,l3)' },
    { t: '                if v and v >= 30)' },
    { t: '    if above < 2: return "GREEN"   # 단일신호 차단', hi: true },
    { t: '    return raw' },
  ];
  return (
    <>
      <Chrome index="07B" label="07B · CROSS-VALIDATION GATE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>② 앙상블 · 교차검증 게이트</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>단일 신호는, 코드가 차단한다.</Line>

      <CodeBox x={120} y={380} width={920} height={580} delay={0.5}
        file="pipeline/scorer.py · 게이트 B" lines={lines} />

      <TrapPanel x={1080} y={380} width={720} height={580} delay={0.9}
        trap="2013 Google Flu Trends — 검색 단일 신호로 실제의 2배 과대예측 후 서비스 종료."
        fix="2개 이상 계층이 30점 이상일 때만 YELLOW+ 발령. 단일 신호는 강제로 GREEN."
        result="게이트 끄고 켠 비교 · 가짜경보율 0.602 → 0.206 — 65.8% 감소" />
    </>
  );
}

// =============================================================================
// S07C — Walk-forward · 이상탐지
// =============================================================================
function S07C() {
  const lines = [
    { t: '# ml/xgboost/model.py', dim: true },
    { t: 'tscv = TimeSeriesSplit(n_splits=5, gap=4)', hi: true },
    { t: '# gap=4 → 한 달치 미래 데이터 차단', dim: true },
    { t: '' },
    { t: 'for train_idx, val_idx in tscv.split(X):' },
    { t: '    model.fit(X[train_idx], y[train_idx])' },
    { t: '    pred = model.predict(X[val_idx]) > 55' },
    { t: '    f1_scores.append(f1_score(y[val_idx], pred))' },
    { t: '' },
    { t: '# ml/anomaly/autoencoder.py', dim: true },
    { t: 'threshold = np.percentile(errors, 95)', hi: true },
    { t: '# 99p — 처음 보는 패턴만 이상 처리', dim: true },
  ];
  return (
    <>
      <Chrome index="07C" label="07C · WALK-FORWARD" />
      <Line x={120} y={140} style={TYPE.eyebrow}>③ ML 검증 — 시계열 함정 차단</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>미래로 과거를 학습하지 않는다.</Line>

      <CodeBox x={120} y={380} width={920} height={580} delay={0.5}
        file="XGBoost walk-forward · Autoencoder 99p" lines={lines} />

      <TrapPanel x={1080} y={380} width={720} height={520} delay={0.9}
        trap="일반 K-Fold(섞어 검증)는 미래 데이터로 과거를 학습 — 발표용 점수만 잘 나오고 실전에서 폭망."
        fix="시간 순 검증 + 4주 갭으로 미래 누출 차단 · 자동인코더 95% 분위수로 신종 패턴 감지."
        result="17지역 시간순 검증 · 종합정확도 0.882 · 신뢰도 0.949 · MCC 0.595 재현" />

      <Plate x={1080} y={920} width={720} height={50} delay={1.8} opacity={0.4}>
        <div style={{ padding: '12px 22px', fontFamily: FONT, fontSize: 16, color: WHITE_70, display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>재현</span>
          <span style={{ fontFamily: CODE_FONT, fontSize: 16, color: ACCENT }}>$ python -m ml.reproduce_validation</span>
        </div>
      </Plate>
    </>
  );
}

// =============================================================================
// S07D2 — RAG 리포트 실제 출력 예시 (9섹션 mock + 인용)
// =============================================================================
function ReportSection({ num, title, sample, delay, hero }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      padding: '8px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-6}px)`,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <span style={{
          fontSize: 12, fontFamily: CODE_FONT, color: hero ? ACCENT : WHITE_45,
          width: 22, flexShrink: 0,
        }}>## {num}</span>
        <span style={{
          fontSize: 15, color: hero ? ACCENT : WHITE,
          fontWeight: hero ? 700 : 600,
        }}>{title}</span>
      </div>
      {sample && (
        <div style={{
          marginLeft: 32, marginTop: 4,
          fontSize: 13, color: WHITE_70, lineHeight: 1.4,
          fontStyle: 'italic',
        }}>{sample}</div>
      )}
    </div>
  );
}

function CitationRow({ idx, citation, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      display: 'flex', gap: 10, padding: '8px 0',
      borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-6}px)`,
    }}>
      <span style={{
        fontSize: 13, fontFamily: CODE_FONT, color: ACCENT,
        width: 28, flexShrink: 0, fontWeight: 600,
      }}>[{idx}]</span>
      <span style={{ fontSize: 14, color: WHITE_70, lineHeight: 1.4 }}>{citation}</span>
    </div>
  );
}

function S07D2() {
  return (
    <>
      <Chrome index="07D2" label="07D2 · REPORT OUTPUT" />
      <Line x={120} y={140} style={TYPE.eyebrow}>④-2 RAG 리포트 — 실제 출력</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>출처가 박힌 9섹션.</Line>

      {/* 좌측 — 9섹션 리포트 mock (실제 출력 형태) */}
      <Plate x={120} y={350} width={1080} height={620} delay={0.5}>
        <div style={{ padding: 28, fontFamily: FONT, height: '100%', boxSizing: 'border-box', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: `2px solid ${ACCENT}`, paddingBottom: 10, marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 15, color: ACCENT, fontWeight: 700, fontFamily: CODE_FONT }}>alert_report.md</div>
              <div style={{ fontSize: 13, color: WHITE_70, marginTop: 4 }}>서울특별시 · 2025-W49 · alert_level: <span style={{ color: '#eab308', fontWeight: 700 }}>YELLOW</span></div>
            </div>
            <div style={{ fontSize: 11, color: WHITE_45, fontFamily: CODE_FONT }}>Claude Haiku · SSE</div>
          </div>

          <ReportSection num="1" title="한 줄 요약"
            sample="서울특별시 위험등급 주의(YELLOW). 약국 OTC와 검색 트렌드 동시 상승, 하수 농도 보조 확인."
            delay={1.0} hero />
          <ReportSection num="2" title="핵심 지표 (composite=종합점수)"
            sample="종합점수 42.7 (전주 대비 +8.4%) · 약국 58 · 하수 31 · 검색 46"
            delay={1.15} />
          <ReportSection num="3" title="레이어별 분석"
            sample="L1 OTC 58/100 — 감기약 검색지수 급등, L3 단독발령 금지 원칙 적용"
            delay={1.30} />
          <ReportSection num="4" title="7·14·21일 전망"
            sample="TFT 예측: 2주 후 confirmed_per_100k 약 380~440 구간"
            delay={1.45} />
          <ReportSection num="5" title="권고 조치 (보건당국·의료기관·시민)"
            sample="역학조사관 사전 배치 · 응급실 트리아지 강화 · 마스크 권고"
            delay={1.60} />
          <ReportSection num="6" title="참고 문헌 [1]~[5]"
            sample="WHO·ECDC·KDCA 가이드 인용"
            delay={1.75} />
          <ReportSection num="7" title="면책 (ISMS-P 2.9 · EU AI Act Art.13·14)"
            sample="AI 보조 자료 · 인간 전문가 검토 필요 · 진단 대체 아님"
            delay={1.90} hero />

          <div style={{
            marginTop: 14, padding: '10px 14px',
            background: 'rgba(34,227,255,0.06)', borderLeft: `2px solid ${ACCENT}`,
            fontSize: 13, color: WHITE_70, lineHeight: 1.5,
          }}>
            <span style={{ color: ACCENT, fontWeight: 600, fontFamily: CODE_FONT, marginRight: 8 }}>SCREENSHOT</span>
            실제 화면은 <span style={{ fontFamily: CODE_FONT, color: ACCENT }}>frontend/public/slides/uploads/rag-report.png</span> 추가 시 자동 표시
          </div>
        </div>
      </Plate>

      {/* 우측 — 인용 5건 + 활용 사례 */}
      <Plate x={1240} y={350} width={560} height={620} delay={0.7}>
        <div style={{ padding: 28, fontFamily: FONT, height: '100%', boxSizing: 'border-box' }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>RAG 인용 · top-5</div>
          <div style={{ ...TYPE.small, fontSize: 13, color: WHITE_70, marginTop: 4 }}>
            매 리포트 자동 첨부 · Qdrant 의미 검색
          </div>

          <div style={{ marginTop: 18 }}>
            <CitationRow idx="1" citation="WHO (2022) Wastewater Surveillance Guidelines · p.42" delay={1.1} />
            <CitationRow idx="2" citation="ECDC (2023) Multi-signal Cross-Validation Manual · p.15" delay={1.25} />
            <CitationRow idx="3" citation="KDCA (2024) ILINet 운영지침 · p.8" delay={1.40} />
            <CitationRow idx="4" citation="Lazer et al. (2014) Science · p.1203" delay={1.55} />
            <CitationRow idx="5" citation="Larsen & Wigginton (2020) Nature Biotech · p.1151" delay={1.70} />
          </div>

          <div style={{ marginTop: 24, paddingTop: 18, borderTop: `1px solid ${WHITE_15}` }}>
            <div style={{ ...TYPE.label, color: ACCENT }}>왜 9섹션 강제</div>
            <div style={{ marginTop: 10, fontSize: 16, color: WHITE_70, lineHeight: 1.5 }}>
              KDCA 주간 감염병 보고서 표준 포맷.
              보건당국이 그대로 결재 라인에 올릴 수 있어야 함.
            </div>
          </div>

          <div style={{
            marginTop: 18, padding: '12px 14px',
            background: 'rgba(5,7,11,0.55)', borderLeft: `2px solid ${ACCENT}`,
          }}>
            <div style={{ ...TYPE.label, color: ACCENT, fontSize: 12 }}>구별 포인트</div>
            <div style={{ marginTop: 8, fontSize: 15, color: WHITE, fontWeight: 500, lineHeight: 1.45 }}>
              일반 챗봇: 그럴듯하게 지어냄<br/>
              <span style={{ color: ACCENT }}>UIS RAG: 출처·면책·표준 포맷 강제</span>
            </div>
          </div>
        </div>
      </Plate>
    </>
  );
}

// =============================================================================
// S07E — 적재 → 전처리 → 앙상블 흐름 (한 장)
// =============================================================================
function PipeStage({ x, y, delay, num, title, sub, code, hero }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width: 300, height: 320,
      border: `1px solid ${hero ? ACCENT : WHITE_15}`,
      background: `rgba(5,7,11,${hero ? 0.7 : 0.5})`,
      backdropFilter: 'blur(8px)',
      opacity: p, transform: `translateY(${(1-p)*16}px)`,
      padding: 22, boxSizing: 'border-box', fontFamily: FONT,
    }}>
      <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45 }}>STEP {num}</div>
      <div style={{ marginTop: 10, fontSize: 26, fontWeight: 700, color: WHITE, letterSpacing: '-0.01em' }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 16, color: WHITE_70, lineHeight: 1.4 }}>{sub}</div>
      <div style={{
        position: 'absolute', left: 22, right: 22, bottom: 22,
        padding: '10px 12px',
        background: 'rgba(34,227,255,0.06)',
        borderLeft: `2px solid ${ACCENT}`,
        fontFamily: CODE_FONT, fontSize: 14, color: ACCENT,
        whiteSpace: 'pre', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>{code}</div>
    </div>
  );
}

function PipeArrow({ x, y, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <svg style={{ position: 'absolute', inset: 0, width: 1920, height: 1080, pointerEvents: 'none' }}>
      <line x1={x} y1={y} x2={x + 32 * p} y2={y} stroke={ACCENT} strokeWidth={1.5} opacity={0.7} />
      {p > 0.95 && <polygon points={`${x+32},${y} ${x+24},${y-5} ${x+24},${y+5}`} fill={ACCENT} />}
    </svg>
  );
}

function GlossaryRow({ term, def, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.4)));
  return (
    <div style={{
      display: 'flex', gap: 18, padding: '10px 0',
      borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-8}px)`,
    }}>
      <span style={{ width: 200, fontSize: 18, color: ACCENT, fontWeight: 600, flexShrink: 0 }}>{term}</span>
      <span style={{ fontSize: 18, color: WHITE_70, lineHeight: 1.4 }}>{def}</span>
    </div>
  );
}

function S07E() {
  return (
    <>
      <Chrome index="07E" label="07E · INGESTION → ENSEMBLE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>⑤ 적재 → 전처리 → 앙상블</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>원시 점이, 모델 한 줄로.</Line>

      <PipeStage x={120}  y={380} delay={0.4} num={1}
        title="수집"     sub="주 단위 자동 크론 (월·화 09~10시)"
        code="kafka_producer.send(...)" />
      <PipeArrow x={425} y={540} delay={0.55} />

      <PipeStage x={465}  y={380} delay={0.6} num={2}
        title="정규화"   sub="단위 다른 신호를 0~100 같은 척도로"
        code="min_max_normalize(values)" />
      <PipeArrow x={770} y={540} delay={0.75} />

      <PipeStage x={810}  y={380} delay={0.8} num={3}
        title="DB 적재"  sub="Timescale 하이퍼테이블·주간 파티션"
        code="INSERT layer_signals" />
      <PipeArrow x={1115} y={540} delay={0.95} />

      <PipeStage x={1155} y={380} delay={1.0} num={4} hero
        title="앙상블"   sub="가중평균 + 게이트 B"
        code="0.35·L1 + 0.40·L2 + 0.25·L3" />
      <PipeArrow x={1460} y={540} delay={1.15} />

      <PipeStage x={1500} y={380} delay={1.2} num={5}
        title="모델 입력" sub="피처 5개 (L1, L2, L3, 기온, 습도)"
        code="model.predict(X)" />

      <Plate x={120} y={780} width={1680} height={200} delay={1.6}>
        <div style={{ padding: '24px 36px', fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>어려운 용어 한 줄 풀이</div>
          <div style={{ marginTop: 14 }}>
            <GlossaryRow term="정규화 Min-Max"
              def="단위 다른 신호(건수·ppm·검색지수)를 0~100으로 줄세움. 비교가 안 되던 걸 비교 가능하게."
              delay={2.0} />
            <GlossaryRow term="Timescale 하이퍼테이블"
              def="시간 기준으로 자동 분할되는 시계열 DB. 옛날 데이터까지 빠르게 조회."
              delay={2.2} />
            <GlossaryRow term="앙상블 + 게이트 B"
              def="세 신호의 가중평균. 단, 2개 이상 동시에 30점 이상 안 되면 GREEN 강제."
              delay={2.4} />
          </div>
        </div>
      </Plate>
    </>
  );
}

// =============================================================================
// S07F — 모델 3종 역할 분담 (XGB · TFT · AE)
// =============================================================================
function AttentionBars({ bars, delay }) {
  const { localTime } = useSprite();
  return (
    <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${WHITE_15}` }}>
      <div style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>Attention top-3 (실측)</div>
      <div style={{ marginTop: 8 }}>
        {bars.map((b, i) => {
          const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay - i * 0.12) / 0.6)));
          const w = b.value * 100 * p;
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
              <span style={{ width: 36, fontSize: 12, color: WHITE_70, fontFamily: CODE_FONT }}>{b.label}</span>
              <div style={{ flex: 1, height: 8, background: WHITE_15, position: 'relative' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${w}%`, background: ACCENT }} />
              </div>
              <span style={{ width: 32, fontSize: 11, color: ACCENT, fontFamily: CODE_FONT, textAlign: 'right' }}>
                {(b.value * p).toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ModelCard({ x, y, delay, badge, name, role, metaphor, io, usage, hero, attentionBars }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.7)));
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width: 540, height: 620,
      border: `1px solid ${hero ? ACCENT : WHITE_15}`,
      background: `rgba(5,7,11,${hero ? 0.7 : 0.5})`,
      backdropFilter: 'blur(8px)',
      opacity: p, transform: `translateY(${(1-p)*20}px)`,
      padding: 32, boxSizing: 'border-box', fontFamily: FONT,
    }}>
      <div style={{ ...TYPE.label, color: hero ? ACCENT : WHITE_45, fontFamily: CODE_FONT, fontSize: 14, letterSpacing: '0.18em' }}>{badge}</div>
      <div style={{ marginTop: 12, fontSize: 40, fontWeight: 700, color: WHITE, letterSpacing: '-0.02em' }}>{name}</div>
      <div style={{ marginTop: 4, fontSize: 17, color: WHITE_70 }}>{role}</div>

      {usage && (
        <div style={{ marginTop: 18, paddingTop: 14, borderTop: `1px solid ${WHITE_15}` }}>
          <div style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>주요 활용처</div>
          <div style={{ marginTop: 6, fontSize: 16, color: WHITE_70, lineHeight: 1.45 }}>{usage}</div>
        </div>
      )}

      <div style={{ marginTop: 14, padding: '14px 16px', background: 'rgba(34,227,255,0.06)', borderLeft: `2px solid ${ACCENT}` }}>
        <div style={{ ...TYPE.label, color: ACCENT, fontSize: 13 }}>비유</div>
        <div style={{ marginTop: 8, fontSize: 21, color: WHITE, fontWeight: 500, lineHeight: 1.4, letterSpacing: '-0.01em' }}>
          “{metaphor}”
        </div>
      </div>

      {attentionBars && <AttentionBars bars={attentionBars} delay={delay + 0.6} />}

      <div style={{ position: 'absolute', left: 32, right: 32, bottom: 32 }}>
        <div style={{ ...TYPE.label, color: WHITE_45, fontSize: 13 }}>입력 → 출력</div>
        <div style={{ marginTop: 8, fontFamily: CODE_FONT, fontSize: 15, color: WHITE_70, lineHeight: 1.5 }}>
          {io}
        </div>
      </div>
    </div>
  );
}

function S07F() {
  return (
    <>
      <Chrome index="07F" label="07F · MODEL ROLES" />
      <Line x={120} y={140} style={TYPE.eyebrow}>⑥ 모델 3종 — 왜 셋이냐</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>각자 다른 질문에 답한다.</Line>

      <ModelCard x={120}  y={310} delay={0.4}
        badge="XGBOOST · 회귀"
        name="XGBoost"
        role="현재 위험도 점수화 (그라디언트 부스팅 트리 앙상블)"
        usage="Kaggle 우승 단골 · 신용평가 · 이탈예측 · 광고 CTR"
        metaphor="지금 빨간불인가, 초록불인가?"
        io={"5개 신호 입력 → 종합 위험점수 0~100\n시계열 분할 5-fold · 4주 갭(미래 차단)\nF1 0.882 · 경보 신뢰도 0.95"} />

      <ModelCard x={690}  y={310} delay={0.6} hero
        badge="TFT · 시계열"
        name="TFT"
        role="7·14·21일 미래 예측 (어텐션 기반 시계열 트랜스포머)"
        usage="Google Research 2020 · 전력 수요 · 교통 흐름 · 소매 매출 시계열"
        metaphor="다음 주, 다음 다음 주는 어떻게 될까?"
        attentionBars={[
          { label: '기온',  value: 0.15 },
          { label: 'OTC',   value: 0.14 },
          { label: '하수',  value: 0.07 },
        ]}
        io={"과거 24주 → 다음 3주 예측 · 실측 attention 표기\n실데이터 17지역 학습 (DB 26주+)\n148K 파라미터 · 검증손실 5.48"} />

      <ModelCard x={1260} y={310} delay={0.8}
        badge="AUTOENCODER · 이상탐지"
        name="Autoencoder"
        role="처음 보는 패턴 감지 (압축-복원 신경망)"
        usage="신용카드 이상거래 · 설비 예지정비 · 네트워크 침입탐지"
        metaphor="어? 이건 처음 보는데?"
        io={"4개 신호 → 압축 → 복원\n복원 오차 상위 5%만 이상으로 판정\n→ 신종 팬데믹 시그널\n사전 라벨 불필요 (비지도 학습)"} />

      <Plate x={120} y={940} width={1680} height={50} delay={1.6} opacity={0.4}>
        <div style={{ padding: '12px 32px', fontFamily: FONT, fontSize: 17, color: WHITE_70 }}>
          <span style={{ color: ACCENT, fontWeight: 600, marginRight: 14 }}>왜 셋이냐</span>
          XGB는 과거 패턴 안 정확 · TFT는 미래 봐도 신종 못 잡음 · AE 단독은 점수 못 냄 — <span style={{ color: ACCENT }}>역할이 다르다</span>
        </div>
      </Plate>
    </>
  );
}

// =============================================================================
// S07D — RAG 챗봇 (Claude · Qdrant)
// =============================================================================
function S07D() {
  const lines = [
    { t: '# ml/rag/report_generator.py', dim: true },
    { t: 'LLM_MODEL = "claude-sonnet-4-6"', hi: true },
    { t: 'COLLECTION = "epidemiology_docs"   # Qdrant', hi: true },
    { t: 'TOP_K = 5                          # WHO·ECDC·KDCA' },
    { t: '' },
    { t: 'async def generate_alert_report(signals, region):' },
    { t: '    docs = vectordb.search(signals, top_k=TOP_K)' },
    { t: '    prompt = build_prompt(signals, docs, region)' },
    { t: '    return await call_claude(prompt)        # SSE 스트리밍' },
    { t: '' },
    { t: '# 출력 — 9 섹션 강제 (KDCA 표준 포맷)', dim: true },
    { t: '## 1. 요약  ## 2. 핵심지표  ## 3. 레이어별 분석', hi: true },
    { t: '## 4. 7/14/21일 전망  ## 5. 권고  ## 6. 참고문헌', hi: true },
    { t: '## 7. 면책 (ISMS-P 2.9 · EU AI Act Art.13·14)', hi: true },
  ];
  return (
    <>
      <Chrome index="07D" label="07D · RAG REPORT" />
      <Line x={120} y={140} style={TYPE.eyebrow}>④ RAG 챗봇 — 출처가 있는 답변</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>LLM 혼자 떠들지 않는다.</Line>

      <CodeBox x={120} y={380} width={920} height={580} delay={0.5}
        file="Claude Haiku · Qdrant top-5 인용" lines={lines} />

      <TrapPanel x={1080} y={380} width={720} height={580} delay={0.9}
        trap="일반 챗봇은 그럴듯하게 지어낸다 — 보건당국이 절대 못 받는 이유."
        fix="Qdrant에서 WHO·ECDC·KDCA 가이드 5건 인용 후 Claude가 9섹션 KDCA 포맷으로 정리. 면책조항 강제 삽입."
        result="9 섹션 · 출처 5건 · SSE 스트리밍 · ISMS-P 2.9 면책" />
    </>
  );
}

// =============================================================================
// (S12B + PriorArtRow 제거 — 2026-05-05 다이어트, S12 4-quadrant 로 통합)
// =============================================================================

// =============================================================================
// S13B — 외부 자문 계획 (단순)
// =============================================================================
function S13B() {
  return (
    <>
      <Chrome index="13B" label="13B · EXPERT REVIEW" />
      <Line x={120} y={140} style={TYPE.eyebrow}>외부 자문 — 검증은 우리가 못 한다</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>두 기관에 맡긴다.</Line>

      <AdvisorCard x={120} y={400} delay={0.5}
        tag="의학 · 역학 검증"
        org="질병관리청 (KDCA)"
        sub="감염병관리과 · 역학조사과"
        ask="L2 하수 2주 선행이 임상 워크플로에서 활용 가능한가?" />
      <AdvisorCard x={120} y={700} delay={0.7}
        tag="법 · 보안 검증"
        org="한국인터넷진흥원 (KISA)"
        sub="ISMS-P 사전 컨설팅"
        ask="시·도 단위 집계가 가명처리로 충분한가?" />

      <Plate x={980} y={400} width={820} height={580} delay={0.9}>
        <div style={{ padding: 48, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>발송 트리거 · 어느 정도 되면 보낼지</div>

          <TriggerRow text="17지역 백테스트 PDF — F1 0.882·Granger p=0.021"
            done={true} delay={1.3} />
          <TriggerRow text="실데이터 26주 누적 — 누가 돌려도 같은 수치"
            done={true} delay={1.5} />
          <TriggerRow text="재현 스크립트 — ml/reproduce_validation.py"
            done={true} delay={1.7} />

          <div style={{ marginTop: 36, paddingTop: 28, borderTop: `1px solid ${WHITE_15}` }}>
            <div style={{ ...TYPE.label, color: ACCENT }}>현재 상태</div>
            <div style={{ marginTop: 12, fontSize: 32, color: WHITE, fontWeight: 600, letterSpacing: '-0.01em' }}>
              세 트리거 모두 <span style={{ color: ACCENT }}>충족</span>.
            </div>
            <div style={{ ...TYPE.small, color: WHITE_70, marginTop: 8 }}>
              발송 자료: walk-forward 결과 PDF · Granger 검정 · 데모 URL
            </div>
          </div>
        </div>
      </Plate>
    </>
  );
}

function AdvisorCard({ x, y, delay, tag, org, sub, ask }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.6)));
  return (
    <div style={{
      position: 'absolute', left: x, top: y, width: 820, height: 260,
      background: 'rgba(5,7,11,0.55)', backdropFilter: 'blur(8px)',
      border: `1px solid ${WHITE_15}`, padding: 36, boxSizing: 'border-box',
      fontFamily: FONT, opacity: p, transform: `translateY(${(1-p)*14}px)`,
    }}>
      <div style={{ ...TYPE.label, color: ACCENT }}>{tag}</div>
      <div style={{ marginTop: 16, fontSize: 44, fontWeight: 700, color: WHITE, letterSpacing: '-0.02em' }}>{org}</div>
      <div style={{ ...TYPE.small, color: WHITE_70, marginTop: 6 }}>{sub}</div>
      <div style={{ marginTop: 22, fontSize: 22, color: WHITE_45, fontStyle: 'italic' }}>
        “{ask}”
      </div>
    </div>
  );
}

function TriggerRow({ text, done, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 16,
      padding: '16px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-10}px)`,
    }}>
      <span style={{
        width: 28, height: 28, lineHeight: '28px', textAlign: 'center',
        color: done ? '#05070B' : WHITE_45,
        background: done ? ACCENT : 'transparent',
        border: `1.5px solid ${done ? ACCENT : WHITE_45}`,
        fontSize: 18, fontWeight: 700, flexShrink: 0,
      }}>{done ? '✓' : ''}</span>
      <span style={{ fontSize: 22, color: WHITE, fontWeight: 400, lineHeight: 1.4 }}>{text}</span>
    </div>
  );
}

window.Scenes = {
  S01, S02, S03, S04, S05,
  S05A,
  S06, S07,
  S07A, S07B, S07C, S07D, S07D2, S07E, S07F,
  S08, S10, S10A,
  S11, S12,
  S13,
  S13B,
  S14, S15, S16,
  SCENE_DUR,
};
