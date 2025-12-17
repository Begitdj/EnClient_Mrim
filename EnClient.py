# говно код продакшен
from proto_types import *
from proto import *
import json, random, aiohttp, asyncio, os, importlib.util, shutil, concurrent.futures
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
sequence = 1 # Пока Статик
magic = 0xDEADBEEF  # написано что надо хз
proto = 65543  # Версия протокола наверное
session = PromptSession() # Промты Тулкиты
# Пул потоков(10)
executor = concurrent.futures. ThreadPoolExecutor(max_workers=10)
plugin_commands = {}
# For plugins only!
class PluginInterface:
    def __init__(self, writer):
        self.writer = writer
        self.message_handlers = []
        self.queue = asyncio.Queue()
        
    async def on_message(self, handler):
        self.message_handlers.append(handler)
        
    async def send(self, target, text):
        await send_message(target, text, self.writer)

    async def blog(self, text):
        await MicroBlog(text, self.writer)

    async def status(self, status_id):
        await changeStatus(status_id, self.writer)

    async def alarm(self, target):
        await alarm(target, self.writer)

    async def accept(self, email):
        await accept(email, self.writer)
    async def _message_worker(self):
        while True:
            msg_data = await self.queue.get()

            for handler in self.message_handlers:
                try:
                    await handler(msg_data)
                except Exception as e:
                    print(f"[!] Ошибка в плагине {handler.__name__}: {e}")
            
            self.queue.task_done()

async def load_plugins(writer):
    global plugin_interface
    plugin_interface = PluginInterface(writer)
    asyncio.create_task(plugin_interface._message_worker())
    base = os.path.dirname(os.path.abspath(__file__))
    plugins_dir = os.path.join(base, "EnClient/plugins")
    
    if not os.path.exists("EnClient"): os.mkdir("EnClient")
    if not os.path.exists(plugins_dir): os.mkdir(plugins_dir)
    if not os.path.exists(f"{plugins_dir}/configs"): os.mkdir(f"{plugins_dir}/configs")
    
    for file in os.listdir(plugins_dir):
        if file.endswith(".py"):
            name = file[:-3]
            try:
                file_path = os.path.join(plugins_dir, file)
                spec = importlib.util.spec_from_file_location(name, file_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                if hasattr(mod, 'commands'):
                    plugin_commands.update(mod.commands)
                
                if hasattr(mod, "setup"):
                    await mod.setup(plugin_interface)
                    
                print(f"[*] Плагин {file} загружен")
            except Exception as e:
                print(f"[!] Ошибка плагина {file}: {e}")
            

async def monitor(reader, writer):
    print("EnClient Monitoring on")
    while True:
        try:
            data = await reader.read(4096) 
            
            if not data:
                print("--- Connection closed Reconnecting.... ---")
                return False
            if len(data) >= 44:
                header = await unbuild_header(data[:44])
                other_data = data[44:]

                if header.get("command") == 0x1009:
                    print("Получен пакет сообщения!")
                    
                    # Извлекаем ID сообщения
                    msg_id = int.from_bytes(other_data[0:4], "little")

                    # Извлекаем флаги
                    flags = int.from_bytes(other_data[4:8], "little")

                    # От кого
                    from_msg_length = int.from_bytes(other_data[8:12], "little")
                    from_msg = other_data[12:12 + from_msg_length].decode('windows-1251')

                    # Извлекаем сообщение
                    msg_length = int.from_bytes(other_data[12 + from_msg_length:16 + from_msg_length], "little")
                    message_text = other_data[16 + from_msg_length:16 + from_msg_length + msg_length].decode('windows-1251')

                    # Извлекаем rtf сообщение
                    rtf_length = int.from_bytes(other_data[16 + from_msg_length + msg_length:20 + from_msg_length + msg_length], "little")
                    rtf_message = other_data[20 + from_msg_length + msg_length:].decode('windows-1251')

                    # Если подходящие флаги, то идем дальше (почему бы и нет?)
                    if flags in [0, 128]:
                        # Создаем пакет о том, что сообщение получено
                        print("Тип: Сообщение")
                        from_bytes = await create_lps(from_msg)
                        msg_id_bytes = await create_ul(msg_id)
                        packet_size = len(from_bytes + msg_id_bytes)
                        packet_data = from_bytes + msg_id_bytes

                        # Отправляем пакет
                        packetRecv = await build_header(magic, proto, sequence, MRIM_CS_MESSAGE_RECV, packet_size) + packet_data
                        writer.write(packetRecv)
                        await writer.drain()
                        msg_data = {"from": from_msg, "text": message_text, "id": msg_id}
                        plugin_interface.queue.put_nowait(msg_data)
    
                        
                        print("Отправил команду MRIM_CS_MESSAGE_RECV")
                        print(f"От: {from_msg}\nТекст: {message_text}")
                    elif flags == 12:
                        print("Тип: Авторизация")
                        print(f"От: {from_msg}")
                        print("Для одобрения можно воспользоваться командой accept {email}")
        except Exception as e:
            print(f"--- Error: {e} ---")
            return False
    return True
    
async def hi():
    print("EnClient 1.7\nBy Sony Eshka(Begitdj) <3")
    if not os.path.exists("EnClient"): os.mkdir("EnClient")
    if os.path.exists("EnClient.json"):
        print("[?] Старый путь хранения файла!")
        shutil.move('EnClient.json', 'EnClient/EnClient.json')
        print("[+] Путь автоматически был переделан под новый формат!")
    if os.path.exists("EnClient/EnClient.json"):
        		try:
        			with open("EnClient/EnClient.json", 'r', encoding='utf-8') as f:
        				data = json.load(f)
        		except json.JSONDecodeError:
        			print("Ошибка декодирования JSON!!")
    else:
        print("Привет! Похоже вы запустили EnClient в первый раз. Пройдите простую первоначальную настройку")
        data = {
            "login": input("Введите логин: "),
            "password": input("Введите пароль: "),
            "host": input("Введите Хост: "),
            "port": input("Введите Порт(от сервера редиректа обычно это 2042): ")
        }
        if data['port'].isdigit() == False:
        	print("Порт содержит текст!")
        	os._exit(0)
        q = input("Сохранить данные в файл для последующей авто авторизации?(y/n): ")
        if q.lower() == 'y':
            with open("EnClient/EnClient.json", 'w', encoding='utf-8') as f:
            	json.dump(data, f, indent=2, ensure_ascii=False)
            print("Сохранено!")
        elif q.lower() == 'n':
        	print("Пропуск...")
        else:
        	print("Некоректный ввод! Пропуск...")
    
    # Вызываем твою функцию auth
    result = await auth(data['login'], data['password'], data['host'], data['port'], sequence)
    return result
async def getMainServer(redirect_host, redirect_port):
	    try:
	    	reader, writer = await asyncio.open_connection(redirect_host, redirect_port)
	    except Exception as e:
	       print(f"Error Conection: {redirect_host}:{redirect_port}: {e}")
	       return None
	       
	    try:
	       redirect_data = await reader.read(-1)
	       writer.close()
	       await writer.wait_closed()
	    except Exception as e:
	       print(f"Error during data reading or closing: {e}")
	       return None
        

	    if not redirect_data:
	           print(f"Final data from: {redirect_host}:{redirect_port}")
	           return b''
            
	    return redirect_data.decode('utf-8')
async def auth(login, passworde, host, port, sequence):
    try:
    	main = await getMainServer(host, port)
    	mainParts = main.strip().split(':')
    	host = mainParts[0]
    	port = mainParts[1]
    except Exception as e:
        print("Error!")
        os._exit(0)
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            print(f"Подключено к {host}:{port}")
            header = await build_header(magic, proto, sequence, MRIM_CS_HELLO, 0)
            writer.write(header)
            await writer.drain()
            print("Отправлен HELLO пакет")
            sequence += 1
            data = await reader.read(1024)
            header = await unbuild_header(data)
            email = await create_lps(login)
            password = await create_lps(passworde)
            status = await create_ul(1)
            user_agent = await create_lps("EnClient")
            size = len(email + password + status + user_agent)
            packet = await build_header(magic, proto, sequence, MRIM_CS_LOGIN2, size) + email + password + status + user_agent
            writer.write(packet)
            await writer.drain()
            print("Получаб пакет от сервера после авторизации: ")
            data = await reader.read(1024)
            header = await unbuild_header(data)
            await asyncio.sleep(0.1)
            data = await reader.read(1024)
            header = await unbuild_header(data)
            if header['magic'] == 0: # арт ты долбаеб
                print("Иди нахцй дурень ошибка авторизации")
                break
            else:
                print("Авторизовалось прикинь")
                await load_plugins(writer)
            with patch_stdout():
                monitor_task = asyncio.create_task(monitor(reader, writer))
                command_tash = asyncio.create_task(mainCommand(writer))
            await asyncio.gather(monitor_task)

        except ConnectionRefusedError:
            print("--- Ошибка: Подключение отклонено. Проверьте хост/порт. ---")
        except asyncio.TimeoutError:
            print("--- Ошибка: Тайм-аут при подключении. ---")
        except Exception as e:
            print(f"--- Фатальная ошибка: {e}. Переподключение через 5 секунд... ---")
        finally:
            await asyncio.sleep(5)

async def mainCommand(writer):
    """
    спасибо им он помог написать это гавно мне лень
    """
    
    while True:
        try:
            line = await session.prompt_async("cmd> ")
            line = line.strip()
            
            if not line:
                continue
                
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd == "exit":
                print("Выход...")
                writer.close()
                await writer.wait_closed()
                os._exit(0)
            elif cmd == "microblog":
                if args:
                    text = args[0] if len(args) == 1 else " ".join(args)
                    await MicroBlog(text, writer)
                else:
                    print("Текста нет!\n")
            elif cmd == "send":
                if len(args) >= 2:
                    email = args[0]
                    msg = args[1] 
                    if len(args) > 2:
                        msg = " ".join(args[1:])
                    
                    if msg and msg[0] in ('"', "'") and msg[-1] == msg[0]:
                        msg = msg[1:-1]
                    await send_message(email, msg, writer)
                else:
                    print("Емаил то введи\n")
            elif cmd == "accept":
                if args:
                    await accept(args[0], writer)
                else:
                    print("Емаил то введи\n")
            elif cmd=="status":
            	if args:
            		try:
            			await changeStatus(int(args[0]), writer)
            		except ValueError:
            			print("Ошибка преобразования в число!")
            	else:
            		print("Нет номера статуса!")
            elif cmd=="alarm":
            	if args:
            		await alarm(args[0], writer)
            	else:
            		print("Нет почты!!")
            elif cmd in plugin_commands:
            	try:
            		func = plugin_commands[cmd]
            		if asyncio.iscoroutinefunction(func):
            			asyncio.create_task(func(plugin_interface, args))
            		else:
            			loop = asyncio.get_event_loop()
            			loop.run_in_executor(None, func, plugin_interface, args)
            	except Exception as e:
            		print(f"Error executing plugin: {e}")

            elif cmd == "modules":
            	print(f"Список комманд из модулей: {plugin_commands}")
            elif cmd == "help":
                print('Список доступных команд:\n1. help\n2. microblog <text>\n3. send <email> "Text"\n4. accept <email>\n5. status <status number> - Смена статуса(надо указать номер статуса в протоколе Mail.Ru Agent)\n6. alarm <email> - отправляет будильник\n7. modules - список комманд из модулей 8. exit')
            else:
                print(f"Неизвестно: {cmd}\n")
        except Exception as e:
            print(f"Ошибка в mainCommand: {e}")
            break
    return True
async def send_message(target, msg, writer):
	to = await create_lps(target)
	rtf_message = await create_lps("") # ртф соо нахуй
	msg2 = msg.encode('windows-1251')
	message = await create_lps(msg)
	flags = await create_ul(0)
	size = len(flags + message + to + rtf_message)
	packetMsg = await build_header(magic, proto, sequence, MRIM_CS_MESSAGE, size) + flags + to + message + rtf_message
	writer.write(packetMsg)
	await writer.drain()
async def MicroBlog(mblog, writer):
	flags = await create_ul(1)
	rukoblud = mblog.encode('utf-16-le')
	text = await create_lps(rukoblud)
	MRIM_BLOG = 0x1064
	size = len(flags + text)
	packetMBlog = await build_header(magic, proto, sequence, MRIM_BLOG, size) + flags + text
	writer.write(packetMBlog)
	await writer.drain()
async def accept(email, writer):
                        AcceptMail = await create_lps(email)
                        size = len(AcceptMail)

                        packetAuth = await build_header(magic, proto, sequence, MRIM_CS_AUTHORIZE, size) + AcceptMail
                        writer.write(packetAuth)
                        await writer.drain()
            
                        print("Отправил команду MRIM_CS_AUTHORIZE")
async def changeStatus(status, writer):
    status = await create_ul(status)
    size = len(status)
    packetStatus = await build_header(magic, proto, sequence, MRIM_CS_CHANGE_STATUS, size) + status
    writer.write(packetStatus)
    await writer.drain()
async def alarm(target, writer):
	flags = await create_ul(16512)
	to = await create_lps(target)
	message = await create_lps(" ")
	rtf_message = await create_lps("")
	size = len(flags + to + message + rtf_message)
	packetAlarm = await build_header(magic, proto, sequence, MRIM_CS_MESSAGE, size) + flags + to + message + rtf_message
	writer.write(packetAlarm)
	await writer.drain()

if __name__ == "__main__":
    asyncio.run(hi())
