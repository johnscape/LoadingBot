import math
from io import BytesIO
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import random
import numpy as np

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ImageSize = (1092, 768)
FontSize = 28
DistanceFrom = (10, 40)

quoteList = [
    "I used to be an adventurer like you./Then I took an arrow in the knee.",
    "Watch Full HD Movies & TV Shows",
    "If you are fighting a Squad of archers,/it is a viable option to just drop prone at the end of your turn.",
    "That's a nice argument senator,/why don't you back up it with a source?",
    "|   |i/||    | _"
]


class PerlinSampler:
    def __init__(self, seed, width, height):
        self.Width = width
        self.Height = height
        self.Random = seed
        self.Gradients = [0] * self.Width * self.Height * 2

        np.random.seed(self.Random)
        for i in range(len(self.Gradients)):
            angle = np.random.randint(0, 2147483647) * math.pi * 2
            x = math.sin(angle)
            y = math.cos(angle)
            self.Gradients[i] = x
            self.Gradients[i + 1] = y
            i += 1

    def dot(self, cellX, cellY, vx, vy):
        offset = (cellX + cellY * self.Width) * 2
        wx = self.Gradients[offset]
        wy = self.Gradients[offset + 1]
        return wx * vx + wy * vy

    def lerp(self, a, b, t):
        return a + t * (b - a)

    def curve(self, t):
        return t * t * (3 - 2 * t)

    def GetValue(self, x, y):
        xCell = math.floor(x)
        yCell = math.floor(y)
        xFrac = x - xCell
        yFrac = y - yCell

        x0 = xCell
        y0 = yCell
        x1 = 0 if xCell == self.Width else xCell + 1
        y1 = 0 if yCell == self.Height else yCell + 1

        v00 = self.dot(x0, y0, xFrac, yFrac)
        v10 = self.dot(x1, y0, xFrac - 1, yFrac)
        v01 = self.dot(x0, y1, xFrac, yFrac - 1)
        v11 = self.dot(x1, y1, xFrac - 1, yFrac - 1)

        vx0 = self.lerp(v00, v10, self.curve(xFrac))
        vx1 = self.lerp(v01, v11, self.curve(xFrac))

        return self.lerp(vx0, vx1, self.curve(yFrac))


def LoadQuotes():
    pass


def GetTextSize(text_string, font):
    ascent, descent = font.getmetrics()
    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return text_width, text_height


def AddPerlinNoise(img: Image, seed: int, cellSize, levels, attenuation):
    imgArray = np.asarray(img)
    noise = PerlinSampler(
        seed,
        math.ceil(ImageSize[0] / cellSize),
        math.ceil(ImageSize[1] / cellSize)
    )
    for x in range(ImageSize[0]):
        for y in range(ImageSize[1]):
            imgArray[x, y] = noise.GetValue(x, y)
    # turbulance
    raster = [0] * ImageSize[0] * ImageSize[1]
    localPeriodInverse = 1 / cellSize
    frequencyInverse = 1
    att = 1
    weight = 0
    for l in range(levels):
        sampler = PerlinSampler(
            seed + l,
            math.ceil(ImageSize[0] * localPeriodInverse),
            math.ceil(ImageSize[1] * localPeriodInverse)
        )

        for x in range(ImageSize[0]):
            for y in range(ImageSize[1]):
                val = sampler.GetValue(x * localPeriodInverse, y * localPeriodInverse)
                raster[(x + y * ImageSize[0])] += val * math.pow(frequencyInverse, attenuation)

        weight += math.pow(frequencyInverse, attenuation)
        frequencyInverse *= 5
        localPeriodInverse *= 2
        att *= attenuation

    weightInverse = 1 / weight
    for x in range(ImageSize[0]):
        for y in range(ImageSize[1]):
            raster[(x + y * ImageSize[0])] *= weightInverse
    for x in range(ImageSize[0]):
        for y in range(ImageSize[1]):
            offset = (x + y * ImageSize[0])
            r, g, b = raster[offset]
            r = ((r + 1) / 2) * 255
            g = ((g + 1) / 2) * 255
            b = ((b + 1) / 2) * 255
            imgArray[x, y] = (r, g, b)
    img = Image.fromarray(np.uint8(imgArray))
    img.show()

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
    image = Image.new('RGB', ImageSize, (0, 0, 0))
    drawer = ImageDraw.Draw(image)
    # create fog
    AddPerlinNoise(image, 2, 64, 2, 1)
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
