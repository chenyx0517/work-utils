打包 app：
pyinstaller --noconsole --onefile --windowed --name "字体转 WOFF2 工具" font_trans.py

字体拆分工具使用示例：

# 日语字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language ja --unicode-order-file unicode-ja.txt

# 繁体中文字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language tc --unicode-order-file unicode-zh-TW.txt

# 简体中文字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language zh --unicode-order-file unicode-zh-CN.txt

检测字体：
https://fontdrop.info/
