#!/usr/bin/env python3
import html
import json
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DATA = Path("/home/gns3/netops-sentinel-data")
REPORTS = DATA / "evidence" / "runs"
INCIDENTS = DATA / "incidents" / "incidents.json"
HOST = "127.0.0.1"
PORT = 8080


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def safe_percent(numerator, denominator):
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def format_span(seconds):
    if seconds is None:
        return "no timestamp data"
    if seconds < 60:
        return "less than 1 minute"
    if seconds < 3600:
        return f"{int(seconds // 60)} minutes"
    if seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
    days = seconds / 86400
    return f"{days:.1f} days"


def load_data():
    reports = []
    for path in sorted(REPORTS.glob("reachability-*.json")):
        report = read_json(path, None)
        if isinstance(report, dict):
            report["_file"] = path.name
            reports.append(report)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    recent = [
        report for report in reports
        if (parse_time(report.get("started_at"))
            or parse_time(report.get("finished_at"))
            or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
    ]

    recent_times = [
        parse_time(report.get("finished_at"))
        or parse_time(report.get("started_at"))
        for report in recent
    ]
    recent_times = [stamp for stamp in recent_times if stamp is not None]
    observed_span_seconds = (
        (max(recent_times) - min(recent_times)).total_seconds()
        if len(recent_times) >= 2 else (0 if recent_times else None)
    )

    latest = reports[-1] if reports else {}
    latest_time = (
        parse_time(latest.get("finished_at"))
        or parse_time(latest.get("started_at"))
    )
    age_seconds = max(0, int((now - latest_time).total_seconds())) if latest_time else None

    histories = {}
    addresses = {}
    for report in recent:
        stamp = report.get("finished_at") or report.get("started_at") or ""
        for result in report.get("results", []):
            name = result.get("name") or result.get("ip_address") or "Unknown"
            histories.setdefault(name, []).append((stamp, result))
            addresses[name] = result.get("ip_address", addresses.get(name, ""))

    endpoints = []
    for name, history in sorted(histories.items()):
        history.sort(key=lambda item: item[0])
        observations = [result for _, result in history]
        last = observations[-1]
        reachable_count = sum(r.get("status") == "reachable" for r in observations)
        total = len(observations)
        endpoints.append({
            "name": name,
            "ip_address": addresses.get(name, ""),
            "status": last.get("status", "unknown"),
            "duration_ms": last.get("duration_ms"),
            "packet_loss_percent": last.get("packet_loss_percent"),
            "replies_received": last.get("replies_received"),
            "probes_sent": last.get("probes_sent"),
            "availability_percent": safe_percent(reachable_count, total),
            "observations": total,
        })

    incident_data = read_json(INCIDENTS, {})
    all_events = incident_data.get("events", [])
    if not isinstance(all_events, list):
        all_events = []

    all_events = sorted(all_events, key=lambda e: str(e.get("time", "")))
    active = {}
    for event in all_events:
        endpoint = event.get("endpoint")
        if not endpoint:
            continue
        event_type = str(event.get("event", "")).upper()
        if event_type == "OUTAGE":
            active[endpoint] = event
        elif event_type == "RECOVERY":
            active.pop(endpoint, None)

    trend = []
    for report in recent[-12:]:
        results = report.get("results", [])
        checked = len(results)
        reachable = sum(r.get("status") == "reachable" for r in results)
        stamp = report.get("finished_at") or report.get("started_at") or ""
        trend.append({
            "time": stamp,
            "label": stamp[11:16] if len(stamp) >= 16 else stamp,
            "reachable": reachable,
            "checked": checked,
            "percent": safe_percent(reachable, checked),
        })

    total_endpoints = len(endpoints)
    healthy = sum(e["status"] == "reachable" for e in endpoints)
    overall_availability = (
        round(sum(e["availability_percent"] for e in endpoints) / total_endpoints, 2)
        if total_endpoints else 0
    )

    return {
        "generated_at": now.isoformat(),
        "report_count": len(reports),
        "reports_7d": len(recent),
        "observed_span": format_span(observed_span_seconds),
        "latest": latest,
        "latest_age_seconds": age_seconds,
        "endpoints": endpoints,
        "incidents": all_events[-20:],
        "active_incidents": [
            {"endpoint": name, **event} for name, event in active.items()
        ],
        "trend": trend,
        "healthy_endpoints": healthy,
        "total_endpoints": total_endpoints,
        "overall_availability_percent": overall_availability,
    }


def esc(value):
    return html.escape(str(value if value is not None else "—"))


def fmt_number(value, digits=1):
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def duration_text(seconds):
    if seconds is None:
        return "No reports yet"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m ago"
    return f"{seconds // 86400}d ago"


def make_page(data):
    latest = data["latest"]
    active_count = len(data["active_incidents"])
    healthy = data["healthy_endpoints"]
    total = data["total_endpoints"]
    latest_age = data["latest_age_seconds"]
    stale = latest_age is not None and latest_age > 600

    if not latest:
        overall_status = "Awaiting data"
        overall_class = "neutral"
    elif stale:
        overall_status = "STALE DATA"
        overall_class = "warning"
    elif healthy == total and total:
        overall_status = "ALL SYSTEMS UP"
        overall_class = "good"
    elif healthy:
        overall_status = "DEGRADED"
        overall_class = "warning"
    else:
        overall_status = "OUTAGE"
        overall_class = "bad"

    endpoint_rows = []
    for endpoint in data["endpoints"]:
        status = endpoint["status"]
        status_class = "good" if status == "reachable" else (
            "bad" if status == "unreachable" else "neutral"
        )
        loss = endpoint.get("packet_loss_percent")
        loss_class = "bad" if isinstance(loss, (int, float)) and loss > 0 else ""
        availability = endpoint["availability_percent"]
        avail_class = "good" if availability >= 99 else (
            "warning" if availability >= 90 else "bad"
        )
        replies = endpoint.get("replies_received")
        probes = endpoint.get("probes_sent")
        reply_text = f"{replies}/{probes}" if replies is not None and probes else "—"
        duration = endpoint.get("duration_ms")
        duration = f"{fmt_number(duration)} ms" if duration is not None else "—"

        endpoint_rows.append(f"""
        <tr>
          <td><div class="endpoint-name">{esc(endpoint['name'])}</div>
              <div class="sub mono">{esc(endpoint['ip_address'])}</div></td>
          <td><span class="pill {status_class}"><span class="dot"></span>{esc(status.upper())}</span></td>
          <td class="mono">{duration}</td>
          <td class="{loss_class}">{fmt_number(loss)}%</td>
          <td><div class="availability"><div class="bar"><span class="{avail_class}" style="width:{max(0, min(100, availability))}%"></span></div>
              <strong>{fmt_number(availability, 2)}%</strong></div>
              <div class="sub">{endpoint['observations']} checks in 7 days</div></td>
          <td class="mono">{esc(reply_text)}</td>
        </tr>""")

    incident_rows = []
    for event in data["incidents"]:
        event_type = str(event.get("event", "EVENT")).upper()
        event_class = "bad" if event_type == "OUTAGE" else (
            "good" if event_type == "RECOVERY" else "neutral"
        )
        incident_rows.append(f"""
        <tr>
          <td class="mono">{esc(event.get('time', '—'))}</td>
          <td><strong>{esc(event.get('endpoint', '—'))}</strong></td>
          <td><span class="pill {event_class}">{esc(event_type)}</span></td>
          <td>{esc(event.get('details', '—'))}</td>
        </tr>""")

    active_rows = []
    for event in data["active_incidents"]:
        active_rows.append(f"""
        <div class="active-incident">
          <span class="pill bad"><span class="dot"></span>ACTIVE OUTAGE</span>
          <div class="active-title">{esc(event.get('endpoint', 'Unknown'))}</div>
          <div class="sub">{esc(event.get('details', 'No details recorded'))}</div>
          <div class="sub mono">Detected: {esc(event.get('time', '—'))}</div>
        </div>""")

    trend_bars = []
    for point in data["trend"]:
        percent = point["percent"]
        color_class = "good" if percent >= 99 else (
            "warning" if percent >= 80 else "bad"
        )
        height = max(4, min(100, percent))
        trend_bars.append(f"""
        <div class="trend-point" title="{esc(point['time'])}: {point['reachable']}/{point['checked']} reachable">
          <div class="trend-track"><div class="trend-fill {color_class}" style="height:{height}%"></div></div>
          <div class="trend-label">{esc(point['label'])}</div>
          <div class="trend-value">{fmt_number(percent, 0)}%</div>
        </div>""")

    latest_file = latest.get("_file", "—")
    latest_time = latest.get("finished_at") or latest.get("started_at") or "—"
    host = latest.get("monitoring_host", "—")
    mode = latest.get("monitoring_mode", "read-only")
    report_status = (
        f"{latest.get('reachable', healthy)}/{latest.get('targets_checked', total)} endpoints reachable"
        if latest else "No monitoring reports found"
    )
    freshness_class = "bad" if stale else "good"
    avg_avail = data["overall_availability_percent"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1220">
<title>NetOps Sentinel | Operations</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#080e19; --panel:#101a2a; --panel2:#131f32; --line:#243249;
  --text:#edf3fc; --muted:#91a2ba; --green:#32d583; --red:#ff647c;
  --amber:#f6c76b; --blue:#71a7ff;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:radial-gradient(ellipse at 15% -10%,#182b48 0,transparent 42%),var(--bg); color:var(--text); font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
header {{ border-bottom:1px solid var(--line); background:rgba(9,16,29,.92); }}
.topbar {{ max-width:1500px; margin:auto; padding:22px 28px; display:flex; justify-content:space-between; align-items:center; gap:18px; }}
.brand {{ display:flex; align-items:center; gap:14px; }}
.brand-mark {{ width:44px; height:44px; border-radius:13px; display:grid; place-items:center; color:#a9caff; background:#172b49; border:1px solid #2c4b75; font-size:22px; font-weight:800; }}
h1 {{ margin:0; font-size:22px; letter-spacing:-.5px; }}
.subtitle {{ color:var(--muted); font-size:12px; margin-top:3px; }}
.header-right {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
.pill {{ display:inline-flex; align-items:center; gap:7px; border:1px solid var(--line); padding:5px 9px; border-radius:99px; font-size:11px; font-weight:750; letter-spacing:.35px; white-space:nowrap; }}
.pill.good {{ color:var(--green); border-color:#24543f; background:#10281f; }}
.pill.bad {{ color:var(--red); border-color:#66303d; background:#301923; }}
.pill.warning {{ color:var(--amber); border-color:#67512c; background:#2a2417; }}
.pill.neutral {{ color:var(--muted); background:#151e2c; }}
.dot {{ width:6px; height:6px; border-radius:50%; background:currentColor; display:inline-block; }}
main {{ max-width:1500px; margin:auto; padding:26px 28px 36px; }}
.section-head {{ display:flex; align-items:end; justify-content:space-between; gap:12px; margin-bottom:16px; }}
h2 {{ margin:0; font-size:16px; letter-spacing:-.2px; }}
h3 {{ margin:0; font-size:14px; }}
.muted,.sub {{ color:var(--muted); }}
.sub {{ font-size:11px; margin-top:3px; }}
.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:24px; }}
.kpi,.panel {{ border:1px solid var(--line); background:linear-gradient(145deg,rgba(20,32,51,.97),rgba(13,23,38,.98)); border-radius:15px; box-shadow:0 10px 28px rgba(0,0,0,.12); }}
.kpi {{ padding:18px 19px; min-height:124px; }}
.kpi-label {{ color:var(--muted); font-size:12px; font-weight:600; }}
.kpi-value {{ font-size:29px; font-weight:750; letter-spacing:-1px; margin:8px 0 3px; }}
.kpi-note {{ color:var(--muted); font-size:11px; }}
.value-good {{ color:var(--green); }} .value-bad {{ color:var(--red); }} .value-amber {{ color:var(--amber); }}
.layout {{ display:grid; grid-template-columns:minmax(0,1.6fr) minmax(290px,.8fr); gap:18px; align-items:start; }}
.panel {{ padding:20px; margin-bottom:18px; min-width:0; }}
.panel-note {{ color:var(--muted); font-size:12px; margin:7px 0 17px; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; min-width:760px; }}
th {{ text-align:left; color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.8px; font-weight:700; padding:11px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }}
td {{ padding:14px 10px; border-bottom:1px solid rgba(36,50,73,.75); vertical-align:middle; }}
tbody tr:last-child td {{ border-bottom:0; }}
tbody tr:hover {{ background:rgba(113,167,255,.035); }}
.endpoint-name {{ font-weight:700; }}
.availability {{ display:flex; align-items:center; gap:9px; min-width:130px; }}
.bar {{ width:75px; height:5px; border-radius:8px; background:#273449; overflow:hidden; }}
.bar span {{ display:block; height:100%; border-radius:8px; }}
.good {{ color:var(--green); }} .bar span.good,.trend-fill.good {{ background:var(--green); }}
.bad {{ color:var(--red); }} .bar span.bad,.trend-fill.bad {{ background:var(--red); }}
.warning {{ color:var(--amber); }} .bar span.warning,.trend-fill.warning {{ background:var(--amber); }}
.neutral {{ color:var(--muted); }}
.incident-empty {{ border:1px dashed #30425a; border-radius:12px; padding:22px 14px; text-align:center; color:var(--muted); }}
.incident-empty .check {{ font-size:24px; color:var(--green); margin-bottom:6px; }}
.active-incident {{ border:1px solid #66303d; background:#211722; border-radius:12px; padding:14px; margin-top:12px; }}
.active-title {{ font-size:16px; font-weight:750; margin-top:9px; }}
.trend {{ display:flex; align-items:stretch; gap:10px; min-height:145px; padding-top:6px; }}
.trend-point {{ flex:1; min-width:0; text-align:center; display:flex; flex-direction:column; align-items:center; gap:5px; }}
.trend-track {{ height:94px; width:100%; max-width:28px; display:flex; align-items:end; background:#1b293e; border-radius:6px; overflow:hidden; }}
.trend-fill {{ width:100%; min-height:4px; border-radius:5px 5px 0 0; }}
.trend-label,.trend-value {{ font-size:10px; color:var(--muted); white-space:nowrap; }}
.trend-value {{ color:var(--text); font-weight:700; }}
.meta-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:16px; }}
.meta-item {{ border:1px solid var(--line); border-radius:10px; padding:12px; min-width:0; }}
.meta-label {{ color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.7px; }}
.meta-value {{ margin-top:6px; font-weight:650; overflow-wrap:anywhere; }}
.footer {{ border-top:1px solid var(--line); padding:18px 28px 24px; color:var(--muted); font-size:11px; text-align:center; }}
@media(max-width:1050px) {{ .layout {{ grid-template-columns:1fr; }} }}
@media(max-width:760px) {{ .topbar {{ padding:18px 16px; align-items:flex-start; }} main {{ padding:20px 14px; }} .kpis {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }} .kpi {{ padding:14px; min-height:112px; }} .kpi-value {{ font-size:24px; }} .panel {{ padding:15px; }} .header-right {{ justify-content:flex-end; }} h1 {{ font-size:19px; }} }}
@media(max-width:420px) {{ .brand-mark {{ display:none; }} .kpis {{ grid-template-columns:1fr 1fr; }} .kpi-value {{ font-size:21px; }} .meta-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div class="brand">
      <div class="brand-mark">N</div>
      <div><h1>NetOps Sentinel</h1><div class="subtitle">NETWORK OPERATIONS CENTER / READ-ONLY MONITORING</div></div>
    </div>
    <div class="header-right">
      <span class="pill {overall_class}"><span class="dot"></span>{esc(overall_status)}</span>
      <span class="pill neutral">ICMPv4</span>
      <span class="pill neutral">REFRESH 30s</span>
    </div>
  </div>
</header>
<main id="dashboard">
  <div class="section-head">
    <div><h2>Operations overview</h2><div class="panel-note" style="margin-bottom:0">Current sampled reachability and evidence from the rolling seven-day window.</div></div>
    <div class="muted mono">LAST CHECK: {esc(duration_text(latest_age))}</div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="kpi-label">Reachable endpoints</div><div class="kpi-value {'value-good' if healthy == total and total else 'value-amber'}">{healthy}<span class="muted"> / {total}</span></div><div class="kpi-note">Latest recorded endpoint states</div></div>
    <div class="kpi"><div class="kpi-label">Active incidents</div><div class="kpi-value {'value-bad' if active_count else 'value-good'}">{active_count}</div><div class="kpi-note">Derived from outage and recovery events</div></div>
    <div class="kpi"><div class="kpi-label">Mean observed availability</div><div class="kpi-value">{fmt_number(avg_avail, 2)}<span class="muted">%</span></div><div class="kpi-note">Mean observed availability; span: {data['observed_span']}</div></div>
    <div class="kpi"><div class="kpi-label">Reports collected</div><div class="kpi-value">{data['report_count']}</div><div class="kpi-note">{data['reports_7d']} reports in rolling 7-day window</div></div>
  </div>

  <div class="layout">
    <div>
      <section class="panel">
        <div class="section-head"><h2>Endpoint health</h2><span class="pill neutral">{total} monitored</span></div>
        <div class="panel-note">Probe execution time is the total check duration, not individual ICMP round-trip latency. Availability uses collected checks in the rolling 7-day window. Observed span: {esc(data['observed_span'])}.</div>
        <div class="table-wrap"><table><thead><tr>
          <th>Endpoint / address</th><th>Status</th><th>Execution time</th><th>Loss</th><th>Availability</th><th>Replies</th>
        </tr></thead><tbody>
        {''.join(endpoint_rows) or '<tr><td colspan="6" class="muted">No monitoring reports found.</td></tr>'}
        </tbody></table></div>
      </section>

      <section class="panel">
        <div class="section-head"><h2>Recent reachability trend</h2><span class="pill neutral">Last {len(data['trend'])} checks</span></div>
        <div class="panel-note">Percentage of endpoints reachable in each recorded report. This is sampled history, not continuous uptime.</div>
        <div class="trend">{''.join(trend_bars) or '<div class="muted">No trend data available yet.</div>'}</div>
      </section>

      <section class="panel">
        <div class="section-head"><h2>Incident timeline</h2><span class="pill {'bad' if active_count else 'good'}">{active_count} active</span></div>
        <div class="panel-note">Outage events are raised after consecutive failed reports; recovery is recorded when reachability returns.</div>
        {''.join(active_rows) if active_rows else '<div class="incident-empty"><div class="check">✓</div><strong>No active incidents</strong><div class="sub">No unresolved outage events are recorded.</div></div>'}
        <div class="table-wrap" style="margin-top:16px"><table style="min-width:620px"><thead><tr><th>Time</th><th>Endpoint</th><th>Event</th><th>Details</th></tr></thead>
        <tbody>{''.join(incident_rows) or '<tr><td colspan="4" class="muted">No incidents recorded yet.</td></tr>'}</tbody></table></div>
      </section>
    </div>

    <aside>
      <section class="panel">
        <div class="section-head"><h2>Latest monitoring run</h2><span class="pill {freshness_class}">{'STALE' if stale else 'CURRENT' if latest else 'NO DATA'}</span></div>
        <div class="panel-note">{esc(report_status)}</div>
        <div class="meta-grid">
          <div class="meta-item"><div class="meta-label">Completed at</div><div class="meta-value mono">{esc(latest.get('finished_at') or latest.get('started_at') or '—')}</div></div>
          <div class="meta-item"><div class="meta-label">Monitoring host</div><div class="meta-value">{esc(latest.get('monitoring_host', '—'))}</div></div>
          <div class="meta-item"><div class="meta-label">Mode</div><div class="meta-value">{esc(mode)}</div></div>
          <div class="meta-item"><div class="meta-label">Probe type</div><div class="meta-value">{esc(latest.get('probe_type', 'ICMPv4'))}</div></div>
        </div>
        <div class="meta-item" style="margin-top:12px"><div class="meta-label">Evidence file</div><div class="meta-value mono">{esc(latest_file)}</div></div>
      </section>

      <section class="panel">
        <div class="section-head"><h2>Monitoring notes</h2></div>
        <div class="meta-item"><div class="meta-label">Data freshness</div><div class="meta-value">{esc(duration_text(latest_age))}</div><div class="sub">A run older than 10 minutes is marked stale.</div></div>
        <div class="meta-item" style="margin-top:10px"><div class="meta-label">Collection model</div><div class="meta-value">Scheduled ICMP probes</div><div class="sub">Results reflect point-in-time checks.</div></div>
        <div class="meta-item" style="margin-top:10px"><div class="meta-label">Interpretation</div><div class="sub">ICMP failure alone does not prove a host or application is down. Validate with routing, service, or device telemetry before escalating.</div></div>
      </section>
    </aside>
  </div>
</main>
<footer class="footer" id="footer">NETOPS SENTINEL · READ-ONLY EVIDENCE VIEW · Generated {esc(data['generated_at'])}</footer>
<script>
async function refreshDashboard() {{
  try {{
    const response = await fetch("/", {{cache: "no-store"}});
    if (!response.ok) return;
    const page = new DOMParser().parseFromString(await response.text(), "text/html");
    const updated = page.querySelector("#dashboard");
    const current = document.querySelector("#dashboard");
    if (updated && current) current.innerHTML = updated.innerHTML;
    const newFooter = page.querySelector("#footer");
    const footer = document.querySelector("#footer");
    if (newFooter && footer) footer.textContent = newFooter.textContent;
  }} catch (error) {{
    console.warn("Dashboard refresh failed", error);
  }}
}}
setInterval(refreshDashboard, 30000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/status":
            body = json.dumps(load_data(), indent=2).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif route in ("/", "/index.html"):
            body = make_page(load_data()).encode("utf-8")
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"Dashboard: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
