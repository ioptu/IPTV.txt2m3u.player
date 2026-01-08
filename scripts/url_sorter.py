import argparse
import sys
import re
import os
import tempfile
import shutil

def sort_m3u_urls(input_file, output_file, keywords_str, reverse_mode=False, target_channels_str=None, new_name=None, force=False):
    # 1. 参数解析与标准化
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    target_channels = [c.strip() for c in target_channels_str.split(',') if c.strip()] if target_channels_str else None
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error: 无法读取输入文件: {e}")
        return False

    # 2. 结构化解析
    processed_content = []
    start_index = 0
    # 兼容处理首行（BOM 或 空格）
    if lines and '#EXTM3U' in lines[0]:
        processed_content.append(lines[0].strip())
        start_index = 1

    channels_data = []
    current_inf = None
    current_urls = []

    for line in lines[start_index:]:
        line = line.strip()
        if not line: continue
        if line.startswith('#EXTINF'):
            if current_inf:
                channels_data.append({"inf": current_inf, "urls": current_urls})
            current_inf = line
            current_urls = []
        else:
            current_urls.append(line)
    
    # 存入最后一个频道组
    if current_inf:
        channels_data.append({"inf": current_inf, "urls": current_urls})

    # 排序得分函数
    def get_sort_score(item):
        if "://" not in item: return 9999 # 非 URL 行保持在末尾
        for index, kw in enumerate(keywords):
            if kw in item:
                # 标准模式：关键字越靠前分数越低（负数）
                # 反向模式：关键字越靠前分数越高（正数）
                return (index + 1) if reverse_mode else (index - len(keywords))
        return 0 # 未匹配项分为 0

    # 重命名函数
    def rename_inf(inf_line, name):
        # 同步更新 tvg-name 属性
        if 'tvg-name="' in inf_line:
            inf_line = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{name}"', inf_line)
        # 更新末尾显示名称
        if ',' in inf_line:
            parts = inf_line.rsplit(',', 1)
            return f"{parts[0]},{name}"
        return f"{inf_line},{name}"

    # 3. 生成输出内容
    output_lines = []
    rename_count = 0
    sort_count = 0
    
    if processed_content:
        output_lines.append(processed_content[0])
    
    for ch in channels_data:
        # 条件 A: 频道名匹配（命中 -ch）
        name_match = any(tc in ch["inf"] for tc in target_channels) if target_channels else False
        
        # 条件 B: 旗下 URL 匹配（命中 -k）
        url_match = any(any(kw in url for kw in keywords) for url in ch["urls"])
        
        # 只有 A 和 B 同时成立，才执行重命名
        final_inf = ch["inf"]
        if name_match and url_match and new_name:
            final_inf = rename_inf(ch["inf"], new_name)
            rename_count += 1
        
        output_lines.append(final_inf)
        
        # 排序逻辑：如果指定了 -ch，则只对命中的频道排序；未指定则全局排
        should_sort = name_match if target_channels else True
        if should_sort and len(ch["urls"]) > 1:
            # 稳定排序保证了未匹配项保持原始相对顺序
            sorted_list = sorted(ch["urls"], key=get_sort_score)
            output_lines.extend(sorted_list)
            if sorted_list != ch["urls"]:  # 如果排序有变化
                sort_count += 1
        else:
            output_lines.extend(ch["urls"])
    
    return output_lines, rename_count, sort_count, len(channels_data)

def safe_write_output(lines, input_path, output_path):
    """
    安全地写入输出文件，支持同文件覆盖
    
    :param lines: 要写入的行列表
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :return: (success, temp_path) 成功返回(True, None)，失败返回(False, temp_path)
    """
    # 获取绝对路径以判断是否为同一个文件
    input_abs = os.path.abspath(input_path)
    output_abs = os.path.abspath(output_path)
    is_same_file = input_abs == output_abs
    
    temp_path = None
    
    try:
        # 如果是同一个文件，先写到临时文件
        if is_same_file:
            # 在与输出文件相同目录创建临时文件
            output_dir = os.path.dirname(output_path) or '.'
            fd, temp_path = tempfile.mkstemp(
                dir=output_dir,
                suffix='.m3u',
                prefix='.tmp_',
                text=True
            )
            
            # 使用文件描述符打开文件
            out_f = os.fdopen(fd, 'w', encoding='utf-8')
        else:
            # 直接打开输出文件
            out_f = open(output_path, 'w', encoding='utf-8')
        
        # 写入数据
        with out_f:
            for line in lines:
                out_f.write(line + '\n')
        
        # 如果是同一个文件，进行原子替换
        if is_same_file:
            try:
                # Python 3.3+ 推荐使用 os.replace 实现原子替换
                os.replace(temp_path, output_path)
                temp_path = None  # 替换成功，清除临时文件引用
            except Exception as e:
                # 如果 os.replace 失败，使用 shutil.move 作为备选
                print(f"警告：原子替换失败，使用备选方案: {e}")
                shutil.move(temp_path, output_path)
                temp_path = None  # 移动成功，清除临时文件引用
        
        return True, None
        
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False, temp_path

def validate_arguments(input_path, output_path):
    """
    验证命令行参数的合理性
    
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :return: 验证成功返回True，失败返回False
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误：输入文件 '{input_path}' 不存在")
        return False
    
    # 检查输入文件是否可读
    if not os.access(input_path, os.R_OK):
        print(f"错误：输入文件 '{input_path}' 不可读")
        return False
    
    # 检查是否为文件
    if not os.path.isfile(input_path):
        print(f"错误：'{input_path}' 不是文件")
        return False
    
    # 检查输入文件扩展名（可选警告）
    if not input_path.lower().endswith('.m3u'):
        print(f"警告：输入文件 '{input_path}' 可能不是标准M3U文件")
    
    # 检查输出目录是否可写
    output_dir = os.path.dirname(os.path.abspath(output_path)) or '.'
    if not os.access(output_dir, os.W_OK):
        print(f"错误：输出目录 '{output_dir}' 不可写")
        return False
    
    # 检查输入输出是否为同一文件（提供信息性提示）
    input_abs = os.path.abspath(input_path)
    output_abs = os.path.abspath(output_path)
    
    if input_abs == output_abs:
        print("信息：输入和输出为同一文件，将安全覆盖原文件")
    
    return True

def cleanup_temp_file(temp_path):
    """
    清理临时文件
    """
    if temp_path and os.path.exists(temp_path):
        try:
            os.unlink(temp_path)
            print(f"已清理临时文件: {temp_path}")
        except Exception as e:
            print(f"警告：无法删除临时文件 {temp_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="M3U 复合条件重命名与 URL 排序加固工具")
    parser.add_argument("-i", "--input", required=True, help="输入文件路径")
    parser.add_argument("-o", "--output", default="sorted_output.m3u", help="输出文件路径")
    parser.add_argument("-k", "--keywords", required=True, help="排序关键字，逗号分隔 (大小写敏感)")
    parser.add_argument("-r", "--reverse", action="store_true", help="开启反向模式 (匹配项放最后)")
    parser.add_argument("-ch", "--channels", help="目标频道名关键字，逗号分隔")
    parser.add_argument("-rn", "--rename", help="重命名 (仅在满足 -ch 且包含 -k 时生效)")
    parser.add_argument("--force", action="store_true", help="强制覆盖输出文件（如果已存在且与输入不同）")
    
    args = parser.parse_args()
    
    # 验证参数
    if not validate_arguments(args.input, args.output):
        sys.exit(1)
    
    # 检查输出文件是否已存在且与输入不同
    input_abs = os.path.abspath(args.input)
    output_abs = os.path.abspath(args.output)
    
    if os.path.exists(args.output) and input_abs != output_abs:
        if not args.force:
            print(f"错误：输出文件 '{args.output}' 已存在")
            print("使用 --force 参数强制覆盖，或指定不同的输出文件")
            sys.exit(1)
    
    # 处理M3U文件
    try:
        output_lines, rename_count, sort_count, total_channels = sort_m3u_urls(
            args.input, args.output, args.keywords, args.reverse, 
            args.channels, args.rename, args.force
        )
        
        if output_lines is False:  # 如果sort_m3u_urls返回False表示失败
            sys.exit(1)
        
        # 安全写入输出文件
        success, temp_path = safe_write_output(output_lines, args.input, args.output)
        
        # 如果失败，清理临时文件
        if not success:
            cleanup_temp_file(temp_path)
            print("处理失败！")
            sys.exit(1)
        
        # 输出统计信息
        print(f"✅ 处理成功！")
        print(f"   输入文件: {args.input}")
        print(f"   输出文件: {args.output}")
        print(f"   频道统计: {total_channels} 个频道")
        print(f"   排序统计: {sort_count} 个频道已排序")
        
        if args.rename:
            print(f"   重命名统计: {rename_count} 个频道已重命名为 '{args.rename}'")
        
        if args.reverse:
            print(f"   排序模式: 反向模式 (匹配项放最后)")
        else:
            print(f"   排序模式: 正向模式 (匹配项放前面)")
        
        if args.channels:
            print(f"   目标频道: {args.channels}")
        
        if input_abs == output_abs:
            print(f"   注意: 已安全覆盖原文件")
            
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
