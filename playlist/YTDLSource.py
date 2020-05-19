import discord
import asyncio
import youtube_dl
import datetime
import os

path = os.getenv('APPDATA') + '/Playlist/songs'

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''
beforeArgs = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
ffmpeg_options = {
    'options': '-vn'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': path+'/%(title)s.mp3',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def create_youtube_link(title, source):
    dura = str(datetime.timedelta(seconds=source.duration))
    embed = discord.Embed(
        title=f'{title}{source.title} - ({dura})',
        url=f'https://www.youtube.com/watch?v={source.id}'
    )
    return embed


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=1):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.id = data.get('id')
        self.final_file_name = data.get('final_file_name')

    @classmethod
    async def from_url(cls, song_info, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song_info['url'], download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        data['final_file_name'] = filename
        print(f'Downloaded file {filename}')
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)