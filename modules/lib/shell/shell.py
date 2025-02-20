# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Class defining a minimalist shell, directly executable on the board.
We modify directories, list, delete, move files, edit files ...
The commands are :
- cd          : change directory
- pwd         : current directory
- cat         : display the content of file
- cls         : clear screen
- mkdir       : create directory
- mv          : move file
- rmdir       : remove directory
- cp          : copy file
- rm          : remove file
- ls          : list file
- ll          : list file long
- date        : get the system date or synchronize with Ntp
- setdate     : set date and time
- uptime      : the amount of time system is running
- find        : find a file
- run         : execute python script
- download    : transfer files from device to computer (only available with camflasher)
- upload      : transfer files from computer to device (only available with camflasher)
- edit        : edit a text file
- exit        : exit of shell
- gc          : garbage collection
- grep        : grep text in many files
- mount       : mount sd card
- umount      : umount sd card
- temperature : device temperature
- meminfo     : memory informations
- flashinfo   : flash informations
- sysinfo     : system informations
- deepsleep   : deepsleep of board
- ping        : ping host
- reboot      : reboot board
- help        : list all command available
- man         : manual of one command
- df          : display free disk space
- ip2host     : convert ip address in hostname
- host2ip     : convert hostname in ip address
- eval        : evaluation python string
- exec        : execute python string
- dump        : display hexadecimal dump of the content of file
"""
# pylint:disable=wrong-import-position
import sys
sys.path.append("lib")
sys.path.append("simul")
import io
import os
import uos
import machine
from tools import useful,logger,sdcard,filesystem,exchange,info,strings,terminal,watchdog

stdout_redirected = None

def print_(message, end=None):
	""" Redirect the print to file """
	global stdout_redirected
	if stdout_redirected is None:
		if end is None:
			print(message)
		else:
			print(message, end=end)
	else:
		stdout_redirected.write(message)
		if end is None:
			stdout_redirected.write("\n")
		else:
			stdout_redirected.write(end)

def get_screen_size():
	""" Return the screen size and check if output redirected """
	global stdout_redirected
	if stdout_redirected is None:
		height, width = terminal.get_screen_size()
	else:
		height, width = terminal.MAXINT, 80
	return height, width

def cd(directory = "/"):
	""" Change directory """
	try:
		uos.chdir(filesystem.normpath(directory))
	except:
		if directory != ".":
			print_("No such file or directory '%s'"%directory)

def pwd():
	""" Display the current directory """
	print_("%s"%uos.getcwd())

def mkdir(directory, recursive=False, quiet=False):
	""" Make directory """
	try:
		if quiet is False:
			print_("mkdir '%s'"%directory)
		filesystem.makedir(filesystem.normpath(directory), recursive)
	except:
		print_("Cannot mkdir '%s'"%directory)

def removedir(directory, force=False, quiet=False, simulate=False, ignore_error=False):
	""" Remove directory """
	try:
		if filesystem.exists(directory+"/.DS_Store"):
			rmfile(directory+"/.DS_Store", quiet, force, simulate)
		if (filesystem.ismicropython() or force) and simulate is False:
			uos.rmdir(directory)
		if quiet is False:
			print_("rmdir '%s'"%(directory))
	except:
		if ignore_error is False:
			print_("rmdir '%s' not removed"%(directory))

def rmdir(directory, recursive=False, force=False, quiet=False, simulate=False, ignore_error=False):
	""" Remove directory """
	directory = filesystem.normpath(directory)
	if recursive is False:
		removedir(directory, force=force, quiet=quiet, simulate=simulate, ignore_error=ignore_error)
	else:
		directories = [directory]
		d = directory
		while 1:
			parts = filesystem.split(d)
			if parts[1] == "" or parts[0] == "":
				break
			directories.append(parts[0])
			d = parts[0]
		if "/" in directories:
			directories.remove("/")
		if sdcard.SdCard.get_mountpoint() in directories:
			directories.remove(sdcard.SdCard.get_mountpoint())
		for d in directories:
			if filesystem.exists(d) and d != ".":
				removedir(d, force=force, quiet=quiet, simulate=simulate, ignore_error=ignore_error)

def mv(source, destination):
	""" Move or rename file """
	try:
		uos.rename(filesystem.normpath(source),filesystem.normpath(destination))
	except:
		print_("Cannot mv '%s'->'%s'"%(source,destination))

def copyfile(src,dst,quiet):
	""" Copy file """
	dst = dst.replace("//","/")
	dst = dst.replace("//","/")
	dstdir, dstfile = filesystem.split(dst)
	try:
		if not filesystem.exists(dstdir):
			if dstdir != "." and dstdir != "":
				mkdir(dstdir, recursive=True, quiet=quiet)
		src_file = open(src, 'rb')
		dst_file = open(dst, 'wb')
		if quiet is False:
			print_("cp '%s' -> '%s'"%(src,dst))
		while True:
			buf = src_file.read(256)
			if len(buf) > 0:
				dst_file.write(buf)
			if len(buf) < 256:
				break
		src_file.close()
		dst_file.close()
	except:
		print_("Cannot cp '%s' -> '%s'"%(src, dst))

def cp(source, destination, recursive=False, quiet=False):
	""" Copy file command """
	source = filesystem.normpath(source)
	destination = filesystem.normpath(destination)
	if filesystem.isfile(source):
		copyfile(source,destination,quiet)
	else:
		if filesystem.isdir(source):
			path = source
			pattern = "*"
		else:
			path, pattern = filesystem.split(source)

		_, filenames = filesystem.scandir(path, pattern, recursive)

		for src in filenames:
			dst = destination + "/" + src[len(path):]
			copyfile(src,dst,quiet)

def rmfile(filename, quiet=False, force=False, simulate=False):
	""" Remove file """
	try:
		if (filesystem.ismicropython() or force) and simulate is False:
			uos.remove(filesystem.normpath(filename))
		if quiet is False:
			print_("rm '%s'"%(filename))
	except:
		print_("rm '%s' not removed"%(filename))

def rm(file, recursive=False, quiet=False, force=False, simulate=False):
	""" Remove file command """
	file = filesystem.normpath(file)
	filenames   = []
	directories = []

	if filesystem.isfile(file):
		path = file
		rmfile(file, force=force, quiet=quiet, simulate=simulate)
	else:
		if filesystem.isdir(file):
			if recursive:
				directories.append(file)
				path = file
				pattern = "*"
			else:
				path = None
				pattern = None
		else:
			path, pattern = filesystem.split(file)

		if path is None:
			print_("Cannot rm '%s'"%file)
		else:
			dirs, filenames = filesystem.scandir(path, pattern, recursive)
			directories += dirs

			for filename in filenames:
				rmfile(filename, force=force, quiet=quiet, simulate=simulate)

			if recursive:
				directories.sort()
				directories.reverse()

				for directory in directories:
					rmdir(directory, recursive=recursive, force=force, quiet=quiet, simulate=simulate, ignore_error=True)

class LsDisplayer:
	""" Ls displayer class """
	def __init__(self, path, showdir, long):
		""" Constructor """
		self.height, self.width = get_screen_size()
		self.count = 1
		self.long = long
		self.path = path
		self.showdir = showdir

	def purge_path(self, path):
		""" Purge the path for the display """
		path = path.encode("utf8")
		path = filesystem.normpath(path)
		prefix = filesystem.prefix([path, self.path.encode("utf8")])
		return path[len(prefix):].lstrip(b"/")

	def show(self, path):
		""" Show the information of a file or directory """
		fileinfo = filesystem.fileinfo(path)
		date_ = fileinfo[8]
		size = fileinfo[6]

		# If directory
		if fileinfo[0] & 0x4000 == 0x4000:
			if self.showdir:
				if self.long:
					message = b"%s %s [%s]"%(strings.date_to_bytes(date_),b" "*7,self.purge_path(path))
				else:
					message = b"[%s]"%self.purge_path(path)
				self.count = print_part(message, self.width, self.height, self.count)
		else:
			if self.long:
				fileinfo = filesystem.fileinfo(path)
				date_ = fileinfo[8]
				size = fileinfo[6]
				message = b"%s %s %s"%(strings.date_to_bytes(date_),strings.size_to_bytes(size),self.purge_path(path))
			else:
				message = self.purge_path(path)
			self.count = print_part(message, self.width, self.height, self.count)

	def show_dir(self, state):
		""" Indicates if the directory must show """
		self.showdir = state

def ls(file="", recursive=False, long=False):
	""" List files command """
	searchfile(file, recursive, LsDisplayer(uos.getcwd(), True, long))

def ll(file="", recursive=False):
	""" List files long command """
	searchfile(file, recursive, LsDisplayer(uos.getcwd(), True, True))

def searchfile(file, recursive, obj = None):
	""" Search file """
	file = filesystem.normpath(file)
	p = filesystem.abspath(uos.getcwd(), file)
	filenames = []
	try:
		if file == "":
			_,filenames = filesystem.scandir(uos.getcwd(), "*", recursive, obj)
		elif filesystem.isfile(p):
			if obj is not None:
				obj.show_dir(False)
				obj.show(p)
			filenames = [p]
		elif filesystem.isdir(p):
			_, filenames = filesystem.scandir(p, "*", recursive, obj)
		else:
			path, pattern = filesystem.split(p)
			if obj is not None:
				obj.show_dir(False)
			_, filenames = filesystem.scandir(path, pattern, recursive, obj)
	except Exception as err:
		print_(err)
	if len(filenames) == 0 and file != "" and file != ".":
		print_("%s : No such file or directory"%file)
	return filenames

def find(file):
	""" Find a file in directories """
	filenames = searchfile(file, True)
	for filename in filenames:
		print_(filename)

def print_part(message, width, height, count):
	""" Print a part of text """
	global stdout_redirected
	if isinstance(message , bytes):
		message = message.decode("utf8")
	if count is not None and count >= height:
		print_(message,end="")
		if stdout_redirected is None:
			key = terminal.getch()
		else:
			key = " "
		count = 1
		if key in ["x","X","q","Q","\x1B"]:
			return None
		print_("\n", end="")
	else:
		if count is None:
			count = 1
		else:
			count += 1
		print_(message)
	return count

def grep(file, text, recursive=False, ignorecase=False, regexp=False):
	""" Grep command """
	from re import search
	file = filesystem.normpath(file)
	def __search(text, content, ignorecase, regexp):
		if ignorecase:
			content  = content.lower()
			text = text.lower()
		if regexp:
			if search(text, content):
				return True
		else:
			if content.find(text) != -1:
				return True
		return False

	def __grep(text, filename, ignorecase, regexp, width, height, count):
		lineNumber = 1
		with open(filename,"r", encoding="latin-1") as f:
			while 1:
				line = f.readline()
				if line:
					if __search(text, line, ignorecase, regexp):
						line = line.replace("\t","    ")
						message = "%s:%d:%s"%(filename, lineNumber, line)
						message = message.rstrip()[:width]
						count = print_part(message, width, height, count)
						if count is None:
							print_("")
							return None
					lineNumber += 1
				else:
					break
		return count

	if filesystem.isfile(file):
		filenames = [file]
	else:
		path, pattern = filesystem.split(file)
		_, filenames = filesystem.scandir(path, pattern, recursive)

	height, width = get_screen_size()
	count = 1
	for filename in filenames:
		count = __grep(text, filename, ignorecase, regexp, width, height, count)
		if count is None:
			break

def ping(host):
	""" Ping host """
	try:
		from server.ping import ping as ping_
		ping_(host, count=4, timeout=1)
	except:
		print_("Not available")

def ip2host(ip_address):
	""" Convert ip to hostname """
	try:
		import wifi
		_, _, _, dns = wifi.Station.get_info()
		from server.dnsclient import resolve_hostname
		print_(resolve_hostname(dns, ip_address))
	except:
		print_("Not available")

def host2ip(hostname):
	""" Convert hostname to ip """
	try:
		import wifi
		_, _, _, dns = wifi.Station.get_info()
		from server.dnsclient import resolve_ip_address
		print_(resolve_ip_address(dns, hostname))
	except:
		print_("Not available")

def mountsd(mountpoint="/sd"):
	""" Mount command """
	try:
		sdcard.SdCard.mount(mountpoint)
		print_("Sd mounted on '%s'"%mountpoint)
	except:
		print_("Cannot mount sd on '%s'"%mountpoint)

def umountsd(mountpoint="/sd"):
	""" Umount command """
	try:
		sdcard.SdCard.umount(mountpoint)
		print_("Sd umounted from '%s'"%mountpoint)
	except:
		print_("Cannot umount sd from '%s'"%mountpoint)

def date(update=False, offsetUTC=+1, noDst=False):
	""" Get or set date """
	try:
		from server.timesetting import set_date
		if update:
			if noDst:
				dst = False
			else:
				dst = True
			set_date(offsetUTC, dst)
		del sys.modules["server.timesetting"]
	except:
		pass
	print_(strings.date_to_string())

def setdate(datetime=""):
	""" Set date and time """
	import re
	date_=re.compile("[/: ]")
	failed = False
	try:
		spls = date_.split(datetime)

		lst = []
		if len(spls) > 1:
			for spl in spls:
				if len(spl) > 0:
					try:
						r = spl.lstrip("0")
						if len(r) == 0:
							lst.append(0)
						else:
							lst.append(eval(r))
					except:
						failed = True
						break
			if len(lst) == 6:
				# pylint: disable=unbalanced-tuple-unpacking
				year,month,day,hour,minute,second = lst
				machine.RTC().datetime((year, month, day, 0, hour, minute, second, 0))
			else:
				failed = True
		else:
			failed = True
	except Exception as err:
		failed = True
		logger.syslog(err)

	if failed is True:
		print_('Expected format "YYYY/MM/DD hh:mm:ss"')

def formatsd(fstype="FAT"):
	""" Format sd card """
	if fstype in ["FAT","LFS"]:
		if sdcard.SdCard.is_mounted() is False:
			res = input("All data will be lost on Sd card ? proceed with format (y/n) :")
			if res in ["y","Y"]:
				if sdcard.SdCard.formatsd() is True:
					print_("Formatting terminated")
				else:
					print_("Formatting failed")
		else:
			print_("Sd card is mounted, a reboot required")
	else:
		print_("Filesystem supported : FAT or LFS")

def reboot():
	""" Reboot command """
	try:
		from tools import system
		system.reboot("Reboot device with command")
	except:
		machine.deepsleep(1000)

def deepsleep(seconds=60):
	""" Deep sleep command """
	machine.deepsleep(int(seconds)*1000)

edit_class = None
def edit(file, no_color=False, read_only=False):
	""" Edit command """
	global edit_class
	global stdout_redirected
	if stdout_redirected is None:
		if edit_class is None:
			try:
				from shell.editor import Editor
			except:
				from editor import Editor
			edit_class = Editor
		edit_class(file, no_color=no_color, read_only=read_only)

def cat(file):
	""" Cat command """
	try:
		f = open(file, "r")
		height, width = get_screen_size()
		count = 1
		while 1:
			line = f.readline()
			if not line:
				break
			message = line.replace("\t","    ").rstrip()[:width]
			count = print_part(message, width, height, count)
			if count is None:
				break
		f.close()
	except:
		print_("Cannot cat '%s'"%(file))

def df(mountpoint = None):
	""" Display free disk space """
	print_(strings.tostrings(info.flashinfo(mountpoint=mountpoint, display=False)))

def gc():
	""" Garbage collector command """
	from gc import collect
	collect()

def uptime():
	""" Tell how long the system has been running """
	print_(info.uptime())

def man(command):
	""" Man command """
	print_(man_one(command))

def man_one(command_name):
	""" Manual of one command """
	try:
		command_name, command_function, command_params, command_flags = get_command(command_name)
		text = "  " + command_name + " "
		for param in command_params:
			text += param + " "
		text += "\n"
		for flag,flagName,val in command_flags:
			text += "    %s : %s\n"%(flag,flagName)
		result = text[:-1]
	except:
		result = "Unknown command '%s'"%command_name
	return result

# pylint: disable=redefined-builtin
def help():
	""" Help command """
	height, width = get_screen_size()
	count = 1
	cmds = list(shell_commands.keys())
	cmds.sort()
	for command in cmds:
		lines = man_one(command)
		lines = "-"*30+"\n" + lines
		for line in lines.split("\n"):
			count = print_part(line, width, height, count)
			if count is None:
				return

def eval_(string):
	""" Evaluate content of string """
	print_(eval(string))

def exec_(string):
	""" Execute content of string """
	exec(string)

shell_exited = False
def exit():
	""" Exit shell command """
	global shell_exited
	shell_exited = True

def dump_(filename):
	""" dump file content """
	height, width = get_screen_size()
	if stdout_redirected is None:
		width = (width - 12)//4
	else:
		width = 16
	offset = 0
	file = open(filename, "rb")
	data = b' '
	count = 1
	while True:
		line = io.BytesIO()
		line.write(b'%08X  ' % offset)
		data = file.read(width)
		if len(data) <= 0:
			break
		strings.dump_line (data, line, width)
		offset += width
		count = print_part(line.getvalue(), width, height, count)
		if count is None:
			break

def cls():
	""" clear screen """
	print_("\x1B[2J\x1B[0;0f", end="")

def check_cam_flasher():
	""" Check if the terminal is CamFlasher """
	global stdout_redirected
	if stdout_redirected is None:
		# Request terminal device attribut
		sys.stdout.write(b"\x1B[0c")

		# Wait terminal device attribut response
		response = terminal.getch(duration=1000)

		# If CamFlasher detected
		if response == "\x1B[?3;2c":
			return True
	return False

def upload(file="", recursive=False):
	""" Upload file from computer to device """
	if check_cam_flasher():
		print_("Upload to device start")
		try:
			command = exchange.UploadCommand(uos.getcwd())
			command.write(file, recursive, sys.stdin.buffer, sys.stdout.buffer)
			result = True
			while result:
				file_reader = exchange.FileReader()
				result = file_reader.read(uos.getcwd(), sys.stdin.buffer, sys.stdout.buffer)
				watchdog.WatchDog.feed()
			print_("Upload end")
		except Exception as err:
			logger.syslog(err, display=False)
			print_("Upload failed")
	else:
		print_("CamFlasher application required for this command")

class Exporter:
	""" Exporter file to camflasher """
	def __init__(self):
		""" Constructor """

	def send_file(self, path):
		""" Send the file """
		result = True
		fileinfo = filesystem.fileinfo(path)

		# If a file
		if fileinfo[0] & 0x4000 != 0x4000:
			file_write = exchange.FileWriter()
			if filesystem.exists(path):
				sys.stdout.buffer.write("࿊".encode("utf8"))
				result = file_write.write(path, sys.stdin.buffer, sys.stdout.buffer)
				watchdog.WatchDog.feed()
		return result

	def show(self, path):
		""" Show the information of a file or directory """
		for _ in range(3):
			# If the send successful exit, else retry three time
			if self.send_file(path) is True:
				break

	def show_dir(self, state):
		""" Indicates if the directory must show """

def download(file="", recursive=False):
	""" Download file from device to computer """
	if check_cam_flasher():
		print_("Download from device start")
		try:
			searchfile(file, recursive, Exporter())
			print_ ("Download end")
		except Exception as err:
			logger.syslog(err, display=False)
			print_("Download failed")
	else:
		print_("CamFlasher application required for this command")

def temperature():
	""" Get the internal temperature """
	celcius, farenheit = info.temperature()
	print_("%.2f°C, %d°F"%(celcius, farenheit))

def meminfo():
	""" Get memory informations """
	print_(strings.tostrings(info.meminfo(display=False)))

def flashinfo(mountpoint=None):
	""" Get flash informations """
	print_(strings.tostrings(info.flashinfo(mountpoint=mountpoint, display=False)))

def sysinfo():
	""" Get system informations """
	print_(strings.tostrings(info.sysinfo(display=False)))

def vtcolors():
	""" Show all VT100 colors """
	res = b'\x1B[4m4 bits colors\x1B[m\n'
	for i in range(16):
		if i % 8 == 0:
			res += b"\n  "
		if i < 9:
			forecolor = 15
		else:
			forecolor = 0
		res += b"\x1B[38;5;%dm\x1B[48;5;%dm %2d \x1B[0m"%(forecolor, i,i)
	res += b'\n\n\x1B[4m8 bits colors\x1B[m\n'
	j = 0
	for i in range(16,256):
		if j % 12== 0:
			res += b"\n  "
		backcolor = i
		if j % 36 < 36//2:
			forecolor = 15
		else:
			forecolor = 0
		res += b"\x1B[38;5;%dm\x1B[48;5;%dm %3d \x1B[0m"%(forecolor,backcolor,i)
		j += 1
	res += b'\n\n\x1B[4mModifiers\x1B[m\n\n'

	for i,j in [(0,"reset/normal"),(1,b"bold"),(3,b"italic"),(4,b"underline"),(7,b"reverse")]:
		res += b"  %d : \x1B[%dm%s\x1B[0m\n"%(i,i,j)
	res += b'\n\x1B[4mExamples\x1B[m\n\n'
	res += b'  >>> print("\\033[\033[1m1\033[m;\033[7m7\033[mmBold reverse\\033[0m")\n'
	res += b"  \033[1;7mBold reverse\033[0m"
	res += b"\n\n"
	res += b'  >>> print("\033[38;5;15m\033[48;5;1m\\033[48;5;1m\033[m\033[38;5;13m\\033[38;5;13m\033[mHello\\033[m")\n'
	res += b"  \033[48;5;1m\033[38;5;13mHello\033[m\n"

	print_(res.decode("utf8"))

def get_command(command_name):
	""" Get a command callback according to the command name """
	try:
		global shell_commands
		command = shell_commands[command_name]
		command_function = command[0]
		command_params = []
		command_flags  = []
		for item in command[1:]:
			if type(item) == type(""):
				command_params.append(item)
			if type(item) == type((0,)):
				command_flags.append(item)
	except  Exception as err:
		# pylint: disable=raise-missing-from
		raise Exception("Command not found '%s'"%command_name)
	return command_name, command_function, command_params, command_flags

def exec_command(args):
	""" Execute command """
	global stdout_redirected
	command_name = ""
	command_function = None
	command_params = []
	command_flags = []
	output_redirection = None
	output_filename = None
	try:
		if len(args) >= 1:
			paramsCount = 0
			flags   = {}
			for arg in args:
				arg = arg.strip()
				if len(arg) > 0:
					if command_name == "":
						command_name, command_function, command_params, command_flags = get_command(arg)
					else:
						if len(arg) >= 2 and arg[:2] == "--":
							for commandFlag in command_flags:
								if arg.strip()[2:] == commandFlag[1].strip():
									flags[commandFlag[1]] = commandFlag[2]
									break
							else:
								raise Exception("Illegal option '%s' for"%arg)
						elif arg[0] == "-":
							for commandFlag in command_flags:
								if arg.strip() == commandFlag[0].strip():
									flags[commandFlag[1]] = commandFlag[2]
									break
							else:
								raise Exception("Illegal option '%s' for"%arg)
						elif arg[0] == ">":
							output_redirection = True
						else:
							if output_redirection is None:
								if paramsCount >= len(command_params):
									raise Exception("Too many parameters for")
								else:
									flags[command_params[paramsCount]] = arg
									paramsCount += 1
							elif output_redirection is True:
								output_filename = arg

	except Exception as err:
		# print_(logger.syslog(err))
		print_(err)
		return
	stdout_redirected = None
	try:
		if command_name.strip() != "":
			if output_filename is not None:
				try:
					stdout_redirected = open(output_filename, "w")
				except:
					pass
			command_function(**flags)
	except TypeError as err:
		logger.syslog(err, display=False)
		print_("Missing parameters for '%s'"%command_name)
	except KeyboardInterrupt as err:
		logger.syslog(err)
		print_(" [Canceled]")
	except Exception as err:
		logger.syslog(err)
	finally:
		if stdout_redirected is not None:
			stdout_redirected.close()
		stdout_redirected = None

def parse_command_line(commandLine):
	""" Parse command line """
	commands = []
	args = []
	quote = None
	arg = ""
	for char in commandLine:
		if char == '"' or char == "'":
			if quote is not None:
				if quote == char:
					args.append(arg)
					arg = ""
					quote = None
				else:
					arg += char
			else:
				quote = char
		elif char == " ":
			if quote is not None:
				arg += char
			else:
				args.append(arg)
				arg = ""
		elif char == ";":
			if quote is not None:
				arg += char
			else:
				if len(arg) > 0:
					args.append(arg)
				commands.append(args)
				arg = ""
				args = []
		else:
			arg += char
	if len(arg) > 0:
		args.append(arg)
	if len(args) > 0:
		commands.append(args)

	for command in commands:
		exec_command(command)

def sh(path=None, throw=False):
	""" Start the shell """
	global shell_exited

	if path is not None:
		uos.chdir(path)

	shell_exited = False
	while shell_exited is False:
		try:
			commandLine = ""
			commandLine = input("%s=> "%os.getcwd())
			watchdog.WatchDog.feed()
		except EOFError:
			print_("")
			break
		except KeyboardInterrupt:
			print_("Ctr-C detected, use 'exit' to restart server or 'quit' to get python prompt")

		if commandLine.strip() == "quit":
			if throw is True:
				raise KeyboardInterrupt()
			else:
				break
		parse_command_line(commandLine)

async def async_shell():
	""" Asynchronous shell """
	import uasyncio
	try:
		from server.server import Server
	except:
		Server = None

	print_("\nPress key to start shell")
	if filesystem.ismicropython():
		polling1 = 2
		polling2 = 0.01
	else:
		polling1 = 0.1
		polling2 = 0.5
	while 1:
		# If key pressed
		if terminal.kbhit(polling2):
			character = terminal.getch()[0]

			# Check if character is correct to start shell
			if not ord(character) in [0,0xA]:
				# Ask to suspend server during shell
				if Server is not None:
					Server.suspend()

					# Wait all server suspended
					await Server.wait_all_suspended()

				# Extend watch dog duration
				watchdog.WatchDog.start(watchdog.LONG_WATCH_DOG*2)

				# Get the size of screen
				terminal.refresh_screen_size()

				# Start shell
				print("")
				logger.syslog("<"*10+" Enter shell " +">"*10)
				print("Use 'exit' to restart server or 'quit' to get python prompt")
				sh(throw=True)
				print("")
				logger.syslog("<"*10+" Exit  shell " +">"*10)

				# Restore default path
				uos.chdir("/")

				# Resume watch dog duration
				watchdog.WatchDog.start(watchdog.SHORT_WATCH_DOG)

				# Resume server
				if Server is not None:
					Server.resume()
		else:
			await uasyncio.sleep(polling1)

shell_commands = \
{
	"cd"         :[cd              ,"directory"            ],
	"pwd"        :[pwd                                     ],
	"cat"        :[cat             ,"file"                 ],
	"cls"        :[cls                                     ],
	"mkdir"      :[mkdir           ,"directory",             ("-r","recursive",True)],
	"mv"         :[mv              ,"source","destination" ],
	"rmdir"      :[rmdir           ,"directory",             ("-r","recursive",True),("-f","force",True),("-q","quiet",True),("-s","simulate",True)],
	"cp"         :[cp              ,"source","destination",  ("-r","recursive",True),("-q","quiet",True)],
	"rm"         :[rm              ,"file",                  ("-r","recursive",True),("-f","force",True),("-s","simulate",True)],
	"ls"         :[ls              ,"file",                  ("-r","recursive",True),("-l","long",True)],
	"ll"         :[ll              ,"file",                  ("-r","recursive",True)],
	"date"       :[date            ,"offsetUTC" ,            ("-u","update",True),   ("-n","noDst",True)],
	"setdate"    :[setdate         ,"datetime"             ],
	"uptime"     :[uptime                                  ],
	"find"       :[find            ,"file"                 ],
	"run"        :[useful.run      ,"filename"             ],
	"download"   :[download        ,"file",                  ("-r","recursive",True)],
	"upload"     :[upload          ,"file",                  ("-r","recursive",True)],
	"edit"       :[edit            ,"file",                  ("-n","no_color",True),("-r","read_only",True)],
	"exit"       :[exit                                    ],
	"gc"         :[gc                                      ],
	"grep"       :[grep            ,"text","file",           ("-r","recursive",True),("-i","ignorecase",True),("-e","regexp",True)],
	"mount"      :[mountsd         ,"mountpoint"           ],
	"umount"     :[umountsd        ,"mountpoint"           ],
	"temperature":[temperature                             ],
	"meminfo"    :[meminfo                                 ],
	"flashinfo"  :[flashinfo                               ],
	"sysinfo"    :[sysinfo                                 ],
	"deepsleep"  :[deepsleep       ,"seconds"              ],
	"ping"       :[ping            ,"host"                 ],
	"reboot"     :[reboot                                  ],
	"help"       :[help                                    ],
	"man"        :[man             ,"command"              ],
	"df"         :[df              ,"mountpoint"           ],
	"ip2host"    :[ip2host         ,"ip_address"           ],
	"host2ip"    :[host2ip         ,"hostname"             ],
	"eval"       :[eval_           ,"string"               ],
	"exec"       :[exec_           ,"string"               ],
	"dump"       :[dump_           ,"filename"             ],
	"formatsd"   :[formatsd        ,"fstype"               ],
	"vtcolors"   :[vtcolors                                ],
}

if __name__ == "__main__":
	sh(sys.argv[1])
