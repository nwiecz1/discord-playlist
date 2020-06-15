from discord.ext import commands
from Music import Music

bot = commands.Bot(command_prefix=commands.when_mentioned_or('$'), case_insensitive=True, description='Lets you set and play playlists from youtube')


@bot.event
async def on_ready():
    """
    Called when the bot starts.
    """
    print(f'Logged in as {bot.user.name} with id {bot.user.id}')

bot.add_cog(Music(bot))
env = open('.env', mode='r')
token = env.read()
env.close()
bot.run(token)
