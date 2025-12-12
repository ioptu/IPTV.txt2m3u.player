import re
import argparse
import sys
import os

# --- 辅助函数：提取 Group-Title ---
def extract_group_title(info_line):
    """从 #EXTINF 行中提取 group-title 的值。"""
    match = re.search(r'group-title="([^"]*)"', info_line)
    if match:
        return match.group(1).strip()
    return ""

# --- 辅助函数：解析单个 M3U 内容 ---
# 仍然返回 order_list, channels_map, header，但 channels_map 现在包含 group 信息
def parse_single_m3u(m3u_content):
    if not m3u_content:
        return [], {}, ""
        
    lines = [line.strip() for line in m3u_content.strip().split('\n') if line.strip()]
    
    # channels_map 结构: { "频道名称": {"info": "#EXTINF...", "urls": set(), "group": "..."} }
    channels_map = {}
    order_list = []
    header = ""
    
    current_info_line = None
    current_channel_name = None
    
    for line in lines:
        if line.startswith('#EXTM3U'):
            if not header:
                header = line
            continue

        if line.startswith('#EXTINF:'):
            current_info_line = line
            name_match = re.search(r',(.+)$', line)
            current_channel_name = name_match.group(1).strip() if name_match else None
            group_title = extract_group_title(current_info_line)
            
            if current_channel_name:
                if current_channel_name not in channels_map:
                    channels_map[current_channel_name] = {
                        "info": current_info_line, 
                        "urls": set(),
                        "group": group_title
                    }
                    order_list.append(current_channel_name)
                else:
                    channels_map[current_channel_name]["info"] = current_info_line
                    channels_map[current_channel_name]["group"] = group_title
            
        elif (line.startswith('http://') or line.startswith('https://')):
            if current_channel_name and current_channel_name in channels_map:
                channels_map[current_channel_name]["urls"].add(line)
        
        else:
            current_channel_name = None

    return order_list, channels_map, header


# --- 主函数：实现 Group-Title 优先的相对插入排序逻辑 ---
def main():
    parser = argparse.ArgumentParser(
        description="合并多个M3U文件的内容，按 Group-Title 排序，并在组内使用相对插入排序。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-i', '--input', type=str, nargs='+', required=True, help="一个或多个输入M3U文件的路径")
    parser.add_argument('-o', '--output', type=str, required=True, help="输出M3U文件的路径")
    args = parser.parse_args()
    
    if not args.input:
        print("错误: 请提供至少一个输入文件。", file=sys.stderr)
        sys.exit(1)
        
    # 主数据结构：
    # final_channels_data = {
    #     "group_name": {
    #         "channels": { "频道名": {"info": "#EXTINF...", "urls": set()} },
    #         "order_list": ["频道名1", "频道名2", ...] # 该分组的内部顺序列表
    #     }
    # }
    final_channels_data = {}
    # 记录 Group-Title 首次出现的顺序（用于最终 Group 排序）
    group_global_order = [] 
    final_header = ""
    
    # 1. 遍历所有输入文件并合并数据
    for input_file in args.input:
        if not os.path.exists(input_file):
            print(f"警告: 输入文件 '{input_file}' 不存在。跳过。", file=sys.stderr)
            continue
        if input_file == args.output:
            print(f"警告: 输入文件 '{input_file}' 和输出文件不能是同一个文件。跳过。", file=sys.stderr)
            continue
            
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            current_order_list, current_map, header = parse_single_m3u(content)
            
            if not final_header and header:
                final_header = header
            
            # 针对当前文件中的每个 Group-Title 执行相对插入逻辑
            
            # A. 将当前文件的所有频道按 Group-Title 分组
            current_groups = {}
            for channel_name in current_order_list:
                data = current_map[channel_name]
                group = data["group"]
                if group not in current_groups:
                    current_groups[group] = []
                current_groups[group].append(channel_name)

            # B. 遍历当前文件中的 Group-Title，执行合并和相对插入
            for group_title, current_group_channels in current_groups.items():
                
                # 1. 初始化 Group 数据
                if group_title not in final_channels_data:
                    final_channels_data[group_title] = {"channels": {}, "order_list": []}
                    group_global_order.append(group_title) # 记录新的 Group 顺序
                
                final_group_data = final_channels_data[group_title]
                final_group_channels = final_group_data["channels"]
                final_group_order = final_group_data["order_list"]
                
                # 2. 执行组内相对插入排序
                last_known_channel_index = -1
                
                # 预扫描：找到当前文件中的频道在 final_group_order 中最后出现的位置
                # 注意：这里我们不再进行预扫描，因为组内顺序是动态插入的。
                # last_known_channel_index 将追踪上一个已处理/已插入的频道位置。

                for channel_name in current_group_channels:
                    current_channel_data = current_map[channel_name]

                    if channel_name in final_group_channels:
                        # 频道已存在: A. 合并 URL 并更新属性
                        
                        # 更新 info/urls
                        final_group_channels[channel_name]["info"] = current_channel_data["info"]
                        final_group_channels[channel_name]["urls"].update(current_channel_data["urls"])
                        
                        # 更新 last_known_channel_index
                        try:
                            # 找到该频道在 Group Order 列表中的位置
                            last_known_channel_index = final_group_order.index(channel_name)
                        except ValueError:
                            # 理论上不会发生，但以防万一
                            pass
                            
                    else:
                        # 频道是新的: B. 相对插入
                        
                        # 1. 将新频道添加到 Group Map
                        final_group_channels[channel_name] = {
                            "info": current_channel_data["info"], 
                            "urls": current_channel_data["urls"] # 直接赋值集合
                        }
                        
                        # 2. 插入到 order_list 中，位置是 last_known_channel_index + 1
                        insert_index = last_known_channel_index + 1
                        final_group_order.insert(insert_index, channel_name)
                        
                        # 3. 更新 last_known_channel_index
                        last_known_channel_index = insert_index
                        
        except Exception as e:
            print(f"处理文件 '{input_file}' 时发生错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 2. 写入最终结果：按 Group Global Order 和 Group Order List 写入
    output_lines = [final_header] if final_header else []
    
    for group_title in group_global_order:
        if group_title in final_channels_data:
            group_data = final_channels_data[group_title]
            
            # 遍历该 Group 内部的频道顺序
            for name in group_data["order_list"]:
                if name in group_data["channels"]:
                    data = group_data["channels"][name]
                    
                    # 写入 EXTINF 行
                    output_lines.append(data["info"])
                    
                    # 写入 URL 行 (排序后，保持稳定)
                    for url in sorted(list(data["urls"])):
                        output_lines.append(url)
                
    modified_m3u = '\n'.join(output_lines)

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(modified_m3u)
            
        print(f"成功: {len(args.input)} 个 M3U 文件已合并，并使用 Group-Title 优先的相对插入排序写入到 '{args.output}'")
        
    except Exception as e:
        print(f"写入文件时发生错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
