"""
Covenant Compliance Bot — Entry Point

Standalone Discord bot that monitors obligaciones and sends
alerts at 90, 30, 15, and 3 days before due dates.

Based on Edubot patterns (SQLAlchemy async + discord.py + tasks.loop).
Connects to the same Supabase PostgreSQL as the Debt Tracker web app.
"""

import logging
import asyncio
from datetime import time

import discord
from discord.ext import tasks

from config import config
from commands import register_commands
from tasks import check_vencimientos

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("covenant-bot")


# --- Bot Setup ---
intents = discord.Intents.default()
intents.members = True  # Needed to resolve member mentions

bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)


# --- Daily Task Loop (discord.py tasks.loop) ---
@tasks.loop(time=time(hour=config.check_hour, minute=0))
async def daily_check():
    """Runs once per day at the configured hour."""
    logger.info("Starting daily compliance check...")
    try:
        stats = await check_vencimientos(bot)
        logger.info(f"Daily check stats: {stats}")
    except Exception as e:
        logger.exception(f"Daily check failed: {e}")


@daily_check.before_loop
async def before_daily_check():
    """Wait until the bot is fully ready before starting the loop."""
    await bot.wait_until_ready()
    logger.info(f"Daily check loop scheduled at {config.check_hour}:00 ({config.timezone})")


# --- Events ---
@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Guilds: {[g.name for g in bot.guilds]}")

    # Register slash commands and sync to each guild (instant, not global)
    register_commands(tree)
    for guild in bot.guilds:
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        logger.info(f"Slash commands synced to guild: {guild.name}")
    logger.info("All slash commands synced")

    # Start daily task
    if not daily_check.is_running():
        daily_check.start()
        logger.info("Daily compliance check task started")


# --- Main ---
def main():
    logger.info("Starting Covenant Compliance Bot...")
    logger.info(f"Alert channel: {config.alert_channel_id}")
    logger.info(f"Daily check hour: {config.check_hour}:00")
    logger.info(f"Alert thresholds: {config.alert_thresholds} days")

    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
