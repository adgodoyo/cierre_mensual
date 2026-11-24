/* Pestañas: Procesamiento, Patrones, Pronóstico e Inventario. */
const condAlerta = () => S.cid === 'TODOS' ? '1=1' : `concesionario_id='${S.cid}'`;
const colorCanal = c => SERIES[CANALES.indexOf(c)];
const colorLinea = l => SERIES[LINEAS.indexOf(l)];
const SEV = { Alta: C.terra, Media: C.ambar, Baja: C.teal };

TABS.proceso = {
  titulo: 'Procesamiento',
  render(el) {
    const r = encabezado(el, 'Del archivo desordenado al dato confiable', 'El agente reconoce cada formato por su contenido, homologa las cuentas y explica en una frase cada hallazgo.');
    const sede = S.sede || (S.cid === 'AND' || S.cid === 'TODOS' ? 'SUR' : sedesDe()[0]), cidV = S.cid === 'TODOS' ? 'AND' : S.cid, v = APP.meta.vistas[S.mes][cidV];
    const ancho = Math.max(...v.filas.map(f => f.celdas.length)), letras = Array.from({ length: ancho }, (_, i) => String.fromCharCode(65 + i));
    const crudas = v.filas.map(f => ({ fila: f.n, _m: f.marca, ...Object.fromEntries(letras.map((l, i) => [l, f.celdas[i] ?? ''])) }));
    tarjeta(r, { w: 6, t: 'Antes: hoja Balance del reporte mensual', s: `${v.archivo.split('/').pop()}: títulos, secciones y subtotales mezclados con las cuentas.`, html: tablaHTML(crudas, ['fila', ...letras], { marca: f => f._m, alto: 420 }), src: { script: '04_pruebas/generar_datos.py', ruta: v.archivo } });
    const limpias = q(`SELECT cuenta_origen, cuenta_codigo, departamento, saldo, fuente FROM saldos WHERE periodo=? AND sede_id=? ORDER BY cuenta_codigo='2205' DESC, saldo_id LIMIT 14`, [S.mes, sede]);
    tarjeta(r, { w: 6, t: 'Después: tabla ordenada', s: 'Una fila por registro, con su celda de origen.', html: tablaHTML(limpias, null, { fmt: { saldo: x => M(x) }, marca: f => f.cuenta_codigo === '2205', alto: 420 }), src: { tabla: 'saldos', script: 'src/ingesta.py' } });
    tarjeta(r, { w: 12, t: 'Mapa del reporte mensual: qué trae cada hoja', s: 'Un solo libro por concesionario y mes. Cada hoja tiene su propio reto, y el agente sabe cómo leerla.', html: tablaHTML(v.hojas, ['hoja', 'contenido', 'reto', 'tabla', 'filas'], { nombres: { hoja: 'Hoja', contenido: 'Qué trae', reto: 'Qué resuelve el agente', tabla: 'Tabla destino', filas: 'Filas' }, envolver: ['contenido', 'reto'], alto: 460 }), src: { tabla: 'cargas', script: 'src/ingesta.py', ruta: v.archivo } });
    tarjeta(r, { w: 6, id: 'g-cob', h: 300, t: 'Cobertura del mapeo', s: 'Cuentas distintas con homologación.', src: { tabla: 'saldos, cuentas', script: 'src/procesamiento.py', ruta: '00_manuales/mapeo_puc_formato.xlsx', filtros: 'concesionario, sede, mes' } });
    tarjeta(r, { w: 6, id: 'g22', h: 300, t: 'Cuadre contable por sede', s: 'Diferencia entre Activo y Pasivo + Patrimonio.', src: { tabla: 'saldos', script: 'src/procesamiento.py', filtros: 'concesionario, sede, mes' } });
    const al = q(`SELECT severidad, sede_id, hallazgo, explicacion, impacto_cop, origen FROM alertas WHERE periodo=? AND ${condAlerta()} ORDER BY CASE severidad WHEN 'Alta' THEN 0 WHEN 'Media' THEN 1 ELSE 2 END, impacto_cop DESC`, [S.mes]);
    tarjeta(r, { w: 12, t: `Alertas de ${mesL(S.mes)} (${al.length})`, s: 'Cada alerta dice qué pasó, por qué importa y en qué celda verificarlo.', html: tablaHTML(al, null, { nombres: { severidad: 'Severidad', sede_id: 'Sede', hallazgo: 'Hallazgo', explicacion: 'Explicación', impacto_cop: 'Impacto', origen: 'Origen' }, fmt: { severidad: etiqueta, impacto_cop: x => x == null ? '' : M(x) }, envolver: ['hallazgo', 'explicacion'], alto: 500 }), src: { tabla: 'alertas', script: 'src/procesamiento.py', ruta: `03_salidas/${APP.meta.mes}/alertas_${APP.meta.mes}.xlsx`, filtros: 'concesionario, mes' } });
    tarjeta(r, { w: 12, id: 'g20', h: 310, t: 'Alertas por severidad y mes (número de alertas)', s: 'La historia de los controles en los 24 meses.', src: { tabla: 'alertas', script: 'src/procesamiento.py', filtros: 'concesionario' } });
    const ctas = q(`SELECT cuenta_origen c, MAX(cuenta_codigo IS NOT NULL) m FROM saldos WHERE periodo=? AND ${inSedes()} GROUP BY substr(cuenta_origen,1,4)`, [S.mes]), ok = ctas.filter(x => x.m).length, no = ctas.length - ok;
    plot('g-cob', [{ type: 'pie', hole: .66, labels: ['Homologadas', 'Por confirmar'], values: [ok, no], sort: false, marker: { colors: [C.teal, C.terra], line: { color: C.papel, width: 2 } }, textinfo: 'value', hovertemplate: '%{label}: %{value} cuentas<extra></extra>' }], { margin: { l: 4, r: 4, t: 4, b: 28 }, legend: { y: -.08 }, annotations: [{ text: `<b>${P(ok / ctas.length, 1)}</b>`, showarrow: false, font: { size: 21, family: 'Fraunces, serif', color: C.navy } }] });
    const sedes = sedesDe(), cuadre = sedes.map(s => { const f = q(`SELECT SUM(CASE WHEN substr(cuenta_origen,1,1)='1' THEN saldo ELSE 0 END) a, SUM(CASE WHEN substr(cuenta_origen,1,1) IN ('2','3') THEN saldo ELSE 0 END) p FROM saldos WHERE periodo=? AND sede_id=? AND cuenta_origen NOT LIKE '%-%'`, [S.mes, s])[0]; return { s: APP.sedes.find(x => x.sede_id === s).nombre, d: (f.p - f.a) / 1e6 }; });
    plot('g22', [{ type: 'bar', orientation: 'h', y: cuadre.map(x => `${x.d === 0 ? '✓' : '✕'} ${x.s}`), x: cuadre.map(x => x.d), text: cuadre.map(x => x.d === 0 ? 'Cuadra' : `$${n(x.d, 1)} M`), textposition: 'auto', marker: { color: cuadre.map(x => x.d === 0 ? C.teal : C.terra) }, hovertemplate: '%{y}: diferencia $%{x:,.1f} M<extra></extra>' }], { margin: { l: 104, r: 20, b: 42 }, xaxis: { title: 'Diferencia (COP millones)', zeroline: true, range: [0, Math.max(5, ...cuadre.map(x => x.d)) * 1.15] }, yaxis: { autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
    const hist = q(`SELECT periodo, severidad, COUNT(*) c FROM alertas WHERE ${condAlerta()} GROUP BY 1,2`);
    plot('g20', ['Alta', 'Media', 'Baja'].map(s => ({ type: 'bar', name: s, x: APP.periodos.map(mesC), y: APP.periodos.map(p => hist.find(h => h.periodo === p && h.severidad === s)?.c || 0), marker: { color: SEV[s], line: { color: C.papel, width: 1 } }, hovertemplate: `${s}<br>%{x}: %{y}<extra></extra>` })), { barmode: 'stack', xaxis: { type: 'category', tickangle: -45 }, yaxis: { title: 'Alertas', dtick: 2 } });
  },
};

TABS.patrones = {
  titulo: 'Patrones',
  render(el) {
    const r = encabezado(el, 'Lo que los datos cuentan', 'Preguntas de negocio convertidas en gráficos. Pase el cursor para ver el detalle de cada punto.');
    const fv = { tabla: 'ventas', script: 'src/ingesta.py', filtros: 'concesionario, sede, canal, línea' };
    [['g2', 6, 'Puente de utilidad operativa (COP millones)', 'Qué explica el cambio frente al mes anterior.', { tabla: 'saldos', script: 'src/procesamiento.py', filtros: 'concesionario, sede, mes, línea' }],
     ['g3', 6, 'Ingresos por departamento (COP millones)', 'Clic en un departamento para ver sus sedes.', { tabla: 'saldos', script: 'src/ingesta.py', filtros: 'concesionario, sede, mes' }],
     ['g4', 7, 'De las ventas a la utilidad (COP millones)', 'Hacia dónde se va cada peso vendido.', { tabla: 'saldos', script: 'src/procesamiento.py', filtros: 'concesionario, sede, mes, línea' }],
     ['g5', 5, 'Margen bruto por canal y mes (%)', 'Más oscuro significa mayor margen.', fv],
     ['g9', 12, 'Ventas diarias del año (unidades)', 'Cada cuadro es un día. Los cierres de mes se ven más oscuros.', fv],
     ['g10', 6, 'Pareto de modelos: margen acumulado (COP millones)', 'Pocos modelos concentran la mayor parte del margen. Últimos 12 meses.', fv],
     ['g11', 6, 'Precio y margen por modelo', 'Tamaño = unidades. Color y forma = canal. Últimos 12 meses.', fv],
     ['g12', 4, 'Descuentos por canal (% del precio)', 'Caja = la mitad central de las ventas.', fv],
     ['g13', 4, 'Mezcla de canales en el tiempo (% de ingresos)', 'Flotas llega por oleadas; Eléctricos crece.', fv],
     ['g14', 4, 'Estacionalidad de ingresos (COP miles de millones)', 'Dos años superpuestos. Diciembre sobresale.', { tabla: 'saldos', script: 'src/pronostico.py', filtros: 'concesionario, sede, línea' }],
     ['g6', 4, 'Concesionarios en 5 indicadores', 'Índice 100 = el mejor de la red en cada indicador.', { tabla: 'saldos, inventario, fi, personal, ventas', script: 'src/pronostico.py', filtros: 'mes' }],
     ['g7', 4, 'Ranking de ingresos, mes a mes (COP miles de millones)', 'Presione reproducir para ver los 24 meses.', { tabla: 'saldos', script: 'src/pronostico.py', filtros: 'línea' }],
     ['g21', 4, 'Correlación entre indicadores', 'Verde: se mueven juntos. Terracota: en sentido opuesto.', { tabla: 'saldos, inventario, fi, ventas', script: 'src/pronostico.py', filtros: 'concesionario, sede' }],
     ['g19', 12, 'Gastos con anomalías marcadas (COP millones)', 'Cada punto es un pago. Los marcados tienen una razón al pasar el cursor.', { tabla: 'gastos, alertas', script: 'src/procesamiento.py', ruta: `03_salidas/${APP.meta.mes}/anomalias_gastos_${APP.meta.mes}.xlsx`, filtros: 'concesionario, sede' }],
     ['g28', 7, 'Penetración de financiación y seguros (% de unidades)', 'Fila superior: créditos. Fila inferior: pólizas.', { tabla: 'fi', script: 'src/ingesta.py', filtros: 'mes' }],
     ['g29', 5, 'Unidades por vendedor y sede', 'La línea marca la meta de 6 unidades.', { tabla: 'ventas, personal', script: 'src/ingesta.py', filtros: 'concesionario, sede, mes' }],
    ].forEach(([id, w, t, s, src]) => tarjeta(r, { id, w, t, s, src, h: id === 'g9' ? 230 : id === 'g28' ? 350 : 340 }));
    this.puente(); this.treemap(); this.sankey(); this.margenCanal(); this.calendario(); this.pareto(); this.burbujas(); this.descuentos(); this.mezcla(); this.estacional(); this.radar(); this.carrera(); this.correlacion(); this.anomalias(); this.gauges(); this.productividad();
  },
  puente() {
    const ser = mensual(), b = enMes(ser, S.mes), a = enMes(ser, mesMenos(S.mes, 1));
    if (!a) { document.getElementById('g2').innerHTML = '<p class="nota">No hay mes anterior para comparar.</p>'; return; }
    const ventas = (b.ingresos - a.ingresos) * a.margen, margen = (b.margen - a.margen) * b.ingresos;
    const pasos = [['Ventas', ventas], ['Margen', margen], ['Variables', a.variable - b.variable], ['Personal', a.personal - b.personal], ['Semifijos', a.semifijo - b.semifijo], ['Fijos', a.fijo - b.fijo], ['Financieros', a.financiero - b.financiero]];
    const x = [mesC(a.periodo), ...pasos.map(p => p[0]), mesC(b.periodo)], y = [a.utilidad, ...pasos.map(p => p[1]), b.utilidad].map(v => v / 1e6);
    plot('g2', [{ type: 'waterfall', x, y, measure: ['absolute', ...pasos.map(() => 'relative'), 'total'], text: y.map(v => n(v, 0)), textposition: 'outside', cliponaxis: false, connector: { line: { color: '#BDB29F', width: 1 } }, increasing: { marker: { color: C.teal } }, decreasing: { marker: { color: C.terra } }, totals: { marker: { color: C.navy } }, hovertemplate: '%{x}: $%{y:,.1f} M<extra></extra>' }], { showlegend: false, yaxis: { title: 'COP millones' } });
  },
  treemap() {
    const f = q(`SELECT departamento d, sede_id s, SUM(saldo) v FROM saldos WHERE periodo=? AND ${inSedes()} AND cuenta_codigo='4135' GROUP BY 1,2 HAVING v>0`, [S.mes]);
    const ds = [...new Set(f.map(x => x.d))], nom = s => APP.sedes.find(x => x.sede_id === s).nombre, tot = d => f.filter(x => x.d === d).reduce((a, x) => a + x.v, 0);
    const paleta = [C.navy, C.terra, C.teal, C.plum, '#4F7596', '#C97F5F', '#4F8F8A', '#8F6688', '#7C8B99'];
    plot('g3', [{ type: 'treemap', ids: [...ds, ...f.map(x => `${x.d}/${x.s}`)], labels: [...ds.map(d => DEPTOS[d]), ...f.map(x => nom(x.s))], parents: [...ds.map(() => ''), ...f.map(x => x.d)], values: [...ds.map(tot), ...f.map(x => x.v)].map(v => v / 1e6), branchvalues: 'total', maxdepth: 2, marker: { colors: [...ds.map((_, i) => paleta[i % paleta.length]), ...f.map(x => paleta[ds.indexOf(x.d) % paleta.length])], line: { color: C.papel, width: 2 } }, textinfo: 'label+value+percent root', texttemplate: '%{label}<br>$%{value:,.0f} M', hovertemplate: '%{label}: $%{value:,.1f} M<extra></extra>' }], { margin: { l: 2, r: 2, t: 4, b: 2 } });
  },
  sankey() {
    const b = enMes(mensual(), S.mes), o = v => Math.max(v, 0) / 1e6;
    const nodos = ['Ventas netas', 'Costo de ventas', 'Utilidad bruta', 'Variables', 'Personal', 'Semifijos', 'Fijos', 'Financieros', 'Utilidad operativa'];
    plot('g4', [{ type: 'sankey', arrangement: 'snap', valueformat: ',.0f', valuesuffix: ' M', node: { label: nodos, pad: 14, thickness: 15, color: [C.navy, C.terra, C.teal, '#C97F5F', C.plum, '#8F6688', '#7C8B99', '#A9673F', C.teal], line: { color: C.papel, width: 1 } }, link: { source: [0, 0, 2, 2, 2, 2, 2, 2], target: [1, 2, 3, 4, 5, 6, 7, 8], value: [b.costo, b.bruto, b.variable, b.personal, b.semifijo, b.fijo, b.financiero, b.utilidad].map(o), color: 'rgba(31,78,121,.16)' } }], { margin: { l: 6, r: 6, t: 8, b: 8 } });
  },
  margenCanal() {
    const f = q(`SELECT v.periodo p, v.canal c, 100.0*SUM(v.margen)/SUM(v.precio-v.descuento) m FROM ventas v WHERE ${condVentas()} GROUP BY 1,2`);
    const cs = CANALES.filter(c => f.some(x => x.c === c));
    plot('g5', [{ type: 'heatmap', x: APP.periodos.map(mesC), y: cs, z: cs.map(c => APP.periodos.map(p => f.find(x => x.p === p && x.c === c)?.m ?? null)), colorscale: SEQ, xgap: 2, ygap: 2, colorbar: { thickness: 9, title: '%' }, hovertemplate: '%{y}, %{x}: %{z:.1f} %<extra></extra>', hoverongaps: false }], { margin: { l: 96 }, xaxis: { type: 'category', tickangle: -60, tickfont: { size: 9 } }, yaxis: { gridcolor: 'rgba(0,0,0,0)' } });
  },
  calendario() {
    const anio = S.mes.slice(0, 4), f = Object.fromEntries(q(`SELECT v.fecha d, COUNT(*) c FROM ventas v WHERE ${condVentas()} AND substr(v.fecha,1,4)=? GROUP BY 1`, [anio]).map(x => [x.d, x.c]));
    const ini = new Date(Date.UTC(+anio, 0, 1)), desf = (ini.getUTCDay() + 6) % 7, dias = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'], z = dias.map(() => Array(54).fill(null)), t = dias.map(() => Array(54).fill(''));
    for (let d = new Date(ini); d.getUTCFullYear() === +anio; d.setUTCDate(d.getUTCDate() + 1)) { const id = d.toISOString().slice(0, 10), o = Math.floor((d - ini) / 864e5) + desf, w = Math.floor(o / 7), y = o % 7; z[y][w] = id.slice(0, 7) > S.mes ? null : f[id] ?? 0; t[y][w] = `${+id.slice(8)} ${MESES[+id.slice(5, 7) - 1]}`; }
    const marcas = MESES.map((m, i) => ({ v: Math.floor((Math.floor((Date.UTC(+anio, i, 1) - ini) / 864e5) + desf) / 7), m }));
    plot('g9', [{ type: 'heatmap', z, text: t, colorscale: SEQ, xgap: 2, ygap: 2, hoverongaps: false, colorbar: { thickness: 9, title: 'Unid.' }, hovertemplate: '%{text}: %{z} unidades<extra></extra>' }], { margin: { l: 40, t: 6, b: 26 }, xaxis: { tickvals: marcas.map(x => x.v), ticktext: marcas.map(x => x.m), showline: false }, yaxis: { tickvals: [0, 1, 2, 3, 4, 5, 6], ticktext: dias, autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
  },
  doceMeses(a = 'v') { return `${a}.periodo BETWEEN '${mesMenos(S.mes, 11)}' AND '${S.mes}'`; },
  pareto() {
    const f = q(`SELECT v.modelo m, SUM(v.margen) x FROM ventas v WHERE ${condVentas()} AND ${this.doceMeses()} GROUP BY 1 ORDER BY x DESC`); if (!f.length) return;
    const tot = f.reduce((a, x) => a + x.x, 0); let c = 0; const acu = f.map(x => (c += x.x) / tot * 100);
    plot('g10', [{ type: 'bar', x: f.map(x => x.m), y: f.map(x => x.x / 1e6), name: 'Margen', marker: { color: C.navy }, hovertemplate: '%{x}: $%{y:,.0f} M<extra></extra>' }, { x: f.map(x => x.m), y: acu, yaxis: 'y2', name: '% acumulado', mode: 'lines+markers', line: { color: C.terra, width: 2, dash: 'dash' }, marker: { size: 6, symbol: 'square' }, hovertemplate: '%{x}: %{y:.0f} % acumulado<extra></extra>' }], { margin: { b: 90, r: 44 }, xaxis: { tickangle: -40, tickfont: { size: 10 } }, yaxis: { title: 'COP millones' }, yaxis2: { overlaying: 'y', side: 'right', range: [0, 105], ticksuffix: ' %', showgrid: false, tickfont: { color: C.suave } }, shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y2', y0: 80, y1: 80, line: { color: C.suave, dash: 'dot', width: 1 } }] });
  },
  burbujas() {
    const f = q(`SELECT v.modelo m, v.canal c, COUNT(*) u, AVG(v.precio)/1e6 p, 100.0*SUM(v.margen)/SUM(v.precio-v.descuento) g FROM ventas v WHERE ${condVentas()} AND ${this.doceMeses()} GROUP BY 1,2`);
    plot('g11', CANALES.filter(c => f.some(x => x.c === c)).map(c => { const d = f.filter(x => x.c === c); return { x: d.map(x => x.p), y: d.map(x => x.g), text: d.map(x => x.m), customdata: d.map(x => x.u), name: c, mode: 'markers', marker: { size: d.map(x => Math.max(8, Math.sqrt(x.u) * 3.2)), color: colorCanal(c), symbol: SIMBOLOS[CANALES.indexOf(c)], opacity: .82, line: { color: C.papel, width: 1.5 } }, hovertemplate: `%{text} · ${c}<br>Precio medio: $%{x:,.0f} M<br>Margen: %{y:.1f} %<br>%{customdata} unidades<extra></extra>` }; }), { xaxis: { title: 'Precio medio (COP millones)', gridcolor: '#E9E1D3' }, yaxis: { title: 'Margen (%)' } });
  },
  descuentos() {
    const f = q(`SELECT v.canal c, 100.0*v.descuento/v.precio d FROM ventas v WHERE ${condVentas()} AND ${this.doceMeses()}`);
    plot('g12', CANALES.filter(c => f.some(x => x.c === c)).map(c => ({ type: 'box', y: f.filter(x => x.c === c).map(x => x.d), name: c, marker: { color: colorCanal(c), size: 3 }, line: { color: colorCanal(c), width: 1.5 }, boxpoints: 'outliers', hoverinfo: 'y' })), { showlegend: false, yaxis: { title: '% del precio' }, xaxis: { tickfont: { size: 10 } } });
  },
  mezcla() {
    const f = q(`SELECT v.periodo p, v.canal c, SUM(v.precio-v.descuento) x FROM ventas v WHERE ${condVentas()} GROUP BY 1,2`);
    plot('g13', CANALES.map((c, i) => ({ x: APP.periodos.map(mesC), y: APP.periodos.map(p => f.find(y => y.p === p && y.c === c)?.x || 0), name: c, stackgroup: 'uno', groupnorm: 'percent', mode: 'lines', line: { color: SERIES[i], width: .8 }, fillcolor: SERIES[i], hovertemplate: `${c}<br>%{x}: %{y:.1f} %<extra></extra>` })), { xaxis: { type: 'category', tickangle: -60, tickfont: { size: 9 }, nticks: 12 }, yaxis: { ticksuffix: ' %', range: [0, 100] }, legend: { y: 1.2 } });
  },
  estacional() {
    const ser = mensual(), fin = S.mes, a = [], b = [];
    for (let i = 11; i >= 0; i--) a.push(enMes(ser, mesMenos(fin, i))), b.push(enMes(ser, mesMenos(fin, i + 12)));
    const orden = a.map(x => x ? +x.periodo.slice(5) : 0), th = orden.map(m => MESES[m - 1]);
    const traza = (d, nom, i) => ({ type: 'scatterpolar', r: [...d.map(x => x ? x.ingresos / 1e9 : null), d[0] ? d[0].ingresos / 1e9 : null], theta: [...th, th[0]], name: nom, mode: 'lines+markers', line: { color: SERIES[i], width: 2, dash: TRAZOS[i] }, marker: { size: 6, symbol: SIMBOLOS[i] }, hovertemplate: `${nom}<br>%{theta}: $%{r:.1f} mil M<extra></extra>` });
    plot('g14', [traza(b, 'Año anterior', 1), traza(a, 'Últimos 12 meses', 0)], { margin: { l: 34, r: 34, t: 34, b: 24 }, legend: { y: 1.17 }, polar: { bgcolor: 'rgba(0,0,0,0)', radialaxis: { gridcolor: '#E0D7C8', tickfont: { size: 9, color: C.suave }, angle: 90 }, angularaxis: { direction: 'clockwise', rotation: 90, gridcolor: '#E0D7C8' } } });
  },
  radar() {
    const fila = c => { const s = sedesDe(c, ''), l = lista(s), m = enMes(mensual(c, '', ''), S.mes), i = q(`SELECT 1.0*SUM(CASE WHEN rango='>60' THEN costo ELSE 0 END)/SUM(costo) v FROM inventario WHERE periodo=? AND sede_id IN (${l})`, [S.mes])[0].v, fi = q(`SELECT 1.0*SUM(creditos)/SUM(unidades) p, SUM(unidades) u FROM fi WHERE periodo=? AND sede_id IN (${l})`, [S.mes])[0], vend = q(`SELECT SUM(personas) p FROM personal WHERE periodo=? AND rol='Vendedores' AND sede_id IN (${l})`, [S.mes])[0].p; return [m.margen, 1 - i, fi.p, m.utilidad / m.ingresos, fi.u / vend]; };
    const dat = CONC.map(fila), mejores = dat[0].map((_, j) => Math.max(...dat.map(d => d[j]))), ejes = ['Margen', 'Inventario sano', 'Penetración F&I', 'Rentabilidad', 'Productividad'];
    plot('g6', CONC.map((c, i) => ({ type: 'scatterpolar', r: [...dat[i].map((v, j) => v / mejores[j] * 100), dat[i][0] / mejores[0] * 100], theta: [...ejes, ejes[0]], name: APP.nombres[c], mode: 'lines+markers', line: { color: SERIES[i], dash: TRAZOS[i], width: 2 }, marker: { symbol: SIMBOLOS[i], size: 6 }, hovertemplate: `${APP.nombres[c]}<br>%{theta}: %{r:.0f}<extra></extra>` })), { margin: { l: 44, r: 44, t: 44, b: 22 }, legend: { y: 1.26, font: { size: 10 } }, polar: { bgcolor: 'rgba(0,0,0,0)', radialaxis: { range: [Math.max(0, Math.floor(Math.min(...dat.flatMap(d => d.map((v, j) => v / mejores[j] * 100))) / 10) * 10 - 10), 104], tickfont: { size: 9, color: C.suave }, gridcolor: '#E0D7C8', angle: 90 }, angularaxis: { gridcolor: '#E0D7C8', tickfont: { size: 10 } } } });
  },
  carrera() {
    const el = document.getElementById('g7'); el.insertAdjacentHTML('beforebegin', '<div class="barra"><button type="button" id="carr-play">Reproducir</button><input id="carr" type="range" min="0" aria-label="Mes del ranking" style="flex:1"><b id="carr-m"></b></div>');
    const pers = APP.periodos, datos = Object.fromEntries(CONC.map(c => [c, Object.fromEntries(mensual(c, '', S.linea).map(x => [x.periodo, x.ingresos / 1e9]))])), max = Math.max(...CONC.flatMap(c => Object.values(datos[c]))) * 1.2;
    const rg = document.getElementById('carr'), et = document.getElementById('carr-m'), play = document.getElementById('carr-play'); rg.max = pers.length - 1; rg.value = pers.indexOf(S.mes);
    const pintar = () => { const p = pers[+rg.value]; et.textContent = mesC(p); const o = [...CONC].sort((a, b) => datos[a][p] - datos[b][p]); plot('g7', [{ type: 'bar', orientation: 'h', y: o.map(c => APP.nombres[c]), x: o.map(c => datos[c][p]), text: o.map(c => `$${n(datos[c][p], 1)}`), textposition: 'outside', cliponaxis: false, marker: { color: o.map(c => SERIES[CONC.indexOf(c)]) }, hovertemplate: '%{y}: $%{x:.1f} mil M<extra></extra>' }], { margin: { l: 142, r: 34, b: 34 }, showlegend: false, xaxis: { range: [0, max], gridcolor: '#E9E1D3' }, yaxis: { gridcolor: 'rgba(0,0,0,0)' } }); };
    rg.oninput = pintar; pintar(); let t = null;
    play.onclick = () => { if (t) { clearInterval(t); t = null; play.textContent = 'Reproducir'; return; } if (+rg.value >= pers.length - 1) rg.value = 0; play.textContent = 'Pausar'; t = cada(620, () => { if (+rg.value >= pers.length - 1) { clearInterval(t); t = null; play.textContent = 'Reproducir'; return; } rg.value = +rg.value + 1; pintar(); }); };
  },
  correlacion() {
    const ser = mensual(), inv = Object.fromEntries(invSerie().map(x => [x.periodo, x.viejo])), fi = Object.fromEntries(fiSerie().map(x => [x.periodo, x.pen])), u = Object.fromEntries(q(`SELECT v.periodo p, COUNT(*) c FROM ventas v WHERE ${condVentas()} GROUP BY 1`).map(x => [x.p, x.c]));
    const vars = { Ingresos: ser.map(x => x.ingresos), Margen: ser.map(x => x.margen), Unidades: ser.map(x => u[x.periodo] || 0), Personal: ser.map(x => x.personal), Financiero: ser.map(x => x.financiero), 'Inv. >60': ser.map(x => inv[x.periodo] || 0), 'F&I': ser.map(x => fi[x.periodo] || 0) };
    const corr = (a, b) => { const ma = a.reduce((s, x) => s + x, 0) / a.length, mb = b.reduce((s, x) => s + x, 0) / b.length; let c = 0, da = 0, db = 0; a.forEach((x, i) => { c += (x - ma) * (b[i] - mb); da += (x - ma) ** 2; db += (b[i] - mb) ** 2; }); return da && db ? c / Math.sqrt(da * db) : 0; };
    const ks = Object.keys(vars), z = ks.map(a => ks.map(b => corr(vars[a], vars[b])));
    plot('g21', [{ type: 'heatmap', x: ks, y: ks, z, zmin: -1, zmax: 1, colorscale: DIV, xgap: 2, ygap: 2, text: z.map(f => f.map(v => n(v, 2))), texttemplate: '%{text}', textfont: { size: 9 }, colorbar: { thickness: 9 }, hovertemplate: '%{y} y %{x}: %{text}<extra></extra>' }], { margin: { l: 72, b: 64 }, xaxis: { tickangle: -40 }, yaxis: { autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
  },
  anomalias() {
    const f = q(`SELECT g.fecha, g.valor, g.proveedor, g.sede_id, a.explicacion, a.severidad FROM gastos g LEFT JOIN alertas a ON a.origen=g.fuente AND a.regla='anomalia_gasto' WHERE ${inSedes('g')}`);
    const norm = f.filter(x => !x.explicacion), mal = f.filter(x => x.explicacion);
    plot('g19', [{ type: 'scattergl', x: norm.map(x => x.fecha), y: norm.map(x => x.valor / 1e6), text: norm.map(x => x.proveedor), name: 'Pago normal', mode: 'markers', marker: { color: '#9FB3C4', size: 5, opacity: .55 }, hovertemplate: '%{text}<br>%{x|%d %b %Y}: $%{y:,.1f} M<extra></extra>' }, { type: 'scatter', x: mal.map(x => x.fecha), y: mal.map(x => x.valor / 1e6), text: mal.map(x => `${x.proveedor}: ${x.explicacion}`), name: 'Pago con anomalía', mode: 'markers', marker: { color: C.terra, size: 12, symbol: 'diamond', line: { color: C.papel, width: 2 } }, hovertemplate: '%{text}<br>%{x|%d %b %Y}: $%{y:,.1f} M<extra></extra>' }], { xaxis: { type: 'date', tickformat: '%b %y' }, yaxis: { title: 'COP millones' } });
  },
  gauges() {
    const trazas = [], anot = [];
    CONC.forEach((c, i) => { const d = q(`SELECT 100.0*SUM(creditos)/SUM(unidades) p, 100.0*SUM(polizas)/SUM(unidades) s FROM fi WHERE periodo=? AND sede_id IN (${lista(sedesDe(c, ''))})`, [S.mes])[0]; [[d.p, 0, C.navy], [d.s, 1, C.teal]].forEach(([v, fila, col]) => trazas.push({ type: 'indicator', mode: 'gauge+number', value: v, number: { suffix: ' %', valueformat: '.1f', font: { size: 18, family: 'Fraunces, serif', color: C.navy } }, domain: { x: [i / 4 + .012, (i + 1) / 4 - .012], y: fila ? [0, .42] : [.5, .92] }, gauge: { shape: 'angular', axis: { range: [0, 70], tickfont: { size: 8 }, nticks: 4 }, bar: { color: col, thickness: .6 }, bgcolor: '#EFE7DA', borderwidth: 0 } })); anot.push({ text: APP.nombres[c].replace('Concesionario ', ''), x: (i + .5) / 4, y: 1.02, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 11, color: C.suave } }); });
    plot('g28', trazas, { margin: { l: 8, r: 8, t: 22, b: 6 }, annotations: anot });
  },
  productividad() {
    const sedes = sedesDe(), f = sedes.map(s => { const u = q(`SELECT COUNT(*) c FROM ventas WHERE periodo=? AND sede_id=?`, [S.mes, s])[0].c, p = q(`SELECT personas p FROM personal WHERE periodo=? AND sede_id=? AND rol='Vendedores'`, [S.mes, s])[0].p; return { s: APP.sedes.find(x => x.sede_id === s).nombre, v: u / p, u, p }; });
    plot('g29', [{ type: 'bar', x: f.map(x => x.s), y: f.map(x => x.v), customdata: f.map(x => [x.u, x.p]), text: f.map(x => n(x.v, 1)), textposition: 'inside', insidetextanchor: 'middle', textfont: { color: '#fff', size: 14 }, marker: { color: f.map(x => x.v >= 6 ? C.navy : C.terra) }, hovertemplate: '%{x}: %{y:.1f} unidades por vendedor<br>%{customdata[0]} unidades, %{customdata[1]} vendedores<extra></extra>' }], { margin: { b: 64 }, xaxis: { tickangle: f.length > 4 ? -35 : 0 }, yaxis: { title: 'Unidades por vendedor', rangemode: 'tozero' }, shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 6, y1: 6, line: { color: C.tinta, dash: 'dash', width: 1.4 } }], annotations: [{ xref: 'paper', x: 1, y: 6, text: 'Meta: 6', showarrow: false, yshift: 9, xanchor: 'right', font: { size: 11, color: C.suave } }] });
  },
};

/* Misma fórmula de src/pronostico.py (función aplicar). */
function aplicarEscenario(base, p) {
  return base.map(m => {
    const est = (m.periodo.endsWith('-12') ? 1 + p.dic : 1) * (1 + (p.demanda || 0));
    let iv = 0, bv = 0;
    for (const [canal, d] of Object.entries(m.canales)) { const f = canal === 'Flotas' ? 1 + p.flotas : canal === 'Retail' ? (1 + p.retail) * est : est, ing = d.unidades * f * d.precio; iv += ing; bv += ing * d.margen; }
    const otros = m.ing_otros * est, ingresos = iv + otros, bruto = bv + otros * m.margen_otros, financiero = m.saldo * (m.tasa + p.tasa_bp / 10000 / 12);
    return { periodo: m.periodo, ingresos, bruto, financiero, utilidad: bruto - ingresos * m.variable_pct - m.personal - m.semifijo - m.fijo - financiero };
  });
}

TABS.pronostico = {
  titulo: 'Pronóstico',
  p: { tasa_bp: 0, flotas: 0, retail: 0, dic: 0, demanda: 0 },
  render(el) {
    const cid = S.cid === 'TODOS' ? 'AND' : S.cid, X = APP.pron.concesionarios[cid]; this.X = X;
    const r = encabezado(el, `Cierre de 2026: ${X.nombre}`, 'Mueva los supuestos y vea cómo cambia el año. El cálculo corre en vivo con unidades, precio y margen por canal.');
    if (S.cid === 'TODOS') el.querySelector('.intro').insertAdjacentHTML('afterend', '<p class="aviso">El pronóstico se calcula por concesionario. Se muestra Concesionario Andino.</p>');
    r.insertAdjacentHTML('beforebegin', `<p class="aviso">${esc(APP.pron.supuesto_demanda)} ${esc(APP.pron.tasa_interpretacion)}</p>`);
    const fs = { script: 'src/pronostico.py', ruta: 'docs/data/pronostico.json', filtros: 'concesionario' };
    const desl = [['tasa_bp', 'Tasa wholesale', -100, 300, 25, v => `${v >= 0 ? '+' : ''}${v} bp`], ['flotas', 'Flotas', -30, 30, 1, v => `${v >= 0 ? '+' : ''}${v} %`], ['retail', 'Retail', -20, 20, 1, v => `${v >= 0 ? '+' : ''}${v} %`], ['dic', 'Estacionalidad de diciembre', -20, 20, 1, v => `${v >= 0 ? '+' : ''}${v} %`], ['demanda', 'Ritmo de demanda', -20, 15, 1, v => `${v >= 0 ? '+' : ''}${v} %`]];
    const html = `<div class="barra">${Object.keys(X.escenarios).map(e => `<button type="button" data-e="${e}">${e}</button>`).join('')}</div>${desl.map(([k, t, a, b, s]) => `<label class="deslizador"><span>${t}<output id="o-${k}"></output></span><input type="range" id="s-${k}" min="${a}" max="${b}" step="${s}"></label>`).join('')}<div class="res"><div>Ingresos 2026<b id="r-i"></b></div><div>Utilidad operativa<b id="r-u"></b></div></div>`;
    tarjeta(r, { w: 4, t: 'Simulador de supuestos', s: 'Aplica a noviembre y diciembre de 2026.', html, src: fs });
    tarjeta(r, { id: 'g23', w: 8, h: 470, t: 'Ingresos reales y escenarios (COP miles de millones)', s: 'Bandas de confianza de 80 % y 95 % alrededor del escenario Base.', src: fs });
    tarjeta(r, { id: 'g24', w: 6, h: 380, t: 'Backtest: real frente a pronóstico (COP miles de millones)', s: `Con datos hasta junio, error medio (MAPE): drivers ${P(X.backtest.mape_drivers)}, ETS ${P(X.backtest.mape_ets)}.`, src: fs });
    tarjeta(r, { id: 'g25', w: 6, h: 380, t: 'Tornado: qué mueve más la utilidad (COP millones)', s: 'Cambio en la utilidad operativa 2026 frente al escenario Base.', src: fs });
    tarjeta(r, { id: 'g26', w: 5, h: 350, t: 'Utilidad operativa: tasa × Flotas (COP miles de millones)', s: 'Más oscuro significa mayor utilidad.', src: fs });
    tarjeta(r, { id: 'g27', w: 7, h: 350, t: 'Descomposición de los ingresos (COP miles de millones)', s: 'Tendencia, estacionalidad y lo que queda sin explicar.', src: fs });
    desl.forEach(([k, , , , , f]) => { const i = document.getElementById(`s-${k}`), o = document.getElementById(`o-${k}`), esc100 = k !== 'tasa_bp'; const leer = () => esc100 ? Math.round(this.p[k] * 100) : this.p[k]; i.value = leer(); o.textContent = f(leer()); i.oninput = () => { this.p[k] = esc100 ? +i.value / 100 : +i.value; o.textContent = f(+i.value); this.calcular(); }; });
    el.querySelectorAll('[data-e]').forEach(b => b.onclick = () => { Object.assign(this.p, X.escenarios[b.dataset.e].supuestos); desl.forEach(([k, , , , , f]) => { const v = k === 'tasa_bp' ? this.p[k] : Math.round(this.p[k] * 100); document.getElementById(`s-${k}`).value = v; document.getElementById(`o-${k}`).textContent = f(v); }); this.calcular(); });
    this.calcular(); this.fijos();
  },
  calcular() {
    const X = this.X, m = aplicarEscenario(X.motor, this.p), ing = X.ytd_ingresos + m.reduce((a, x) => a + x.ingresos, 0), uti = X.ytd_utilidad + m.reduce((a, x) => a + x.utilidad, 0);
    document.getElementById('r-i').textContent = MM(ing, 1); document.getElementById('r-u').textContent = MM(uti, 2); this.resultado = { ing, uti };
    const h = X.historia.slice(-14), xh = h.map(x => mesC(x.periodo)), ult = h[h.length - 1], xf = X.escenarios.Base.meses.map(x => mesC(x.periodo)), xb = [xh[xh.length - 1], ...xf], base = X.escenarios.Base.meses;
    const banda = (a, b, nom, col) => ({ x: [...xb, ...[...xb].reverse()], y: [ult.ingresos / 1e9, ...base.map(x => x[b] / 1e9), ...[...base].reverse().map(x => x[a] / 1e9), ult.ingresos / 1e9], fill: 'toself', fillcolor: col, mode: 'lines', line: { width: 0 }, name: nom, hoverinfo: 'skip' });
    const esc = [['Optimista', C.teal, 'dash', 'diamond'], ['Base', C.navy, 'dot', 'circle'], ['Pesimista', C.terra, 'dashdot', 'square']].map(([e, col, d, s]) => ({ x: xb, y: [ult.ingresos / 1e9, ...X.escenarios[e].meses.map(x => x.ingresos / 1e9)], name: `${e}: ${MM(X.escenarios[e].ingresos_anio)}`, mode: 'lines+markers', line: { color: col, dash: d, width: 2 }, marker: { size: 8, symbol: s }, hovertemplate: `${e}<br>%{x}: $%{y:.1f} mil M<extra></extra>` }));
    plot('g23', [banda('banda95_inf', 'banda95_sup', 'Banda 95 %', 'rgba(107,58,99,.10)'), banda('banda_inf', 'banda_sup', 'Banda 80 %', 'rgba(107,58,99,.20)'), { x: xh, y: h.map(x => x.ingresos / 1e9), name: 'Real', mode: 'lines+markers', line: { color: C.tinta, width: 2.6 }, marker: { size: 6 }, hovertemplate: 'Real<br>%{x}: $%{y:.1f} mil M<extra></extra>' }, ...esc, { x: xb, y: [ult.ingresos / 1e9, ...m.map(x => x.ingresos / 1e9)], name: `Su escenario: ${MM(ing)}`, mode: 'lines+markers', line: { color: C.plum, width: 3 }, marker: { size: 11, symbol: 'star' }, hovertemplate: 'Su escenario<br>%{x}: $%{y:.1f} mil M<extra></extra>' }], { xaxis: { type: 'category', categoryorder: 'array', categoryarray: [...xh, ...xf] }, yaxis: { title: 'COP miles de millones' }, legend: { y: 1.17, font: { size: 10 } }, margin: { t: 30 } });
  },
  fijos() {
    const X = this.X, b = X.backtest.meses, x = b.map(f => mesC(f.periodo));
    plot('g24', [{ x, y: b.map(f => f.real / 1e9), name: 'Real', mode: 'lines+markers', line: { color: C.tinta, width: 2.5 }, marker: { size: 8 }, hovertemplate: 'Real %{x}: $%{y:.2f} mil M<extra></extra>' }, { x, y: b.map(f => f.drivers / 1e9), name: 'Drivers', mode: 'lines+markers', line: { color: C.navy, dash: 'dash' }, marker: { size: 8, symbol: 'square' }, hovertemplate: 'Drivers %{x}: $%{y:.2f} mil M<extra></extra>' }, { x, y: b.map(f => f.ets / 1e9), name: 'ETS', mode: 'lines+markers', line: { color: C.terra, dash: 'dot' }, marker: { size: 8, symbol: 'diamond' }, hovertemplate: 'ETS %{x}: $%{y:.2f} mil M<extra></extra>' }, { type: 'bar', x, y: b.map(f => f.error_drivers * 100), xaxis: 'x2', yaxis: 'y2', name: 'Error drivers', marker: { color: C.navy }, hovertemplate: 'Drivers %{x}: %{y:.1f} %<extra></extra>' }, { type: 'bar', x, y: b.map(f => f.error_ets * 100), xaxis: 'x2', yaxis: 'y2', name: 'Error ETS', marker: { color: C.terra }, hovertemplate: 'ETS %{x}: %{y:.1f} %<extra></extra>' }], { grid: { rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' }, yaxis: { domain: [.42, 1], title: 'Ingresos' }, yaxis2: { domain: [0, .3], title: 'Error %', gridcolor: '#E9E1D3', zerolinecolor: '#8B8171' }, xaxis2: { linecolor: C.borde }, barmode: 'group', legend: { y: 1.16 }, margin: { t: 28 } });
    const t = [...X.tornado].sort((a, c) => Math.abs(a.alto - a.bajo) - Math.abs(c.alto - c.bajo)), et = t.map(f => f.supuesto);
    plot('g25', [{ type: 'bar', orientation: 'h', y: et, x: t.map(f => f.bajo / 1e6), name: 'Caso adverso', marker: { color: C.terra }, text: t.map(f => n(f.bajo / 1e6, 0)), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}<br>%{x:,.0f} M<extra></extra>' }, { type: 'bar', orientation: 'h', y: et, x: t.map(f => f.alto / 1e6), name: 'Caso favorable', marker: { color: C.teal }, text: t.map(f => `+${n(f.alto / 1e6, 0)}`), textposition: 'outside', cliponaxis: false, hovertemplate: '%{y}<br>+%{x:,.0f} M<extra></extra>' }], { barmode: 'relative', margin: { l: 190, r: 34 }, xaxis: { range: [Math.min(...t.map(f => f.bajo / 1e6)) * 1.22, Math.max(...t.map(f => f.alto / 1e6)) * 1.22], title: 'COP millones', gridcolor: '#E9E1D3', zeroline: true, zerolinecolor: C.tinta }, yaxis: { gridcolor: 'rgba(0,0,0,0)' } });
    const s = X.sensibilidad, z = s.utilidad.map(f => f.map(v => v / 1e9));
    plot('g26', [{ type: 'heatmap', x: s.flotas_etiquetas, y: s.tasa_etiquetas, z, colorscale: SEQ, xgap: 3, ygap: 3, text: z.map(f => f.map(v => n(v, 3))), texttemplate: '$%{text}', textfont: { size: 13 }, colorbar: { thickness: 9 }, hovertemplate: '%{y} · %{x}<br>$%{text} mil M<extra></extra>' }], { margin: { l: 72 }, yaxis: { autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } });
    const d = X.descomposicion, ex = d.periodos.map(mesC), comp = [['Observado', d.observado, C.tinta, 'y'], ['Tendencia', d.tendencia, C.navy, 'y2'], ['Estacional', d.estacional, C.teal, 'y3'], ['Residuo', d.residuo, C.terra, 'y4']];
    plot('g27', comp.map(([nom, v, col, eje]) => ({ x: ex, y: v.map(a => a == null ? null : a / 1e9), yaxis: eje, name: nom, mode: 'lines', line: { color: col, width: 2 }, connectgaps: false, hovertemplate: `${nom} %{x}: %{y:.2f}<extra></extra>` })), { showlegend: false, margin: { l: 72, t: 6 }, xaxis: { type: 'category', anchor: 'y4', tickangle: -50, tickfont: { size: 9 } }, yaxis: { domain: [.79, 1], title: { text: 'Observado', font: { size: 10 } } }, yaxis2: { domain: [.53, .74], title: { text: 'Tendencia', font: { size: 10 } }, gridcolor: '#E9E1D3' }, yaxis3: { domain: [.27, .48], title: { text: 'Estacional', font: { size: 10 } }, gridcolor: '#E9E1D3' }, yaxis4: { domain: [0, .22], tickformat: '.3f', nticks: 3, title: { text: 'Residuo', font: { size: 10 } }, gridcolor: '#E9E1D3' } });
  },
};

TABS.inventario = {
  titulo: 'Inventario',
  render(el) {
    const r = encabezado(el, 'El capital parado en el patio', 'Cada vehículo con más de 60 días financia intereses. Aquí se ve cuánto, dónde y cuáles son.');
    const fi = { tabla: 'inventario', script: 'src/ingesta.py', filtros: 'concesionario, sede, mes, línea' };
    const vi = q(`SELECT SUM(CASE WHEN i.rango='>60' THEN i.costo ELSE 0 END) v, SUM(i.costo) t, COUNT(*) u, SUM(i.rango='>60') o FROM inventario i WHERE ${condInv()}`)[0], tasa = APP.pron.patrones.tasa_ilustrativa;
    r.insertAdjacentHTML('beforebegin', `<div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr))"><article class="kpi"><small>Inventario total</small><strong>${M(vi.t, 0)}</strong><span class="var">${n(vi.u)} unidades</span></article><article class="kpi"><small>Más de 60 días</small><strong>${M(vi.v, 0)}</strong><span class="var">${P(vi.v / vi.t)} del valor · ${n(vi.o)} unidades</span></article><article class="kpi"><small>Costo financiero al mes</small><strong>${M(vi.v * tasa)}</strong><span class="var">Tasa ilustrativa ${P(tasa)} mensual</span></article></div>`);
    tarjeta(r, { id: 'g15', w: 7, h: 390, t: 'Antigüedad por línea y sede (COP millones)', s: 'Clic en una barra para filtrar por esa línea.', src: fi });
    tarjeta(r, { id: 'g17', w: 5, h: 390, t: 'Distribución de días en inventario (unidades)', s: 'La línea marca el umbral de 60 días.', src: fi });
    tarjeta(r, { id: 'g16', w: 6, h: 330, t: 'Costo financiero del inventario envejecido (COP millones al mes)', s: `Inventario de más de 60 días × ${P(tasa)} mensual.`, src: { ...fi, filtros: 'concesionario, sede, línea' } });
    tarjeta(r, { id: 'g18', w: 6, h: 330, t: 'Obligaciones wholesale: saldo y tasa', s: 'Barras = saldo (COP miles de millones). Línea = tasa mensual ponderada.', src: { tabla: 'obligaciones', script: 'src/ingesta.py', filtros: 'concesionario, sede' } });
    const lentas = q(`SELECT i.vin, s.nombre AS sede, i.linea, i.modelo, i.dias, i.costo, i.fecha_ingreso, i.costo*${tasa} AS costo_mes FROM inventario i JOIN sedes s USING(sede_id) WHERE ${condInv()} ORDER BY i.dias DESC, i.costo DESC LIMIT 25`);
    tarjeta(r, { w: 12, t: 'Las 25 unidades más lentas', s: 'La lista para la reunión con el equipo comercial.', html: tablaHTML(lentas, null, { nombres: { vin: 'VIN', sede: 'Sede', linea: 'Línea', modelo: 'Modelo', dias: 'Días', costo: 'Costo', fecha_ingreso: 'Ingreso', costo_mes: 'Costo financiero / mes' }, fmt: { costo: x => M(x), costo_mes: x => M(x, 2) }, alto: 360 }), src: fi });
    const d = q(`SELECT i.linea l, s.nombre se, i.rango r, SUM(i.costo) v FROM inventario i JOIN sedes s USING(sede_id) WHERE ${condInv()} GROUP BY 1,2,3`), cats = [...new Set(d.map(x => `${x.l}|${x.se}`))].sort((a, b) => LINEAS.indexOf(a.split('|')[0]) - LINEAS.indexOf(b.split('|')[0]));
    const g15 = plot('g15', [['0-30', C.teal], ['31-60', C.ambar], ['>60', C.terra]].map(([k, col]) => ({ type: 'bar', name: `${k} días`, x: [cats.map(c => c.split('|')[0]), cats.map(c => c.split('|')[1])], y: cats.map(c => (d.find(x => `${x.l}|${x.se}` === c && x.r === k)?.v || 0) / 1e6), marker: { color: col, line: { color: C.papel, width: 1 } }, hovertemplate: `${k} días<br>%{x}: $%{y:,.0f} M<extra></extra>` })), { barmode: 'stack', margin: { b: 70 }, xaxis: { tickangle: -35, tickfont: { size: 10 } }, yaxis: { title: 'COP millones' } });
    g15?.on('plotly_click', e => { const l = e.points[0].x?.[0] ?? e.points[0].data.x[0][e.points[0].pointNumber]; if (LINEAS.includes(l)) fijarFiltro('linea', S.linea === l ? '' : l); });
    const dias = q(`SELECT i.dias d FROM inventario i WHERE ${condInv()}`).map(x => x.d), maxC = 1;
    plot('g17', [{ type: 'histogram', x: dias.filter(x => x <= 60), name: 'Hasta 60 días', xbins: { start: 0, end: 155, size: 5 }, marker: { color: C.navy, line: { color: C.papel, width: 1 } }, hovertemplate: '%{x} días: %{y} unidades<extra></extra>' }, { type: 'histogram', x: dias.filter(x => x > 60), name: 'Más de 60 días', xbins: { start: 0, end: 155, size: 5 }, marker: { color: C.terra, line: { color: C.papel, width: 1 } }, hovertemplate: '%{x} días: %{y} unidades<extra></extra>' }], { barmode: 'stack', xaxis: { title: 'Días en inventario' }, yaxis: { title: 'Unidades' }, shapes: [{ type: 'line', x0: 60, x1: 60, yref: 'paper', y0: 0, y1: maxC, line: { color: C.tinta, dash: 'dash', width: 1.5 } }], annotations: [{ x: 60, yref: 'paper', y: 1, text: '60 días', showarrow: false, xanchor: 'left', xshift: 4, font: { size: 11 } }] });
    const cs = invSerie();
    plot('g16', [{ x: cs.map(x => mesC(x.periodo)), y: cs.map(x => x.viejo * tasa / 1e6), fill: 'tozeroy', fillcolor: 'rgba(180,83,42,.2)', mode: 'lines+markers', line: { color: C.terra, width: 2 }, marker: { size: 5 }, hovertemplate: '%{x}: $%{y:.1f} M al mes<extra></extra>' }], { xaxis: { type: 'category', tickangle: -50, tickfont: { size: 9 } }, yaxis: { title: 'COP millones', rangemode: 'tozero' } });
    const ob = q(`SELECT periodo p, SUM(saldo) s, 1.0*SUM(interes_mes)/SUM(saldo) t FROM obligaciones WHERE ${inSedes()} GROUP BY 1 ORDER BY 1`);
    plot('g18', [{ type: 'bar', x: ob.map(x => mesC(x.p)), y: ob.map(x => x.s / 1e9), name: 'Saldo', marker: { color: C.navy }, hovertemplate: '%{x}: $%{y:.1f} mil M<extra></extra>' }, { x: ob.map(x => mesC(x.p)), y: ob.map(x => x.t * 100), yaxis: 'y2', name: 'Tasa mensual', mode: 'lines+markers', line: { color: C.terra, width: 2, dash: 'dash' }, marker: { size: 6, symbol: 'square' }, hovertemplate: '%{x}: %{y:.3f} % mensual<extra></extra>' }], { margin: { r: 54 }, xaxis: { type: 'category', tickangle: -50, tickfont: { size: 9 } }, yaxis: { title: 'Saldo (mil M)' }, yaxis2: { overlaying: 'y', side: 'right', ticksuffix: ' %', showgrid: false, tickfont: { color: C.suave }, tickformat: '.2f' } });
  },
};
