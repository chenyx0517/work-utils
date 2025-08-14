#!/usr/bin/env python3
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter

def compress_font(input_font, output_font, weights):
    print(f"Processing font: {input_font}")
    print(f"Target weights: {weights}")
    
    # 加载字体
    font = TTFont(input_font)
    
    # 检查是否是可变字体
    is_variable = 'fvar' in font
    
    if is_variable:
        print("Detected variable font")
        # 获取字重范围
        fvar = font['fvar']
        weight_axis = None
        for axis in fvar.axes:
            if axis.axisTag == 'wght':
                weight_axis = axis
                break
        
        if not weight_axis:
            print("Error: Font does not have a weight axis!")
            sys.exit(1)
        
        print(f"Weight range: {weight_axis.minValue} - {weight_axis.maxValue}")
        
        # 为每个目标字重创建实例
        for weight in weights:
            print(f"\nProcessing weight: {weight}")
            
            # 创建字重实例
            from fontTools.varLib.instancer import instantiateVariableFont
            instance = instantiateVariableFont(font, {'wght': weight})
            
            # 创建子集器
            subsetter = Subsetter()
            
            # 设置要保留的字符
            chars = set()
            # 基本拉丁字母
            chars.update(chr(i) for i in range(0x0021, 0x007F))
            # 中文汉字
            chars.update(chr(i) for i in range(0x4E00, 0x9FFF))
            # 中文标点符号
            chars.update(chr(i) for i in range(0x3000, 0x303F))
            # 全角字符
            chars.update(chr(i) for i in range(0xFF00, 0xFFEF))
            
            subsetter.populate(text=''.join(chars))
            subsetter.subset(instance)
            
            # 生成输出文件名
            output_name = os.path.splitext(output_font)[0]
            output_path = f"{output_name}-{weight}.woff2"
            
            # 保存为 WOFF2
            instance.flavor = 'woff2'
            instance.save(output_path)
            
            # 输出文件大小信息
            input_size = os.path.getsize(input_font)
            output_size = os.path.getsize(output_path)
            print(f"Original size: {input_size/1024/1024:.2f}MB")
            print(f"Compressed size: {output_size/1024/1024:.2f}MB")
            print(f"Compression ratio: {(1 - output_size/input_size)*100:.2f}%")
            print(f"Output file: {output_path}")
    else:
        print("Detected static font")
        print("Note: Static fonts don't support weight filtering, processing as single weight")
        
        # 创建子集器
        subsetter = Subsetter()
        
        # 设置要保留的字符
        chars = set()
        # 基本拉丁字母
        chars.update(chr(i) for i in range(0x0021, 0x007F))
        # 中文汉字
        chars.update(chr(i) for i in range(0x4E00, 0x9FFF))
        # 中文标点符号
        chars.update(chr(i) for i in range(0x3000, 0x303F))
        # 全角字符
        chars.update(chr(i) for i in range(0xFF00, 0xFFEF))
        
        subsetter.populate(text=''.join(chars))
        subsetter.subset(font)
        
        # 生成输出文件名
        output_name = os.path.splitext(output_font)[0]
        output_path = f"{output_name}.woff2"
        
        # 保存为 WOFF2
        font.flavor = 'woff2'
        font.save(output_path)
        
        # 输出文件大小信息
        input_size = os.path.getsize(input_font)
        output_size = os.path.getsize(output_path)
        print(f"Original size: {input_size/1024/1024:.2f}MB")
        print(f"Compressed size: {output_size/1024/1024:.2f}MB")
        print(f"Compression ratio: {(1 - output_size/input_size)*100:.2f}%")
        print(f"Output file: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compress_font.py <input_font> [weight1 weight2 ...]")
        print("\nExamples:")
        print("  python compress_font.py font.ttf                    # Variable font with default weights")
        print("  python compress_font.py font.ttf 400 500            # Variable font with specific weights")
        print("  python compress_font.py static-font.ttf             # Static font (weights ignored)")
        sys.exit(1)
    
    input_font = sys.argv[1]
    weights = [int(w) for w in sys.argv[2:]] if len(sys.argv) > 2 else [400, 500]
    
    output_font = os.path.splitext(input_font)[0] + "-min.woff2"
    compress_font(input_font, output_font, weights) 