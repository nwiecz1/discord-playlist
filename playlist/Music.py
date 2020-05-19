import discord
from discord.ext import commands
import importlib.resources as pkg_resources
import json
import random
from YTDLSource import YTDLSource
import asyncio


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.playlists = {}
        self.song_list = []
        self.context = None
        self.playlist_name = None
        file_text = pkg_resources.read_text('resources', 'playlists.json')
        playlist_data = json.loads(file_text)
        print(playlist_data)
        for info, songs in playlist_data.items():
            print(f"Loading playlist {info}")
            self.playlists[info] = songs['song_list']

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def list(self, ctx):
        """ Lists the current playlist order """
        if len(self.song_list) > 0:
            output = ""
            for index, song in enumerate(self.song_list, start=1):
                output += f'#{index} {song["name"]}\n'
            await ctx.send(f'Current Queue:\n {output}')
        else:
            await ctx.send('Nothing currently in queue')

    @commands.command()
    async def available(self, ctx):
        """ Lists the available playlists"""
        playlist_txt = '\n'.join(self.playlists.keys())
        await ctx.send(f'Available Playlists: \n{playlist_txt}')

    @commands.command()
    async def play(self, ctx, *, name):
        if name not in self.playlists or len(self.playlists[name]) == 0:
            await ctx.send(f'No such playlist exists with name {name} or there are no songs in the playlist')
            return
        if len(self.song_list) > 0:
            await ctx.send(f'Playlist {self.playlist_name} is already active.  Please wait until it is done to queue another')
            return

        await self.start(ctx, name)

    async def start(self, ctx, name):
        await ctx.send(f'Now starting playlist {name}')
        self.playlist_name = name

        self.song_list = self.playlists[name]
        random.shuffle(self.song_list)
        self.context = ctx
        source = await YTDLSource.from_url(self.song_list[0], loop=self.bot.loop, stream=False)
        await ctx.send(f'Now playing {source.title}')
        ctx.voice_client.play(source, after=self.after)

    async def playit(self):
        self.song_list.pop(0)
        if len(self.song_list) > 0:
            source = await YTDLSource.from_url(self.song_list[0], loop=self.bot.loop, stream=False)
            await self.context.send(f'Now playing {source.title}')
            self.bot.voice_clients[0].play(source, after=self.after)
        else:
            await self.context.send('Playlist complete!')
            await self.context.voice_client.disconnect()
            self.context = None

    def after(self, error):
        try:
            fut = asyncio.run_coroutine_threadsafe(self.playit(), self.bot.loop)
            fut.result()
        except Exception as e:
            print(e)

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        if ctx.voice_client is not None:
            await ctx.send(f'Bye')
            await ctx.voice_client.disconnect()
        self.context = None

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
