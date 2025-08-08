import PySimpleGUI as sg
import os
import sys
from fontTools import subset
from fontTools.subset import Options
from fontTools.ttLib import TTFont

# --- 字体转换核心逻辑 ---
def convert_ttf_to_woff2_core(input_ttf_path, output_woff2_path=None, subset_chars=None, weight_value=None):
    """
    将 TTF/OTF 字体文件转换为 WOFF2 格式。
    subset_chars: 只保留这些字符（字符串），为 None 或空字符串时保留全部。
    weight_value: 可变字体时，指定字重（int），否则忽略。
    此函数返回 (成功状态, 消息字符串)。
    """
    if not os.path.exists(input_ttf_path):
        return False, f"错误: 输入文件不存在 - {input_ttf_path}"

    if not input_ttf_path.lower().endswith((".ttf", ".otf")):
        return False, f"错误: 输入文件 '{input_ttf_path}' 似乎不是 TTF 或 OTF 格式。"

    if output_woff2_path is None:
        base_name = os.path.splitext(os.path.basename(input_ttf_path))[0]
        output_woff2_path = os.path.join(os.path.dirname(input_ttf_path), f"{base_name}.woff2")

    output_dir = os.path.dirname(output_woff2_path)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            return False, f"错误: 无法创建输出目录 '{output_dir}': {e}"

    try:
        from fontTools import subset
        import traceback
        # 1. 先实例化字重（如有）
        font_for_subset = input_ttf_path
        temp_font = None
        if weight_value is not None and str(weight_value).isdigit():
            weight_value = int(weight_value)
            try:
                with TTFont(input_ttf_path) as font_check:
                    if 'fvar' in font_check:
                        wght_axis = [a for a in font_check['fvar'].axes if a.axisTag == 'wght']
                        if wght_axis:
                            min_w = int(wght_axis[0].minValue)
                            max_w = int(wght_axis[0].maxValue)
                            if not (min_w <= weight_value <= max_w):
                                return False, f"字重 {weight_value} 超出字体支持范围（{min_w}~{max_w}），请重新选择。"
                            # 实例化
                            from fontTools.varLib.instancer import instantiateVariableFont
                            temp_font = instantiateVariableFont(font_check, {'wght': weight_value}, inplace=False)
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmpf:
                                temp_font.save(tmpf.name)
                                font_for_subset = tmpf.name
                            print(f"[调试] 已实例化字重: {weight_value}, 临时字体: {font_for_subset}")
                        else:
                            print(f"[调试] 字体是可变字体但没有 'wght' 轴，将忽略字重选择。")
                    else:
                        print(f"[调试] 字体不是可变字体，将忽略字重选择。")
            except Exception as e:
                return False, f"检测字体支持的字重时出错: {e}\n{traceback.format_exc()}"

        # 2. 配置 subset options
        options = subset.Options()
        options.flavor = "woff2"
        options.with_zopfli = False
        options.desubroutinize = True
        options.name_IDs = ['*']
        options.name_legacy = True
        options.name_languages = ['*']
        options.layout_features = ['*']
        options.notdef_glyph = True
        options.notdef_outline = True
        options.recalc_bounds = True
        options.recalc_timestamp = True
        options.canonical_order = True

        subsetter = subset.Subsetter(options=options)
        font = subset.load_font(font_for_subset, options)
        if subset_chars and subset_chars.strip():
            unicodes = [ord(c) for c in subset_chars]
            subsetter.populate(unicodes=unicodes)
            subsetter.subset(font)
        subset.save_font(font, output_woff2_path, options)

        message = f"成功转换: '{input_ttf_path}' 到 '{output_woff2_path}'"
        if subset_chars and subset_chars.strip():
            message += " (仅保留指定字符)"
        if weight_value:
            message += f" 字重:{weight_value}"
        return True, message

    except Exception as e:
        import traceback
        print(f"[调试] 字体转换时发生错误: {e}")
        print(traceback.format_exc())
        return False, f"字体转换时发生错误: {e}\n{traceback.format_exc()}"
# --- GUI 界面布局 ---
def create_gui_layout():
    # 快捷字符选项
    quick_char_options = [
        ("全部数字", "0123456789"),
        ("大写英文", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ("小写英文", "abcdefghijklmnopqrstuvwxyz"),
        ("大小写英文", "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
        ("常用标点", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"),
        ("全部简体中文", ''.join(chr(i) for i in range(0x4E00, 0x9FFF + 1))),
        ("全部繁体中文", ''.join(chr(i) for i in range(0x3400, 0x4DBF + 1)) + ''.join(chr(i) for i in range(0x4E00, 0x9FFF + 1))),
        ("全部日文", ''.join(chr(i) for i in range(0x3040, 0x309F + 1)) + ''.join(chr(i) for i in range(0x30A0, 0x30FF + 1)) + ''.join(chr(i) for i in range(0x31F0, 0x31FF + 1))),
        ("全部韩文", ''.join(chr(i) for i in range(0xAC00, 0xD7A3 + 1)))
    ]
    quick_char_labels = [opt[0] for opt in quick_char_options]
    quick_char_checkboxes = [
        sg.Checkbox(label, key=f'-QC_{i}-', font=("微软雅黑", 13), enable_events=False)
        for i, label in enumerate(quick_char_labels)
    ]

    # 每行最多显示3个checkbox
    checkbox_rows = [quick_char_checkboxes[i:i+3] for i in range(0, len(quick_char_checkboxes), 3)]

    # 预置10个隐藏Checkbox用于字重选择
    weight_checkboxes_layout = [
        sg.Checkbox('', key=f'-W_{i}-', visible=False, font=("微软雅黑", 13))
        for i in range(10)
    ]
    
    # 将字重多选框放入一个列中
    weight_column = sg.Column([weight_checkboxes_layout], key='-WEIGHT_COLUMN-', visible=False)

    

    layout = [
        [sg.Text("TTF/OTF 转 WOFF2 工具", font=("微软雅黑", 18, "bold"), text_color="#5DA9E9", pad=((0,0),(10,10)))],
        [sg.Text("选择要转换的字体文件:", font=("微软雅黑", 14)), 
         sg.Input(key='-INPUT_FILE-', enable_events=True, readonly=True, size=(40,1)), 
         sg.FileBrowse(file_types=(("Font Files", "*.ttf *.otf"),), button_color=("#fff", "#5DA9E9"))],
        [sg.Text("选择输出文件夹 (可选):", font=("微软雅黑", 14)), 
         sg.Input(key='-OUTPUT_FOLDER-', readonly=True, size=(40,1)), 
         sg.FolderBrowse(button_color=("#fff", "#5DA9E9"))],
        [sg.Text("快捷字符选择（可多选）:", font=("微软雅黑", 14))],
        *checkbox_rows,
        [sg.Text("请输入需要保留的字符（留空为全部）:", font=("微软雅黑", 14))],
        [sg.Multiline(key='-SUBSET_CHARS-', size=(60,4), font=("Consolas", 14),background_color="#fff")],
        [sg.Text("提示：字符过多时转换较慢哦", font=("微软雅黑", 12), text_color="#6D326D")],
        [sg.Text("选择字重（仅可变字体可选，可多选）:", key='-WEIGHT_LABEL-', visible=False, font=("微软雅黑", 14))],
        [weight_column], # 将列放入布局中
        [sg.Button("开始转换", key='-CONVERT_BUTTON-', size=(12,1), font=("微软雅黑", 14, "bold"), button_color=("#fff", "#5DA9E9"))],
        [sg.HorizontalSeparator()],
        [sg.Text("状态信息：", font=("微软雅黑", 12, "bold"), text_color="#336699")],
        [sg.Multiline(size=(70, 12), key='-OUTPUT-', autoscroll=True, disabled=True, background_color='#fff', text_color='#5da9e6', font=("Consolas", 10), border_width=2)]
    ]
    return layout


# --- 主 GUI 逻辑 ---
# ... (GUI 布局和核心转换逻辑部分保持不变)

def main_gui():
    """运行 PySimpleGUI 应用程序。"""
    sg.theme('Reddit')
    window = sg.Window(
        "字体 TTF/OTF 转 WOFF2 工具",
        create_gui_layout(),
        icon=None,
        finalize=True,
        size=(900, 700),
        resizable=True
    )

    # 修正韩语字符集定义
    quick_char_options = [
        ("全部数字", "0123456789"),
        ("大写英文", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ("小写英文", "abcdefghijklmnopqrstuvwxyz"),
        ("大小写英文", "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
        ("常用标点", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"),
        ("全部简体中文", ''.join(chr(i) for i in range(0x4E00, 0x9FFF + 1))),
        ("全部繁体中文", ''.join(chr(i) for i in range(0x3400, 0x4DBF + 1)) + ''.join(chr(i) for i in range(0x4E00, 0x9FFF + 1))),
        ("全部日文", ''.join(chr(i) for i in range(0x3040, 0x309F + 1)) + ''.join(chr(i) for i in range(0x30A0, 0x30FF + 1)) + ''.join(chr(i) for i in range(0x31F0, 0x31FF + 1))),
        ("全部韩文", ''.join(chr(i) for i in range(0xAC00, 0xD7A3 + 1)))
    ]

    current_weights = []

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif event == '-FILL_CHARS-':
            current_chars = values.get('-SUBSET_CHARS-', '') or ''
            selected_chars_from_quick = []
            for i, option in enumerate(quick_char_options):
                if values.get(f'-QC_{i}-'):
                    selected_chars_from_quick.append(option[1])
            quick_chars_to_add = ''.join(selected_chars_from_quick)
            combined_chars = ''.join(sorted(set(current_chars + quick_chars_to_add)))
            window['-SUBSET_CHARS-'].update(combined_chars)
        elif event == '-INPUT_FILE-':
            input_file_path = values['-INPUT_FILE-']
            if input_file_path:
                output_folder = os.path.dirname(input_file_path)
                window['-OUTPUT_FOLDER-'].update(output_folder)

                window['-WEIGHT_LABEL-'].update(visible=False)
                window['-WEIGHT_COLUMN-'].update(visible=False)
                current_weights = []

                try:
                    font = TTFont(input_file_path)
                    if 'fvar' in font:
                        fvar = font['fvar']
                        weights_from_font = []
                        for axis in fvar.axes:
                            if axis.axisTag == 'wght':
                                min_w = int(axis.minValue)
                                max_w = int(axis.maxValue)
                                default_w = int(axis.defaultValue)
                                weights_from_font = sorted(list(set([min_w, 100, 200, 300, 400, 500, 600, 700, 800, 900, max_w, default_w])))
                                weights_from_font = [w for w in weights_from_font if min_w <= w <= max_w]
                                break

                        if weights_from_font:
                            window['-WEIGHT_LABEL-'].update(visible=True)
                            window['-WEIGHT_COLUMN-'].update(visible=True)
                            current_weights = weights_from_font
                            for i in range(10):
                                if i < len(current_weights):
                                    window[f'-W_{i}-'].update(text=str(current_weights[i]), visible=True, value=False)
                                else:
                                    window[f'-W_{i}-'].update(text='', visible=False, value=False)
                        else:
                            window['-WEIGHT_LABEL-'].update(visible=False)
                            window['-WEIGHT_COLUMN-'].update(visible=False)

                    else:
                        window['-WEIGHT_LABEL-'].update(visible=False)
                        window['-WEIGHT_COLUMN-'].update(visible=False)
                except Exception as e:
                    window['-OUTPUT-'].print(f"警告: 无法读取字体文件或检测字重。错误: {e}", text_color='orange')
                    window['-WEIGHT_LABEL-'].update(visible=False)
                    window['-WEIGHT_COLUMN-'].update(visible=False)
        elif event == '-CONVERT_BUTTON-':
            input_file = values['-INPUT_FILE-']
            output_folder = values['-OUTPUT_FOLDER-']
            subset_chars = values.get('-SUBSET_CHARS-', '') or ''

            weight_values = []
            for i in range(len(current_weights)):
                if values.get(f'-W_{i}-'):
                    weight_values.append(current_weights[i])

            quick_chars_from_checkboxes = []
            for i, option in enumerate(quick_char_options):
                if values.get(f'-QC_{i}-'):
                    quick_chars_from_checkboxes.append(option[1])
            quick_chars = ''.join(quick_chars_from_checkboxes)

            all_chars = ''.join(sorted(set(subset_chars + quick_chars))) if (subset_chars or quick_chars) else None

            if not input_file:
                sg.popup_error("请先选择一个字体文件！")
                continue

            if not weight_values:
                weight_values = [None]

            success_count = 0

            for weight_value in weight_values:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                output_filename = f"{base_name}_w{weight_value}.woff2" if weight_value is not None else f"{base_name}.woff2"
                
                final_output_path = os.path.join(output_folder or os.path.dirname(input_file), output_filename)

                window['-OUTPUT-'].print(f"正在处理文件: {input_file}")
                window['-OUTPUT-'].print(f"目标输出: {final_output_path}")
                if all_chars:
                    window['-OUTPUT-'].print(f"仅保留字符: {all_chars}")
                if weight_value:
                    window['-OUTPUT-'].print(f"字重: {weight_value}")

                success, message = convert_ttf_to_woff2_core(input_file, final_output_path, all_chars, weight_value)

                if success:
                    window['-OUTPUT-'].print(f"成功: {message}", text_color='green')
                    success_count += 1
                else:
                    window['-OUTPUT-'].print(f"失败: {message}", text_color='red')

            if success_count > 0:
                sg.popup_ok("转换完成！", f"成功转换 {success_count} 个文件。")
            else:
                sg.popup_error("转换失败！", "请检查状态信息。")
    window.close()


if __name__ == "__main__":
    try:
        import brotli
    except ImportError:
        sg.popup_error("错误: 缺少 'brotli' 库！\n"
                       "WOFF2 转换需要 Brotli 压缩算法。\n"
                       "请在终端运行 'pip install brotli' 安装后重试。")
        sys.exit(1)

    main_gui()



