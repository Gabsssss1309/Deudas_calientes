"""
Discord embed builder + sender for compliance alerts.
Generates rich embeds with obligation details and responsible mentions.
"""

import discord
from datetime import date

from models import Obligacion, MapeoResponsable

# Color map by urgency level
COLORS = {
    90: 0x3498DB,   # Blue — informativo
    30: 0xF1C40F,   # Yellow — advertencia
    15: 0xE67E22,   # Orange — urgente
    3:  0xE74C3C,   # Red — crítico
}

URGENCY_LABELS = {
    90: "📋 Recordatorio",
    30: "⚠️ Atención",
    15: "🔶 Urgente",
    3:  "🔴 Crítico",
}


def build_mention(obligacion: Obligacion, mapeo: dict[str, MapeoResponsable]) -> str:
    """
    Build the Discord mention string.
    Priority: obligacion.responsable_discord_id > mapeo by area > area name.
    """
    # Direct Discord ID on the obligation
    if obligacion.responsable_discord_id:
        discord_id = obligacion.responsable_discord_id
        # Detect if it's a role or user based on length/prefix convention
        # Discord IDs are snowflakes (17-20 digits)
        return f"<@{discord_id}>"

    # Fallback: area mapping
    area_map = mapeo.get(obligacion.area)
    if area_map:
        prefix = "@&" if area_map.tipo == "role" else "@"
        return f"<{prefix}{area_map.discord_id}>"

    # Last resort: just the area name
    return f"**{obligacion.area.capitalize()}**"


def build_alert_embed(
    obligacion: Obligacion,
    dias_restantes: int,
    threshold: int,
    deuda_nombre: str,
    mapeo: dict[str, MapeoResponsable],
) -> tuple[discord.Embed, str]:
    """
    Build a Discord Embed for a compliance alert.

    Returns:
        (embed, mention_text) — the embed and the mention string
        to include outside the embed so Discord pings the user/role.
    """
    color = COLORS.get(threshold, 0x95A5A6)
    label = URGENCY_LABELS.get(threshold, "📋 Recordatorio")
    mention = build_mention(obligacion, mapeo)

    embed = discord.Embed(
        title=f"{label} — Vencimiento en {dias_restantes} días",
        color=color,
    )

    embed.add_field(
        name="📄 Obligación",
        value=obligacion.descripcion[:1024],
        inline=False,
    )
    embed.add_field(
        name="🏗️ Proyecto / Deuda",
        value=deuda_nombre,
        inline=True,
    )
    embed.add_field(
        name="📅 Fecha de Vencimiento",
        value=obligacion.fecha_vencimiento.strftime("%d/%m/%Y"),
        inline=True,
    )
    embed.add_field(
        name="⏳ Días Restantes",
        value=str(dias_restantes),
        inline=True,
    )
    embed.add_field(
        name="🏢 Área",
        value=obligacion.area.capitalize(),
        inline=True,
    )
    embed.add_field(
        name="👤 Responsable",
        value=mention,
        inline=True,
    )
    embed.add_field(
        name="📊 Estatus",
        value=obligacion.estatus.replace("_", " ").capitalize(),
        inline=True,
    )

    if obligacion.notas:
        embed.add_field(
            name="📝 Notas",
            value=obligacion.notas[:1024],
            inline=False,
        )

    embed.set_footer(text=f"Debt Tracker — Alerta de Cumplimiento | ID: {str(obligacion.id)[:8]}")
    embed.timestamp = None  # The bot sets this at send time if needed

    # Mention goes outside embed so Discord actually pings
    return embed, mention


async def send_alert(
    channel: discord.TextChannel,
    obligacion: Obligacion,
    dias_restantes: int,
    threshold: int,
    deuda_nombre: str,
    mapeo: dict[str, MapeoResponsable],
) -> discord.Message:
    """
    Send a compliance alert embed to the specified Discord channel.
    Returns the sent message.
    """
    embed, mention = build_alert_embed(
        obligacion, dias_restantes, threshold, deuda_nombre, mapeo,
    )

    return await channel.send(
        content=f"🔔 {mention} — Obligación próxima a vencer:",
        embed=embed,
    )
