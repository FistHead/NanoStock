import asyncio
from telethon import TelegramClient
from telebot.async_telebot import AsyncTeleBot

TOKEN = "8796292840:AAG_eXfOZopCAJN6-G2UAzVbnQWN3uivb9k"
bot = AsyncTeleBot(TOKEN)

api_id = 26402292
api_hash = "8f7ee20499752de0b70c8f3a323ce293"

client = TelegramClient('channel_parser', api_id, api_hash)

@bot.message_handler(commands=['start'])
async def start(message):
    await bot.reply_to(message, "пришли ссылку на тгк в формате: /get_messages @username")

@bot.message_handler(commands=['get_messages'])
async def get_messages(message):
    parts = message.text.split()
    if len(parts) < 2:
        await bot.reply_to(message, "укажи юзнейм канала. Пример:\n/get_messages @telegram")
        return

    channel_username = parts[-1]
    await bot.reply_to(message, f"парсинг канала {channel_username} начат...")
    
    out = ''
    try:
        async for msg in client.iter_messages(channel_username, limit=5): 
            if msg.text:
                out += f"📝 Пост [ID: {msg.id}]: {msg.text[:50]}...\n"
                
                comments_list = []
                try:
                    async for comment in client.iter_messages(channel_username, reply_to=msg.id, limit=16):
                        if comment.text:
                            comments_list.append(f"   └ 💬 {comment.text[:200]}")
                except Exception as comment_error:
                    pass
                
                if comments_list:
                    out += "\n".join(comments_list) + "\n\n"
                else:
                    out += "   └ 💬 Комментариев нет\n\n"
        
        if not out:
            out = "Не удалось найти текстовых сообщений...."
            
        await bot.reply_to(message, out)
        
    except Exception as e:
        await bot.reply_to(message, f"Ошибка при парсинге: {e}")

async def main():
    await client.start()
    print('Telethon клиент запущен.')
    
    print('Бот запущен и готов к работе...')
    await bot.polling(non_stop=True)

asyncio.run(main())