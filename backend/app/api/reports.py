import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.metric import Metric
from app.models.alert import AlertEvent, AlertRule
from app.models.machine import Machine
from app.models.company import Company

router = APIRouter(prefix="/api/reports", tags=["reports"])

# ── Shared PDF helpers ─────────────────────────────────────────────────────

TEAL        = (0x2d / 255, 0xd4 / 255, 0xbf / 255)   # #2dd4bf
DARK_NAVY   = (0x05 / 255, 0x0a / 255, 0x12 / 255)
MID_NAVY    = (0x0a / 255, 0x12 / 255, 0x20 / 255)
WHITE       = (1, 1, 1)
LIGHT_GREY  = (0.95, 0.95, 0.95)
SLATE       = (0.58, 0.64, 0.72)
TEXT_DARK   = (0.13, 0.16, 0.20)
RED         = (0.94, 0.27, 0.27)
AMBER       = (0.96, 0.62, 0.04)


def _build_pdf_machine(machine: Machine, metrics: list, from_dt, to_dt) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    rl_teal   = colors.Color(*TEAL)
    rl_navy   = colors.Color(*DARK_NAVY)
    rl_mid    = colors.Color(*MID_NAVY)
    rl_slate  = colors.Color(*SLATE)
    rl_lgrey  = colors.Color(*LIGHT_GREY)
    rl_red    = colors.Color(*RED)
    rl_amber  = colors.Color(*AMBER)

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20,
                        textColor=rl_navy, spaceAfter=2)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12,
                        textColor=rl_teal, spaceAfter=6)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                          textColor=colors.Color(*TEXT_DARK), spaceAfter=4)
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                           textColor=rl_slate)
    hdr_lbl = ParagraphStyle("lbl", fontName="Helvetica", fontSize=7,
                             textColor=rl_slate, spaceAfter=1)
    hdr_val = ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=11,
                             textColor=rl_navy)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    from_str  = from_dt.strftime("%Y-%m-%d") if from_dt else "All time"
    to_str    = to_dt.strftime("%Y-%m-%d")   if to_dt   else "Now"

    # ── Summary stats ──────────────────────────────────────────────────────
    cpu_vals  = [m.cpu_percent  for m in metrics if m.cpu_percent  is not None]
    ram_vals  = [m.ram_percent  for m in metrics if m.ram_percent  is not None]
    net_sent  = [m.net_sent_mb  for m in metrics if m.net_sent_mb  is not None]
    net_recv  = [m.net_recv_mb  for m in metrics if m.net_recv_mb  is not None]

    avg_cpu = sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0
    max_cpu = max(cpu_vals) if cpu_vals else 0
    avg_ram = sum(ram_vals) / len(ram_vals) if ram_vals else 0
    max_ram = max(ram_vals) if ram_vals else 0
    tot_sent = sum(net_sent) if net_sent else 0
    tot_recv = sum(net_recv) if net_recv else 0

    def stat_cell(label, value):
        return [Paragraph(label, hdr_lbl), Paragraph(value, hdr_val)]

    stat_data = [[
        stat_cell("AVG CPU",       f"{avg_cpu:.1f}%"),
        stat_cell("PEAK CPU",      f"{max_cpu:.1f}%"),
        stat_cell("AVG RAM",       f"{avg_ram:.1f}%"),
        stat_cell("PEAK RAM",      f"{max_ram:.1f}%"),
        stat_cell("NET SENT",      f"{tot_sent/1024:.2f} GB" if tot_sent > 1024 else f"{tot_sent:.0f} MB"),
        stat_cell("NET RECV",      f"{tot_recv/1024:.2f} GB" if tot_recv > 1024 else f"{tot_recv:.0f} MB"),
        stat_cell("DATA POINTS",   str(len(metrics))),
    ]]
    stat_table = Table(stat_data, colWidths=[35*mm]*7)
    stat_table.setStyle(TableStyle([
        ("BOX",        (0,0), (-1,-1), 0.5, rl_teal),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, colors.Color(0.45, 0.84, 0.75, 0.3)),
        ("BACKGROUND", (0,0), (-1,-1), rl_lgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))

    # ── Data table — downsample to max 200 rows ────────────────────────────
    step = max(1, len(metrics) // 200)
    rows = metrics[::step]

    col_hdrs = ["Timestamp", "CPU %", "RAM %", "CPU Freq MHz",
                "RAM Used GB", "Net Sent MB", "Net Recv MB", "Latency ms"]
    table_data = [col_hdrs]
    for m in rows:
        def _v(val, dec=1):
            return f"{val:.{dec}f}" if val is not None else "—"
        table_data.append([
            m.collected_at.strftime("%Y-%m-%d %H:%M") if m.collected_at else "—",
            _v(m.cpu_percent), _v(m.ram_percent), _v(m.cpu_freq_mhz, 0),
            _v(m.ram_used_gb, 2), _v(m.net_sent_mb, 1), _v(m.net_recv_mb, 1),
            _v(m.net_latency_ms, 0),
        ])

    col_w = [42*mm, 18*mm, 18*mm, 26*mm, 22*mm, 24*mm, 24*mm, 22*mm]
    data_table = Table(table_data, colWidths=col_w, repeatRows=1)

    row_styles = [
        ("BACKGROUND",  (0,0), (-1,0),  rl_navy),
        ("TEXTCOLOR",   (0,0), (-1,0),  rl_teal),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  8),
        ("FONTSIZE",    (0,1), (-1,-1), 7.5),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",   (0,1), (-1,-1), colors.Color(*TEXT_DARK)),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("ALIGN",       (0,0), (0,-1),  "LEFT"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, rl_lgrey]),
        ("LINEBELOW",   (0,0), (-1,0),  1.0, rl_teal),
        ("LINEBELOW",   (0,1), (-1,-1), 0.3, colors.Color(0.85, 0.85, 0.85)),
    ]

    # Highlight high CPU/RAM rows
    for i, m in enumerate(rows, start=1):
        if m.cpu_percent and m.cpu_percent >= 90:
            row_styles.append(("BACKGROUND", (1,i), (1,i), colors.Color(*RED, 0.15)))
        elif m.cpu_percent and m.cpu_percent >= 70:
            row_styles.append(("BACKGROUND", (1,i), (1,i), colors.Color(*AMBER, 0.15)))
        if m.ram_percent and m.ram_percent >= 90:
            row_styles.append(("BACKGROUND", (2,i), (2,i), colors.Color(*RED, 0.15)))
        elif m.ram_percent and m.ram_percent >= 70:
            row_styles.append(("BACKGROUND", (2,i), (2,i), colors.Color(*AMBER, 0.15)))

    data_table.setStyle(TableStyle(row_styles))

    # ── Assemble document ──────────────────────────────────────────────────
    def on_page(canvas, doc):
        w, h = landscape(A4)
        canvas.saveState()
        # Top bar
        canvas.setFillColor(rl_navy)
        canvas.rect(0, h - 22*mm, w, 22*mm, fill=1, stroke=0)
        canvas.setFillColor(rl_teal)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(18*mm, h - 13*mm, "Numbers10 Technology Solutions")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 18*mm, h - 10*mm, f"Generated: {generated}")
        canvas.drawRightString(w - 18*mm, h - 17*mm, f"Page {doc.page}")
        # Bottom bar
        canvas.setFillColor(rl_navy)
        canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
        canvas.setFillColor(rl_teal)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18*mm, 3.5*mm, "Numbers10 PCMonitor  |  Confidential")
        canvas.restoreState()

    story = [
        Spacer(1, 6*mm),
        Paragraph(f"Machine Metrics Report", h1),
        Paragraph(f"{machine.hostname}  ·  {machine.os_version or ''}  ·  {machine.ip_address or ''}", body),
        HRFlowable(width="100%", thickness=1, color=rl_teal, spaceAfter=8),
        Paragraph(f"Period: {from_str}  →  {to_str}", small),
        Spacer(1, 4*mm),
        Paragraph("SUMMARY", h2),
        stat_table,
        Spacer(1, 6*mm),
        Paragraph("METRICS DATA", h2),
        Paragraph(
            f"Showing {len(rows)} of {len(metrics)} records"
            + (f" (sampled every {step} readings)" if step > 1 else ""),
            small
        ),
        Spacer(1, 2*mm),
        data_table,
    ]

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _build_pdf_alerts(events: list, rules: dict, machines: dict, from_dt, to_dt) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    rl_teal  = colors.Color(*TEAL)
    rl_navy  = colors.Color(*DARK_NAVY)
    rl_lgrey = colors.Color(*LIGHT_GREY)
    rl_red   = colors.Color(*RED)
    rl_amber = colors.Color(*AMBER)
    rl_info  = colors.Color(*TEAL)

    h1    = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, textColor=rl_navy, spaceAfter=2)
    h2    = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, textColor=rl_teal, spaceAfter=6)
    body  = ParagraphStyle("body", fontName="Helvetica", fontSize=9, textColor=colors.Color(*TEXT_DARK))
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=8, textColor=colors.Color(*SLATE))
    lbl   = ParagraphStyle("lbl", fontName="Helvetica", fontSize=7, textColor=colors.Color(*SLATE), spaceAfter=1)
    val   = ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=13, textColor=rl_navy)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    from_str  = from_dt.strftime("%Y-%m-%d") if from_dt else "All time"
    to_str    = to_dt.strftime("%Y-%m-%d")   if to_dt   else "Now"

    sev_counts = {"critical": 0, "warning": 0, "info": 0}
    resolved = sum(1 for e in events if e.resolved_at)
    for e in events:
        rule = rules.get(e.rule_id)
        if rule:
            sev_counts[rule.severity] = sev_counts.get(rule.severity, 0) + 1

    def stat_cell(label, value, color=None):
        v_style = ParagraphStyle("v2", fontName="Helvetica-Bold", fontSize=13,
                                 textColor=color or rl_navy)
        return [Paragraph(label, lbl), Paragraph(str(value), v_style)]

    stat_data = [[
        stat_cell("TOTAL ALERTS",  len(events)),
        stat_cell("CRITICAL",      sev_counts.get("critical", 0), rl_red),
        stat_cell("WARNING",       sev_counts.get("warning",  0), rl_amber),
        stat_cell("INFO",          sev_counts.get("info",     0), rl_info),
        stat_cell("RESOLVED",      resolved),
        stat_cell("UNRESOLVED",    len(events) - resolved),
    ]]
    stat_table = Table(stat_data, colWidths=[28*mm]*6)
    stat_table.setStyle(TableStyle([
        ("BOX",        (0,0), (-1,-1), 0.5, rl_teal),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, colors.Color(0.45, 0.84, 0.75, 0.3)),
        ("BACKGROUND", (0,0), (-1,-1), rl_lgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))

    col_hdrs = ["Triggered", "Machine", "Rule", "Severity", "Value", "Resolved", "Ack"]
    table_data = [col_hdrs]
    SEV_COLORS = {"critical": rl_red, "warning": rl_amber, "info": rl_info}

    for e in events:
        rule    = rules.get(e.rule_id)
        machine = machines.get(e.machine_id)
        table_data.append([
            e.triggered_at.strftime("%Y-%m-%d %H:%M") if e.triggered_at else "—",
            machine.hostname if machine else str(e.machine_id),
            rule.name        if rule    else str(e.rule_id),
            (rule.severity.upper() if rule else "—"),
            f"{e.current_value:.2f}" if e.current_value is not None else "—",
            e.resolved_at.strftime("%H:%M") if e.resolved_at else "Active",
            "Yes" if e.acknowledged else "No",
        ])

    col_w = [32*mm, 32*mm, 42*mm, 20*mm, 18*mm, 20*mm, 12*mm]
    data_table = Table(table_data, colWidths=col_w, repeatRows=1)

    row_styles = [
        ("BACKGROUND",  (0,0), (-1,0),  rl_navy),
        ("TEXTCOLOR",   (0,0), (-1,0),  rl_teal),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  8),
        ("FONTSIZE",    (0,1), (-1,-1), 7.5),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR",   (0,1), (-1,-1), colors.Color(*TEXT_DARK)),
        ("ALIGN",       (3,0), (-1,-1), "CENTER"),
        ("ALIGN",       (0,0), (2,-1),  "LEFT"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, rl_lgrey]),
        ("LINEBELOW",   (0,0), (-1,0),  1.0, rl_teal),
        ("LINEBELOW",   (0,1), (-1,-1), 0.3, colors.Color(0.85, 0.85, 0.85)),
    ]

    for i, e in enumerate(events, start=1):
        rule = rules.get(e.rule_id)
        sev  = rule.severity if rule else "info"
        c    = SEV_COLORS.get(sev, rl_info)
        row_styles.append(("TEXTCOLOR",   (3,i), (3,i), c))
        row_styles.append(("FONTNAME",    (3,i), (3,i), "Helvetica-Bold"))
        if not e.resolved_at:
            row_styles.append(("TEXTCOLOR", (5,i), (5,i), rl_red))
            row_styles.append(("FONTNAME",  (5,i), (5,i), "Helvetica-Bold"))

    data_table.setStyle(TableStyle(row_styles))

    def on_page(canvas, doc):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(rl_navy)
        canvas.rect(0, h - 22*mm, w, 22*mm, fill=1, stroke=0)
        canvas.setFillColor(rl_teal)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(18*mm, h - 13*mm, "Numbers10 Technology Solutions")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 18*mm, h - 10*mm, f"Generated: {generated}")
        canvas.drawRightString(w - 18*mm, h - 17*mm, f"Page {doc.page}")
        canvas.setFillColor(rl_navy)
        canvas.rect(0, 0, w, 10*mm, fill=1, stroke=0)
        canvas.setFillColor(rl_teal)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18*mm, 3.5*mm, "Numbers10 PCMonitor  |  Confidential")
        canvas.restoreState()

    story = [
        Spacer(1, 6*mm),
        Paragraph("Alert Events Report", h1),
        HRFlowable(width="100%", thickness=1, color=rl_teal, spaceAfter=8),
        Paragraph(f"Period: {from_str}  →  {to_str}", small),
        Spacer(1, 4*mm),
        Paragraph("SUMMARY", h2),
        stat_table,
        Spacer(1, 6*mm),
        Paragraph("ALERT EVENTS", h2),
        Spacer(1, 2*mm),
        data_table,
    ]
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


# ── API endpoints ──────────────────────────────────────────────────────────

@router.get("/machine/{machine_id}")
async def export_machine_metrics(
    machine_id: int,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt:   Optional[datetime] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    machine_result = await db.execute(select(Machine).where(Machine.id == machine_id))
    machine = machine_result.scalar_one_or_none()

    query = select(Metric).where(Metric.machine_id == machine_id)
    if from_dt:
        query = query.where(Metric.collected_at >= from_dt)
    if to_dt:
        query = query.where(Metric.collected_at <= to_dt)
    query = query.order_by(Metric.collected_at.asc())

    result  = await db.execute(query)
    metrics = result.scalars().all()

    pdf_bytes = _build_pdf_machine(machine, metrics, from_dt, to_dt)
    filename  = f"metrics_{machine.hostname}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/alerts")
async def export_alerts(
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt:   Optional[datetime] = Query(None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlertEvent)
    if from_dt:
        query = query.where(AlertEvent.triggered_at >= from_dt)
    if to_dt:
        query = query.where(AlertEvent.triggered_at <= to_dt)
    query = query.order_by(AlertEvent.triggered_at.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    rule_ids    = {e.rule_id    for e in events if e.rule_id}
    machine_ids = {e.machine_id for e in events if e.machine_id}

    rules_result    = await db.execute(select(AlertRule).where(AlertRule.id.in_(rule_ids)))
    machines_result = await db.execute(select(Machine).where(Machine.id.in_(machine_ids)))
    rules    = {r.id: r for r in rules_result.scalars().all()}
    machines = {m.id: m for m in machines_result.scalars().all()}

    pdf_bytes = _build_pdf_alerts(events, rules, machines, from_dt, to_dt)
    filename  = f"alerts_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
