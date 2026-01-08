import re
import argparse
import os
import sys
import tempfile
import shutil

#频道组‘混乱’的m3u专用脚本，如将CCTV各频道按照体育、新闻、影视等分在了不同频道组
# --- 1. 辅助函数：提取归一化 Key ---
def get_norm_key(name):
    """去掉横杠和后缀'台'，转大写，用于判断是否为同名频道"""
    if not name: return ""
    temp = name.replace('-', '')
    if temp.endswith('台'):
        temp = temp[:-1]
    return temp.strip().upper()

# --- 2. 辅助函数：判断显示优先级 ---
def is_preferred(name):
    """判断名字是否含有横杠或'台'"""
    return '-' in name or name.endswith('台')

# --- 3. 辅助函数：提取 CCTV 数字 ---
def extract_cctv_num(name):
    """提取 CCTV 后的数字，用于排序。如果没有数字则排在最后。"""
    match = re.search(r'(?i)CCTV-?(\d+)', name)
    return int(match.group(1)) if match else 999

# --- 4. 辅助函数：解析 M3U ---
def parse_m3u(file_path):
    if not os.path.exists(file_path):
        return None, []
        
    channels = {} # key: norm_key, value: data_dict
    order = []    # 记录第一次发现该频道的顺序
    header = "#EXTM3U"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    current_info = None
    current_name = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTM3U'):
            header = line
            continue
            
        if line.startswith('#EXTINF:'):
            current_info = line
            # 提取逗号后的频道名
            name_match = re.search(r',([^,]+)$', line)
            current_name = name_match.group(1).strip() if name_match else None
            
        elif line.startswith(('http://', 'https://')) and current_name:
            norm_key = get_norm_key(current_name)
            
            # 提取原有的 group-title
            group_match = re.search(r'group-title="([^"]*)"', current_info)
            original_group = group_match.group(1) if group_match else "其他"
            
            if norm_key not in channels:
                channels[norm_key] = {
                    "info": current_info,
                    "name": current_name,
                    "urls": {line},
                    "original_group": original_group,
                    "order_idx": len(order)
                }
                order.append(norm_key)
            else:
                # 合并 URL
                channels[norm_key]["urls"].add(line)
                # 检查显示名称优先级：如果新名字更符合偏好，更新 info
                old_name = channels[norm_key]["name"]
                if is_preferred(current_name) and not is_preferred(old_name):
                    channels[norm_key]["info"] = current_info
                    channels[norm_key]["name"] = current_name
                    
    return header, channels, order

# --- 5. 安全文件写入函数 ---
def safe_write_output(header, final_list, input_path, output_path):
    """
    安全地写入输出文件，支持同文件覆盖
    
    :param header: M3U文件头部
    :param final_list: 最终频道列表
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
            out_f.write(header + '\n')
            for item in final_list:
                # 替换或更新 info 行中的 group-title
                info = item["info"]
                new_group = item["final_group"]
                if 'group-title="' in info:
                    info = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', info)
                else:
                    info = info.replace('#EXTINF:', f'#EXTINF: group-title="{new_group}",')
                
                out_f.write(info + '\n')
                # URL 排序输出保持稳定
                for url in sorted(list(item["urls"])):
                    out_f.write(url + '\n')
        
        # 如果是同一个文件，进行原子替换
        if is_same_file:
            try:
                # Python 3.3+ 推荐使用 os.replace 实现原子替换
                os.replace(temp_path, output_path)
                temp_path = None  # 替换成功，清除临时文件引用
            except Exception as e:
                # 如果 os.replace 失败，使用 shutil.move 作为备选
                print(f"警告：原子替换失败，使用备选方案: {e}", file=sys.stderr)
                shutil.move(temp_path, output_path)
                temp_path = None  # 移动成功，清除临时文件引用
        
        return True, None
        
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False, temp_path

# --- 6. 验证参数函数 ---
def validate_arguments(input_path, output_path):
    """
    验证命令行参数的合理性
    
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :return: 验证成功返回True，失败返回False
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误：输入文件 '{input_path}' 不存在", file=sys.stderr)
        return False
    
    # 检查输入文件是否可读
    if not os.access(input_path, os.R_OK):
        print(f"错误：输入文件 '{input_path}' 不可读", file=sys.stderr)
        return False
    
    # 检查是否为文件
    if not os.path.isfile(input_path):
        print(f"错误：'{input_path}' 不是文件", file=sys.stderr)
        return False
    
    # 检查输入文件扩展名（可选警告）
    if not input_path.lower().endswith('.m3u'):
        print(f"警告：输入文件 '{input_path}' 可能不是标准M3U文件", file=sys.stderr)
    
    # 检查输出目录是否可写
    output_dir = os.path.dirname(os.path.abspath(output_path)) or '.'
    if not os.access(output_dir, os.W_OK):
        print(f"错误：输出目录 '{output_dir}' 不可写", file=sys.stderr)
        return False
    
    # 检查输入输出是否为同一文件（提供信息性提示）
    input_abs = os.path.abspath(input_path)
    output_abs = os.path.abspath(output_path)
    
    if input_abs == output_abs:
        print("信息：输入和输出为同一文件，将安全覆盖原文件", file=sys.stderr)
    
    return True

# --- 7. 清理临时文件函数 ---
def cleanup_temp_file(temp_path):
    """
    清理临时文件
    """
    if temp_path and os.path.exists(temp_path):
        try:
            os.unlink(temp_path)
            print(f"已清理临时文件: {temp_path}", file=sys.stderr)
        except Exception as e:
            print(f"警告：无法删除临时文件 {temp_path}: {e}", file=sys.stderr)

# --- 8. 主逻辑 ---
def main():
    parser = argparse.ArgumentParser(description="单文件M3U频道合并排序脚本 - 安全处理同文件覆盖")
    parser.add_argument('-i', '--input', required=True, help="输入M3U文件")
    parser.add_argument('-o', '--output', required=True, help="输出M3U文件")
    parser.add_argument('--force', action='store_true',
                       help='强制覆盖输出文件（如果已存在且与输入不同）')
    
    args = parser.parse_args()

    # 验证参数
    if not validate_arguments(args.input, args.output):
        sys.exit(1)
    
    # 检查输出文件是否已存在且与输入不同
    input_abs = os.path.abspath(args.input)
    output_abs = os.path.abspath(args.output)
    
    if os.path.exists(args.output) and input_abs != output_abs:
        if not args.force:
            print(f"错误：输出文件 '{args.output}' 已存在", file=sys.stderr)
            print("使用 --force 参数强制覆盖，或指定不同的输出文件", file=sys.stderr)
            sys.exit(1)
    
    # 解析M3U文件
    result = parse_m3u(args.input)
    if result[0] is None:
        print("未发现有效频道数据。", file=sys.stderr)
        sys.exit(1)
    
    header, channels, order = result
    
    if not channels:
        print("未发现有效频道数据。", file=sys.stderr)
        sys.exit(1)

    # 分类桶
    cctv_bucket = []
    weishee_bucket = []
    other_bucket = []

    for key, data in channels.items():
        name = data["name"]
        if "CCTV" in name.upper():
            data["final_group"] = "央视"
            cctv_bucket.append(data)
        elif "卫视" in name:
            data["final_group"] = "卫视"
            weishee_bucket.append(data)
        else:
            data["final_group"] = data["original_group"]
            other_bucket.append(data)

    # 排序：
    # 央视：按数字排
    cctv_bucket.sort(key=lambda x: extract_cctv_num(x["name"]))
    # 卫视：按原顺序排
    weishee_bucket.sort(key=lambda x: x["order_idx"])
    # 其他：按原频道组名，组内按原顺序
    other_bucket.sort(key=lambda x: (x["original_group"], x["order_idx"]))

    # 生成最终列表
    final_list = cctv_bucket + weishee_bucket + other_bucket

    # 安全写入输出文件
    success, temp_path = safe_write_output(header, final_list, args.input, args.output)
    
    # 如果失败，清理临时文件
    if not success:
        cleanup_temp_file(temp_path)
        print("处理失败！", file=sys.stderr)
        sys.exit(1)
    
    # 输出统计信息
    print(f"处理完成！", file=sys.stderr)
    print(f"- 央视：{len(cctv_bucket)} 个", file=sys.stderr)
    print(f"- 卫视：{len(weishee_bucket)} 个", file=sys.stderr)
    print(f"- 其他：{len(other_bucket)} 个", file=sys.stderr)
    print(f"- 总计：{len(final_list)} 个频道", file=sys.stderr)
    print(f"结果已保存至：{args.output}", file=sys.stderr)
    
    # 检查是否使用了安全覆盖
    if os.path.abspath(args.input) == os.path.abspath(args.output):
        print("注意：已安全覆盖原文件", file=sys.stderr)

if __name__ == "__main__":
    main()
