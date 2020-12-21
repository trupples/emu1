import sys
import subprocess
import time
import threading
import atexit

r = [0] * 64
c = None
running = True
rom_ptr = 0

def R(x): return f"r[{x}]"									# repr memory slot rx
def i(x): return f"0o{oct(x+64)[-2:]}" if x > 7 else str(x)	# repr immediate ix
def l(x): return f"0o{oct(x+4096)[-4:]}"					# repr label lx 

def go_down():
	global rom_ptr
	rom_ptr = (rom_ptr + 1) % len(rom)

def go_up():
	global rom_ptr
	rom_ptr = (rom_ptr - 1) % len(rom)

def jump_up(lab, rc):
	target = f"pass # jump target {l(lab)}, {i(rc)}"
	#print(target, c)
	while rom[rom_ptr][0] != target and rom[rom_ptr][0] != f"if c == {c}: {target}":
		go_up()
	#print("Found")
	go_up()

def jump_dn(lab, rc):
	target = f"pass # jump target {l(lab)}, {i(rc)}"
	#print(target, c)
	while rom[rom_ptr][0] != target and rom[rom_ptr][0] != f"if c == {c}: {target}":
		go_down()
	#print("Found")
	go_up()

def signed(x):
	if x >= 32:
		x -= 64
	return x

def rol(x, amnt):
	return ((x << amnt) | (x >> (6 - amnt)) & 63)

IPP = -4
# printf("%d: (%d: %o) %o %o %o\n", pc, condition, opc, d, a, b);
def pseudocode(b64):
	global IPP
	IPP += 4
	OPC, A, B, C = ["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".index(x) for x in b64]
	if OPC == 0:
		pseudocode = "print('Halting!'); running = False # OPC = 0"
		return (pseudocode, compile(pseudocode, "asm", "exec", optimize=1))
	condition, op = divmod(OPC - 1, 21)

	raw = f"({b64}) {' +-'[condition]} {i(op)} {i(A)} {i(B)} {i(C)}"

	indirect = f"r[({R(B)} + {i(C)}) & 63]".replace("(r[0] + ", "(").replace(" + 0)", ")").replace("(0) & 63", "0")

	if op in [0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12]:
		c = R(C) if op in [0, 2, 4, 6, 8, 11, 12] else i(C)
		o = {0: "+", 1: "+", 2: "-", 4: "|", 5: "|", 6: "^", 7: "^", 8: "&", 9: "&", 11: "<<", 12: ">>"}[op]
		pseudocode = f"{R(A)} = ({R(B)} {o} {c}) & 63"
	elif op == 3:
		a, b = None, None
		if (A >> 3) & 3 == 0:   a, b = R(B), R(C)
		elif (A >> 3) & 3 == 1: a, b = R(C), R(B)
		elif (A >> 3) & 3 == 2: a, b = R(B), i(C)
		elif (A >> 3) & 3 == 3: a, b = i(B), R(C)

		pseudocode = {
			0: f"c = True",
			1: f"c = False",
			2: f"c = {a} == {b}",
			3: f"c = {a} != {b}",
			4: f"c = signed({a}) < signed({b})",
			5: f"c = signed({a}) > signed({b})",
			6: f"c = {a} < {b}",
			7: f"c = {a} > {b}"
		}[A & 7]
		#print(pseudocode)
	elif op == 10:
		a = R(B)
		b = C & 7
		pseudocode = R(A) + " = " + [
			f"({a} << {b}) & 63",
			f"{a} >> {b}",
			f"(signed({a}) >> {b}) & 63",
			f"rol({a}, {b})"
		][(C >> 3) & 3]
	elif op == 13:	pseudocode = R(A) + " = " + indirect
	elif op == 14:	pseudocode = indirect + " = " + R(A)
	elif op == 15:	pseudocode = f"pass # jump target {l(A * 64 + B)}, {i(C)}"
	elif op == 16:	pseudocode = f"jump_up({l(A * 64 + B)}, {R(C)})"
	elif op == 17:	pseudocode = f"jump_dn({l(A * 64 + B)}, {R(C)})"
	elif op == 18:	pseudocode = f"{R(A)} = IO[{i(B)}]({R(C)})"
	elif op == 19:
		pr = C & 15
		if (C >> 4) & 1 == 0:
			#pseudocode = f"print('fmu/{pr}',{R(A)}, '*', {R(B)}, '= ', end=''); {R(A)} = (({R(A)} * {R(B)}) >> {pr}) & 63; print({R(A)})"
			pseudocode = f"{R(A)} = (({R(A)} * {R(B)}) >> {pr}) & 63"
		elif (C >> 4) & 1 == 1:
			pseudocode = f"{R(A)} = ((signed({R(A)}) * signed({R(B)})) >> {pr}) & 63"
	elif op == 20: pseudocode = "raise Exception('ILLEGAL INSTRUCTION 20')"

	pseudocode = pseudocode.replace("r[0] = ", "").replace("r[0]", "0")
	pseudocode = {
		0: "",
		1: "if c == True: ",
		2: "if c == False: "
	}[condition] + pseudocode

	milkalog = f"{IPP*3//4}: ({condition}: {oct(op)[2:]}) {oct(A)[2:]} {oct(B)[2:]} {oct(C)[2:]}"

	return (pseudocode, compile(pseudocode, "asm", "exec", optimize=1), milkalog)

emu_charset = list("0123456789abcdefghijklmnopqrstuvwxyz +-*/<=>()[]{}#$_?|^&!~,.:\n".upper()) + [""]
assert len(emu_charset) == 64
def ascii2emu(x):
	if x not in emu_charset: x = ''
	return emu_charset.index(x)

def emu2ascii(x):
	if x not in range(64): return 63
	return emu_charset[x]

serial_buf = []

def SERIAL_INCOMING(_):
	return min(len(serial_buf), 63)

def SERIAL_READ(_):
	return serial_buf.pop(0) if len(serial_buf) > 0 else 63

def SERIAL_WRITE(x):
	print(emu2ascii(x), end='')
	return 0

clock_start = time.time()
def clock_reset():
	global clock_start
	clock_start = time.time()

def clock_get():
	return min(4095, int((time.time() - clock_start) * 100))

def CLOCK_LO_CS(x):
	r = clock_get()
	if x: clock_reset()
	return r & 63

def CLOCK_HI_CS(x):
	r = clock_get()
	if x: clock_reset()
	return r // 64

from enet import ENET_INCOMING, ENET_RECV, ENET_SEND, ENET_CONN_CTRL, enet_server, enet_client

print(sys.argv)
if len(sys.argv) >= 3:
	print("SERVERERRRRERERRE")
	print(sys.argv[2])
	if sys.argv[2][0] == 's':
		enet_server(int(sys.argv[2][1:]))
	if sys.argv[2][0] == 'c':
		enet_client(sys.argv[2][1:])

IO = {
	0: SERIAL_INCOMING,
	1: SERIAL_READ,
	2: SERIAL_WRITE,
	3: CLOCK_LO_CS,
	4: CLOCK_HI_CS,
	
	8: ENET_INCOMING,
	9: ENET_RECV,
	10: ENET_SEND,
	11: ENET_CONN_CTRL,
}

rom = open(sys.argv[1] if len(sys.argv) > 1 else "emu10.rom", "r").read().strip()
rom = [pseudocode(rom[i:i+4]) for i in range(0, len(rom), 4)]

print("\n".join(q[0] for q in rom))

def stdin_thread_fn():
	global serial_buf
	while running:
		Z = [ascii2emu(x) for x in input().upper()]
		serial_buf += [q for q in Z if q != None]

stdin_thread = threading.Thread(target=stdin_thread_fn)
stdin_thread.start()

from collections import defaultdict
perf = defaultdict(list)

def log_perf():
	print("#\tns\tasm")
	for i in range(len(rom)):
		if i in perf:
			print(f"{len(perf[i])}\t{int(1000000000 * sum(perf[i]) / len(perf[i]))}\t{rom[i][0]}")
		else:
			print(f"-\t-\t{rom[i][0]}")

#atexit.register(log_perf)

def fp(a, b):
	ab = a * 64 + b
	if ab >= 2048:
		ab -= 4096
	return ab / 256 #((a * 64 + b) / 256)

debug = False
num = 0
while running:
	num += 1
	assert r[0] == 0
	#debug = rom_ptr > 100
	#if debug: print(rom_ptr, rom[rom_ptr][0])
	#if debug: input(f"step? {c} {r[:30]} {(fp(r[1], r[2]), fp(r[3], r[4]), fp(r[5], r[6]))}")
	#t0 = time.perf_counter()
	#rp = rom_ptr
	#if rom[rom_ptr][0] == 'jump_up(0o2002, r[63])':
	#	print((fp(r[1], r[2]), fp(r[3], r[4]), fp(r[5], r[6])), r[1:7])
	#if 'pass # jump target 0o1012, 0' in rom[rom_ptr][0]:
	#	print(fp(r[12], r[13]), fp(r[14], r[15]))
	if not((rom[rom_ptr][0].startswith("if c == True: ") and c == False) or (rom[rom_ptr][0].startswith("if c == False: ") and c == True)):
		print(int(c or 0), rom[rom_ptr][2])
	exec(rom[rom_ptr][1])
	#t1 = time.perf_counter()
	#perf[rp].append(t1-t0)
	# if len(perf[rp]) > 100000 and debug == False:
		# print("DEBUG LONG LOOP")
		# debug = True
	go_down()

print(f"{num} steps")
print("Press enter to finish.")
stdin_thread.join()
