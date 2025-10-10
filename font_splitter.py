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
from fontTools import subset
from fontTools.ttLib import TTFont
import argparse
from typing import List, Tuple, Iterable, Dict

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

def split_font(input_font_path: str, output_folder: str, num_chunks: int = 200, preferred_order: List[str] = None, chars_per_chunk: int | None = None) -> bool:
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
        
        # 创建子集字体
        success_count = 0
        for i, chunk in enumerate(char_chunks, 1):
            output_filename = f"{base_name}_subset_{i:03d}{file_ext}"
            output_path = os.path.join(output_folder, output_filename)
            
            print(f"创建子集 {i}/{len(char_chunks)}: {output_filename} (包含 {len(chunk)} 个字符)")
            
            if create_font_subset(input_font_path, output_path, chunk):
                success_count += 1
            else:
                print(f"警告: 创建子集 {i} 失败")
        
        print(f"\n拆分完成! 成功创建 {success_count}/{len(char_chunks)} 个子集字体")
        
        # 生成字符映射文件
        mapping_file = os.path.join(output_folder, f"{base_name}_character_mapping.txt")
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write(f"字体拆分字符映射 - {base_name}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, chunk in enumerate(char_chunks, 1):
                f.write(f"子集 {i:03d} ({len(chunk)} 个字符):\n")
                f.write(f"字符: {''.join(chunk)}\n")
                # 计算并写出与外部文件一致风格（小写、不加空格、逗号分隔）的 unicode-range 表达
                cps = [ord(c) for c in chunk]
                ranges = codepoints_to_unicode_ranges(cps)
                f.write("unicode-range: " + ",".join(ranges) + ";\n")
                f.write("-" * 30 + "\n")
        
        print(f"字符映射文件已保存: {mapping_file}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"拆分字体时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='字体拆分工具 - 按外部提供的 unicode 顺序拆分成多个子集')
    parser.add_argument('input_font', help='输入字体文件路径 (.ttf, .otf)')
    parser.add_argument('-o', '--output', help='输出文件夹路径', default='./splitRes')
    parser.add_argument('-n', '--num-chunks', type=int, help='拆分的块数量（与 --chars-per-chunk 互斥，若同时提供则以 --chars-per-chunk 为准）', default=200)
    parser.add_argument('--chars-per-chunk', type=int, help='每个子集的最大字符数（优先于 --num-chunks 计算实际块数）')
    parser.add_argument('--unicode-order-file', action='append', required=False, help='从包含 unicode-range 的文件读取字符顺序（可多次提供）')
    parser.add_argument('--character-list-file', action='append', required=False, help='从纯字符列表文件读取字符顺序（可多次提供）')
    parser.add_argument('--include-blocks', nargs='*', default=[], help='预设块：jp-basic, tc-basic 等，可多选')
    parser.add_argument('--auto-order-from-corpus', nargs='*', help='从文本语料自动构建字符频率顺序（追加到末尾）')
    parser.add_argument('--language', choices=['zh','ja','tc'], help='限定语言：zh(简中), ja(日文), tc(繁体)。提供后仅构建该语言的顺序，不与其他语言合并。')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input_font):
        print(f"错误: 输入字体文件不存在: {args.input_font}")
        sys.exit(1)
    
    # 如果提供了顺序文件，解析字符顺序
    preferred_order_chars: List[str] = []
    # 语言模式：若指定 language，则仅依据该语言相关来源生成顺序
    if args.language:
        lang = args.language
        if lang == 'zh':
            # 简中：依赖外部顺序文件（你已有），否则仅用字体交集（等同空顺序会报错）
            if args.unicode_order_file:
                for p in args.unicode_order_file:
                    print(f"读取外部字符顺序文件: {p}")
                    chars = parse_unicode_order_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
            if args.character_list_file:
                for p in args.character_list_file:
                    print(f"读取字符列表文件: {p}")
                    chars = load_character_list_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        elif lang == 'ja':
            # 日文：允许外部文件；若未提供则使用 jp-basic 预设；可叠加语料
            if args.unicode_order_file:
                for p in args.unicode_order_file:
                    print(f"读取外部字符顺序文件: {p}")
                    chars = parse_unicode_order_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
            if args.character_list_file:
                for p in args.character_list_file:
                    print(f"读取字符列表文件: {p}")
                    chars = load_character_list_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
            if not args.unicode_order_file and not args.character_list_file:
                chars = expand_unicode_ranges_to_chars(PRESET_BLOCKS['jp-basic'])
                preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        elif lang == 'tc':
            # 繁体：允许外部文件；若未提供则使用 tc-basic 预设；可叠加语料
            if args.unicode_order_file:
                for p in args.unicode_order_file:
                    print(f"读取外部字符顺序文件: {p}")
                    chars = parse_unicode_order_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
            if args.character_list_file:
                for p in args.character_list_file:
                    print(f"读取字符列表文件: {p}")
                    chars = load_character_list_file(p)
                    preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
            if not args.unicode_order_file and not args.character_list_file:
                chars = expand_unicode_ranges_to_chars(PRESET_BLOCKS['tc-basic'])
                preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        # 语料可选追加（频率优先）：若提供语料，则以语料频率顺序为主，其他来源为辅
        if args.auto_order_from_corpus:
            auto_chars = build_order_from_corpus(args.auto_order_from_corpus)
            preferred_order_chars = merge_orders_keep_first(auto_chars, preferred_order_chars)
    else:
        # 未指定语言：按原有逻辑，将所有来源合并
        if args.unicode_order_file:
            for p in args.unicode_order_file:
                print(f"读取外部字符顺序文件: {p}")
                chars = parse_unicode_order_file(p)
                preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        if args.character_list_file:
            for p in args.character_list_file:
                print(f"读取字符列表文件: {p}")
                chars = load_character_list_file(p)
                preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        if args.include_blocks:
            for key in args.include_blocks:
                if key not in PRESET_BLOCKS:
                    print(f"警告: 未知预设块 {key}")
                    continue
                block_ranges = PRESET_BLOCKS[key]
                chars = expand_unicode_ranges_to_chars(block_ranges)
                preferred_order_chars = merge_orders_keep_first(preferred_order_chars, chars)
        # 语料可选追加（频率优先）：若提供语料，则以语料频率顺序为主，其他来源为辅
        if args.auto_order_from_corpus:
            auto_chars = build_order_from_corpus(args.auto_order_from_corpus)
            preferred_order_chars = merge_orders_keep_first(auto_chars, preferred_order_chars)
    print(f"聚合后的顺序字符数: {len(preferred_order_chars)}")

    # 执行拆分（若仍为空，提示必须至少提供一种顺序来源）
    if not preferred_order_chars:
        print("错误: 未提供任何字符顺序来源。请使用 --unicode-order-file 或 --include-blocks 或 --auto-order-from-corpus")
        sys.exit(1)

    # 执行拆分
    # 根据语言加一层目录
    effective_output = os.path.join(args.output, args.language) if args.language else os.path.join(args.output, 'mixed')
    os.makedirs(effective_output, exist_ok=True)

    print(f"开始拆分字体: {args.input_font}")
    print(f"输出文件夹: {effective_output}")
    if args.chars_per_chunk and args.chars_per_chunk > 0:
        print(f"按每块最多 {args.chars_per_chunk} 个字符计算块数")
    else:
        print(f"拆分数量: {args.num_chunks}")
    print("-" * 50)
    start_time = time.time()
    success = split_font(
        args.input_font,
        effective_output,
        args.num_chunks,
        preferred_order=preferred_order_chars,
        chars_per_chunk=args.chars_per_chunk,
    )
    total_seconds = time.time() - start_time
    
    if success:
        print("\n✅ 字体拆分完成!")
        print(f"总耗时: {total_seconds:.2f} 秒 (~{total_seconds/60:.2f} 分钟)")
    else:
        print("\n❌ 字体拆分失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()
