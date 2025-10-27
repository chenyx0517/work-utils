# Font Converter Tool

一个用于将 TTF 字体转换为 WOFF2 格式的桌面应用程序，支持多语言字体子集化。

## 功能特性

- 🎨 TTF/OTF 字体转换为 WOFF2 格式
- 🌍 支持多语言字体子集化（简体中文、繁体中文、日文）
- 📦 桌面应用程序，支持拖拽操作
- ⚡ 高效的字体压缩和优化
- 🎯 精确的 Unicode 范围控制

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 运行桌面应用

```bash
python src/font_trans.py
```

### 命令行字体拆分

```bash
# 简体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language zh

# 繁体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language tc

# 日文
python src/font_splitter.py assets/fonts/YourFont.ttf --language ja
```

### 打包应用程序

```bash
pyinstaller FontTool.spec
```

## 项目结构

```
├── src/                    # 源代码
│   ├── font_trans.py       # 主应用程序
│   ├── font_splitter.py    # 字体拆分工具
│   └── app.py              # 核心转换逻辑
├── assets/                 # 资源文件
│   ├── fonts/              # 字体文件
│   └── icons/              # 图标文件
├── docs/                   # 文档
├── dist/                   # 打包输出目录
├── unicode-*.txt           # Unicode范围定义文件
├── requirements.txt        # Python依赖
├── FontTool.spec      # PyInstaller配置
└── README.md              # 项目说明
```

## 技术栈

- **Python 3.8+**
- **PyWebView** - 桌面应用框架
- **FontTools** - 字体处理库
- **PyInstaller** - 应用打包工具

## 许可证

ISC License
