import os
import sys
import webview
import json
import hashlib
import re
import math
from fontTools import subset
from fontTools.ttLib import TTFont
import time
from typing import List, Dict, Optional
from datetime import datetime
import io
import tempfile
import traceback

def convert_ttf_to_woff2_core(input_ttf_path, output_woff2_path=None, subset_chars=None, weight_value=None):
    """将 TTF/OTF 转为 WOFF2，可选子集与字重实例化。返回 (success, message, final_path, time_seconds)"""
    if not os.path.exists(input_ttf_path):
        return False, f"错误: 输入文件不存在 - {input_ttf_path}", None, 0
    if not input_ttf_path.lower().endswith((".ttf", ".otf")):
        return False, f"错误: 输入文件 '{input_ttf_path}' 不是 TTF 或 OTF 格式。", None, 0

    # 确保输出目录存在
    if output_woff2_path:
        output_dir = os.path.dirname(output_woff2_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError as e:
                return False, f"错误: 无法创建输出目录 '{output_dir}': {e}", None, 0

    try:
        from fontTools import subset as ft_subset
        from fontTools.ttLib import TTFont as FT_TTFont
        from fontTools.varLib.instancer import instantiateVariableFont

        font_for_subset = input_ttf_path
        temp_font_path = None

        # 可变字体字重实例化
        if weight_value is not None and str(weight_value).isdigit():
            weight_value = int(weight_value)
            with FT_TTFont(input_ttf_path) as font_check:
                if 'fvar' in font_check:
                    wght_axis = [a for a in font_check['fvar'].axes if a.axisTag == 'wght']
                    if wght_axis:
                        min_w = int(wght_axis[0].minValue)
                        max_w = int(wght_axis[0].maxValue)
                        if not (min_w <= weight_value <= max_w):
                            return False, f"字重 {weight_value} 超出字体支持范围（{min_w}~{max_w}），请重新选择。", None, 0
                        temp_font = instantiateVariableFont(font_check, {'wght': weight_value}, inplace=False)
                        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmpf:
                            temp_font.save(tmpf.name)
                            font_for_subset = tmpf.name
                            temp_font_path = tmpf.name

        start_time = time.time()
        font = FT_TTFont(font_for_subset)

        # 子集化
        if subset_chars and subset_chars.strip():
            sub = ft_subset.Subsetter()
            sub.populate(text=subset_chars)
            sub.subset(font)

        font.flavor = 'woff2'
        final_path = output_woff2_path or os.path.splitext(input_ttf_path)[0] + '.woff2'
        font.save(final_path)
        conversion_time = time.time() - start_time

        message = f"✓ {os.path.basename(input_ttf_path)} 转换成功"
        if weight_value is not None:
            message += f" (字重:{weight_value})"
        message += f" - 耗时: {conversion_time:.2f}秒"
        return True, message, final_path, conversion_time

    except Exception as e:
        return False, f"字体转换时发生错误: {e}\n{traceback.format_exc()}", None, 0
    finally:
        if 'temp_font_path' in locals() and temp_font_path and os.path.exists(temp_font_path):
            try:
                os.remove(temp_font_path)
            except Exception:
                pass


def convert_ttf_to_woff_core(input_ttf_path, output_woff_path=None, subset_chars=None, weight_value=None):
    """将 TTF/OTF 转为 WOFF，可选子集与字重实例化。返回 (success, message, final_path, time_seconds)"""
    if not os.path.exists(input_ttf_path):
        return False, f"错误: 输入文件不存在 - {input_ttf_path}", None, 0
    if not input_ttf_path.lower().endswith((".ttf", ".otf")):
        return False, f"错误: 输入文件 '{input_ttf_path}' 不是 TTF 或 OTF 格式。", None, 0

    if output_woff_path:
        output_dir = os.path.dirname(output_woff_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError as e:
                return False, f"错误: 无法创建输出目录 '{output_dir}': {e}", None, 0

    try:
        from fontTools import subset as ft_subset
        from fontTools.ttLib import TTFont as FT_TTFont
        from fontTools.varLib.instancer import instantiateVariableFont

        font_for_subset = input_ttf_path
        temp_font_path = None

        if weight_value is not None and str(weight_value).isdigit():
            weight_value = int(weight_value)
            with FT_TTFont(input_ttf_path) as font_check:
                if 'fvar' in font_check:
                    wght_axis = [a for a in font_check['fvar'].axes if a.axisTag == 'wght']
                    if wght_axis:
                        min_w = int(wght_axis[0].minValue)
                        max_w = int(wght_axis[0].maxValue)
                        if not (min_w <= weight_value <= max_w):
                            return False, f"字重 {weight_value} 超出字体支持范围（{min_w}~{max_w}），请重新选择。", None, 0
                        temp_font = instantiateVariableFont(font_check, {'wght': weight_value}, inplace=False)
                        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmpf:
                            temp_font.save(tmpf.name)
                            font_for_subset = tmpf.name
                            temp_font_path = tmpf.name

        start_time = time.time()
        font = FT_TTFont(font_for_subset)

        if subset_chars and subset_chars.strip():
            sub = ft_subset.Subsetter()
            sub.populate(text=subset_chars)
            sub.subset(font)

        font.flavor = 'woff'
        final_path = output_woff_path or os.path.splitext(input_ttf_path)[0] + '.woff'
        font.save(final_path)
        conversion_time = time.time() - start_time

        message = f"✓ {os.path.basename(input_ttf_path)} 转换成功"
        if weight_value is not None:
            message += f" (字重:{weight_value})"
        message += f" - 耗时: {conversion_time:.2f}秒"
        return True, message, final_path, conversion_time

    except Exception as e:
        return False, f"字体转换时发生错误: {e}\n{traceback.format_exc()}", None, 0
    finally:
        if 'temp_font_path' in locals() and temp_font_path and os.path.exists(temp_font_path):
            try:
                os.remove(temp_font_path)
            except Exception:
                pass

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# 语言到unicode文件的映射
LANGUAGE_UNICODE_MAP = {
    'zh': 'unicode-zh-CN.txt',  # 简体中文
    'ja': 'unicode-ja.txt',     # 日文
    'tc': 'unicode-zh-TW.txt',  # 繁体中文
}

class FontConverterAPI:
    def __init__(self):
        self.window = None
        self.current_progress = {
            'step': '',
            'message': '',
            'percent': 0,
            'details': {},
            'is_running': False,
            'current': 0,
            'total': 0,
            'elapsed_time': '',
            'remaining_time': ''
        }

    def select_input_file(self):
        try:
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG
            )
            if result and result[0]:
                # 手动检查文件扩展名
                if result[0].lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                    return result[0]
                else:
                    print("请选择 .ttf、.otf、.woff 或 .woff2 格式的字体文件")
                    return None
            return None
        except Exception as e:
            print(f"选择文件错误: {e}")
            return None

    def select_output_folder(self):
        try:
            result = self.window.create_file_dialog(
                webview.FOLDER_DIALOG
            )
            return result[0] if result else None
        except Exception as e:
            print(f"选择文件夹错误: {e}")
            return None

    def get_progress(self):
        """获取当前进度状态"""
        return self.current_progress.copy()

    def update_progress(self, **kwargs):
        """更新进度状态"""
        self.current_progress.update(kwargs)

    def get_font_weights(self, font_path):
        try:
            font = TTFont(font_path)
            if 'fvar' in font:
                for axis in font['fvar'].axes:
                    if axis.axisTag == 'wght':
                        min_w = int(axis.minValue)
                        max_w = int(axis.maxValue)
                        default_w = int(axis.defaultValue)
                        weights = sorted(list(set([
                            min_w, 100, 200, 300, 400, 500, 600, 700, 800, 900, max_w, default_w
                        ])))
                        return [w for w in weights if min_w <= w <= max_w]
            return []
        except Exception as e:
            print(f"获取字重错误: {e}")
            return []

    def parse_unicode_ranges_from_text(self, text: str) -> List[int]:
        """从文本中解析unicode范围"""
        codepoints: List[int] = []
        seen = set()
        for m in re.finditer(r"unicode-range\s*:\s*([^;]+);", text, flags=re.IGNORECASE):
            ranges_part = m.group(1)
            ranges_part = re.sub(r"/\*.*?\*/", "", ranges_part, flags=re.DOTALL)
            for item in ranges_part.split(','):
                token = item.strip()
                if not token:
                    continue
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

    def parse_unicode_order_file(self, file_path: str) -> List[str]:
        """从unicode配置文件中解析出按出现顺序排列的 Unicode"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            cps = self.parse_unicode_ranges_from_text(content)
            chars: List[str] = []
            for cp in cps:
                try:
                    chars.append(chr(cp))
                except Exception:
                    pass
            return chars
        except Exception as e:
            print(f"读取或解析 unicode 顺序文件失败: {e}")
            return []



    def create_font_subset(self, input_font_path: str, output_path: str, chars: List[str]) -> bool:
        """创建字体子集"""
        try:
            font = TTFont(input_font_path)
            subsetter = subset.Subsetter()
            char_text = ''.join(chars)
            subsetter.populate(text=char_text)
            subsetter.subset(font)
            font.save(output_path)
            return True
        except Exception as e:
            print(f"创建字体子集时出错: {e}")
            return False

    def codepoints_to_unicode_ranges(self, codepoints: List[int]) -> List[str]:
        """将已排序的码点列表压缩为 CSS unicode-range 片段列表"""
        if not codepoints:
            return []
        cps = list(codepoints)
        ranges: List[str] = []
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


    def generate_src_from_urls(self, url_map: Dict[str, str]) -> str:
        """根据已上传的各格式URL生成src，按兼容性优先级排序"""
        order = [
            ('woff2', 'woff2'),
            ('woff', 'woff'),
            ('ttf', 'truetype'),
            ('eot', 'embedded-opentype'),
        ]
        parts: List[str] = []
        for ext, fmt in order:
            url = url_map.get(ext)
            if url:
                parts.append(f'url("{url}") format("{fmt}")')
        return ','.join(parts)



    def start_conversion(self, input_path, subset_chars=None, weights=None, output_folder=None, output_formats=None):
        """
        开始字体转换和子集化
        
        参数:
        - input_path: 输入字体文件路径
        - subset_chars: 需要保留的字符字符串
        - weights: 需要转换的字重列表
        - output_folder: 输出文件夹路径
        - output_formats: 输出格式列表 (e.g., ['woff2', 'woff'])
        """
        try:
            if not input_path or not os.path.exists(input_path):
                return {"success": False, "message": "输入文件不存在"}

            if not output_formats:
                output_formats = ['woff2']  # 默认格式

            start_time = time.time()
            converted_paths = []
            weights = weights or [None]

            for weight in weights:
                # 每次循环都创建一个新的字体对象副本，以避免状态冲突
                font_to_convert = TTFont(input_path)

                # 1. 处理字重（如果是可变字体）
                if weight and 'fvar' in font_to_convert:
                    from fontTools.varLib.instancer import instantiateVariableFont
                    font_to_convert = instantiateVariableFont(font_to_convert, {'wght': float(weight)})
                
                # 2. 进行子集化处理
                if subset_chars and subset_chars.strip():
                    print(f"Received subset_chars: '{subset_chars}'")
                    # 创建子集化器
                    subsetter = subset.Subsetter()
                    # 填充要保留的字符
                    subsetter.populate(text=subset_chars)
                    # 对字体进行子集化操作，这会直接修改 `font_to_convert` 对象
                    subsetter.subset(font_to_convert)

                # 3. 为每种格式生成文件
                for format in output_formats:
                    # 确定输出文件名
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    weight_suffix = f"_w{weight}" if weight else ""
                    output_name = f"{base_name}{weight_suffix}.{format}"
                    output_path = os.path.join(output_folder or os.path.dirname(input_path), output_name)

                    # 根据格式设置 flavor
                    if format in ['woff', 'woff2']:
                        font_to_convert.flavor = format
                    
                    # 4. 保存经过子集化和格式处理的字体
                    font_to_convert.save(output_path)
                    converted_paths.append(output_path)

            total_time = time.time() - start_time
            return {
                "success": True,
                "paths": converted_paths,
                "total_time_seconds": total_time
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"转换过程中发生错误: {str(e)}"
            }
def main():
    try:
        import brotli
    except ImportError:
        try:
            import brotlicffi as brotli
        except ImportError:
            print("错误: 缺少 'brotli' 或 'brotlicffi' 库！")
            print("请运行: pip install brotli 或 pip install brotlicffi")
            sys.exit(1)

    # 获取HTML文件路径
    html_path = get_resource_path('index.html')
    if not os.path.exists(html_path):
        print(f"错误: 找不到index.html，路径: {html_path}")
        sys.exit(1)

    # 创建API实例
    api = FontConverterAPI()

    # 创建窗口
    window = webview.create_window(
        '字体拆分和转换工具',
        html_path,
        js_api=api,
        width=1000,
        height=1000,
        min_size=(900, 700)
    )
    api.window = window

    # 启动应用
    webview.start()

if __name__ == "__main__":
    main()