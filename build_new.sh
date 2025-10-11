#!/bin/bash

echo "开始重新打包字体拆分和转换工具..."

# 清理之前的构建
echo "清理之前的构建文件..."
rm -rf build/
rm -rf dist/

# 使用新的spec文件打包
echo "使用PyInstaller打包..."
pyinstaller FontConverter.spec

# 检查打包结果
if [ -d "dist/FontConverter.app" ]; then
    echo "✅ 打包成功！"
    echo "应用位置: dist/FontConverter.app"
    echo "你可以直接运行这个应用"
else
    echo "❌ 打包失败，请检查错误信息"
fi

echo "打包完成！"
