import discord
from discord.ext import commands
from googleapiclient.discovery import build
from google.cloud import storage
from dotenv import load_dotenv
import os
import requests
from google.oauth2 import service_account
import uuid

# Load environment variables from .env file
load_dotenv()

# Discord Bot Setup
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix='ch!', intents=intents)

# Google Custom Search API Setup
API_KEY = os.getenv('API_KEY')
CX = os.getenv('CX')

# Google Cloud Storage Setup
PROJECT_ID = os.getenv('PROJECT_ID')
BUCKET_NAME = os.getenv('BUCKET_NAME')

# Google Cloud Service Account Key File Setup
KEY_FILE_PATH = 'key.json'

# Google Custom Search API Setup
credentials = service_account.Credentials.from_service_account_file(KEY_FILE_PATH)
service = build('customsearch', 'v1', developerKey=API_KEY, credentials=credentials)

# Google Cloud Storage Setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = KEY_FILE_PATH
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')


@bot.command()
async def search(ctx, *, keyword):
    try:
        # Make a request to the Google Custom Search API
        response = service.cse().list(q=keyword, cx=CX, searchType='image').execute()
        items = response['items']

        # Handle errors if no search results are found
        if not items:
            await ctx.send("No photos found for the given keyword.")
            return

        # Track distinct photo sources
        distinct_sources = set()
        photos_downloaded = 0

        for item in items:
            # Check if the photo source is distinct
            if item['link'] not in distinct_sources:
                distinct_sources.add(item['link'])

                # Download the photo from the URL
                extension = item['link'].split('.')[-1]
                filename = f"{uuid.uuid4()}.{extension}"
                blob = bucket.blob(filename)
                blob.upload_from_string(requests.get(item['link']).content)

                photos_downloaded += 1

                # Stop when 10 distinct photos are downloaded
                if photos_downloaded == 10:
                    break

        # Generate the link to the Google Cloud Storage bucket
        storage_link = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        await ctx.send(f"Search complete! You can access the photos [here]({storage_link}).")

    except Exception as e:
        # Handle errors during the search process
        await ctx.send("An error occurred during the search process. Please try again later.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Please try again.")


@bot.event
async def on_message(message):
    if message.channel.id == 833221715366641684:  # Replace with your desired channel ID
        await bot.process_commands(message)


# Run the bot
bot.run(os.getenv('BOT_TOKEN'))
