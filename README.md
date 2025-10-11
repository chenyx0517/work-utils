打包 app：
conda activate font_convert_new && pyinstaller FontConverter.spec

字体拆分工具使用示例：

# 日语字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language ja

# 繁体中文字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language tc

# 简体中文字体拆分

python3 font_splitter.py fonts/YourFont.ttf --language zh

检测字体：
https://fontdrop.info/
