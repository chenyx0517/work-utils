#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FontTool 自定义图标生成器
结合原有设计理念，创建更个性化的图标
"""

import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

def create_custom_font_icon(size=1024, 
                          bg_color=(52, 152, 219), 
                          accent_color=(41, 128, 185),
                          text_color=(255, 255, 255),
                          corner_radius=200,
                          design_style="modern"):
    """创建自定义字体工具图标 - 无边框版本"""
    
    # 创建基础图像，确保完全透明背景
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if design_style == "modern":
        # 现代风格 - 圆角矩形背景
        margin = size // 20
        draw.rounded_rectangle(
            [margin, margin, size-margin, size-margin], 
            radius=corner_radius, 
            fill=bg_color
        )
        
    elif design_style == "classic":
        # 经典风格 - 圆形背景
        margin = size // 20
        draw.ellipse(
            [margin, margin, size-margin, size-margin], 
            fill=bg_color
        )
        
    elif design_style == "minimal":
        # 极简风格 - 简单矩形
        margin = size // 15
        draw.rectangle(
            [margin, margin, size-margin, size-margin], 
            fill=bg_color
        )
    
    # 绘制字体相关图标
    center_x, center_y = size // 2, size // 2
    
    if design_style == "modern":
        # 现代风格 - FT字母 + 装饰
        draw_modern_ft_letters(draw, center_x, center_y, size, text_color)
        
    elif design_style == "classic":
        # 经典风格 - 字体符号
        draw_classic_font_symbols(draw, center_x, center_y, size, text_color)
        
    elif design_style == "minimal":
        # 极简风格 - 简单字母
        draw_minimal_letters(draw, center_x, center_y, size, text_color)
    
    return img

def draw_modern_ft_letters(draw, center_x, center_y, size, color):
    """绘制现代风格的FT字母"""
    letter_size = size // 3
    letter_thickness = size // 16
    
    # 字母 F
    f_x = center_x - letter_size // 2 - letter_size // 4
    f_y = center_y - letter_size // 2
    
    # F 的竖线
    draw.rectangle(
        [f_x, f_y, f_x + letter_thickness, f_y + letter_size],
        fill=color
    )
    # F 的横线
    draw.rectangle(
        [f_x, f_y, f_x + letter_size * 2//3, f_y + letter_thickness],
        fill=color
    )
    # F 的中间横线
    draw.rectangle(
        [f_x, f_y + letter_size//2 - letter_thickness//2, 
         f_x + letter_size//2, f_y + letter_size//2 + letter_thickness//2],
        fill=color
    )
    
    # 字母 T
    t_x = center_x + letter_size // 4
    t_y = center_y - letter_size // 2
    
    # T 的横线
    draw.rectangle(
        [t_x - letter_size//3, t_y, t_x + letter_size//3, t_y + letter_thickness],
        fill=color
    )
    # T 的竖线
    draw.rectangle(
        [t_x - letter_thickness//2, t_y, t_x + letter_thickness//2, t_y + letter_size],
        fill=color
    )
    
    # 添加装饰性元素
    dot_size = size // 20
    dot_spacing = size // 8
    
    # 在字母下方添加小圆点
    for i in range(3):
        dot_x = center_x - dot_spacing + i * dot_spacing
        dot_y = center_y + letter_size // 2 + dot_spacing
        draw.ellipse(
            [dot_x - dot_size//2, dot_y - dot_size//2, 
             dot_x + dot_size//2, dot_y + dot_size//2],
            fill=(*color[:3], 180)
        )

def draw_classic_font_symbols(draw, center_x, center_y, size, color):
    """绘制经典风格的字体符号"""
    # 绘制字体符号 - 类似"A"的形状
    symbol_size = size // 2.5
    
    # A 的左斜线
    left_x = center_x - symbol_size // 2
    right_x = center_x + symbol_size // 2
    top_y = center_y - symbol_size // 2
    bottom_y = center_y + symbol_size // 2
    mid_y = center_y
    
    # A 的左边
    draw.line([left_x, bottom_y, center_x, top_y], fill=color, width=size//32)
    # A 的右边
    draw.line([center_x, top_y, right_x, bottom_y], fill=color, width=size//32)
    # A 的横线
    draw.line([left_x + symbol_size//4, mid_y, right_x - symbol_size//4, mid_y], 
              fill=color, width=size//32)
    
    # 添加装饰性边框
    border_size = size // 8
    draw.rectangle(
        [center_x - border_size, center_y - border_size,
         center_x + border_size, center_y + border_size],
        outline=color, width=size//64
    )

def draw_minimal_letters(draw, center_x, center_y, size, color):
    """绘制极简风格的字母"""
    letter_size = size // 2.5
    letter_thickness = size // 20
    
    # 简单的 "F" 字母
    f_x = center_x - letter_size // 2
    f_y = center_y - letter_size // 2
    
    # F 的竖线
    draw.rectangle(
        [f_x, f_y, f_x + letter_thickness, f_y + letter_size],
        fill=color
    )
    # F 的横线
    draw.rectangle(
        [f_x, f_y, f_x + letter_size * 3//4, f_y + letter_thickness],
        fill=color
    )
    # F 的中间横线
    draw.rectangle(
        [f_x, f_y + letter_size//2 - letter_thickness//2, 
         f_x + letter_size//2, f_y + letter_size//2 + letter_thickness//2],
        fill=color
    )

def apply_rounded_corners(img, corner_radius):
    """应用圆角效果 - 改进版本，消除黑色边框"""
    # 创建透明背景的遮罩
    mask = Image.new('L', img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # 绘制圆角矩形，确保边缘完全透明
    mask_draw.rounded_rectangle(
        [(0, 0), img.size], 
        radius=corner_radius, 
        fill=255
    )
    
    # 应用遮罩，确保边缘完全透明
    img.putalpha(mask)
    
    # 进一步处理边缘，确保没有黑色边框
    # 创建一个新的透明图像
    result = Image.new('RGBA', img.size, (0, 0, 0, 0))
    
    # 将原图粘贴到新图像上
    result.paste(img, (0, 0), img)
    
    return result

def create_color_variants():
    """创建不同颜色主题的图标"""
    color_themes = {
        "blue": {
            "bg_color": (52, 152, 219),
            "accent_color": (41, 128, 185),
            "text_color": (255, 255, 255)
        },
        "green": {
            "bg_color": (46, 204, 113),
            "accent_color": (39, 174, 96),
            "text_color": (255, 255, 255)
        },
        "purple": {
            "bg_color": (155, 89, 182),
            "accent_color": (142, 68, 173),
            "text_color": (255, 255, 255)
        },
        "orange": {
            "bg_color": (230, 126, 34),
            "accent_color": (211, 84, 0),
            "text_color": (255, 255, 255)
        },
        "dark": {
            "bg_color": (52, 73, 94),
            "accent_color": (44, 62, 80),
            "text_color": (255, 255, 255)
        },
        # 新增高级低饱和度颜色主题
        "sage": {
            "bg_color": (134, 154, 140),  # 鼠尾草绿 - 低饱和度
            "accent_color": (108, 128, 114),  # 深一点的鼠尾草绿
            "text_color": (255, 255, 255)
        },
        "mauve": {
            "bg_color": (158, 142, 168),  # 淡紫色 - 低饱和度
            "accent_color": (132, 116, 142),  # 深一点的淡紫色
            "text_color": (255, 255, 255)
        },
        "slate": {
            "bg_color": (120, 130, 140),  # 石板灰蓝 - 低饱和度
            "accent_color": (100, 110, 120),  # 深一点的石板灰蓝
            "text_color": (255, 255, 255)
        },
        "taupe": {
            "bg_color": (150, 140, 130),  # 灰褐色 - 低饱和度
            "accent_color": (130, 120, 110),  # 深一点的灰褐色
            "text_color": (255, 255, 255)
        },
        "sage_light": {
            "bg_color": (200, 210, 205),  # 浅鼠尾草绿 - 非常低饱和度
            "accent_color": (180, 190, 185),  # 深一点的浅鼠尾草绿
            "text_color": (60, 70, 65)  # 深色文字
        }
    }
    
    return color_themes

def create_icon_variants():
    """创建不同风格和颜色的图标变体"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    styles = ["modern", "classic", "minimal"]
    color_themes = create_color_variants()
    
    icons = {}
    
    # 创建默认淡紫色现代风格图标（低饱和度高级色）
    base_size = 1024
    mauve_colors = color_themes["mauve"]
    base_icon = create_custom_font_icon(
        base_size, 
        design_style="modern",
        bg_color=mauve_colors["bg_color"],
        accent_color=mauve_colors["accent_color"],
        text_color=mauve_colors["text_color"]
    )
    
    for size in sizes:
        icon = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        # 不应用圆角处理，避免黑色边框
        icons[f"modern_mauve_{size}"] = icon
    
    # 创建其他风格和颜色的变体（仅1024尺寸）
    for style in styles:
        for theme_name, colors in color_themes.items():
            icon = create_custom_font_icon(
                1024, 
                design_style=style,
                **colors
            )
            # 不应用圆角处理，避免黑色边框
            icons[f"{style}_{theme_name}_1024"] = icon
    
    return icons

def save_icons(icons, output_dir="assets/icons"):
    """保存图标文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存默认图标（现代淡紫色风格）
    default_icon = icons["modern_mauve_1024"]
    main_path = os.path.join(output_dir, "icon_base.png")
    default_icon.save(main_path, "PNG")
    print(f"✅ 保存主图标: {main_path}")
    
    # 保存多尺寸图标
    for size in [16, 32, 64, 128, 256, 512, 1024]:
        key = f"modern_mauve_{size}"
        if key in icons:
            filename = f"icon_{size}x{size}.png"
            filepath = os.path.join(output_dir, filename)
            icons[key].save(filepath, "PNG")
            print(f"✅ 保存图标: {filepath}")
    
    # 保存其他风格变体（供选择）
    variants_dir = os.path.join(output_dir, "variants")
    os.makedirs(variants_dir, exist_ok=True)
    
    for key, icon in icons.items():
        if "_1024" in key and not key.startswith("modern_mauve"):
            filename = f"{key}.png"
            filepath = os.path.join(variants_dir, filename)
            icon.save(filepath, "PNG")
            print(f"✅ 保存变体: {filepath}")
    
    return main_path

def create_icns_file(png_path, output_dir="assets/icons"):
    """创建.icns文件"""
    icns_path = os.path.join(output_dir, "icon.icns")
    
    # 创建iconset目录
    iconset_dir = os.path.join(output_dir, "FontTool.iconset")
    os.makedirs(iconset_dir, exist_ok=True)
    
    # 复制不同尺寸的图标到iconset
    sizes_mapping = {
        16: "icon_16x16.png",
        32: "icon_16x16@2x.png",
        32: "icon_32x32.png", 
        64: "icon_32x32@2x.png",
        128: "icon_128x128.png",
        256: "icon_128x128@2x.png",
        256: "icon_256x256.png",
        512: "icon_256x256@2x.png",
        512: "icon_512x512.png",
        1024: "icon_512x512@2x.png"
    }
    
    for size, filename in sizes_mapping.items():
        src_file = os.path.join(output_dir, f"icon_{size}x{size}.png")
        dst_file = os.path.join(iconset_dir, filename)
        if os.path.exists(src_file):
            os.system(f"cp '{src_file}' '{dst_file}'")
    
    # 使用iconutil创建icns文件
    cmd = f"iconutil -c icns '{iconset_dir}' -o '{icns_path}'"
    result = os.system(cmd)
    
    # 清理临时目录
    os.system(f"rm -rf '{iconset_dir}'")
    
    if result == 0:
        print(f"✅ 创建icns文件: {icns_path}")
    else:
        print(f"⚠️  无法创建icns文件，请手动转换")
    
    return icns_path

def main():
    """主函数"""
    print("🎨 开始创建FontTool自定义图标...")
    print("📋 可用的设计风格:")
    print("   - modern: 现代圆角风格 (默认)")
    print("   - classic: 经典圆形风格") 
    print("   - minimal: 极简矩形风格")
    print("🎨 可用的颜色主题:")
    print("   - mauve: 淡紫色主题 (默认) - 低饱和度高级色")
    print("   - sage: 鼠尾草绿主题 - 低饱和度")
    print("   - slate: 石板灰蓝主题 - 低饱和度")
    print("   - taupe: 灰褐色主题 - 低饱和度")
    print("   - sage_light: 浅鼠尾草绿主题 - 极低饱和度")
    print("   - blue: 蓝色主题")
    print("   - green: 绿色主题")
    print("   - purple: 紫色主题")
    print("   - orange: 橙色主题")
    print("   - dark: 深色主题")
    
    # 创建图标变体
    icons = create_icon_variants()
    
    # 保存图标
    main_png = save_icons(icons)
    
    # 创建icns文件
    create_icns_file(main_png)
    
    print("🎉 图标创建完成！")
    print(f"📁 主图标位置: {main_png}")
    print(f"📁 变体图标位置: assets/icons/variants/")
    print("💡 提示: 查看 variants 目录中的其他风格和颜色变体")

if __name__ == "__main__":
    main()

