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
    return "未分类" # 默认分组

# --- 辅助函数：解析单个 M3U 内容 ---
def parse_single_m3u(m3u_content):
    if not m3u_content:
        return [], {}, ""
        
    lines = [line.strip() for line in m3u_content.strip().split('\n') if line.strip()]
    
    channels_map = {}
    order_list = [] # 存储频道名
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
            # 提取最后一个逗号后的频道名称
            name_match = re.search(r',([^,]+)$', line)
            current_channel_name = name_match.group(1).strip() if name_match else None
            
            if current_channel_name:
                group_title = extract_group_title(current_info_line)
                if current_channel_name not in channels_map:
                    channels_map[current_channel_name] = {
                        "info": current_info_line, 
                        "urls": set(),
                        "group": group_title
                    }
                    order_list.append(current_channel_name)
                else:
                    # 如果已存在，更新其 info 和 group（以最后出现的为准）
                    channels_map[current_channel_name]["info"] = current_info_line
                    channels_map[current_channel_name]["group"] = group_title
            
        elif (line.startswith('http://') or line.startswith('https://')):
            if current_channel_name and current_channel_name in channels_map:
                channels_map[current_channel_name]["urls"].add(line)
        
        else:
            current_channel_name = None

    return order_list, channels_map, header

# --- 主函数 ---
def main():
    parser = argparse.ArgumentParser(
        description="合并M3U文件，仅基于频道名合并URL，并实现Group-Title优先的相对插入排序。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-i', '--input', type=str, nargs='+', required=True, help="一个或多个输入M3U文件的路径")
    parser.add_argument('-o', '--output', type=str, required=True, help="输出M3U文件的路径")
    args = parser.parse_args()
    
    # 存储所有频道的最终数据：{ 频道名: {info, urls, group} }
    final_channels_map = {}
    # 存储分组的全局顺序：[GroupA, GroupB, ...]
    group_global_order = []
    # 存储每个分组内的频道顺序：{ GroupA: [Name1, Name2, ...] }
    group_channels_order = {}
    
    final_header = ""
    
    for input_file in args.input:
        if not os.path.exists(input_file):
            print(f"警告: 文件不存在 '{input_file}'", file=sys.stderr)
            continue
            
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            curr_order, curr_map, header = parse_single_m3u(content)
            if not final_header: final_header = header
            
            # 按文件出现的顺序处理频道
            for name in curr_order:
                item = curr_map[name]
                new_group = item["group"]
                
                # 1. 更新或创建频道全局数据
                if name not in final_channels_map:
                    final_channels_map[name] = {
                        "info": item["info"],
                        "urls": item["urls"],
                        "group": new_group
                    }
                else:
                    # 合并 URL
                    final_channels_map[name]["urls"].update(item["urls"])
                    # 检查是否改变了分组
                    old_group = final_channels_map[name]["group"]
                    if old_group != new_group:
                        # 从旧组的顺序列表中移除
                        if old_group in group_channels_order and name in group_channels_order[old_group]:
                            group_channels_order[old_group].remove(name)
                        # 更新为新组
                        final_channels_map[name]["group"] = new_group
                    # 总是更新最新的 info 属性
                    final_channels_map[name]["info"] = item["info"]

                # 2. 维护分组的全局发现顺序
                if new_group not in group_global_order:
                    group_global_order.append(new_group)
                    group_channels_order[new_group] = []
                
                # 3. 执行组内相对插入排序逻辑
                target_order_list = group_channels_order[new_group]
                
                if name not in target_order_list:
                    # 找到当前文件内，该频道之前的频道在最终列表中的位置
                    # 为了简化，我们追踪该组内上一个处理的频道的索引
                    last_idx = -1
                    # 找到当前频道在当前文件组内的位置，探测其前面的邻居
                    # 这里直接使用 target_order_list 的“动态末尾”作为插入参考点
                    # 实际上，在同一个文件的同一个 Group 内，它们自然是顺序处理的
                    
                    # 寻找插入点：如果之前已经处理过该组的其他频道，last_idx 会被更新
                    # 如果这是新频道，将其插入到上一次在该组操作的位置之后
                    insert_pos = len(target_order_list) # 默认追加
                    
                    # 如果该频道在当前处理的文件中之前有邻居已经存在于 target_order_list
                    # 我们可以通过查找已存在的频道来精确定位，但最简单的实现是追踪上一个操作索引
                    # 这里采用您认可的 last_known_channel_index 逻辑
                    
                    # 逻辑：查找当前组内已有的频道中，在当前文件中排在 name 之前的最后一个频道
                    # 既然我们是按顺序遍历 curr_order，我们只需要记录该组上一次操作的位置即可
                    # 我们定义一个临时变量来辅助当前文件的处理
                    pass 

            # 重新执行一遍精确的组内相对插入（针对当前文件）
            # A. 提取当前文件中属于各个组的频道序列
            file_group_splits = {}
            for name in curr_order:
                g = final_channels_map[name]["group"]
                if g not in file_group_splits: file_group_splits[g] = []
                file_group_splits[g].append(name)
                
            # B. 对每个组应用相对插入
            for g, names in file_group_splits.items():
                target_list = group_channels_order[g]
                last_known_idx = -1
                for n in names:
                    if n in target_list:
                        last_known_idx = target_list.index(n)
                    else:
                        insert_at = last_known_idx + 1
                        target_list.insert(insert_at, n)
                        last_known_idx = insert_at

        except Exception as e:
            print(f"处理文件时出错: {e}", file=sys.stderr)

    # 3. 生成输出
    output_lines = [final_header] if final_header else ["#EXTM3U"]
    for group in group_global_order:
        for name in group_channels_order.get(group, []):
            data = final_channels_map[name]
            output_lines.append(data["info"])
            for url in sorted(list(data["urls"])):
                output_lines.append(url)
                
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        print(f"成功合并至: {args.output}")
    except Exception as e:
        print(f"写入失败: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
