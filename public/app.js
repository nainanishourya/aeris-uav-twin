const $ = (id) => document.getElementById(id);
const api = (path, options) => fetch(path, options).then((response) => {
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
});

function setText(id, value) { $(id).textContent = value ?? '--'; }

function drawChart(records) {
  const values = records.map((item) => Number(item.health_index ?? item.anomaly_score ?? 0)).filter(Number.isFinite).slice(-24);
  if (values.length < 2) return;
  const min = Math.min(...values) - 2;
  const max = Math.max(...values) + 2;
  const points = values.map((value, index) => {
    const x = index * (800 / (values.length - 1));
    const y = 225 - ((value - min) / (max - min || 1)) * 185;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  $('chart-line').setAttribute('points', points.join(' '));
  const [x, y] = points.at(-1).split(',');
  $('chart-dot').setAttribute('cx', x); $('chart-dot').setAttribute('cy', y);
}

function renderHealth(data) {
  const health = Number(data.engine_health_index ?? 0);
  setText('health', health.toFixed(1)); setText('posture-number', health.toFixed(1));
  $('health-meter').style.width = `${Math.max(0, Math.min(100, health))}%`;
  setText('health-status', data.health_status?.toUpperCase()); setText('posture-label', data.health_status?.toUpperCase());
  setText('anomaly', Number(data.anomaly_score ?? 0).toFixed(3));
  setText('rul', Math.round(data.estimated_rul_hours ?? 0));
  setText('fault', data.active_fault); setText('confidence', `${Math.round((data.fault_confidence ?? 0) * 100)}% CONFIDENCE`);
  setText('telemetry', data.telemetry_stream_active ? 'STREAM LIVE' : 'STREAM IDLE');
}

function renderTelemetry(data) {
  setText('rpm', Math.round(data.rpm)); setText('cht', Number(data.cht_c ?? 0).toFixed(1));
  setText('egt', Number(data.egt_c ?? 0).toFixed(1)); setText('oil', Number(data.oil_pressure_bar ?? 0).toFixed(2));
  setText('altitude', Math.round(data.altitude_m)); setText('throttle', `${Math.round(Number(data.throttle ?? 0) * 100)}`);
  if (data.timestamp) setText('timestamp', new Date(data.timestamp * 1000).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' }));
}

async function refresh() {
  try {
    const [health, telemetry, history, diagnostics] = await Promise.all([
      api('/api/health'), api('/api/telemetry/latest'), api('/api/telemetry/history?limit=24'), api('/api/diagnostics')
    ]);
    renderHealth(health); renderTelemetry(telemetry); drawChart(history.records || []);
    setText('maintenance', diagnostics.maintenance_action || health.maintenance_action);
    setText('maintenance-state', health.health_status === 'Healthy' ? 'STANDING BY' : 'REVIEW REQUIRED');
    $('connection').textContent = 'LIVE / SYNCED';
  } catch (error) {
    $('connection').textContent = 'SIGNAL LOST'; $('connection').style.color = 'var(--red)';
    setText('action-note', `API connection error: ${error.message}`);
  }
}

async function startDemo() {
  const button = $('demo-button'); button.disabled = true; button.textContent = 'STARTING SCENARIO...';
  try { await api('/api/demo/start', { method:'POST' }); $('action-note').textContent = 'Injector degradation demo started. Refreshing telemetry...'; await refresh(); }
  catch (error) { $('action-note').textContent = `Unable to start demo: ${error.message}`; }
  finally { button.disabled = false; button.innerHTML = '<span>▶</span> START DEMO SCENARIO'; }
}

$('demo-button').addEventListener('click', startDemo);
refresh(); setInterval(refresh, 5000);