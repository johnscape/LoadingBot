import math
from io import BytesIO
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import random
from perlin_numpy import (
    generate_fractal_noise_2d, generate_fractal_noise_3d,
    generate_perlin_noise_2d, generate_perlin_noise_3d
)
import numpy as np

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ImageSize = (1092, 768)
FontSize = 28
DistanceFrom = (10, 40)
FogCutoff = 0.4

quoteList = [
    "I used to be an adventurer like you./Then I took an arrow in the knee.",
    "Watch Full HD Movies & TV Shows",
    "If you are fighting a Squad of archers,/it is a viable option to just drop prone at the end of your turn.",
    "That's a nice argument senator,/why don't you back up it with a source?",
    "|   |i/||    | _",
    "If you see Tim, you can ask him/to play Freebird."
]


def LoadQuotes():
    pass


def GetTextSize(text_string, font):
    ascent, descent = font.getmetrics()
    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return text_width, text_height


def AddPerlinNoise(seed: int, cellSize, levels, attenuation):
    np.random.seed(seed)
    noise = generate_perlin_noise_2d((2048, 2048), (8, 8))
    subHeight = math.ceil(ImageSize[1] * FogCutoff)
    fog = noise[:subHeight, :ImageSize[0]]
    fog += 1
    fog /= 2
    fog *= 255
    fog /= 3
    for i in range(100):
        fog[i:i+1, :] *= (0.01 * i)
    nullRow = np.zeros((1, ImageSize[0]))
    for diff in range(ImageSize[1] - subHeight):
        fog = np.vstack([nullRow, fog])
    fog = np.repeat(fog[:, :, np.newaxis], 3, axis=2)
    img = Image.fromarray(np.uint8(fog))
    return img


def AddText(drawer):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path, "font.ttf")
    font = ImageFont.truetype(dir_path, FontSize)
    r = random.choice(quoteList)
    quote = [r]
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


def GenerateImage():
    # create fog
    image = AddPerlinNoise(2, 64, 2, 1)
    drawer = ImageDraw.Draw(image)
    # add text
    AddText(drawer)

    # add image
    return image


bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='load')
async def CreateLoadingImage(message):
    try:
        img = GenerateImage()
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        f = discord.File(img_bytes, filename="loading.png")
        await message.channel.send(file=f)
    except OSError as e:
        await message.channel.send("Error: Could not open font!")
        print(e)


bot.run(TOKEN)
