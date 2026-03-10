"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.5.0
"""

import platform
import random
import asyncio
import re
from datetime import timedelta
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class FeedbackForm(discord.ui.Modal, title="Feeedback"):
    feedback = discord.ui.TextInput(
        label="What do you think about this bot?",
        style=discord.TextStyle.long,
        placeholder="Type your answer here...",
        required=True,
        max_length=256,
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.answer = str(self.feedback)
        self.stop()


class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot
        if not hasattr(self.bot, "pending_reminders"):
            self.bot.pending_reminders = {}
        if not hasattr(self.bot, "next_reminder_id"):
            self.bot.next_reminder_id = 1
        self.context_menu_user = app_commands.ContextMenu(
            name="Grab ID", callback=self.grab_id
        )
        self.bot.tree.add_command(self.context_menu_user)
        self.context_menu_message = app_commands.ContextMenu(
            name="Remove spoilers", callback=self.remove_spoilers
        )
        self.bot.tree.add_command(self.context_menu_message)

    async def find_command(
        self, context: Context, command_name: str
    ) -> Optional[commands.Command]:
        command_name = command_name.strip().lower()
        for command in self.bot.walk_commands():
            if command.cog_name == "owner" and not (
                await self.bot.is_owner(context.author)
            ):
                continue
            if command.qualified_name.lower() == command_name:
                return command
            if command.name.lower() == command_name:
                return command
        return None

    @staticmethod
    def parse_reminder_time(reminder_time: str) -> int:
        seconds = 0
        normalized_time = reminder_time.lower().replace(" ", "")
        matches = re.findall(r"(\d+)([hms]?)", normalized_time)
        if not matches:
            return 0

        parsed_length = sum(len(value) + len(unit) for value, unit in matches)
        if parsed_length != len(normalized_time):
            return 0

        for value, unit in matches:
            if unit == "h":
                seconds += int(value) * 3600
            elif unit == "m":
                seconds += int(value) * 60
            else:
                seconds += int(value)

        return seconds

    async def deliver_reminder(self, reminder_id: int) -> None:
        reminder = self.bot.pending_reminders.get(reminder_id)
        if reminder is None:
            return

        try:
            await asyncio.sleep(reminder["seconds"])
            await reminder["channel"].send(
                f"<@{reminder['user_id']}>, reminder: **{reminder['message']}**!"
            )
        except asyncio.CancelledError:
            pass
        except (discord.Forbidden, discord.HTTPException):
            pass
        finally:
            self.bot.pending_reminders.pop(reminder_id, None)

    # Message context menu command
    async def remove_spoilers(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """
        Removes the spoilers from the message. This command requires the MESSAGE_CONTENT intent to work properly.

        :param interaction: The application command interaction.
        :param message: The message that is being interacted with.
        """
        spoiler_attachment = None
        for attachment in message.attachments:
            if attachment.is_spoiler():
                spoiler_attachment = attachment
                break
        embed = discord.Embed(
            title="Message without spoilers",
            description=message.content.replace("||", ""),
            color=0xBEBEFE,
        )
        if spoiler_attachment is not None:
            embed.set_image(url=attachment.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # User context menu command
    async def grab_id(
        self, interaction: discord.Interaction, user: discord.User
    ) -> None:
        """
        Grabs the ID of the user.

        :param interaction: The application command interaction.
        :param user: The user that is being interacted with.
        """
        embed = discord.Embed(
            description=f"The ID of {user.mention} is `{user.id}`.",
            color=0xBEBEFE,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name="help", description="List all commands the bot has loaded."
    )
    async def help(self, context: Context) -> None:
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=0xBEBEFE
        )
        for i in self.bot.cogs:
            if i == "owner" and not (await self.bot.is_owner(context.author)):
                continue
            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="use",
        description="Show how to use a specific command.",
    )
    @app_commands.describe(command_name="The command you want help with.")
    async def use_command(self, context: Context, *, command_name: str) -> None:
        """
        Show how to use a specific command.

        :param context: The hybrid command context.
        :param command_name: The command to explain.
        """
        command = await self.find_command(context, command_name)
        if command is None:
            embed = discord.Embed(
                description=f"I couldn't find a command named `{command_name}`.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        prefix_usage = f"{context.clean_prefix}{command.qualified_name}"
        if command.signature:
            prefix_usage = f"{prefix_usage} {command.signature}"

        embed = discord.Embed(
            title=f"How to use `{command.qualified_name}`",
            color=0xBEBEFE,
        )
        embed.add_field(name="Prefix Usage", value=f"`{prefix_usage}`", inline=False)
        embed.add_field(
            name="Slash Usage",
            value=f"`/{command.qualified_name}`",
            inline=False,
        )
        embed.add_field(
            name="Description",
            value=command.description or "No description available.",
            inline=False,
        )

        if isinstance(command, commands.Group) and command.commands:
            subcommands = "\n".join(
                f"`{subcommand.qualified_name}` - {subcommand.description}"
                for subcommand in command.commands
            )
            embed.add_field(name="Subcommands", value=subcommands, inline=False)

        await context.send(embed=embed)

    @commands.hybrid_command(
        name="botinfo",
        description="Get some useful (or not) information about the bot.",
    )
    async def botinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the bot.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description="Used [Krypton's](https://krypton.ninja) template",
            color=0xBEBEFE,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(name="Owner:", value="Krypton#7331", inline=True)
        embed.add_field(
            name="Python Version:", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(
            name="Prefix:",
            value=f"/ (Slash Commands) or {self.bot.bot_prefix} for normal commands",
            inline=False,
        )
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="serverinfo",
        description="Get some useful (or not) information about the server.",
    )
    async def serverinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in context.guild.roles]
        num_roles = len(roles)
        if num_roles > 50:
            roles = roles[:50]
            roles.append(f">>>> Displaying [50/{num_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**Server Name:**", description=f"{context.guild}", color=0xBEBEFE
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="Server ID", value=context.guild.id)
        embed.add_field(name="Member Count", value=context.guild.member_count)
        embed.add_field(
            name="Text/Voice Channels", value=f"{len(context.guild.channels)}"
        )
        embed.add_field(name=f"Roles ({len(context.guild.roles)})", value=roles)
        embed.set_footer(text=f"Created at: {context.guild.created_at}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="invite",
        description="Get the invite link of the bot to be able to invite it.",
    )
    async def invite(self, context: Context) -> None:
        """
        Get the invite link of the bot to be able to invite it.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description=f"Invite me by clicking [here]({self.bot.invite_link}).",
            color=0xD75BF4,
        )
        try:
            await context.author.send(embed=embed)
            await context.send("I sent you a private message!")
        except discord.Forbidden:
            await context.send(embed=embed)

    @commands.hybrid_command(
        name="server",
        description="Get the invite link of the discord server of the bot for some support.",
    )
    async def server(self, context: Context) -> None:
        """
        Get the invite link of the discord server of the bot for some support.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            description=f"Join the support server for the bot by clicking [here](https://discord.gg/mTBrXyWxAF).",
            color=0xD75BF4,
        )
        try:
            await context.author.send(embed=embed)
            await context.send("I sent you a private message!")
        except discord.Forbidden:
            await context.send(embed=embed)

    @commands.hybrid_command(
        name="8ball",
        description="Ask any question to the bot.",
    )
    @app_commands.describe(question="The question you want to ask.")
    async def eight_ball(self, context: Context, *, question: str) -> None:
        """
        Ask any question to the bot.

        :param context: The hybrid command context.
        :param question: The question that should be asked by the user.
        """
        answers = [
            "It is certain.",
            "It is decidedly so.",
            "You may rely on it.",
            "Without a doubt.",
            "Yes - definitely.",
            "As I see, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again later.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        embed = discord.Embed(
            title="**My Answer:**",
            description=f"{random.choice(answers)}",
            color=0xBEBEFE,
        )
        embed.set_footer(text=f"The question was: {question}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="bitcoin",
        description="Get the current price of bitcoin.",
    )
    async def bitcoin(self, context: Context) -> None:
        """
        Get the current price of bitcoin.

        :param context: The hybrid command context.
        """
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(
                        title="Bitcoin price",
                        description=f"The current price is {data['bpi']['USD']['rate']} :dollar:",
                        color=0xBEBEFE,
                    )
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=0xE02B2B,
                    )
                await context.send(embed=embed)

    @app_commands.command(
        name="feedback", description="Submit a feedback for the owners of the bot"
    )
    async def feedback(self, interaction: discord.Interaction) -> None:
        """
        Submit a feedback for the owners of the bot.

        :param context: The hybrid command context.
        """
        feedback_form = FeedbackForm()
        await interaction.response.send_modal(feedback_form)

        await feedback_form.wait()
        interaction = feedback_form.interaction
        await interaction.response.send_message(
            embed=discord.Embed(
                description="Thank you for your feedback, the owners have been notified about it.",
                color=0xBEBEFE,
            )
        )

        app_owner = (await self.bot.application_info()).owner
        await app_owner.send(
            embed=discord.Embed(
                title="New Feedback",
                description=f"{interaction.user} (<@{interaction.user.id}>) has submitted a new feedback:\n```\n{feedback_form.answer}\n```",
                color=0xBEBEFE,
            )
        )

    @commands.hybrid_command(
        name="remind",
        description="Set a reminder.",
    )
    @app_commands.describe(
        message="The message to be reminded about.",
        time="The time to wait before the reminder (e.g., 100, 1m30s).",
    )
    async def remind(self, context: Context, message: str, time: str) -> None:
        """
        Set a reminder.

        :param context: The hybrid command context.
        :param message: The message to be reminded about.
        :param time: The time to wait before the reminder (e.g., 100, 1m30s).
        """
        seconds = self.parse_reminder_time(time)
        if seconds < 1:
            embed = discord.Embed(
                description="Invalid time format. Please use seconds (e.g. 100) or format like 1m30s.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        if seconds > 86400:
            embed = discord.Embed(
                description="The time cap is currently 24 hours (86400 seconds).",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        if seconds < 1:
            embed = discord.Embed(
                description="The time must be at least 1 second.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        reminder_id = self.bot.next_reminder_id
        self.bot.next_reminder_id += 1
        due_at = int((discord.utils.utcnow() + timedelta(seconds=seconds)).timestamp())
        reminder = {
            "id": reminder_id,
            "user_id": context.author.id,
            "message": message,
            "seconds": seconds,
            "due_at": due_at,
            "channel": context.channel,
            "location": f"#{context.channel}" if context.guild else "Direct Message",
        }
        self.bot.pending_reminders[reminder_id] = reminder
        reminder["task"] = asyncio.create_task(self.deliver_reminder(reminder_id))

        embed = discord.Embed(
            description=(
                f"I will remind you about **{message}** in **{seconds}** seconds.\n"
                f"Reminder ID: `{reminder_id}` (<t:{due_at}:R>)"
            ),
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="remindlist",
        description="List your pending reminders.",
    )
    async def remind_list(self, context: Context) -> None:
        """
        List the pending reminders created by the current user.

        :param context: The hybrid command context.
        """
        reminders = sorted(
            [
                reminder
                for reminder in self.bot.pending_reminders.values()
                if reminder["user_id"] == context.author.id
            ],
            key=lambda reminder: reminder["due_at"],
        )

        if len(reminders) == 0:
            embed = discord.Embed(
                description="You have no pending reminders.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        lines = []
        for reminder in reminders:
            message = reminder["message"]
            if len(message) > 50:
                message = f"{message[:47]}..."
            line = (
                f"`#{reminder['id']}` {message} - <t:{reminder['due_at']}:R> in {reminder['location']}"
            )
            if len("\n".join(lines + [line])) > 3500:
                remaining = len(reminders) - len(lines)
                lines.append(f"...and {remaining} more reminder(s).")
                break
            lines.append(line)

        embed = discord.Embed(
            title="Pending Reminders",
            description="\n".join(lines),
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="remindremove",
        description="Remove one of your pending reminders.",
    )
    @app_commands.describe(reminder_id="The ID of the reminder to remove.")
    async def remind_remove(self, context: Context, reminder_id: int) -> None:
        """
        Remove one of the current user's pending reminders.

        :param context: The hybrid command context.
        :param reminder_id: The ID of the reminder to remove.
        """
        reminder = self.bot.pending_reminders.get(reminder_id)
        if reminder is None or reminder["user_id"] != context.author.id:
            embed = discord.Embed(
                description=f"I couldn't find one of your reminders with ID `{reminder_id}`.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return

        self.bot.pending_reminders.pop(reminder_id, None)
        reminder["task"].cancel()

        embed = discord.Embed(
            description=f"Removed reminder `{reminder_id}`: **{reminder['message']}**",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="quote",
        description="Get a random inspirational quote.",
    )
    async def quote(self, context: Context) -> None:
        """
        Get a random inspirational quote.

        :param context: The hybrid command context.
        """
        quotes = [
            "Dream big. Start small. Act now.",
            "Success is built on consistency, not motivation.",
            "You don’t have to be great to start, but you have to start to be great.",
            "Your future self is watching — don’t disappoint them.",
            "Hard work beats talent when talent doesn’t work hard."
        ]
        embed = discord.Embed(
            description=random.choice(quotes),
            color=0xBEBEFE,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="joke",
        description="Get a random joke.",
    )
    async def joke(self, context: Context) -> None:
        """
        Get a random joke.

        :param context: The hybrid command context.
        """
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I told my computer I needed a break, and it froze.",
            "Why did the developer go broke? Because he used up all his cache.",
            "There are only 10 types of people in the world: those who understand binary and those who don’t.",
            "My code works… I have no idea why."
        ]
        embed = discord.Embed(
            description=random.choice(jokes),
            color=0xBEBEFE,
        )
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(General(bot))
