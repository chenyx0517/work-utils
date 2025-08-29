#!/bin/bash

# ==============================================================================
# 字体转换工具打包脚本 (含图标设置)
# ==============================================================================

# 脚本一旦遇到错误，就立即退出
set -e

# --- 变量定义 ---
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
APP_NAME="FontConverter"
ICON_FILE="icon.ico" # 假设你的图标文件名为 icon.ico

# --- 1. 清理旧的构建文件 ---
echo "🚀 开始打包应用..."
echo "清理旧的构建文件..."
rm -rf "$SCRIPT_DIR/dist"
rm -rf "$SCRIPT_DIR/build"
rm -f "$SCRIPT_DIR/$APP_NAME.spec"
echo "清理完成。"
echo "---"

# --- 2. 检查并安装依赖 ---
echo "检查并安装 Python 依赖..."
if ! command -v pip &> /dev/null
then
    echo "警告：pip 未安装。请先安装 pip。"
    exit 1
fi

pip install pyinstaller pywebview fonttools
echo "依赖安装完成。"
echo "---"

# --- 3. 使用 PyInstaller 打包 ---
echo "开始使用 PyInstaller 打包..."
if [ ! -f "$SCRIPT_DIR/$ICON_FILE" ]; then
    echo "❌ 错误: 找不到图标文件 '$ICON_FILE'，将不使用图标进行打包。"
    ICON_PARAM=""
else
    ICON_PARAM="--icon=$SCRIPT_DIR/$ICON_FILE"
    echo "✔️ 找到图标文件，将在打包时使用它。"
fi

pyinstaller --noconsole --onefile \
    --name "$APP_NAME" \
    --add-data "$SCRIPT_DIR/index.html:." \
    $ICON_PARAM \
    "$SCRIPT_DIR/app.py"
echo "---"

# --- 4. 检查打包结果并输出路径 ---
if [ -f "$SCRIPT_DIR/dist/$APP_NAME" ]; then
    echo "✅ 打包成功！"
    echo "可执行文件位于: $SCRIPT_DIR/dist/$APP_NAME"
else
    echo "❌ 打包失败，请检查上面的错误信息。"
    exit 1
fi