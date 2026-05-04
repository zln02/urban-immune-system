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
      <Line x={120} y={860} delay={0.4} style={{ ...TYPE.titleXL, fontSize: 140 }}>URBAN IMMUNE</Line>
      <Line x={120} y={1000} delay={0.6} style={{ ...TYPE.titleXL, fontSize: 140, color: ACCENT }}>SYSTEM</Line>

      <Plate x={1420} y={180} width={380} height={130} delay={1.2}>
        <div style={{ padding: 24 }}>
          <div style={{ ...TYPE.label, color: ACCENT, marginBottom: 8 }}>AWARD</div>
          <div style={{ ...TYPE.body, fontWeight: 500, color: WHITE }}>LG DX School 2026</div>
          <div style={{ ...TYPE.small, color: WHITE_70 }}>대상 · Grand Prize</div>
        </div>
      </Plate>
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
        <div style={{ padding: 48 }}>
          <div style={{ ...TYPE.label }}>2013 · 실패 사례</div>
          <div style={{ ...TYPE.body, fontSize: 48, fontWeight: 600, marginTop: 16, color: WHITE }}>Google Flu Trends</div>
          <div style={{ ...TYPE.small, marginTop: 12, maxWidth: 680 }}>
            검색 단일 신호로 독감 예측 — 뉴스 · 알고리즘 변화에 흔들려<br/>실제 발생의 2배를 과대 예측 후 종료.
          </div>
          <div style={{ ...TYPE.mega, fontSize: 180, marginTop: 40, color: WHITE_45 }}>2×</div>
        </div>
      </Plate>

      {/* Right: our design — venn diagram of 3 circles */}
      <Plate x={980} y={480} width={820} height={480} delay={1.0}>
        <div style={{ padding: 48 }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>OUR DESIGN</div>
          <div style={{ ...TYPE.body, fontSize: 48, fontWeight: 600, marginTop: 16, color: WHITE }}>3-Layer Ensemble</div>
        </div>
        <VennMotif cx={980+410} cy={480+320} delay={1.4} />
      </Plate>
    </>
  );
}

function VennMotif({ cx, cy, delay }) {
  const { localTime } = useSprite();
  const t = Math.max(0, localTime - delay);
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, t / 1.0)));
  return (
    <svg style={{ position:'absolute', left:0, top:0, width:1920, height:1080, pointerEvents:'none', overflow:'visible' }}>
      <circle cx={cx-50} cy={cy-30} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      <circle cx={cx+50} cy={cy-30} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      <circle cx={cx}    cy={cy+50} r={90*p} fill="none" stroke={ACCENT} strokeWidth={1.5} opacity={0.9} />
      <circle cx={cx}    cy={cy+8}  r={8*p}  fill={ACCENT} />
    </svg>
  );
}

// ----- S05 Architecture -----
function S05() {
  const nodes = [
    { label: '약국', x: 120, y: 520 },
    { label: '하수', x: 120, y: 640 },
    { label: '검색', x: 120, y: 760 },
    { label: 'Kafka', x: 480, y: 640 },
    { label: 'TimescaleDB', x: 820, y: 640 },
    { label: 'AI · TFT / AE', x: 1180, y: 520 },
    { label: 'RAG + Claude', x: 1180, y: 760 },
    { label: 'Dashboard', x: 1560, y: 640, accent: true },
  ];
  return (
    <>
      <Chrome index={5} label="05 · ARCHITECTURE" />
      <Line x={120} y={140} style={TYPE.eyebrow}>시스템 구조</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title} width={1700}>데이터는 왼쪽에서,</Line>
      <Line x={120} y={310} delay={0.3} style={{ ...TYPE.title, color: ACCENT }} width={1700}>경보는 오른쪽에서.</Line>

      <ArchDiagram nodes={nodes} delay={0.7} />

      <Line x={120} y={940} delay={1.8} style={{ ...TYPE.small, color: WHITE_45 }}>
        Kafka = 실시간 데이터 우체통 · Qdrant = 문서 의미 검색 DB · RAG는 WHO · ECDC · KDCA 가이드 5건 top-3 자동 인용
      </Line>
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
        return (
          <div key={i} style={{
            position:'absolute', left: n.x, top: n.y,
            padding: '16px 22px',
            border: `1px solid ${n.accent ? ACCENT : WHITE_15}`,
            background: n.accent ? ACCENT : 'rgba(5,7,11,0.65)',
            color: n.accent ? '#05070B' : WHITE,
            fontFamily: FONT, fontSize: 24, fontWeight: 500,
            opacity: p, transform:`translateY(${(1-p)*10}px)`,
            minWidth: 140, textAlign:'center',
          }}>{n.label}</div>
        );
      })}
      {/* Connection lines */}
      <ArchLines delay={delay + 0.5} />
    </>
  );
}

function ArchLines({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 1.0)));
  const lines = [
    [220, 545, 480, 665], [220, 665, 480, 665], [220, 785, 480, 665],
    [620, 665, 820, 665],
    [980, 665, 1180, 545], [980, 665, 1180, 785],
    [1380, 545, 1560, 665], [1380, 785, 1560, 665],
  ];
  return (
    <svg style={{ position:'absolute', inset:0, width:1920, height:1080, pointerEvents:'none' }}>
      {lines.map(([x1,y1,x2,y2], i) => (
        <line key={i} x1={x1} y1={y1}
          x2={x1 + (x2-x1)*p} y2={y1 + (y2-y1)*p}
          stroke={ACCENT} strokeWidth={1} opacity={0.6} strokeDasharray="4 6" />
      ))}
    </svg>
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
          <div style={{ ...TYPE.label, color: ACCENT }}>🏆 LG DX SCHOOL · 대상 1등</div>
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
      <Line x={1100} y={290} delay={1.4} style={{ ...TYPE.mega, fontSize: 200, color: ACCENT }}>0.667</Line>

      <Line x={120} y={560} delay={0.3} style={TYPE.label}>공모전 수치 · 단일 holdout</Line>
      <Line x={1100} y={560} delay={1.5} style={{ ...TYPE.label, color: ACCENT }}>Walk-forward · 재현 가능</Line>

      <Plate x={120} y={720} width={1680} height={220} delay={1.8}>
        <div style={{ padding: '48px 56px', fontFamily: FONT }}>
          <div style={{ fontSize: 44, fontWeight: 600, color: WHITE, letterSpacing:'-0.02em' }}>
            Precision <span style={{ color: ACCENT }}>1.000 · 오경보 0건</span> 유지 · AUC <span style={{ color: ACCENT }}>0.931</span>.
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
  const added   = ['색맹 안전 팔레트 (CUD)', 'Claude 에이전트 병렬 개발', 'Walk-forward 재현 노트북', 'Granger 인과검정 리포트', '팬데믹 조기탐지 탭', '개인정보 영향평가', 'WCAG AA 접근성', '실시간 SSE 리포트'];
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

// ----- S09 Completeness -----
function S09() {
  const mods = [
    { name: 'Layer 2 · 하수 자동 크롤링', pct: 100 },
    { name: 'Layer 1 · 약국 · Layer 3 · 검색', pct: 100 },
    { name: 'RAG · Qdrant · 가이드 5건', pct: 90 },
    { name: 'Infra · CI/CD · 테스트 35', pct: 85 },
    { name: 'Walk-forward 검증 재현', pct: 80 },
    { name: 'TFT 시계열 실학습', pct: 55 },
  ];
  return (
    <>
      <Chrome index={9} label="09 · COMPLETENESS" />
      <Line x={120} y={140} style={TYPE.eyebrow}>현재 완성도 · 2026.04.24</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>모듈별, 솔직하게.</Line>

      <Plate x={120} y={380} width={1680} height={580} delay={0.5}>
        <div style={{ position: 'relative', padding: 56, height: '100%', boxSizing: 'border-box' }}>
          {mods.map((m, i) => (
            <Bar key={i} x={56} y={56 + i * 72} width={1568} pct={m.pct}
              label={m.name} value={m.pct + '%'} delay={0.8 + i*0.12} />
          ))}
          <div style={{ position: 'absolute', left: 56, bottom: 40, ...TYPE.small, color: WHITE_70 }}>
            남은 6일 — TFT 실학습 마무리 · 발표 시연 예행
          </div>
        </div>
      </Plate>
    </>
  );
}

// ----- S10 Demo -----
function S10() {
  return (
    <>
      <Chrome index={10} label="10 · DEMO" />
      <Line x={120} y={140} style={TYPE.eyebrow}>데모 · 김나영</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>Next.js 대시보드.</Line>

      <Plate x={120} y={380} width={1680} height={580} delay={0.4}>
        <MapMotif delay={0.8} />
      </Plate>

      <Line x={160} y={420} delay={1.0} style={{ ...TYPE.label, color: ACCENT }}>● LIVE · 17개 시·도</Line>
      <Line x={160} y={900} delay={1.2} style={{ ...TYPE.small, color: WHITE_70 }}>
        전국 지도 + Claude 실시간 리포트 + 팬데믹 조기탐지 탭
      </Line>
    </>
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

// ----- S11 Metrics -----
function S11() {
  return (
    <>
      <Chrome index={11} label="11 · MEASURED" />
      <Line x={120} y={140} style={TYPE.eyebrow}>실측 성능 · walk-forward</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>숫자를 있는 그대로.</Line>

      <Plate x={120} y={380} width={1120} height={580} delay={0.5}>
        <div style={{ padding: 40, fontFamily: FONT }}>
          <MetricRow label="Precision" values={['1.000']} delay={0.9} accent />
          <MetricRow label="AUC-ROC"   values={['0.931']} delay={1.1} />
          <MetricRow label="F1-Score"  values={['0.667']} delay={1.3} />
          <MetricRow label="Recall (보수)" values={['0.500']} delay={1.5} dim />
          <MetricRow label="오경보 건수"   values={['0']} delay={1.7} accent header />
          <div style={{ marginTop: 28, ...TYPE.small, color: WHITE_70 }}>
            Hardened task — 주차 신호 → 2주 후 확진자 임계값 · walk-forward 재현
          </div>
        </div>
      </Plate>

      <Plate x={1280} y={380} width={520} height={580} delay={0.7}>
        <div style={{ padding: 40, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>공모전 vs 현재</div>
          <div style={{ ...TYPE.small, marginTop: 8, color: WHITE_70 }}>정직한 walk-forward · 공모전 주장과 정합</div>
          <div style={{ marginTop: 32 }}>
            <GrangerRow label="공모전 주장 F1"   p="0.710" delay={1.2} />
            <GrangerRow label="Walk-forward F1" p="0.667" delay={1.4} />
            <GrangerRow label="Precision"       p="1.000" delay={1.6} />
          </div>
          <div style={{ marginTop: 36, ...TYPE.small, color: WHITE_70, paddingTop: 20, borderTop: `1px solid ${WHITE_15}` }}>
            <span style={{ color: ACCENT }}>ml/reproduce_validation.py</span> · 누가 돌려도 같은 수치
          </div>
        </div>
      </Plate>
    </>
  );
}
function MetricRow({ label, values, delay, accent, header, dim }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{
      display:'flex', justifyContent:'space-between', alignItems:'baseline',
      padding:'22px 0', borderBottom: header ? `2px solid ${ACCENT}` : `1px solid ${WHITE_15}`,
      opacity: p, fontFeatureSettings:'"lnum"',
    }}>
      <span style={{ fontSize: 30, color: accent ? ACCENT : (dim ? WHITE_45 : WHITE), fontWeight: accent ? 700 : 500 }}>{label}</span>
      <span style={{ fontSize: 48, color: accent ? ACCENT : (dim ? WHITE_45 : WHITE), fontWeight: 600 }}>{values[0]}</span>
    </div>
  );
}
function GrangerRow({ label, p, delay }) {
  const { localTime } = useSprite();
  const pp = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', padding:'14px 0', opacity: pp }}>
      <span style={{ fontSize: 22, color: WHITE }}>{label}</span>
      <span style={{ fontSize: 26, color: ACCENT, fontWeight: 600, fontFeatureSettings:'"lnum"' }}>p={p}</span>
    </div>
  );
}

// ----- S12 Competitive map -----
function S12() {
  const rows = [
    ['BlueDot',        '뉴스·항공 NLP',    '글로벌',  '다수',   ''],
    ['CDC NWSS',       '하수 감시',        '미국',    '1',      ''],
    ['KAIST 연구',     '이동량+독감',      '한국',    '2',      ''],
    ['Xu 2025',        '검색+하수',        '중국',    '2',      ''],
    ['Urban Immune',   '약국·하수·검색',   '한국 시도','3',     'ours'],
  ];
  return (
    <>
      <Chrome index={12} label="12 · COMPETITIVE MAP" />
      <Line x={120} y={140} style={TYPE.eyebrow}>경쟁 맵</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>세 신호를 교차하는 한국 맞춤형.</Line>

      <Plate x={120} y={380} width={1680} height={540} delay={0.5}>
        <div style={{ padding: 40, fontFamily: FONT }}>
          <div style={{ display:'grid', gridTemplateColumns:'2.2fr 2.6fr 1.6fr 1fr', gap: 24, ...TYPE.label, paddingBottom: 18, borderBottom:`1px solid ${WHITE_15}` }}>
            <span>프로젝트</span><span>접근</span><span>지역</span><span style={{ textAlign:'right' }}>신호 수</span>
          </div>
          {rows.map((r, i) => <CompRow key={i} row={r} delay={0.9 + i*0.12} />)}
        </div>
      </Plate>

      <Line x={120} y={960} delay={2.0} style={{ ...TYPE.small, color: WHITE_45 }}>
        솔직 인정 — 데이터 규모, 임상 검증은 다음 단계의 타깃.
      </Line>
    </>
  );
}
function CompRow({ row, delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  const ours = row[4] === 'ours';
  return (
    <div style={{
      display:'grid', gridTemplateColumns:'2.2fr 2.6fr 1.6fr 1fr', gap: 24,
      padding: '20px 0', borderBottom: `1px solid ${WHITE_15}`,
      opacity: p, transform: `translateX(${(1-p)*-12}px)`,
      color: ours ? ACCENT : WHITE, fontSize: 24, fontWeight: ours ? 600 : 400,
    }}>
      <span>{row[0]}{ours && <span style={{ marginLeft:10, fontSize:16, color:'#05070B', background:ACCENT, padding:'2px 10px' }}>OURS</span>}</span>
      <span style={{ color: ours ? ACCENT : WHITE_70 }}>{row[1]}</span>
      <span style={{ color: ours ? ACCENT : WHITE_70 }}>{row[2]}</span>
      <span style={{ textAlign:'right', fontWeight: 600 }}>{row[3]}</span>
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
function S15() {
  const phases = [
    { tag: 'NOW',      date: '~2026.06', title: 'Phase 1', desc: '캡스톤 완주' },
    { tag: 'NEXT',     date: '2026 H2',  title: 'Phase 2', desc: 'ILINet · PoC 1건' },
    { tag: '2027 H1',  date: '2027.01',  title: 'Phase 3', desc: 'ISMS-P · 유료 1곳' },
    { tag: '2027 H2',  date: '2027.07',  title: 'Phase 4', desc: '광역 2곳 · AE 운영' },
    { tag: '2028+',    date: '2028~',    title: 'Phase 5', desc: 'KDCA 납품 · WHO' },
  ];
  return (
    <>
      <Chrome index={15} label="15 · ROADMAP" />
      <Line x={120} y={140} style={TYPE.eyebrow}>로드맵 · 상용화</Line>
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>지금 → 2027 B2G.</Line>

      <RoadmapBar delay={0.5} />

      <div style={{ position:'absolute', left: 120, top: 440, right: 120, display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap: 32 }}>
        {phases.map((p, i) => <PhaseCard key={i} {...p} delay={0.8 + i*0.14} accent={i<=1} />)}
      </div>

      <Plate x={120} y={820} width={820} height={140} delay={1.8}>
        <div style={{ padding: 28, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: WHITE_45 }}>가격 모델 · B2G SaaS</div>
          <div style={{ display:'flex', justifyContent:'space-between', marginTop: 14, fontSize: 26, color: WHITE }}>
            <span>지자체 연 <span style={{ color: ACCENT, fontWeight: 600 }}>2,000~6,000만</span></span>
            <span>광역 연 <span style={{ color: ACCENT, fontWeight: 600 }}>1~3억</span></span>
          </div>
        </div>
      </Plate>
      <Plate x={980} y={820} width={820} height={140} delay={2.0}>
        <div style={{ padding: 28, fontFamily: FONT }}>
          <div style={{ ...TYPE.label, color: ACCENT }}>6개월 목표</div>
          <div style={{ fontSize: 22, color: WHITE, marginTop: 14 }}>정부과제 2천~5천 · PoC 1건 · 논문 1편</div>
        </div>
      </Plate>
    </>
  );
}
function RoadmapBar({ delay }) {
  const { localTime } = useSprite();
  const p = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 1.2)));
  return (
    <div style={{ position:'absolute', left:120, top: 400, right: 120, height: 2, background: WHITE_15 }}>
      <div style={{ width: `${100*p}%`, height: '100%', background: ACCENT }} />
    </div>
  );
}
function PhaseCard({ tag, date, title, desc, delay, accent }) {
  const { localTime } = useSprite();
  const pp = Easing.easeOutCubic(Math.max(0, Math.min(1, (localTime - delay) / 0.5)));
  return (
    <div style={{ opacity: pp, transform:`translateY(${(1-pp)*12}px)`, fontFamily: FONT }}>
      <div style={{
        width: 16, height: 16, borderRadius: 0,
        background: accent ? ACCENT : WHITE_45,
        marginTop: -49, marginBottom: 24,
      }} />
      <div style={{ ...TYPE.label, color: accent ? ACCENT : WHITE_45 }}>{tag}</div>
      <div style={{ fontSize: 32, color: WHITE, fontWeight: 600, marginTop: 10 }}>{title}</div>
      <div style={{ ...TYPE.small, color: WHITE_70, marginTop: 6 }}>{date}</div>
      <div style={{ fontSize: 22, color: WHITE, marginTop: 16, fontWeight: 400 }}>{desc}</div>
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
      <Line x={120} y={200} delay={0.1} style={TYPE.title}>다섯 명의 팀, 나란히.</Line>

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
        <div style={{ padding: 40, fontFamily: FONT, textAlign: 'center' }}>
          <div style={{ fontSize: 120, fontWeight: 700, color: WHITE, letterSpacing: '-0.05em' }}>Q <span style={{ color: ACCENT }}>&</span> A</div>
          <div style={{ ...TYPE.small, color: WHITE_70, marginTop: 12 }}>전원 답변 · 5분</div>
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

window.Scenes = { S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S13, S14, S15, S16, SCENE_DUR };
