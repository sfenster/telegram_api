import os
import asyncio
import sqlite3
from telethon import TelegramClient, events

api_id = '20417642'
api_hash = 'f1db98019a4acd081430ada305f34498'

client = TelegramClient('download_session', api_id, api_hash)


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
    home_dir = os.path.expanduser('~')
    file_name = f'{message.message.replace(" ", "_")}.mp4' if message.message else f'{message.id}.mp4'
    return f'{home_dir}/Desktop/incoming/{chat_title}/{file_name}'


async def download_video(client, message, chat_title, file_path):
    # Download the video and track the download progress
    try:
        await client.download_media(message, file=file_path, progress_callback=lambda d, t: print(f'{d}/{t} bytes downloaded ({d/t*100:.2f}%)'))
        print(f'Video saved to {file_path}')
        # Add the video ID to the downloaded_videos table
        with sqlite3.connect('downloads.db') as conn:
            create_downloads_table(conn)
            add_to_downloaded(conn, message.video.id)
    except Exception as e:
        print(f'Error: {str(e)}')


async def handle_video(event, prev_messages_limit=None):
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
            await download_video(client, message, chat_title, file_path)

    # Download videos from previous messages if limit is provided
    if prev_messages_limit:
        async for message in client.iter_messages(chat, limit=prev_messages_limit):
            if message.video:
                file_path = get_file_path(chat_title, message)
                with sqlite3.connect('downloads.db') as conn:
                    already_downloaded = check_already_downloaded(
                        conn, message.video.id)

                if not already_downloaded:
                    await download_video(client, message, chat_title, file_path)


async def list_channels(client):
    # Print the ID and username of each channel and chat
    async for dialog in client.iter_dialogs():
        print('Chat ID:', dialog.id, 'Chat Title:', dialog.title)


async def main():
    # Authenticate with the Telegram API
    prev_messages_limit = None
    
    await client.start()

    # Call the list_channels() function
    await list_channels(client)

    # Connect to the channel and register the handler function
    channel = [-1001576804766, -1001529334183, -
               1001844834912, -1001529959609, -1519877797]
    client.add_event_handler(lambda event: handle_video(event, prev_messages_limit), events.NewMessage(chats=channel))
    await client.run_until_disconnected()

# Run the main function
asyncio.run(main())
