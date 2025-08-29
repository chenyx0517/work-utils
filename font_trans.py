import os
import sys
import webview
from fontTools import subset
from fontTools.ttLib import TTFont
import time

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

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
        print("错误: 缺少 'brotli' 库！")
        print("请运行: pip install brotli")
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
        '字体转换工具',
        html_path,
        js_api=api,
        width=900,
        height=900,
        min_size=(800, 600)
    )
    api.window = window

    # 启动应用
    webview.start(debug=False)

if __name__ == "__main__":
    main()