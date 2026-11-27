const endpoints = {
  overview: '/dashboard/overview',
  filters: '/dashboard/filters',
  evolution: '/dashboard/membership-evolution',
  segmentKpis: '/dashboard/segment-kpis',
  eventKpis: '/dashboard/event-kpis',
  commSegments: '/dashboard/communication-segments',
  exportSegment: '/dashboard/export',
  portfolio: '/affiliates/silver/portfolio',
  renewals: '/affiliates/silver/renewals',
  pillars: '/affiliates/silver/pillars',
  kams: '/affiliates/silver/kam-summary',
  distribution: '/affiliates/silver/distribution',
  participation: '/analytics/silver/participation',
  audience: '/analytics/silver/audience',
  satisfaction: '/analytics/silver/satisfaction',
  dimensions: '/dashboard/satisfaction-topics',
  mlStatus: '/ml/status',
  mlFidelidad: '/ml/fidelidad',
  mlPublico: '/ml/publico-eventos',
  mlUso: '/ml/uso-permanencia',
  mlRiesgo: '/ml/riesgo-renovacion',
};

const state = {
  tab: 'overview',
  chart: 'bars',
  insight: 'memberships',
  audience: 'roles',
  kamView: 'chart',
  expView: 'global',
  distView: 'nivel',
  evKpiView: 'linea',
  segDim: 'sector_economico',
  commSegment: 'AFILIADOS_SIN_PARTICIPACION',
  habeasOnly: false,
  portfolioItems: [],
  lastDistribution: null,
  lastEvolution: null,
  lastParticipation: [],
  lastSatisfaction: [],
  lastEventKpis: null,
  lastKams: [],
};

const byId = (id) => document.getElementById(id);
const request = async (url) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(url);
  return response.json();
};

const appendOptions = (element, values, formatter = (v) => v) => {
  if (!element || !Array.isArray(values)) return;
  values.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = formatter(value);
    element.append(option);
  });
};

const periodBounds = (period) =>
  period ? { fecha_desde: `${period}-01`, fecha_hasta: `${period}-31` } : {};

function query(params) {
  const clean = Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined);
  return clean.length ? `?${new URLSearchParams(clean)}` : '';
}

function escapeHtml(text) {
  return String(text ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/* FLOATING TOOLTIP */
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
  const isEtl = tabName === 'etl';
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

  const filterBtn = byId('toggle-filters-btn');
  const filterDrawer = byId('filters-drawer');
  const kpiGrid = document.querySelector('.metric-grid');
  if (filterBtn) filterBtn.hidden = isEtl;
  if (filterDrawer && isEtl) {
    filterDrawer.hidden = true;
    filterBtn?.setAttribute('aria-expanded', 'false');
  }
  if (kpiGrid) kpiGrid.hidden = isEtl;

  if (isEtl) {
    window.dispatchEvent(new CustomEvent('etl:activate'));
  }
}

function semPill(val) {
  const s = val || 'NO_APLICA';
  return `<span class="sem-pill ${escapeHtml(s)}">${escapeHtml(s)}</span>`;
}

/* 1. SEMAPHORE OVERVIEW */
function renderSemaphoreOverview(overview) {
  const sem = overview.semaforo_riesgo || { ROJO: 0, AMARILLO: 0, VERDE: 0 };
  const total = (sem.ROJO || 0) + (sem.AMARILLO || 0) + (sem.VERDE || 0);
  byId('semaphore-rate-tag').textContent = `Permanencia ${overview.tasa_retencion_historica_pct || 0}%`;
  if (!total) {
    byId('semaphore-overview').innerHTML = '<p>Sin afiliados activos evaluados.</p>';
    return;
  }
  const pR = ((sem.ROJO / total) * 100).toFixed(1);
  const pA = ((sem.AMARILLO / total) * 100).toFixed(1);
  const pV = ((sem.VERDE / total) * 100).toFixed(1);
  byId('semaphore-overview').innerHTML = `
    <div class="stacked">
      <i style="width:${pR}%;background:var(--danger)" data-tip="Riesgo ROJO: ${sem.ROJO} (${pR}%)"></i>
      <i style="width:${pA}%;background:var(--gold)" data-tip="Riesgo AMARILLO: ${sem.AMARILLO} (${pA}%)"></i>
      <i style="width:${pV}%;background:var(--teal)" data-tip="Saludable VERDE: ${sem.VERDE} (${pV}%)"></i>
    </div>
    <div class="sem-grid">
      <div class="sem-box rojo"><strong>${sem.ROJO}</strong><span>Rojo Crítico (${pR}%)</span></div>
      <div class="sem-box amarillo"><strong>${sem.AMARILLO}</strong><span>Amarillo (${pA}%)</span></div>
      <div class="sem-box verde"><strong>${sem.VERDE}</strong><span>Verde Saludable (${pV}%)</span></div>
    </div>
    <div class="nps-legend">
      <span>Ex-afiliados CRM: <b>${overview.ex_afiliados || 0}</b></span>
      <span>Prospectos eventos: <b>${overview.prospectos_leads || 0}</b></span>
    </div>`;
}

/* 2. DYNAMIC INSIGHT PANEL (MEMBERSHIP EVOLUTION / TREND / LIKERT) */
function renderInsightPanel() {
  const target = byId('insight-view');
  const description = byId('insight-description');
  const participation = state.lastParticipation || [];
  const satisfaction = state.lastSatisfaction || [];
  const evo = state.lastEvolution;

  if (state.insight === 'memberships') {
    const rows = (evo?.serie_mensual || []).slice(-14);
    const res = evo?.resumen || {};
    description.textContent = `Altas (verde): ${res.altas_totales || 0} · Renovaciones (violeta): ${res.renovaciones_totales || 0} · Retiros (rojo): ${res.retiros_totales || 0}.`;
    if (!rows.length) {
      target.innerHTML = '<p>Sin movimientos mensuales registrados para este filtro.</p>';
      return;
    }
    const w = 560;
    const h = 215;
    const pad = { l: 36, r: 18, t: 18, b: 30 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;
    const maxV = Math.max(
      ...rows.flatMap((r) => [r.altas_nuevas, r.renovaciones_efectivas, r.retiros_cancelaciones]),
      1
    );
    const grpW = plotW / rows.length;
    const bw = Math.min(10, Math.max(4, (grpW - 8) / 3));

    const grid = [0, 0.5, 1]
      .map((ratio) => {
        const y = pad.t + plotH - ratio * plotH;
        return `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="var(--line)" stroke-dasharray="4 4"/>
                <text x="${pad.l - 6}" y="${y + 3}" text-anchor="end" font-size="9.5" fill="var(--muted)">${Math.round(maxV * ratio)}</text>`;
      })
      .join('');

    const bars = rows
      .map((r, i) => {
        const gx = pad.l + i * grpW + (grpW - bw * 3 - 4) / 2;
        const hA = (r.altas_nuevas / maxV) * plotH;
        const hR = (r.renovaciones_efectivas / maxV) * plotH;
        const hC = (r.retiros_cancelaciones / maxV) * plotH;
        return `<rect x="${gx}" y="${pad.t + plotH - hA}" width="${bw}" height="${hA}" rx="3" fill="var(--teal)" data-tip="${r.periodo_mes} · Altas nuevas: ${r.altas_nuevas}"/>
                <rect x="${gx + bw + 2}" y="${pad.t + plotH - hR}" width="${bw}" height="${hR}" rx="3" fill="var(--brand)" data-tip="${r.periodo_mes} · Renovaciones: ${r.renovaciones_efectivas}"/>
                <rect x="${gx + (bw + 2) * 2}" y="${pad.t + plotH - hC}" width="${bw}" height="${hC}" rx="3" fill="var(--danger)" data-tip="${r.periodo_mes} · Retiros: ${r.retiros_cancelaciones}"/>
                <text x="${gx + bw * 1.5 + 2}" y="${h - 9}" text-anchor="middle" font-size="9" font-weight="600" fill="var(--muted)">${escapeHtml(r.periodo_mes.slice(2))}</text>`;
      })
      .join('');

    target.innerHTML = `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Evolución mensual de membresías">${grid}${bars}</svg>
      <div class="nps-legend">
        <span><i style="background:var(--teal)"></i>Altas nuevas</span>
        <span><i style="background:var(--brand)"></i>Renovaciones</span>
        <span><i style="background:var(--danger)"></i>Retiros / Cancelaciones</span>
      </div>`;
    return;
  }

  if (state.insight === 'nps') {
    const total = satisfaction.reduce((sum, item) => sum + item.respuestas, 0);
    const alta = satisfaction.reduce((sum, item) => sum + (item.promotores || 0), 0);
    const baja = satisfaction.reduce((sum, item) => sum + (item.detractores || 0), 0);
    const media = Math.max(total - alta - baja, 0);
    const idx = total ? Math.round(((alta - baja) / total) * 100) : 0;
    description.textContent =
      'Distribución en escala Likert 1–5 (Alta >= 4.5, Media 3.75–4.49, Baja < 3.75).';
    target.innerHTML = total
      ? `<div class="nps-summary"><strong>+${idx}</strong><span>Índice neto Likert (${total} respuestas)</span></div>
         <div class="stacked">
           <i class="promoter" style="width:${(alta / total) * 100}%" data-tip="Alta (>=4.5): ${alta}"></i>
           <i class="neutral" style="width:${(media / total) * 100}%" data-tip="Media: ${media}"></i>
           <i class="detractor" style="width:${(baja / total) * 100}%" data-tip="Baja (<3.75): ${baja}"></i>
         </div>
         <div class="nps-legend">
           <span><i class="promoter"></i>Alta ${alta} (${Math.round((alta / total) * 100)}%)</span>
           <span><i class="neutral"></i>Media ${media}</span>
           <span><i class="detractor"></i>Baja ${baja}</span>
         </div>`
      : '<p>Sin encuestas para estos filtros.</p>';
    return;
  }

  const periods = [
    ...new Set(
      [
        ...participation.map((item) => item.fecha_evento?.slice(0, 7)),
        ...satisfaction.map((item) => item.periodo_mes),
      ].filter((p) => p && p !== 'SIN_FECHA')
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
  byId('leads-ratio-tag').textContent = total ? `${Math.round((leads / total) * 100)}% leads` : '0% leads';
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
        k.responsable_nombre && !k.responsable_nombre.includes('Sin asignar')
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
    desc.textContent = `Próximos 90 días: ${g.total_90d || 0} activos · Vencidos sin baja formal: ${g.vencidos || 0}.`;
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
    target.innerHTML = `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Curva de vencimientos">${grid}${bars}</svg>`;
    return;
  }

  const kams = (dist.vencimientos_por_kam || []).slice(0, 8);
  const max = Math.max(...kams.map((k) => k.total_90d + k.vencidos), 1);
  desc.textContent = 'Por KAM: vencidos (rojo), 0–30d (naranja), 31–60d (violeta), 61–90d (verde).';
  target.innerHTML = `<div class="bar-list">${
    kams
      .map((k) => {
        const lbl = k.responsable_nombre || k.kam_id;
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
  const mapCfg = {
    nivel: { list: dist.por_nivel || [], key: 'nivel', mode: 'donut', title: 'nivel de membresía' },
    tamano: { list: dist.por_tamano || [], key: 'tamano', mode: 'donut', title: 'tamaño empresarial' },
    empleados: { list: dist.por_rango_empleados || [], key: 'rango_empleados', mode: 'bars', title: 'rango de empleados' },
    sector: { list: dist.por_sector || [], key: 'sector', mode: 'bars', title: 'sector económico' },
    subsector: { list: dist.por_subsector || [], key: 'subsector', mode: 'bars', title: 'subsector económico' },
  };
  const cfg = mapCfg[state.distView] || mapCfg.nivel;
  const items = cfg.list;
  desc.textContent = `Distribución por ${cfg.title} sobre ${dist.total_activos} afiliados activos.`;

  if (cfg.mode === 'bars') {
    const max = Math.max(...items.map((i) => i.empresas), 1);
    target.innerHTML = `<div class="bar-list">${
      items
        .map(
          (i) =>
            `<div class="bar-row"><span title="${escapeHtml(i[cfg.key])}">${escapeHtml(i[cfg.key])}</span><div class="track"><div class="fill" style="width:${(i.empresas / max) * 100}%" data-tip="${escapeHtml(i[cfg.key])}: ${i.empresas} (${i.porcentaje}%)"></div></div><b>${i.empresas} <small>(${i.porcentaje}%)</small></b></div>`
        )
        .join('') || '<p>Sin datos para este criterio.</p>'
    }</div>`;
    return;
  }

  const total = items.reduce((s, i) => s + i.empresas, 0);
  const colors = ['#5000bf', '#39b8ff', '#05cd99', '#ff5a00', '#ffb547', '#9b82ff', '#8f9bba'];
  let offset = 0;
  const slices = items
    .map((item, idx) => {
      const share = total ? item.empresas / total : 0;
      const c = `<circle cx="50" cy="50" r="38" pathLength="100" stroke="${colors[idx % colors.length]}" stroke-dasharray="${share * 100} ${100 - share * 100}" stroke-dashoffset="${-offset}" data-tip="${escapeHtml(item[cfg.key])}: ${item.empresas} (${item.porcentaje}%)"/>`;
      offset += share * 100;
      return c;
    })
    .join('');
  target.innerHTML = total
    ? `<div class="donut-layout"><svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Distribución de activos"><circle class="donut-base" cx="50" cy="50" r="38"/>${slices}<text x="50" y="48">${total}</text><text x="50" y="59">activos</text></svg>
       <ul class="legend">${items
         .map(
           (item, idx) =>
             `<li><i style="background:${colors[idx % colors.length]}"></i><span>${escapeHtml(item[cfg.key])}</span><b>${item.empresas} (${item.porcentaje}%)</b></li>`
         )
         .join('')}</ul></div>`
    : '<p>Sin datos para estos filtros.</p>';
}

/* 3. EVENT TYPE KPIS (GOLD) */
function renderEventKpis(data) {
  state.lastEventKpis = data;
  if (!data) return;
  const rows = state.evKpiView === 'linea' ? data.por_linea_2027 || [] : data.por_modalidad || [];
  byId('event-kpis-description').textContent =
    state.evKpiView === 'linea'
      ? 'Desempeño comparativo de las 4 líneas estratégicas 2027 (penetración en activos, liderazgo C-Level y captación de leads).'
      : 'Comparativa integral por modalidad del evento (Presencial, Virtual e Híbrido).';

  byId('event-kpis-view').innerHTML = `<div class="table-wrap"><table><thead>
    <tr><th>Tipo / Línea</th><th>Eventos</th><th>Asistencias</th><th>Prom. / evento</th><th>Afiliados</th><th>Leads (%)</th><th>Penetración activos</th><th>% Directivos</th></tr>
    </thead><tbody>${
      rows
        .map(
          (r) => `<tr>
            <td><strong>${escapeHtml(r.tipo)}</strong></td>
            <td>${r.total_eventos}</td>
            <td>${r.total_asistencias}</td>
            <td>${r.promedio_asistentes_evento}</td>
            <td>${r.asistencias_afiliados}</td>
            <td>${r.asistencias_leads} <small>(${r.porcentaje_leads}%)</small></td>
            <td><span class="sem-pill VERDE">${r.penetracion_promedio_activos_pct}%</span></td>
            <td>${r.porcentaje_cargos_directivos}%</td>
          </tr>`
        )
        .join('') || '<tr><td colspan="8">Sin KPIs de eventos.</td></tr>'
    }</tbody></table></div>`;
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

  byId('participation-view').innerHTML = `<div class="table-wrap bounded"><table><thead><tr><th>Evento</th><th>Línea</th><th>Ciudad</th><th>Total</th><th>Afiliados</th><th>Leads</th><th>Penetración</th></tr></thead><tbody>${
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.nombre_evento || '—')}</td><td>${escapeHtml(item.linea_oferta || '—')}</td><td>${escapeHtml(item.ciudad_sede || 'Virtual')}</td><td>${item.asistencias}</td><td>${item.asistentes_afiliados ?? '—'}</td><td>${item.asistentes_no_afiliados ?? '—'}</td><td>${item.penetracion_activos_pct ?? 0}%</td></tr>`
      )
      .join('') || '<tr><td colspan="7">Sin asistencias para estos filtros.</td></tr>'
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
    desc.textContent = 'Cargo capturado al momento del evento (silver_fact_asistencias).';
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

/* 4. ENTERPRISE SEGMENT KPIS (SECTOR, SUBSECTOR, SIZE, EMPLOYEES) */
function renderSegmentKpis(data) {
  const items = data.items || [];
  byId('segment-kpis-description').textContent = `Comparativa de permanencia CRM, uso de servicios, riesgo de renovación y equidad (${data.total_categorias || 0} categorías).`;
  const top = items.slice(0, 8);
  const max = Math.max(...top.map((i) => i.afiliados_activos + i.ex_afiliados), 1);
  byId('segment-kpis-chart').innerHTML = `<div class="bar-list" style="margin-bottom:14px">${
    top
      .map((i) => {
        const pAct = (i.afiliados_activos / max) * 100;
        const pEx = (i.ex_afiliados / max) * 100;
        return `<div class="bar-row">
          <span title="${escapeHtml(i.categoria)}">${escapeHtml(i.categoria)}</span>
          <div class="track stacked-track">
            <div class="fill teal" style="width:${pAct}%;border-radius:999px 0 0 999px" data-tip="${escapeHtml(i.categoria)} · Activos: ${i.afiliados_activos} (${i.tasa_permanencia_crm_pct}% permanencia)"></div>
            <div class="fill lead" style="width:${pEx}%" data-tip="${escapeHtml(i.categoria)} · Ex-afiliados: ${i.ex_afiliados}"></div>
          </div>
          <b>${i.afiliados_activos} <small>(${i.tasa_permanencia_crm_pct}%)</small></b>
        </div>`;
      })
      .join('')
  }</div>`;

  byId('segment-kpis-table').innerHTML = `<div class="table-wrap bounded compact-table"><table><thead>
    <tr><th>Categoría</th><th>Activos</th><th>Ex-afiliados</th><th>Leads</th><th>% Permanencia</th><th>% Uso serv.</th><th>Eventos prom.</th><th>Semáforo (R/A/V)</th><th>% Mujeres</th></tr>
    </thead><tbody>${
      items
        .map(
          (i) => `<tr>
            <td>${escapeHtml(i.categoria)}</td>
            <td><strong>${i.afiliados_activos}</strong></td>
            <td>${i.ex_afiliados}</td>
            <td>${i.prospectos_leads}</td>
            <td>${i.tasa_permanencia_crm_pct}%</td>
            <td>${i.porcentaje_uso_servicios}%</td>
            <td>${i.eventos_promedio_activos}</td>
            <td><span class="sem-pill ROJO">${i.riesgo_rojo}</span> <span class="sem-pill AMARILLO">${i.riesgo_amarillo}</span> <span class="sem-pill VERDE">${i.riesgo_verde}</span></td>
            <td>${i.porcentaje_mujeres_promedio !== null ? `${i.porcentaje_mujeres_promedio}%` : '—'}</td>
          </tr>`
        )
        .join('') || '<tr><td colspan="9">Sin datos.</td></tr>'
    }</tbody></table></div>`;
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
  state.lastKams = items;
  renderKamColumnChart(items, 'overview-kams-chart');
  if (state.kamView === 'chart') {
    renderKamColumnChart(items, 'kams-view');
    return;
  }
  if (state.kamView === 'semaphore') {
    const top = items.filter((k) => k.afiliados_activos > 0);
    const max = Math.max(...top.map((k) => k.afiliados_activos), 1);
    byId('kams-view').innerHTML = `<div class="bar-list">${
      top
        .map((k) => {
          const lbl = k.responsable_nombre || k.kam_id;
          return `<div class="bar-row"><span>${escapeHtml(lbl)}</span>
            <div class="track stacked-track">
              <div class="fill" style="width:${(k.riesgo_rojo / max) * 100}%;background:var(--danger);border-radius:0" data-tip="Rojo: ${k.riesgo_rojo}"></div>
              <div class="fill" style="width:${(k.riesgo_amarillo / max) * 100}%;background:var(--gold);border-radius:0" data-tip="Amarillo: ${k.riesgo_amarillo}"></div>
              <div class="fill teal" style="width:${(k.riesgo_verde / max) * 100}%;border-radius:0" data-tip="Verde: ${k.riesgo_verde}"></div>
            </div>
            <b>${k.afiliados_activos}</b></div>`;
        })
        .join('')
    }</div><div class="nps-legend"><span><i style="background:var(--danger)"></i>Rojo</span><span><i style="background:var(--gold)"></i>Amarillo</span><span><i style="background:var(--teal)"></i>Verde</span></div>`;
    return;
  }
  byId('kams-view').innerHTML = `<div class="table-wrap bounded"><table><thead><tr><th>KAM</th><th>Ejecutiva</th><th>Activos</th><th>Rojo</th><th>Vencen 90d</th><th>% Serv.</th><th>Asist.</th><th>Renov.</th></tr></thead><tbody>${
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.kam_id)}</td><td>${escapeHtml(item.responsable_nombre || '—')}</td><td>${item.afiliados_activos}</td><td><span class="sem-pill ROJO">${item.riesgo_rojo}</span></td><td>${item.vencen_90d}</td><td>${item.porcentaje_en_servicios}%</td><td>${item.asistencias_totales}</td><td>${item.renovaciones}</td></tr>`
      )
      .join('') || '<tr><td colspan="8">Sin datos.</td></tr>'
  }</tbody></table></div>`;
}

/* 5. 8 COMMUNICATION SEGMENTS WITH HABEAS DATA */
function renderCommSegments(data) {
  const resumen = data.resumen_segmentos || [];
  byId('comm-segment-pills').innerHTML = resumen
    .map(
      (s) =>
        `<button type="button" class="seg-chip ${s.segmento_codigo === state.commSegment ? 'is-active' : ''}" data-comm-code="${escapeHtml(s.segmento_codigo)}">${escapeHtml(s.segmento_nombre)} (${s.total_registros})</button>`
    )
    .join('');

  document.querySelectorAll('[data-comm-code]').forEach((btn) =>
    btn.addEventListener('click', async () => {
      state.commSegment = btn.dataset.commCode;
      await refreshCommSegmentsOnly();
    })
  );

  const sel = resumen.find((s) => s.segmento_codigo === state.commSegment);
  byId('comm-segment-summary').textContent = sel
    ? `${sel.segmento_nombre}: ${sel.total_registros} registros totales · ${sel.aptos_habeas_data} con Habeas Data verificado (${sel.porcentaje_contactable}%) · Mostrando ${data.total_filtrado} filtrados.`
    : '';

  const kam = byId('kam-filter').value;
  byId('export-comm-btn').href =
    `${endpoints.exportSegment}/${state.commSegment}` +
    query({ kam_id: kam, solo_aptos: state.habeasOnly ? 'true' : '' });

  const items = data.items || [];
  byId('comm-segment-body').innerHTML =
    items
      .map(
        (r) => `<tr>
          <td>${escapeHtml(r.id_empresa || '—')}</td>
          <td>${escapeHtml(r.id_persona || '—')}</td>
          <td>${escapeHtml(r.rol_contacto_resuelto || '—')}</td>
          <td>${escapeHtml(r.kam_id || '—')}</td>
          <td>${escapeHtml(r.nivel_membresia || '—')}</td>
          <td>${escapeHtml(r.sector_economico || '—')}</td>
          <td>${semPill(r.semaforo_riesgo_renovacion)}</td>
          <td>${escapeHtml(r.detalle_criterio || '—')}</td>
          <td>${r.apto_envio_comunicaciones ? '<span class="sem-pill VERDE">Autorizado</span>' : '<span class="sem-pill NO_APLICA">Sin opt-in</span>'}</td>
        </tr>`
      )
      .join('') || '<tr><td colspan="9">Sin registros para este segmento/filtro.</td></tr>';
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
          `<tr><td>${escapeHtml(item.id_empresa)}</td><td>${escapeHtml(item.kam_nombre || item.kam_id || '—')}</td><td>${semPill(item.semaforo_riesgo)}</td><td>${escapeHtml(item.nivel_membresia || '—')}</td><td>${escapeHtml(item.sector_economico || '—')}</td><td>${escapeHtml(item.tamano_empresa || '—')}</td><td>${escapeHtml(item.rango_empleados || '—')}</td><td>${escapeHtml(item.ciudad || '—')}</td><td>${item.eventos_anio ?? 0}</td><td>${escapeHtml(item.fecha_expiracion || '—')}</td></tr>`
      )
      .join('') || '<tr><td colspan="10">Sin resultados para estos filtros.</td></tr>';
}

function renderPortfolio(data) {
  state.portfolioItems = data.items || [];
  byId('portfolio-total').textContent = `${data.total} empresas`;
  renderPortfolioRows(state.portfolioItems);
}

/* 6. SATISFACTION, NLP TOPICS & OFFICIAL NPS SEPARATION */
function renderDimensionsAndNlp(data) {
  const rows = data.por_modalidad || [];
  byId('topics-count').textContent = `${data.total_con_temarios} comentarios`;
  const esc = data.resumen_escalas || {};
  byId('nps-official-badge').textContent =
    esc.respuestas_nps_0_10 > 0
      ? `NPS 0–10 Activo (${esc.respuestas_nps_0_10} resp.)`
      : 'NPS 0–10: esquema listo (pendiente captura 0–10)';

  const axes = [
    { key: 'relevancia_temas', label: 'Relevancia de temas' },
    { key: 'conferencistas', label: 'Conferencistas' },
    { key: 'locacion_plataforma', label: 'Locación / Plataforma' },
    { key: 'convocatoria_publicidad', label: 'Convocatoria y publicidad' },
  ];
  const allVals = rows.flatMap((r) => axes.map((a) => Number(r[a.key] || 0))).filter((v) => v > 0);
  const minDomain = allVals.length ? Math.max(1, Math.floor((Math.min(...allVals) - 0.25) * 2) / 2) : 4.0;
  const span = Math.max(5.0 - minDomain, 0.5);
  byId('dimensions-scale-tag').textContent = `Zoom ${minDomain.toFixed(1)}–5.0`;
  const pct = (val) => Math.max(4, Math.min(100, ((val - minDomain) / span) * 100));

  byId('dimensions-radar').innerHTML = rows.length
    ? `<div class="dim-compare-list">${axes
        .map((ax) => {
          const vals = rows.map((r) => ({ mod: r.modalidad, val: Number(r[ax.key] || 0) }));
          const pres = vals.find((v) => v.mod === 'Presencial');
          const virt = vals.find((v) => v.mod === 'Virtual');
          let deltaTxt = '';
          if (pres && virt) {
            const diff = pres.val - virt.val;
            deltaTxt = Math.abs(diff) < 0.01 ? 'Sin brecha' : diff > 0 ? `+${diff.toFixed(2)} Presencial` : `+${Math.abs(diff).toFixed(2)} Virtual`;
          }
          return `<div class="dim-card"><div class="dim-card-head"><span>${escapeHtml(ax.label)}</span>${deltaTxt ? `<span class="dim-delta">${deltaTxt}</span>` : ''}</div>${vals
            .map(
              (v) =>
                `<div class="dim-bar-row"><span>${escapeHtml(v.mod)}</span><div class="track"><div class="${v.mod === 'Virtual' ? 'fill cyan' : 'fill'}" style="width:${pct(v.val).toFixed(1)}%" data-tip="${escapeHtml(ax.label)} (${escapeHtml(v.mod)}): ${v.val.toFixed(2)} / 5.0"></div></div><b>${v.val.toFixed(2)}</b></div>`
            )
            .join('')}</div>`;
        })
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

  const nlp = data.temas_nlp || [];
  const maxNlp = Math.max(...nlp.map((t) => t.menciones), 1);
  byId('nlp-topics-chart').innerHTML = `<div class="bar-list" style="margin-bottom:14px">${
    nlp
      .map(
        (t) =>
          `<div class="bar-row"><span title="${escapeHtml(t.categoria)}">${escapeHtml(t.categoria)}</span><div class="track"><div class="fill teal" style="width:${(t.menciones / maxNlp) * 100}%" data-tip="${escapeHtml(t.categoria)}: ${t.menciones} menciones · Sat. ${t.satisfaccion_promedio}"></div></div><b>${t.menciones} <small>(${t.porcentaje}%)</small></b></div>`
      )
      .join('') || '<p>Sin categorías temáticas detectadas.</p>'
  }</div>`;

  const topics = data.temarios_recientes || [];
  byId('topics-list').innerHTML =
    topics
      .slice(0, 6)
      .map(
        (item) =>
          `<li>${escapeHtml(item.temario)}<small>${escapeHtml(item.categoria_nlp || 'General')} · ${escapeHtml(item.modalidad || 'Encuesta')} · ${escapeHtml(item.fecha || 'Sin fecha')}</small></li>`
      )
      .join('') || '<li>Sin temarios sugeridos en este periodo.</li>';
}

function renderSatisfaction(items) {
  byId('satisfaction-body').innerHTML =
    items
      .map(
        (item) =>
          `<tr><td>${escapeHtml(item.periodo_mes || 'Sin periodo')}</td><td>${escapeHtml(item.tipo_encuesta || 'POST_EVENTO')}</td><td>${item.respuestas}</td><td><strong>${item.promedio_satisfaccion}</strong></td><td>${item.satisfaccion_alta_pct ?? 0}%</td><td>+${item.nps_adaptado_1_5}</td><td>${item.nps_oficial_0_10 !== null && item.nps_oficial_0_10 !== undefined ? item.nps_oficial_0_10 : '<span class="sem-pill NO_APLICA">Pendiente 0–10</span>'}</td></tr>`
      )
      .join('') || '<tr><td colspan="7">Sin encuestas para este periodo.</td></tr>';
}

/* 7. RESERVED MACHINE LEARNING WORKSPACE */
function renderMlWorkspace(status, fidelidad, publico, uso, riesgo) {
  const modelos = status.modelos || [];
  const activos = modelos.filter((m) => m.estado === 'MODELO_ACTIVO').length;
  byId('ml-global-badge').textContent =
    activos > 0 ? `${activos}/4 Modelos activos` : '4/4 Espacios reservados listos';

  byId('ml-slots-container').innerHTML = modelos
    .map(
      (m) => `<div class="ml-slot-card">
        <h3>${escapeHtml(m.nombre_modelo)}</h3>
        <p>${escapeHtml(m.algoritmo_recomendado)}</p>
        <div class="ml-slot-meta">
          <span class="ml-route-code">${escapeHtml(m.ruta_endpoint)}</span>
          <span class="sem-pill ${m.estado === 'MODELO_ACTIVO' ? 'VERDE' : 'AMARILLO'}">${escapeHtml(m.estado)}</span>
        </div>
        <small style="color:var(--muted);font-size:10.5px">Destino Gold: <code>${escapeHtml(m.columna_gold_objetivo)}</code> (${m.registros_poblandose}/${m.total_universo_elegible})</small>
      </div>`
    )
    .join('');

  const curva = uso.curva_empirica_uso_vs_permanencia || [];
  byId('ml-uso-chart').innerHTML = `<div class="bar-list">${curva
    .map(
      (c) =>
        `<div class="bar-row"><span>${escapeHtml(c.tramo_uso)}</span><div class="track"><div class="fill teal" style="width:${c.tasa_permanencia_pct}%" data-tip="${escapeHtml(c.tramo_uso)}: ${c.permanecen_activas}/${c.empresas_crm} activas (${c.tasa_permanencia_pct}%)"></div></div><b>${c.tasa_permanencia_pct}%</b></div>`
    )
    .join('')}</div>`;

  const leads = (publico.prospectos_alta_interaccion || []).slice(0, 6);
  byId('ml-publico-view').innerHTML = `<div class="table-wrap bounded compact-table"><table><thead><tr><th>Prospecto</th><th>Sector</th><th>Asistencias</th><th>Línea histórica</th><th>Score ML</th></tr></thead><tbody>${
    leads
      .map(
        (l) =>
          `<tr><td>${escapeHtml(l.id_empresa)}</td><td>${escapeHtml(l.sector_economico || '—')}</td><td>${l.total_asistencias_anio}</td><td>${escapeHtml(l.linea_2027_mayor_participacion || '—')}</td><td>${l.score_conversion_lead_ml_0_100 ?? '<span class="sem-pill NO_APLICA">Reservado</span>'}</td></tr>`
      )
      .join('')
  }</tbody></table></div>`;

  const fidRows = (fidelidad.items || []).slice(0, 6);
  byId('ml-fidelidad-view').innerHTML = `<div class="table-wrap bounded compact-table"><table><thead><tr><th>Empresa</th><th>KAM</th><th>Eventos</th><th>Personas</th><th>Score ML</th></tr></thead><tbody>${
    fidRows
      .map(
        (f) =>
          `<tr><td>${escapeHtml(f.id_empresa)}</td><td>${escapeHtml(f.kam_id)}</td><td>${f.total_eventos_anio}</td><td>${f.personas_distintas_anio}</td><td>${f.score_fidelidad_ml_0_100 ?? '<span class="sem-pill NO_APLICA">Reservado</span>'}</td></tr>`
      )
      .join('')
  }</tbody></table></div>`;

  const chRows = (riesgo.cuentas_prioritarias || []).slice(0, 6);
  byId('ml-riesgo-view').innerHTML = `<div class="table-wrap bounded compact-table"><table><thead><tr><th>Empresa</th><th>Vencimiento</th><th>Pts. Heurístico</th><th>Prob. Churn ML</th><th>Semáforo</th></tr></thead><tbody>${
    chRows
      .map(
        (r) =>
          `<tr><td>${escapeHtml(r.id_empresa)}</td><td>${escapeHtml(r.fecha_fin_vigencia || '—')}</td><td>${r.puntaje_riesgo_heuristico ?? 0}</td><td>${r.probabilidad_churn_ml ?? '<span class="sem-pill NO_APLICA">Reservado</span>'}</td><td>${semPill(r.semaforo_riesgo_renovacion)}</td></tr>`
      )
      .join('')
  }</tbody></table></div>`;
}

async function refreshCommSegmentsOnly() {
  const kam = byId('kam-filter').value;
  const data = await request(
    endpoints.commSegments +
      query({
        segmento_codigo: state.commSegment,
        kam_id: kam,
        solo_aptos: state.habeasOnly ? 'true' : '',
      })
  );
  renderCommSegments(data);
}

async function refreshSegmentKpisOnly() {
  const kam = byId('kam-filter').value;
  const country = byId('country-filter').value;
  const data = await request(
    endpoints.segmentKpis + query({ dimension: state.segDim, kam_id: kam, pais: country })
  );
  renderSegmentKpis(data);
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
  const subsector = byId('subsector-filter').value;
  const size = byId('size-filter').value;
  const employees = byId('employees-filter').value;
  const semaphore = byId('semaphore-filter').value;
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
      evolution,
      eventKpis,
      segKpis,
      commSegs,
      satisfaction,
      dimensions,
    ] = await Promise.all([
      request(
        endpoints.portfolio +
          query({
            kam_id: kam,
            nivel_membresia: level,
            sector,
            subsector,
            tamano_empresa: size,
            rango_empleados: employees,
            semaforo: semaphore,
            estado_membresia: membershipStatus,
            ciudad: city,
            pais: country,
          })
      ),
      request(endpoints.renewals + query({ kam_id: kam, periodo_desde: period, periodo_hasta: period })),
      request(
        endpoints.participation +
          query({ ...dates, kam_id: kam, ciudad_evento: eventCity, linea_oferta: line, modalidad: modality })
      ),
      request(
        endpoints.audience +
          query({ ...dates, kam_id: kam, ciudad_evento: eventCity, linea_oferta: line, modalidad: modality })
      ),
      request(endpoints.pillars + query({ kam_id: kam, nivel_membresia: level, sector, pais: country })),
      request(endpoints.kams),
      request(
        endpoints.distribution +
          query({
            kam_id: kam,
            nivel_membresia: level,
            sector,
            subsector,
            tamano_empresa: size,
            rango_empleados: employees,
            ciudad: city,
            pais: country,
          })
      ),
      request(endpoints.evolution + query({ kam_id: kam })),
      request(endpoints.eventKpis + query({ linea_oferta: line, modalidad: modality })),
      request(endpoints.segmentKpis + query({ dimension: state.segDim, kam_id: kam, pais: country })),
      request(
        endpoints.commSegments +
          query({ segmento_codigo: state.commSegment, kam_id: kam, solo_aptos: state.habeasOnly ? 'true' : '' })
      ),
      request(endpoints.satisfaction + query(dates)),
      request(endpoints.dimensions + query(dates)),
    ]);

    state.lastEvolution = evolution;
    state.lastParticipation = participation;
    state.lastSatisfaction = satisfaction;

    renderPortfolio(portfolio);
    renderParticipation(participation);
    renderAudience(audience);
    renderOverviewLines(audience);
    renderEventKpis(eventKpis);
    renderSegmentKpis(segKpis);
    renderPillars(pillars);
    renderKamsSection(kams);
    renderExpirations(distribution);
    renderDistribution(distribution);
    renderCommSegments(commSegs);
    renderSatisfaction(satisfaction);
    renderDimensionsAndNlp(dimensions);
    renderInsightPanel();

    byId('renewal-count').textContent = renewals.reduce((sum, item) => sum + item.renovaciones, 0);
    const totalAtt = participation.reduce((sum, item) => sum + item.asistencias, 0);
    const leadsAtt = participation.reduce((sum, item) => sum + (item.asistentes_no_afiliados || 0), 0);
    byId('attendance-count').textContent = totalAtt;
    byId('attendance-detail').textContent = `${totalAtt - leadsAtt} afiliados · ${leadsAtt} leads`;
    const activeSatisfaction = satisfaction.length
      ? satisfaction.reduce((sum, item) => sum + item.promedio_satisfaccion * item.respuestas, 0) /
        Math.max(satisfaction.reduce((sum, item) => sum + item.respuestas, 0), 1)
      : 0;
    byId('satisfaction-score').textContent = activeSatisfaction.toFixed(2);
    byId('filter-status').textContent = 'En línea';
  } catch (error) {
    byId('filter-status').textContent = 'Error al cargar';
  }
}

async function initialize() {
  try {
    const [overview, flt, mlStatus, mlFid, mlPub, mlUso, mlRiesgo] = await Promise.all([
      request(endpoints.overview),
      request(endpoints.filters),
      request(endpoints.mlStatus),
      request(endpoints.mlFidelidad),
      request(endpoints.mlPublico),
      request(endpoints.mlUso),
      request(endpoints.mlRiesgo),
    ]);

    byId('data-date').textContent = `Corte ${overview.fecha_referencia}`;
    byId('active-count').textContent = overview.afiliados_activos;
    byId('retention-detail').textContent = `${overview.tasa_retencion_historica_pct}% permanencia histórica`;
    byId('service-rate').textContent = `${overview.porcentaje_afiliados_en_servicios}%`;
    byId('service-detail').textContent = `${overview.empresas_con_servicio} de ${overview.afiliados_activos} activos`;
    byId('expiring-count').textContent = overview.vencimientos_proximos['90'];
    byId('risk-red-detail').textContent = `${overview.semaforo_riesgo?.ROJO || 0} en semáforo rojo`;
    byId('source-caption').textContent = `DWH activo (${overview.fuente_datos}) · Silver 3NF + Gold Estrella.`;

    renderSemaphoreOverview(overview);
    renderMlWorkspace(mlStatus, mlFid, mlPub, mlUso, mlRiesgo);

    appendOptions(byId('period-filter'), flt.periodos_asistencia, (value) =>
      new Intl.DateTimeFormat('es-CO', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
        new Date(`${value}-01T00:00:00Z`)
      )
    );
    appendOptions(byId('kam-filter'), flt.kams);
    appendOptions(byId('level-filter'), flt.niveles_membresia);
    appendOptions(byId('sector-filter'), flt.sectores);
    appendOptions(byId('subsector-filter'), flt.subsectores);
    appendOptions(byId('size-filter'), flt.tamanos_empresa);
    appendOptions(byId('employees-filter'), flt.rangos_empleados);
    appendOptions(byId('semaphore-filter'), flt.semaforos_riesgo);
    appendOptions(byId('membership-status-filter'), flt.estados_membresia);
    appendOptions(byId('country-filter'), flt.paises);
    appendOptions(byId('city-filter'), flt.ciudades);
    appendOptions(byId('event-city-filter'), flt.ciudades_evento);
    appendOptions(byId('line-filter'), flt.lineas_oferta);
    appendOptions(byId('modality-filter'), flt.modalidades_evento);

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

byId('habeas-only-toggle')?.addEventListener('change', async (e) => {
  state.habeasOnly = e.target.checked;
  await refreshCommSegmentsOnly();
});

document.querySelectorAll('[data-chart]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-chart]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.chart = btn.dataset.chart;
    renderParticipation(state.lastParticipation);
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
    renderInsightPanel();
  })
);
document.querySelectorAll('[data-kam-view]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-kam-view]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.kamView = btn.dataset.kamView;
    renderKamsSection(state.lastKams);
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
document.querySelectorAll('[data-evkpi-view]').forEach((btn) =>
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-evkpi-view]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.evKpiView = btn.dataset.evkpiView;
    renderEventKpis(state.lastEventKpis);
  })
);
document.querySelectorAll('[data-segdim]').forEach((btn) =>
  btn.addEventListener('click', async () => {
    document.querySelectorAll('[data-segdim]').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.segDim = btn.dataset.segdim;
    await refreshSegmentKpisOnly();
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
