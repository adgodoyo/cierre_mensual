/* Pestañas: Reportes, La rutina, Cómo funciona y Dónde está cada cosa. */
const RUTINA = { clave: 'cierre_mensual_token_github', activa: false, ultima: null };
const espera = ms => new Promise(r => setTimeout(r, ms));
function leerToken() { try { return localStorage.getItem(RUTINA.clave) || ''; } catch { return ''; } }
function guardarToken(t) { try { if (t) localStorage.setItem(RUTINA.clave, t); else localStorage.removeItem(RUTINA.clave); } catch { /* navegador sin almacenamiento */ } }
async function gh(ruta, opciones = {}) {
  const token = leerToken();
  const r = await fetch(`https://api.github.com/repos/${APP.meta.repo}/${ruta}`, { ...opciones, cache: 'no-store', headers: { Accept: 'application/vnd.github+json', ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
  if (!r.ok) throw new Error(r.status === 401 ? 'el token no es válido o venció' : r.status === 403 || r.status === 404 ? 'el token no tiene permiso de Actions en este repositorio' : `GitHub respondió ${r.status}`);
  return r.status === 204 ? null : r.json();
}
function nombrePaso(s) {
  const fijos = { 'Set up job': 'Preparar la máquina', 'Complete job': 'Terminar', 'Instalar dependencias': 'Instalar las herramientas', 'Ejecutar el cierre': 'Ejecutar el cierre (los tres agentes)' };
  return fijos[s] || (/checkout/.test(s) ? 'Descargar el repositorio' : /setup-python/.test(s) ? 'Instalar Python' : /configure-pages/.test(s) ? 'Preparar la publicación' : /upload-pages/.test(s) ? 'Empaquetar el tablero' : /deploy-pages/.test(s) ? 'Publicar el tablero' : s);
}
function proximaEjecucion() {
  const h = new Date(), objetivo = new Date(Date.UTC(h.getUTCFullYear(), h.getUTCMonth(), 5, 12));
  if (objetivo <= h) objetivo.setUTCMonth(objetivo.getUTCMonth() + 1);
  return `${objetivo.getUTCDate()} de ${MESES_L[objetivo.getUTCMonth()]} de ${objetivo.getUTCFullYear()}`;
}
TABS.reportes = {
  titulo: 'Reportes',
  render(el) {
    const cid = S.cid === 'TODOS' ? 'AND' : S.cid, x = APP.rep.reportes[cid];
    const r = encabezado(el, `Reporte ejecutivo: ${x.nombre}`, `Cierre de ${mesL(APP.rep.mes)}. Una página, con conclusión, indicadores, alertas, recomendación y gráfico.`);
    if (S.mes !== APP.rep.mes) r.insertAdjacentHTML('beforebegin', `<p class="aviso">Los reportes se generan para el último cierre (${esc(mesL(APP.rep.mes))}); este contenido no cambia con el filtro de mes.</p>`);
    if (x.borrador) r.insertAdjacentHTML('beforebegin', '<p class="aviso"><b>Borrador.</b> Tiene alertas altas y espera la aprobación de una persona.</p>');
    const salida = `03_salidas/${APP.rep.mes}`, slug = x.nombre.replace(/ /g, '_');
    tarjeta(r, { w: 7, t: 'Reporte de una página', s: 'Vista de la página. Abajo puede abrir el PDF incrustado o descargarlo.', html: `<img class="miniatura" src="${x.png}" alt="Reporte ejecutivo de ${esc(x.nombre)}, datos simulados"><details class="origen"><summary>Ver PDF incrustado</summary><iframe class="pdf" loading="lazy" src="${x.pdf}" title="Reporte ejecutivo de ${esc(x.nombre)}"></iframe></details><p class="nota"><a href="${x.pdf}" target="_blank" rel="noopener">Abrir PDF</a> · <a href="${x.pdf}" download>Descargar PDF</a></p>`, src: { tabla: 'saldos, inventario, alertas', script: 'src/reporte.py', ruta: `${salida}/reporte_ejecutivo_${slug}_${APP.rep.mes}.pdf`, filtros: 'concesionario' } });
    const audio = x.audio ? `<audio id="aud" controls preload="metadata" src="${x.audio}"></audio>` : '<p class="aviso">El audio no está disponible; el guion sí.</p>';
    tarjeta(r, { w: 5, t: 'Resumen en audio', s: `Voz: ${x.voz}. El texto se resalta mientras suena.`, html: `${audio}<div class="transcripcion" id="trans">${x.parrafos.map((p, i) => `<p data-i="${i}">${esc(p)}</p>`).join('')}</div>`, src: { script: 'src/reporte.py', ruta: `${salida}/resumen_audio_${slug}.mp3`, filtros: 'concesionario' } });
    tarjeta(r, { w: 12, t: 'Plantilla frente a motor de IA', s: `Motor activo: ${APP.rep.motor}. ${x.estado_motor}. Las cifras deben ser idénticas.`, html: `<div class="lado"><article><h3>Plantilla (sin IA)</h3><p>${esc(x.plantilla.conclusion)}</p><p>${esc(x.plantilla.recomendacion)}</p></article><article><h3>Con motor: ${esc(APP.rep.motor)}</h3>${APP.rep.motor === 'ninguno' ? '<p class="nota">Este cierre corrió sin motor, a costo cero. Con <code>MOTOR=ollama</code>, <code>anthropic</code> u <code>openai</code>, aquí aparece la versión reescrita con los mismos hechos.</p>' : ''}<p>${esc(x.final.conclusion)}</p><p>${esc(x.final.recomendacion)}</p></article></div>`, src: { script: 'src/motor.py', ruta: 'src/motor.py', filtros: 'concesionario' } });
    const a = document.getElementById('aud');
    if (a) {
      const ps = [...document.querySelectorAll('#trans p')], largos = x.parrafos.map(t => t.length), total = largos.reduce((s, v) => s + v, 0); let acu = 0; const cortes = largos.map(v => (acu += v) / total);
      a.addEventListener('timeupdate', () => { if (!a.duration) return; const f = a.currentTime / a.duration, i = cortes.findIndex(c => f <= c); ps.forEach((p, j) => p.classList.toggle('ahora', j === i)); const c = document.getElementById('trans'), act = ps[i]; if (act) c.scrollTop = act.offsetTop - c.offsetTop - 50; });
      ps.forEach((p, i) => { p.style.cursor = 'pointer'; p.onclick = () => { if (a.duration) { a.currentTime = (i ? cortes[i - 1] : 0) * a.duration + .05; a.play(); } }; });
    }
  },
};

TABS.rutina = {
  titulo: 'La rutina',
  render(el) {
    const r = encabezado(el, 'El sistema trabaja solo; la persona decide', 'Cada mes, el día 5 a las 7:00 a. m. de Bogotá, la rutina ejecuta el cierre y pide aprobación si hay alertas altas.');
    const repo = APP.meta.repo;
    if (!repo) r.insertAdjacentHTML('beforebegin', '<p class="aviso">El repositorio aún no está publicado en GitHub. Las ejecuciones y aprobaciones reales aparecerán aquí al publicarlo; abajo se ve la bitácora con la historia simulada.</p>');
    if (repo) tarjeta(r, { w: 12, t: 'Ejecutar la rutina ahora', s: `La rutina corre sola el día 5 de cada mes a las 7:00 a. m. (próxima: ${proximaEjecucion()}). Aquí puede lanzarla en vivo y ver cada paso.`, html: '<div id="rv"></div>', src: { script: '.github/workflows/cierre_mensual.yml', ruta: '.github/workflows/cierre_mensual.yml' } });
    tarjeta(r, { w: 7, t: 'Ejecuciones de GitHub Actions', s: repo ? 'Consultadas en vivo a GitHub.' : 'Disponible al publicar.', html: '<div id="runs"><p class="nota">Sin datos de GitHub todavía.</p></div>', src: { script: '.github/workflows/cierre_mensual.yml', ruta: '.github/workflows/cierre_mensual.yml' } });
    tarjeta(r, { w: 5, t: 'Aprobaciones (Issues)', s: 'Un Issue abierto detiene la versión final.', html: '<div id="issues"><p class="nota">Sin datos de GitHub todavía.</p></div>', src: { script: '.github/workflows/cierre_mensual.yml', ruta: '.github/workflows/cierre_mensual.yml' } });
    tarjeta(r, { id: 'g-bit', w: 12, h: 300, t: 'Línea de tiempo de los 24 cierres (alertas por mes)', s: 'Historia simulada de la rutina: cada punto es un cierre. Pase el cursor para ver su resultado.', src: { tabla: 'bitacora, alertas', script: 'src/procesamiento.py' } });
    tarjeta(r, { w: 7, t: 'Bitácora reciente', s: 'Los últimos pasos registrados.', html: tablaHTML(q(`SELECT fecha, periodo, paso, resultado, accion, responsable FROM bitacora ORDER BY periodo DESC, bitacora_id DESC LIMIT 40`), null, { alto: 390, envolver: ['accion'], fmt: { fecha: v => esc(String(v).slice(0, 16).replace('T', ' ')) } }), src: { tabla: 'bitacora', script: 'src/procesamiento.py' } });
    tarjeta(r, { w: 5, t: 'Historial de versiones (commits)', s: 'Cada fase y cada cierre quedan versionados.', html: tablaHTML(APP.meta.commits.map(c => ({ commit: c.hash, fecha: c.fecha.slice(0, 10), mensaje: c.mensaje })), null, { alto: 390, envolver: ['mensaje'], fmt: { commit: v => repo ? `<a target="_blank" rel="noopener" href="https://github.com/${repo}/commit/${esc(v)}"><code>${esc(v)}</code></a>` : `<code>${esc(v)}</code>` } }), src: { script: 'run_cierre.py', ruta: 'run_cierre.py' } });
    const al = q(`SELECT b.periodo p, b.resultado res, (SELECT COUNT(*) FROM alertas a WHERE a.periodo=b.periodo) n, (SELECT COUNT(*) FROM alertas a WHERE a.periodo=b.periodo AND a.severidad='Alta') altas FROM bitacora b WHERE b.paso='aprobacion' ORDER BY 1`);
    plot('g-bit', [{ x: al.map(x => mesC(x.p)), y: al.map(x => x.n), customdata: al.map(x => [x.res, x.altas]), mode: 'lines+markers', line: { color: '#9FB3C4', width: 1.5 }, marker: { size: al.map(x => x.altas ? 15 : 9), symbol: al.map(x => x.res === 'Aprobado' ? 'circle' : 'diamond'), color: al.map(x => x.res === 'Aprobado' ? C.teal : C.terra), line: { color: C.papel, width: 2 } }, hovertemplate: '%{x}: %{y} alertas (%{customdata[1]} altas)<br>%{customdata[0]}<extra></extra>' }], { xaxis: { type: 'category', tickangle: -45 }, yaxis: { title: 'Alertas', rangemode: 'tozero' }, showlegend: false });
    if (repo) { this.github(repo); this.panel(); }
  },
  panel() {
    const el = document.getElementById('rv'); if (!el) return;
    const token = leerToken(), urlFlujo = `https://github.com/${APP.meta.repo}/actions/workflows/cierre_mensual.yml`;
    el.innerHTML = `<div class="barra"><button type="button" id="rv-ejecutar" class="boton-principal"${RUTINA.activa ? ' disabled' : ''}>▶ Ejecutar la rutina ahora</button>
      <label class="nota"><input type="checkbox" id="rv-aprobado"> Con aprobación humana (publica sin borrador)</label>
      <a href="${urlFlujo}" target="_blank" rel="noopener">Ver la rutina en GitHub</a></div>
      ${token ? `<p class="nota">Conectado a GitHub en este navegador. <button type="button" id="rv-salir">Desconectar</button></p>`
      : `<details class="origen" open><summary>Conectar este navegador con GitHub (una sola vez)</summary><div><p class="nota">GitHub solo permite lanzar la rutina a personas autorizadas. Cree un <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">token de acceso</a> limitado a este repositorio, con permiso <b>Actions: lectura y escritura</b>, y péguelo aquí. Se guarda solo en este navegador. Sin token, el botón abre la página de GitHub para lanzarla desde allí.</p><div class="barra"><input class="campo" id="rv-token" type="password" placeholder="github_pat_…" aria-label="Token de GitHub" style="flex:1"><button type="button" id="rv-guardar">Conectar</button></div></div></details>`}
      <div id="rv-estado" aria-live="polite"></div>`;
    document.getElementById('rv-ejecutar').onclick = () => leerToken() ? this.ejecutar() : window.open(urlFlujo, '_blank', 'noopener');
    const g = document.getElementById('rv-guardar'); if (g) g.onclick = () => { guardarToken(document.getElementById('rv-token').value.trim()); this.panel(); };
    const s = document.getElementById('rv-salir'); if (s) s.onclick = () => { guardarToken(''); this.panel(); };
    if (RUTINA.ultima) this.pintarPasos(RUTINA.ultima);
  },
  estado(html) { const e = document.getElementById('rv-estado'); if (e) e.innerHTML = html; },
  async ejecutar() {
    const aprobado = document.getElementById('rv-aprobado')?.checked || false, desde = Date.now() - 20000;
    RUTINA.activa = true; RUTINA.ultima = null; this.panel();
    try {
      this.estado('<p class="nota">Enviando la orden a GitHub…</p>');
      await gh('actions/workflows/cierre_mensual.yml/dispatches', { method: 'POST', body: JSON.stringify({ ref: APP.meta.rama || 'main', inputs: { mes: APP.meta.mes, aprobado: String(aprobado) } }) });
      let run = null;
      for (let i = 0; i < 30 && !run; i++) {
        this.estado(`<p class="nota">GitHub recibió la orden. Asignando una máquina… (${i * 3} s)</p>`);
        await espera(3000);
        run = (await gh('actions/workflows/cierre_mensual.yml/runs?event=workflow_dispatch&per_page=5')).workflow_runs.find(x => new Date(x.created_at) >= desde);
      }
      if (!run) throw new Error('GitHub no mostró la ejecución a tiempo; revísela en GitHub');
      RUTINA.inicio = new Date(run.created_at);
      while (true) {
        const [r, jobs] = await Promise.all([gh(`actions/runs/${run.id}`), gh(`actions/runs/${run.id}/jobs`)]);
        const pasos = jobs.jobs.flatMap(j => (j.steps || []).filter(p => !(p.name === 'Complete job' || (j !== jobs.jobs[0] && p.name === 'Set up job'))));
        if (r.status === 'completed') pasos.push({ name: 'Terminar', status: 'completed', conclusion: r.conclusion });
        RUTINA.ultima = { run: r, pasos };
        this.pintarPasos(RUTINA.ultima);
        if (r.status === 'completed') break;
        await espera(4000);
      }
    } catch (e) { this.estado(`<p class="aviso">No se pudo lanzar la rutina: ${esc(e.message)}.</p>`); }
    RUTINA.activa = false;
    const b = document.getElementById('rv-ejecutar'); if (b) b.disabled = false;
    if (APP.meta.repo) this.github(APP.meta.repo);
  },
  pintarPasos({ run, pasos }) {
    const vis = pasos.filter(p => !p.name.startsWith('Post '));
    const icono = p => p.status !== 'completed' ? (p.status === 'in_progress' ? '<span class="pp ahora">●</span>' : '<span class="pp">○</span>') : p.conclusion === 'success' ? '<span class="pp ok">✓</span>' : p.conclusion === 'skipped' ? '<span class="pp">–</span>' : '<span class="pp mal">✕</span>';
    const dur = p => p.started_at ? `${n(((p.completed_at ? new Date(p.completed_at) : new Date()) - new Date(p.started_at)) / 1000, 0)} s` : '';
    const total = n((Date.now() - new Date(run.run_started_at || run.created_at)) / 1000, 0);
    const fin = run.status === 'completed'
      ? (run.conclusion === 'success' ? `<p class="aviso" style="background:#D4E6E2;border-color:${C.teal}"><b>Rutina terminada.</b> GitHub tarda uno o dos minutos en servir la nueva versión del tablero. <button type="button" onclick="location.reload()">Recargar el tablero</button></p>` : `<p class="aviso">La rutina terminó con estado «${esc(run.conclusion)}». <a href="${run.html_url}" target="_blank" rel="noopener">Ver el detalle en GitHub</a>.</p>`)
      : `<p class="nota">En curso: ${total} s. <a href="${run.html_url}" target="_blank" rel="noopener">Ver en GitHub</a></p>`;
    this.estado(`<ol class="pasos">${vis.map(p => `<li class="${p.status}">${icono(p)}<span>${esc(nombrePaso(p.name))}</span><small>${dur(p)}</small></li>`).join('') || '<li><span class="pp ahora">●</span><span>Preparando la máquina</span></li>'}</ol>${fin}`);
  },
  async github(repo) {
    try {
      const [runs, issues] = await Promise.all([gh('actions/runs?per_page=12'), gh('issues?state=all&per_page=12')]);
      const cr = document.getElementById('runs'), ci = document.getElementById('issues'); if (!cr || !ci) return;
      const disparo = { workflow_dispatch: 'Manual', schedule: 'Programada', issues: 'Aprobación' };
      cr.innerHTML = tablaHTML(runs.workflow_runs.map(x => ({ fecha: x.created_at.slice(0, 16).replace('T', ' '), disparo: disparo[x.event] || x.event, duración: `${n((new Date(x.updated_at) - new Date(x.run_started_at || x.created_at)) / 60000, 1)} min`, estado: x.conclusion || x.status, enlace: x.html_url })), ['fecha', 'disparo', 'duración', 'estado', 'enlace'], { fmt: { enlace: v => `<a target="_blank" rel="noopener" href="${esc(v)}">ver</a>` }, alto: 280 });
      const lista = issues.filter(x => !x.pull_request);
      ci.innerHTML = tablaHTML(lista.map(x => ({ estado: x.state === 'open' ? 'Abierto' : 'Aprobado', título: x.title, enlace: x.html_url })), null, { fmt: { enlace: v => `<a target="_blank" rel="noopener" href="${esc(v)}">ver</a>` }, envolver: ['título'], alto: 280 });
    } catch (e) { const c = document.getElementById('runs'); if (c) c.innerHTML = `<p class="nota">No se pudo consultar GitHub (${esc(e.message)}).</p>`; }
  },
};

const CAPAS = [
  { t: 'Motor', d: 'El modelo de lenguaje que redacta. Es opcional e intercambiable.', usa: 'Plantillas por defecto; Ollama, Claude u OpenAI con la variable MOTOR.', f: 'src/motor.py', gr: 'Ninguno, Ollama', pago: 'Claude, ChatGPT, Copilot, Gemini' },
  { t: 'Instrucciones', d: 'El manual del agente: rol, entradas, pasos, reglas y salida.', usa: 'CLAUDE.md y tres manuales escritos como un procedimiento para un analista nuevo.', f: '00_manuales/instrucciones_consolidacion.md', gr: 'Archivos Markdown', pago: 'Proyectos de ChatGPT o Claude, agentes de Copilot' },
  { t: 'Herramientas', d: 'Lo que el agente puede hacer con precisión: leer, calcular, validar y publicar.', usa: 'Python, pandas, statsmodels, reportlab y edge-tts.', f: 'src/procesamiento.py', gr: 'Python y librerías abiertas', pago: 'Power Query, Alteryx, Copilot en Excel' },
  { t: 'Datos y memoria', d: 'Donde queda todo, con la huella de cada fila.', usa: 'SQLite con 14 tablas; la bitácora es la memoria de cada cierre.', f: '02_procesados/cierre.db', gr: 'SQLite, Excel, Supabase (plan gratuito)', pago: 'SQL Server, Snowflake, SharePoint' },
  { t: 'Disparador', d: 'Lo que pone a trabajar al sistema sin que nadie lo pida.', usa: 'GitHub Actions: día 5 de cada mes a las 7:00 a. m. de Bogotá.', f: '.github/workflows/cierre_mensual.yml', gr: 'GitHub Actions, n8n autoalojado', pago: 'Power Automate' },
  { t: 'Supervisión humana', d: 'La persona revisa y aprueba. Sin aprobación, el reporte sigue en borrador.', usa: 'Un Issue de GitHub por cada cierre con alertas altas.', f: '.github/workflows/cierre_mensual.yml', gr: 'GitHub Issues', pago: 'Aprobaciones de Teams o Power Automate' },
];
TABS.como = {
  titulo: 'Cómo funciona',
  sel: 0,
  render(el) {
    const r = encabezado(el, 'Las seis capas de un agente', 'Cambie cualquier capa y las demás siguen funcionando. Haga clic en una capa.');
    tarjeta(r, { w: 5, t: 'Arquitectura', s: 'De lo que piensa a lo que se aprueba.', html: `<div class="capas">${CAPAS.map((c, i) => `<button type="button" data-c="${i}"><b>${i + 1}. ${c.t}</b></button>`).join('')}</div>`, src: { script: 'run_cierre.py', ruta: 'CLAUDE.md' } });
    tarjeta(r, { w: 7, t: 'Detalle de la capa', html: '<div id="capa"></div>', src: { script: 'run_cierre.py', ruta: 'README.md' } });
    const pintar = () => { const c = CAPAS[this.sel]; el.querySelectorAll('[data-c]').forEach(b => b.classList.toggle('activo', +b.dataset.c === this.sel)); document.getElementById('capa').innerHTML = `<h3 style="font-size:24px">${c.t}</h3><p>${esc(c.d)}</p><ul class="lista"><li><b>En este proyecto:</b> ${esc(c.usa)}</li><li><b>Archivo:</b> ${enlace(c.f)}</li><li><b>Alternativas gratuitas:</b> ${esc(c.gr)}</li><li><b>Alternativas de pago:</b> ${esc(c.pago)}</li></ul>`; };
    el.querySelectorAll('[data-c]').forEach(b => b.onclick = () => { this.sel = +b.dataset.c; pintar(); }); pintar();
  },
};

TABS.donde = {
  titulo: 'Dónde está cada cosa',
  render(el) {
    const r = encabezado(el, 'El mapa del repositorio', 'Cada carpeta y archivo, con una línea que explica para qué sirve.');
    const nodo = x => { const d = x.descripcion || x.nota ? ` <span>${esc([x.descripcion, x.nota].filter(Boolean).join(' · '))}</span>` : ''; return x.hijos?.length ? `<li><details${x.ruta.split('/').length < 2 ? ' open' : ''}><summary>${enlace(x.ruta, `${x.nombre}/`)}${d}</summary><ul>${x.hijos.map(nodo).join('')}</ul></details></li>` : `<li>${enlace(x.ruta, x.nombre + (x.tipo === 'carpeta' ? '/' : ''))}${d}</li>`; };
    tarjeta(r, { w: 12, t: 'cierre_mensual/', s: 'Abra las carpetas para ver su contenido.', html: `<ul class="arbol">${APP.meta.arbol.map(nodo).join('')}</ul>`, src: { script: 'src/tablero.py', ruta: 'docs/data/meta.json' } });
  },
};
