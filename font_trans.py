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

    def select_input_file(self):
        try:
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG
            )
            if result and result[0]:
                # 手动检查文件扩展名
                if result[0].lower().endswith(('.ttf', '.otf')):
                    return result[0]
                else:
                    print("请选择 .ttf 或 .otf 格式的字体文件")
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

    def analyze_font_characters(self, font_path: str) -> List[str]:
        """分析字体文件中包含的字符"""
        try:
            font = TTFont(font_path)
            available_chars = []
            
            if 'cmap' in font:
                for table in font['cmap'].tables:
                    if hasattr(table, 'cmap'):
                        for unicode_val, glyph_name in table.cmap.items():
                            if unicode_val > 0:
                                char = chr(unicode_val)
                                available_chars.append(char)
            
            return list(set(available_chars))
        except Exception as e:
            print(f"分析字体字符时出错: {e}")
            return []

    def filter_available_chars(self, font_chars: List[str], ordered_chars: List[str]) -> List[str]:
        """根据外部顺序与字体实际可用字符做有序交集"""
        font_char_set = set(font_chars)
        return [c for c in ordered_chars if c in font_char_set]

    def split_characters_into_chunks(self, chars: List[str], num_chunks: int) -> List[List[str]]:
        """将字符列表分割成指定数量的块"""
        if num_chunks <= 0:
            raise ValueError("块数量必须大于0")
        
        if num_chunks >= len(chars):
            return [[char] for char in chars]

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
        
        while chunks and not chunks[-1]:
            chunks.pop()
        return chunks

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

    def upload_to_cdn(self, font_file_path: str, language: str) -> str:
        """
        通过前端JavaScript调用momo包上传字体文件到CDN
        """
        try:
            # 生成文件名hash，避免重名
            with open(font_file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]
            
            filename = os.path.basename(font_file_path)
            name, ext = os.path.splitext(filename)
            cdn_filename = f"{name}_{file_hash}{ext}"
            
            print(f"🔍 调试信息:")
            print(f"  - 文件路径: {font_file_path}")
            print(f"  - 语言: {language}")
            print(f"  - CDN文件名: {cdn_filename}")
            
            # 调用前端JavaScript函数进行上传
            js_code = f"""
            uploadToCDN('{font_file_path}', '{cdn_filename}', '{language}')
            """
            
            print(f"🔍 执行JavaScript代码: {js_code}")
            
            # 通过webview执行JavaScript
            result = self.window.evaluate_js(js_code)
            
            print(f"🔍 JavaScript返回结果: {result}")
            print(f"🔍 结果类型: {type(result)}")
            
            if result and result.startswith('http'):
                cdn_url = result
                print(f"📤 momo上传成功: {font_file_path} -> {cdn_url}")
                return cdn_url
            else:
                raise Exception(f"momo上传失败：未返回有效URL，返回结果: {result}")
                
        except Exception as e:
            print(f"📤 momo上传失败: {e}")
            print(f"🔍 异常详情: {str(e)}")
            # 回退到Mock URL
            cdn_url = f"https://your-company-cdn.com/fonts/{language}/{cdn_filename}"
            print(f"📤 使用Mock URL: {cdn_url}")
            return cdn_url

    def generate_css_file(self, subset_info_list: List[Dict], font_family: str, output_css_path: str) -> bool:
        """生成包含CDN地址的CSS文件"""
        try:
            css_rules = []
            
            # 添加文件头注释
            header = f"""/* 
 * 字体CSS文件 - {font_family}
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 包含 {len(subset_info_list)} 个字体子集
 */

"""
            
            for subset_info in subset_info_list:
                subset_num = subset_info['subset_num']
                unicode_ranges = subset_info['unicode_ranges']
                cdn_url = subset_info['cdn_url']
                
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
            
            return True
            
        except Exception as e:
            print(f"生成CSS文件时出错: {e}")
            return False

    def split_font_and_generate_css(self, input_font_path: str, font_family: str, language: str, num_chunks: int = 200, output_folder: str = None):
        """
        拆分字体并生成CSS文件
        
        参数:
        - input_font_path: 输入字体文件路径
        - font_family: 字体族名称
        - language: 语言类型 (zh, ja, tc)
        - num_chunks: 拆分的块数量
        - output_folder: 输出文件夹路径
        
        返回:
        - dict: 包含成功状态、CSS文件路径等信息
        """
        try:
            if not os.path.exists(input_font_path):
                return {"success": False, "message": "输入字体文件不存在"}

            # 设置输出文件夹
            if not output_folder:
                output_folder = os.path.dirname(input_font_path)
            
            # 创建语言子目录
            lang_output_folder = os.path.join(output_folder, language)
            os.makedirs(lang_output_folder, exist_ok=True)

            print(f"开始拆分字体: {input_font_path}")
            print(f"输出文件夹: {lang_output_folder}")

            # 分析字体中的字符
            font_chars = self.analyze_font_characters(input_font_path)
            print(f"字体中包含 {len(font_chars)} 个字符")
            if len(font_chars) == 0:
                return {"success": False, "message": "字体文件中没有找到任何字符"}

            # 读取对应语言的unicode文件
            unicode_file = LANGUAGE_UNICODE_MAP[language]
            unicode_file_path = get_resource_path(unicode_file)
            if not os.path.exists(unicode_file_path):
                return {"success": False, "message": f"找不到 {language} 语言的unicode文件: {unicode_file_path}"}

            print(f"自动读取 {language} 语言的字符顺序文件: {unicode_file_path}")
            ordered_chars = self.parse_unicode_order_file(unicode_file_path)
            print(f"unicode文件中包含 {len(ordered_chars)} 个字符")
            
            # 过滤可用字符并按外部顺序排序
            available_chars = self.filter_available_chars(font_chars, ordered_chars)
            print(f"按频率排序的可用字符: {len(available_chars)} 个")
            
            if len(available_chars) == 0:
                return {"success": False, "message": f"字体中没有找到 {language} 语言的字符"}

            # 分割字符
            char_chunks = self.split_characters_into_chunks(available_chars, num_chunks)
            print(f"将字符分割成 {len(char_chunks)} 个块")

            # 获取基础文件名
            base_name = os.path.splitext(os.path.basename(input_font_path))[0]
            file_ext = os.path.splitext(input_font_path)[1]

            # 创建子集字体并收集信息
            success_count = 0
            subset_info_list = []

            for i, chunk in enumerate(char_chunks, 1):
                output_filename = f"{base_name}_subset_{i:03d}{file_ext}"
                output_path = os.path.join(lang_output_folder, output_filename)

                print(f"创建子集 {i}/{len(char_chunks)}: {output_filename} (包含 {len(chunk)} 个字符)")

                if self.create_font_subset(input_font_path, output_path, chunk):
                    success_count += 1

                    # 计算unicode-range
                    cps = [ord(c) for c in chunk]
                    ranges = self.codepoints_to_unicode_ranges(cps)
                    unicode_ranges = ",".join(ranges)

                    # 上传到CDN
                    cdn_url = self.upload_to_cdn(output_path, language)

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

            print(f"拆分完成! 成功创建 {success_count}/{len(char_chunks)} 个子集字体")

            # 生成CSS文件
            css_filename = f"{base_name}_{language}.css"
            css_path = os.path.join(lang_output_folder, css_filename)

            if self.generate_css_file(subset_info_list, font_family, css_path):
                print(f"🎉 CSS文件已生成: {css_path}")
                return {
                    "success": True,
                    "message": f"成功创建 {success_count} 个子集字体并生成CSS文件",
                    "css_path": css_path,
                    "subset_count": success_count,
                    "output_folder": lang_output_folder
                }
            else:
                return {"success": False, "message": "CSS文件生成失败"}

        except Exception as e:
            return {"success": False, "message": f"拆分字体时出错: {str(e)}"}

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
                if subset_chars:
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
    webview.start(debug=True)

if __name__ == "__main__":
    main()