const endpoints = {
  overview: '/dashboard/overview',
  affiliateFilters: '/affiliates/silver/filters',
  analyticsFilters: '/analytics/silver/filters',
  portfolio: '/affiliates/silver/portfolio',
  renewals: '/affiliates/silver/renewals',
  pillars: '/affiliates/silver/pillars',
  kams: '/affiliates/silver/kam-summary',
  distribution: '/affiliates/silver/distribution',
  participation: '/analytics/silver/participation',
  audience: '/analytics/silver/audience',
  satisfaction: '/analytics/silver/satisfaction',
  dimensions: '/analytics/silver/satisfaction-dimensions',
  segments: '/retention/silver/segments',
  engagementRisk: '/retention/silver/engagement-risk',
  exportCsv: '/retention/silver/export',
};

const state = {
  tab: 'overview',
  chart: 'bars',
  insight: 'trend',
  audience: 'roles',
  kamView: 'chart',
  expView: 'global',
  distView: 'nivel',
  riskTab: 'sin_participacion',
  portfolioItems: [],
  lastDistribution: null,
  lastRisk: null,
};

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

function escapeHtml(text) {
  return String(text ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/* FLOATING TOOLTIP FOR ALL SVG & BAR DATA POINTS */
const tooltipEl = byId('chart-tooltip');
document.addEventListener('pointermove', (e) => {
  const target = e.target.closest?.('[data-tip]');
  if (!target) {
    tooltipEl.hidden = true;
    return;
  }
  tooltipEl.textContent = target.dataset.tip;
  tooltipEl.style.left = `${e.clientX}px`;
  tooltipEl.style.top = `${e.clientY}px`;
  tooltipEl.hidden = false;
});
document.addEventListener('pointerout', (e) => {
  if (!e.relatedTarget || !e.relatedTarget.closest?.('[data-tip]')) {
    tooltipEl.hidden = true;
  }
});

/* SMOOTH CUBIC BEZIER PATH HELPER (HORIZON UI STYLE) */
function smoothPath(points) {
  if (!points.length) return '';
  if (points.length === 1) return `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  let d = `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[Math.max(i - 1, 0)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(i + 2, points.length - 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }
  return d;
}

function setActiveTab(tabName) {
  state.tab = tabName;
  document.querySelectorAll('[data-tab]').forEach((btn) => {
    const active = btn.dataset.tab === tabName;
    btn.classList.toggle('is-active', active);
    btn.setAttribute('aria-selected', String(active));
    if (active && btn.dataset.title) {
      byId('view-heading').textContent = btn.dataset.title;
    }
  });
  document.querySelectorAll('[data-view]').forEach((panel) => {
    panel.classList.toggle('is-active', panel.dataset.view === tabName);
  });
}

function renderTrendAreaChart(participation, satisfaction) {
  const target = byId('insight-view');
  const description = byId('insight-description');

  if (state.insight === 'nps') {
    const total = satisfaction.reduce((sum, item) => sum + item.respuestas, 0);
    const promoters = satisfaction.reduce((sum, item) => sum + (item.promotores || 0), 0);
    const detractors = satisfaction.reduce((sum, item) => sum + (item.detractores || 0), 0);
    const neutral = Math.max(total - promoters - detractors, 0);
    const nps = total ? Math.round(((promoters - detractors) / total) * 100) : 0;
    description.textContent =
      'Composición NPS adaptado (4–5 promotor, 3 neutro, 1–2 detractor).';
    target.innerHTML = total
      ? `<div class="nps-summary"><strong>${nps}</strong><span>NPS adaptado (${total} respuestas)</span></div>
         <div class="stacked">
           <i class="promoter" style="width:${(promoters / total) * 100}%" data-tip="Promotores: ${promoters}"></i>
           <i class="neutral" style="width:${(neutral / total) * 100}%" data-tip="Neutros: ${neutral}"></i>
           <i class="detractor" style="width:${(detractors / total) * 100}%" data-tip="Detractores: ${detractors}"></i>
         </div>
         <div class="nps-legend">
           <span><i class="promoter"></i>Promotores ${promoters} (${Math.round((promoters / total) * 100)}%)</span>
           <span><i class="neutral"></i>Neutros ${neutral}</span>
           <span><i class="detractor"></i>Detractores ${detractors}</span>
         </div>`
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

  const attValues = periods.map((p) =>
    participation
      .filter((item) => item.fecha_evento?.startsWith(p))
      .reduce((sum, item) => sum + item.asistencias, 0)
  );
  const satValues = periods.map((p) => {
    const recs = satisfaction.filter((item) => item.periodo_mes === p);
    return recs.length
      ? recs.reduce((s, r) => s + r.promedio_satisfaccion, 0) / recs.length
      : null;
  });

  description.textContent =
    'Curva violeta: asistencias por mes · Curva cian: satisfacción promedio (1–5).';

  if (!periods.length) {
    target.innerHTML = '<p>Sin periodos para mostrar.</p>';
    return;
  }

  const w = 560;
  const h = 215;
  const pad = { l: 38, r: 24, t: 18, b: 28 };
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const maxAtt = Math.max(...attValues, 1);
  const stepX = periods.length > 1 ? plotW / (periods.length - 1) : 0;

  const pts = attValues.map((val, i) => ({
    x: pad.l + (periods.length > 1 ? i * stepX : plotW / 2),
    y: pad.t + plotH - (val / maxAtt) * plotH,
    val,
    period: periods[i],
    label: periods[i].slice(2),
  }));

  const linePath = smoothPath(pts);
  const areaPath = `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${(pad.t + plotH).toFixed(1)} L${pts[0].x.toFixed(1)},${(pad.t + plotH).toFixed(1)} Z`;

  const satPts = satValues
    .map((val, i) =>
      val === null
        ? null
        : {
            x: pts[i].x,
            y: pad.t + plotH - (Math.max(0, Math.min(5, val)) / 5) * plotH,
            val,
            period: periods[i],
          }
    )
    .filter(Boolean);
  const satPath = smoothPath(satPts);

  const gridLines = [0, 0.5, 1]
    .map((ratio) => {
      const y = pad.t + plotH - ratio * plotH;
      return `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--line)" stroke-dasharray="4 4"/>
              <text x="${pad.l - 8}" y="${y + 3}" text-anchor="end" font-size="9.5" fill="var(--muted)">${Math.round(maxAtt * ratio)}</text>`;
    })
    .join('');

  target.innerHTML = `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Tendencia mensual de asistencias y satisfacción">
    <defs>
      <linearGradient id="horizonArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#5000bf" stop-opacity="0.28"/>
        <stop offset="100%" stop-color="#5000bf" stop-opacity="0.01"/>
      </linearGradient>
    </defs>
    ${gridLines}
    <path d="${areaPath}" fill="url(#horizonArea)"/>
    <path d="${linePath}" fill="none" stroke="var(--brand)" stroke-width="3" stroke-linecap="round"/>
    ${satPath ? `<path d="${satPath}" fill="none" stroke="var(--cyan)" stroke-width="2.5" stroke-linecap="round"/>` : ''}
    ${pts
      .map(
        (p) =>
          `<circle cx="${p.x}" cy="${p.y}" r="4.5" fill="var(--surface)" stroke="var(--brand)" stroke-width="2.5" data-tip="${p.period} · ${p.val} asistencias"/>
           <text x="${p.x}" y="${h - 8}" text-anchor="middle" font-size="9.5" font-weight="600" fill="var(--muted)">${p.label}</text>`
      )
      .join('')}
    ${satPts
      .map(
        (p) =>
          `<circle cx="${p.x}" cy="${p.y}" r="3.8" fill="var(--surface)" stroke="var(--cyan)" stroke-width="2.2" data-tip="${p.period} · Satisfacción ${p.val.toFixed(2)}"/>`
      )
      .join('')}
  </svg>`;
}

function renderOverviewLines(audience) {
  const lines = audience.lineas_oferta || [];
  const total = lines.reduce((s, item) => s + item.asistencias, 0);
  const leads = lines.reduce((s, item) => s + item.no_afiliados, 0);
  const max = Math.max(...lines.map((i) => i.asistencias), 1);
  byId('leads-ratio-tag').textContent = total
    ? `${Math.round((leads / total) * 100)}% leads`
    : '0% leads';
  byId('overview-lines-view').innerHTML = `<div class="bar-list">${
    lines
      .map((item) => {
        const afPct = (item.afiliados / max) * 100;
        const noAfPct = (item.no_afiliados / max) * 100;
        return `<div class="bar-row"><span>${escapeHtml(item.linea_oferta)}</span>
          <div class="track stacked-track">
            <div class="fill" style="width:${afPct}%" data-tip="${escapeHtml(item.linea_oferta)} · Afiliados: ${item.afiliados}"></div>
            <div class="fill lead" style="width:${noAfPct}%" data-tip="${escapeHtml(item.linea_oferta)} · Leads: ${item.no_afiliados}"></div>
          </div>
          <b>${item.asistencias}</b></div>`;
      })
      .join('') || '<p>Sin datos por línea.</p>'
  }</div><div class="nps-legend"><span><i style="background:var(--brand)"></i>Afiliados (${total - leads})</span><span><i style="background:var(--accent)"></i>Leads (${leads})</span></div>`;
}

function renderKamColumnChart(items, targetId) {
  const top = items.filter((k) => k.afiliados_activos > 0).slice(0, 8);
  if (!top.length) {
    byId(targetId).innerHTML = '<p>Sin datos por ejecutiva.</p>';
    return;
  }
  const w = 520;
  const h = 210;
  const pad = { l: 34, r: 12, t: 16, b: 34 };
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const maxVal = Math.max(...top.map((k) => k.afiliados_activos), 1);
  const groupW = plotW / top.length;
  const barW = Math.min(14, (groupW - 12) / 3);

  const grid = [0, 0.5, 1]
    .map((r) => {
      const y = pad.t + plotH - r * plotH;
      return `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--line)" stroke-dasharray="4 4"/>
              <text x="${pad.l - 6}" y="${y + 3}" text-anchor="end" font-size="9.5" fill="var(--muted)">${Math.round(maxVal * r)}</text>`;
    })
    .join('');

  const bars = top
    .map((k, i) => {
      const gx = pad.l + i * groupW + (groupW - barW * 3 - 6) / 2;
      const hAct = (k.afiliados_activos / maxVal) * plotH;
      const hSrv = (k.empresas_con_asistencia / maxVal) * plotH;
      const hVen = (k.vencen_90d / maxVal) * plotH;
      const lbl =
        k.responsable_nombre && k.responsable_nombre !== 'Sin asignar'
          ? k.responsable_nombre
          : k.kam_id.replace('KAM-', '');
      return `<rect x="${gx}" y="${pad.t + plotH - hAct}" width="${barW}" height="${hAct}" rx="6" fill="var(--brand)" data-tip="${escapeHtml(lbl)} · ${k.afiliados_activos} activos"/>
              <rect x="${gx + barW + 3}" y="${pad.t + plotH - hSrv}" width="${barW}" height="${hSrv}" rx="6" fill="var(--teal)" data-tip="${escapeHtml(lbl)} · ${k.empresas_con_asistencia} con asistencia (${k.porcentaje_en_servicios}%)"/>
              <rect x="${gx + (barW + 3) * 2}" y="${pad.t + plotH - hVen}" width="${barW}" height="${hVen}" rx="6" fill="var(--accent)" data-tip="${escapeHtml(lbl)} · ${k.vencen_90d} vencen en 90d"/>
              <text x="${gx + barW * 1.5 + 3}" y="${h - 12}" text-anchor="middle" font-size="9.5" font-weight="600" fill="var(--muted)">${escapeHtml(lbl.slice(0, 9))}</text>`;
    })
    .join('');

  byId(targetId).innerHTML = `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Comparativa por ejecutiva KAM">${grid}${bars}</svg>
    <div class="nps-legend"><span><i style="background:var(--brand)"></i>Activos</span><span><i style="background:var(--teal)"></i>Con asistencia</span><span><i style="background:var(--accent)"></i>Vencen 90d</span></div>`;
}

function renderExpirations(dist) {
  state.lastDistribution = dist;
  const target = byId('expirations-view');
  const desc = byId('expirations-description');
  if (!dist) return;

  if (state.expView === 'global') {
    const g = dist.vencimientos_global || {};
    const buckets = [
      { label: 'Vencidos', val: g.vencidos || 0, color: 'var(--danger)' },
      { label: '0–30 días', val: g.d0_30 || 0, color: 'var(--accent)' },
      { label: '31–60 días', val: g.d31_60 || 0, color: 'var(--brand)' },
      { label: '61–90 días', val: g.d61_90 || 0, color: 'var(--teal)' },
    ];
    desc.textContent = `Próximos 90 días: ${g.total_90d || 0} activos · Vencidos: ${g.vencidos || 0}.`;
    const w = 440;
    const h = 190;
    const pad = { l: 34, r: 16, t: 22, b: 30 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;
    const maxV = Math.max(...buckets.map((b) => b.val), 1);
    const colW = plotW / buckets.length;
    const barW = Math.min(44, colW * 0.48);

    const grid = [0, 0.5, 1]
      .map((r) => {
        const y = pad.t + plotH - r * plotH;
        return `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--line)" stroke-dasharray="4 4"/>
                <text x="${pad.l - 6}" y="${y + 3}" text-anchor="end" font-size="9.5" fill="var(--muted)">${Math.round(maxV * r)}</text>`;
      })
      .join('');

    const bars = buckets
      .map((b, i) => {
        const x = pad.l + i * colW + (colW - barW) / 2;
        const bh = (b.val / maxV) * plotH;
        const y = pad.t + plotH - bh;
        return `<rect x="${x}" y="${pad.t}" width="${barW}" height="${plotH}" rx="10" fill="var(--canvas)"/>
                <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="10" fill="${b.color}" data-tip="${b.label}: ${b.val} empresas"/>
                <text x="${x + barW / 2}" y="${Math.max(y - 6, 13)}" text-anchor="middle" font-size="11" font-weight="800" fill="var(--ink)">${b.val}</text>
                <text x="${x + barW / 2}" y="${h - 9}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--muted)">${b.label}</text>`;
      })
      .join('');

    target.innerHTML = `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Curva de vencimientos 30, 60 y 90 días">${grid}${bars}</svg>`;
    return;
  }

  const kams = (dist.vencimientos_por_kam || []).slice(0, 8);
  const max = Math.max(...kams.map((k) => k.total_90d + k.vencidos), 1);
  desc.textContent = 'Por KAM: vencidos (rojo), 0–30d (naranja), 31–60d (violeta), 61–90d (verde).';
  target.innerHTML = `<div class="bar-list">${
    kams
      .map((k) => {
        const lbl =
          k.responsable_nombre && k.responsable_nombre !== 'Sin asignar'
            ? k.responsable_nombre
            : k.kam_id;
        return `<div class="bar-row"><span title="${escapeHtml(lbl)}">${escapeHtml(lbl)}</span>
          <div class="track stacked-track">
            <div class="fill" style="width:${(k.vencidos / max) * 100}%;background:var(--danger);border-radius:0" data-tip="${escapeHtml(lbl)} · Vencidos: ${k.vencidos}"></div>
            <div class="fill lead" style="width:${(k.d0_30 / max) * 100}%;border-radius:0" data-tip="${escapeHtml(lbl)} · 0-30d: ${k.d0_30}"></div>
            <div class="fill" style="width:${(k.d31_60 / max) * 100}%;border-radius:0" data-tip="${escapeHtml(lbl)} · 31-60d: ${k.d31_60}"></div>
            <div class="fill teal" style="width:${(k.d61_90 / max) * 100}%;border-radius:0" data-tip="${escapeHtml(lbl)} · 61-90d: ${k.d61_90}"></div>
          </div>
          <b>${k.total_90d}</b></div>`;
      })
      .join('') || '<p>Sin vencimientos en los próximos 90 días.</p>'
  }</div>`;
}

function renderDistribution(dist) {
  if (!dist) return;
  const target = byId('distribution-view');
  const desc = byId('distribution-description');

  if (state.distView === 'sector') {
    const items = dist.por_sector || [];
    const max = Math.max(...items.map((i) => i.empresas), 1);
    desc.textContent = `Top sectores económicos sobre ${dist.total_activos} afiliados activos.`;
    target.innerHTML = `<div class="bar-list">${
      items
        .map(
          (i) =>
            `<div class="bar-row"><span title="${escapeHtml(i.sector)}">${escapeHtml(i.sector)}</span><div class="track"><div class="fill" style="width:${(i.empresas / max) * 100}%" data-tip="${escapeHtml(i.sector)}: ${i.empresas} (${i.porcentaje}%)"></div></div><b>${i.empresas} <small>(${i.porcentaje}%)</small></b></div>`
        )
        .join('') || '<p>Sin datos de sectores.</p>'
    }</div>`;
    return;
  }

  const items = state.distView === 'nivel' ? dist.por_nivel || [] : dist.por_tamano || [];
  const labelKey = state.distView === 'nivel' ? 'nivel' : 'tamano';
  const total = items.reduce((s, i) => s + i.empresas, 0);
  const colors = ['#5000bf', '#39b8ff', '#05cd99', '#ff5a00', '#ffb547', '#9b82ff', '#8f9bba'];
  let offset = 0;
  const slices = items
    .map((item, idx) => {
      const share = total ? item.empresas / total : 0;
      const c = `<circle cx="50" cy="50" r="38" pathLength="100" stroke="${colors[idx % colors.length]}" stroke-dasharray="${share * 100} ${100 - share * 100}" stroke-dashoffset="${-offset}" data-tip="${escapeHtml(item[labelKey])}: ${item.empresas} (${item.porcentaje}%)"/>`;
      offset += share * 100;
      return c;
    })
    .join('');

  desc.textContent =
    state.distView === 'nivel'
      ? `Distribución por nivel de membresía (${total} activos).`
      : `Distribución por tamaño empresarial (${total} activos).`;
  target.innerHTML = total
    ? `<div class="donut-layout"><svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Distribución de activos"><circle class="donut-base" cx="50" cy="50" r="38"/>${slices}<text x="50" y="48">${total}</text><text x="50" y="59">activos</text></svg>
       <ul class="legend">${items
         .map(
           (item, idx) =>
             `<li><i style="background:${colors[idx % colors.length]}"></i><span>${escapeHtml(item[labelKey])}</span><b>${item.empresas} (${item.porcentaje}%)</b></li>`
         )
         .join('')}</ul></div>`
    : '<p>Sin datos para estos filtros.</p>';
}

function renderParticipation(items) {
  if (state.chart === 'bars') {
    const top = [...items].sort((a, b) => b.asistencias - a.asistencias).slice(0, 10);
    const max = Math.max(...top.map((item) => item.asistencias), 1);
    byId('participation-view').innerHTML = `<div class="bar-list">${
      top
        .map((item) => {
          const af = item.asistentes_afiliados ?? item.asistencias;
          const noAf = item.asistentes_no_afiliados ?? 0;
          return `<div class="bar-row"><span title="${escapeHtml(item.nombre_evento)}">${escapeHtml(item.nombre_evento || 'Sin nombre')}</span>
            <div class="track stacked-track">
              <div class="fill" style="width:${(af / max) * 100}%" data-tip="${escapeHtml(item.nombre_evento)} · Afiliados: ${af}"></div>
              <div class="fill lead" style="width:${(noAf / max) * 100}%" data-tip="${escapeHtml(item.nombre_evento)} · Leads: ${noAf}"></div>
            </div>
            <b>${item.asistencias}</b></div>`;
        })
        .join('') || '<p>Sin asistencias para estos filtros.</p>'
    }</div><div class="nps-legend"><span><i style="background:var(--brand)"></i>Afiliados</span><span><i style="background:var(--accent)"></i>Leads</span></div>`;
    return;
  }

  if (state.chart === 'donut') {
    const top = [...items].sort((a, b) => b.asistencias - a.asistencias).slice(0, 7);
    const total = top.reduce((sum, item) => sum + item.asistencias, 0);
    const colors = ['#5000bf', '#ff5a00', '#05cd99', '#39b8ff', '#ffb547', '#9b82ff', '#ee5d50'];
    let offset = 0;
    const slices = top
      .map((item, idx) => {
        const share = total ? item.asistencias / total : 0;
        const circle = `<circle cx="50" cy="50" r="38" pathLength="100" stroke="${colors[idx % colors.length]}" stroke-dasharray="${share * 100} ${100 - share * 100}" stroke-dashoffset="${-offset}" data-tip="${escapeHtml(item.nombre_evento)}: ${item.asistencias}"/>`;
        offset += share * 100;
        return circle;
      })
      .join('');
    byId('participation-view').innerHTML = total
      ? `<div class="donut-layout"><svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Distribución de asistencias"><circle class="donut-base" cx="50" cy="50" r="38"/>${slices}<text x="50" y="48">${total}</text><text x="50" y="59">top 7</text></svg>
         <ul class="legend">${top
           .map(
             (item, idx) =>
               `<li><i style="background:${colors[idx % colors.length]}"></i><span title="${escapeHtml(item.nombre_evento)}">${escapeHtml(item.nombre_evento || 'Evento')}</span><b>${item.asistencias}</b></li>`
           )
           .join('')}</ul></div>`
      : '<p>Sin asistencias para estos filtros.</p>';
    return;
  }

  byId('participation-view').innerHTML = `<div class="table-wrap bounded"><table><thead><tr><th>Evento</th><th>Línea</th><th>Total</th><th>Afiliados</th><th>Leads</th><th>Empresas</th></tr></thead><tbody>${
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.nombre_evento || '—')}</td><td>${escapeHtml(item.linea_oferta || '—')}</td><td>${item.asistencias}</td><td>${item.asistentes_afiliados ?? '—'}</td><td>${item.asistentes_no_afiliados ?? '—'}</td><td>${item.empresas_distintas}</td></tr>`
      )
      .join('') || '<tr><td colspan="6">Sin asistencias para estos filtros.</td></tr>'
  }</tbody></table></div>`;
}

function renderAudience(data) {
  const target = byId('audience-view');
  const desc = byId('audience-description');

  if (state.audience === 'roles') {
    const items = (data.niveles_cargo || []).slice(0, 7);
    const total = items.reduce((s, i) => s + i.asistencias, 0);
    const colors = ['#5000bf', '#05cd99', '#39b8ff', '#ff5a00', '#ffb547', '#9b82ff', '#8f9bba'];
    let offset = 0;
    const slices = items
      .map((item, idx) => {
        const share = total ? item.asistencias / total : 0;
        const c = `<circle cx="50" cy="50" r="38" pathLength="100" stroke="${colors[idx % colors.length]}" stroke-dasharray="${share * 100} ${100 - share * 100}" stroke-dashoffset="${-offset}" data-tip="${escapeHtml(item.nivel_cargo)}: ${item.asistencias}"/>`;
        offset += share * 100;
        return c;
      })
      .join('');
    desc.textContent = 'Distribución jerárquica de los participantes en eventos Silver.';
    target.innerHTML = total
      ? `<div class="donut-layout"><svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Cargos"><circle class="donut-base" cx="50" cy="50" r="38"/>${slices}<text x="50" y="48">${total}</text><text x="50" y="59">cargos</text></svg>
         <ul class="legend">${items
           .map(
             (item, idx) =>
               `<li><i style="background:${colors[idx % colors.length]}"></i><span>${escapeHtml(item.nivel_cargo)}</span><b>${item.asistencias}</b></li>`
           )
           .join('')}</ul></div>`
      : '<p>Sin datos de audiencia.</p>';
    return;
  }

  const items = state.audience === 'lines' ? data.lineas_oferta || [] : data.modalidades || [];
  const labelKey = state.audience === 'lines' ? 'linea_oferta' : 'modalidad';
  const max = Math.max(...items.map((item) => item.asistencias), 1);
  desc.textContent =
    state.audience === 'lines'
      ? 'Afiliados (violeta) vs. Leads (naranja) por línea 2027.'
      : 'Afiliados (violeta) vs. Leads (naranja) por modalidad.';
  target.innerHTML = `<div class="bar-list">${
    items
      .map((item) => {
        const afPct = (item.afiliados / max) * 100;
        const noAfPct = (item.no_afiliados / max) * 100;
        return `<div class="bar-row"><span>${escapeHtml(item[labelKey])}</span>
          <div class="track stacked-track">
            <div class="fill" style="width:${afPct}%" data-tip="Afiliados: ${item.afiliados}"></div>
            <div class="fill lead" style="width:${noAfPct}%" data-tip="Leads: ${item.no_afiliados}"></div>
          </div><b>${item.asistencias}</b></div>`;
      })
      .join('') || '<p>Sin datos.</p>'
  }</div>`;
}

function renderPillars(data) {
  const items = data.pilares || [];
  byId('pillars-description').textContent = `Adopción sobre ${data.total_activos} afiliados activos.`;
  const pctMuj = data.porcentaje_mujeres_promedio;
  byId('women-share').textContent =
    pctMuj !== null ? `${pctMuj}% mujeres (n=${data.empresas_con_dato_mujeres})` : 'Sin dato diversidad';

  const gaugeVal = pctMuj ?? 0;
  const gaugeSvg = `<div class="gauge-box">
    <svg class="donut" style="width:98px" viewBox="0 0 100 100" role="img" aria-label="Participación femenina">
      <circle class="donut-base" cx="50" cy="50" r="38"/>
      <circle cx="50" cy="50" r="38" pathLength="100" stroke="var(--accent)" stroke-dasharray="${gaugeVal} ${100 - gaugeVal}"/>
      <text x="50" y="53">${pctMuj !== null ? `${pctMuj}%` : '—'}</text>
    </svg>
    <small>Mujeres promedio</small>
  </div>`;

  const bars = `<div class="bar-list">${items
    .map(
      (item) =>
        `<div class="bar-row"><span>${escapeHtml(item.nombre)}</span><div class="track"><div class="fill teal" style="width:${item.porcentaje}%" data-tip="${escapeHtml(item.nombre)}: ${item.empresas} (${item.porcentaje}%)"></div></div><b>${item.empresas} <small>(${item.porcentaje}%)</small></b></div>`
    )
    .join('')}</div>`;

  byId('pillars-view').innerHTML = `<div class="pillars-wrap">${gaugeSvg}${bars}</div>`;
}

function renderKamsSection(items) {
  renderKamColumnChart(items, 'overview-kams-chart');
  if (state.kamView === 'chart') {
    renderKamColumnChart(items, 'kams-view');
    return;
  }
  byId('kams-view').innerHTML = `<div class="table-wrap bounded"><table><thead><tr><th>KAM</th><th>Ejecutiva</th><th>Activos</th><th>Vencen 90d</th><th>Con asist.</th><th>% Serv.</th><th>Asist.</th><th>Renov.</th></tr></thead><tbody>${
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.kam_id)}</td><td>${escapeHtml(item.responsable_nombre || '—')}</td><td>${item.afiliados_activos}</td><td>${item.vencen_90d}</td><td>${item.empresas_con_asistencia}</td><td>${item.porcentaje_en_servicios}%</td><td>${item.asistencias_totales}</td><td>${item.renovaciones}</td></tr>`
      )
      .join('') || '<tr><td colspan="8">Sin datos.</td></tr>'
  }</tbody></table></div>`;
}

function renderDimensionsRadar(data) {
  const rows = data.por_modalidad || [];
  byId('topics-count').textContent = `${data.total_con_temarios} temarios`;

  const axes = [
    { key: 'locacion_plataforma', label: 'Locación / Plat.' },
    { key: 'convocatoria_publicidad', label: 'Convocatoria' },
    { key: 'conferencistas', label: 'Conferencistas' },
    { key: 'relevancia_temas', label: 'Relevancia' },
  ];
  const cx = 145;
  const cy = 105;
  const rMax = 72;
  const angles = axes.map((_, i) => -Math.PI / 2 + (i * 2 * Math.PI) / axes.length);

  const rings = [1, 2, 3, 4, 5]
    .map((lvl) => {
      const r = (lvl / 5) * rMax;
      const pts = angles.map((a) => `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`).join(' ');
      return `<polygon points="${pts}" fill="none" stroke="var(--line)" stroke-width="1"/>`;
    })
    .join('');

  const spokes = angles
    .map((a, i) => {
      const x2 = cx + rMax * Math.cos(a);
      const y2 = cy + rMax * Math.sin(a);
      const lx = cx + (rMax + 24) * Math.cos(a);
      const ly = cy + (rMax + 15) * Math.sin(a);
      return `<line x1="${cx}" y1="${cy}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="var(--line)"/>
              <text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="9.5" font-weight="600" fill="var(--muted)">${axes[i].label}</text>`;
    })
    .join('');

  const palette = { Presencial: '#5000bf', Virtual: '#39b8ff' };
  const polygons = rows
    .map((row, idx) => {
      const color = palette[row.modalidad] || (idx === 0 ? '#5000bf' : '#05cd99');
      const pts = axes
        .map((ax, i) => {
          const val = Math.max(0, Math.min(5, Number(row[ax.key] || 0)));
          const r = (val / 5) * rMax;
          return `${(cx + r * Math.cos(angles[i])).toFixed(1)},${(cy + r * Math.sin(angles[i])).toFixed(1)}`;
        })
        .join(' ');
      return `<polygon points="${pts}" fill="${color}" fill-opacity="0.18" stroke="${color}" stroke-width="2.4" data-tip="${escapeHtml(row.modalidad)} · Promedio ${row.promedio_general}"/>`;
    })
    .join('');

  byId('dimensions-radar').innerHTML = rows.length
    ? `<svg class="svg-chart" style="max-height:210px" viewBox="0 0 290 210" role="img" aria-label="Radar de dimensiones de satisfacción">${rings}${spokes}${polygons}</svg>
       <div class="nps-legend">${rows
         .map((r, i) => `<span><i style="background:${palette[r.modalidad] || (i === 0 ? '#5000bf' : '#05cd99')}"></i>${escapeHtml(r.modalidad)} (${r.promedio_general})</span>`)
         .join('')}</div>`
    : '<p>Sin encuestas para este periodo.</p>';

  byId('dimensions-table').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Modalidad</th><th>Resp.</th><th>Loc./Plat.</th><th>Convoc.</th><th>Confer.</th><th>Temas</th></tr></thead><tbody>${
    rows
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.modalidad)}</td><td>${item.respuestas}</td><td>${item.locacion_plataforma}</td><td>${item.convocatoria_publicidad}</td><td>${item.conferencistas}</td><td>${item.relevancia_temas}</td></tr>`
      )
      .join('') || '<tr><td colspan="6">Sin datos.</td></tr>'
  }</tbody></table></div>`;

  const topics = data.temarios_recientes || [];
  byId('topics-list').innerHTML =
    topics
      .map(
        (item) =>
          `<li>${escapeHtml(item.temario)}<small>${escapeHtml(item.modalidad || 'Encuesta')} · ${escapeHtml(item.fecha || 'Sin fecha')}</small></li>`
      )
      .join('') || '<li>Sin temarios sugeridos en este periodo.</li>';
}

function renderEngagementRisk(data) {
  state.lastRisk = data;
  if (!data) return;
  const res = data.resumen || {};
  const total = res.total_activos || 0;
  const sinP = res.sin_participacion || 0;
  const mono = res.monocontacto || 0;
  const multi = res.multicontacto || 0;

  byId('avg-people-tag').textContent = `${res.promedio_personas_participantes || 0} pers./empresa`;
  byId('engagement-health-bar').innerHTML = total
    ? `<div class="stacked">
         <i class="detractor" style="width:${(sinP / total) * 100}%" data-tip="Sin participación: ${sinP}"></i>
         <i class="neutral" style="width:${(mono / total) * 100}%" data-tip="Monocontacto: ${mono}"></i>
         <i class="promoter" style="width:${(multi / total) * 100}%" data-tip="Multicontacto: ${multi}"></i>
       </div>
       <div class="nps-legend">
         <span><i class="detractor"></i>Pagan y no participan: <b>${sinP}</b> (${Math.round((sinP / total) * 100)}%)</span>
         <span><i class="neutral"></i>Monocontacto (1 pers.): <b>${mono}</b> (${Math.round((mono / total) * 100)}%)</span>
         <span><i class="promoter"></i>Multicontacto (2+ pers.): <b>${multi}</b> (${Math.round((multi / total) * 100)}%)</span>
       </div>`
    : '<p>Sin afiliados activos en el filtro actual.</p>';

  const list =
    state.riskTab === 'sin_participacion'
      ? data.lista_sin_participacion || []
      : data.lista_monocontacto || [];

  byId('risk-body').innerHTML =
    list
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.id_empresa)}</td><td>${escapeHtml(item.kam_nombre || item.kam_id || '—')}</td><td>${escapeHtml(item.nivel_membresia || '—')}</td><td>${escapeHtml(item.sector_economico || '—')}</td><td>${escapeHtml(item.ciudad || '—')}</td><td>${escapeHtml(item.fecha_expiracion || '—')}</td><td>${item.personas_participantes}</td><td>${item.asistencias}</td></tr>`
      )
      .join('') || '<tr><td colspan="8">Sin empresas en este segmento.</td></tr>';

  const kam = byId('kam-filter').value;
  const level = byId('level-filter').value;
  const sector = byId('sector-filter').value;
  const country = byId('country-filter').value;
  const qs = query({ kam_id: kam, nivel_membresia: level, sector, pais: country });
  byId('export-risk-btn').href = `${endpoints.exportCsv}/${state.riskTab}${qs}`;
}

function renderPortfolioRows(items) {
  const term = (byId('portfolio-search')?.value || '').trim().toLowerCase();
  const filtered = term
    ? items.filter((item) =>
        [item.id_empresa, item.kam_nombre, item.kam_id, item.sector_economico, item.ciudad, item.nivel_membresia]
          .filter(Boolean)
          .some((val) => String(val).toLowerCase().includes(term))
      )
    : items;
  byId('portfolio-body').innerHTML =
    filtered
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.id_empresa)}</td><td>${escapeHtml(item.kam_nombre || item.kam_id || '—')}</td><td>${escapeHtml(item.nivel_membresia || '—')}</td><td>${escapeHtml(item.sector_economico || '—')}</td><td>${escapeHtml(item.tamano_empresa || '—')}</td><td>${escapeHtml(item.estado_membresia || '—')}</td><td>${escapeHtml(item.ciudad || '—')}</td><td>${escapeHtml(item.fecha_miembro_desde || '—')}</td><td>${escapeHtml(item.fecha_expiracion || '—')}</td></tr>`
      )
      .join('') || '<tr><td colspan="9">Sin resultados para estos filtros.</td></tr>';
}

function renderPortfolio(data) {
  state.portfolioItems = data.items || [];
  byId('portfolio-total').textContent = `${data.total} empresas`;
  renderPortfolioRows(state.portfolioItems);
}

function renderSatisfaction(items) {
  byId('satisfaction-body').innerHTML =
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.periodo_mes || 'Sin periodo')}</td><td>${item.respuestas}</td><td>${item.promedio_satisfaccion}</td><td>${item.nps_adaptado_1_5}</td></tr>`
      )
      .join('') || '<tr><td colspan="4">Sin encuestas para este periodo.</td></tr>';
}

function renderSegments(data) {
  const rows = [
    ...data.vencimientos_proximos.slice(0, 2).map(
      (row) => `Contactar ${escapeHtml(row.id_empresa)}<small>Vence ${escapeHtml(row.fecha_expiracion)} · ${escapeHtml(row.kam_id)}</small>`
    ),
    ...data.afiliados_sin_participacion.slice(0, 2).map(
      (row) => `Activar ${escapeHtml(row.id_empresa)}<small>Sin participación · ${escapeHtml(row.kam_id)}</small>`
    ),
    ...data.asistentes_no_afiliados.slice(0, 2).map(
      (row) => `Convertir lead ${escapeHtml(row.id_persona)}<small>Evento #${escapeHtml(row.id_evento)}</small>`
    ),
  ];
  byId('segments-list').innerHTML =
    rows.map((row) => `<li>${row}</li>`).join('') || '<li>Sin acciones pendientes.</li>';
}

function updateActiveFiltersBadge() {
  const selects = [...document.querySelectorAll('.filters select')];
  const count = selects.filter((el) => el.value).length;
  byId('active-filters-badge').textContent = String(count);
}

async function refresh() {
  updateActiveFiltersBadge();
  const period = byId('period-filter').value;
  const kam = byId('kam-filter').value;
  const level = byId('level-filter').value;
  const sector = byId('sector-filter').value;
  const size = byId('size-filter').value;
  const membershipStatus = byId('membership-status-filter').value;
  const country = byId('country-filter').value;
  const city = byId('city-filter').value;
  const eventCity = byId('event-city-filter').value;
  const line = byId('line-filter').value;
  const modality = byId('modality-filter').value;
  const dates = periodBounds(period);
  byId('filter-status').textContent = 'Actualizando…';

  try {
    const [
      portfolio,
      renewals,
      participation,
      audience,
      pillars,
      kams,
      distribution,
      engagementRisk,
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
            pais: country,
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
      request(
        endpoints.pillars + query({ kam_id: kam, nivel_membresia: level, sector, pais: country })
      ),
      request(endpoints.kams),
      request(
        endpoints.distribution +
          query({
            kam_id: kam,
            nivel_membresia: level,
            sector,
            tamano_empresa: size,
            ciudad: city,
            pais: country,
          })
      ),
      request(
        endpoints.engagementRisk +
          query({ kam_id: kam, nivel_membresia: level, sector, pais: country })
      ),
      request(endpoints.satisfaction + query(dates)),
      request(endpoints.dimensions + query(dates)),
      request(endpoints.segments),
    ]);

    renderPortfolio(portfolio);
    renderParticipation(participation);
    renderAudience(audience);
    renderOverviewLines(audience);
    renderPillars(pillars);
    renderKamsSection(kams);
    renderExpirations(distribution);
    renderDistribution(distribution);
    renderEngagementRisk(engagementRisk);
    renderSatisfaction(satisfaction);
    renderDimensionsRadar(dimensions);
    renderTrendAreaChart(participation, satisfaction);
    renderSegments(segments);

    byId('renewal-count').textContent = renewals.reduce((sum, item) => sum + item.renovaciones, 0);
    const totalAtt = participation.reduce((sum, item) => sum + item.asistencias, 0);
    const leadsAtt = participation.reduce((sum, item) => sum + (item.asistentes_no_afiliados || 0), 0);
    byId('attendance-count').textContent = totalAtt;
    byId('attendance-detail').textContent = `${totalAtt - leadsAtt} afiliados · ${leadsAtt} leads`;
    const activeSatisfaction = satisfaction.length
      ? satisfaction.reduce((sum, item) => sum + item.promedio_satisfaccion, 0) / satisfaction.length
      : 0;
    byId('satisfaction-score').textContent = activeSatisfaction.toFixed(2);
    byId('filter-status').textContent = 'En línea';
  } catch (error) {
    byId('filter-status').textContent = 'Error al cargar';
  }
}

async function initialize() {
  try {
    const [overview, affiliateFilters, analyticsFilters] = await Promise.all([
      request(endpoints.overview),
      request(endpoints.affiliateFilters),
      request(endpoints.analyticsFilters),
    ]);
    byId('data-date').textContent = `Corte ${overview.fecha_referencia}`;
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
    appendOptions(byId('country-filter'), affiliateFilters.paises || []);
    appendOptions(byId('city-filter'), affiliateFilters.ciudades);
    appendOptions(byId('event-city-filter'), analyticsFilters.ciudades_evento || []);
    appendOptions(byId('line-filter'), analyticsFilters.lineas_oferta || []);
    appendOptions(byId('modality-filter'), analyticsFilters.modalidades_evento || []);
    await refresh();
  } catch (error) {
    byId('filter-status').textContent = 'Error al inicializar';
  }
}

/* EVENT LISTENERS */
byId('toggle-filters-btn').addEventListener('click', () => {
  const drawer = byId('filters-drawer');
  const open = drawer.hidden;
  drawer.hidden = !open;
  byId('toggle-filters-btn').setAttribute('aria-expanded', String(open));
});

document.querySelectorAll('[data-tab]').forEach((btn) =>
  btn.addEventListener('click', () => setActiveTab(btn.dataset.tab))
);
document.querySelectorAll('[data-tab-target]').forEach((el) =>
  el.addEventListener('click', (e) => {
    e.preventDefault();
    setActiveTab(el.dataset.tabTarget);
  })
);
document.querySelectorAll('.filters select').forEach((el) => el.addEventListener('change', refresh));
byId('clear-filters').addEventListener('click', () => {
  document.querySelectorAll('.filters select').forEach((el) => {
    el.value = '';
  });
  refresh();
});
byId('portfolio-search')?.addEventListener('input', () => renderPortfolioRows(state.portfolioItems));

document.querySelectorAll('[data-chart]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-chart]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.chart = btn.dataset.chart;
    refresh();
  })
);
document.querySelectorAll('[data-audience]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-audience]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.audience = btn.dataset.audience;
    refresh();
  })
);
document.querySelectorAll('[data-insight]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-insight]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.insight = btn.dataset.insight;
    refresh();
  })
);
document.querySelectorAll('[data-kam-view]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-kam-view]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.kamView = btn.dataset.kamView;
    refresh();
  })
);
document.querySelectorAll('[data-exp-view]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-exp-view]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.expView = btn.dataset.expView;
    renderExpirations(state.lastDistribution);
  })
);
document.querySelectorAll('[data-dist-view]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-dist-view]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.distView = btn.dataset.distView;
    renderDistribution(state.lastDistribution);
  })
);
document.querySelectorAll('[data-risk-tab]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-risk-tab]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.riskTab = btn.dataset.riskTab;
    renderEngagementRisk(state.lastRisk);
  })
);

function applyTheme(dark) {
  document.documentElement.dataset.theme = dark ? 'dark' : '';
  localStorage.setItem('actho-theme', dark ? 'dark' : 'light');
  byId('theme-icon').innerHTML = dark
    ? '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
    : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
}

applyTheme(localStorage.getItem('actho-theme') === 'dark');
byId('theme-toggle').addEventListener('click', () => {
  applyTheme(document.documentElement.dataset.theme !== 'dark');
});

initialize();
