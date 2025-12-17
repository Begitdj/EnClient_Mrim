import asyncio

async def setup(bot):
    # Эта надпись появится при запуске бота
    print("Sample Plugin!")

async def hello_cmd(bot, args):
    """Команда: hello <email>"""
    if args:
        target = args[0]
        await bot.send(target, "Привет от SamplePlugin!")
        print(f"Поприветствовал {target}")
    else:
        print("Кому отправить привет?")

# Регистрация команды в консоли
commands = {
    "hello": hello_cmd
}
