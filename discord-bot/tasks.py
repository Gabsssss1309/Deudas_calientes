"""
Task Runner — Daily covenant compliance checker.

Runs once per day (configurable hour). For each active obligation:
  1. Divides its full period (periodo_dias) into 3 equal intervals.
  2. Sends a Discord embed when TODAY matches one of those 3 dates (±1 day):
       Alert 1 → due_date − ⌊period × 2/3⌋  (early warning)
       Alert 2 → due_date − ⌊period × 1/3⌋  (midpoint reminder)
       Alert 3 → due_date                    (deadline)
  3. Uses AlertaEnviada to guarantee each alert fires exactly once.
  4. Auto-marks obligations past due as 'vencido'.

Obligations without periodo_dias fall back to the legacy threshold system
(90 / 30 / 15 / 3 days) for backwards compatibility.
"""

import logging
from datetime import date, timedelta
from math import floor

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from db import async_session
from models import Obligacion, Deuda, MapeoResponsable, AlertaEnviada
from alerts import send_alert, send_period_alert
from config import config

logger = logging.getLogger("covenant-bot.tasks")

TOLERANCE = 1   # ± days — lets a job that slips by 1 day still fire


async def load_mapeo() -> dict[str, MapeoResponsable]:
    """Load the area → Discord ID mapping into a dict keyed by area."""
    async with async_session() as session:
        result = await session.execute(select(MapeoResponsable))
        rows = result.scalars().all()
        return {r.area: r for r in rows}


def _period_alert_schedule(periodo_dias: int) -> list[tuple[int, int]]:
    """
    Return [(dias_antes, alert_num), ...] for the 3 equidistant alerts.

    dias_antes  — days before the due date when the alert should fire
    alert_num   — 1 (early), 2 (mid), 3 (due date)
    """
    third = periodo_dias / 3
    return [
        (floor(third * 2), 1),   # 2/3 of period remaining
        (floor(third),     2),   # 1/3 of period remaining
        (0,                3),   # due date
    ]


def _is_alert_day(dias_restantes: int, dias_antes: int) -> bool:
    return abs(dias_restantes - dias_antes) <= TOLERANCE


async def _get_or_fetch_channel(bot, channel_id: int):
    channel = bot.get_channel(channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            logger.error(f"Cannot fetch channel {channel_id}: {e}")
            return None
    return channel


async def check_vencimientos(bot) -> dict:
    """
    Main daily task. Scans obligations and sends alerts.
    Returns a summary dict with counts.
    """
    today  = date.today()
    stats  = {"checked": 0, "alerts_sent": 0, "marked_vencido": 0, "errors": 0}
    mapeo  = await load_mapeo()

    # Legacy thresholds (for obligations without periodo_dias)
    legacy_thresholds = sorted(config.alert_thresholds, reverse=True)  # [90,30,15,3]
    max_legacy_window = today + timedelta(days=max(legacy_thresholds))

    async with async_session() as session:
        query = (
            select(Obligacion)
            .options(selectinload(Obligacion.deuda))
            .where(Obligacion.estatus.in_(["pendiente", "en_progreso"]))
            .order_by(Obligacion.fecha_vencimiento)
        )
        result     = await session.execute(query)
        obligaciones = result.scalars().all()
        stats["checked"] = len(obligaciones)

        logger.info(f"Checking {len(obligaciones)} active obligations")

        for ob in obligaciones:
            dias_restantes = (ob.fecha_vencimiento - today).days

            # ── Auto-mark overdue ─────────────────────────────────────────
            if dias_restantes < 0:
                ob.estatus = "vencido"
                session.add(ob)
                stats["marked_vencido"] += 1
                logger.info(f"Marked vencido: {ob.id} (overdue {-dias_restantes}d)")
                continue

            # ── Resolve alert channel ─────────────────────────────────────
            channel_id = config.alert_channel_id
            if ob.deuda and ob.deuda.discord_canal_id:
                try:
                    channel_id = int(ob.deuda.discord_canal_id)
                except (ValueError, TypeError):
                    pass

            if not channel_id:
                logger.warning(f"No alert channel for obligation {ob.id}")
                stats["errors"] += 1
                continue

            channel = await _get_or_fetch_channel(bot, channel_id)
            if not channel:
                stats["errors"] += 1
                continue

            deuda_nombre = ob.deuda.nombre if ob.deuda else "N/A"

            # ── 3-period equidistant logic ────────────────────────────────
            if ob.periodo_dias:
                schedule = _period_alert_schedule(ob.periodo_dias)

                for dias_antes, alert_num in schedule:
                    if not _is_alert_day(dias_restantes, dias_antes):
                        continue

                    # Dedup check
                    existing = await session.execute(
                        select(AlertaEnviada).where(
                            and_(
                                AlertaEnviada.obligacion_id == ob.id,
                                AlertaEnviada.dias_antes    == dias_antes,
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    try:
                        await send_period_alert(
                            channel       = channel,
                            obligacion    = ob,
                            dias_restantes= dias_restantes,
                            alert_num     = alert_num,
                            periodo_dias  = ob.periodo_dias,
                            deuda_nombre  = deuda_nombre,
                            mapeo         = mapeo,
                        )
                        session.add(AlertaEnviada(
                            obligacion_id  = ob.id,
                            dias_antes     = dias_antes,
                            canal_discord_id = str(channel_id),
                        ))
                        stats["alerts_sent"] += 1
                        logger.info(
                            f"Period alert {alert_num}/3 sent: "
                            f"{ob.descripcion[:50]}… | {dias_restantes}d remaining"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send period alert for {ob.id}: {e}")
                        stats["errors"] += 1

                    break   # one alert per obligation per run

            # ── Legacy threshold logic (no periodo_dias) ──────────────────
            else:
                if ob.fecha_vencimiento > max_legacy_window:
                    continue

                for threshold in legacy_thresholds:
                    if dias_restantes > threshold:
                        continue

                    existing = await session.execute(
                        select(AlertaEnviada).where(
                            and_(
                                AlertaEnviada.obligacion_id == ob.id,
                                AlertaEnviada.dias_antes    == threshold,
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    try:
                        await send_alert(
                            channel       = channel,
                            obligacion    = ob,
                            dias_restantes= dias_restantes,
                            threshold     = threshold,
                            deuda_nombre  = deuda_nombre,
                            mapeo         = mapeo,
                        )
                        session.add(AlertaEnviada(
                            obligacion_id    = ob.id,
                            dias_antes       = threshold,
                            canal_discord_id = str(channel_id),
                        ))
                        stats["alerts_sent"] += 1
                        logger.info(
                            f"Legacy alert sent: {ob.descripcion[:50]}… | "
                            f"{dias_restantes}d remaining (threshold={threshold}d)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send legacy alert for {ob.id}: {e}")
                        stats["errors"] += 1

                    break

        await session.commit()

    logger.info(
        f"Daily check complete: {stats['checked']} checked, "
        f"{stats['alerts_sent']} alerts sent, "
        f"{stats['marked_vencido']} marked vencido, "
        f"{stats['errors']} errors"
    )
    return stats
