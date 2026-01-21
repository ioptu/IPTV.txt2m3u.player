## 主要功能:
- 支持FLV、M3U8、M3U、TS多种格式
- EPG电视节目指南
- 卡顿自动换源与手动换源
- 频道列表自动刷新
- URL过滤黑名单
- 丰富的键盘快捷键
- 视频"画质增强"
- 自定义HTTP Headers
- 多码率、音轨、字幕切换(需直播源支持)

## 使用方法:
- 打开"开发者模式"，"加载已解压的扩展"即可。
---

## .m3u8
> chrome已经原生支持播放.m3u8的链接。某些m3u8使用chrome直接播放会出现只有声音，没有画面；某些非标准的hls视频链接目前chrome还是无法直接播放，例如链接中不含.m3u8关键字，同时其响应头中content-type不是标准的hls的MIME。
> 而使用其他播放器如potplayer和本扩展则不存在这些问题（本扩展的播放能力上限取决于[hls.js-v1.6.15](https://github.com/video-dev/hls.js/blob/master/README.md)）。


## http
> 在浏览器地址栏输入的某些http开头的源播放失败可能与浏览器开启了自动https有关


## 离线安装crx
> [利用组策略启用离线安装的crx（edge示例）](https://learn.microsoft.com/zh-cn/deployedge/microsoft-edge-manage-extensions-policies#allow-or-block-extensions-in-group-policy)
>
> [安装组策略模板（edge示例）](https://learn.microsoft.com/zh-cn/deployedge/configure-microsoft-edge)
>
> [下载组策略模板 edge](https://aka.ms/EdgeEnterprise)
>
> [下载组策略模板 chrome](https://www.chromium.org/administrators/policy-templates/)
>
> ["打包扩展"获得crx（edge示例）](https://learn.microsoft.com/zh-cn/deployedge/microsoft-edge-manage-extensions-webstore#publish-an-extension)

## 其他

> [移动端播放软件APK](https://github.com/skysolf/iptv/)
>
> [电视直播软件_mytv-android](https://github.com/mytv-android/mytv-android) + [mytv可用js直播源](https://gitee.com/organizations/mytv-android/projects)
>
> [Github文件加速](https://gh-proxy.com/) 将GitHub链接转换为多区域加速链接，解决GitHub访问慢、下载失败等问题
