// WebGLBackground.jsx — full-bleed shader background.
// Slow, abstract field of flowing lines + noise. Responds to scene index
// and the global time. Draws to a <canvas> at the Stage's size.
//
// Props:
//   variant: number     // scene index 0..15, subtly remixes palette / motion
//   accent:  [r,g,b]    // accent color in 0..1 RGB
//   width, height

function WebGLBackground({ variant = 0, accent = [0.35, 0.95, 1.0], bg = [0.02, 0.025, 0.035], atmosphere = 0.55, mood = 0, width = 1920, height = 1080 }) {
  const canvasRef = React.useRef(null);
  const glRef = React.useRef(null);
  const progRef = React.useRef(null);
  const startRef = React.useRef(performance.now());
  const variantRef = React.useRef(variant);
  const accentRef = React.useRef(accent);
  const bgRef = React.useRef(bg);
  const atmoRef = React.useRef(atmosphere);
  const moodRef = React.useRef(mood);

  React.useEffect(() => { variantRef.current = variant; }, [variant]);
  React.useEffect(() => { accentRef.current = accent; }, [accent]);
  React.useEffect(() => { bgRef.current = bg; }, [bg]);
  React.useEffect(() => { atmoRef.current = atmosphere; }, [atmosphere]);
  React.useEffect(() => { moodRef.current = mood; }, [mood]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl', { antialias: true, premultipliedAlpha: false });
    if (!gl) return;
    glRef.current = gl;

    const vsrc = `
      attribute vec2 aPos;
      varying vec2 vUV;
      void main(){
        vUV = aPos * 0.5 + 0.5;
        gl_Position = vec4(aPos, 0.0, 1.0);
      }`;

    const fsrc = `
      precision highp float;
      varying vec2 vUV;
      uniform vec2  uRes;
      uniform float uTime;
      uniform float uVariant;
      uniform vec3  uAccent;
      uniform vec3  uBg;
      uniform float uAtmo;
      uniform float uMood;

      // hash / noise
      float hash(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
      float noise(vec2 p){
        vec2 i = floor(p), f = fract(p);
        float a = hash(i);
        float b = hash(i + vec2(1.0,0.0));
        float c = hash(i + vec2(0.0,1.0));
        float d = hash(i + vec2(1.0,1.0));
        vec2 u = f*f*(3.0-2.0*f);
        return mix(a,b,u.x) + (c-a)*u.y*(1.0-u.x) + (d-b)*u.x*u.y;
      }
      float fbm(vec2 p){
        float v = 0.0;
        float amp = 0.5;
        for(int i=0;i<5;i++){
          v += amp*noise(p);
          p *= 2.02;
          amp *= 0.5;
        }
        return v;
      }

      void main(){
        vec2 uv = (gl_FragCoord.xy - 0.5*uRes) / min(uRes.x, uRes.y);
        float t = uTime * 0.08;
        float v = uVariant;

        // warp coordinates
        vec2 q = uv*1.2 + vec2(t*0.3, -t*0.25 + v*0.37);
        float n = fbm(q);
        vec2 q2 = uv*2.0 + vec2(fbm(q+t), fbm(q-t));
        float n2 = fbm(q2);

        // flowing contour lines — density rises with atmosphere
        float density = mix(5.0, 16.0, uAtmo);
        float line = abs(sin((n2*density + t*2.0 + v*1.7)*3.14159));
        float sharp = mix(0.08, 0.02, uAtmo);
        line = 1.0 - smoothstep(0.0, sharp, line);

        // subtle radial falloff toward center
        float r = length(uv);
        float vign = smoothstep(1.6, 0.2, r);

        // base (from mood)
        vec3 col = uBg;

        // haze — stronger in neon, softer in paper
        col += mix(0.02, 0.10, uAtmo) * vec3(n2) * vign;

        // accent line glow — intensity scales with atmosphere
        float glow = mix(0.20, 0.95, uAtmo);
        col += uAccent * line * glow * vign;

        // horizontal drifting band
        float band = smoothstep(0.48, 0.5, fract(uv.y*0.8 + t*0.5 + v*0.1));
        col += uAccent * band * 0.04 * (1.0 - uMood*0.5);

        // film grain — inverted polarity in paper mode so it feels like print
        float g = hash(gl_FragCoord.xy + t*60.0) - 0.5;
        col += g * mix(0.02, 0.05, uMood);

        gl_FragColor = vec4(col, 1.0);
      }`;

    function compile(type, src){
      const sh = gl.createShader(type);
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error(gl.getShaderInfoLog(sh));
        return null;
      }
      return sh;
    }
    const vs = compile(gl.VERTEX_SHADER, vsrc);
    const fs = compile(gl.FRAGMENT_SHADER, fsrc);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    progRef.current = prog;

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1,-1,  1,-1,  -1,1,   -1,1,  1,-1,  1,1
    ]), gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(prog, 'aPos');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(prog, 'uRes');
    const uTime = gl.getUniformLocation(prog, 'uTime');
    const uVariant = gl.getUniformLocation(prog, 'uVariant');
    const uAccent = gl.getUniformLocation(prog, 'uAccent');
    const uBg = gl.getUniformLocation(prog, 'uBg');
    const uAtmo = gl.getUniformLocation(prog, 'uAtmo');
    const uMood = gl.getUniformLocation(prog, 'uMood');

    let raf;
    const render = () => {
      const w = canvas.width = width;
      const h = canvas.height = height;
      gl.viewport(0, 0, w, h);
      gl.useProgram(prog);
      gl.uniform2f(uRes, w, h);
      gl.uniform1f(uTime, (performance.now() - startRef.current)/1000);
      gl.uniform1f(uVariant, variantRef.current);
      const a = accentRef.current, b = bgRef.current;
      gl.uniform3f(uAccent, a[0], a[1], a[2]);
      gl.uniform3f(uBg, b[0], b[1], b[2]);
      gl.uniform1f(uAtmo, atmoRef.current);
      gl.uniform1f(uMood, moodRef.current);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      raf = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(raf);
  }, [width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width} height={height}
      style={{ position:'absolute', inset:0, width:'100%', height:'100%', display:'block' }}
    />
  );
}

window.WebGLBackground = WebGLBackground;
