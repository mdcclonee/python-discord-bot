import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="role")
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, action: str, *, role: discord.Role):
        """
        Usage:
        !role @user add @role
        !role @user remove @role
        """

        # Check bot permissions
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("❌ I don't have permission to manage roles.")

        # Prevent editing roles higher than bot
        if role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot manage that role (it's higher than my highest role).")

        # Prevent user from modifying someone with higher role
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot modify someone with an equal or higher role than you.")

        action = action.lower()

        if action == "add":
            if role in member.roles:
                return await ctx.send("⚠️ User already has that role.")
            
            await member.add_roles(role)
            await ctx.send(f"✅ Added **{role.name}** to {member.mention}")

        elif action == "remove":
            if role not in member.roles:
                return await ctx.send("⚠️ User doesn't have that role.")
            
            await member.remove_roles(role)
            await ctx.send(f"❌ Removed **{role.name}** from {member.mention}")

        else:
            await ctx.send("⚠️ Use `add` or `remove`.")

    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need `Manage Roles` permission to use this command.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found.")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send("❌ Role not found.")
        else:
            await ctx.send("❌ Something went wrong.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))