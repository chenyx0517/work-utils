import time
from font_trans import convert_ttf_to_woff2_core

input_file = "./有爱魔兽圆体-M.ttf"

start = time.time()
success, msg = convert_ttf_to_woff2_core(input_file)
end = time.time()

print(msg)
print(f"耗时：{end - start:.2f} 秒")

