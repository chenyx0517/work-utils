#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体拆分工具使用示例
"""

import os
import subprocess
import sys

def run_example():
    """运行使用示例"""
    
    print("🚀 字体拆分工具使用示例")
    print("=" * 50)
    
    # 检查字体文件是否存在
    font_file = "fonts/有爱魔兽圆体-M.ttf"
    if not os.path.exists(font_file):
        print(f"❌ 字体文件不存在: {font_file}")
        print("请确保字体文件存在于fonts目录中")
        return False
    
    # 检查unicode文件是否存在
    unicode_file = "unicode-zh-TW.txt"
    if not os.path.exists(unicode_file):
        print(f"❌ Unicode文件不存在: {unicode_file}")
        print("请确保unicode文件存在")
        return False
    
    print("✅ 所有必要文件都存在")
    
    # 示例1: 基本用法
    print("\n📝 示例1: 基本字体拆分+CDN上传+CSS生成")
    print("-" * 30)
    
    cmd1 = [
        'python', 'font_splitter.py',
        font_file,
        '--language', 'tc',
        '--num-chunks', '3',  # 只拆分3个子集，加快演示
        '--output', 'example_output'
    ]
    
    print(f"命令: {' '.join(cmd1)}")
    print("执行中...")
    
    try:
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=120)
        if result1.returncode == 0:
            print("✅ 字体拆分+CDN上传+CSS生成成功")
            print("输出文件:")
            for file in os.listdir('example_output/tc'):
                print(f"  - {file}")
                if file.endswith('.css'):
                    print("    CSS文件内容预览:")
                    with open(f'example_output/tc/{file}', 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:15]  # 显示前15行
                        for line in lines:
                            print(f"    {line.rstrip()}")
        else:
            print("❌ 字体处理失败")
            print(result1.stderr)
            return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False
    
    # 示例2: 自定义字体族名称
    print("\n📝 示例2: 自定义字体族名称")
    print("-" * 30)
    
    cmd2 = [
        'python', 'font_splitter.py',
        font_file,
        '--language', 'tc',
        '--num-chunks', '3',
        '--font-family', '示例字体',
        '--output', 'example_output_custom'
    ]
    
    print(f"命令: {' '.join(cmd2)}")
    print("执行中...")
    
    try:
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
        if result2.returncode == 0:
            print("✅ 自定义字体族名称成功")
            print("输出文件:")
            for file in os.listdir('example_output_custom/tc'):
                print(f"  - {file}")
        else:
            print("❌ 自定义字体族名称失败")
            print(result2.stderr)
            return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False
    
    print("\n🎉 所有示例执行完成!")
    print("\n📋 总结:")
    print("1. 基本用法: 字体拆分+CDN上传+CSS生成")
    print("2. 自定义字体族: 可以自定义CSS中的字体族名称")
    
    return True

def cleanup_examples():
    """清理示例文件"""
    import shutil
    
    example_dirs = ['example_output', 'example_output_custom']
    
    for example_dir in example_dirs:
        if os.path.exists(example_dir):
            shutil.rmtree(example_dir)
            print(f"🗑️  已清理: {example_dir}")

if __name__ == "__main__":
    try:
        success = run_example()
        
        if success:
            print("\n✅ 示例运行成功!")
        else:
            print("\n❌ 示例运行失败!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  示例被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 示例异常: {e}")
        sys.exit(1)
    finally:
        # 询问是否清理示例文件
        try:
            response = input("\n是否清理示例文件? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                cleanup_examples()
        except KeyboardInterrupt:
            pass
