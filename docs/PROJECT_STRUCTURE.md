# 项目结构说明

## 📁 目录结构

```
font-converter-tool/
├── src/                    # 源代码目录
│   ├── font_trans.py       # 主应用程序 (GUI)
│   ├── font_splitter.py    # 字体拆分工具 (CLI)
│   └── app.py              # 核心转换逻辑
├── assets/                 # 资源文件
│   ├── fonts/              # 字体文件
│   │   └── zh/             # 中文字体相关
│   └── icons/              # 图标文件
├── docs/                   # 文档目录
│   ├── README.md           # 原始README
│   ├── BACKEND_API_SETUP.md
│   ├── CDN_UPLOAD_GUIDE.md
│   ├── QUICK_AUTH_SETUP.md
│   ├── REAL_API_CONFIG.md
│   └── REAL_CDN_SETUP.md
├── dist/                   # 打包输出目录
├── splitRes/               # 字体拆分结果
│   ├── ja/                 # 日文字符映射
│   └── tc/                 # 繁体中文字符映射
├── unicode-*.txt           # Unicode范围定义文件
├── index.html              # Web界面
├── styles.css              # 样式文件
├── FontTool.spec      # PyInstaller配置
├── build.sh                # 构建脚本
├── requirements.txt        # Python依赖
├── package.json            # Node.js配置
├── .gitignore              # Git忽略文件
└── README.md               # 项目说明
```

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python src/font_trans.py
```

### 构建应用

```bash
./build.sh
```

### 字体拆分

```bash
# 简体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language zh

# 繁体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language tc

# 日文
python src/font_splitter.py assets/fonts/YourFont.ttf --language ja
```

## 📝 文件说明

- **src/font_trans.py**: 主应用程序，使用 PyWebView 构建的桌面 GUI
- **src/font_splitter.py**: 命令行字体拆分工具
- **src/app.py**: 核心字体转换逻辑
- **FontTool.spec**: PyInstaller 打包配置
- **unicode-\*.txt**: 各语言的 Unicode 字符范围定义
- **assets/fonts/**: 存放字体文件
- **assets/icons/**: 存放应用图标
- **docs/**: 存放项目文档
- **splitRes/**: 字体拆分后的字符映射文件
