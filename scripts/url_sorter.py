import argparse
import sys
import re
import os
import tempfile
import shutil
from typing import List, Dict, Optional, Tuple, Set

def parse_extinf_group(extinf_line: str) -> Optional[str]:
    """
    从EXTINF行解析group-title属性
    
    Args:
        extinf_line: EXTINF行字符串
        
    Returns:
        str: 频道组名，如果没有则返回None
    """
    # 查找 group-title="..." 模式
    group_match = re.search(r'group-title="([^"]*)"', extinf_line)
    if group_match:
        return group_match.group(1)
    
    # 也可以尝试查找 group-title='...' 单引号模式
    group_match = re.search(r"group-title='([^']*)'", extinf_line)
    if group_match:
        return group_match.group(1)
    
    return None

def update_extinf_group(extinf_line: str, new_group_name: str) -> str:
    """
    更新EXTINF行中的group-title属性
    
    Args:
        extinf_line: 原始的EXTINF行
        new_group_name: 新的频道组名
        
    Returns:
        str: 更新后的EXTINF行
    """
    # 如果已有group-title属性，替换它
    if 'group-title="' in extinf_line:
        updated_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group_name}"', extinf_line)
    elif "group-title='" in extinf_line:
        updated_line = re.sub(r"group-title='[^']*'", f"group-title='{new_group_name}'", updated_line)
    else:
        # 如果没有group-title属性，需要添加
        # 找到频道名部分（最后一个逗号之后）
        if ',' in extinf_line:
            parts = extinf_line.rsplit(',', 1)
            # 在属性和频道名之间插入group-title
            attributes = parts[0]
            channel_name = parts[1]
            # 确保属性以空格结尾或有合适的格式
            if attributes.endswith('"'):
                updated_line = f'{attributes} group-title="{new_group_name}",{channel_name}'
            else:
                updated_line = f'{attributes} group-title="{new_group_name}",{channel_name}'
        else:
            # 如果格式不符合预期，直接返回原行
            return extinf_line
    
    return updated_line

def parse_m3u_file(lines: List[str]) -> Tuple[List[Dict], List[str]]:
    """
    解析M3U文件，支持多种格式
    
    Args:
        lines: M3U文件的所有行
        
    Returns:
        tuple: (channels_data, header_lines)
    """
    channels_data = []
    header_lines = []
    
    # 存储当前解析状态
    current_inf = None
    current_urls = []
    current_group = None
    current_extgrp = None  # 存储EXTGRP行内容
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # 处理文件头
        if i == 0 and (line.startswith('#EXTM3U') or line.startswith('#PLAYLIST')):
            header_lines.append(line)
            i += 1
            continue
        
        # 处理其他可能的头部注释
        if i < 3 and line.startswith('#'):
            if not line.startswith('#EXTINF') and not line.startswith('#EXTGRP'):
                header_lines.append(line)
                i += 1
                continue
        
        # 处理EXTGRP标签
        if line.startswith('#EXTGRP:'):
            current_extgrp = line  # 保存EXTGRP行
            current_group = line.replace('#EXTGRP:', '').strip()
            i += 1
            continue
        
        # 处理EXTINF行
        if line.startswith('#EXTINF'):
            # 保存上一个频道
            if current_inf:
                # 确定组名：优先使用EXTGRP，其次使用group-title属性
                group = current_group
                if group is None:
                    group = parse_extinf_group(current_inf)
                
                channels_data.append({
                    "inf": current_inf, 
                    "urls": current_urls,
                    "group": group,
                    "extgrp_line": current_extgrp  # 保存EXTGRP行（如果有）
                })
            
            # 开始新频道
            current_inf = line
            current_urls = []
            current_group = parse_extinf_group(line)  # 尝试从EXTINF解析组名
            current_extgrp = None  # 重置EXTGRP
            i += 1
            continue
        
        # 处理URL行
        if not line.startswith('#'):  # 排除其他注释行
            current_urls.append(line)
            i += 1
            continue
        
        # 其他注释行直接跳过
        i += 1
    
    # 保存最后一个频道
    if current_inf:
        # 确定组名：优先使用EXTGRP，其次使用group-title属性
        group = current_group
        if group is None:
            group = parse_extinf_group(current_inf)
        
        channels_data.append({
            "inf": current_inf, 
            "urls": current_urls,
            "group": group,
            "extgrp_line": current_extgrp
        })
    
    return channels_data, header_lines

def sort_m3u_urls(input_file: str, output_file: str, keywords_str: str, 
                  reverse_mode: bool = False, target_channels_str: Optional[str] = None,
                  new_name: Optional[str] = None, force: bool = False,
                  group_names_str: Optional[str] = None, rename_group: Optional[str] = None,
                  group_sort: bool = False) -> Tuple[List[str], int, int, int, int, int, int]:
    """
    处理M3U文件，支持URL排序和条件重命名
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        keywords_str: URL排序关键字字符串，逗号分隔
        reverse_mode: 是否反向排序
        target_channels_str: 目标频道名关键字，逗号分隔
        new_name: 重命名后的频道名
        force: 是否强制覆盖输出文件
        group_names_str: 频道组名关键字，逗号分隔
        rename_group: 重命名后的频道组名
        group_sort: 是否对频道组进行排序（组间排序）
        
    Returns:
        tuple: (output_lines, rename_count, sort_count, total_channels, 
                group_rename_count, group_sort_count, group_rename_with_k_count)
    """
    # 1. 参数解析与标准化
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    target_channels = [c.strip() for c in target_channels_str.split(',') if c.strip()] if target_channels_str else None
    group_names = [g.strip() for g in group_names_str.split(',') if g.strip()] if group_names_str else None
    
    # 检查是否进入重命名模式
    rename_mode = bool(new_name or rename_group)
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error: 无法读取输入文件: {e}")
        return None, 0, 0, 0, 0, 0, 0
    
    # 2. 结构化解析
    channels_data, header_lines = parse_m3u_file([line.rstrip('\n') for line in lines])
    
    # 排序得分函数（URL排序）- 只对URL进行关键字匹配
    def get_url_sort_score(item: str) -> int:
        if "://" not in item: 
            return 9999  # 非 URL 行保持在末尾
        
        # 只在URL中查找关键字
        for index, kw in enumerate(keywords):
            if kw.lower() in item.lower():  # 不区分大小写匹配
                # 标准模式：关键字越靠前分数越低（负数）
                # 反向模式：关键字越靠前分数越高（正数）
                return (index + 1) if reverse_mode else (index - len(keywords))
        return 0  # 未匹配项分为 0

    # 频道组排序得分函数（组间排序）- 基于group-title匹配
    def get_group_sort_score(channel_data: Dict) -> int:
        """为频道组排序计算得分（只基于group-title）"""
        ch_group = channel_data.get("group", "")
        
        # 如果指定了组名关键词，匹配的组排在前面
        if group_names:
            for index, group_kw in enumerate(group_names):
                if group_kw.lower() in ch_group.lower():  # 不区分大小写匹配
                    # 返回负数确保匹配的组排在前面
                    return index - len(group_names)
        return 0  # 未指定组名或未匹配的组

    # 重命名频道函数
    def rename_inf(inf_line: str, name: str) -> str:
        # 同步更新 tvg-name 属性
        if 'tvg-name="' in inf_line:
            inf_line = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{name}"', inf_line)
        elif "tvg-name='" in inf_line:
            inf_line = re.sub(r"tvg-name='[^']*'", f"tvg-name='{name}'", inf_line)
        
        # 更新末尾显示名称
        if ',' in inf_line:
            parts = inf_line.rsplit(',', 1)
            return f"{parts[0]},{name}"
        return f"{inf_line},{name}"

    # 3. 生成输出内容
    output_lines = []
    rename_count = 0
    sort_count = 0
    group_rename_count = 0
    group_sort_count = 0
    group_rename_with_k_count = 0
    
    # 添加文件头
    output_lines.extend(header_lines)
    
    # 如果需要组间排序，先对channels_data排序
    if group_sort and group_names and not rename_mode:
        channels_data.sort(key=get_group_sort_score)
        group_sort_count = 1  # 标记组间排序已执行
    
    # 处理每个频道
    processed_groups = set()
    last_group = None  # 跟踪上一个频道组，用于避免重复输出EXTGRP
    
    for ch in channels_data:
        ch_group = ch.get("group", "")
        extgrp_line = ch.get("extgrp_line")
        
        # 条件 A: 频道名匹配（命中 -ch）- 在EXTINF行中查找
        name_match = any(tc.lower() in ch["inf"].lower() for tc in target_channels) if target_channels else False
        
        # 条件 B: 旗下 URL 匹配（命中 -k）- 在URL中查找关键字
        url_match_for_rename = any(any(kw.lower() in url.lower() for kw in keywords) for url in ch["urls"])
        
        # 条件 C: 频道组匹配（命中 -gr）- 在group-title中查找
        group_match = any(gn.lower() in ch_group.lower() for gn in group_names) if group_names else True
        
        # 判断是否需要处理当前频道
        should_process = True
        if group_names and not group_match:
            # 不匹配的频道组，如果只是组内排序则跳过，如果是组间排序则保留
            should_process = not group_sort or (group_sort and not rename_mode)
        
        # ========== 输出EXTGRP行（如果需要）==========
        # 只有在组发生变化且该频道有EXTGRP行或需要显示组信息时才输出
        if ch_group and ch_group != last_group:
            # 在重命名模式下，如果有EXTGRP行且满足条件，可能需要修改它
            if rename_mode and rename_group and group_match:
                # 判断是否应该重命名这个组
                should_rename_this_group = False
                
                if not keywords and not target_channels:
                    # 情况1: 只有 -gr + -rg (无 -k 和 -ch)
                    should_rename_this_group = True
                elif keywords and not target_channels and url_match_for_rename:
                    # 情况2: -gr + -rg + -k (无 -ch)
                    should_rename_this_group = True
                elif not keywords and target_channels and name_match:
                    # 情况3: -gr + -rg + -ch (无 -k)
                    should_rename_this_group = True
                elif keywords and target_channels and name_match and url_match_for_rename:
                    # 情况4: -gr + -rg + -k + -ch
                    should_rename_this_group = True
                
                if should_rename_this_group:
                    output_lines.append(f"#EXTGRP:{rename_group}")
                    if ch_group not in processed_groups:
                        group_rename_count += 1
                        processed_groups.add(ch_group)
                        if keywords:
                            group_rename_with_k_count += 1
                    last_group = ch_group  # 更新last_group为新组名
                else:
                    # 不重命名，输出原EXTGRP行或跳过
                    if extgrp_line:
                        output_lines.append(extgrp_line)
                    last_group = ch_group
            elif not rename_mode:
                # 排序模式下，直接输出原EXTGRP行
                if extgrp_line:
                    output_lines.append(extgrp_line)
                last_group = ch_group
            else:
                # 重命名模式下但没有-rg参数，直接输出原EXTGRP行
                if extgrp_line:
                    output_lines.append(extgrp_line)
                last_group = ch_group
        
        if not should_process:
            # 不匹配的频道组，直接输出原内容
            if not rename_mode and ch_group and ch_group == last_group and extgrp_line:
                # 如果已经在上面输出了EXTGRP，这里不再输出
                pass
            output_lines.append(ch["inf"])
            output_lines.extend(ch["urls"])
            continue
        
        # 初始化最终INF行
        final_inf = ch["inf"]
        channel_renamed = False
        
        # ========== 重命名模式逻辑 ==========
        if rename_mode:
            # 1. 频道重命名逻辑（需要同时满足-ch和-k）
            if new_name and target_channels and keywords:
                if name_match and url_match_for_rename:
                    final_inf = rename_inf(ch["inf"], new_name)
                    rename_count += 1
                    channel_renamed = True
            
            # 2. 频道组重命名逻辑（处理group-title属性格式）
            # 注意：对于EXTGRP格式，组重命名已经在上面处理了
            if rename_group and group_match and parse_extinf_group(final_inf):
                # 判断该频道是否满足组重命名条件（针对group-title属性）
                should_rename_group_attr = False
                
                if not keywords and not target_channels:
                    # 情况1: 只有 -gr + -rg (无 -k 和 -ch)
                    should_rename_group_attr = True
                elif keywords and not target_channels and url_match_for_rename:
                    # 情况2: -gr + -rg + -k (无 -ch)
                    should_rename_group_attr = True
                elif not keywords and target_channels and name_match:
                    # 情况3: -gr + -rg + -ch (无 -k)
                    should_rename_group_attr = True
                elif keywords and target_channels and name_match and url_match_for_rename:
                    # 情况4: -gr + -rg + -k + -ch
                    should_rename_group_attr = True
                
                # 执行组重命名（针对group-title属性）
                if should_rename_group_attr:
                    final_inf = update_extinf_group(final_inf, rename_group)
                    if ch_group not in processed_groups:
                        group_rename_count += 1
                        processed_groups.add(ch_group)
                        if keywords:
                            group_rename_with_k_count += 1
        
        # ========== 排序模式逻辑 ==========
        else:
            # 如果没有进入重命名模式，执行URL排序
            should_sort_urls = False
            
            if group_sort:
                # 组间排序模式：只对匹配的组进行URL排序
                should_sort_urls = group_match and len(ch["urls"]) > 1
            else:
                # 组内排序模式：根据其他条件判断
                if target_channels:
                    # 如果指定了-ch，只对频道名匹配且属于匹配组的频道排序
                    should_sort_urls = name_match and group_match
                elif group_names:
                    # 指定了-gr，对匹配的频道组排序
                    should_sort_urls = group_match
                else:
                    # 未指定-gr和-ch，全局排序
                    should_sort_urls = True
            
            # 执行URL排序（基于URL中的关键字）
            if should_sort_urls and len(ch["urls"]) > 1:
                # 稳定排序保证了未匹配项保持原始相对顺序
                sorted_list = sorted(ch["urls"], key=get_url_sort_score)
                output_lines.extend(sorted_list)
                if sorted_list != ch["urls"]:  # 如果排序有变化
                    sort_count += 1
            else:
                output_lines.extend(ch["urls"])
        
        # 输出最终的INF行
        output_lines.append(final_inf)
        
        # 如果没有进入重命名模式，URL已经在上面的排序逻辑中输出了
        if rename_mode:
            # 在重命名模式下，直接输出原始URL（不排序）
            output_lines.extend(ch["urls"])
    
    return output_lines, rename_count, sort_count, len(channels_data), group_rename_count, group_sort_count, group_rename_with_k_count

# ... 后面的函数保持不变 ...

def safe_write_output(lines: List[str], input_path: str, output_path: str) -> Tuple[bool, Optional[str]]:
    """安全写入输出文件，代码保持不变"""
    # ... 代码保持不变 ...

def validate_arguments(input_path: str, output_path: str) -> bool:
    """验证参数，代码保持不变"""
    # ... 代码保持不变 ...

def cleanup_temp_file(temp_path: Optional[str]) -> None:
    """清理临时文件，代码保持不变"""
    # ... 代码保持不变 ...

def main():
    parser = argparse.ArgumentParser(
        description="M3U URL排序与条件重命名工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 工作模式说明
----------------------------------------
脚本有两种工作模式，互斥执行：

1. 📝 重命名模式（当有 -rn 或 -rg 参数时激活）：
   - 执行频道重命名和/或频道组重命名
   - ❌ 不执行URL排序

2. 🔄 排序模式（没有 -rn 和 -rg 参数时激活）：
   - 执行URL排序和/或组间排序
   - ❌ 不执行重命名操作

🎯 支持格式：
----------------------------------------
1. 标准group-title格式：
   #EXTINF:-1 tvg-name="Channel" group-title="Group1", Channel Name
   http://example.com/stream.m3u8

2. EXTGRP标签格式：
   #EXTINF:-1 tvg-name="Channel", Channel Name
   #EXTGRP:Group1
   http://example.com/stream.m3u8

3. 混合格式：
   #PLAYLIST:Playlist1
   #EXTINF:-1 tvg-name="Channel 1", Channel 1
   #EXTGRP:Group1
   http://site.domain/channel1

🎯 URL排序功能：
----------------------------------------
支持所有格式的URL排序：
   %(prog)s -i input.m3u -k "4k,1080p,720p" -gr "央视"
   → 对央视组内的频道URL按画质排序（支持EXTGRP格式）

🎯 频道重命名功能：
----------------------------------------
支持所有格式的频道重命名（需同时指定 -ch 和 -k）：
   %(prog)s -i input.m3u -k "youtube" -ch "Music" -rn "YouTubeMusic"
   → 重命名频道名包含"Music"且URL包含"youtube"的频道

🎯 频道组重命名功能：
----------------------------------------
支持所有格式的频道组重命名：
   组合1: 只有 -gr + -rg
     → 无条件重命名所有匹配组的频道
     
   组合2: -gr + -rg + -k
     → 重命名匹配组中URL包含-k关键字的频道
     
   组合3: -gr + -rg + -ch  
     → 重命名匹配组中频道名包含-ch关键字的频道
     
   组合4: -gr + -rg + -k + -ch
     → 重命名匹配组中同时满足频道名和URL条件的频道
        """
    )
    
    # 基础参数
    parser.add_argument("-i", "--input", required=True, help="输入M3U文件路径")
    parser.add_argument("-o", "--output", default="sorted_output.m3u", help="输出文件路径")
    parser.add_argument("-k", "--keywords", default="", help="URL关键字，逗号分隔（用于条件匹配）")
    parser.add_argument("-r", "--reverse", action="store_true", 
                       help="开启反向模式（仅在排序模式下有效）")
    
    # 频道相关参数
    parser.add_argument("-ch", "--channels", 
                       help="目标频道名关键字，逗号分隔（在频道显示名称中查找）")
    parser.add_argument("-rn", "--rename", 
                       help="重命名频道名（需同时满足 -ch 和 -k 条件）")
    
    # 频道组相关参数
    parser.add_argument("-gr", "--groups", 
                       help="目标频道组名关键字，逗号分隔（在group-title或#EXTGRP中查找）")
    parser.add_argument("-rg", "--rename-group", 
                       help="重命名频道组名，支持多种条件组合（见说明）")
    parser.add_argument("-gs", "--group-sort", action="store_true", 
                       help="对频道组进行排序（组间排序，仅在排序模式下有效）")
    
    parser.add_argument("--force", action="store_true", 
                       help="强制覆盖输出文件（如果已存在且与输入不同）")
    
    args = parser.parse_args()
    
    # 验证参数逻辑关系
    if args.rename_group and not args.groups:
        print("错误：-rg/--rename-group 参数需要配合 -gr/--groups 使用")
        sys.exit(1)
    
    if args.rename and not (args.channels and args.keywords):
        print("错误：-rn/--rename 参数需要同时配合 -ch 和 -k 使用")
        sys.exit(1)
    
    # 确定工作模式
    rename_mode = bool(args.rename or args.rename_group)
    
    if rename_mode:
        print(f"\n📝 进入重命名模式")
        if args.rename:
            print(f"   频道重命名：将重命名满足条件的频道为 '{args.rename}'")
            print(f"   条件：频道名包含 '{args.channels}' 且 URL包含 '{args.keywords}'")
            print(f"   支持格式：group-title属性和#EXTGRP标签格式")
        
        if args.rename_group:
            print(f"\n   频道组重命名：将重命名满足条件的频道组为 '{args.rename_group}'")
            print(f"   目标组：'{args.groups}'")
            print(f"   支持格式：group-title属性和#EXTGRP标签格式")
            
            # 根据参数组合显示具体条件
            if args.keywords and args.channels:
                print(f"   条件：频道名包含 '{args.channels}' 且 URL包含 '{args.keywords}'")
            elif args.keywords:
                print(f"   条件：URL包含 '{args.keywords}'")
            elif args.channels:
                print(f"   条件：频道名包含 '{args.channels}'")
            else:
                print(f"   条件：无条件重命名所有匹配组")
        
        print(f"   ❌ URL排序功能已禁用")
    else:
        print(f"\n🔄 进入排序模式")
        if args.keywords:
            print(f"   URL排序关键字：'{args.keywords}'")
            print(f"   支持格式：group-title属性和#EXTGRP标签格式")
        if args.group_sort:
            print(f"   组间排序：启用")
        print(f"   ❌ 重命名功能已禁用")
    
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
        output_lines, rename_count, sort_count, total_channels, group_rename_count, group_sort_count, group_rename_with_k_count = sort_m3u_urls(
            args.input, args.output, args.keywords, args.reverse, 
            args.channels, args.rename, args.force,
            args.groups, args.rename_group, args.group_sort
        )
        
        if output_lines is None:  # 如果sort_m3u_urls返回None表示失败
            sys.exit(1)
        
        # 安全写入输出文件
        success, temp_path = safe_write_output(output_lines, args.input, args.output)
        
        # 如果失败，清理临时文件
        if not success:
            cleanup_temp_file(temp_path)
            print("处理失败！")
            sys.exit(1)
        
        # 输出统计信息
        print(f"\n✅ 处理成功！")
        print(f"   输入文件: {args.input}")
        print(f"   输出文件: {args.output}")
        print(f"   频道总数: {total_channels} 个")
        
        if rename_mode:
            print(f"\n📝 重命名模式结果:")
            if args.rename:
                print(f"   频道重命名: {rename_count} 个频道已重命名为 '{args.rename}'")
            
            if args.rename_group:
                print(f"   频道组重命名: {group_rename_count} 个频道的组名已修改为 '{args.rename_group}'")
                
                # 显示具体的重命名条件统计
                if args.keywords and not args.channels:
                    print(f"   （其中 {group_rename_with_k_count} 个因URL包含 '{args.keywords}' 而被重命名）")
                elif args.keywords and args.channels:
                    print(f"   （其中 {group_rename_with_k_count} 个因同时满足频道名和URL条件而被重命名）")
                
                if group_rename_count == 0:
                    print(f"   ⚠️ 没有频道满足重命名条件")
                    if args.keywords and args.channels:
                        print(f"     需同时满足：频道名包含 '{args.channels}' 且 URL包含 '{args.keywords}'")
                    elif args.keywords:
                        print(f"     需满足：URL包含 '{args.keywords}'")
                    elif args.channels:
                        print(f"     需满足：频道名包含 '{args.channels}'")
        else:
            print(f"\n🔄 排序模式结果:")
            if args.keywords:
                print(f"   URL排序: {sort_count} 个频道的URL已按 '{args.keywords}' 排序")
            if args.group_sort and group_sort_count:
                print(f"   组间排序: 频道组已按照 '{args.groups}' 顺序排列")
        
        if args.reverse and not rename_mode and args.keywords:
            print(f"   排序模式: 反向模式（匹配 '{args.keywords}' 的URL放最后）")
        elif args.keywords and not rename_mode:
            print(f"   排序模式: 正向模式（匹配 '{args.keywords}' 的URL放前面）")
        
        if input_abs == output_abs:
            print(f"   文件操作: 已安全覆盖原文件")
            
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
