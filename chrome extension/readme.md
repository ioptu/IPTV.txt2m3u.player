## 主要功能:
- 支持FLV、M3U8、M3U、TS多种格式
- 稳定音量与"画质增强"
- 卡顿自动换源与手动换源
- 频道列表自动刷新
- EPG电视节目指南
- URL过滤黑名单 
- 自定义Headers
- 多码率、音轨、字幕切换(需直播源支持)，以及字幕翻译(使用chrome内置离线AI翻译接口)
## 使用方法:
- 打开"开发者模式"，"加载已解压的扩展程序"即可。
---

## .m3u8
> Chrome 已原生支持 .m3u8 链接，但若链接不含 .m3u8 关键字且 Content-Type 非标准 HLS MIME，Chrome 亦无法播放。 相比之下，本扩展程序（基于 [hls.js-v1.6.15](https://github.com/video-dev/hls.js/blob/master/README.md)）兼容性更强，可规避上述问题。
>

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
