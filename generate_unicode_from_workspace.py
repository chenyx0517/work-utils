#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from typing import List, Dict, Set

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

TEXT_EXTS = {
    '.txt', '.md', '.html', '.htm', '.css', '.js', '.ts', '.tsx', '.jsx',
    '.json', '.yml', '.yaml', '.py', '.mdx'
}

EXCLUDED_DIRS = {
    'build', 'dist', 'release', '__pycache__', 'node_modules', '.git', '.venv', '.mypy_cache'
}

# Language block predicates
def in_ranges(cp: int, ranges: List[range]) -> bool:
    return any(cp in r for r in ranges)

RANGES_COMMON = [
    range(0x3000, 0x3040),   # CJK Symbols and Punctuation
    range(0xFE10, 0xFE20),   # Vertical Forms
    range(0xFE30, 0xFE50),   # CJK Compatibility Forms
    range(0x16FE0, 0x17000), # Ideographic Symbols and Punctuation
    range(0xFF00, 0xFFF0),   # Halfwidth and Fullwidth Forms
]

RANGES_CJK_CORE = [
    range(0x3400, 0x4DC0),   # Ext A
    range(0x4E00, 0xA000),   # Unified
    range(0xF900, 0xFB00),   # Compatibility Ideographs
    range(0x2F800, 0x2FA20), # Compatibility Ideographs Supplement
    range(0x20000, 0x2A6E0), # Ext B
    range(0x2A700, 0x2B740), # Ext C
    range(0x2B740, 0x2B820), # Ext D
    range(0x2B820, 0x2CEB0), # Ext E
    range(0x2CEB0, 0x2EBF0), # Ext F
    range(0x30000, 0x31350), # Ext G
]

RANGES_JA_ONLY = [
    range(0x3040, 0x30A0),   # Hiragana
    range(0x30A0, 0x3100),   # Katakana
    range(0x31F0, 0x3200),   # Katakana Phonetic Extensions
    range(0x1B000, 0x1B100), # Kana Supplement
    range(0x1B100, 0x1B130), # Kana/Hiragana Extended-A
    range(0x1B130, 0x1B170), # Small Kana Extension
    range(0x1AFF0, 0x1B000), # Kana Extended-B
    range(0xFF66, 0xFFA0),   # Halfwidth Katakana
]

RANGES_ZH_TW_ONLY = [
    range(0x3100, 0x3130),   # Bopomofo
    range(0x31A0, 0x31C0),   # Bopomofo Extended
]

def collect_texts(root: str) -> List[str]:
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTS:
                files.append(os.path.join(dirpath, name))
    return files

def build_frequency_order(paths: List[str]) -> List[str]:
    counts: Dict[str, int] = {}
    first_index: Dict[str, int] = {}
    cursor = 0
    for p in paths:
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for ch in f.read():
                    if ord(ch) <= 0x1F:
                        continue
                    counts[ch] = counts.get(ch, 0) + 1
                    if ch not in first_index:
                        first_index[ch] = cursor
                    cursor += 1
        except Exception:
            pass
    ordered = sorted(counts.keys(), key=lambda c: (-counts[c], first_index[c]))
    return ordered

def compress_to_unicode_ranges(chars: List[str]) -> List[str]:
    if not chars:
        return []
    cps = [ord(c) for c in chars]
    # Do not sort; keep input order. Compress only consecutive codepoints.
    ranges = []
    start = cps[0]
    prev = cps[0]
    for cp in cps[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        if start == prev:
            ranges.append(f"U+{start:x}")
        else:
            ranges.append(f"U+{start:x}-{prev:x}")
        start = prev = cp
    if start == prev:
        ranges.append(f"U+{start:x}")
    else:
        ranges.append(f"U+{start:x}-{prev:x}")
    return ranges

def fill_long_tail(ordered_chars: List[str], allow_pred) -> List[str]:
    seen: Set[str] = set(ordered_chars)
    # Iterate through allowed ranges by codepoint order
    additions: List[str] = []
    all_ranges = RANGES_COMMON + RANGES_CJK_CORE
    # allow_pred should already include language-specific ranges
    # We iterate a safe superset; allow_pred will filter
    for r in all_ranges:
        for cp in r:
            ch = chr(cp)
            if ch not in seen and allow_pred(cp):
                additions.append(ch)
                seen.add(ch)
    return ordered_chars + additions

def write_face(path: str, family: str, ranges: List[str]):
    content = (
        "@font-face {\n"
        f"  font-family: {family};\n"
        "  font-weight: 400;\n"
        "  font-display: swap;\n"
        "  unicode-range: " + ",\n    ".join(ranges) + ";\n"
        "}\n"
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    files = collect_texts(WORKSPACE)
    freq_chars = build_frequency_order(files)

    # JA
    def allow_ja(cp: int) -> bool:
        return in_ranges(cp, RANGES_COMMON + RANGES_JA_ONLY + RANGES_CJK_CORE)
    ja_chars = [c for c in freq_chars if allow_ja(ord(c))]
    ja_chars = fill_long_tail(ja_chars, allow_ja)
    ja_ranges = compress_to_unicode_ranges(ja_chars)
    write_face(os.path.join(WORKSPACE, 'unicode-ja.txt'), 'Japanese Frequency Order', ja_ranges)

    # ZH-TW
    def allow_zh_tw(cp: int) -> bool:
        return in_ranges(cp, RANGES_COMMON + RANGES_ZH_TW_ONLY + RANGES_CJK_CORE)
    tw_chars = [c for c in freq_chars if allow_zh_tw(ord(c))]
    tw_chars = fill_long_tail(tw_chars, allow_zh_tw)
    tw_ranges = compress_to_unicode_ranges(tw_chars)
    write_face(os.path.join(WORKSPACE, 'unicode-zh-TW.txt'), 'Traditional Chinese Frequency Order', tw_ranges)

    # ZH-CN
    def allow_zh_cn(cp: int) -> bool:
        return in_ranges(cp, RANGES_COMMON + RANGES_CJK_CORE)
    cn_chars = [c for c in freq_chars if allow_zh_cn(ord(c))]
    cn_chars = fill_long_tail(cn_chars, allow_zh_cn)
    cn_ranges = compress_to_unicode_ranges(cn_chars)
    write_face(os.path.join(WORKSPACE, 'unicode-zh-CN.txt'), 'Simplified Chinese Frequency Order', cn_ranges)

if __name__ == '__main__':
    main()


