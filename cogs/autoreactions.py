import discord
from discord.ext import commands

class AutoReactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


        self.reaction_map = {
            "w": ["🔥"],
            "win": ["🏆", "🔥"],
            "lol": ["😂"],
            "hello": ["👋"],
            "bye": ["👋"],
            "goodnight": ["🌙"],
            "gg": ["👏"],
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        content = message.content.lower()

        for keyword, emojis in self.reaction_map.items():
            if keyword in content:
                for emoji in emojis:
                    try:
                        await message.add_reaction(emoji)
                    except discord.HTTPException:
                        pass  


    @commands.command(name="addreaction")
    @commands.has_permissions(manage_messages=True)
    async def add_reaction_keyword(self, ctx, keyword: str, emoji: str):
        keyword = keyword.lower()

        if keyword in self.reaction_map:
            self.reaction_map[keyword].append(emoji)
        else:
            self.reaction_map[keyword] = [emoji]

        await ctx.send(f"Added reaction {emoji} for keyword '{keyword}'")


    @commands.command(name="removereaction")
    @commands.has_permissions(manage_messages=True)
    async def remove_reaction_keyword(self, ctx, keyword: str):
        keyword = keyword.lower()

        if keyword in self.reaction_map:
            del self.reaction_map[keyword]
            await ctx.send(f"Removed keyword '{keyword}'")
        else:
            await ctx.send("Keyword not found.")

async def setup(bot):
    await bot.add_cog(AutoReactions(bot))