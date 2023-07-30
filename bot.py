import discord
import os
import logging
import sys
import yaml
import discord.ext.commands
import cairocffi as cairo
import pangocffi as pango
import pangocairocffi as pangocairo
import random
import io
import PIL.Image
import math

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
        try:
            game = config['sets'][arg]
        except KeyError:
            await ctx.reply(f'Unknown game: `{arg}`. Use `!bingo list` to list games.')
            return

        WIDTH  = config['space_size']*game['size'][0]
        HEIGHT = config['space_size']*game['size'][1]

        # Initialise the image
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        context = cairo.Context(surface)

        # Set the background
        # We use these inline lambdas to turn 0-255 values into the 0-1 floats that cairo expects
        context.set_source_rgb(*list(map(lambda x: x/255, game['background_color'])))
        context.rectangle(0, 0, WIDTH, HEIGHT)
        context.fill()

        # Draw grid
        context.set_source_rgb(*list(map(lambda x: x/255, game['line_color'])))
        for i in range(1, game['size'][0]):
            context.move_to(i*config['space_size'], 0)
            context.line_to(i*config['space_size'], HEIGHT)
            context.stroke()

        for i in range(1, game['size'][1]):
            context.move_to(0, i*config['space_size'])
            context.line_to(WIDTH, i*config['space_size'])
            context.stroke()

        # Draw the Free Space symbol

        # Push our existing card onto the stack
        context.save()

        # Open the PNG file as a stream, load it with PIL, and turn it into a separate surface in Cairo
        f = open(game['free_space'], 'rb')
        i = io.BytesIO(f.read())
        im = PIL.Image.open(i)
        imagebuffer = io.BytesIO()  
        im.save(imagebuffer, format="PNG")
        imagebuffer.seek(0)
        imagesurface = cairo.ImageSurface.create_from_png(imagebuffer)

        # Move the cursor to the top left of the centre square
        context.translate(config['space_size']*math.floor(game['size'][0]/2), config['space_size']*math.floor(game['size'][1]/2) )

        # Shrink it to the size of a square
        img_height = imagesurface.get_height()
        img_width = imagesurface.get_width()

        width_ratio = config['space_size'] / float(img_width)
        height_ratio = config['space_size'] / float(img_height)
        ratio = min(width_ratio, height_ratio)

        context.scale(ratio, ratio)

        # Apply the image
        context.set_source_surface(imagesurface, 0, 0)
        context.paint()

        # Pop our old work off the stack, now we're back in 'normal' draw mode
        context.restore()

        # Now we can write our items
        # Take our bingo items, and randomise them
        random.shuffle(game['items'])
        item_tracker=0
        for y in range(game['size'][0]):
            for x in range(game['size'][0]):
                # Skip the center square
                if (x,y) == (math.floor(game['size'][0]/2), math.floor(game['size'][1]/2)):
                    pass
                else:
                    # Push main drawing to the stack
                    context.save()

                    # Set outrselves to the font color
                    context.set_source_rgb(*list(map(lambda x: x/255, game['text_color'])))

                    # Move to the top-right of the square (less a margin)
                    context.translate(x*config['space_size']+config['margin'], y*config['space_size']+config['margin'])
                    # Make a new layout
                    layout = pangocairo.create_layout(context)
                    layout.width = pango.units_from_double(config['space_size']-2*config['margin'])
                    layout.height = pango.units_from_double(config['space_size']-2*config['margin'])
                    layout.alignment = pango.Alignment.CENTER

                    # Starting font size bounds
                    lower_bound = 0
                    upper_bound =  config['space_size']

                    # We do a 8-step binary search to find the ideal size
                    for i in range(8):
                        # Guess the size
                        guess = upper_bound - (upper_bound - lower_bound)/2
        
                        # Try this size
                        layout.apply_markup('<span font="{}">{}</span>'.format(guess, game['items'][item_tracker]))
                        if layout.get_extents()[1].height > (config['space_size']-config['margin'])*1000 or layout.get_extents()[1].width > (config['space_size']-config['margin'])*1000:
                            # We're too big
                            upper_bound = guess
                        else:
                            # We might be able to go bigger
                            lower_bound = guess

                    # Final format, better to be a little too small, so use lower bound
                    layout.apply_markup('<span font="{}">{}</span>'.format(lower_bound, game['items'][item_tracker]))
                    
                    # Shuffle down to center vertically
                    context.translate(0, (config['space_size']-config['margin']*2)//2 - ((layout.get_extents()[1].height//1000)//2)  )

                    logging.debug('{},{}: {}, {}'.format(x, y, game['items'][item_tracker], lower_bound))

                    item_tracker = item_tracker + 1
                    pangocairo.show_layout(context, layout)
                    context.restore()
        
        with io.BytesIO() as card:
            surface.write_to_png(card)
            card.seek(0)
            await ctx.reply(f'Here\'s your bingo card for {game["description"]}', file=discord.File(fp=card, filename='bingo.png'))

bot.run(os.environ['DISCORD_TOKEN'], log_handler=None)