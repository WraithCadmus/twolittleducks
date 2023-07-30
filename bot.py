import discord
import os
import logging
import sys
import yaml
import discord.ext.commands

# Load our config file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

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
async def bingo(ctx, arg='help'):
    if arg == 'list':
        reply = []
        reply.append("Available games:")
        for game in config['sets']:
            reply.append(f'- `{game}`: {config["sets"][game]["description"]}')
            await ctx.reply('\n'.join(reply), mention_author=True)
    elif arg == 'help':
        await ctx.reply('Usage: Type `!bingo game` to play a specific game, `!bingo list` to list games, or `"bingo help` for this message')
    else:
        pass



bot.run(os.environ['DISCORD_TOKEN'], log_handler=None)