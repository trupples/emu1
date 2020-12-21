import sys

while True:
	c = sys.stdin.buffer.read1(1)[0]
	sys.stdout.write((list("0123456789abcdefghijklmnopqrstuvwxyz +-*/<=>()[]{}#$_?|^&!~,.:\n".upper()) + [""])[c])

