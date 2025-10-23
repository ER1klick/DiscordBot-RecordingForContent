import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Задаем намерения (intents)
intents = disnake.Intents.default()
intents.members = True
intents.message_content = True # Необходимо для некоторых команд

# Создаем экземпляр бота
bot = commands.Bot(
    command_prefix="!", # Префикс для текстовых команд (если понадобятся)
    intents=intents,
    test_guilds=[int(os.getenv("TEST_GUILD_ID"))], # Сервер для быстрой регистрации команд
    reload=True # Автоматическая перезагрузка когов при изменении файлов
)

@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен и готов к работе!")
    print(f"disnake version: {disnake.__version__}")

# Загружаем все файлы .py из папки cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and not filename.startswith("__"):
        try:
            bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Успешно загружен ког: {filename}")
        except Exception as e:
            print(f"Не удалось загрузить ког {filename}: {e}")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))