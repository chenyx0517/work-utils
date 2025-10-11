#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体拆分工具
根据字符频率顺序将字体包拆分成多个子字体包
"""

import os
import sys
import math
import re
import time
import json
import hashlib
from fontTools import subset
from fontTools.ttLib import TTFont
import argparse
from typing import List, Tuple, Iterable, Dict, Optional
from datetime import datetime

# CDN配置 - 根据公司实际情况修改
CDN_CONFIG = {
    'base_url': 'https://your-company-cdn.com/fonts',  # 替换为实际的CDN地址
}

# 语言到unicode文件的映射
LANGUAGE_UNICODE_MAP = {
    'zh': 'unicode-zh-CN.txt',  # 简体中文
    'ja': 'unicode-ja.txt',     # 日文
    'tc': 'unicode-zh-TW.txt',  # 繁体中文
}

def parse_unicode_ranges_from_text(text: str) -> List[int]:
    """
   
    """
    codepoints: List[int] = []
    seen = set()
    for m in re.finditer(r"unicode-range\s*:\s*([^;]+);", text, flags=re.IGNORECASE):
        ranges_part = m.group(1)
        # 去除 C 风格块注释，避免注释把逗号分割打乱
        ranges_part = re.sub(r"/\*.*?\*/", "", ranges_part, flags=re.DOTALL)
        # 逗号分割每个项
        for item in ranges_part.split(','):
            token = item.strip()
            if not token:
                continue
            # 解析 U+XXXX 或 U+XXXX-YYYY
            m2 = re.match(r"U\+([0-9A-Fa-f]{1,6})(?:-([0-9A-Fa-f]{1,6}))?", token)
            if not m2:
                continue
            start_hex = m2.group(1)
            end_hex = m2.group(2)
            start_cp = int(start_hex, 16)
            end_cp = int(end_hex, 16) if end_hex else start_cp
            if end_cp < start_cp:
                start_cp, end_cp = end_cp, start_cp
            for cp in range(start_cp, end_cp + 1):
                if cp not in seen:
                    seen.add(cp)
                    codepoints.append(cp)
    return codepoints

def parse_unicode_order_file(file_path: str) -> List[str]:
    """
    从unicode配置文件中解析出按出现顺序排列的 Unicode
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        cps = parse_unicode_ranges_from_text(content)
        chars: List[str] = []
        for cp in cps:
            try:
                chars.append(chr(cp))
            except Exception:
                # 跳过无效码点
                pass
        return chars
    except Exception as e:
        print(f"读取或解析 unicode 顺序文件失败: {e}")
        return []

def load_character_list_file(file_path: str) -> List[str]:
    """
    从纯字符列表文件中读取字符。
    文件内容应该是连续的字符字符串，没有其他格式。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return list(content)
    except Exception as e:
        print(f"读取字符列表文件失败: {e}")
        return []

def expand_unicode_ranges_to_chars(ranges: Iterable[str]) -> List[str]:
    """
    将形如 'U+4e00' 或 'U+4e00-4e0f' 的片段列表展开为字符列表（保序去重）。
    仅用于预设块展开。
    """
    seen = set()
    chars: List[str] = []
    for token in ranges:
        m2 = re.match(r"U\+([0-9A-Fa-f]{1,6})(?:-([0-9A-Fa-f]{1,6}))?", token.strip())
        if not m2:
            continue
        start_cp = int(m2.group(1), 16)
        end_cp = int(m2.group(2), 16) if m2.group(2) else start_cp
        if end_cp < start_cp:
            start_cp, end_cp = end_cp, start_cp
        for cp in range(start_cp, end_cp + 1):
            if cp not in seen:
                seen.add(cp)
                try:
                    chars.append(chr(cp))
                except Exception:
                    pass
    return chars

def merge_orders_keep_first(*orders: Iterable[str]) -> List[str]:
    """
    合并多个字符序列，保留首次出现的顺序，后续重复将被忽略。
    """
    seen = set()
    merged: List[str] = []
    for order in orders:
        if not order:
            continue
        for ch in order:
            if ch not in seen:
                seen.add(ch)
                merged.append(ch)
    return merged

def build_order_from_corpus(paths: List[str]) -> List[str]:
    """
    从文本语料构建字符频率顺序：按出现次数从高到低，出现次数相同时按先出现顺序稳定排序。
    仅统计 BMP 常用可打印字符（不限定语言）。
    """
    counts: Dict[str, int] = {}
    first_index: Dict[str, int] = {}
    idx = 0
    for p in paths:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    for ch in line:
                        # 过滤控制字符
                        if ch <= '\u001f':
                            continue
                        counts[ch] = counts.get(ch, 0) + 1
                        if ch not in first_index:
                            first_index[ch] = idx
                        idx += 1
        except Exception as e:
            print(f"警告: 读取语料失败 {p}: {e}")
    # 按频次降序、首次出现升序排序
    ordered = sorted(counts.keys(), key=lambda c: (-counts[c], first_index[c]))
    return ordered

PRESET_BLOCKS: Dict[str, List[str]] = {
    # 基础日文块：平假名、片假名、片假名音标扩展、半角片假名
    'jp-basic': [
        'U+3040-309F',  # Hiragana
        'U+30A0-30FF',  # Katakana
        'U+31F0-31FF',  # Katakana Phonetic Extensions
        'U+FF66-FF9F',  # Halfwidth Katakana
        # 常用 CJK 统一表意文字（汉字，共用），按区块整体追加，由你的外部顺序再做交集
        'U+4E00-9FFF',  # CJK Unified Ideographs
    ],
    # 繁体基础块：CJK 统一表意文字及兼容/扩展常用区（粗粒度）
    'tc-basic': [
        'U+4E00-9FFF',  # CJK Unified Ideographs
        'U+3400-4DBF',  # CJK Extension A
        'U+F900-FAFF',  # CJK Compatibility Ideographs
        'U+2F800-2FA1F',  # CJK Compatibility Ideographs Supplement
    ],
}

def analyze_font_characters(font_path: str) -> List[str]:
    """
    分析字体文件中包含的字符
    返回字体中实际存在的字符列表
    """
    try:
        font = TTFont(font_path)
        available_chars = []
        
        # 获取字体中的所有字符
        if 'cmap' in font:
            for table in font['cmap'].tables:
                if hasattr(table, 'cmap'):
                    for unicode_val, glyph_name in table.cmap.items():
                        if unicode_val > 0:  # 排除控制字符
                            char = chr(unicode_val)
                            available_chars.append(char)
        
        return list(set(available_chars))  # 去重
    except Exception as e:
        print(f"分析字体字符时出错: {e}")
        return []

def filter_available_chars(font_chars: List[str], ordered_chars: List[str]) -> List[str]:
    """
    根据外部顺序与字体实际可用字符做有序交集，仅保留二者都包含的字符，保序不补齐。
    """
    font_char_set = set(font_chars)
    return [c for c in ordered_chars if c in font_char_set]

def split_characters_into_chunks(chars: List[str], num_chunks: int) -> List[List[str]]:
    """
    将字符列表分割成指定数量的块
    返回字符块列表
    """
    if num_chunks <= 0:
        raise ValueError("块数量必须大于0")
    
    if num_chunks >= len(chars):
        # 如果块数量大于等于字符数量，每个字符一个块（可能会多出空块，后续过滤）
        return [[char] for char in chars]

    # 将字符精确地划分为 num_chunks 个连续块，尽量平均分配
    total = len(chars)
    base = total // num_chunks
    rem = total % num_chunks
    chunks: List[List[str]] = []
    idx = 0
    for i in range(num_chunks):
        size = base + (1 if i < rem else 0)
        if size == 0:
            chunks.append([])
            continue
        chunk = chars[idx:idx + size]
        chunks.append(chunk)
        idx += size
    # 去掉尾部可能的空块
    while chunks and not chunks[-1]:
        chunks.pop()
    return chunks

def create_font_subset(input_font_path: str, output_path: str, chars: List[str]) -> bool:
    """
    创建字体子集
    返回是否成功
    """
    try:
        # 加载字体
        font = TTFont(input_font_path)
        
        # 创建子集化器
        subsetter = subset.Subsetter()
        
        # 设置要保留的字符
        char_text = ''.join(chars)
        subsetter.populate(text=char_text)
        
        # 执行子集化
        subsetter.subset(font)
        
        # 保存子集字体
        font.save(output_path)
        
        return True
    except Exception as e:
        print(f"创建字体子集时出错: {e}")
        return False

def codepoints_to_unicode_ranges(codepoints: List[int]) -> List[str]:
    """
    将已排序的码点列表压缩为 CSS unicode-range 片段列表，例如：
    [0x4E00,0x4E01,0x4E02,0x4E05] -> ['U+4E00-4E02','U+4E05']
    """
    if not codepoints:
        return []
    # 不排序，严格按照传入顺序压缩相邻码点，以保持与外部顺序一致的展示
    cps = list(codepoints)
    ranges: List[str] = []
    start = cps[0]
    prev = cps[0]
    for cp in cps[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        # 结束上一个段
        if start == prev:
            ranges.append(f"U+{start:x}")
        else:
            ranges.append(f"U+{start:x}-{prev:x}")
        start = prev = cp
    # 最后一段
    if start == prev:
        ranges.append(f"U+{start:x}")
    else:
        ranges.append(f"U+{start:x}-{prev:x}")
    return ranges

# Mock CDN上传接口 - 后续替换为实际OSS接口
def mock_upload_to_cdn(font_file_path: str, cdn_base_url: str, language: str) -> str:
    """
    Mock CDN上传接口
    实际使用时替换为公司的OSS上传接口
    
    参数:
    - font_file_path: 本地字体文件路径
    - cdn_base_url: CDN基础URL
    - language: 语言标识
    
    返回:
    - CDN URL
    """
    # 生成文件名hash，避免重名
    with open(font_file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    filename = os.path.basename(font_file_path)
    name, ext = os.path.splitext(filename)
    cdn_filename = f"{name}_{file_hash}{ext}"
    
    # Mock CDN URL
    cdn_url = f"{cdn_base_url}/{language}/{cdn_filename}"
    
    print(f"  📤 Mock上传: {font_file_path} -> {cdn_url}")
    
    # 这里应该调用实际的OSS上传接口
    # 例如: upload_result = oss_client.upload_file(font_file_path, cdn_filename)
    
    return cdn_url

def generate_css_file(subset_info_list: List[Dict], cdn_base_url: str, font_family: str, output_css_path: str) -> bool:
    """
    生成包含CDN地址的CSS文件
    
    参数:
    - subset_info_list: 子集信息列表
    - cdn_base_url: CDN基础URL
    - font_family: 字体族名称
    - output_css_path: 输出CSS文件路径
    
    返回:
    - bool: 是否成功
    """
    try:
        css_rules = []
        
        # 添加文件头注释
        header = f"""/* 
 * 字体CSS文件 - {font_family}
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * CDN基础地址: {cdn_base_url}
 * 包含 {len(subset_info_list)} 个字体子集
 */

"""
        
        for subset_info in subset_info_list:
            subset_num = subset_info['subset_num']
            unicode_ranges = subset_info['unicode_ranges']
            cdn_url = subset_info['cdn_url']
            language = subset_info.get('language', 'unknown')
            
            # 生成@font-face规则
            font_face = f"""@font-face {{
  font-family: {font_family};
  font-weight: 400;
  font-display: swap;
  src: url("{cdn_url}");
  unicode-range: {unicode_ranges};
}}"""
            
            css_rules.append(font_face)
        
        # 写入CSS文件
        with open(output_css_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write('\n\n'.join(css_rules))
        
        print(f"✅ CSS文件已生成: {output_css_path}")
        return True
        
    except Exception as e:
        print(f"生成CSS文件时出错: {e}")
        return False

def split_font(input_font_path: str, output_folder: str, num_chunks: int = 200, preferred_order: List[str] = None, chars_per_chunk: int | None = None, font_family: str = "有爱魔兽圆体-M", language: str = "mixed") -> bool:
    """
    拆分字体文件
    
    参数:
    - input_font_path: 输入字体文件路径
    - output_folder: 输出文件夹路径
    - num_chunks: 要拆分的块数量，默认200
    
    返回:
    - bool: 是否成功
    """
    try:
        # 检查输入文件
        if not os.path.exists(input_font_path):
            print(f"错误: 输入字体文件不存在: {input_font_path}")
            return False
        
        # 创建输出文件夹
        os.makedirs(output_folder, exist_ok=True)
        
        print(f"开始分析字体文件: {input_font_path}")
        
        # 分析字体中的字符
        font_chars = analyze_font_characters(input_font_path)
        print(f"字体中包含 {len(font_chars)} 个字符")
        
        # 必须提供外部顺序
        if not preferred_order:
            print("错误: 未提供外部字符顺序（--unicode-order-file）")
            return False
        frequency_order = preferred_order
        
        # 过滤可用字符并按外部顺序排序（严格交集，不补齐）
        available_chars = filter_available_chars(font_chars, frequency_order)
        print(f"按频率排序的可用字符: {len(available_chars)} 个")
        
        # 计算实际块数：优先按每块字符数估算；否则使用指定块数
        effective_num_chunks = num_chunks
        if chars_per_chunk and chars_per_chunk > 0:
            effective_num_chunks = max(1, math.ceil(len(available_chars) / chars_per_chunk))

        # 分割字符
        char_chunks = split_characters_into_chunks(available_chars, effective_num_chunks)
        print(f"将字符分割成 {len(char_chunks)} 个块")
        
        # 获取基础文件名
        base_name = os.path.splitext(os.path.basename(input_font_path))[0]
        file_ext = os.path.splitext(input_font_path)[1]
        
        # 创建子集字体并收集信息
        success_count = 0
        subset_info_list = []
        
        for i, chunk in enumerate(char_chunks, 1):
            output_filename = f"{base_name}_subset_{i:03d}{file_ext}"
            output_path = os.path.join(output_folder, output_filename)
            
            print(f"创建子集 {i}/{len(char_chunks)}: {output_filename} (包含 {len(chunk)} 个字符)")
            
            if create_font_subset(input_font_path, output_path, chunk):
                success_count += 1
                
                # 计算unicode-range
                cps = [ord(c) for c in chunk]
                ranges = codepoints_to_unicode_ranges(cps)
                unicode_ranges = ",".join(ranges)
                
                # 上传到CDN并获取CDN URL
                cdn_url = mock_upload_to_cdn(output_path, CDN_CONFIG['base_url'], language)
                
                # 收集子集信息
                subset_info = {
                    'subset_num': i,
                    'char_count': len(chunk),
                    'characters': ''.join(chunk),
                    'unicode_ranges': unicode_ranges,
                    'local_path': output_path,
                    'cdn_url': cdn_url,
                    'language': language
                }
                subset_info_list.append(subset_info)
            else:
                print(f"警告: 创建子集 {i} 失败")
        
        print(f"\n拆分完成! 成功创建 {success_count}/{len(char_chunks)} 个子集字体")
        
        # 生成字符映射文件
        mapping_file = os.path.join(output_folder, f"{base_name}_character_mapping.txt")
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write(f"字体拆分字符映射 - {base_name}\n")
            f.write("=" * 50 + "\n\n")
            
            for subset_info in subset_info_list:
                f.write(f"子集 {subset_info['subset_num']:03d} ({subset_info['char_count']} 个字符):\n")
                f.write(f"字符: {subset_info['characters']}\n")
                f.write("unicode-range: " + subset_info['unicode_ranges'] + ";\n")
                if subset_info['cdn_url']:
                    f.write(f"CDN地址: {subset_info['cdn_url']}\n")
                f.write("-" * 30 + "\n")
        
        print(f"字符映射文件已保存: {mapping_file}")
        
        # 生成CSS文件
        if subset_info_list:
            css_filename = f"{base_name}_{language}.css"
            css_path = os.path.join(output_folder, css_filename)
            
            if generate_css_file(subset_info_list, CDN_CONFIG['base_url'], font_family, css_path):
                print(f"🎉 CSS文件已生成: {css_path}")
                print(f"💡 使用方法: 在HTML中引入此CSS文件，然后设置 font-family: '{font_family}'")
            else:
                print("❌ CSS文件生成失败")
        
        return success_count > 0
        
    except Exception as e:
        print(f"拆分字体时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='字体拆分工具 - 按语言自动选择unicode顺序拆分成多个子集并生成CDN CSS')
    parser.add_argument('input_font', help='输入字体文件路径 (.ttf, .otf)')
    parser.add_argument('-o', '--output', help='输出文件夹路径', default='./splitRes')
    parser.add_argument('-n', '--num-chunks', type=int, help='拆分的块数量（与 --chars-per-chunk 互斥，若同时提供则以 --chars-per-chunk 为准）', default=200)
    parser.add_argument('--chars-per-chunk', type=int, help='每个子集的最大字符数（优先于 --num-chunks 计算实际块数）')
    parser.add_argument('--character-list-file', action='append', required=False, help='从纯字符列表文件读取字符顺序（可多次提供）')
    parser.add_argument('--include-blocks', nargs='*', default=[], help='预设块：jp-basic, tc-basic 等，可多选')
    parser.add_argument('--auto-order-from-corpus', nargs='*', help='从文本语料自动构建字符频率顺序（追加到末尾）')
    parser.add_argument('--language', choices=['zh','ja','tc'], required=True, help='语言类型：zh(简中), ja(日文), tc(繁体)')
    
    # 字体相关参数
    parser.add_argument('--font-family', help='字体族名称', default='有爱魔兽圆体-M')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input_font):
        print(f"错误: 输入字体文件不存在: {args.input_font}")
        sys.exit(1)
    
    # 根据语言自动选择unicode文件
    lang = args.language
    preferred_order_chars: List[str] = []
    
    # 自动读取对应语言的unicode文件
    unicode_file = LANGUAGE_UNICODE_MAP[lang]
    if os.path.exists(unicode_file):
        print(f"自动读取 {lang} 语言的字符顺序文件: {unicode_file}")
        chars = parse_unicode_order_file(unicode_file)
        preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
    else:
        print(f"警告: 找不到 {lang} 语言的unicode文件: {unicode_file}")
        # 使用预设块作为备用
        if lang == 'ja':
            chars = expand_unicode_ranges_to_chars(PRESET_BLOCKS['jp-basic'])
            preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        elif lang == 'tc':
            chars = expand_unicode_ranges_to_chars(PRESET_BLOCKS['tc-basic'])
            preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
    
    # 可选：添加额外的字符列表文件
    if args.character_list_file:
        for p in args.character_list_file:
            print(f"读取额外字符列表文件: {p}")
            chars = load_character_list_file(p)
            preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
    
    # 可选：添加预设块
    if args.include_blocks:
        for key in args.include_blocks:
            if key not in PRESET_BLOCKS:
                print(f"警告: 未知预设块 {key}")
                continue
            block_ranges = PRESET_BLOCKS[key]
            chars = expand_unicode_ranges_to_chars(block_ranges)
            preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
    
    # 可选：从语料构建频率顺序
    if args.auto_order_from_corpus:
        auto_chars = build_order_from_corpus(args.auto_order_from_corpus)
        preferred_order_chars = merge_orders_keep_first(auto_chars, preferred_order_chars)
    
    print(f"聚合后的顺序字符数: {len(preferred_order_chars)}")

    # 执行拆分（若仍为空，提示错误）
    if not preferred_order_chars:
        print(f"错误: 无法为 {lang} 语言构建字符顺序。请检查对应的unicode文件是否存在。")
        sys.exit(1)

    # 执行拆分
    # 根据语言加一层目录
    effective_output = os.path.join(args.output, args.language)
    os.makedirs(effective_output, exist_ok=True)

    print(f"开始拆分字体: {args.input_font}")
    print(f"输出文件夹: {effective_output}")
    if args.chars_per_chunk and args.chars_per_chunk > 0:
        print(f"按每块最多 {args.chars_per_chunk} 个字符计算块数")
    else:
        print(f"拆分数量: {args.num_chunks}")
    
    # CDN配置信息
    print(f"CDN基础地址: {CDN_CONFIG['base_url']}")
    print("📤 将自动上传字体文件到CDN并生成CSS")
    
    print("-" * 50)
    start_time = time.time()
    success = split_font(
        args.input_font,
        effective_output,
        args.num_chunks,
        preferred_order=preferred_order_chars,
        chars_per_chunk=args.chars_per_chunk,
        font_family=args.font_family,
        language=args.language
    )
    total_seconds = time.time() - start_time
    
    if success:
        print("\n✅ 字体拆分完成!")
        print(f"总耗时: {total_seconds:.2f} 秒 (~{total_seconds/60:.2f} 分钟)")
        
        print("\n🎉 字体已上传到CDN，CSS文件已生成!")
        print("💡 使用方法:")
        print(f"   1. 在HTML中引入生成的CSS文件")
        print(f"   2. 设置 font-family: '{args.font_family}'")
    else:
        print("\n❌ 字体拆分失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()
