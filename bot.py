import math
from io import BytesIO
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import random
from perlin_numpy import (
    generate_fractal_noise_2d, generate_perlin_noise_2d
)
import numpy as np
import time

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ImageSize = (1092, 768)
FontSize = 28
DistanceFrom = (10, 40)
FogCutoff = 0.7
isPlaying = False

quoteList = []


def LoadQuotes():
    with open("quoteList.txt", 'r') as reader:
        lines = reader.readlines()
        for line in lines:
            quoteList.append(line)


def SaveQuotes():
    with open("quoteList.txt", 'w') as writer:
        for q in quoteList:
            writer.write(q)


def GetTextSize(text_string, font):
    ascent, descent = font.getmetrics()
    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return text_width, text_height


def CreateSmoke(seed: int, cellSize, levels, attenuation):
    np.random.seed(random.randint(0, seed))
    noise = generate_perlin_noise_2d((2048, 2048), (8, 8))
    subHeight = math.ceil(ImageSize[1] * FogCutoff)
    fog = noise[:subHeight, :ImageSize[0]]
    sharpen = [
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ]
    sharpen = np.asarray(sharpen)
    fog += 1
    fog /= 2
    fog *= 255
    fog /= 3
    for i in range(200):
        fog[i:i + 1, :] *= (0.005 * i)
    nullRow = np.zeros((1, ImageSize[0]))
    for diff in range(ImageSize[1] - subHeight):
        fog = np.vstack([nullRow, fog])
    # fog = np.convolve(fog, sharpen, mode='full')
    fog = np.repeat(fog[:, :, np.newaxis], 3, axis=2)
    img = Image.fromarray(np.uint8(fog))
    return img


def AddText(drawer, text):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path, "font.ttf")
    font = ImageFont.truetype(dir_path, FontSize)
    if text == "":
        text = random.choice(quoteList)
    quote = [text]
    while True:
        found = False
        for q in quote:
            pos = q.find('/')
            if pos >= 0:
                q1 = q[0:pos]
                q2 = q[pos + 1:]
                quote.remove(q)
                if q1 != "":
                    quote.append(q1)
                if q2 != "":
                    quote.append(q2)
        if not found:
            break

    largestLen = 0
    sumHeight = 0
    for q in quote:
        l, h = GetTextSize(q, font)
        if l > largestLen:
            largestLen = l
        sumHeight += h

    for q in quote:
        drawer.text(
            (ImageSize[0] - DistanceFrom[0] - largestLen, ImageSize[1] - DistanceFrom[1] - sumHeight),
            q,
            font=font,
            fill=(255, 255, 255))
        _, h = GetTextSize(q, font)
        sumHeight -= h


def GenerateImage(text):
    # create fog
    image = CreateSmoke(1024, 64, 2, 1)
    drawer = ImageDraw.Draw(image)
    # add text
    AddText(drawer, text)

    # add image
    return image


def CreateLoadingImage(txt):
    img = GenerateImage(txt)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    LoadQuotes()
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='load')
async def SendLoadingImage(message, *args):
    text = ""
    if len(args) > 0:
        text = " ".join(args)
    try:
        img_bytes = CreateLoadingImage(text)
        f = discord.File(img_bytes, filename="loading.png")
        await message.channel.send(file=f)
    except OSError as e:
        await message.channel.send("Error: {0}".format(e))
        print(e)


@bot.command(name='addq')
async def AddNewQuote(message, *args):
    text = ""
    if len(args) > 0:
        text = " ".join(args)
        text += '\n'
        quoteList.append(text)
        SaveQuotes()
        await message.channel.send("Quote added!")


@bot.command(name="quotehelp")
async def HelpCommand(message):
    await message.channel.send("All command must be started with '!'")
    await message.channel.send("load - Generates a random loading screen")
    await message.channel.send("load text - Generates a loading screen with the described text")
    await message.channel.send("addq text - Adds a new quote to the list")


@bot.command(name="load+")
async def LoadAndPlay(message, *args):
    voice_channel = discord.utils.get(message.guild.channels, name='General')
    if voice_channel is not None:
        if len(bot.voice_clients) > 0:
            await message.channel.send("The music is already playing!")
            return
        vc = await voice_channel.connect()
        text = ""
        if len(args) > 0:
            text = " ".join(args)
        try:
            img_bytes = CreateLoadingImage(text)
            f = discord.File(img_bytes, filename="loading.png")
            await message.channel.send(file=f)
            vc.play(discord.FFmpegPCMAudio('skyrim.mp3'), after=lambda e: print('done', e))
            time.sleep(15)
            vc.stop()
            vc.disconnect()

        except OSError as e:
            await message.channel.send("Error: {0}".format(e))
            print(e)
    else:
        await message.channel.send("You need to be on a voice channel")


bot.run(TOKEN)
