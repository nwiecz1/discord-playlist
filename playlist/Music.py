import discord
from discord.ext import commands
import json
import random
from YTDLSource import YTDLSource
import asyncio
from YTDLSource import create_youtube_link
import os

path = os.getenv('APPDATA') + '/Playlist'
playlist_file = path + '/playlists.json'


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.playlists = {}
        self.song_list = []
        self.playlist_data = None
        self.context = None
        self.playlist_name = None
        self.load_playlists()

    def load_playlists(self):
        self.playlists = {}
        with open(playlist_file) as json_file:
            self.playlist_data = json.load(json_file)
            for info, songs in self.playlist_data.items():
                print(f"Loaded playlist {info}")
                self.playlists[info] = songs

    def write_playlist_update(self):
        with open(playlist_file, 'w') as out:
            json.dump(self.playlists, out, indent=4)
        print(f'Wrote updates to {playlist_file}')

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins the voice channel. """
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def list(self, ctx):
        """ Lists the current playlist order """
        if len(self.song_list) > 0:
            output = ""
            for index, song in enumerate(self.song_list, start=1):
                output += f'{index}. {song["name"]}\n'
            await ctx.send(f'Current Queue:\n {output}')
        else:
            await ctx.send('Nothing currently in queue')

    @commands.command()
    async def available(self, ctx):
        """ Lists the available playlists"""
        playlist_txt = '\n'.join(self.playlists.keys())
        await ctx.send(f'Available Playlists: \n{playlist_txt}')

    @commands.command()
    async def add(self, ctx, playlist_name, song_name, youtube_link):
        """ Adds the song to the playlist in question and reloads the playlist"""
        if playlist_name not in self.playlists:
            await ctx.send(f'No such playlist exists with name {playlist_name}. '
                           f'Use $available command to see available or $create to add a new playlist.')
            return
        pl = self.playlists[playlist_name].copy()
        if any(item['url'] == str(youtube_link).strip() for item in pl):
            await ctx.send(f'Youtube link already exists for this playlist')
            return
        song_info = {'url': youtube_link}
        source = await YTDLSource.from_url(song_info, loop=self.bot.loop, stream=False)
        pl.append({
            "name": str(song_name),
            "url": str(youtube_link).strip(),
            "file": source.final_file_name
        })
        self.playlists[playlist_name] = pl
        self.write_playlist_update()
        await ctx.send(f'Added song {song_name} to playlist {playlist_name}')

    @commands.command()
    async def create(self, ctx, playlist_name):
        """ Adds a new playlist """
        if playlist_name in self.playlists:
            await ctx.send(f'Playlist with name {playlist_name} already exists.')
            return
        self.playlists[playlist_name] = []
        self.write_playlist_update()
        await ctx.send(f'Successfully added {playlist_name}.')

    @commands.command()
    async def reload(self, ctx):
        """ Reloads the playlists from the json file. """
        self.load_playlists()
        await ctx.send('Playlist successfully reloaded.')

    @commands.command()
    async def play(self, ctx, *, name):
        """ Plays the playlist in question. """
        if name not in self.playlists or len(self.playlists[name]) == 0:
            await ctx.send(f'No such playlist exists with name {name} or there are no songs in the playlist')
            return
        if len(self.song_list) > 0:
            await ctx.send(
                f'Playlist {self.playlist_name} is already active.  Please wait until it is done to queue another')
            return

        await self.start(ctx, name)

    async def start(self, ctx, name):
        await ctx.send(f'Now starting playlist {name}')
        self.playlist_name = name

        self.song_list = self.playlists[name].copy()
        random.shuffle(self.song_list)
        self.context = ctx
        source = await YTDLSource.from_url(self.song_list[0], loop=self.bot.loop, stream=False)
        yt_link = create_youtube_link('Now playing: ', source)
        await ctx.send(embed=yt_link)
        ctx.voice_client.play(source, after=self.after)

    async def playit(self):
        self.song_list.pop(0)
        if len(self.song_list) > 0:
            source = await YTDLSource.from_url(self.song_list[0], loop=self.bot.loop, stream=False)
            yt_link = create_youtube_link('Now playing: ', source)
            await self.context.send(embed=yt_link)
            self.bot.voice_clients[0].play(source, after=self.after)
        else:
            await self.context.send(f'Playlist {self.playlist_name} complete!')
            await self.context.voice_client.disconnect()
            self.context = None
            self.playlist_name = None

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
        self.song_list = []
        self.playlist_name = None

    @commands.command()
    async def skip(self, ctx):
        """Skips the current song."""
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            print(error)
        elif isinstance(error, commands.BadArgument):
            await ctx.send('Command has an invalid argument.  Please view $help for more details.')

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
