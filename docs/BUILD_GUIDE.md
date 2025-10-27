# 构建和打包指南

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

```bash
python src/font_trans.py
```

## 📦 打包应用

### 方法 1：使用构建脚本（推荐）

```bash
./build.sh
```

### 方法 2：手动打包

```bash
pyinstaller FontTool.spec
```

打包完成后，应用将生成在 `dist/FontTool.app`

### 运行打包后的应用

```bash
open dist/FontTool.app
```

## 🔧 字体拆分工具

### 命令行使用

```bash
# 简体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language zh

# 繁体中文
python src/font_splitter.py assets/fonts/YourFont.ttf --language tc

# 日文
python src/font_splitter.py assets/fonts/YourFont.ttf --language ja
```

## 📁 项目结构

```
├── src/                    # 源代码
│   ├── font_trans.py       # 主应用程序
│   ├── font_splitter.py    # 字体拆分工具
│   └── app.py              # 核心转换逻辑
├── assets/                 # 资源文件
│   ├── fonts/              # 字体文件
│   └── icons/              # 图标文件
├── dist/                   # 打包输出目录
├── unicode-*.txt           # Unicode范围定义
├── FontTool.spec      # PyInstaller配置
├── build.sh                # 构建脚本
└── requirements.txt        # Python依赖
```

## ⚠️ 注意事项

1. **macOS 安全设置**：首次运行时可能需要在"系统偏好设置 > 安全性与隐私"中允许运行
2. **依赖检查**：确保已安装所有 Python 依赖
3. **字体文件**：将需要转换的字体文件放在 `assets/fonts/` 目录中
4. **Unicode 文件**：确保 `unicode-*.txt` 文件存在且格式正确
