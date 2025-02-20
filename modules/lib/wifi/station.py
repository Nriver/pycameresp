# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Classes used to manage the wifi station """
import time
from wifi import ip, hostname
import uasyncio
from tools import jsonconfig,strings,logger

class NetworkConfig(jsonconfig.JsonConfig):
	""" Wifi station configuration class """
	def __init__(self):
		""" Constructor """
		jsonconfig.JsonConfig.__init__(self)
		self.wifi_password  = b""
		self.ssid          = b""
		self.ip_address     = b""
		self.netmask       = b""
		self.gateway       = b""
		self.dns           = b""
		self.dynamic       = True

	def __repr__(self):
		""" Display the content of wifi station """
		# Get network address
		ip_address, netmask, gateway, dns = Station.wlan.ifconfig()

		result = "%s:\n"%self.__class__.__name__
		result +="   Ip address :%s\n"%ip_address
		result +="   Netmask    :%s\n"%netmask
		result +="   Gateway    :%s\n"%gateway
		result +="   Dns        :%s\n"%dns
		result +="   Ssid       :%s\n"%strings.tostrings(self.ssid)
		# result +="   Password   :%s\n"%strings.tostrings(self.wifi_password)
		return result

	def save(self, file = None, part_filename=None):
		""" Save wifi configuration """
		result = jsonconfig.JsonConfig.save(self, file=file, part_filename=self.ssid)
		return result

	def list_known(self):
		""" List all configuration files """
		return jsonconfig.JsonConfig.list_all(self)

	def forget(self, part_filename=None):
		""" Forget configuration """
		return jsonconfig.JsonConfig.forget(self, part_filename=self.ssid)

class StationConfig(jsonconfig.JsonConfig):
	""" Wifi station configuration class """
	def __init__(self):
		""" Constructor """
		jsonconfig.JsonConfig.__init__(self)
		self.hostname      = b"esp%05d"%hostname.Hostname.get_number()
		self.activated     = True
		self.fallback      = True
		self.default       = b""

	def __repr__(self):
		""" Display the content of wifi station """
		# Get network address
		result = "%s:\n"%self.__class__.__name__
		result +="   Activated  :%s\n"%strings.tostrings(self.activated)
		result  ="   Hostname   :%s\n"%strings.tostrings(self.hostname)
		return result

class Station:
	""" Class to manage wifi station """
	wlan    = None
	config  = None
	network = None
	other_networks = []
	known_network = []
	last_scan = [0]

	@staticmethod
	def init():
		""" Initialize wlan object """
		if Station.wlan is None:
			from network import WLAN, STA_IF
			Station.wlan = WLAN(STA_IF)

	@staticmethod
	async def connect(network, max_retry=15):
		""" Connect to wifi hotspot """
		Station.init()
		result = False
		if not Station.wlan.isconnected():
			Station.wlan.active(True)
			Station.configure(network)
			Station.wlan.connect(strings.tobytes(network.ssid), strings.tobytes(network.wifi_password))
			retry = 0
			while not Station.wlan.isconnected() and retry < max_retry:
				await uasyncio.sleep(1)
				logger.syslog ("   %-2d/%d wait connection to %s"%(retry+1, max_retry, strings.tostrings(network.ssid)))
				retry += 1

			if Station.wlan.isconnected() is False:
				Station.wlan.active(False)
			else:
				result = True
		else:
			result = True
		return result

	@staticmethod
	def disconnect():
		""" Disconnect the wifi """
		Station.init()
		if Station.wlan.isconnected():
			Station.wlan.disconnect()
		if Station.wlan.active():
			Station.wlan.active(False)

	@staticmethod
	def is_active():
		""" Indicates if the wifi is active """
		if Station.wlan is None:
			return False
		return Station.wlan.active()

	@staticmethod
	def is_fallback():
		""" Indicates if the access point must be started when wifi not reachable """
		Station.reload_config()
		return Station.config.fallback

	@staticmethod
	def configure(network):
		""" Configure the wifi """
		Station.init()
		# If ip is dynamic
		if  network.dynamic   is True:
			if len(Station.get_hostname()) > 0:
				Station.wlan.config(dhcp_hostname= strings.tostrings(Station.get_hostname()))
		else:
			try:
				Station.wlan.ifconfig((strings.tostrings(network.ip_address),strings.tostrings(network.netmask),strings.tostrings(network.gateway),strings.tostrings(network.dns)))
			except Exception as err:
				logger.syslog(err, msg="Cannot configure wifi station")
		try:
			network.ip_address = strings.tobytes(Station.wlan.ifconfig()[0])
			network.netmask   = strings.tobytes(Station.wlan.ifconfig()[1])
			network.gateway   = strings.tobytes(Station.wlan.ifconfig()[2])
			network.dns       = strings.tobytes(Station.wlan.ifconfig()[3])
		except Exception as err:
			logger.syslog(err, msg="Cannot get ip station")

	@staticmethod
	def reload_config():
		""" Reload configuration if it changed """
		if Station.config is None:
			Station.config = StationConfig()
			Station.network = NetworkConfig()
			if Station.config.load() is False:
				Station.config.save()
				logger.syslog("Wifi not initialized")
		else:
			if Station.config.is_changed():
				Station.config.load()
		return Station.config

	@staticmethod
	def is_connected():
		""" Indicates if the wifi is connected """
		if Station.wlan:
			return Station.wlan.isconnected()
		return False

	@staticmethod
	def scan():
		""" Scan other networks """
		Station.init()
		if Station.last_scan[0] + 120 < time.time() or len(Station.other_networks) == 0:
			Station.other_networks = []
			Station.wlan.active(True)
			try:
				other_networks = Station.wlan.scan()
				for ssid, bssid, channel, rssi, authmode, hidden in sorted(other_networks, key=lambda x: x[3], reverse=True):
					logger.syslog("Network detected %s"%strings.tostrings(ssid))
					Station.other_networks.append((ssid, channel, authmode))
				Station.last_scan[0] = time.time()
			except Exception as err:
				logger.syslog("No network found")

		return Station.other_networks

	@staticmethod
	def is_activated():
		""" Indicates if the wifi station is configured to be activated """
		Station.reload_config()
		if Station.config is not None:
			return Station.config.activated
		else:
			return False

	@staticmethod
	async def select_network(network_name, max_retry):
		""" Select the network and try to connect """
		Station.reload_config()
		if network_name != b"":
			# Load default network
			if Station.network.load(part_filename=network_name):
				logger.syslog("Try to connect to %s"%strings.tostrings(Station.network.ssid))

				# If the connection failed
				if await Station.connect(Station.network, max_retry) is True:
					logger.syslog("Connected to %s"%strings.tostrings(Station.network.ssid))
					print(repr(Station.config) + repr(Station.network))
					Station.config.default = network_name
					Station.config.save()
					return True
		return False

	@staticmethod
	async def scan_networks(max_retry):
		""" Scan networks known """
		result = False
		networks = Station.scan()
		# Scan other networks
		if len(networks) > 0:
			# List known networks
			Station.known_network = Station.network.list_known()

			# If the defaut network not yet initialized
			if len(Station.config.default) == 0:
				# For all known networks
				for network_name in Station.known_network:
					# Search in detected networks
					for network in networks:
						# If the known network is found in detected network
						if network[0] == network_name:
							result = await Station.select_network(network_name, max_retry)
							if result is True:
								break

			# If wifi not yet found
			if result is False:
				# For all known networks
				for network_name in Station.known_network:
					# If the network not already tested
					if network_name != Station.config.default:
						result = await Station.select_network(network_name, max_retry)
						if result is True:
							break
		return result

	@staticmethod
	async def choose_network(force=False, max_retry=15):
		""" Choose network within reach """
		result = False
		Station.reload_config()

		# Load wifi configuration
		if Station.config.load():
			if Station.config.activated or force:
				result = await Station.select_network(Station.config.default, max_retry)
				if result is False:
					result = await Station.scan_networks(max_retry)
			else:
				logger.syslog("Wifi disabled")
		else:
			Station.config.save()
			logger.syslog("Wifi not initialized")
		return result

	@staticmethod
	async def start(force=False, max_retry=15):
		""" Start the wifi according to the configuration. Force is used to skip configuration activation flag """
		result = False
		Station.init()
		if Station.is_active() is False:
			logger.syslog("Start wifi")
			if await Station.choose_network(force, max_retry) is True:
				result = True
		else:
			if Station.wlan.isconnected():
				logger.syslog("Wifi already started")
				result = True
			else:
				logger.syslog("Wifi started but not connected")
		return result

	@staticmethod
	def stop():
		""" Stop the wifi station """
		if Station.wlan is not None:
			logger.syslog("Stop wifi")
			try:
				if Station.wlan.isconnected():
					Station.wlan.disconnect()
				if Station.wlan.active():
					Station.wlan.active(False)
			except:
				pass
			Station.wlan = None

	@staticmethod
	def is_ip_on_interface(ipAddr):
		""" Indicates if the address ip is connected to wifi station """
		ipInterface = Station.get_info()
		if ipInterface != ("","","",""):
			return ip.issameinterface(strings.tostrings(ipAddr), ipInterface[0], ipInterface[1])
		return False

	@staticmethod
	def get_info():
		""" Returns the connection informations """
		if Station.wlan:
			if Station.wlan.isconnected():
				return Station.wlan.ifconfig()
		return ("","","","")

	@staticmethod
	def get_hostname():
		""" Returns the host name """
		Station.reload_config()
		return Station.config.hostname
