"""
Slash commands for the Covenant Compliance bot.
"""

import logging
import traceback

import discord
from discord import app_commands
from sqlalchemy import select

from db import async_session
from models import MapeoResponsable, Obligacion, Deuda

logger = logging.getLogger("covenant-bot.commands")

# Valid areas (must match the DB constraint)
AREAS = [
    app_commands.Choice(name="Legal", value="legal"),
    app_commands.Choice(name="Técnica", value="tecnica"),
    app_commands.Choice(name="Financiera", value="financiera"),
    app_commands.Choice(name="Seguros", value="seguros"),
    app_commands.Choice(name="Ambiental", value="ambiental"),
    app_commands.Choice(name="Operaciones", value="operaciones"),
    app_commands.Choice(name="Compliance", value="compliance"),
    app_commands.Choice(name="Gerencia", value="gerencia"),
]


def register_commands(tree: app_commands.CommandTree):
    """Register all slash commands on the given command tree."""

    @tree.command(
        name="asignar_responsable",
        description="Vincular un área de cumplimiento a un usuario o rol de Discord",
    )
    @app_commands.describe(
        area="Área de cumplimiento",
        mencion="Usuario o Rol de Discord responsable",
        nombre="Nombre descriptivo (ej. 'Equipo Legal')",
    )
    @app_commands.choices(area=AREAS)
    async def asignar_responsable(
        interaction: discord.Interaction,
        area: app_commands.Choice[str],
        mencion: discord.Role | discord.Member,
        nombre: str | None = None,
    ):
        """
        /asignar_responsable area:Legal mencion:@EquipoLegal nombre:"Equipo Legal"

        Maps an area to a Discord user or role. The bot will mention this
        entity in compliance alerts for obligations in that area.
        """
        try:
            # Determine type
            is_role = isinstance(mencion, discord.Role)
            tipo = "role" if is_role else "user"
            discord_id = str(mencion.id)
            display_name = nombre or mencion.name

            async with async_session() as session:
                # Upsert: check if area already exists
                result = await session.execute(
                    select(MapeoResponsable).where(MapeoResponsable.area == area.value)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.discord_id = discord_id
                    existing.tipo = tipo
                    existing.nombre = display_name
                    session.add(existing)
                    action = "actualizado"
                else:
                    new_mapeo = MapeoResponsable(
                        area=area.value,
                        discord_id=discord_id,
                        tipo=tipo,
                        nombre=display_name,
                    )
                    session.add(new_mapeo)
                    action = "creado"

                await session.commit()

            prefix = "@&" if is_role else "@"
            embed = discord.Embed(
                title="✅ Responsable Asignado",
                color=0x915BD8,  # Unergy purple
                description=(
                    f"**Área:** {area.name}\n"
                    f"**Responsable:** <{prefix}{discord_id}> ({display_name})\n"
                    f"**Tipo:** {'Rol' if is_role else 'Usuario'}\n\n"
                    f"Mapeo {action} correctamente."
                ),
            )
            embed.set_footer(text="Debt Tracker — Compliance Alerts")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.exception(f"Error en /asignar_responsable: {e}")
            try:
                await interaction.response.send_message(
                    f"❌ Error al asignar responsable: {type(e).__name__}: {e}",
                    ephemeral=True,
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"❌ Error al asignar responsable: {type(e).__name__}: {e}",
                    ephemeral=True,
                )

    @tree.command(
        name="ver_responsables",
        description="Ver el mapeo actual de áreas a responsables de Discord",
    )
    async def ver_responsables(interaction: discord.Interaction):
        """Show the current area → Discord mapping."""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(MapeoResponsable).order_by(MapeoResponsable.area)
                )
                rows = result.scalars().all()

            if not rows:
                await interaction.response.send_message(
                    "No hay responsables asignados. Usa `/asignar_responsable` para configurar.",
                    ephemeral=True,
                )
                return

            lines = []
            for r in rows:
                prefix = "@&" if r.tipo == "role" else "@"
                lines.append(f"**{r.area.capitalize()}** → <{prefix}{r.discord_id}> ({r.nombre or 'sin nombre'})")

            embed = discord.Embed(
                title="📋 Mapeo de Responsables",
                color=0x915BD8,
                description="\n".join(lines),
            )
            embed.set_footer(text="Debt Tracker — Compliance Alerts")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.exception(f"Error en /ver_responsables: {e}")
            try:
                await interaction.response.send_message(
                    f"❌ Error: {type(e).__name__}: {e}", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"❌ Error: {type(e).__name__}: {e}", ephemeral=True
                )

    @tree.command(
        name="proximos_vencimientos",
        description="Ver obligaciones próximas a vencer (próximos 30 días)",
    )
    @app_commands.describe(dias="Ventana en días (default: 30)")
    async def proximos_vencimientos(
        interaction: discord.Interaction,
        dias: int = 30,
    ):
        """Show upcoming obligations within the specified window."""
        try:
            from datetime import date, timedelta

            today = date.today()
            window = today + timedelta(days=dias)

            async with async_session() as session:
                query = (
                    select(Obligacion)
                    .join(Deuda, Obligacion.deuda_id == Deuda.id)
                    .where(
                        Obligacion.estatus.in_(["pendiente", "en_progreso"]),
                        Obligacion.fecha_vencimiento.between(today, window),
                    )
                    .order_by(Obligacion.fecha_vencimiento)
                    .limit(15)
                )
                result = await session.execute(query)
                rows = result.scalars().all()

            if not rows:
                await interaction.response.send_message(
                    f"No hay obligaciones con vencimiento en los próximos {dias} días. ✅",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title=f"⏳ Próximos Vencimientos ({dias} días)",
                color=0xF1C40F,
            )
            for ob in rows:
                dias_rest = (ob.fecha_vencimiento - today).days
                emoji = "🔴" if dias_rest <= 3 else "🟠" if dias_rest <= 15 else "🟡" if dias_rest <= 30 else "🔵"
                embed.add_field(
                    name=f"{emoji} {ob.descripcion[:80]}",
                    value=(
                        f"📅 {ob.fecha_vencimiento.strftime('%d/%m/%Y')} "
                        f"({dias_rest}d) | 🏢 {ob.area.capitalize()} | "
                        f"Estado: {ob.estatus}"
                    ),
                    inline=False,
                )

            embed.set_footer(text=f"Mostrando máx. 15 de {len(rows)} | Debt Tracker")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.exception(f"Error en /proximos_vencimientos: {e}")
            try:
                await interaction.response.send_message(
                    f"❌ Error: {type(e).__name__}: {e}", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    f"❌ Error: {type(e).__name__}: {e}", ephemeral=True
                )

    @tree.command(
        name="check_ahora",
        description="Ejecutar manualmente el chequeo diario de vencimientos",
    )
    async def check_ahora(interaction: discord.Interaction):
        """Manually trigger the daily compliance check."""
        await interaction.response.defer(thinking=True)

        try:
            from tasks import check_vencimientos
            stats = await check_vencimientos(interaction.client)

            embed = discord.Embed(
                title="✅ Chequeo Manual Completado",
                color=0x2ECC71,
                description=(
                    f"**Obligaciones revisadas:** {stats['checked']}\n"
                    f"**Alertas enviadas:** {stats['alerts_sent']}\n"
                    f"**Marcadas vencidas:** {stats['marked_vencido']}\n"
                    f"**Errores:** {stats['errors']}"
                ),
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.exception(f"Error en /check_ahora: {e}")
            await interaction.followup.send(
                f"❌ Error en chequeo: {type(e).__name__}: {e}"
            )
