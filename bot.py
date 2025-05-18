import logging
import asyncio
import requests
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
print(load_dotenv())

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# for PythonAnywhere, comment out if running locally.
from aiogram.client.session.aiohttp import AiohttpSession
session = AiohttpSession(proxy='http://proxy.server:3128')


logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('TOKEN')
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# /start command
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Welcome to the Simple Sticker Creator!\n\n"
        "Send me any image URL and I'll instantly convert it to a Telegram sticker."
    )

# /help command handler
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🔍 How to use this bot:\n\n"
        "1. Simply send me an image or an image URL starting with http:// or https://\n"
        "2. I'll immediately return it as a sticker\n"
        "3. You can save or forward the sticker to your chats\n\n"
        "That's it! No sticker packs or extra steps needed."
    )

# process image to sticker
async def process_image_to_sticker(image_data, message, processing_message):
    """
    Process image data into a Telegram sticker.

    Args:
        image_data: Binary image data
        message: Original message object
        processing_message: Processing notification message object
    """
    try:
        img = Image.open(BytesIO(image_data))
        # resize image
        width, height = img.size
        if width > height:
            new_width = 512
            new_height = int(height * (512 / width))
        else:
            new_height = 512
            new_width = int(width * (512 / height))

        # https://www.geeksforgeeks.org/python-pil-image-resize-method/
        img = img.resize((new_width, new_height), Image.LANCZOS)

        output = BytesIO()
        img.save(output, format="WEBP", optimize=True)
        if output.tell() > 512 * 1024:
            output = BytesIO()
            quality = 95

            while quality > 30:
                output.seek(0)
                output.truncate(0)
                img.save(output, format="WEBP", optimize=True, quality=quality)
                if output.tell() <= 512 * 1024:
                    break
                quality -= 5

        output.seek(0)

        # delete earlier msg
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=processing_message.message_id
        )

        # Send sticker
        from aiogram.types import BufferedInputFile
        await bot.send_sticker(
            chat_id=message.chat.id,
            sticker=BufferedInputFile(output.getvalue(), filename="sticker.webp")
        )

        # Send success message
        await message.answer(
            "✅ Sticker created!\n\n"
            "You can now forward this sticker to any chat.\n"
            "To save it to your Favorites, tap and hold the sticker, then select 'Add to Favorites'."
        )
        return True
    except Exception as e:
        await bot.edit_message_text(
            f"❌ Failed to process image: {str(e)}",
            chat_id=message.chat.id,
            message_id=processing_message.message_id
        )
        logging.error(f"Image processing error: {str(e)}")
        return False

# if message starts with URL
@dp.message(F.text.startswith(("http://", "https://")))
async def process_url(message: types.Message):
    url = message.text
    processing_message = await message.answer("⏳ Processing image...")
    
    try:
        # download image
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            await bot.edit_message_text(
                f"❌ Failed to download image. Error code: {response.status_code}",
                chat_id=message.chat.id,
                message_id=processing_message.message_id
            )
            return
        
        # check if is not img
        content_type = response.headers.get('Content-Type', '').lower()
        is_image = content_type.startswith('image/')

        if not is_image and not (
            url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
        ):
            await bot.edit_message_text(
                "❌ The URL doesn't point to a supported image format. Please send a JPG, JPEG, PNG, WEBP, or GIF image URL.",
                chat_id=message.chat.id,
                message_id=processing_message.message_id
            )
            return

        # process img
        await process_image_to_sticker(response.content, message, processing_message)
    except Exception as e:
        await bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id=message.chat.id,
            message_id=processing_message.message_id
        )
        logging.error(f"Request error: {str(e)}")

# if url can't be downloaded thanks to PythonAnywhere's allow list :(, 
# allow user to send attached image
@dp.message(F.photo)
async def process_picture(message: types.Message):
    processing_message = await message.answer("⏳ Processing image...")

    try:
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # fetch from attachment and process
        file_content = await bot.download_file(file_path)
        await process_image_to_sticker(file_content.read(), message, processing_message)

    except Exception as e:
        await bot.edit_message_text(
            f"❌ Error: {str(e)}. If the file fails to download, please send it as an attachment.",
            chat_id=message.chat.id,
            message_id=processing_message.message_id
        )
        logging.error(f"File download error: {str(e)}.")

# if img isnt url
@dp.message(F.text)
async def handle_text(message: types.Message):
    await message.answer("Please send attach an image or send a valid Image URL starting with http:// or https://")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())