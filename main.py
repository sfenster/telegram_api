import os
import asyncio
import sqlite3
import dotenv
import config
import importlib
from telethon import TelegramClient, events

dotenv.load_dotenv()
api_id = os.environ.get('API_ID')
api_hash = os.environ.get('API_HASH')

client = TelegramClient('download_session', api_id, api_hash)
video_min_duration = 10
downloads = None
home = os.path.expanduser('~')

envclass_name, envsubclass_name =os.environ.get("APP_SETTINGS", 'config.DevelopmentConfig').split(".")
envclass = importlib.import_module(envclass_name)
env = getattr(envclass, envsubclass_name)



def get_download_dir():
    dl = getattr(env, 'DOWNLOADS')
    dl = dl.replace("~", home)
    try:
        # Attempt to open the file for writing
        #with open(dl, 'w'):
        if os.access(dl, os.W_OK):
            return dl  # File was opened successfully
        # Default to home directory if specified path is not accessible
        else:
            dl = f'{home}/incoming'
            return dl
    except OSError as e:
        # File location is not accessible or writable
        print(f'Error: {str(e)}')
    


def create_downloads_table(conn):
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS downloaded_videos (id INTEGER PRIMARY KEY)')


def check_already_downloaded(conn, video_id):
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM downloaded_videos WHERE id=?', (video_id,))
    return cursor.fetchone() is not None


def add_to_downloaded(conn, video_id):
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO downloaded_videos (id) VALUES (?)', (video_id,))
    conn.commit()


def get_file_path(chat_title, message):
    
    file_name = f'{message.message.replace(" ", "_")}.mp4' if message.message else f'{message.id}.mp4'
    print(f'Potential file path = {downloads}/{chat_title}/{file_name}')
    return f'{downloads}/{chat_title}/{file_name}'


async def download_video(client, message, file_path):
    # Download the video and track the download progress
    try:
        # Get the duration of the video
        duration = message.file.duration

        # Only download the video if it's longer than 10 seconds
        if duration > video_min_duration:
            await client.download_media(message, file=file_path, progress_callback=lambda d, t: print(f'{d}/{t} bytes downloaded ({d/t*100:.2f}%)'))
            print(f'Video saved to {file_path}')
            # Add the video ID to the downloaded_videos table
            with sqlite3.connect('downloads.db') as conn:
                create_downloads_table(conn)
                add_to_downloaded(conn, message.video.id)
        else:
            print(
                f'Video duration is {duration}s, which is shorter than 10s. Skipping download.')
    except Exception as e:
        print(f'Error: {str(e)}')


async def handle_video(event):
    print('New message detected.')
    message = event.message
    chat = await event.get_chat()
    chat_title = chat.title.replace(' ', '_')
    print(
        f'New message from chat {chat_title} — id: {message.id}, text: {message.message}')

    # Check if the message contains a video
    if message.video:
        print(f'New message contains video called {message.video.id}.')
        # Define the file path where the video will be saved
        file_path = get_file_path(chat_title, message)
        # Create the folder if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Check if the video has already been downloaded
        with sqlite3.connect('downloads.db') as conn:
            already_downloaded = check_already_downloaded(
                conn, message.video.id)

        if already_downloaded:
            print(
                f'Video with ID {message.video.id} has already been downloaded.')
        else:
            # Download the video
            await download_video(client, message, file_path)

    # Download videos from previous messages if limit is provided


async def handle_previous_videos(chat, prev_messages_limit=None):
    chat_title = chat.title.replace(' ', '_')
    async for message in client.iter_messages(chat, limit=prev_messages_limit):
        try:
            if message.video:
                print(f'Message has video with id {message.video.id} and duration {message.file.duration}.')
                file_path = get_file_path(chat_title, message)
                with sqlite3.connect('downloads.db') as conn:
                    already_downloaded = check_already_downloaded(
                        conn, message.video.id)

                if not already_downloaded:
                    await download_video(client, message, file_path)
                else:
                    print(f'{message.video.id} already downloaded.')
        except Exception as e:
            print(f'Error: {str(e)}')
            print('Resuming...')

async def list_channels(client):
    # Print the ID and username of each channel and chat
    async for dialog in client.iter_dialogs():
        print('Chat ID:', dialog.id, 'Chat Title:', dialog.title)


async def rip_channel(id, limit):
    # Call the handle_previous_videos() function for a single chat
    if limit is not None:
        chat = await client.get_entity(id)
        await handle_previous_videos(chat, limit)


async def main():
    # Authenticate with the Telegram API
    prev_messages_limit = None
    single_chat_id = -1001529959609
    single_chat_msg_limit = None
    channel = [-1001576804766, 
               -1001844834912, 
               -1001529959609, 
               -1001519877797,
               -1001835054584,
               -1001572063931, 
               -1001748083163,
               ]
    
    downloads = get_download_dir()
    print(f'download directory: {downloads}')

    await client.start()
    client.add_event_handler(handle_video, events.NewMessage(chats=channel))

        # Call the list_channels() function
    await list_channels(client)

        # Call the rip_channel() function
    await rip_channel(single_chat_id, single_chat_msg_limit)

    if prev_messages_limit is not None:
        for chat_id in channel:
            chat = await client.get_entity(chat_id)
            await handle_previous_videos(chat, prev_messages_limit)

    await client.run_until_disconnected()
    

# Run the main function
asyncio.run(main())
