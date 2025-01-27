import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import re

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue = []
        self.repeat_queue = []
        self.repeat_mode = False
        self.last_played_song = None

    @commands.command(name='join', help='Faz o bot entrar no canal de voz')
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f'Conectado ao canal {channel}')
        else:
            await ctx.send('Você precisa estar em um canal de voz para usar este comando.')

    @commands.command(name='leave', help='Faz o bot sair do canal de voz')
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.send('Desconectado do canal de voz')
        else:
            await ctx.send('O bot não está em um canal de voz')
    
    @commands.command(name='play', aliases=['p'], help='Toca um arquivo MP3, WAV, OGG ou uma URL do YouTube')
    async def play(self, ctx, *, file_name_or_url: str):
        downloads_directory = 'music/downloads/'
        await ctx.send('Baixando o áudio...')
        file_name = os.path.basename(file_name_or_url)
        file_path = os.path.join(downloads_directory, file_name)

        if ctx.voice_client is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await channel.connect()
                await ctx.send(f'Conectado ao canal {channel}')
            else:
                await ctx.send('Você precisa estar em um canal de voz para usar este comando.')
                return

        if 'youtube.com' in file_name_or_url or 'youtu.be' in file_name_or_url:
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(downloads_directory, '%(title)s.%(ext)s'),
                    'cookiefile': 'cookies.txt',
                    'username': 'your_username',
                    'password': 'your_password',
                }

                os.makedirs(downloads_directory, exist_ok=True)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(file_name_or_url, download=True)
                    sanitized_title = re.sub(r'[<>:"/\\|?*]', "", info['title'])
                    extension = file_name_or_url.split('.')[-1]
                    if extension == 'ogg':
                        file_path = os.path.join(downloads_directory, f"{sanitized_title}.ogg")
                    elif extension == 'wav':
                        file_path = os.path.join(downloads_directory, f"{sanitized_title}.wav")
                    else:
                        file_path = os.path.join(downloads_directory, f"{sanitized_title}.mp3")
            except yt_dlp.utils.DownloadError as e:
                await ctx.send(f'Ocorreu um erro ao baixar o áudio: {str(e)}')
                return

            if not os.path.isfile(file_path):
                await ctx.send('Arquivo não encontrado mesmo após o download.')
                return

            self.music_queue.append(file_path)
            await self.play_next(ctx)

        else:
            if file_name_or_url.endswith('.mp3') or file_name_or_url.endswith('.wav') or file_name_or_url.endswith('.ogg'):
                file_path = os.path.join(downloads_directory, file_name_or_url)
                if os.path.isfile(file_path):
                    self.music_queue.append(file_path)
                    await self.play_next(ctx)
                else:
                    await ctx.send(f'Arquivo {file_name_or_url} não encontrado.')
            else:
                await ctx.send('Formato de arquivo inválido. Use MP3, WAV ou OGG.')

    async def play_next(self, ctx):
        global repeat_mode, repeat_queue

        if ctx.voice_client is None:
            await ctx.send('Erro: o bot não está em um canal de voz.')
            return

        if self.music_queue or (repeat_mode and self.repeat_queue):
            # Caso o repeat esteja on e a fila vazia retornamos pra fila original
            if not self.music_queue and repeat_mode and self.repeat_queue:
                self.music_queue.extend(self.repeat_queue)

            next_song = self.music_queue[0] if self.music_queue else self.last_played_song
            source = discord.FFmpegPCMAudio(next_song)
            self.last_played_song = next_song

            def after_playing(err):
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            ctx.voice_client.play(source, after=after_playing)
            await ctx.send(f'Tocando: {os.path.basename(next_song)}')

            # Remove a musica da fila se o repeat estiver off
            if not repeat_mode:
                self.music_queue.pop(0)
            else:
                self.repeat_queue.append(self.music_queue.pop(0))
        else:
            await ctx.send('A fila de músicas está vazia.')

    @commands.command(name='repeat', help='Ativa/desativa o modo de repetição')
    async def repeat(self, ctx):
        global repeat_mode
        repeat_mode = not repeat_mode
        if repeat_mode:
            await ctx.send('Modo de repetição ativado.')
        else:
            await ctx.send('Modo de repetição desativado.')

    @commands.command(name='queue', help='Exibe a fila de músicas')
    async def queue(self, ctx):
        if not self.music_queue:
            await ctx.send('A fila de músicas está vazia.')
        else:
            queue_message = 'Fila de músicas:\n'
            for i, song in enumerate(self.music_queue):
                queue_message += f'{i+1}. {os.path.basename(song)}\n'
            await ctx.send(queue_message)

    @commands.command(name='skip', help='Pula a música atual')
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await self.play_next(ctx)
        else:
            await ctx.send('Não há nenhuma música tocando no momento.')

    @commands.command(name='stop', help='Para a reprodução da música')
    async def stop(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            self.music_queue.clear()
            self.repeat_queue.clear()
            self.last_played_song = None
            await ctx.send('A reprodução da música foi interrompida.')
        else:
            await ctx.send('Não há nenhuma música tocando no momento.')

def setup(bot):
    bot.add_cog(MusicBot(bot))