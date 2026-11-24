/* Arranque: carga la base real en el navegador, arma filtros y pestañas. */
const ORDEN = ['resumen', 'recorrido', 'bd', 'proceso', 'patrones', 'pronostico', 'inventario', 'reportes', 'rutina', 'como', 'donde'];
const opciones = (el, items, val) => { el.innerHTML = items.map(([v, t]) => `<option value="${esc(v)}"${v === val ? ' selected' : ''}>${esc(t)}</option>`).join(''); };

function sincronizarFiltros() {
  opciones(document.getElementById('f-cid'), [['TODOS', 'Toda la red'], ...CONC.map(c => [c, APP.nombres[c]])], S.cid);
  opciones(document.getElementById('f-sede'), [['', 'Todas'], ...APP.sedes.filter(x => S.cid === 'TODOS' || x.concesionario_id === S.cid).map(x => [x.sede_id, x.nombre])], S.sede);
  opciones(document.getElementById('f-mes'), [...APP.periodos].reverse().map(p => [p, mesL(p)]), S.mes);
  opciones(document.getElementById('f-canal'), [['', 'Todos'], ...CANALES.map(c => [c, c])], S.canal);
  opciones(document.getElementById('f-linea'), [['', 'Todas'], ...LINEAS.map(c => [c, c])], S.linea);
}

function dibujar() {
  limpiarTemporizadores();
  const el = document.getElementById('contenido');
  // El mapa descarga su geografía en segundo plano: purgarlo a mitad de camino produce un error.
  el.querySelectorAll('.js-plotly-plot').forEach(g => { if (!g.data?.some(t => t.type === 'scattergeo')) Plotly.purge(g); });
  el.innerHTML = '';
  document.querySelectorAll('#pestanas button').forEach(b => { const a = b.dataset.tab === APP.tab; b.classList.toggle('activo', a); b.setAttribute('aria-current', a ? 'page' : 'false'); });
  try { TABS[APP.tab].render(el); }
  catch (e) { console.error(e); el.innerHTML = `<p class="aviso">No se pudo dibujar esta sección: ${esc(e.message)}</p>`; }
}

async function iniciar() {
  try {
    if (location.protocol === 'file:') throw new Error('Abra el tablero con un servidor local: python -m http.server --directory docs 8000');
    const SQL = await initSqlJs({ locateFile: f => `https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/${f}` });
    const [db, meta, pron, rep] = await Promise.all([
      fetch('data/cierre.db', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error('No se encontró cierre.db'); return r.arrayBuffer(); }),
      ...['meta', 'pronostico', 'reportes'].map(f => fetch(`data/${f}.json`, { cache: 'no-cache' }).then(r => r.json())),
    ]);
    APP.db = new SQL.Database(new Uint8Array(db)); APP.meta = meta; APP.pron = pron; APP.rep = rep;
    APP.sedes = q('SELECT sede_id, concesionario_id, nombre FROM sedes ORDER BY concesionario_id, sede_id');
    q('SELECT concesionario_id c, nombre n FROM concesionarios').forEach(x => { APP.nombres[x.c] = x.n; });
    APP.periodos = q('SELECT DISTINCT periodo p FROM saldos ORDER BY 1').map(x => x.p);
    S.mes = meta.mes;
    const nav = document.getElementById('pestanas');
    nav.innerHTML = ORDEN.map(k => `<button type="button" data-tab="${k}">${esc(TABS[k].titulo)}</button>`).join('');
    nav.addEventListener('click', e => { const b = e.target.closest('button'); if (b) { APP.tab = b.dataset.tab; history.replaceState(null, '', `#${APP.tab}`); dibujar(); scrollTo({ top: 0 }); } });
    const inicial = location.hash.slice(1); if (ORDEN.includes(inicial)) APP.tab = inicial;
    [['f-cid', 'cid'], ['f-sede', 'sede'], ['f-mes', 'mes'], ['f-canal', 'canal'], ['f-linea', 'linea']].forEach(([id, k]) => document.getElementById(id).addEventListener('change', e => fijarFiltro(k, e.target.value)));
    document.getElementById('ir-rutina').addEventListener('click', () => { APP.tab = 'rutina'; history.replaceState(null, '', '#rutina'); dibujar(); setTimeout(() => document.getElementById('rv')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 150); });
    document.getElementById('f-limpiar').addEventListener('click', () => { Object.assign(S, { cid: 'AND', sede: '', mes: meta.mes, canal: '', linea: '' }); sincronizarFiltros(); dibujar(); });
    sincronizarFiltros(); dibujar();
    window.TABLERO_LISTO = true;
  } catch (e) {
    console.error(e);
    document.getElementById('contenido').innerHTML = `<p class="aviso">No se pudo abrir el tablero. ${esc(e.message)}</p>`;
  }
}
iniciar();
