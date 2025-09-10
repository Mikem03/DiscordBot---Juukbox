import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import yt_dlp


###
###video mode / host the bot on a pi
###


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

voice_client = {}
queue = {}
titleQueue = []
nowPlaying = ""

yt_dlp_options = {
    'format': 'bestaudio[ext=webm]/bestaudio/best',
    'noplaylist': True,
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
}

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    print(f"We are logged in as {bot.user.name}")

### Helper Functions for !play ###

async def search_youtube(query, options):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: extract(query, options))

def extract(query, options):
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(query, download=False)

async def play_song(ctx, channel, search):
    query = "ytsearch1: " + search
    results = await search_youtube(query, yt_dlp_options)
    tracks = results.get('entries', [])
    if not tracks:
        await ctx.send("No results found.")
        return

    first_track = tracks[0]
    audio_url = first_track['url']
    title = first_track.get('title', "Untitled")
    global nowPlaying
    nowPlaying = title

    def after_playing(error):
        if error:
            print(f"Error after playing: {error}")
        next_song = None
        if queue[channel.id]:
            next_song = queue[channel.id].pop(0)
        if next_song:
            coro = play_song(next_song[1], channel, next_song[0])
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error playing next song: {e}")
        else:
            print("Queue is empty or next song is None after skip.")

    try:
        voice_client[channel.id].play(
            discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
            after=after_playing
        )
        global titleQueue
        if titleQueue:
            del titleQueue[0]
        await ctx.send(nowPlaying)

    except Exception as e:
        logging.error(f"Error occurred while playing audio: {e}")
        await ctx.send("An error occurred while trying to play the audio.")



### !play ### 
@bot.command()
async def play(ctx, *, search: str = None):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id not in voice_client or not voice_client[channel.id].is_connected():
        voice_client[channel.id] = await channel.connect()


    if channel.id not in queue:
        queue[channel.id] = []


    ### RESUME ####
    if search is None:
        if voice_client[channel.id].is_paused():
            voice_client[channel.id].resume()
            await ctx.send("Resumed playback")
        else:
            await ctx.send("No audio is currently playing.")
        return    
    else:
        titleQueue.append(search)

    #### QUEUE ###
    if voice_client[channel.id].is_playing() or voice_client[channel.id].is_paused():
        queue[channel.id].append((search, ctx))
        await ctx.send(f"Added to queue: {search}")
        return

    await play_song(ctx, channel, search)


### PAUSE ###
@bot.command()
async def pause(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id not in voice_client or not voice_client[channel.id].is_connected():
        await ctx.send("I'm not connected to your voice channel.")
        return

    voice_client[channel.id].pause()
    await ctx.send("Audio paused. To resume use !play")


### SHOW QUEUE ###
@bot.command()
async def showqueue(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id not in queue or not queue[channel.id]:
        await ctx.send("The queue is empty.")
        return

    queue_message = "\n".join(f"{i+1}. {title}" for i, title in enumerate(titleQueue))
    await ctx.send(f"Now playing: {nowPlaying} \n \nCurrent queue:\n{queue_message}")

###STOP ###
@bot.command()
async def stop(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id in voice_client and voice_client[channel.id].is_connected():
        voice_client[channel.id].stop()

    if channel.id in queue:
        queue[channel.id].clear()

    await ctx.send("Audio stopped and queue cleared.")

###SKIP###
@bot.command()
async def skip(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id not in queue or not queue[channel.id]:
        await ctx.send("The queue is empty.")
        return
    
    voice_client[channel.id].stop()

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
