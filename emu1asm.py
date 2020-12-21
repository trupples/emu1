""" EMU 1.0 assembler

Syntax features:

// line comments

!define word value <- acts like the C #define mostly

Character literals with \
for example \X = 041, \5 = 005, \^ = 067
\SP = space = 044
\LF = linefeed = 076

Octal literals with 0 prefix, decimal literals with no prefix. Negative decimals properly handled.

"""




import re, sys

def pr(s):
	if s[0] == 'r':
		return (int(s[1:]), )

charset = list("0123456789abcdefghijklmnopqrstuvwxyz") + ["sp"] + list("+-*/<=>()[]{}#$_?|^&!~,.:") + ["lf", "-1"]

assert len(charset) == 64

def pi(s):
	if s[0] == '0' or (s[0] == '-' and s[1] == '0'):
		return (int(s, 8) % 64, )
	if s[0] in "123456789" or (s[0] == '-' and s[1] in "123456789"):
		return (int(s) % 64, )
	if s[0] == '\\':
		return (charset.index(s[1:]), )


def pindirect(s):
	if s[0] == '[' and s[-1] == ']':
		s = s[1:-1]
		parts = {part.strip() for part in s.split("+")}
		reg = 0
		off = 0
		for part in parts:
			if pr(part):
				reg = pr(part)
				parts.remove(part)
				break
		for part in parts:
			if pi(part):
				off = pi(part)
				parts.remove(part)
				break
		assert parts == set()
		return [reg, off]


def OPC(op, c):
	return c * 21 + op + 1

cc = ["tr", "fa", "eq", "ne", "sl", "sg", "ul", "ug"]

binary = ''
defines = {}
while True:
	try:
		enc = None
		Line = input().strip().lower()
		line, comment = (Line + ' // ').split('//', 1)
		if line.startswith("!define "):
			hashdef, name, val = line.split(" ", 2)
			defines[name] = val
			continue
		for n, v in defines.items():
			line = re.sub(r"\b" + n + r"\b", v, line)
			# line = line.replace(n, v)
		line = line.strip()
		if line == '':
			continue
		if line[0] == '+':
			c = 1
			line = line[1:].strip()
		elif line[0] == '-':
			c = 2
			line = line[1:].strip()
		else:
			c = 0

		op_text, v = (line + " ").split(" ", 1)
		v = [arg.strip() for arg in v.split(",")]

		if op_text == 'halt': enc = [0, 0, 0, 0]

		if op_text == 'add' and pr(v[2]): enc = [OPC(0, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'add' and pi(v[2]): enc = [OPC(1, c), pr(v[0]), pr(v[1]), pi(v[2])]
		if op_text == 'sub' and pr(v[2]): enc = [OPC(2, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'or'  and pr(v[2]): enc = [OPC(4, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'or'  and pi(v[2]): enc = [OPC(5, c), pr(v[0]), pr(v[1]), pi(v[2])]
		if op_text == 'xor' and pr(v[2]): enc = [OPC(6, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'xor' and pi(v[2]): enc = [OPC(7, c), pr(v[0]), pr(v[1]), pi(v[2])]
		if op_text == 'and' and pr(v[2]): enc = [OPC(8, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'and' and pi(v[2]): enc = [OPC(9, c), pr(v[0]), pr(v[1]), pi(v[2])]
		if op_text == 'shl' and pr(v[2]): enc = [OPC(11, c), pr(v[0]), pr(v[1]), pr(v[2])]
		if op_text == 'shr' and pr(v[2]): enc = [OPC(12, c), pr(v[0]), pr(v[1]), pr(v[2])]

		if op_text[:3] == 'cmp' and pr(v[0]) and pr(v[1]): enc = [OPC(3, c), cc.index(op_text[3:]), pr(v[0]), pr(v[1])]
		#if op_text[:4] =='xcmp' and pr(v[0]) and pr(v[1]): enc = [OPC(3, c), cc.index(op_text[4:])+8, pr(v[1]), pr(v[0])]
		if op_text[:3] == 'cmp' and pr(v[0]) and pi(v[1]): enc = [OPC(3, c), cc.index(op_text[3:])+16, pr(v[0]), pi(v[1])]
		if op_text[:3] == 'cmp' and pi(v[0]) and pr(v[1]): enc = [OPC(3, c), cc.index(op_text[3:])+24, pi(v[0]), pr(v[1])]


		if op_text == 'shl' and pi(v[2]): enc = [OPC(10, c), pr(v[0]), pr(v[1]), pi(v[2])]
		if op_text == 'shr' and pi(v[2]): enc = [OPC(10, c), pr(v[0]), pr(v[1]), pi(v[2])[0]+8]
		if op_text == 'sar':              enc = [OPC(10, c), pr(v[0]), pr(v[1]), pi(v[2])[0]+16]
		if op_text == 'rol':              enc = [OPC(10, c), pr(v[0]), pr(v[1]), pi(v[2])[0]+24]

		if op_text == 'ld': enc = [OPC(13, c), pr(v[0])] + pindirect(v[1])
		if op_text == 'st': enc = [OPC(14, c), pr(v[1])] + pindirect(v[0])

		if op_text[:4] == 'fmu/': enc = [OPC(19, c), pr(v[0]), pr(v[1]), int(op_text[4:])]
		if op_text[:4] == 'fms/': enc = [OPC(19, c), pr(v[0]), pr(v[1]), int(op_text[4:])+16]

		if op_text == 'lbl': enc = [OPC(15, c), int(v[0], 8) >> 6, int(v[0], 8) & 63, (pi(v[1]) if len(v) == 2 else 0)]
		if op_text == 'jup': enc = [OPC(16, c), int(v[0], 8) >> 6, int(v[0], 8) & 63, (pr(v[1]) if len(v) == 2 else 0)]
		if op_text == 'jdn': enc = [OPC(17, c), int(v[0], 8) >> 6, int(v[0], 8) & 63, (pr(v[1]) if len(v) == 2 else 0)]

		if op_text == 'io':
			if len(v) == 3: enc = [OPC(18, c), pr(v[0]), pi(v[1]), pr(v[2])]
			elif len(v) == 2 and pr(v[0]): enc = [OPC(18, c), pr(v[0]), pi(v[1]), 0]
			elif len(v) == 2 and pr(v[1]): enc = [OPC(18, c), 0, pi(v[0]), pr(v[1])]
			elif len(v) == 1: enc = [OPC(18, c), 0, pi(v[0]), 0]

		binary += ''.join("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[q[0] if type(q) == tuple else q] for q in enc)
	except EOFError:
		break
	except Exception as e:
		sys.stderr.write(f"Bad line '{Line}' {e}")
		pass

print(binary)
