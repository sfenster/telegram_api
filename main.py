from telethon import TelegramClient, events

api_id = 20417642
api_hash = f1db98019a4acd081430ada305f34498

client = TelegramClient('session_name', api_id, api_hash)

# Authenticate with the Telegram API
client.start()

# Define a handler function for video messages


async def handle_video(event):
    message = event.message
    if message.video:
        # Download the video
        await client.download_media(message, file='videos/{}'.format(message.video.id))

# Connect to the channel and register the handler function
channel = 'CHANNEL_USERNAME'
client.add_event_handler(handle_video, events.NewMessage(chats=channel))
client.run_until_disconnected()
