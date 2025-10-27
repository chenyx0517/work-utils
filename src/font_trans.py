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

    def create_font_subset_in_memory(self, input_font_path: str, characters: List[str]) -> bytes:
        """在内存中创建字体子集，返回字体数据"""
        try:
            from fontTools.subset import Subsetter
            from fontTools.ttLib import TTFont
            
            # 加载字体
            font = TTFont(input_font_path)
            
            # 创建子集器
            subsetter = Subsetter()
            subsetter.populate(text=''.join(characters))
            subsetter.subset(font)
            
            # 将字体保存到内存
            font_buffer = io.BytesIO()
            font.save(font_buffer)
            font_data = font_buffer.getvalue()
            font_buffer.close()
            
            return font_data
            
        except Exception as e:
            print(f"在内存中创建字体子集时出错: {e}")
            return None

    def convert_subset_bytes_to_formats(self, ttf_bytes: bytes) -> Dict[str, bytes]:
        """将TTF子集字节转换为多种格式(woff2/woff/ttf)，EOT尝试可选"""
        results: Dict[str, bytes] = {}
        results['ttf'] = ttf_bytes

        # 加载到 TTFont
        ttf_buffer = io.BytesIO(ttf_bytes)
        font = TTFont(ttf_buffer)

        # 生成 woff2
        try:
            font.flavor = 'woff2'
            buf = io.BytesIO()
            font.save(buf)
            results['woff2'] = buf.getvalue()
            buf.close()
        except Exception as _:
            pass

        # 生成 woff
        try:
            font.flavor = 'woff'
            buf = io.BytesIO()
            font.save(buf)
            results['woff'] = buf.getvalue()
            buf.close()
        except Exception as _:
            pass

        # 可选：EOT 需要外部工具，若无则跳过
        # if shutil.which('ttf2eot'):
        #     ...
        return results

    def upload_font_data_to_cdn(self, font_data: bytes, filename: str, language: str) -> str:
        """上传字体数据到CDN"""
        try:
            import requests
            import hashlib
            import oss2 
            
            # 生成文件名hash，避免重名
            file_hash = hashlib.md5(font_data).hexdigest()[:8]
            name, ext = os.path.splitext(filename)
            cdn_filename = f"{name}_{file_hash}{ext}"
            
            print(f"🔍 开始上传字体数据:")
            print(f"  - 文件名: {cdn_filename}")
            print(f"  - 语言: {language}")
            print(f"  - 数据大小: {len(font_data)} bytes")
            
            # API 基础地址
            base_url = "https://awe-test.diezhi.net/v2/resources"
            
            # 接口不需要认证信息
            headers = {
                "Content-Type": "application/json",
            }
            
            print(f"✅ 接口无需认证，开始上传流程")
            
            # 计算文件信息
            file_size = len(font_data)
            file_hash = hashlib.md5(font_data).hexdigest()
            file_ext = os.path.splitext(cdn_filename)[1][1:]  # 去掉点号
            
            print(f"🔍 文件信息: {cdn_filename}, 大小: {file_size} bytes, 哈希: {file_hash}")
            
            # ===== 第一步：获取STS临时凭证 =====
            sts_url = f"{base_url}/sts/get"
            sts_data = {
                "client_id": 1065,  # 修改为数字类型
                "path": "activity",   
                "file_type": file_ext, # 添加文件类型
                "file_md5": file_hash,
                "operate_id": "web_fontmin_utils",  
            }
            
            print(f"🔍 第一步：获取STS凭证")
            print(f"🔍 STS URL: {sts_url}")
            print(f"🔍 STS 参数: {sts_data}")
            
            sts_response = requests.post(sts_url, headers=headers, json=sts_data, timeout=30)
            
            print(f"🔍 STS 响应状态码: {sts_response.status_code}")
            print(f"🔍 STS 响应内容: {sts_response.text}")
            
            if sts_response.status_code != 200:
                raise Exception(f"获取STS凭证失败: {sts_response.status_code} - {sts_response.text}")
            
            sts_result = sts_response.json()
            
            # 检查STS响应格式
            if sts_result.get('code') != 0: # 修正检查成功状态
                raise Exception(f"STS请求失败: {sts_result}")
            
            # 提取OSS信息
            oss_data = sts_result.get('data', {})
            bucket = oss_data.get('bucket')
            region = oss_data.get('region')
            access_key_id = oss_data.get('ak_id')  # 修正字段名
            access_key_secret = oss_data.get('ak_secret')  # 修正字段名
            security_token = oss_data.get('sts_token')  # 修正字段名
            upload_path = oss_data.get('bucket_path')  # 使用bucket_path作为上传路径
            resource_id = oss_data.get('resource_id')
            
            if not all([bucket, region, access_key_id, access_key_secret, security_token, upload_path, resource_id]):
                raise Exception(f"STS响应缺少必要信息: {oss_data}")
            
            print(f"✅ 获取STS凭证成功")
            print(f"🔍 OSS信息: bucket={bucket}, region={region}, upload_path={upload_path}")
            
            # ===== 第二步：上传文件到OSS =====
            # 创建OSS客户端
            auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
            # 修正OSS域名格式
            oss_endpoint = f"https://{region}.aliyuncs.com"
            bucket_obj = oss2.Bucket(auth, oss_endpoint, bucket)
            
            # 上传文件
            print(f"🔍 第二步：上传文件到OSS")
            print(f"🔍 上传路径: {upload_path}")
            
            result = bucket_obj.put_object(upload_path, font_data)
            
            if result.status == 200:
                # 构建CDN URL - 使用bucket_domain
                bucket_domain = oss_data.get('bucket_domain', f"{bucket}.oss-{region}.aliyuncs.com")
                cdn_url = f"https://{bucket_domain}/{upload_path}"
                print(f"✅ OSS上传成功: {cdn_url}")
                return cdn_url
            else:
                raise Exception(f"OSS上传失败: {result}")
                
        except ImportError:
            print("⚠️ oss2库未安装，无法直接上传到OSS")
            print("💡 请运行: pip install oss2")
            raise Exception("需要安装oss2库")
                
        except ImportError:
            print("⚠️ requests库未安装，无法使用Python后端上传")
            print("💡 请运行: pip install requests")
            raise Exception("需要安装requests库")
        except Exception as e:
            print(f"❌ Python后端上传失败: {e}")
            raise

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
        上传字体文件到CDN - 直接使用Python后端上传
        
        两步上传流程：
        1. 获取STS临时凭证
        2. 使用临时凭证上传文件到OSS
        3. 保存到素材中心
        """
        try:
            # 生成文件名hash，避免重名
            with open(font_file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()[:8]
            
            filename = os.path.basename(font_file_path)
            name, ext = os.path.splitext(filename)
            cdn_filename = f"{name}_{file_hash}{ext}"
            
            print(f"🔍 开始上传字体文件:")
            print(f"  - 文件路径: {font_file_path}")
            print(f"  - 语言: {language}")
            print(f"  - CDN文件名: {cdn_filename}")
            
            # 直接使用Python后端上传
            return self._upload_via_python_backend(font_file_path, cdn_filename, language)
                
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            print(f"🔍 异常详情: {str(e)}")
            
            # 回退到模拟URL（用于测试）
            cdn_url = f"https://your-actual-cdn-domain.com/fonts/{language}/{cdn_filename}"
            print(f"📤 使用模拟URL: {cdn_url}")
            print(f"💡 提示：要使用真实CDN，请配置认证信息")
            return cdn_url

    def _upload_via_python_backend(self, font_file_path: str, cdn_filename: str, language: str) -> str:
        """
        通过Python后端直接上传到CDN（两步上传流程）
        
        第一步：获取STS临时凭证
        第二步：使用临时凭证上传文件到OSS
        """
        try:
            import requests
            import hashlib
            
            # API 基础地址
            base_url = "https://awe-test.diezhi.net/v2/resources"
            
            # 接口不需要认证信息
            headers = {
                "Content-Type": "application/json",
            }
            
            print(f"✅ 接口无需认证，开始上传流程")
            
            # 读取文件内容
            with open(font_file_path, 'rb') as f:
                file_data = f.read()
            
            # 计算文件信息
            file_size = len(file_data)
            file_hash = hashlib.md5(file_data).hexdigest()
            file_ext = os.path.splitext(cdn_filename)[1][1:]  # 去掉点号
            
            print(f"🔍 文件信息: {cdn_filename}, 大小: {file_size} bytes, 哈希: {file_hash}")
            
            # ===== 第一步：获取STS临时凭证 =====
            sts_url = f"{base_url}/sts/get"
            sts_data = {
                "client_id": 1065,  # 修改为数字类型
                "path": "activity",  
                "file_type": file_ext,  # 添加文件类型
                "file_md5": file_hash,
                "operate_id": "web_fontmin_utils",  
            }
            
            print(f"🔍 第一步：获取STS凭证")
            print(f"🔍 STS URL: {sts_url}")
            print(f"🔍 STS 参数: {sts_data}")
            
            sts_response = requests.post(sts_url, headers=headers, json=sts_data, timeout=30)
            
            print(f"🔍 STS 响应状态码: {sts_response.status_code}")
            print(f"🔍 STS 响应内容: {sts_response.text}")
            
            if sts_response.status_code != 200:
                raise Exception(f"获取STS凭证失败: {sts_response.status_code} - {sts_response.text}")
            
            sts_result = sts_response.json()
            
            # 检查STS响应格式
            if sts_result.get('code') != 0:
                raise Exception(f"STS请求失败: {sts_result}")
            
            # 提取OSS信息
            oss_data = sts_result.get('data', {})
            bucket = oss_data.get('bucket')
            region = oss_data.get('region')
            access_key_id = oss_data.get('ak_id')  # 修正字段名
            access_key_secret = oss_data.get('ak_secret')  # 修正字段名
            security_token = oss_data.get('sts_token')  # 修正字段名
            upload_path = oss_data.get('bucket_path')  # 使用bucket_path作为上传路径
            resource_id = oss_data.get('resource_id')
            
            if not all([bucket, region, access_key_id, access_key_secret, security_token, upload_path, resource_id]):
                raise Exception(f"STS响应缺少必要信息: {oss_data}")
            
            print(f"✅ 获取STS凭证成功")
            print(f"🔍 OSS信息: bucket={bucket}, region={region}, upload_path={upload_path}")
            
            # ===== 第二步：上传文件到OSS =====
            # 这里需要使用阿里云OSS SDK，但为了简化，我们先尝试直接HTTP上传
            # 实际项目中可能需要安装: pip install oss2
            
            try:
                import oss2
                
                # 创建OSS客户端
                auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
                # 修正OSS域名格式
                oss_endpoint = f"https://{region}.aliyuncs.com"
                bucket_obj = oss2.Bucket(auth, oss_endpoint, bucket)
                
                # 上传文件
                print(f"🔍 第二步：上传文件到OSS")
                print(f"🔍 上传路径: {upload_path}")
                

                bucket_domain = oss_data.get('bucket_domain', f"{bucket}.oss-{region}.aliyuncs.com")
                cdn_url = f"https://{bucket_domain}/{upload_path}"
                return cdn_url
            except ImportError:
                print("⚠️ oss2库未安装，无法直接上传到OSS")
                print("💡 请运行: pip install oss2")
                raise Exception("需要安装oss2库")
                
        except ImportError:
            print("⚠️ requests库未安装，无法使用Python后端上传")
            print("💡 请运行: pip install requests")
            raise Exception("需要安装requests库")
        except Exception as e:
            print(f"❌ Python后端上传失败: {e}")
            raise

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

    def generate_css_file(self, subset_info_list: List[Dict], font_family: str, output_css_path: str) -> bool:
        """生成包含CDN地址的CSS文件"""
        try:
            css_rules = []
            
            # 添加文件头注释
            header = f"""/* 
 * 字体CSS文件 - {font_family}
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 包含 {len(subset_info_list)} 个字体子集
 * 支持多种格式: woff2, woff, ttf, eot
 */

"""
            
            for subset_info in subset_info_list:
                subset_num = subset_info['subset_num']
                unicode_ranges = subset_info['unicode_ranges']
                url_map = subset_info.get('cdn_urls') or {}
                
                # 生成多种格式的src属性(仅使用实际已上传的URL)
                multi_format_src = self.generate_src_from_urls(url_map)
                
                # 生成@font-face规则
                font_face = f"""@font-face {{
  font-family: {font_family};
  font-weight: 400;
  font-display: swap;
  src: {multi_format_src};
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

            # 设置输出文件夹 - 只用于CSS文件
            if not output_folder:
                output_folder = os.path.dirname(input_font_path)
            
            # 创建语言子目录 - 只用于CSS文件
            lang_output_folder = os.path.join(output_folder, language)
            os.makedirs(lang_output_folder, exist_ok=True)

            print(f"开始拆分字体: {input_font_path}")
            print(f"输出文件夹: {lang_output_folder}")

            # 步骤1: 分析字体中的字符
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

            # 步骤2: 开始拆分字体子集

            # 获取基础文件名
            base_name = os.path.splitext(os.path.basename(input_font_path))[0]
            file_ext = os.path.splitext(input_font_path)[1]

            # 创建子集字体并收集信息
            success_count = 0
            subset_info_list = []
            
            # 进度跟踪
            import time
            start_time = time.time()
            total_chunks = len(char_chunks)

            # 时间格式化函数（放在循环外，避免作用域问题）
            def format_time(seconds):
                if seconds < 60:
                    return f"{int(seconds)}秒"
                elif seconds < 3600:
                    return f"{int(seconds//60)}分{int(seconds%60)}秒"
                else:
                    hours = int(seconds//3600)
                    minutes = int((seconds%3600)//60)
                    return f"{hours}小时{minutes}分钟"
            
            # 初始化进度状态
            self.update_progress(
                is_running=True,
                step='splitting',
                message=f'开始拆分字体，共 {total_chunks} 个子集',
                percent=0,
                current=0,
                total=total_chunks,
                elapsed_time='0秒',
                remaining_time='计算中...'
            )

            for i, chunk in enumerate(char_chunks, 1):
                output_filename = f"{base_name}_subset_{i:03d}{file_ext}"
                # 不保存本地文件，只用于生成CDN文件名

                print(f"创建子集 {i}/{len(char_chunks)}: {output_filename} (包含 {len(chunk)} 个字符)")

                # 创建临时字体子集到内存
                temp_font_data = self.create_font_subset_in_memory(input_font_path, chunk)
                if temp_font_data:
                    success_count += 1

                    # 计算unicode-range
                    cps = [ord(c) for c in chunk]
                    ranges = self.codepoints_to_unicode_ranges(cps)
                    unicode_ranges = ",".join(ranges)

                    # 步骤3: 生成多格式并分别上传
                    format_bytes_map = self.convert_subset_bytes_to_formats(temp_font_data)
                    cdn_urls: Dict[str, str] = {}
                    base_name_only, _ = os.path.splitext(output_filename)
                    for ext_key, data_bytes in format_bytes_map.items():
                        upload_filename = f"{base_name_only}.{ext_key}"
                        try:
                            url = self.upload_font_data_to_cdn(data_bytes, upload_filename, language)
                            cdn_urls[ext_key] = url
                        except Exception as upload_err:
                            print(f"上传 {upload_filename} 失败: {upload_err}")
                    
                    # 计算进度和时间估算
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    progress_percent = (i / total_chunks) * 100
                    
                    if i > 1:  # 至少处理了2个文件才能估算
                        avg_time_per_file = elapsed_time / i
                        remaining_files = total_chunks - i
                        estimated_remaining_time = avg_time_per_file * remaining_files
                        
                        remaining_time_str = format_time(estimated_remaining_time)
                        elapsed_time_str = format_time(elapsed_time)
                        
                        # 更新进度状态
                        self.update_progress(
                            current=i,
                            total=total_chunks,
                            percent=progress_percent,
                            elapsed_time=elapsed_time_str,
                            remaining_time=remaining_time_str,
                            message=f"已拆分 {i}/{total_chunks} 个子集，预计剩余 {remaining_time_str}"
                        )
                    else:
                        # 第一个文件，只显示开始信息
                        self.update_progress(
                            current=i,
                            total=total_chunks,
                            percent=progress_percent,
                            elapsed_time=format_time(elapsed_time),
                            remaining_time='计算中...',
                            message=f"开始拆分字体，共 {total_chunks} 个子集"
                        )

                    # 收集子集信息
                    subset_info = {
                        'subset_num': i,
                        'char_count': len(chunk),
                        'characters': ''.join(chunk),
                        'unicode_ranges': unicode_ranges,
                        'cdn_urls': cdn_urls,
                        'language': language
                    }
                    subset_info_list.append(subset_info)
                else:
                    print(f"警告: 创建子集 {i} 失败")

            print(f"拆分完成! 成功创建 {success_count}/{len(char_chunks)} 个子集字体")

            # 更新进度状态为完成
            self.update_progress(
                is_running=False,
                step='completed',
                message=f'拆分完成! 成功创建 {success_count}/{len(char_chunks)} 个子集字体',
                percent=100,
                current=total_chunks,
                total=total_chunks
            )

            # 步骤4: 生成CSS文件
            
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