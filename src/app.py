import os
import sys
import tempfile
import traceback
import time
import threading

# 延迟导入重型库
def lazy_import_fonttools():
    """延迟导入字体处理库"""
    global subset, TTFont, instantiateVariableFont
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    return subset, TTFont, instantiateVariableFont

def lazy_import_webview():
    """延迟导入WebView"""
    import webview
    return webview

# --- 字体转换核心逻辑 ---
def convert_ttf_to_woff2_core(input_ttf_path, output_woff2_path=None, subset_chars=None, weight_value=None):
    if not os.path.exists(input_ttf_path):
        return False, f"错误: 输入文件不存在 - {input_ttf_path}", None
    if not input_ttf_path.lower().endswith((".ttf", ".otf")):
        return False, f"错误: 输入文件 '{input_ttf_path}' 不是 TTF 或 OTF 格式。", None
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_woff2_path)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            return False, f"错误: 无法创建输出目录 '{output_dir}': {e}", None

    try:
        # 延迟导入字体处理库
        subset, TTFont, instantiateVariableFont = lazy_import_fonttools()
        font_for_subset = input_ttf_path
        temp_font_path = None

        if weight_value is not None and str(weight_value).isdigit():
            weight_value = int(weight_value)
            with TTFont(input_ttf_path) as font_check:
                if 'fvar' in font_check:
                    wght_axis = [a for a in font_check['fvar'].axes if a.axisTag == 'wght']
                    if wght_axis:
                        min_w = int(wght_axis[0].minValue)
                        max_w = int(wght_axis[0].maxValue)
                        if not (min_w <= weight_value <= max_w):
                            return False, f"字重 {weight_value} 超出字体支持范围（{min_w}~{max_w}），请重新选择。", None
                        
                        temp_font = instantiateVariableFont(font_check, {'wght': weight_value}, inplace=False)
                        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmpf:
                            temp_font.save(tmpf.name)
                            font_for_subset = tmpf.name
                            temp_font_path = tmpf.name
        
        start_time = time.time()
        
        font = TTFont(font_for_subset)
        
        if subset_chars and subset_chars.strip():
            subsetter = subset.Subsetter()
            subsetter.populate(text=subset_chars)
            subsetter.subset(font)
        
        font.flavor = 'woff2'
        font.save(output_woff2_path)
        
        end_time = time.time()
        conversion_time = end_time - start_time

        message = f"✓ {os.path.basename(input_ttf_path)} 转换成功"
        if weight_value is not None:
            message += f" (字重:{weight_value})"
        message += f" - 耗时: {conversion_time:.2f}秒"
        
        return True, message, output_woff2_path, conversion_time

    except Exception as e:
        return False, f"字体转换时发生错误: {e}\n{traceback.format_exc()}", None, 0
    finally:
        if temp_font_path and os.path.exists(temp_font_path):
            os.remove(temp_font_path)

def convert_ttf_to_woff_core(input_ttf_path, output_woff_path=None, subset_chars=None, weight_value=None):
    """转换TTF到WOFF格式"""
    if not os.path.exists(input_ttf_path):
        return False, f"错误: 输入文件不存在 - {input_ttf_path}", None
    if not input_ttf_path.lower().endswith((".ttf", ".otf")):
        return False, f"错误: 输入文件 '{input_ttf_path}' 不是 TTF 或 OTF 格式。", None
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_woff_path)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            return False, f"错误: 无法创建输出目录 '{output_dir}': {e}", None

    try:
        # 延迟导入字体处理库
        subset, TTFont, instantiateVariableFont = lazy_import_fonttools()
        font_for_subset = input_ttf_path
        temp_font_path = None

        if weight_value is not None and str(weight_value).isdigit():
            weight_value = int(weight_value)
            with TTFont(input_ttf_path) as font_check:
                if 'fvar' in font_check:
                    wght_axis = [a for a in font_check['fvar'].axes if a.axisTag == 'wght']
                    if wght_axis:
                        min_w = int(wght_axis[0].minValue)
                        max_w = int(wght_axis[0].maxValue)
                        if not (min_w <= weight_value <= max_w):
                            return False, f"字重 {weight_value} 超出字体支持范围（{min_w}~{max_w}），请重新选择。", None
                        
                        temp_font = instantiateVariableFont(font_check, {'wght': weight_value}, inplace=False)
                        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmpf:
                            temp_font.save(tmpf.name)
                            font_for_subset = tmpf.name
                            temp_font_path = tmpf.name
        
        start_time = time.time()
        
        font = TTFont(font_for_subset)
        
        if subset_chars and subset_chars.strip():
            subsetter = subset.Subsetter()
            subsetter.populate(text=subset_chars)
            subsetter.subset(font)
        
        font.flavor = 'woff'
        font.save(output_woff_path)
        
        end_time = time.time()
        conversion_time = end_time - start_time

        message = f"✓ {os.path.basename(input_ttf_path)} 转换成功"
        if weight_value is not None:
            message += f" (字重:{weight_value})"
        message += f" - 耗时: {conversion_time:.2f}秒"
        
        return True, message, output_woff_path, conversion_time

    except Exception as e:
        return False, f"字体转换时发生错误: {e}\n{traceback.format_exc()}", None, 0
    finally:
        if temp_font_path and os.path.exists(temp_font_path):
            os.remove(temp_font_path)

class Api:
    def __init__(self, window=None):
        self.window = window
        self.is_processing = False
        self.current_task = None

    def select_input_file(self):
        try:
            print("🔍 API: select_input_file 被调用")
            webview = lazy_import_webview()
            print("🔍 API: webview 导入成功")
            print(f"🔍 API: window 对象: {self.window}")
            
            file_paths = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=[
                    ('字体文件', '*.ttf;*.otf;*.woff;*.woff2'),
                    ('TTF字体', '*.ttf'),
                    ('OTF字体', '*.otf'),
                    ('WOFF字体', '*.woff'),
                    ('WOFF2字体', '*.woff2'),
                    ('所有文件', '*.*')
                ]
            )
            print(f"🔍 API: 文件选择结果: {file_paths}")
            result = file_paths[0] if file_paths and file_paths[0] else None
            print(f"🔍 API: 返回结果: {result}")
            return result
        except Exception as e:
            print(f"❌ API: select_input_file 异常: {e}")
            import traceback
            print(f"❌ API: 异常详情: {traceback.format_exc()}")
            return None
    
    def select_output_folder(self):
        try:
            webview = lazy_import_webview()
            folder_path = self.window.create_file_dialog(
                webview.FOLDER_DIALOG,
                allow_multiple=False,
            )
            return folder_path[0] if folder_path and folder_path[0] else None
        except Exception as e:
            print(f"❌ API: select_output_folder 异常: {e}")
            return None

    def get_processing_status(self):
        """获取当前处理状态"""
        return {
            "is_processing": self.is_processing,
            "current_task": self.current_task
        }

    def get_progress(self):
        """获取当前处理进度"""
        return {
            "is_running": self.is_processing,
            "current_task": self.current_task,
            "progress": 0  # 可以后续添加具体的进度百分比
        }

    def split_font_and_generate_css(self, input_font_path, font_family, language, num_chunks, output_folder=None):
        """拆分字体并生成CSS"""
        if self.is_processing:
            return {"success": False, "message": "⚠️ 正在处理其他任务，请稍后再试"}
        
        if not input_font_path:
            return {"success": False, "message": "✗ 错误: 未选择字体文件"}
        
        # 验证文件格式
        if not input_font_path.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            return {"success": False, "message": f"✗ 错误: 不支持的文件格式 - {input_font_path}"}
        
        # 设置输出目录
        if not output_folder:
            output_folder = os.path.dirname(input_font_path)
        
        self.is_processing = True
        self.current_task = f"拆分字体 {os.path.basename(input_font_path)}"
        
        try:
            # 导入拆分模块
            from font_splitter import split_font
            
            # 根据语言选择unicode文件
            language_unicode_map = {
                'zh': 'unicode-zh-CN.txt',
                'tc': 'unicode-zh-TW.txt', 
                'ja': 'unicode-ja.txt'
            }
            
            unicode_file = language_unicode_map.get(language, 'unicode-zh-CN.txt')
            unicode_path = os.path.join(os.path.dirname(__file__), '..', unicode_file)
            
            if not os.path.exists(unicode_path):
                return {"success": False, "message": f"✗ 错误: 找不到语言文件 {unicode_file}"}
            
            # 读取字符顺序
            with open(unicode_path, 'r', encoding='utf-8') as f:
                preferred_order = list(f.read().strip())
            
            # 执行拆分
            success = split_font(
                input_font_path,
                output_folder,
                num_chunks=num_chunks,
                preferred_order=preferred_order,
                font_family=font_family,
                language=language
            )
            
            if success:
                return {"success": True, "message": "🎉 字体拆分完成！CSS文件已生成。"}
            else:
                return {"success": False, "message": "✗ 字体拆分失败"}
                
        except Exception as e:
            return {"success": False, "message": f"✗ 拆分过程中发生错误: {str(e)}"}
        finally:
            self.is_processing = False
            self.current_task = None

    def split_font_and_generate_css_with_file(self, file_data, filename, font_family, language, num_chunks, output_folder=None):
        """使用文件数据拆分字体并生成CSS"""
        if self.is_processing:
            return {"success": False, "message": "⚠️ 正在处理其他任务，请稍后再试"}
        
        if not file_data:
            return {"success": False, "message": "✗ 错误: 未接收到文件数据"}
        
        try:
            # 解析base64数据
            import base64
            if file_data.startswith('data:'):
                file_data = file_data.split(',')[1]
            
            # 解码base64
            file_bytes = base64.b64decode(file_data)
            
            # 创建临时文件
            import tempfile
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, filename)
            
            # 写入临时文件
            with open(temp_file_path, 'wb') as f:
                f.write(file_bytes)
            
            # 验证文件格式
            if not filename.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                return {"success": False, "message": f"✗ 错误: 不支持的文件格式 - {filename}"}
            
            # 设置输出目录
            if not output_folder:
                desktop_path = os.path.expanduser("~/Desktop")
                if os.path.exists(desktop_path):
                    output_folder = desktop_path
                else:
                    output_folder = os.getcwd()
            
            self.is_processing = True
            self.current_task = f"拆分字体 {filename}"
            
            try:
                # 导入拆分模块
                from font_splitter import split_font
                
                # 根据语言选择unicode文件
                language_unicode_map = {
                    'zh': 'unicode-zh-CN.txt',
                    'tc': 'unicode-zh-TW.txt', 
                    'ja': 'unicode-ja.txt'
                }
                
                unicode_file = language_unicode_map.get(language, 'unicode-zh-CN.txt')
                
                # 尝试多个可能的路径
                possible_paths = [
                    # 开发环境路径
                    os.path.join(os.path.dirname(__file__), '..', unicode_file),
                    os.path.join(os.path.dirname(__file__), '..', 'unicode', unicode_file),
                    
                    # macOS应用包路径 - 从Frameworks目录到Resources (修复路径)
                    os.path.join(os.path.dirname(__file__), '..', 'Resources', 'unicode', unicode_file),
                    os.path.join(os.path.dirname(__file__), '..', 'Resources', unicode_file),
                    
                    # macOS应用包路径 - 从MacOS目录到Resources
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Resources', 'unicode', unicode_file),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Resources', unicode_file),
                    
                    # 当前工作目录路径
                    os.path.join(os.getcwd(), unicode_file),
                    os.path.join(os.getcwd(), 'unicode', unicode_file),
                    
                    # 绝对路径
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', unicode_file),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'unicode', unicode_file),
                    
                    # 直接文件名
                    unicode_file
                ]
                
                unicode_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        unicode_path = path
                        break
                
                if not unicode_path:
                    return {"success": False, "message": f"✗ 错误: 找不到语言文件 {unicode_file}，尝试的路径: {possible_paths}"}
                
                # 读取字符顺序
                from font_splitter import parse_unicode_order_file
                preferred_order = parse_unicode_order_file(unicode_path)
                
                # 执行拆分
                success = split_font(
                    temp_file_path,
                    output_folder,
                    num_chunks=num_chunks,
                    preferred_order=preferred_order,
                    font_family=font_family,
                    language=language
                )
                
                if success:
                    # 查找生成的CSS文件
                    base_name = os.path.splitext(filename)[0]
                    css_filename = f"{base_name}_{language}.css"
                    css_path = os.path.join(output_folder, css_filename)
                    
                    # 计算子集数量（简单估算）
                    subset_count = min(num_chunks, 200)  # 实际应该从split_font函数返回
                    
                    return {
                        "success": True, 
                        "message": "🎉 字体拆分完成！CSS文件已生成。",
                        "subset_count": subset_count,
                        "css_path": css_path
                    }
                else:
                    return {"success": False, "message": "✗ 字体拆分失败"}
                    
            except Exception as e:
                return {"success": False, "message": f"✗ 拆分过程中发生错误: {str(e)}"}
            finally:
                self.is_processing = False
                self.current_task = None
                
        except Exception as e:
            return {"success": False, "message": f"✗ 错误: 文件处理失败 - {str(e)}"}
        finally:
            # 清理临时文件
            try:
                if 'temp_file_path' in locals():
                    os.remove(temp_file_path)
                    os.rmdir(temp_dir)
            except:
                pass

    def cancel_processing(self):
        """取消当前处理"""
        if self.is_processing:
            self.is_processing = False
            self.current_task = None
            return {"success": True, "message": "✓ 已取消处理"}
        return {"success": False, "message": "没有正在处理的任务"}

    def get_font_weights_from_data(self, file_data, filename):
        """从文件数据获取字重信息"""
        weights = []
        if not file_data:
            return weights
        
        try:
            # 解析base64数据
            import base64
            if file_data.startswith('data:'):
                file_data = file_data.split(',')[1]
            
            # 解码base64
            file_bytes = base64.b64decode(file_data)
            
            # 创建临时文件
            import tempfile
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, filename)
            
            # 写入临时文件
            with open(temp_file_path, 'wb') as f:
                f.write(file_bytes)
            
            # 获取字重信息
            weights = self._get_font_weights_from_file(temp_file_path)
            
            # 清理临时文件
            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except:
                pass
                
        except Exception as e:
            print(f"❌ 从文件数据获取字重失败: {e}")
        
        return weights

    def get_font_weights(self, file_path):
        """从文件路径获取字重信息"""
        if not file_path or not os.path.exists(file_path):
            return []
        return self._get_font_weights_from_file(file_path)
    
    def _get_font_weights_from_file(self, file_path):
        """内部方法：从文件获取字重信息"""
        weights = []
        try:
            # 延迟导入字体处理库
            _, TTFont, _ = lazy_import_fonttools()
            font = TTFont(file_path)
            if 'fvar' in font:
                fvar_table = font['fvar']
                for axis in fvar_table.axes:
                    if axis.axisTag == 'wght':
                        min_w, max_w, default_w = int(axis.minValue), int(axis.maxValue), int(axis.defaultValue)
                        weights_to_check = [100, 200, 300, 400, 500, 600, 700, 800, 900]
                        final_weights = sorted(list(set([min_w, max_w, default_w] + [w for w in weights_to_check if min_w <= w <= max_w])))
                        if hasattr(fvar_table, 'instances'):
                            final_weights.extend([int(instance.coordinates['wght']) for instance in fvar_table.instances if 'wght' in instance.coordinates])
                        weights = sorted(list(set(final_weights)))
                        break
        except Exception as e:
            print(f"❌ 获取字重失败: {e}")
        return weights

    def get_font_info(self, file_path):
        """获取字体文件详细信息"""
        if not file_path or not os.path.exists(file_path):
            return {"success": False, "message": "文件不存在"}
        
        try:
            # 延迟导入字体处理库
            _, TTFont, _ = lazy_import_fonttools()
            font = TTFont(file_path)
            info = {
                "success": True,
                "file_name": os.path.basename(file_path),
                "file_size": f"{os.path.getsize(file_path) / 1024 / 1024:.2f} MB",
                "font_family": "未知",
                "font_style": "未知",
                "is_variable": False,
                "weights": [],
                "character_count": 0
            }
            
            # 获取字体名称
            if 'name' in font:
                name_table = font['name']
                for record in name_table.names:
                    if record.nameID == 1:  # Font Family name
                        info["font_family"] = record.toUnicode()
                    elif record.nameID == 2:  # Font Subfamily name
                        info["font_style"] = record.toUnicode()
            
            # 检查是否为变量字体
            if 'fvar' in font:
                info["is_variable"] = True
                info["weights"] = self.get_font_weights(file_path)
            
            # 获取字符数量
            if 'cmap' in font:
                cmap = font['cmap']
                char_count = 0
                for table in cmap.tables:
                    char_count += len(table.cmap)
                info["character_count"] = char_count
            
            return info
            
        except Exception as e:
            return {"success": False, "message": f"获取字体信息失败: {str(e)}"}

    def start_conversion_with_file(self, file_data, filename, subset_chars="", weights=None, output_folder=None, formats=None):
        """使用文件数据开始转换"""
        if self.is_processing:
            return {"success": False, "message": "⚠️ 正在处理其他任务，请稍后再试"}
        
        if not file_data:
            return {"success": False, "message": "✗ 错误: 未接收到文件数据"}
        
        try:
            # 解析base64数据
            import base64
            if file_data.startswith('data:'):
                # 移除data:前缀
                file_data = file_data.split(',')[1]
            
            # 解码base64
            file_bytes = base64.b64decode(file_data)
            
            # 创建临时文件
            import tempfile
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, filename)
            
            # 写入临时文件
            with open(temp_file_path, 'wb') as f:
                f.write(file_bytes)
            
            # 验证文件格式
            if not filename.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                return {"success": False, "message": f"✗ 错误: 不支持的文件格式 - {filename}"}
            
            # 如果没有指定输出目录，尝试智能推断
            if not output_folder:
                # 尝试在常见目录中查找同名文件，使用其所在目录
                common_dirs = [
                    os.path.expanduser("~/Desktop"),
                    os.path.expanduser("~/Downloads"),
                    os.path.expanduser("~/Documents"),
                    os.getcwd()
                ]
                
                for dir_path in common_dirs:
                    if os.path.exists(dir_path):
                        potential_file = os.path.join(dir_path, filename)
                        if os.path.exists(potential_file):
                            output_folder = dir_path
                            break
                
                # 如果还是没找到，使用桌面作为默认
                if not output_folder:
                    desktop_path = os.path.expanduser("~/Desktop")
                    if os.path.exists(desktop_path):
                        output_folder = desktop_path
                    else:
                        output_folder = os.getcwd()
            
            # 调用原有的转换逻辑
            result = self._do_conversion(temp_file_path, subset_chars, weights, output_folder, formats)
            
            # 清理临时文件
            try:
                os.remove(temp_file_path)
                os.rmdir(temp_dir)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {"success": False, "message": f"✗ 错误: 文件处理失败 - {str(e)}"}

    def start_conversion(self, input_path, subset_chars="", weights=None, output_folder=None, formats=None):
        if self.is_processing:
            return {"success": False, "message": "⚠️ 正在处理其他任务，请稍后再试"}
        
        if not input_path:
            return {"success": False, "message": "✗ 错误: 未选择文件"}
        
        # 如果文件路径不存在，尝试在常见目录中查找
        if not os.path.exists(input_path):
            # 尝试在桌面和下载文件夹中查找
            common_dirs = [
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Downloads"),
                os.getcwd()
            ]
            
            filename = os.path.basename(input_path)
            for dir_path in common_dirs:
                if os.path.exists(dir_path):
                    full_path = os.path.join(dir_path, filename)
                    if os.path.exists(full_path):
                        input_path = full_path
                        break
            else:
                return {"success": False, "message": f"✗ 错误: 找不到文件 '{filename}'，请确保文件在桌面或下载文件夹中。"}
        
        # 验证文件格式
        if not input_path.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
            return {"success": False, "message": f"✗ 错误: 不支持的文件格式 - {os.path.basename(input_path)}"}
        
        # 调用私有转换方法
        return self._do_conversion(input_path, subset_chars, weights, output_folder, formats)
    
    def _do_conversion(self, input_path, subset_chars="", weights=None, output_folder=None, formats=None):
        """私有转换方法"""
        # 默认输出格式
        if not formats:
            formats = ['woff2']
        
        self.is_processing = True
        self.current_task = f"转换 {os.path.basename(input_path)}"
        
        try:
            # 设置输出目录 - 优先使用用户指定，否则使用桌面
            if output_folder:
                output_folder = output_folder
            else:
                # 尝试使用桌面作为默认输出目录
                desktop_path = os.path.expanduser("~/Desktop")
                if os.path.exists(desktop_path):
                    output_folder = desktop_path
                else:
                    # 如果桌面不存在，使用当前目录
                    output_folder = os.getcwd()
            
            total_start_time = time.time()
            
            results = []
            conversion_weights = weights if weights else [None]

            for weight in conversion_weights:
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                weight_suffix = f"_w{weight}" if weight is not None else ""
                
                for format_type in formats:
                    if format_type == 'woff2':
                        output_filename = f"{base_name}{weight_suffix}.woff2"
                        output_path = os.path.join(output_folder, output_filename)
                        success, message, final_path, conversion_time = convert_ttf_to_woff2_core(input_path, output_path, subset_chars, weight)
                    elif format_type == 'woff':
                        output_filename = f"{base_name}{weight_suffix}.woff"
                        output_path = os.path.join(output_folder, output_filename)
                        success, message, final_path, conversion_time = convert_ttf_to_woff_core(input_path, output_path, subset_chars, weight)
                    else:
                        continue  # 跳过不支持的格式
                    
                    results.append({
                        "success": success,
                        "message": message,
                        "path": final_path,
                        "time": conversion_time,
                        "format": format_type
                    })
            
            total_end_time = time.time()
            total_conversion_time = total_end_time - total_start_time

            success_count = sum(1 for r in results if r['success'])
            
            if success_count == len(results):
                final_message = f"🎉 转换完成！共 {success_count} 个文件。\n"
                return {"success": True, "message": final_message, "paths": [r['path'] for r in results], "total_time_seconds": total_conversion_time}
            else:
                error_messages = [f"{r['message']}" for r in results if not r['success']]
                final_message = f"✗ 部分文件转换失败，成功 {success_count} 个，失败 {len(results) - success_count} 个。\n"
                final_message += "详细错误:\n" + "\n".join(error_messages)
                return {"success": False, "message": final_message, "total_time_seconds": total_conversion_time}
        
        except Exception as e:
            return {"success": False, "message": f"✗ 转换过程中发生错误: {str(e)}"}
        finally:
            self.is_processing = False
            self.current_task = None

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持打包后的应用"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 打包后的应用
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(base_path)
        return os.path.join(project_root, relative_path)

def main():
    """主函数"""
    print("🚀 正在启动字体转换工具...")
    
    # 获取HTML文件路径
    html_file_path = get_resource_path('index.html')

    if not os.path.exists(html_file_path):
        print(f"❌ 错误: 找不到HTML文件在 {html_file_path}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"Python可执行文件: {sys.executable}")
        if getattr(sys, 'frozen', False):
            print(f"打包临时目录: {sys._MEIPASS}")
        sys.exit(1)

    # 延迟导入WebView
    webview = lazy_import_webview()
    
    # 创建API和窗口
    api = Api()
    window = webview.create_window(
        'FontTool',
        url=f'file://{html_file_path}',
        js_api=api,
        width=1000,
        height=700,
        min_size=(800, 600),
        resizable=True,
        shadow=True,
        on_top=False
    )
    api.window = window
    
    print("✅ 应用启动完成")
    webview.start()

if __name__ == '__main__':
    main()