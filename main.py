import discord
from discord import app_commands
from discord.ext import commands
import datetime

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = 1378014005703999518  # Your guild ID
OWNER_ID = 1378013027135393792  # <-- Replace with your Discord user ID (int)

warnings_db = {}  # In-memory warnings store

# Custom owner check decorator for app commands
def is_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Commands synced to guild ID {GUILD_ID}")


# Owner-only sync command to force global sync
@bot.tree.command(name="sync", description="Force sync commands globally (owner only)")
@is_owner()
async def sync(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message("Synced commands globally.")


# ===== Moderation Commands =====

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.describe(member="Member to warn", reason="Reason for warning")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    guild_id = interaction.guild.id
    user_id = member.id
    warnings_db.setdefault(guild_id, {}).setdefault(user_id, []).append(reason)
    await interaction.response.send_message(f"{member.mention} has been warned for: {reason}")

@bot.tree.command(name="warnings", description="List all warnings for a member")
@app_commands.describe(member="Member to check warnings for")
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    guild_id = interaction.guild.id
    user_id = member.id
    warnings_list = warnings_db.get(guild_id, {}).get(user_id, [])

    if not warnings_list:
        await interaction.response.send_message(f"{member.mention} has no warnings.", ephemeral=True)
    else:
        msg = f"Warnings for {member.mention}:\n" + "\n".join([f"{i+1}. {w}" for i, w in enumerate(warnings_list)])
        await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="unwarn", description="Remove a specific warning from a user")
@app_commands.describe(member="Member to unwarn", index="Warning number to remove")
@app_commands.checks.has_permissions(moderate_members=True)
async def unwarn(interaction: discord.Interaction, member: discord.Member, index: int):
    guild_id = interaction.guild.id
    user_id = member.id
    warnings_list = warnings_db.get(guild_id, {}).get(user_id, [])

    if 0 < index <= len(warnings_list):
        removed = warnings_list.pop(index - 1)
        await interaction.response.send_message(f"Removed warning #{index} from {member.mention}: {removed}")
    else:
        await interaction.response.send_message("Invalid warning index.", ephemeral=True)

@bot.tree.command(name="mute", description="Mute a member for X minutes")
@app_commands.describe(member="Member to mute", duration="Duration in minutes", reason="Reason for mute")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
    try:
        timeout_duration = datetime.timedelta(minutes=duration)
        await member.timeout_for(timeout_duration, reason=reason)
        await interaction.response.send_message(f"{member.mention} has been muted for {duration} minutes. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to mute: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="Member to unmute")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout_until(None)
        await interaction.response.send_message(f"{member.mention} has been unmuted.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to unmute: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick", reason="Reason for kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member.mention} has been kicked. Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban", reason="Reason for ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member.mention} has been banned. Reason: {reason}")

@bot.tree.command(name="unban", description="Unban a user (username#discriminator)")
@app_commands.describe(user="User to unban (e.g. User#1234)")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user: str):
    try:
        name, discriminator = user.split("#")
    except ValueError:
        await interaction.response.send_message("Please provide username in the format: User#1234", ephemeral=True)
        return
    for ban_entry in await interaction.guild.bans():
        if ban_entry.user.name == name and ban_entry.user.discriminator == discriminator:
            await interaction.guild.unban(ban_entry.user)
            await interaction.response.send_message(f"Unbanned {user}")
            return
    await interaction.response.send_message("User not found in ban list.", ephemeral=True)

@bot.tree.command(name="lockdown", description="Lock channel (block messages + threads)")
@app_commands.checks.has_permissions(manage_channels=True)
async def lockdown(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    overwrite.create_public_threads = False
    overwrite.create_private_threads = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Channel locked down.", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    overwrite.create_public_threads = None
    overwrite.create_private_threads = None
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Channel unlocked.", ephemeral=True)

@bot.tree.command(name="lockall", description="Lock all text channels in the server")
@app_commands.checks.has_permissions(administrator=True)
async def lockall(interaction: discord.Interaction):
    for channel in interaction.guild.text_channels:
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 All text channels have been locked.")

@bot.tree.command(name="unlockall", description="Unlock all text channels in the server")
@app_commands.checks.has_permissions(administrator=True)
async def unlockall(interaction: discord.Interaction):
    for channel in interaction.guild.text_channels:
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 All text channels have been unlocked.")

@bot.tree.command(name="purge", description="Bulk delete messages in a channel")
@app_commands.describe(amount="Number of messages to delete")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to delete messages: {e}", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode delay in the channel (in seconds)")
@app_commands.describe(seconds="Seconds between messages (0 to disable)")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("⏱ Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
        return
    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"⏱ Slowmode set to {seconds} seconds.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to set slowmode: {e}", ephemeral=True)

# ===== Utility Commands =====

@bot.tree.command(name="userinfo", description="Get info about a user")
@app_commands.describe(user="The user to get info about")
async def userinfo(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"User Info - {user}", color=discord.Color.blue())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Name", value=str(user), inline=True)
    embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    if isinstance(user, discord.Member):
        embed.add_field(name="Joined At", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Get info about the server")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Show user's avatar")
@app_commands.describe(user="The user whose avatar you want to see")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    avatar_url = user.display_avatar.url if user.display_avatar else user.default_avatar.url
    embed = discord.Embed(title=f"{user.display_name}'s avatar")
    embed.set_image(url=avatar_url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="commands", description="List all bot commands")
async def commands_list(interaction: discord.Interaction):
    cmds = """
**Moderation:**
/warn [member] [reason]
/warnings [member]
/unwarn [member] [index]
/mute [member] [duration] [reason]
/unmute [member]
/kick [member] [reason]
/ban [member] [reason]
/unban [user#1234]

/lockdown
/unlock
/lockall
/unlockall

/purge [amount]
/slowmode [seconds]

**Utility:**
/userinfo [user]
/serverinfo
/avatar [user]
/commands
/sync (owner only)
"""
    await interaction.response.send_message(cmds, ephemeral=True)

# ===== Error Handling =====

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


bot.run("MTM3ODAxNDE5NzM3NTQzOTA0OA.Gd9Mnd.wch--LAx9yis6KYarL9VARukVadt2PPBFvWdbk")
