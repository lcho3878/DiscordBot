
import os
from dotenv import load_dotenv
import discord
from keep_alive import keep_alive  # 이 줄을 추가하세요
from discord.ext import commands
from googleapiclient.discovery import build
import yt_dlp
import asyncio

load_dotenv()

# 디스코드 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned,
                   intents=intents)  # 접두사 제거

# 명렁어 env
PLAY_MESSAGE = os.environ.get('PLAY_MESSAGE')
SKIP_MESSAGE = os.environ.get('SKIP_MESSAGE')

# 유튜브 API 키 (https://console.developers.google.com 에서 발급)
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_COOKIE_STRING = os.environ.get('YOUTUBE_COOKIE_STRING')
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

FFMPEG_OPTIONS = {
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 64k'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,
    'skip_download': True,
    'forceurl': True,
    'http_headers': {
        'Cookie': YOUTUBE_COOKIE_STRING
    }
}


# 유튜브 검색 함수
def search_youtube(query):
    # 쿼리에 자동으로 "official audio" 추가
    audio_query = query + " official audio"
    request = youtube.search().list(q=audio_query,
                                    part='snippet',
                                    type='video',
                                    maxResults=1)
    response = request.execute()
    # audio 관련 키워드가 있는 영상 먼저 찾기
    for item in response['items']:
        title = item['snippet']['title'].lower()
        if 'audio' in title or 'official' in title:
            return f"https://www.youtube.com/watch?v={item['id']['videoId']}"

    # 없으면 그냥 첫 번째 결과 리턴
    return f"https://www.youtube.com/watch?v={response['items'][0]['id']['videoId']}"

def search_and_get_info(query):
    # yt-dlp가 직접 검색하도록 합니다. 'ytsearch1:'은 검색 결과 1개를 의미합니다.
    search_query = f"ytsearch1:{query} official audio"
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        # 검색과 정보 추출을 한 번에 실행합니다.
        info = ydl.extract_info(search_query, download=False)
        # 검색 결과가 리스트 형태로 반환되므로 첫 번째 항목을 사용합니다.
        if 'entries' in info and info['entries']:
            return info['entries'][0]
    return None


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    if content.startswith(PLAY_MESSAGE):
        query = content.replace(PLAY_MESSAGE, "").strip()

        if not query:
            await message.channel.send("🎵 재생할 검색어를 함께 입력해 주세요!")
            return

        if message.author.voice is None:
            await message.channel.send("먼저 음성 채널에 들어가 주세요!")
            return

        voice_channel = message.author.voice.channel

        if message.guild.voice_client is None:
            await voice_channel.connect()
        elif message.guild.voice_client.channel != voice_channel:
            await message.guild.voice_client.move_to(voice_channel)

        try:
            info = search_and_get_info(query)
            if not info:
                await message.channel.send("🔍 검색 결과를 찾지 못했어요.")
                return

            url = info['webpage_url']
            audio_url = info['url']
            title = info['title']
            await message.channel.send(f"🎵 **{title}** 재생을 시작할게요!\n{url}")

        except yt_dlp.utils.DownloadError as e:
            # 429 오류 등을 여기서 잡아서 사용자에게 친절하게 알려줍니다.
            await message.channel.send("⚠️ 유튜브 요청 제한에 걸렸거나 영상을 불러올 수 없어요. 잠시 후 다시 시도해 주세요.")
            print(f"yt-dlp 오류 발생: {e}")
            return
        except Exception as e:
            await message.channel.send("⚙️ 알 수 없는 오류가 발생했어요.")
            print(f"일반 오류 발생: {e}")
            return

        # url = search_youtube(query)
        # await message.channel.send(f"🔍 검색 결과: {url}")

        # with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        #     info = ydl.extract_info(url, download=False)
        #     audio_url = info['url']

        vc = message.guild.voice_client
        if vc.is_playing():
            vc.stop()

        vc.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
                after=lambda e: print(f'재생 중 오류 발생: {e}') if e else None)

    # SKIP 처리 직접 추가
    if content.startswith(SKIP_MESSAGE):
        vc = message.guild.voice_client
        if vc:
            await vc.disconnect()
            await message.channel.send("👋 빠이~")
        else:
            await message.channel.send("봇이 음성 채널에 없습니다.")
        return
    await bot.process_commands(message)  # 기존 명령어도 사용 가능하게 유지


# 음성 채널 접속
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("먼저 음성 채널에 들어가 주세요!")


# 유튜브 키워드로 재생
@bot.command(name=PLAY_MESSAGE)
async def play(ctx, *, query):
    # 사용자가 음성 채널에 있는지 확인
    if ctx.author.voice is None:
        await ctx.send("먼저 음성 채널에 들어가 주세요!")
        return

    voice_channel = ctx.author.voice.channel

    # 봇이 이미 연결되어 있는지 확인하고, 없다면 연결
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    # 유튜브 검색
    url = search_youtube(query)
    await ctx.send(f"🔍 검색결과: {url}")

    # 오디오 재생
    # with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop()

    vc.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
            after=lambda e: print(f'오류: {e}') if e else None)


# 나가기
@bot.command(name=SKIP_MESSAGE)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


# 실행
keep_alive()
bot.run(DISCORD_BOT_TOKEN)