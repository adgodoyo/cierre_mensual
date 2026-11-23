/* Pestañas: Resumen, El recorrido del dato y Base de datos. */
const fechaX = p => `${p}-01`;
const invSerie = () => qc(`inv|${S.cid}|${S.sede}|${S.linea}`, () => q(`SELECT i.periodo, SUM(CASE WHEN i.rango='>60' THEN i.costo ELSE 0 END) viejo, SUM(i.costo) total FROM inventario i WHERE ${condInv('i', false)} GROUP BY 1 ORDER BY 1`));
const fiSerie = () => qc(`fi|${S.cid}|${S.sede}`, () => q(`SELECT periodo, 1.0*SUM(creditos)/SUM(unidades) pen, 1.0*SUM(polizas)/SUM(unidades) seg FROM fi WHERE ${inSedes()} GROUP BY 1 ORDER BY 1`));

TABS.resumen = {
  titulo: 'Resumen',
  render(el) {
    const serie = mensual(), inv = invSerie(), fi = fiSerie(), ant = mesMenos(S.mes, 1), aa = mesMenos(S.mes, 12);
    const alcance = S.cid === 'TODOS' ? 'la red' : APP.nombres[S.cid];
    el.insertAdjacentHTML('beforeend', `<div class="intro"><h2>${esc(alcance)}: ${esc(mesL(S.mes))}</h2><p>Los cinco indicadores del mes, cada uno comparado con el mes anterior y con el mismo mes del año pasado.</p></div><div class="kpis" id="kpis"></div>`);
    const v = (arr, p, k) => arr.find(x => x.periodo === p)?.[k];
    const rel = (a, b) => a == null || !b ? 's. d.' : `${a / b - 1 >= 0 ? '+' : ''}${n((a / b - 1) * 100, 1)} %`;
    const pp = (a, b) => a == null || b == null ? 's. d.' : `${a - b >= 0 ? '+' : ''}${n((a - b) * 100, 1)} pp`;
    const defs = [
      ['Ingresos', serie, 'ingresos', MM, rel], ['Margen bruto', serie, 'margen', P, pp], ['Utilidad operativa', serie, 'utilidad', M, rel],
      ['Inventario >60 días', inv, 'viejo', x => M(x, 0), rel], ['Penetración F&I', fi, 'pen', P, pp],
    ];
    const caja = document.getElementById('kpis');
    defs.forEach(([t, arr, k, f, dif], i) => caja.insertAdjacentHTML('beforeend', `<article class="kpi"><small>${esc(t)}</small><strong>${esc(f(v(arr, S.mes, k)))}</strong><div class="var">${dif(v(arr, S.mes, k), v(arr, ant, k))} vs. mes ant.<br>${dif(v(arr, S.mes, k), v(arr, aa, k))} vs. año ant.</div><div class="spark" id="sp${i}"></div></article>`));
    defs.forEach(([t, arr, k], i) => {
      const d = arr.filter(x => x.periodo <= S.mes);
      plot(`sp${i}`, [{ x: d.map(x => mesC(x.periodo)), y: d.map(x => x[k]), type: 'scatter', mode: 'lines', line: { color: C.navy, width: 2 }, hovertemplate: '%{x}<extra></extra>' }],
        { margin: { l: 2, r: 2, t: 2, b: 2 }, xaxis: { visible: false }, yaxis: { visible: false }, showlegend: false }, { displayModeBar: false });
    });
    const r = document.createElement('div'); r.className = 'rejilla'; el.appendChild(r);
    tarjeta(r, { id: 'g1', w: 8, h: 390, t: 'Ingresos mensuales por concesionario (COP miles de millones)', s: 'Use la barra inferior para acercarse a un periodo. Clic en la leyenda para ocultar una serie.', src: { tabla: 'saldos', script: 'src/ingesta.py', filtros: 'concesionario, sede, línea' } });
    tarjeta(r, { id: 'g30', w: 4, h: 390, t: 'Mapa de la red', s: 'Burbuja = ingresos del mes. Color = margen bruto. Clic para filtrar.', src: { tabla: 'saldos, concesionarios', script: 'src/ingesta.py', filtros: 'mes, línea' } });
    plot('g1', CONC.map((c, i) => {
      const d = mensual(c, c === S.cid ? S.sede : '', S.linea);
      const activo = S.cid === 'TODOS' || c === S.cid;
      return { x: d.map(x => fechaX(x.periodo)), y: d.map(x => x.ingresos / 1e9), name: APP.nombres[c], mode: 'lines+markers', line: { color: SERIES[i], dash: TRAZOS[i], width: activo ? 2.6 : 1.4 }, marker: { symbol: SIMBOLOS[i], size: 6 }, opacity: activo ? 1 : .55, hovertemplate: `${APP.nombres[c]}<br>%{x|%b %Y}: $%{y:.1f} mil M<extra></extra>` };
    }), { hovermode: 'x unified', xaxis: { type: 'date', tickformat: '%b %y', rangeslider: { thickness: .1, bgcolor: '#EFE7DA' } }, yaxis: { title: 'COP miles de millones' } });
    const coords = { AND: [4.71, -74.07, 'Bogotá'], VAL: [3.45, -76.53, 'Cali'], CAR: [10.97, -74.8, 'Barranquilla'], LLA: [4.14, -73.2, 'Villavicencio'] };
    const dat = CONC.map(c => ({ c, ...(enMes(mensual(c, '', S.linea), S.mes) || {}) }));
    const mapa = plot('g30', [{ type: 'scattergeo', lat: dat.map(d => coords[d.c][0]), lon: dat.map(d => coords[d.c][1]), text: dat.map(d => APP.nombres[d.c]), customdata: dat.map(d => [d.c, MM(d.ingresos), P(d.margen)]), mode: 'markers+text', textposition: dat.map(d => ({ AND: 'top center', VAL: 'bottom center', CAR: 'top center', LLA: 'bottom right' }[d.c])), textfont: { size: 10, color: C.tinta },
      marker: { size: dat.map(d => 13 + 25 * d.ingresos / Math.max(...dat.map(x => x.ingresos))), color: dat.map(d => d.margen * 100), colorscale: [[0, '#A9BED0'], [1, C.navy]], line: { color: C.papel, width: 2 }, colorbar: { title: 'Margen %', thickness: 9, len: .6 } }, hovertemplate: '%{text}<br>Ingresos: %{customdata[1]}<br>Margen: %{customdata[2]}<extra></extra>' }],
      { margin: { l: 0, r: 0, t: 0, b: 0 }, geo: { scope: 'south america', resolution: 50, lataxis: { range: [-5, 14] }, lonaxis: { range: [-82, -65] }, bgcolor: 'rgba(0,0,0,0)', landcolor: '#E7DECF', countrycolor: '#FFFFFF', showcountries: true, coastlinecolor: '#BFB4A2', showocean: false, showlakes: false } });
    mapa?.on('plotly_click', e => fijarFiltro('cid', e.points[0].customdata[0]));
  },
};

const ETAPAS = [['crudo', 'Archivo crudo', 'Como llega de la sede'], ['limpia', 'Tabla limpia', 'Una fila por registro'], ['base', 'Base de datos', 'Carga con huella'], ['modelo', 'Formato', 'Línea consolidada'], ['grafico', 'Gráfico', 'Serie del indicador'], ['reporte', 'Reporte', 'Página ejecutiva']];
TABS.recorrido = {
  titulo: 'El recorrido del dato',
  etapa: 'crudo',
  render(el) {
    el.insertAdjacentHTML('beforeend', `<div class="intro"><h2>El recorrido de una cifra</h2><p>Siga la cuenta 2205 Proveedores desde el archivo que envió la sede hasta el reporte. Haga clic en cada etapa.</p></div><div class="barra"><label>Sede a rastrear <select class="campo" id="rec-sede">${APP.sedes.filter(x => S.cid === 'TODOS' || x.concesionario_id === S.cid).map(x => `<option value="${x.sede_id}">${esc(x.nombre)}</option>`).join('')}</select></label></div><div class="flujo">${ETAPAS.map(([k, t, s]) => `<button type="button" class="paso" data-e="${k}"><b>${t}</b><small>${s}</small></button>`).join('')}</div><div class="rejilla" id="rec"></div>`);
    const sel = document.getElementById('rec-sede');
    const pref = S.sede || (S.cid === 'AND' || S.cid === 'TODOS' ? 'SUR' : sel.value); sel.value = pref;
    const pintar = () => this.etapaVista(sel.value);
    sel.addEventListener('change', pintar);
    el.querySelectorAll('.paso').forEach(b => b.addEventListener('click', () => { this.etapa = b.dataset.e; pintar(); }));
    pintar();
  },
  etapaVista(sede) {
    document.querySelectorAll('.paso').forEach(b => b.classList.toggle('activo', b.dataset.e === this.etapa));
    const r = document.getElementById('rec'); r.querySelectorAll('.js-plotly-plot').forEach(g => Plotly.purge(g)); r.innerHTML = '';
    const info = APP.sedes.find(x => x.sede_id === sede), cid = info.concesionario_id, vista = APP.meta.vistas[S.mes]?.[sede];
    if (this.etapa === 'crudo') {
      const ancho = Math.max(...vista.filas.map(f => f.celdas.length));
      const filas = vista.filas.map(f => { const o = { fila: f.n, _m: f.marca }; for (let i = 0; i < ancho; i++) o[String.fromCharCode(65 + i)] = f.celdas[i] ?? ''; return o; });
      tarjeta(r, { w: 12, t: `Así llegó: ${vista.archivo.split('/').pop()}`, s: `Formato ${vista.formato.toUpperCase()}, ${vista.total_filas} filas. Se muestran las primeras filas y, resaltadas, las de la cuenta 2205.`, html: tablaHTML(filas, ['fila', ...Array.from({ length: ancho }, (_, i) => String.fromCharCode(65 + i))], { marca: f => f._m }), src: { script: '04_pruebas/generar_datos.py', ruta: vista.archivo } });
    } else if (this.etapa === 'limpia') {
      const filas = q(`SELECT periodo, sede_id, cuenta_origen, cuenta_codigo, saldo, fuente FROM saldos WHERE periodo=? AND sede_id=? AND cuenta_codigo='2205'`, [S.mes, sede]);
      tarjeta(r, { w: 12, t: 'Las mismas filas, ordenadas', s: 'Cada fila conserva el archivo y la celda exacta de donde salió.', html: tablaHTML(filas, null, { fmt: { saldo: v => M(v) } }), src: { tabla: 'saldos', script: 'src/ingesta.py' } });
    } else if (this.etapa === 'base') {
      const filas = q(`SELECT periodo, archivo, tabla, filas, estado, modo, commit_hash, cargado_en FROM cargas WHERE periodo=? AND archivo LIKE ?`, [S.mes, `%/${sede}_balance%`]);
      tarjeta(r, { w: 12, t: 'La huella de la carga', s: 'La tabla cargas registra qué archivo entró, cuántas filas agregó, cuándo y con qué versión del código.', html: tablaHTML(filas), src: { tabla: 'cargas', script: 'src/ingesta.py' } });
    } else if (this.etapa === 'modelo') {
      const filas = q(`SELECT c.codigo_formato, c.linea_formato, s.sede_id, SUM(x.saldo) saldo FROM saldos x JOIN cuentas c USING(cuenta_codigo) JOIN sedes s ON s.sede_id=x.sede_id WHERE x.periodo=? AND s.concesionario_id=? AND c.cuenta_codigo='2205' GROUP BY 1,2,3`, [S.mes, cid]);
      filas.push({ codigo_formato: 'ESF.2.02', linea_formato: 'Consolidado', sede_id: 'Todas', saldo: filas.reduce((a, f) => a + f.saldo, 0) });
      tarjeta(r, { w: 12, t: 'La línea en el formato consolidado', s: 'La cuenta PUC 2205 se homologa a ESF.2.02 y se suman las sedes.', html: tablaHTML(filas, null, { fmt: { saldo: v => M(v) }, marca: f => f.sede_id === sede }), src: { tabla: 'saldos, cuentas', script: 'src/procesamiento.py', ruta: `03_salidas/${S.mes}/formato_consolidado_${S.mes}.xlsx` } });
    } else if (this.etapa === 'grafico') {
      tarjeta(r, { id: 'rec-g', w: 12, h: 340, t: `Proveedores de ${info.nombre}, últimos 24 meses (COP millones)`, s: 'La misma cifra, ahora como serie para ver si el mes se sale de lo normal.', src: { tabla: 'saldos', script: 'src/ingesta.py' } });
      const d = q(`SELECT periodo, SUM(saldo) v FROM saldos WHERE sede_id=? AND cuenta_codigo='2205' GROUP BY 1 ORDER BY 1`, [sede]);
      plot('rec-g', [{ x: d.map(x => mesC(x.periodo)), y: d.map(x => x.v / 1e6), type: 'scatter', mode: 'lines+markers', line: { color: C.navy, width: 2 }, marker: { size: 7, color: d.map(x => x.periodo === S.mes ? C.terra : C.navy) }, hovertemplate: '%{x}: $%{y:,.1f} M<extra></extra>' }], { yaxis: { title: 'COP millones' } });
    } else {
      const rep = APP.rep.reportes[cid];
      tarjeta(r, { w: 12, t: `Página ejecutiva de ${rep.nombre}`, s: 'El reporte resume el cierre más reciente; cada hallazgo muestra su archivo y celda.', html: `<img class="miniatura" style="max-width:620px" src="${rep.png}" alt="Reporte ejecutivo de ${esc(rep.nombre)}, datos simulados">`, src: { script: 'src/reporte.py', ruta: `03_salidas/${APP.rep.mes}/reporte_ejecutivo_${rep.nombre.replace(/ /g, '_')}_${APP.rep.mes}.pdf` } });
    }
  },
};

const CONSULTAS = () => {
  const m = S.mes, ml = MESES_L[+m.slice(5) - 1], s = inSedes('x');
  return [
    [`Ventas por canal en ${ml}`, `SELECT x.canal, COUNT(*) AS unidades, SUM(x.precio - x.descuento) AS ventas_netas\nFROM ventas x\nWHERE x.periodo = '${m}' AND ${s}\nGROUP BY x.canal ORDER BY ventas_netas DESC;`],
    ['Cuentas sin mapear', `SELECT x.periodo, x.sede_id, x.cuenta_origen, x.saldo, x.fuente\nFROM saldos x\nWHERE x.cuenta_codigo IS NULL AND ${s};`],
    ['Top 10 gastos atípicos', `SELECT a.periodo, a.hallazgo, a.impacto_cop, a.origen\nFROM alertas a\nWHERE a.regla = 'anomalia_gasto'\nORDER BY a.impacto_cop DESC LIMIT 10;`],
    ['Inventario de más de 60 días por sede', `SELECT s.nombre AS sede, COUNT(*) AS unidades, SUM(x.costo) AS valor\nFROM inventario x JOIN sedes s USING (sede_id)\nWHERE x.periodo = '${m}' AND x.rango = '>60' AND ${s}\nGROUP BY s.nombre ORDER BY valor DESC;`],
    ['Margen por modelo', `SELECT x.modelo, COUNT(*) AS unidades, ROUND(100.0 * SUM(x.margen) / SUM(x.precio - x.descuento), 1) AS margen_pct\nFROM ventas x\nWHERE x.periodo = '${m}' AND ${s}\nGROUP BY x.modelo ORDER BY margen_pct DESC;`],
    ['Alertas altas del mes', `SELECT a.concesionario_id, a.hallazgo, a.impacto_cop, a.origen\nFROM alertas a\nWHERE a.periodo = '${m}' AND a.severidad = 'Alta'\nORDER BY a.impacto_cop DESC;`],
    ['Personal por rol', `SELECT x.rol, SUM(x.personas) AS personas, SUM(x.costo) AS costo\nFROM personal x\nWHERE x.periodo = '${m}' AND ${s}\nGROUP BY x.rol ORDER BY costo DESC;`],
    ['Saldo wholesale por entidad', `SELECT x.entidad, SUM(x.saldo) AS saldo, ROUND(100.0 * SUM(x.interes_mes) / SUM(x.saldo), 2) AS tasa_mensual_pct\nFROM obligaciones x\nWHERE x.periodo = '${m}' AND ${s}\nGROUP BY x.entidad ORDER BY saldo DESC;`],
    ['Unidades de Usados más antiguas', `SELECT x.vin, x.modelo, x.sede_id, x.dias, x.costo, x.fecha_ingreso\nFROM inventario x\nWHERE x.periodo = '${m}' AND x.linea = 'Usados' AND ${s}\nORDER BY x.dias DESC LIMIT 10;`],
    ['Filas cargadas por mes', `SELECT periodo, COUNT(*) AS archivos, SUM(filas) AS filas\nFROM cargas\nGROUP BY periodo ORDER BY periodo;`],
  ];
};
const TABLAS_MES = ['saldos', 'ventas', 'inventario', 'gastos', 'personal', 'fi', 'obligaciones', 'alertas', 'cargas', 'bitacora'];

TABS.bd = {
  titulo: 'Base de datos',
  exp: { tabla: 'saldos', pag: 0, orden: null, dir: 'ASC', busca: '' },
  render(el) {
    const r = encabezado(el, 'La base de datos, abierta en su navegador', 'Esta es la base SQLite real del proyecto. Nada se envía a un servidor: cada consulta corre en este computador.');
    tarjeta(r, { w: 12, t: 'Diagrama entidad-relación', s: 'Cada caja es una tabla y cada línea una llave. Haga clic en una tabla para abrirla abajo.', html: `<div class="er-caja">${this.svgER()}</div>`, src: { tabla: 'sqlite_master', script: 'src/esquema.py', ruta: 'src/esquema.py' } });
    tarjeta(r, { w: 8, t: 'Explorador de tablas', s: 'Ordene con clic en la columna y busque en todas las columnas.', html: '<div id="exp"></div>', src: { tabla: 'todas', script: 'src/ingesta.py', ruta: 'docs/data/cierre.db' } });
    tarjeta(r, { w: 4, t: 'Diccionario de datos', s: 'Qué significa cada campo de la tabla abierta.', html: '<div id="dicc"></div>', src: { script: 'src/esquema.py', ruta: '00_manuales/diccionario_de_datos.md' } });
    tarjeta(r, { w: 12, t: 'Consultas listas', s: 'Clic en una pregunta: verá el SQL, el resultado y su gráfico. También puede escribir su propia consulta.', html: `<div class="consultas">${CONSULTAS().map(([t], i) => `<button type="button" data-c="${i}">${esc(t)}</button>`).join('')}</div><textarea class="sql" id="sql" spellcheck="false" aria-label="Editor SQL"></textarea><div class="barra" style="margin-top:8px"><button type="button" id="correr">Ejecutar consulta</button><span class="nota" id="sql-msg"></span></div><div class="rejilla"><div class="w7" style="grid-column:span 7;min-width:0" id="sql-res"></div><div style="grid-column:span 5;min-width:0"><div id="sql-g" style="height:300px"></div></div></div>`, src: { tabla: 'según la consulta', script: 'docs/js/tabs_datos.js', ruta: 'docs/data/cierre.db', filtros: 'concesionario, sede y mes en las consultas listas' } });
    tarjeta(r, { w: 7, id: 'g-crec', h: 390, t: 'Cómo se actualiza: filas por tabla, mes a mes', s: 'Mueva el mes o presione reproducir para ver crecer la base en sus 24 cargas.', src: { tabla: 'todas las tablas mensuales', script: 'src/ingesta.py' } });
    tarjeta(r, { w: 5, t: 'Bitácora del mes', s: 'Cada ejecución, qué hizo y quién aprobó.', html: '<div class="barra"><button type="button" id="play">Reproducir</button><input id="mes-rango" type="range" min="0" max="23" aria-label="Mes de la carga" style="flex:1"><b id="mes-et"></b></div><div id="bit"></div>', src: { tabla: 'bitacora', script: 'src/procesamiento.py' } });
    tarjeta(r, { w: 7, t: 'Qué cambió entre dos meses', s: 'Compara filas agregadas e indicadores.', html: `<div class="barra"><label>Desde <select class="campo" id="d-a"></select></label><label>Hasta <select class="campo" id="d-b"></select></label></div><div id="dif"></div>`, src: { tabla: 'todas las tablas mensuales', script: 'docs/js/tabs_datos.js' } });
    const mt = APP.meta, repo = mt.repo, crudo = repo ? `https://raw.githubusercontent.com/${repo}/${mt.rama}/docs/data/cierre.db` : null;
    tarjeta(r, { w: 5, t: 'Dónde vive', s: 'La base es un solo archivo dentro del repositorio.', html: `<ul class="lista"><li>Tamaño: <b>${n(mt.db_bytes / 1e6, 1)} MB</b></li><li>Ruta: ${enlace(mt.db_ruta)}</li><li>Último commit: ${repo ? `<a target="_blank" rel="noopener" href="https://github.com/${repo}/commit/${mt.commit}"><code>${esc(mt.commit)}</code></a>` : `<code>${esc(mt.commit)}</code>`}</li><li>Visor alterno: ${crudo ? `<a target="_blank" rel="noopener" href="https://lite.datasette.io/?url=${encodeURIComponent(crudo)}">abrir en Datasette Lite</a>` : 'Datasette Lite se activa al publicar en GitHub'}</li></ul>`, src: { script: 'src/tablero.py', ruta: mt.db_ruta } });
    el.querySelectorAll('g.t').forEach(g => { const abrir = () => { Object.assign(this.exp, { tabla: g.dataset.t, pag: 0, orden: null, busca: '' }); this.explorador(); document.getElementById('exp').scrollIntoView({ behavior: 'smooth', block: 'center' }); }; g.addEventListener('click', abrir); g.addEventListener('keydown', e => { if (e.key === 'Enter') abrir(); }); });
    this.explorador();
    const ta = document.getElementById('sql'), cons = CONSULTAS();
    el.querySelectorAll('[data-c]').forEach(b => b.addEventListener('click', () => { el.querySelectorAll('[data-c]').forEach(x => x.classList.remove('activo')); b.classList.add('activo'); ta.value = cons[+b.dataset.c][1]; this.correr(); }));
    document.getElementById('correr').addEventListener('click', () => this.correr());
    ta.value = cons[0][1]; el.querySelector('[data-c="0"]').classList.add('activo'); this.correr();
    this.crecimiento();
  },
  svgER() {
    const P0 = { gastos: [20, 20], personal: [20, 235], fi: [20, 400], ventas: [290, 20], inventario: [290, 270], obligaciones: [290, 470], concesionarios: [560, 20], sedes: [560, 120], cargas: [560, 330], cuentas: [830, 20], saldos: [830, 190], bitacora: [830, 370], pronosticos: [1100, 20], alertas: [1100, 200] };
    const W = 240, L = 15, T = 25, E = APP.meta.esquema;
    const caja = t => { const cols = E[t].columnas.filter(c => !['fuente', 'cargado_en'].includes(c.nombre)); return { x: P0[t][0], y: P0[t][1], w: W, h: T + cols.length * L + 19, cols }; };
    let lineas = '', cajas = '';
    Object.keys(E).forEach(t => E[t].columnas.filter(c => c.fk).forEach(c => {
      const a = caja(t), b = caja(c.fk), der = b.x >= a.x + W, izq = b.x + W <= a.x;
      const x1 = der ? a.x + W : izq ? a.x : a.x + W / 2, y1 = der || izq ? a.y + 18 : (b.y > a.y ? a.y + a.h : a.y), x2 = der ? b.x : izq ? b.x + W : b.x + W / 2, y2 = der || izq ? b.y + 18 : (b.y > a.y ? b.y : b.y + b.h), m = (x1 + x2) / 2;
      lineas += `<path d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}" fill="none" stroke="${C.teal}" stroke-opacity=".55" stroke-width="1.5"><title>${t}.${c.nombre} → ${c.fk}</title></path><circle cx="${x2}" cy="${y2}" r="3.5" fill="${C.teal}"/>`;
    }));
    Object.keys(E).forEach(t => {
      const b = caja(t);
      cajas += `<g class="t" data-t="${t}" tabindex="0" role="button" aria-label="Abrir tabla ${t}"><rect class="cuerpo" x="${b.x}" y="${b.y}" width="${W}" height="${b.h}" rx="5" fill="${C.papel}" stroke="${C.borde}"/><path d="M${b.x},${b.y + T} v-20 a5,5 0 0 1 5,-5 h${W - 10} a5,5 0 0 1 5,5 v20 z" fill="${C.navy}"/><text x="${b.x + 9}" y="${b.y + 17}" fill="#fff" font-size="13" font-weight="600">${t}</text>`;
      b.cols.forEach((c, i) => { const y = b.y + T + 12 + i * L; cajas += `<text x="${b.x + 8}" y="${y}" font-size="10.5" fill="${c.pk ? C.terra : c.fk ? C.teal : C.tinta}" font-weight="${c.pk || c.fk ? 600 : 400}">${c.pk ? 'PK ' : c.fk ? 'FK ' : ''}${c.nombre}</text><text x="${b.x + W - 8}" y="${y}" font-size="9.5" text-anchor="end" fill="${C.suave}">${c.tipo}</text>`; });
      cajas += `<text x="${b.x + 8}" y="${b.y + b.h - 5}" font-size="9.5" fill="${C.suave}">+ fuente, cargado_en</text></g>`;
    });
    return `<svg class="er" viewBox="0 0 1360 640" role="group" aria-label="Diagrama entidad-relación">${lineas}${cajas}</svg>`;
  },
  explorador() {
    const x = this.exp, E = APP.meta.esquema[x.tabla], cols = E.columnas.map(c => c.nombre), porPag = 15;
    const cond = x.busca ? `WHERE ${cols.map(c => `CAST("${c}" AS TEXT) LIKE ?`).join(' OR ')}` : '', ps = x.busca ? cols.map(() => `%${x.busca}%`) : [];
    const total = q(`SELECT COUNT(*) c FROM ${x.tabla} ${cond}`, ps)[0].c;
    const orden = x.orden ? `ORDER BY "${x.orden}" ${x.dir}` : '';
    const filas = q(`SELECT * FROM ${x.tabla} ${cond} ${orden} LIMIT ${porPag} OFFSET ${x.pag * porPag}`, ps);
    const paginas = Math.max(1, Math.ceil(total / porPag));
    document.getElementById('exp').innerHTML = `<div class="barra"><select class="campo" id="exp-t" aria-label="Tabla">${Object.keys(APP.meta.esquema).map(t => `<option${t === x.tabla ? ' selected' : ''}>${t}</option>`).join('')}</select><input class="campo" id="exp-b" placeholder="Buscar en la tabla" value="${esc(x.busca)}" aria-label="Buscar"><span class="nota"><b>${n(total)}</b> filas · ${cols.length} columnas</span><button type="button" id="ant"${x.pag ? '' : ' disabled'}>Anterior</button><span class="nota">${n(x.pag + 1)} de ${n(paginas)}</span><button type="button" id="sig"${x.pag + 1 < paginas ? '' : ' disabled'}>Siguiente</button></div><div class="tabla-caja"><table><thead><tr>${cols.map(c => `<th data-col="${c}">${c}${x.orden === c ? (x.dir === 'ASC' ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${filas.map(f => `<tr>${cols.map(c => `<td class="${typeof f[c] === 'number' ? 'num' : ''}">${typeof f[c] === 'number' ? n(f[c], Number.isInteger(f[c]) ? 0 : 4) : esc(f[c])}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${cols.length}">Sin filas</td></tr>`}</tbody></table></div>`;
    document.getElementById('dicc').innerHTML = `<p class="nota"><b>${esc(x.tabla)}</b>: ${esc(E.descripcion)}<br>Lo escribe ${enlace(E.script.includes('*') ? 'src' : E.script, E.script)}</p>${tablaHTML(E.columnas.map(c => ({ campo: c.nombre, significado: c.significado, tipo: c.tipo, ejemplo: c.ejemplo })), null, { alto: 345, envolver: ['significado'] })}`;
    document.getElementById('exp-t').onchange = e => { Object.assign(x, { tabla: e.target.value, pag: 0, orden: null, busca: '' }); this.explorador(); };
    const b = document.getElementById('exp-b'); b.onchange = () => { x.busca = b.value.trim(); x.pag = 0; this.explorador(); };
    document.getElementById('ant').onclick = () => { x.pag--; this.explorador(); };
    document.getElementById('sig').onclick = () => { x.pag++; this.explorador(); };
    document.querySelectorAll('#exp th[data-col]').forEach(th => th.onclick = () => { const c = th.dataset.col; x.dir = x.orden === c && x.dir === 'ASC' ? 'DESC' : 'ASC'; x.orden = c; x.pag = 0; this.explorador(); });
  },
  correr() {
    const sql = document.getElementById('sql').value.trim().replace(/;\s*$/, ''), msg = document.getElementById('sql-msg'), res = document.getElementById('sql-res');
    if (!/^(select|with|explain|pragma)\b/i.test(sql) || sql.includes(';')) { msg.textContent = 'Solo se permite una consulta de lectura (SELECT).'; return; }
    try {
      const t = performance.now(), out = APP.db.exec(`${sql}`), ms = performance.now() - t;
      if (!out.length) { msg.textContent = 'La consulta no devolvió filas.'; res.innerHTML = ''; Plotly.purge('sql-g'); return; }
      const { columns: cs, values } = out[0], filas = values.slice(0, 500).map(v => Object.fromEntries(cs.map((c, i) => [c, v[i]])));
      msg.textContent = `${n(values.length)} filas en ${n(ms, 1)} ms, dentro de su navegador.`;
      res.innerHTML = tablaHTML(filas, cs, { alto: 300 });
      const cx = cs.find(c => typeof filas[0][c] === 'string') || cs[0], cy = [...cs].reverse().find(c => c !== cx && typeof filas[0][c] === 'number');
      if (cy && filas.length <= 40) plot('sql-g', [{ x: filas.map(f => String(f[cx])), y: filas.map(f => f[cy]), type: 'bar', marker: { color: C.navy }, hovertemplate: `%{x}<br>${cy}: %{y:,.1f}<extra></extra>` }], { margin: { b: 86 }, xaxis: { tickangle: -35 }, yaxis: { title: cy } });
      else Plotly.purge('sql-g');
    } catch (e) { msg.textContent = `Revise la consulta: ${e.message}`; }
  },
  crecimiento() {
    const pers = APP.periodos, datos = {};
    TABLAS_MES.forEach(t => { datos[t] = Object.fromEntries(q(`SELECT periodo p, COUNT(*) c FROM ${t} GROUP BY 1`).map(x => [x.p, x.c])); });
    const acum = i => TABLAS_MES.map(t => pers.slice(0, i + 1).reduce((a, p) => a + (datos[t][p] || 0), 0));
    const rango = document.getElementById('mes-rango'), et = document.getElementById('mes-et'), bit = document.getElementById('bit'); rango.max = pers.length - 1; rango.value = pers.indexOf(S.mes);
    const maxX = Math.max(...acum(pers.length - 1)) * 1.14;
    const pintar = () => {
      const i = +rango.value, y = acum(i), p = pers[i]; et.textContent = mesC(p);
      plot('g-crec', [{ type: 'bar', orientation: 'h', y: TABLAS_MES, x: y, text: y.map(v => n(v)), textposition: 'outside', cliponaxis: false, marker: { color: C.navy }, hovertemplate: '%{y}: %{x:,} filas<extra></extra>' }], { margin: { l: 90, r: 50 }, xaxis: { range: [0, maxX], title: `Filas acumuladas hasta ${mesL(p)}`, gridcolor: '#E9E1D3' }, yaxis: { autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
      bit.innerHTML = tablaHTML(q('SELECT paso, resultado, accion, responsable FROM bitacora WHERE periodo=? ORDER BY bitacora_id', [p]), null, { alto: 270, envolver: ['accion'] });
    };
    rango.oninput = pintar; pintar();
    let t = null; const play = document.getElementById('play');
    play.onclick = () => { if (t) { clearInterval(t); t = null; play.textContent = 'Reproducir'; return; } if (+rango.value >= pers.length - 1) rango.value = 0; play.textContent = 'Pausar'; t = cada(520, () => { if (+rango.value >= pers.length - 1) { clearInterval(t); t = null; play.textContent = 'Reproducir'; return; } rango.value = +rango.value + 1; pintar(); }); };
    const a = document.getElementById('d-a'), b = document.getElementById('d-b'), ops = pers.map(p => `<option value="${p}">${mesL(p)}</option>`).join(''); a.innerHTML = ops; b.innerHTML = ops; b.value = S.mes; a.value = mesMenos(S.mes, 1) >= pers[0] ? mesMenos(S.mes, 1) : pers[0];
    const dif = () => {
      const ser = mensual(), f = (p, k) => enMes(ser, p)?.[k];
      const filas = [...TABLAS_MES.map(t => ({ concepto: `Filas en ${t}`, desde: datos[t][a.value] || 0, hasta: datos[t][b.value] || 0 })), ...[['Ingresos', 'ingresos'], ['Utilidad bruta', 'bruto'], ['Gastos de personal', 'personal'], ['Utilidad operativa', 'utilidad']].map(([c, k]) => ({ concepto: `${c} (COP)`, desde: f(a.value, k), hasta: f(b.value, k) }))];
      filas.forEach(x => { x.cambio = x.hasta - x.desde; });
      document.getElementById('dif').innerHTML = tablaHTML(filas, null, { alto: 300 });
    };
    a.onchange = dif; b.onchange = dif; dif();
  },
};
