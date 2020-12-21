from pwn import *

FLAG = "X-MAS{Y0U-$UR3-AS-H#LL-4REN'T!!1!!}"

emu_charset = list("0123456789abcdefghijklmnopqrstuvwxyz +-*/<=>()[]{}#$_?|^&!~,.:\n".upper()) + [""]
assert len(emu_charset) == 64
def ascii2emu(x):
	if x not in emu_charset: x = '#'
	return emu_charset.index(x)

def emu2ascii(x):
	return emu_charset[x]

queue = []

def cb(c):
	print(f"New connection: {c.rhost}:{c.rport}")
	queue.append(c)

srv = server(12345, callback=cb, blocking=False)

while True:
	if len(queue) == 0:
		time.sleep(0.01)
		continue
	queue = queue[1:] + queue[:1]
	try:
		queue[0]._fillbuffer(timeout = 0.01)
		if len(queue[0].buffer) >= 40:
			msg = ''.join(emu2ascii(q) for q in queue[0].recvn(40))
			msg = f"{msg[:4]}: {msg[4:]}\n"
			if msg == "YMAS: I MIGHT BE BETTER THAN X-MAS LOLOLOL\n":
				print(f"{queue[0].rhost}:{queue[0].rport} GOT A FLAG")
				queue[0].send(bytes([ascii2emu(c) for c in FLAG]))
			else:
				print(msg, end='')
				for conn in queue[1:]:
					try:
						conn.send(bytes([ascii2emu(c) for c in msg]))
					except EOFError:
						pass
	except EOFError:
		print(f"Disconnected {queue[0].rhost}:{queue[0].rport}")
		queue[0].close()
		queue = queue[1:]
