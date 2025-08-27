import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import asyncio
import yt_dlp


### rewrite this whole thing to use search queries
###
###video mode/ stream dont download / github this / docker / host the bot on a pi
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
nowPlaying = ""

yt_dlp_options = {'format': 'bestaudio[ext=webm]/bestaudio/best', 'noplaylist': True}

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    print(f"We are logged in as {bot.user.name}")


### Helper Function for !play ###

async def play_song(ctx, channel, url):
    ydl = yt_dlp.YoutubeDL(yt_dlp_options)
    info = ydl.extract_info(url, download=False)
    audio_url = info['url']
    print(f"Extracted audio URL: {audio_url}")

    def after_playing(error):
        if error:
            print(f"Error after playing: {error}")
        next_song = None
        if queue[channel.id]:
            next_song = queue[channel.id].pop(0)
        if next_song:
            coro = play_song(next_song[2], channel, next_song[0])
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error playing next song: {e}")

    try:
        voice_client[channel.id].play(
            discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
            after=after_playing
        )

        global nowPlaying
        nowPlaying = f"Now Playing:  {info.get('title', 'Unknown Title')}"
        await ctx.send(nowPlaying)

    except Exception as e:
        logging.error(f"Error occurred while playing audio: {e}")
        await ctx.send("An error occurred while trying to play the audio.")

### !play ### 
@bot.command()
async def play(ctx, url: str = None):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if channel.id not in voice_client or not voice_client[channel.id].is_connected():
        voice_client[channel.id] = await channel.connect()


    if channel.id not in queue:
        queue[channel.id] = []

    if url is None:
        if voice_client[channel.id].is_paused():
            voice_client[channel.id].resume()
            await ctx.send("Resumed playback")
        else:
            await ctx.send("No audio is currently playing.")
        return

    if voice_client[channel.id].is_playing() or voice_client[channel.id].is_paused():
        ydl = yt_dlp.YoutubeDL(yt_dlp_options)
        info = ydl.extract_info(url, download=False)
        title = info.get('title', url)   
        queue[channel.id].append((url, title, ctx))
        await ctx.send(f"Song added to queue: {title}")
        return

    await play_song(ctx, channel, url)    


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
    await ctx.send("Audio paused. To resume use !play or react to this message with a thumbs up.")


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

    titles = [title for _, title, _ in queue[channel.id]]
    queue_message = "\n".join(f"{i+1}. {title}" for i, title in enumerate(titles))
    await ctx.send(f"{nowPlaying} \n \nCurrent queue:\n{queue_message}")

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
    voice_client[channel.id].stop()

bot.run(token, log_handler=handler, log_level=logging.DEBUG)