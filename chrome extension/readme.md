## 主要功能:
- 支持FLV、M3U8、M3U多种格式
- EPG电视节目指南
- 多源切换与卡顿自动换源
- 播放列表自动刷新
- URL过滤黑名单
- 丰富的键盘快捷键
- 视频"画质增强"

## 使用方法:
- 在浏览器扩展管理页面打开"开发者模式"后，"加载已解压的扩展"即可。
---

## .m3u8
> chrome已经原生支持播放.m3u8的链接。没有.m3u8关键字但是响应头中有“content-type application/vnd.apple.mpegurl”字段的链接也能播放（vnd.apple.mpegurl是hls的mime类型之一）。
>
> chrome直接播放的hls有些会出现只有声音，没有画面；一些非标准的hls目前chrome还是无法直接播放，例如链接中不含.m3u8关键字，同时其响应头中content-type是text/plain。而使用其他播放器如potplayer和本扩展则不存在这些问题（本扩展的播放能力上限取决于[hls.js-v1.6.15](https://github.com/video-dev/hls.js/blob/master/README.md)）。


## http
> 一些在浏览器地址栏输入的http开头的源播放失败可能与浏览器开启了自动https有关


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
