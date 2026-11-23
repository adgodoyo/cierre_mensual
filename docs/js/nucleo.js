/* Núcleo del tablero: estado de filtros, consultas a SQLite y ayudas de gráficos. */
const C = { navy: '#1F4E79', teal: '#1D6B67', terra: '#B4532A', plum: '#6B3A63', crema: '#F3EDE2', papel: '#FBF8F2', tinta: '#2A2A2A', suave: '#5F584C', borde: '#DDD3C2', ambar: '#B98A22' };
const SERIES = [C.navy, C.terra, C.teal, C.plum];
const TRAZOS = ['solid', 'dash', 'dot', 'dashdot'];
const SIMBOLOS = ['circle', 'square', 'diamond', 'triangle-up'];
const CONC = ['AND', 'VAL', 'CAR', 'LLA'];
const CANALES = ['Retail', 'Flotas', 'Plan de ahorro', 'Eléctricos'];
const LINEAS = ['Livianos', 'Usados', 'Eléctricos', 'Pesados'];
const DEPTOS = { LIV: 'Livianos', USA: 'Usados', ELE: 'Eléctricos', PES: 'Pesados', FYI: 'F&I', SER: 'Servicio', REP: 'Repuestos', ACC: 'Accesorios', ADM: 'Administrativo' };
const DEPTO_DE_LINEA = { Livianos: 'LIV', Usados: 'USA', 'Eléctricos': 'ELE', Pesados: 'PES' };
const SEQ = [[0, '#EFE7DA'], [.5, '#7C9DB8'], [1, C.navy]];
const DIV = [[0, C.terra], [.5, '#EFEAE1'], [1, C.teal]];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const MESES_L = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

Plotly.register({ moduleType: 'locale', name: 'es', dictionary: { 'Download plot as a png': 'Descargar como PNG', 'Zoom in': 'Acercar', 'Zoom out': 'Alejar', 'Autoscale': 'Ajustar', 'Reset axes': 'Restablecer ejes', 'Pan': 'Mover', 'Zoom': 'Zoom' },
  format: { days: ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'], shortDays: ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'], months: MESES_L.map(m => m[0].toUpperCase() + m.slice(1)), shortMonths: MESES, date: '%d/%m/%Y', decimal: ',', thousands: '.' } });

const S = { cid: 'AND', sede: '', mes: '2026-10', canal: '', linea: '' };
const APP = { db: null, meta: null, pron: null, rep: null, tab: 'resumen', sedes: [], periodos: [], nombres: {}, cache: new Map(), temporizadores: [] };
const TABS = {};

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const n = (v, d = 0) => v == null || !isFinite(v) ? 's. d.' : Number(v).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
const M = (v, d = 1) => v == null ? 's. d.' : `${v < 0 ? '-' : ''}$${n(Math.abs(v) / 1e6, d)} M`;
const MM = (v, d = 1) => v == null ? 's. d.' : `${v < 0 ? '-' : ''}$${n(Math.abs(v) / 1e9, d)} mil M`;
const P = (v, d = 1) => v == null || !isFinite(v) ? 's. d.' : `${n(v * 100, d)} %`;
const mesC = p => `${MESES[+p.slice(5) - 1]} ${p.slice(2, 4)}`;
const mesL = p => `${MESES_L[+p.slice(5) - 1]} de ${p.slice(0, 4)}`;
const mesMenos = (p, k) => { let [a, m] = p.split('-').map(Number); m -= k; while (m < 1) { m += 12; a--; } while (m > 12) { m -= 12; a++; } return `${a}-${String(m).padStart(2, '0')}`; };
const lista = a => a.map(x => `'${String(x).replace(/'/g, "''")}'`).join(',');

function q(sql, params = []) {
  const st = APP.db.prepare(sql); const filas = [];
  try { st.bind(params); while (st.step()) filas.push(st.getAsObject()); } finally { st.free(); }
  return filas;
}
function qc(clave, fn) { if (!APP.cache.has(clave)) APP.cache.set(clave, fn()); return APP.cache.get(clave); }
const sedesDe = (cid = S.cid, sede = S.sede) => APP.sedes.filter(x => (cid === 'TODOS' || x.concesionario_id === cid) && (!sede || x.sede_id === sede)).map(x => x.sede_id);
const inSedes = (alias = '', cid, sede) => `${alias ? alias + '.' : ''}sede_id IN (${lista(sedesDe(cid, sede))})`;
function condVentas(a = 'v', usarMes = false) { let c = inSedes(a); if (S.canal) c += ` AND ${a}.canal=${lista([S.canal])}`; if (S.linea) c += ` AND ${a}.linea=${lista([S.linea])}`; if (usarMes) c += ` AND ${a}.periodo='${S.mes}'`; return c; }
function condInv(a = 'i', usarMes = true) { let c = inSedes(a); if (S.linea) c += ` AND ${a}.linea=${lista([S.linea])}`; if (usarMes) c += ` AND ${a}.periodo='${S.mes}'`; return c; }

function mensual(cid = S.cid, sede = S.sede, linea = S.linea) {
  return qc(`m|${cid}|${sede}|${linea}`, () => {
    const d = linea ? ` AND departamento='${DEPTO_DE_LINEA[linea]}'` : '';
    const filas = q(`SELECT periodo, substr(cuenta_origen,1,4) c, SUM(saldo) v FROM saldos WHERE ${inSedes('', cid, sede)} AND cuenta_origen LIKE '%-%'${d} GROUP BY 1,2 ORDER BY 1`);
    const mapa = {};
    filas.forEach(f => { (mapa[f.periodo] ||= { periodo: f.periodo })[f.c] = f.v; });
    return Object.values(mapa).map(x => {
      const g = k => x[k] || 0; const bruto = g('4135') - g('6135'); const semifijo = g('5135') + g('5195');
      return { periodo: x.periodo, ingresos: g('4135'), costo: g('6135'), bruto, variable: g('5205'), personal: g('5105'), semifijo, fijo: g('5120'), financiero: g('5305'), utilidad: bruto - g('5205') - g('5105') - semifijo - g('5120') - g('5305'), margen: g('4135') ? bruto / g('4135') : null };
    });
  });
}
const enMes = (serie, p) => serie.find(x => x.periodo === p);

function enlace(ruta, texto) {
  const r = APP.meta?.repo;
  if (!r) return `<code>${esc(texto || ruta)}</code>`;
  const tipo = /\.[a-z0-9]+$/i.test(ruta) ? 'blob' : 'tree';
  return `<a href="https://github.com/${r}/${tipo}/${APP.meta.rama}/${encodeURI(ruta)}" target="_blank" rel="noopener"><code>${esc(texto || ruta)}</code></a>`;
}
function origen(src = {}) {
  const tabla = src.tabla ? `Tabla: <code>${esc(src.tabla)}</code> · ` : '';
  const ruta = src.ruta || (src.tabla ? 'docs/data/cierre.db' : 'docs/data/pronostico.json');
  return `<details class="origen"><summary>¿De dónde sale?</summary><div>${tabla}Script: ${enlace(src.script || 'src/ingesta.py')} · Archivo: ${enlace(ruta)}${src.filtros ? ` · Obedece: ${esc(src.filtros)}` : ''} · Datos simulados</div></details>`;
}
function tarjeta(padre, o) {
  const s = document.createElement('section'); s.className = `tarjeta w${o.w || 6}`;
  s.innerHTML = `<h3>${esc(o.t)}</h3>${o.s ? `<p class="sub">${esc(o.s)}</p>` : ''}${o.html ?? `<div class="graf" id="${o.id}" style="min-height:${o.h || 330}px" role="img" aria-label="${esc(o.t)}"></div>`}${origen(o.src)}`;
  padre.appendChild(s); return s;
}
function encabezado(el, t, s) { el.insertAdjacentHTML('beforeend', `<div class="intro"><h2>${esc(t)}</h2><p>${esc(s)}</p></div>`); const r = document.createElement('div'); r.className = 'rejilla'; el.appendChild(r); return r; }

const BASE = () => ({
  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', separators: ',.', font: { family: 'Inter, system-ui, sans-serif', size: 12, color: C.tinta },
  margin: { l: 56, r: 18, t: 12, b: 44 }, hoverlabel: { bgcolor: C.papel, bordercolor: C.borde, font: { color: C.tinta, size: 13 } }, hovermode: 'closest',
  legend: { orientation: 'h', y: 1.1, x: 0, font: { size: 11 } },
  xaxis: { gridcolor: 'rgba(0,0,0,0)', linecolor: C.borde, tickfont: { color: C.suave }, automargin: true },
  yaxis: { gridcolor: '#E9E1D3', zerolinecolor: '#BDB29F', linecolor: 'rgba(0,0,0,0)', tickfont: { color: C.suave }, automargin: true },
});
const CONFIG = { responsive: true, displaylogo: false, locale: 'es', modeBarButtonsToRemove: ['lasso2d', 'select2d'], toImageButtonOptions: { format: 'png', scale: 2, filename: 'cierre_andino_datos_simulados' } };
function fusion(a, b) { const r = { ...a }; for (const k in b) r[k] = b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object' ? fusion(a[k], b[k]) : b[k]; return r; }
function plot(id, trazas, disp = {}, conf = {}) { const el = document.getElementById(id); if (!el) return null; Plotly.react(el, trazas, fusion(BASE(), disp), { ...CONFIG, ...conf }); return el; }
function tablaHTML(filas, cols, opts = {}) {
  if (!filas.length) return '<p class="nota">No hay filas para estos filtros.</p>';
  cols = cols || Object.keys(filas[0]);
  const num = c => filas.some(f => typeof f[c] === 'number');
  const val = (f, c) => opts.fmt?.[c] ? opts.fmt[c](f[c], f) : typeof f[c] === 'number' ? n(f[c], Number.isInteger(f[c]) ? 0 : 3) : esc(f[c]);
  return `<div class="tabla-caja" style="max-height:${opts.alto || 430}px"><table><thead><tr>${cols.map(c => `<th class="${num(c) ? 'num' : ''}">${esc(opts.nombres?.[c] || c)}</th>`).join('')}</tr></thead><tbody>${filas.map(f => `<tr class="${opts.marca?.(f) ? 'marca' : ''}">${cols.map(c => `<td class="${num(c) ? 'num' : ''} ${opts.envolver?.includes(c) ? 'envuelve' : ''}">${val(f, c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
const etiqueta = v => `<span class="etq ${esc(v)}">${esc(v)}</span>`;
function cada(ms, fn) { const t = setInterval(fn, ms); APP.temporizadores.push(t); return t; }
function limpiarTemporizadores() { APP.temporizadores.forEach(clearInterval); APP.temporizadores = []; }
function fijarFiltro(k, v) { S[k] = v; if (k === 'cid') S.sede = ''; sincronizarFiltros(); dibujar(); }
