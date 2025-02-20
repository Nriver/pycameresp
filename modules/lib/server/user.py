# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Class used to manage a username and a password """
from tools import logger,jsonconfig,encryption,strings,info

EMPTY_PASSWORD = b"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # empty password

class UserConfig(jsonconfig.JsonConfig):
	""" User configuration """
	def __init__(self):
		""" Constructor """
		jsonconfig.JsonConfig.__init__(self)
		self.user = b""
		self.password = EMPTY_PASSWORD
		if self.load() is False:
			self.save()

class User:
	""" Singleton class to manage the user. Only one user can be defined """
	instance = None
	login_state = [None]

	@staticmethod
	def init():
		""" Constructor """
		if User.instance is None:
			User.instance = UserConfig()

	@staticmethod
	def get_login_state():
		""" Indicates if login success or failed detected """
		result = User.login_state[0]
		User.login_state[0] = None
		return result

	@staticmethod
	def check(user, password, log=True, display=True):
		""" Check the user and password """
		User.init()
		user = user.lower()

		if User.instance.user == b"":
			info.set_last_activity()
			return True
		elif user == User.instance.user:
			if encryption.gethash(password) == User.instance.password:
				info.set_last_activity()
				if log is True:
					User.login_state[0] = True
				return True
			else:
				if log is True:
					User.login_state[0] = False
					logger.syslog("Login failed, wrong password for user '%s'"%strings.tostrings(user), display=display)
		else:
			if user != b"":
				if log is True:
					User.login_state[0] = False
					logger.syslog("Login failed, unkwnon user '%s'"%strings.tostrings(user), display=display)
		return False

	@staticmethod
	def is_empty():
		""" If no user defined """
		User.init()
		if User.instance.user == b"":
			return True
		else:
			return False

	@staticmethod
	def get_user():
		""" Get the user """
		User.init()
		return User.instance.user

	@staticmethod
	def change(user, current_password, new_password, renew_password):
		""" Change the user and password, check if the password is correct before to do this """
		User.init()
		user = user.lower()

		if User.check(user, current_password):
			if new_password == renew_password:
				if new_password == b"":
					User.instance.user     = b""
					User.instance.password = EMPTY_PASSWORD
				else:
					User.instance.user     = user
					User.instance.password = encryption.gethash(new_password)
				User.instance.save()
				return True
			else:
				return None
		return False
