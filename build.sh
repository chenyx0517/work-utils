#!/bin/bash

# FontTool Build Script - 优化版
# 字体处理工具构建脚本

echo "🚀 开始构建 FontTool..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -r requirements.txt

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
rm -rf dist/ build/ FontTool.app

# 选择构建模式
echo "请选择构建模式："
echo "1) 单文件模式 (文件小，启动较慢)"
echo "2) 目录模式 (启动快，需要分发整个目录)"
echo "3) 优化单文件模式 (平衡大小和速度)"
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo "🔨 使用单文件模式构建..."
        pyinstaller FontTool.spec
        ;;
    2)
        echo "🔨 使用目录模式构建 (推荐，启动最快)..."
        pyinstaller FontTool-dir.spec
        ;;
    3)
        echo "🔨 使用优化单文件模式构建..."
        pyinstaller FontTool-optimized.spec
        ;;
    *)
        echo "❌ 无效选择，使用默认单文件模式"
        pyinstaller FontTool.spec
        ;;
esac

# 检查构建结果
if [ -d "dist/FontTool.app" ]; then
    echo "✅ 构建成功！"
    echo "📱 应用位置: dist/FontTool.app"
    echo "🎯 运行命令: open dist/FontTool.app"
    
    # 显示文件大小
    app_size=$(du -sh dist/FontTool.app | cut -f1)
    echo "📊 应用大小: $app_size"
    
    # 性能提示
    if [ "$choice" = "2" ]; then
        echo "💡 提示: 目录模式启动最快，但需要分发整个 FontTool.app 目录"
    elif [ "$choice" = "3" ]; then
        echo "💡 提示: 优化单文件模式平衡了文件大小和启动速度"
    else
        echo "💡 提示: 单文件模式便于分发，但启动较慢"
    fi
else
    echo "❌ 构建失败，请检查错误信息"
    exit 1
fi
