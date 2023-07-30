import discord
import os
import logging
import sys
import yaml
import discord.ext.commands

# Set up a logger so we can send just the card to stdout
handler = logging.StreamHandler()

discord_logger = logging.getLogger('discord')
discord_logger.addHandler(handler)

my_logger = logging.getLogger('bingo')
my_logger.addHandler(handler)

dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)

handler.setLevel(logging.INFO)
discord_logger.setLevel(logging.INFO)
my_logger.setLevel(logging.INFO)

# Load our config file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

my_logger.info(f'Available games: {", ".join(config["sets"].keys())}')

# Set up the discord client
intents = discord.Intents.default()
intents.message_content = True

bot = discord.ext.commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    discord_logger.info(f'We have logged in as {bot.user}')

@bot.command()
async def bingo(ctx):
    await ctx.reply('Let\'s play Bingo!', mention_author=True)

bot.run(os.environ['DISCORD_TOKEN'], log_handler=None)