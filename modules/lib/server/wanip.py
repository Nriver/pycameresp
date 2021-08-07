import uasyncio
from server.stream import *
from server.httprequest import *
from tools import useful

async def request(host, port, path):
	""" Asynchronous request to ip server """
	reader,writer = await uasyncio.open_connection(useful.tostrings(host), port)
	streamio = Stream(reader, writer)
	req = HttpRequest(None)
	req.setPath(path)
	req.setHeader(b"HOST",b"ESP32")
	req.setMethod(b"GET")
	req.setHeader(b"User-Agent",b"ESP32")
	req.setHeader(b"Accept-Encoding",b"gzip, deflate")
	req.setHeader(b"Connection",b"keep-alive")
	await req.send(streamio)
	response = HttpResponse(streamio)
	await response.receive(streamio)
	result = None
	if response.status == b"200":
		result = response.getContent()
	writer.close()
	await writer.wait_closed()
	return result

async def getWanIpAsync():
	""" Get the wan ip address with asynchronous method """
	resp = await request("ip4only.me",80,b"/api/")
	if resp:
		spl = resp.split(b",")
		if len(spl) > 1:
			return spl[1].decode("utf-8")
	return None

