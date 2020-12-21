from PIL import Image
im = Image.open("edge.png")
v = im.tobytes()[::4]
S=set(divmod(i, 64)[::-1] for i in range(4096) if v[i] == 255)
for i, P in enumerate(S): print(f"add r1, r0, {P[0]}\nio 20, r1\nadd r1, r0, {P[1]}\nio 20, r1")
