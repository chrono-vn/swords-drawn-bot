import discord
from discord import app_commands
from discord.ext import commands
from config import DISCORD_TOKEN, OFFICER_ROLE_IDS, CORE_MEMBER_ROLE_IDS
from db import init_db, get_current_charges, deduct_charge, next_charge_message
from sheets import log_commendation, update_members_tab

# ── Setup ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def has_any_role(member: discord.Member, role_ids: list) -> bool:
    return any(r.id in role_ids for r in member.roles)

# ── /commend ───────────────────────────────────────────────────────────────
@bot.tree.command(name="commend", description="Commend a guild member")
@app_commands.describe(member="The member to commend", reason="Why they deserve it")
async def commend(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.defer(ephemeral=True)

    giver = interaction.user

    if member.id == giver.id:
        await interaction.followup.send("You can't commend yourself.", ephemeral=True)
        return

    charges = get_current_charges(str(giver.id))
    if charges < 1:
        msg = next_charge_message(str(giver.id))
        await interaction.followup.send(
            f"You have no commendation charges left. {msg}", ephemeral=True
        )
        return

    try:
        log_commendation("commend", member.display_name, member.id,
                         giver.display_name, giver.id, reason)
        update_members_tab(member.display_name, member.id, "commend")
    except Exception as e:
        await interaction.followup.send(
            f"Something went wrong writing to the sheet: {e}", ephemeral=True
        )
        return

    deduct_charge(str(giver.id))

    await interaction.followup.send(
        f"✅ Commendation logged. You have **{charges - 1}** charge(s) remaining.",
        ephemeral=True
    )
    await interaction.channel.send(
        f"⭐ **{giver.display_name}** commended **{member.display_name}** — *{reason}*"
    )

# ── /demerit ───────────────────────────────────────────────────────────────
@bot.tree.command(name="demerit", description="Log a demerit against a member (Officer+ only)")
@app_commands.describe(member="The member", reason="Reason for the demerit")
async def demerit(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.defer(ephemeral=True)

    if not has_any_role(interaction.user, OFFICER_ROLE_IDS):
        await interaction.followup.send("You don't have permission to issue demerits.", ephemeral=True)
        return

    try:
        log_commendation("demerit", member.display_name, member.id,
                         interaction.user.display_name, interaction.user.id, reason)
        update_members_tab(member.display_name, member.id, "demerit")
    except Exception as e:
        await interaction.followup.send(f"Sheet write failed: {e}", ephemeral=True)
        return

    await interaction.followup.send(
        f"Demerit logged against {member.display_name}.", ephemeral=True
    )

# ── /commends ──────────────────────────────────────────────────────────────
@bot.tree.command(name="commends", description="Check a member's commendation count")
@app_commands.describe(member="The member to look up")
async def commends(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)

    if not has_any_role(interaction.user, CORE_MEMBER_ROLE_IDS):
        await interaction.followup.send("Core Member+ only.", ephemeral=True)
        return

    from sheets import get_sheet
    sheet   = get_sheet()
    members = sheet.worksheet("members")
    rows    = members.get_all_records()
    row     = next((r for r in rows if str(r["discord_id"]) == str(member.id)), None)

    if not row:
        await interaction.followup.send(f"{member.display_name} has no recorded commendations.", ephemeral=True)
        return

    await interaction.followup.send(
        f"**{member.display_name}** — ⭐ {row['commend_count']} commend(s), "
        f"❌ {row['demerit_count']} demerit(s)",
        ephemeral=True
    )

# ── /leaderboard ───────────────────────────────────────────────────────────
@bot.tree.command(name="leaderboard", description="Top 10 most commended members")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    from sheets import get_sheet
    sheet   = get_sheet()
    members = sheet.worksheet("members")
    rows    = members.get_all_records()

    sorted_rows = sorted(rows, key=lambda r: int(r["commend_count"] or 0), reverse=True)[:10]

    if not sorted_rows:
        await interaction.followup.send("No commendations recorded yet.")
        return

    lines = ["**⭐ Commendation Leaderboard**\n"]
    medals = ["🥇","🥈","🥉"]
    for i, row in enumerate(sorted_rows):
        prefix = medals[i] if i < 3 else f"`{i+1}.`"
        lines.append(f"{prefix} **{row['display_name']}** — {row['commend_count']} commend(s)")

    await interaction.followup.send("\n".join(lines))

# ── Startup ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"Bot online as {bot.user}")

bot.run(DISCORD_TOKEN)