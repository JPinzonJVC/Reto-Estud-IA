const endpoints = {
  overview: '/dashboard/overview',
  affiliateFilters: '/affiliates/silver/filters',
  analyticsFilters: '/analytics/silver/filters',
  portfolio: '/affiliates/silver/portfolio',
  renewals: '/affiliates/silver/renewals',
  pillars: '/affiliates/silver/pillars',
  kams: '/affiliates/silver/kam-summary',
  participation: '/analytics/silver/participation',
  audience: '/analytics/silver/audience',
  satisfaction: '/analytics/silver/satisfaction',
  dimensions: '/analytics/silver/satisfaction-dimensions',
  segments: '/retention/silver/segments',
};

const state = { chart: 'bars', insight: 'trend', audience: 'roles' };
const byId = (id) => document.getElementById(id);
const request = async (url) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(url);
  return response.json();
};
const appendOptions = (element, values, formatter = (value) => value) =>
  values.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = formatter(value);
    element.append(option);
  });
const periodBounds = (period) =>
  period ? { fecha_desde: `${period}-01`, fecha_hasta: `${period}-31` } : {};
function query(params) {
  const clean = Object.entries(params).filter(([, value]) => value);
  return clean.length ? `?${new URLSearchParams(clean)}` : '';
}

function renderBars(items) {
  const top = [...items].sort((a, b) => b.asistencias - a.asistencias).slice(0, 10);
  const maximum = Math.max(...top.map((item) => item.asistencias), 1);
  byId('participation-view').innerHTML = `<div class="bar-list">${
    top
      .map(
        (item) =>
          `<div class="bar-row"><span title="${item.nombre_evento || ''}">${item.nombre_evento || 'Evento sin nombre'}</span><div class="track"><div class="fill" style="width:${(item.asistencias / maximum) * 100}%"></div></div><b>${item.asistencias}</b></div>`
      )
      .join('') || '<p>Sin asistencias para estos filtros.</p>'
  }</div>`;
}

function renderParticipation(items) {
  if (state.chart === 'bars') return renderBars(items);
  if (state.chart === 'donut') {
    const top = [...items].sort((a, b) => b.asistencias - a.asistencias).slice(0, 8);
    const total = top.reduce((sum, item) => sum + item.asistencias, 0);
    const colors = ['#5000bf', '#ff5a00', '#75bdbb', '#9f7aea', '#2b6cb0', '#d69e2e', '#38a169', '#e53e3e'];
    let offset = 0;
    const slices = top
      .map((item, index) => {
        const share = total ? item.asistencias / total : 0;
        const circle = `<circle cx="50" cy="50" r="38" pathLength="100" stroke="${colors[index % colors.length]}" stroke-dasharray="${share * 100} ${100 - share * 100}" stroke-dashoffset="${-offset}"/>`;
        offset += share * 100;
        return circle;
      })
      .join('');
    byId('participation-view').innerHTML = total
      ? `<div class="donut-layout"><svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Distribución de asistencias por evento"><circle class="donut-base" cx="50" cy="50" r="38"/>${slices}<text x="50" y="48">${total}</text><text x="50" y="59">top 8</text></svg><ul class="legend">${top
          .map(
            (item, index) =>
              `<li><i style="background:${colors[index % colors.length]}"></i><span>${item.nombre_evento || 'Evento'}</span><b>${item.asistencias}</b></li>`
          )
          .join('')}</ul></div>`
      : '<p>Sin asistencias para estos filtros.</p>';
    return;
  }
  byId('participation-view').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Evento</th><th>Línea</th><th>Asistencias</th><th>Afiliados</th><th>Leads</th><th>Empresas</th></tr></thead><tbody>${
    items
      .map(
        (item) =>
          `<tr><td>${item.nombre_evento || '—'}</td><td>${item.linea_oferta || '—'}</td><td>${item.asistencias}</td><td>${item.asistentes_afiliados ?? '—'}</td><td>${item.asistentes_no_afiliados ?? '—'}</td><td>${item.empresas_distintas}</td></tr>`
      )
      .join('') || '<tr><td colspan="6">Sin asistencias para estos filtros.</td></tr>'
  }</tbody></table></div>`;
}

function renderAudience(data) {
  const target = byId('audience-view');
  const desc = byId('audience-description');
  if (state.audience === 'roles') {
    const items = data.niveles_cargo || [];
    const max = Math.max(...items.map((item) => item.asistencias), 1);
    desc.textContent = 'Distribución de asistencias según el nivel jerárquico del participante.';
    target.innerHTML = `<div class="bar-list">${
      items
        .map(
          (item) =>
            `<div class="bar-row"><span>${item.nivel_cargo}</span><div class="track"><div class="fill" style="width:${(item.asistencias / max) * 100}%"></div></div><b>${item.asistencias}</b></div>`
        )
        .join('') || '<p>Sin datos de audiencia para estos filtros.</p>'
    }</div>`;
    return;
  }
  const items = state.audience === 'lines' ? data.lineas_oferta || [] : data.modalidades || [];
  const labelKey = state.audience === 'lines' ? 'linea_oferta' : 'modalidad';
  const max = Math.max(...items.map((item) => item.asistencias), 1);
  desc.textContent =
    state.audience === 'lines'
      ? 'Afiliados (violeta) vs. No afiliados / Leads (naranja) por línea de oferta 2027.'
      : 'Afiliados (violeta) vs. No afiliados / Leads (naranja) por modalidad de evento.';
  target.innerHTML = `<div class="bar-list">${
    items
      .map((item) => {
        const afPct = (item.afiliados / max) * 100;
        const noAfPct = (item.no_afiliados / max) * 100;
        return `<div class="bar-row"><span>${item[labelKey]}</span><div class="track stacked-track"><div class="fill" style="width:${afPct}%" title="Afiliados: ${item.afiliados}"></div><div class="fill lead" style="width:${noAfPct}%" title="No afiliados: ${item.no_afiliados}"></div></div><b>${item.asistencias}</b></div>`;
      })
      .join('') || '<p>Sin datos para estos filtros.</p>'
  }</div><div class="nps-legend"><span><i style="background:var(--violet)"></i>Afiliados</span><span><i style="background:var(--orange)"></i>No afiliados (Leads)</span></div>`;
}

function renderPillars(data) {
  const items = data.pilares || [];
  byId('pillars-description').textContent = `Adopción sobre ${data.total_activos} afiliados activos en el filtro actual.`;
  byId('women-share').textContent =
    data.porcentaje_mujeres_promedio !== null
      ? `${data.porcentaje_mujeres_promedio}% mujeres (n=${data.empresas_con_dato_mujeres})`
      : 'Sin dato diversidad';
  byId('pillars-view').innerHTML = `<div class="bar-list">${
    items
      .map(
        (item) =>
          `<div class="bar-row"><span>${item.nombre}</span><div class="track"><div class="fill teal" style="width:${item.porcentaje}%"></div></div><b>${item.empresas} <small>(${item.porcentaje}%)</small></b></div>`
      )
      .join('') || '<p>Sin datos de pilares.</p>'
  }</div>`;
}

function renderKams(items) {
  byId('kams-total').textContent = `${items.length} ejecutivas`;
  byId('kams-body').innerHTML =
    items
      .map(
        (item) =>
          `<tr><td>${item.kam_id}</td><td>${item.responsable_nombre || '—'}</td><td>${item.afiliados_activos}</td><td>${item.vencen_90d}</td><td>${item.empresas_con_asistencia}</td><td>${item.porcentaje_en_servicios}%</td><td>${item.asistencias_totales}</td><td>${item.renovaciones}</td></tr>`
      )
      .join('') || '<tr><td colspan="8">Sin datos por ejecutiva.</td></tr>';
}

function renderDimensions(data) {
  const rows = data.por_modalidad || [];
  byId('topics-count').textContent = `${data.total_con_temarios} temarios`;
  byId('dimensions-view').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Modalidad</th><th>Resp.</th><th>Loc./Plat.</th><th>Convoc.</th><th>Confer.</th><th>Temas</th></tr></thead><tbody>${
    rows
      .map(
        (item) =>
          `<tr><td>${item.modalidad}</td><td>${item.respuestas}</td><td>${item.locacion_plataforma}</td><td>${item.convocatoria_publicidad}</td><td>${item.conferencistas}</td><td>${item.relevancia_temas}</td></tr>`
      )
      .join('') || '<tr><td colspan="6">Sin encuestas para este periodo.</td></tr>'
  }</tbody></table></div>`;
  const topics = data.temarios_recientes || [];
  byId('topics-list').innerHTML =
    topics
      .slice(0, 6)
      .map(
        (item) =>
          `<li>${item.temario}<small>${item.modalidad || 'Encuesta'} · ${item.fecha || 'Sin fecha'}</small></li>`
      )
      .join('') || '<li>Sin temarios sugeridos en este periodo.</li>';
}

function renderPortfolio(data) {
  byId('portfolio-total').textContent = `${data.total} empresas`;
  byId('portfolio-body').innerHTML =
    data.items
      .map(
        (item) =>
          `<tr><td>${item.id_empresa}</td><td>${item.kam_nombre || item.kam_id || '—'}</td><td>${item.nivel_membresia || '—'}</td><td>${item.sector_economico || '—'}</td><td>${item.tamano_empresa || '—'}</td><td>${item.estado_membresia || '—'}</td><td>${item.ciudad || '—'}</td><td>${item.fecha_miembro_desde || '—'}</td><td>${item.fecha_expiracion || '—'}</td></tr>`
      )
      .join('') || '<tr><td colspan="9">Sin resultados para estos filtros.</td></tr>';
}

function renderSatisfaction(items) {
  byId('satisfaction-body').innerHTML =
    items
      .map(
        (item) =>
          `<tr><td>${item.periodo_mes || 'Sin periodo'}</td><td>${item.respuestas}</td><td>${item.promedio_satisfaccion}</td><td>${item.nps_adaptado_1_5}</td></tr>`
      )
      .join('') || '<tr><td colspan="4">Sin encuestas para este periodo.</td></tr>';
}

function renderInsights(participation, satisfaction) {
  const target = byId('insight-view');
  const description = byId('insight-description');
  if (state.insight === 'nps') {
    const total = satisfaction.reduce((sum, item) => sum + item.respuestas, 0);
    const promoters = satisfaction.reduce((sum, item) => sum + (item.promotores || 0), 0);
    const detractors = satisfaction.reduce((sum, item) => sum + (item.detractores || 0), 0);
    const neutral = Math.max(total - promoters - detractors, 0);
    const nps = total ? Math.round(((promoters - detractors) / total) * 100) : 0;
    description.textContent =
      'Composición NPS adaptado: 4–5 promotor, 3 neutro y 1–2 detractor. Una respuesta de 3 no cambia el NPS neto.';
    target.innerHTML = total
      ? `<div class="nps-summary"><strong>${nps}</strong><span>NPS adaptado</span></div><div class="stacked"><i class="promoter" style="width:${(promoters / total) * 100}%"></i><i class="neutral" style="width:${(neutral / total) * 100}%"></i><i class="detractor" style="width:${(detractors / total) * 100}%"></i></div><div class="nps-legend"><span><i class="promoter"></i>Promotores ${promoters}</span><span><i class="neutral"></i>Neutros ${neutral}</span><span><i class="detractor"></i>Detractores ${detractors}</span></div>`
      : '<p>Sin encuestas para estos filtros.</p>';
    return;
  }
  const periods = [
    ...new Set(
      [
        ...participation.map((item) => item.fecha_evento?.slice(0, 7)),
        ...satisfaction.map((item) => item.periodo_mes),
      ].filter(Boolean)
    ),
  ].sort();
  const values = periods.map((period) =>
    participation
      .filter((item) => item.fecha_evento?.startsWith(period))
      .reduce((sum, item) => sum + item.asistencias, 0)
  );
  const maximum = Math.max(...values, 1);
  description.textContent = 'Tendencia mensual de asistencias y promedio de satisfacción en Silver.';
  target.innerHTML = periods.length
    ? `<div class="trend-list">${periods
        .map(
          (period, index) =>
            `<div><span>${period}</span><div class="track"><i class="fill" style="width:${(values[index] / maximum) * 100}%"></i></div><b>${values[index]}</b></div>`
        )
        .join('')}</div><p class="chart-note">Satisfacción: ${periods
        .map((period) => {
          const records = satisfaction.filter((item) => item.periodo_mes === period);
          const value = records.length
            ? records.reduce((sum, item) => sum + item.promedio_satisfaccion, 0) / records.length
            : null;
          return `${period} ${value === null ? 'sin respuesta' : value.toFixed(2)}`;
        })
        .join(' · ')}</p>`
    : '<p>Sin periodos para mostrar.</p>';
}

function renderSegments(data) {
  const rows = [
    ...data.vencimientos_proximos.slice(0, 2).map(
      (row) => `Contactar ${row.id_empresa}<small>Vence ${row.fecha_expiracion} · ${row.kam_id}</small>`
    ),
    ...data.afiliados_sin_participacion.slice(0, 2).map(
      (row) => `Activar ${row.id_empresa}<small>Sin participación · ${row.kam_id}</small>`
    ),
    ...data.asistentes_no_afiliados.slice(0, 2).map(
      (row) => `Convertir asistente ${row.id_persona}<small>Evento ${row.id_evento}</small>`
    ),
  ];
  byId('segments-list').innerHTML =
    rows.map((row) => `<li>${row}</li>`).join('') || '<li>Sin acciones pendientes.</li>';
}

async function refresh() {
  const period = byId('period-filter').value;
  const kam = byId('kam-filter').value;
  const level = byId('level-filter').value;
  const sector = byId('sector-filter').value;
  const size = byId('size-filter').value;
  const membershipStatus = byId('membership-status-filter').value;
  const city = byId('city-filter').value;
  const eventCity = byId('event-city-filter').value;
  const line = byId('line-filter').value;
  const modality = byId('modality-filter').value;
  const dates = periodBounds(period);
  byId('filter-status').textContent = 'Actualizando indicadores…';
  try {
    const [
      portfolio,
      renewals,
      participation,
      audience,
      pillars,
      kams,
      satisfaction,
      dimensions,
      segments,
    ] = await Promise.all([
      request(
        endpoints.portfolio +
          query({
            kam_id: kam,
            nivel_membresia: level,
            sector,
            tamano_empresa: size,
            estado_membresia: membershipStatus,
            ciudad: city,
          })
      ),
      request(
        endpoints.renewals + query({ kam_id: kam, periodo_desde: period, periodo_hasta: period })
      ),
      request(
        endpoints.participation +
          query({
            ...dates,
            kam_id: kam,
            ciudad_evento: eventCity,
            linea_oferta: line,
            modalidad: modality,
          })
      ),
      request(
        endpoints.audience +
          query({
            ...dates,
            kam_id: kam,
            ciudad_evento: eventCity,
            linea_oferta: line,
            modalidad: modality,
          })
      ),
      request(endpoints.pillars + query({ kam_id: kam, nivel_membresia: level, sector })),
      request(endpoints.kams),
      request(endpoints.satisfaction + query(dates)),
      request(endpoints.dimensions + query(dates)),
      request(endpoints.segments),
    ]);
    renderPortfolio(portfolio);
    renderParticipation(participation);
    renderAudience(audience);
    renderPillars(pillars);
    renderKams(kams);
    renderSatisfaction(satisfaction);
    renderDimensions(dimensions);
    renderInsights(participation, satisfaction);
    renderSegments(segments);
    byId('renewal-count').textContent = renewals.reduce((sum, item) => sum + item.renovaciones, 0);
    const totalAtt = participation.reduce((sum, item) => sum + item.asistencias, 0);
    const leadsAtt = participation.reduce(
      (sum, item) => sum + (item.asistentes_no_afiliados || 0),
      0
    );
    byId('attendance-count').textContent = totalAtt;
    byId('attendance-detail').textContent = `${totalAtt - leadsAtt} afiliados · ${leadsAtt} leads`;
    const activeSatisfaction = satisfaction.length
      ? satisfaction.reduce((sum, item) => sum + item.promedio_satisfaccion, 0) /
        satisfaction.length
      : 0;
    byId('satisfaction-score').textContent = activeSatisfaction.toFixed(2);
    byId('filter-status').textContent = `Filtros aplicados: ${period || 'todos los periodos'} · ${
      kam || 'todas las KAM'
    } · ${line || 'todas las líneas'}.`;
  } catch (error) {
    byId('filter-status').textContent = 'No fue posible actualizar algunos indicadores.';
  }
}

async function initialize() {
  try {
    const [overview, affiliateFilters, analyticsFilters] = await Promise.all([
      request(endpoints.overview),
      request(endpoints.affiliateFilters),
      request(endpoints.analyticsFilters),
    ]);
    byId('data-date').textContent = `Corte: ${overview.fecha_referencia}`;
    byId('active-count').textContent = overview.afiliados_activos;
    byId('service-rate').textContent = `${overview.porcentaje_afiliados_en_servicios}%`;
    byId('service-detail').textContent = `${overview.empresas_con_servicio} de ${overview.afiliados_activos} activos`;
    byId('expiring-count').textContent = overview.vencimientos_proximos['90'];
    appendOptions(byId('period-filter'), analyticsFilters.periodos_asistencia, (value) =>
      new Intl.DateTimeFormat('es-CO', {
        month: 'long',
        year: 'numeric',
        timeZone: 'UTC',
      }).format(new Date(`${value}-01T00:00:00Z`))
    );
    appendOptions(byId('kam-filter'), affiliateFilters.kams);
    appendOptions(byId('level-filter'), affiliateFilters.niveles_membresia);
    appendOptions(byId('sector-filter'), affiliateFilters.sectores);
    appendOptions(byId('size-filter'), affiliateFilters.tamanos_empresa || []);
    appendOptions(byId('membership-status-filter'), affiliateFilters.estados_membresia || []);
    appendOptions(byId('city-filter'), affiliateFilters.ciudades);
    appendOptions(byId('event-city-filter'), analyticsFilters.ciudades_evento || []);
    appendOptions(byId('line-filter'), analyticsFilters.lineas_oferta || []);
    appendOptions(byId('modality-filter'), analyticsFilters.modalidades_evento || []);
    await refresh();
  } catch (error) {
    byId('filter-status').textContent = 'No fue posible cargar el dashboard.';
  }
}

document
  .querySelectorAll('.filters select')
  .forEach((element) => element.addEventListener('change', refresh));
byId('clear-filters').addEventListener('click', () => {
  document.querySelectorAll('.filters select').forEach((element) => {
    element.value = '';
  });
  refresh();
});
document.querySelectorAll('[data-chart]').forEach((button) =>
  button.addEventListener('click', () => {
    document
      .querySelectorAll('[data-chart]')
      .forEach((item) => item.classList.remove('is-active'));
    button.classList.add('is-active');
    state.chart = button.dataset.chart;
    refresh();
  })
);
document.querySelectorAll('[data-audience]').forEach((button) =>
  button.addEventListener('click', () => {
    document
      .querySelectorAll('[data-audience]')
      .forEach((item) => item.classList.remove('is-active'));
    button.classList.add('is-active');
    state.audience = button.dataset.audience;
    refresh();
  })
);
document.querySelectorAll('[data-insight]').forEach((button) =>
  button.addEventListener('click', () => {
    document
      .querySelectorAll('[data-insight]')
      .forEach((item) => item.classList.remove('is-active'));
    button.classList.add('is-active');
    state.insight = button.dataset.insight;
    refresh();
  })
);
const storedTheme = localStorage.getItem('actho-theme');
if (storedTheme === 'dark') {
  document.documentElement.dataset.theme = 'dark';
  byId('theme-toggle').textContent = 'Modo claro';
}
byId('theme-toggle').addEventListener('click', () => {
  const dark = document.documentElement.dataset.theme !== 'dark';
  document.documentElement.dataset.theme = dark ? 'dark' : '';
  localStorage.setItem('actho-theme', dark ? 'dark' : 'light');
  byId('theme-toggle').textContent = dark ? 'Modo claro' : 'Modo oscuro';
});
initialize();
