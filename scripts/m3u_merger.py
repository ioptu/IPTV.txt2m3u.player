import re
import argparse
import sys
import os
import tempfile
import shutil

# --- 辅助函数：提取 Group-Title ---
def extract_group_title(info_line):
    """从 #EXTINF 行中提取 group-title 的值。"""
    match = re.search(r'group-title="([^"]*)"', info_line)
    if match:
        return match.group(1).strip()
    return ""

# --- 辅助函数：解析单个 M3U 内容 (支持多URL) ---
def parse_single_m3u(m3u_content):
    if not m3u_content:
        return [], {}, ""
        
    lines = [line.strip() for line in m3u_content.strip().split('\n') if line.strip()]
    
    # channels_map 结构: { ("频道名称", "Group-Title"): {"info": "#EXTINF...", "urls": set()} }
    channels_map = {}
    order_list = [] # 包含 ("频道名称", "Group-Title") 复合键
    header = ""
    
    current_info_line = None
    current_channel_name = None
    current_group_title = None
    current_config_lines = []  # 存储配置行
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('#EXTM3U'):
            if not header:
                header = line
            i += 1
            continue

        if line.startswith('#EXTINF:'):
            # 如果之前有频道数据，先保存
            if current_info_line and current_channel_name:
                channel_key = (current_channel_name, current_group_title)
                
                if channel_key not in channels_map:
                    channels_map[channel_key] = {
                        "info": current_info_line, 
                        "urls": set(),
                        "configs": list(current_config_lines)  # 保存配置行
                    }
                    order_list.append(channel_key)
                else:
                    # 合并到已存在的频道
                    channels_map[channel_key]["info"] = current_info_line
                    channels_map[channel_key]["configs"].extend(current_config_lines)
            
            # 开始新频道
            current_info_line = line
            name_match = re.search(r',(.+)$', line)
            current_channel_name = name_match.group(1).strip() if name_match else None
            current_group_title = extract_group_title(current_info_line)
            current_config_lines = []  # 重置配置行
            i += 1
            
        elif line.startswith('#') and not line.startswith('#EXTINF:'):
            # 收集配置行（如#EXTVLCOPT）
            current_config_lines.append(line)
            i += 1
            
        elif line.startswith(('http://', 'https://')):
            # URL 属于最近解析成功的频道实体
            if current_channel_name and current_group_title is not None:
                channel_key = (current_channel_name, current_group_title)
                if channel_key not in channels_map:
                    # 如果还没有创建频道实体，先创建
                    channels_map[channel_key] = {
                        "info": current_info_line, 
                        "urls": set(),
                        "configs": list(current_config_lines)
                    }
                    order_list.append(channel_key)
                channels_map[channel_key]["urls"].add(line)
            i += 1
            
        else:
            # 未知行，跳过
            i += 1
    
    # 处理最后一个频道
    if current_info_line and current_channel_name:
        channel_key = (current_channel_name, current_group_title)
        
        if channel_key not in channels_map:
            channels_map[channel_key] = {
                "info": current_info_line, 
                "urls": set(),
                "configs": list(current_config_lines)
            }
            order_list.append(channel_key)
        else:
            channels_map[channel_key]["info"] = current_info_line
            channels_map[channel_key]["configs"].extend(current_config_lines)

    return order_list, channels_map, header

# --- 安全文件写入函数 ---
def safe_write_output(content, input_files, output_path):
    """
    安全地写入输出文件，支持输入文件包含输出文件的情况
    """
    # 检查输出文件是否在输入文件中
    output_abs = os.path.abspath(output_path)
    input_abs_list = [os.path.abspath(f) for f in input_files if os.path.exists(f)]
    
    is_output_in_inputs = output_abs in input_abs_list
    temp_path = None
    
    try:
        if is_output_in_inputs:
            output_dir = os.path.dirname(output_path) or '.'
            fd, temp_path = tempfile.mkstemp(
                dir=output_dir,
                suffix='.m3u',
                prefix='.tmp_',
                text=True
            )
            out_f = os.fdopen(fd, 'w', encoding='utf-8')
        else:
            out_f = open(output_path, 'w', encoding='utf-8')
        
        with out_f:
            out_f.write(content)
        
        if is_output_in_inputs:
            try:
                os.replace(temp_path, output_path)
                temp_path = None
            except Exception as e:
                print(f"警告：原子替换失败，使用备选方案: {e}")
                shutil.move(temp_path, output_path)
                temp_path = None
        
        return True, None
        
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False, temp_path

# --- 验证参数函数 ---
def validate_arguments(input_files, output_path):
    """
    验证命令行参数的合理性
    """
    valid_inputs = []
    for input_file in input_files:
        if not os.path.exists(input_file):
            print(f"警告: 输入文件 '{input_file}' 不存在。", file=sys.stderr)
            continue
        
        if not os.access(input_file, os.R_OK):
            print(f"错误: 输入文件 '{input_file}' 不可读", file=sys.stderr)
            return False
        
        if not os.path.isfile(input_file):
            print(f"错误: '{input_file}' 不是文件", file=sys.stderr)
            return False
        
        if not input_file.lower().endswith('.m3u'):
            print(f"警告: 输入文件 '{input_file}' 可能不是标准M3U文件", file=sys.stderr)
        
        valid_inputs.append(input_file)
    
    if not valid_inputs:
        print("错误: 没有有效的输入文件", file=sys.stderr)
        return False
    
    output_dir = os.path.dirname(os.path.abspath(output_path)) or '.'
    if not os.access(output_dir, os.W_OK):
        print(f"错误: 输出目录 '{output_dir}' 不可写", file=sys.stderr)
        return False
    
    output_abs = os.path.abspath(output_path)
    if output_abs in [os.path.abspath(f) for f in valid_inputs]:
        print(f"信息: 输出文件 '{output_path}' 是输入文件之一，将安全覆盖", file=sys.stderr)
    
    return True

# --- 主函数：支持多URL的合并 ---
def main():
    parser = argparse.ArgumentParser(
        description="合并M3U文件，支持一个频道下多个URL的合并，并进行 Group-Title 优先的相对插入排序。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-i', '--input', type=str, nargs='+', required=True, 
                       help="一个或多个输入M3U文件的路径")
    parser.add_argument('-o', '--output', type=str, required=True, 
                       help="输出M3U文件的路径")
    parser.add_argument('--force', action='store_true',
                       help="强制操作，即使输出文件已存在且不是输入文件")
    parser.add_argument('--no-config', action='store_true',
                       help="不保留配置行（如#EXTVLCOPT）")
    
    args = parser.parse_args()
    
    if not args.input:
        print("错误: 请提供至少一个输入文件。", file=sys.stderr)
        sys.exit(1)
    
    if not validate_arguments(args.input, args.output):
        sys.exit(1)
    
    output_abs = os.path.abspath(args.output)
    input_abs_list = [os.path.abspath(f) for f in args.input if os.path.exists(f)]
    
    if os.path.exists(args.output) and output_abs not in input_abs_list:
        if not args.force:
            print(f"错误: 输出文件 '{args.output}' 已存在且不是输入文件", file=sys.stderr)
            print("      使用 --force 参数强制覆盖，或指定不同的输出文件", file=sys.stderr)
            sys.exit(1)
    
    final_channels_data = {}
    group_global_order = [] 
    final_header = ""
    
    valid_input_files = []
    for input_file in args.input:
        if not os.path.exists(input_file):
            print(f"警告: 输入文件 '{input_file}' 不存在。跳过。", file=sys.stderr)
            continue
            
        valid_input_files.append(input_file)
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            current_order_list, current_map, header = parse_single_m3u(content)
            
            if not final_header and header:
                final_header = header
            
            current_groups = {}
            for channel_key in current_order_list:
                _, group = channel_key
                data = current_map[channel_key]
                
                if group not in current_groups:
                    current_groups[group] = []
                current_groups[group].append((channel_key, data)) 

            for group_title, current_group_items in current_groups.items():
                if group_title not in final_channels_data:
                    final_channels_data[group_title] = {"channels": {}, "order_list": []}
                    group_global_order.append(group_title)
                
                final_group_data = final_channels_data[group_title]
                final_group_channels = final_group_data["channels"]
                final_group_order = final_group_data["order_list"]
                
                last_known_channel_index = -1

                for channel_key, current_channel_data in current_group_items:
                    channel_name, _ = channel_key
                    
                    if channel_name in final_group_channels:
                        # 合并：更新info，合并URL和配置行
                        final_group_channels[channel_name]["info"] = current_channel_data["info"]
                        final_group_channels[channel_name]["urls"].update(current_channel_data["urls"])
                        
                        # 合并配置行（去重）
                        existing_configs = final_group_channels[channel_name].get("configs", [])
                        new_configs = current_channel_data.get("configs", [])
                        all_configs = list(set(existing_configs + new_configs))
                        final_group_channels[channel_name]["configs"] = all_configs
                        
                        try:
                            last_known_channel_index = final_group_order.index(channel_name)
                        except ValueError:
                            pass
                            
                    else:
                        # 新频道：添加
                        final_group_channels[channel_name] = {
                            "info": current_channel_data["info"], 
                            "urls": current_channel_data["urls"],
                            "configs": current_channel_data.get("configs", [])
                        }
                        
                        insert_index = last_known_channel_index + 1
                        final_group_order.insert(insert_index, channel_name)
                        last_known_channel_index = insert_index
                        
        except Exception as e:
            print(f"处理文件 '{input_file}' 时发生错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 生成最终内容
    output_lines = [final_header] if final_header else []
    
    for group_title in group_global_order:
        if group_title in final_channels_data:
            group_data = final_channels_data[group_title]
            
            for name in group_data["order_list"]:
                if name in group_data["channels"]:
                    data = group_data["channels"][name]
                    
                    output_lines.append(data["info"])
                    
                    # 写入配置行（如果启用）
                    if not args.no_config and data.get("configs"):
                        for config in data["configs"]:
                            output_lines.append(config)
                    
                    # 写入URL行（排序后）
                    for url in sorted(list(data["urls"])):
                        output_lines.append(url)
                
    modified_m3u = '\n'.join(output_lines)

    # 安全写入
    success, temp_path = safe_write_output(modified_m3u, valid_input_files, args.output)
    
    if not success:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        print("处理失败！", file=sys.stderr)
        sys.exit(1)
    
    # 统计信息
    total_channels = 0
    total_groups = len(group_global_order)
    total_urls = 0
    
    for group_title in group_global_order:
        if group_title in final_channels_data:
            group_data = final_channels_data[group_title]
            total_channels += len(group_data["order_list"])
            for name in group_data["order_list"]:
                if name in group_data["channels"]:
                    data = group_data["channels"][name]
                    total_urls += len(data["urls"])
    
    print(f"成功: {len(valid_input_files)} 个 M3U 文件已合并", file=sys.stderr)
    print(f"      共 {total_channels} 个频道，{total_groups} 个分组", file=sys.stderr)
    print(f"      合并了 {total_urls} 个URL", file=sys.stderr)
    
    if args.no_config:
        print(f"      已过滤所有配置行", file=sys.stderr)
    
    # 显示多URL频道统计
    multi_url_channels = 0
    for group_title in group_global_order:
        if group_title in final_channels_data:
            group_data = final_channels_data[group_title]
            for name in group_data["order_list"]:
                if name in group_data["channels"]:
                    data = group_data["channels"][name]
                    if len(data["urls"]) > 1:
                        multi_url_channels += 1
    
    if multi_url_channels > 0:
        print(f"      其中 {multi_url_channels} 个频道有多个URL源", file=sys.stderr)
    
    print(f"      结果已写入 '{args.output}'", file=sys.stderr)
    
    if output_abs in [os.path.abspath(f) for f in valid_input_files]:
        print(f"注意: 已安全覆盖输入文件 '{args.output}'", file=sys.stderr)

if __name__ == "__main__":
    main()
