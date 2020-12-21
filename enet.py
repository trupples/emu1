# from enet import ENET_INCOMING, ENET_RECV, ENET_SEND, ENET_CONN_CTRL, enet_server, enet_client
import time
from pwn import *

srv = None
conn = None
marked = None
queue = []

def ENET_INCOMING(_):
	global conn
	try:
		conn._fillbuffer(timeout = 0.001)
	except EOFError:
		conn.close()
	return min(63, len(conn.buffer))

def ENET_RECV(_):
	x = conn.recvn(1, timeout=0.001)
	if x == b'': return 63
	if x[0] not in range(63): x = bytes([0o63])
	return x[0]

def ENET_SEND(x):
	try:
		conn.send(bytes([x]))
	except EOFError:
		conn.close()
	return 0

def ENET_CONN_CTRL(o):
	global srv, conn, marked, queue

	#print(f"conn ctrl {o}")

	if o == 1:
		marked = queue[0]
		return 0
	elif o == 2:
		found = False

		while True:
			N = len(queue)
			for _ in range(N):
				queue = queue[1:] + queue[:1]
				if queue[0] == marked:
					found = True
				if queue[0].connected():
					conn = queue[0]
					return found
				else:
					print(f"Disconnected {queue[0].rhost}:{queue[0].rport}")
					queue = queue[1:]
			time.sleep(0.01)

def enet_server(addr):
	global srv, queue
	def cb(c):
		print(f"New connection: {c.rhost}:{c.rport}")
		queue.append(c)

	srv = server(int(addr), callback=cb, blocking=False)
	print(srv)

def enet_client(addr):
	global conn
	addr = addr.split(":")
	addr[1] = int(addr[1])
	conn = remote(addr[0], addr[1])
