from PIL import Image
im = Image.open("win.png")
v = im.tobytes()[::4]

for x in range(7, 54):
	a1 = int(''.join("01"[v[y*64 + x] == 255] for y in range(10, 16)), 2)
	a2 = int(''.join("01"[v[y*64 + x] == 255] for y in range(16, 22)), 2)
	a3 = int(''.join("01"[v[y*64 + x] == 255] for y in range(22, 28)), 2)
	print(f"add r1, r0 {a1}")
	print(f"io 20, r1")
	print(f"add r1, r0 {a2}")
	print(f"io 20, r1")
	print(f"add r1, r0 {a3}")
	print(f"io 20, r1")
		
