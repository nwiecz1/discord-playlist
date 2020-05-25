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
    """
    Music player.  The main part of the bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.playlists = {}
        self.song_list = []
        self.playlist_data = None
        self.context = None
        self.playlist_name = None
        self.load_playlists()

    def load_playlists(self):
        """
        Loads the playlists.
        """
        self.playlists = {}
        with open(playlist_file) as json_file:
            self.playlist_data = json.load(json_file)
            for info, songs in self.playlist_data.items():
                print(f"Loaded playlist {info}")
                self.playlists[info] = songs

    def write_playlist_update(self):
        """
        Writes any updates to the playlist json file.
        """
        with open(playlist_file, 'w') as out:
            json.dump(self.playlists, out, indent=4)
        print(f'Wrote updates to {playlist_file}')

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """
        Joins the voice channel
        :param ctx: Bot context
        :param channel: Channel to join.
        """
        """Joins the voice channel. """
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def list(self, ctx):
        """
        Lists the current playlist order
        :param ctx: Bot context.
        """
        if len(self.song_list) > 0:
            output = ""
            for index, song in enumerate(self.song_list, start=1):
                output += f'{index}. {song["name"]}\n'
            await ctx.send(f'Current Queue:\n {output}')
        else:
            await ctx.send('Nothing currently in queue')

    @commands.command()
    async def available(self, ctx):
        """
        Lists the available playlists
        :param ctx: Bot context
        """
        playlist_txt = '\n'.join(self.playlists.keys())
        await ctx.send(f'Available Playlists: \n{playlist_txt}')

    @commands.command()
    async def add(self, ctx, playlist_name, song_name, youtube_link):
        """
        Adds the song to the playlist in question and reloads the playlist
        :param ctx: Bot context
        :param playlist_name: The name of playlist to add to
        :param song_name: The name of the song (use quotes).
        :param youtube_link: The full youtube link.
        """
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
        """
        Creates a new playlist.
        :param ctx: Bot context.
        :param playlist_name: The name of the playlist.
        """
        if playlist_name in self.playlists:
            await ctx.send(f'Playlist with name {playlist_name} already exists.')
            return
        self.playlists[playlist_name] = []
        self.write_playlist_update()
        await ctx.send(f'Successfully added {playlist_name}.')

    @commands.command()
    async def reload(self, ctx):
        """
        Reloads the playlists from the json file.
        :param ctx: The bot context.
        """
        self.load_playlists()
        await ctx.send('Playlist successfully reloaded.')

    @commands.command()
    async def play(self, ctx, *, name):
        """
        Plays the playlist in question.
        :param ctx: The context.
        :param name: The playlist name.
        """
        if name not in self.playlists or len(self.playlists[name]) == 0:
            await ctx.send(f'No such playlist exists with name {name} or there are no songs in the playlist')
            return
        if len(self.song_list) > 0:
            await ctx.send(
                f'Playlist {self.playlist_name} is already active.  Please wait until it is done to queue another')
            return

        await self.start(ctx, name)

    async def start(self, ctx, name):
        """
        Starts the playlist.
        :param ctx: The bot context.
        :param name: The playlist name.
        :return:
        """
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
        """
        Plays the playlist song.
        """
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
        """
        Callback method after the playlist.
        :param error: Error if any.
        """
        try:
            fut = asyncio.run_coroutine_threadsafe(self.playit(), self.bot.loop)
            fut.result()
        except Exception as e:
            print(e)

    @commands.command()
    async def stop(self, ctx):
        """
        Stops and disconnects the bot from voice
        :param ctx: The bot context.
        """
        if ctx.voice_client is not None:
            await ctx.send(f'Bye')
            await ctx.voice_client.disconnect()
        self.context = None
        self.song_list = []
        self.playlist_name = None

    @commands.command()
    async def skip(self, ctx):
        """
        Skips the current song.
        :param ctx: The bot context.
        """
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Occurs on error.
        :param ctx: The bot context.
        :param error: The error.
        """
        if isinstance(error, commands.CommandNotFound):
            print(error)
        elif isinstance(error, commands.BadArgument):
            await ctx.send('Command has an invalid argument.  Please view $help for more details.')

    @play.before_invoke
    async def ensure_voice(self, ctx):
        """
        Occurs before a method is called. Makes sure the bot is connected to voice.
        :param ctx: The bot context.
        """
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
