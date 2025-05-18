import logging
import asyncio
import requests
from io import BytesIO
from PIL import Image

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# Configure logging
logging.basicConfig(level=logging.INFO)
TOKEN = ""

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Start command handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Welcome to the Simple Sticker Creator!\n\n"
        "Send me any image URL and I'll instantly convert it to a Telegram sticker."
    )

# Help command handler
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🔍 How to use this bot:\n\n"
        "1. Simply send me an image URL starting with http:// or https://\n"
        "2. I'll immediately return it as a sticker\n"
        "3. You can save or forward the sticker to your chats\n\n"
        "That's it! No sticker packs or extra steps needed."
    )

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
        
        # rezise
        try:
            img = Image.open(BytesIO(response.content))
            width, height = img.size
            if width > height:
                new_width = 512
                new_height = int(height * (512 / width))
            else:
                new_height = 512
                new_width = int(width * (512 / height))

            # https://www.geeksforgeeks.org/python-pil-image-resize-method/
            img = img.resize((new_width, new_height), Image.LANCZOS)

            # save image
            output = BytesIO()
            img.save(output, format="WEBP", optimize=True)
            
            # check file size
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
            
            # delete processing message
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)
            
            from aiogram.types import BufferedInputFile
            # send as sticker
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker=BufferedInputFile(output.getvalue(), filename="sticker.webp")
            )
            
            # thamk yu guten tag gudbye
            await message.answer(
                "✅ Sticker created!\n\n"
                "You can now forward this sticker to any chat.\n"
                "To save it to your Favorites, tap and hold the sticker, then select 'Add to Favorites'."
            )
            
        except Exception as e:
            await bot.edit_message_text(
                f"❌ Failed to process image: {str(e)}",
                chat_id=message.chat.id,
                message_id=processing_message.message_id
            )
            logging.error(f"Image processing error: {str(e)}")
            
    except Exception as e:
        await bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id=message.chat.id,
            message_id=processing_message.message_id
        )
        logging.error(f"Request error: {str(e)}")

# if img isnt url
@dp.message(F.text)
async def handle_text(message: types.Message):
    await message.answer("Please send a valid image URL starting with http:// or https://")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())