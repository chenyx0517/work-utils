import os
import sys
import webview
from fontTools import subset
from fontTools.ttLib import TTFont
import tempfile
import traceback
import time

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
        from fontTools.varLib.instancer import instantiateVariableFont
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

class Api:
    def __init__(self, window=None):
        self.window = window

    def select_input_file(self):
        try:
            file_paths = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=('字体文件 (*.ttf;*.otf)', '所有文件 (*.*)')
            )
            return file_paths[0] if file_paths and file_paths[0] else None
        except Exception as e:
            print(f"❌ API: select_input_file 异常: {e}")
            return None
    
    def select_output_folder(self):
        try:
            folder_path = self.window.create_file_dialog(
                webview.FOLDER_DIALOG,
                allow_multiple=False,
            )
            return folder_path[0] if folder_path and folder_path[0] else None
        except Exception as e:
            print(f"❌ API: select_output_folder 异常: {e}")
            return None

    def get_font_weights(self, file_path):
        weights = []
        if not file_path or not os.path.exists(file_path):
            return weights
        try:
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

    def start_conversion(self, input_path, subset_chars="", weights=None, output_folder=None):
        if not input_path or not os.path.exists(input_path):
            return {"success": False, "message": f"✗ 错误: 文件不存在 - {input_path}"}
        
        output_folder = output_folder or os.path.dirname(input_path)
        total_start_time = time.time()
        
        results = []
        conversion_weights = weights if weights else [None]

        for weight in conversion_weights:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{base_name}_w{weight}.woff2" if weight is not None else f"{base_name}.woff2"
            output_path = os.path.join(output_folder, output_filename)
            
            success, message, final_path, conversion_time = convert_ttf_to_woff2_core(input_path, output_path, subset_chars, weight)
            
            results.append({
                "success": success,
                "message": message,
                "path": final_path,
                "time": conversion_time
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

if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(__file__))
    html_file_path = os.path.join(base_path, 'index.html')

    if not os.path.exists(html_file_path):
        print(f"❌ 错误: 找不到HTML文件在 {html_file_path}")
        sys.exit(1)

    api = Api()
    window = webview.create_window(
        '字体转换工具',
        url=f'file://{html_file_path}',
        js_api=api,
        width=800,
        height=1000,
        resizable=True
    )
    api.window = window
    
    webview.start()