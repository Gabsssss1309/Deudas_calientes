"""
Task Runner — Daily covenant compliance checker.

Runs once per day (configurable hour). For each active obligation:
  1. Calculates days until fecha_vencimiento.
  2. If days match a threshold (90, 30, 15, 3) AND no alert was sent for that
     threshold, sends a Discord embed and records it in alertas_enviadas.
  3. Auto-marks obligations past due as 'vencido'.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from db import async_session
from models import Obligacion, Deuda, MapeoResponsable, AlertaEnviada
from alerts import send_alert
from config import config

logger = logging.getLogger("covenant-bot.tasks")


async def load_mapeo() -> dict[str, MapeoResponsable]:
    """Load the area → Discord ID mapping into a dict keyed by area."""
    async with async_session() as session:
        result = await session.execute(select(MapeoResponsable))
        rows = result.scalars().all()
        return {r.area: r for r in rows}


async def check_vencimientos(bot) -> dict:
    """
    Main daily task. Scans obligations and sends alerts.

    Returns a summary dict with counts.
    """
    today = date.today()
    thresholds = sorted(config.alert_thresholds, reverse=True)  # [90, 30, 15, 3]
    stats = {"checked": 0, "alerts_sent": 0, "marked_vencido": 0, "errors": 0}

    # Determine the widest window we need (90 days ahead)
    max_window = today + timedelta(days=max(thresholds))

    mapeo = await load_mapeo()

    async with async_session() as session:
        # Fetch active obligations within the alert window
        query = (
            select(Obligacion)
            .options(selectinload(Obligacion.deuda))
            .where(
                and_(
                    Obligacion.estatus.in_(["pendiente", "en_progreso"]),
                    Obligacion.fecha_vencimiento <= max_window,
                )
            )
            .order_by(Obligacion.fecha_vencimiento)
        )
        result = await session.execute(query)
        obligaciones = result.scalars().all()

        stats["checked"] = len(obligaciones)
        logger.info(f"Checking {len(obligaciones)} active obligations (window: today → {max_window})")

        for ob in obligaciones:
            dias_restantes = (ob.fecha_vencimiento - today).days

            # --- Auto-mark vencido ---
            if dias_restantes < 0:
                ob.estatus = "vencido"
                session.add(ob)
                stats["marked_vencido"] += 1
                logger.info(f"Obligation {ob.id} marked as vencido (overdue by {-dias_restantes} days)")
                continue

            # --- Check each threshold ---
            for threshold in thresholds:
                if dias_restantes > threshold:
                    continue  # Not yet in this threshold window

                if dias_restantes <= threshold:
                    # Check if alert already sent for this threshold
                    existing = await session.execute(
                        select(AlertaEnviada).where(
                            and_(
                                AlertaEnviada.obligacion_id == ob.id,
                                AlertaEnviada.dias_antes == threshold,
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Already sent

                    # Resolve the alert channel
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

                    channel = bot.get_channel(channel_id)
                    if not channel:
                        try:
                            channel = await bot.fetch_channel(channel_id)
                        except Exception as e:
                            logger.error(f"Cannot fetch channel {channel_id}: {e}")
                            stats["errors"] += 1
                            continue

                    # Send the alert
                    try:
                        deuda_nombre = ob.deuda.nombre if ob.deuda else "N/A"
                        await send_alert(
                            channel=channel,
                            obligacion=ob,
                            dias_restantes=dias_restantes,
                            threshold=threshold,
                            deuda_nombre=deuda_nombre,
                            mapeo=mapeo,
                        )

                        # Record the sent alert
                        alerta = AlertaEnviada(
                            obligacion_id=ob.id,
                            dias_antes=threshold,
                            canal_discord_id=str(channel_id),
                        )
                        session.add(alerta)
                        stats["alerts_sent"] += 1
                        logger.info(
                            f"Alert sent: {ob.descripcion[:50]}... | "
                            f"{dias_restantes}d remaining (threshold={threshold}d)"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send alert for {ob.id}: {e}")
                        stats["errors"] += 1

                    break  # Only send the most relevant threshold per obligation per run

        await session.commit()

    logger.info(
        f"Daily check complete: {stats['checked']} checked, "
        f"{stats['alerts_sent']} alerts sent, "
        f"{stats['marked_vencido']} marked vencido, "
        f"{stats['errors']} errors"
    )
    return stats
