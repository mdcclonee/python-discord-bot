"""
Description: Auto-moderation cog to prevent spamming.
"""

import time
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands


class AutoMod(commands.Cog, name="automod"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # Dictionary to track message timestamps per user
        self.spam_cache = defaultdict(list)
        # Dictionary to track when a user was last warned
        self.warned_users = {}
        # Dictionary to track when a user was first muted
        self.first_muted_users = {}
        
        # Spam configuration defaults
        self.message_limit = 5      # Max messages allowed
        self.time_window = 5        # Time window in seconds
        self.warning_window = 60    # Time window after warning/mute where further spam escalates
        self.first_mute_duration = 30   # Timeout duration in seconds for first offense
        self.second_mute_duration = 300 # Timeout duration in seconds for second offense (5 min)

    def clear_user_records(self, user_id: int) -> None:
        """Clears all spam records for a user."""
        self.spam_cache.pop(user_id, None)
        self.warned_users.pop(user_id, None)
        self.first_muted_users.pop(user_id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore messages from bots or outside of a guild
        if message.author.bot or message.guild is None:
            return

        # Ignore administrators
        if message.author.guild_permissions.administrator:
            return

        user_id = message.author.id
        now = time.time()

        # Remove old message timestamps outside the time window
        self.spam_cache[user_id] = [
            msg_time for msg_time in self.spam_cache[user_id] 
            if now - msg_time <= self.time_window
        ]

        # Add the current message timestamp
        self.spam_cache[user_id].append(now)

        # Check if user has exceeded the message limit
        if len(self.spam_cache[user_id]) > self.message_limit:
            # Clear the cache for this user to prevent duplicate timeout triggers
            self.spam_cache[user_id].clear()

            last_muted = self.first_muted_users.get(user_id, 0)
            last_warned = self.warned_users.get(user_id, 0)

            # Check if they spam again within 60s after serving the 30s mute (total 90s window)
            if last_muted > 0 and now - last_muted <= self.first_mute_duration + self.warning_window:
                try:
                    until = discord.utils.utcnow() + timedelta(seconds=self.second_mute_duration)
                    await message.author.timeout(until, reason="AutoMod: Repeated spamming")

                    embed = discord.Embed(
                        title="⚠️ Repeated Spam Detected",
                        description=f"**{message.author.mention}** has been timed out for {self.second_mute_duration // 60} minutes due to repeated spamming.",
                        color=0xE02B2B,
                    )
                    await message.channel.send(embed=embed)
                    
                    # Reset cycle after the severe mute
                    self.first_muted_users.pop(user_id, None)
                except discord.Forbidden:
                    pass
            elif last_warned > 0 and now - last_warned <= self.warning_window:
                try:
                    # Timeout the user for 30s
                    until = discord.utils.utcnow() + timedelta(seconds=self.first_mute_duration)
                    await message.author.timeout(until, reason="AutoMod: Continued spamming after warning")

                    embed = discord.Embed(
                        title="⚠️ Spam Detected",
                        description=f"**{message.author.mention}** has been timed out for {self.first_mute_duration} seconds due to continued spamming.",
                        color=0xE02B2B,
                    )
                    await message.channel.send(embed=embed)
                    
                    # Move from warned state to first mute state
                    self.warned_users.pop(user_id, None)
                    self.first_muted_users[user_id] = now
                except discord.Forbidden:
                    pass  # Bot doesn't have permissions to timeout this user
            else:
                # Issue a warning first
                self.warned_users[user_id] = now
                self.first_muted_users.pop(user_id, None) # Clear any old mute records
                reason = "AutoMod: Spamming messages"
                
                try:
                    total = await self.bot.database.add_warn(
                        user_id, message.guild.id, self.bot.user.id, reason
                    )
                    
                    embed = discord.Embed(
                        title="⚠️ Spam Warning",
                        description=f"**{message.author.mention}**, please stop spamming! You will be muted if you continue.\nTotal warns for this user: {total}",
                        color=0xF59E42, # Orange Warning Color
                    )
                    await message.channel.send(embed=embed)
                    
                    try:
                        await message.author.send(f"You were warned in **{message.guild.name}**!\nReason: {reason}")
                    except discord.Forbidden:
                        pass
                except Exception:
                    pass


async def setup(bot) -> None:
    await bot.add_cog(AutoMod(bot))