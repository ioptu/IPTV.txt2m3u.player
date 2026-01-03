import argparse
import sys

def sort_m3u_urls(input_file, output_file, keywords_str, reverse_mode=False):
    # 将输入的逗号分隔关键字转为列表并去除空格
    # 注意：这里保留关键字原始大小写
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: 找不到文件 '{input_file}'")
        return
    except Exception as e:
        print(f"Error: 读取文件时发生错误: {e}")
        return

    processed_content = []
    start_index = 0
    if lines and lines[0].strip().startswith('#EXTM3U'):
        processed_content.append(lines[0].strip())
        start_index = 1

    channels = []
    current_inf = None
    current_urls = []

    for line in lines[start_index:]:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF'):
            if current_inf:
                channels.append({"inf": current_inf, "urls": current_urls})
            current_inf = line
            current_urls = []
        else:
            current_urls.append(line)
    
    if current_inf:
        channels.append({"inf": current_inf, "urls": current_urls})

    def get_sort_score(url):
        # 严格大小写敏感匹配
        for index, kw in enumerate(keywords):
            if kw in url:  # 不再使用 .lower()
                if reverse_mode:
                    # 反向模式：匹配到的索引越靠前，分数越大，排在最后
                    return index + 1
                else:
                    # 正常模式：匹配到的索引越靠前，分数越小（负数），排在最前
                    return index - len(keywords)
        
        # 未匹配项分数为 0
        # 正常模式：0 比负数大，排后面
        # 反向模式：0 比正数小，排前面
        return 0

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            if processed_content:
                f.write(processed_content[0] + '\n')
            
            for ch in channels:
                f.write(ch["inf"] + '\n')
                # 稳定排序：分数相同（如都未匹配）时保持原序
                sorted_urls = sorted(ch["urls"], key=get_sort_score)
                for url in sorted_urls:
                    f.write(url + '\n')
    except Exception as e:
        print(f"Error: 写入文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="根据关键字对 M3U 播放列表中的 URL 进行大小写敏感排序")
    
    parser.add_argument("-i", "--input", required=True, help="输入的 M3U 文件路径")
    parser.add_argument("-o", "--output", default="sorted_output.m3u", help="输出的 M3U 文件路径")
    parser.add_argument("-k", "--keywords", required=True, help="排序关键字，区分大小写")
    parser.add_argument("-r", "--reverse", action="store_true", help="反向模式：匹配项排在末尾，未匹配项排在最前")

    args = parser.parse_args()

    sort_m3u_urls(args.input, args.output, args.keywords, args.reverse)
    
    print(f"处理完成！(大小写敏感模式)")
    print(f"排序策略: {'[未匹配] -> [关键字1] -> [关键字2]' if args.reverse else '[关键字1] -> [关键字2] -> [未匹配]'}")

if __name__ == "__main__":
    main()
