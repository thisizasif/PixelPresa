from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from PIL import Image
import os
import tempfile
import logging

TOKEN = ' YOUT BOT TOKEN HERE '
SIZE, PHOTO, QUALITY, ANOTHER = range(4)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"),
              logging.StreamHandler()])


async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'Welcome to the Image Compressor Bot!\n\n'
        'Send me a photo you want to compress or type /help for more instructions.'
    )
    return PHOTO


async def photo(update: Update, context: CallbackContext) -> int:
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text(
        'Enter the desired file size in KB, MB, or MiB (e.g., 500KB, 2MB).')
    return SIZE


def resize_image(file_path: str, target_size: int, unit: str,
                 quality: int) -> str:
    with Image.open(file_path) as img:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        new_file_path = temp_file.name

        while True:
            img.save(new_file_path, 'JPEG', quality=quality)
            file_size = os.path.getsize(new_file_path)
            if (unit == 'KB' and file_size / 1024 <= target_size) or \
               (unit in ('MB', 'MiB') and file_size / (1024 * 1024) <= target_size):
                break
            quality -= 5
            if quality < 5:
                break

        return new_file_path


async def set_size(update: Update, context: CallbackContext) -> int:
    try:
        size_str = update.message.text.strip().upper()
        if size_str.endswith('KB'):
            target_size = int(size_str[:-2].strip())
            unit = 'KB'
        elif size_str.endswith('MB'):
            target_size = int(size_str[:-2].strip())
            unit = 'MB'
        elif size_str.endswith('MIB'):
            target_size = int(size_str[:-3].strip())
            unit = 'MiB'
        else:
            await update.message.reply_text(
                'Invalid size format. Please use KB, MB, or MiB (e.g., 500KB, 2MB, 1MiB).'
            )
            return SIZE

        context.user_data['target_size'] = target_size
        context.user_data['unit'] = unit
        await update.message.reply_text(
            'Enter the desired image quality (1-95, where 95 is the highest quality).'
        )
        return QUALITY
    except Exception as e:
        logging.error(f'Error: {e}')
        await update.message.reply_text(f'Error: {e}\nPlease try again.')
        return SIZE


async def set_quality(update: Update, context: CallbackContext) -> int:
    try:
        quality = int(update.message.text.strip())
        if not (1 <= quality <= 95):
            raise ValueError('Quality must be between 1 and 95.')

        target_size = context.user_data['target_size']
        unit = context.user_data['unit']

        await update.message.reply_text('Processing your image, please wait...'
                                        )

        photo_file = await context.bot.get_file(context.user_data['photo'])
        temp_input_file = tempfile.NamedTemporaryFile(delete=False)
        await photo_file.download_to_drive(temp_input_file.name)

        new_file_path = resize_image(temp_input_file.name, target_size, unit,
                                     quality)

        with open(new_file_path, 'rb') as file:
            await update.message.reply_document(document=InputFile(file))

        original_size = os.path.getsize(temp_input_file.name)
        compressed_size = os.path.getsize(new_file_path)
        compression_ratio = original_size / compressed_size

        os.remove(temp_input_file.name)
        os.remove(new_file_path)

        await update.message.reply_text(
            f'Here is your compressed image.\n'
            f'Original size: {original_size / 1024:.2f} KB\n'
            f'Compressed size: {compressed_size / 1024:.2f} KB\n'
            f'Compression ratio: {compression_ratio:.2f}\n\n'
            'Do you want to compress another photo? Send another photo or type /cancel to stop.'
        )
        return PHOTO
    except Exception as e:
        logging.error(f'Error: {e}')
        await update.message.reply_text(f'Error: {e}\nPlease try again.')
        return SIZE


async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'Operation cancelled. Thank you for using the Image Compressor Bot!')
    return ConversationHandler.END


async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "I can help you compress images. Here are the commands you can use:\n"
        "/start - Start the compression process\n"
        "/cancel - Cancel the current operation\n"
        "To compress an image:\n"
        "1. Send me a photo\n"
        "2. Enter the desired file size (e.g., 500KB, 2MB, 1MiB)\n"
        "3. Enter the desired image quality (1-95, where 95 is the highest quality)\n"
        "If you make a mistake, just send the size again.")
    await update.message.reply_text(help_text)


async def invalid_message(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Invalid input. Please send a valid photo or use /cancel to exit.')


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [
                MessageHandler(filters.PHOTO, photo),
                MessageHandler(filters.ALL, invalid_message)
            ],
            SIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_size),
                MessageHandler(filters.ALL, invalid_message)
            ],
            QUALITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_quality),
                MessageHandler(filters.ALL, invalid_message)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.ALL, invalid_message))

    application.run_polling()


if __name__ == '__main__':
    main()
  
