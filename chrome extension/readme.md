---
- 打开"开发者模式"后，"加载已解压的扩展"即可。
---

## .m3u8
> chrome已经原生支持播放.m3u8的链接。没有.m3u8关键字但是响应头中有“content-type application/vnd.apple.mpegurl”字段的链接也能播放（vnd.apple.mpegurl是hls的mime类型之一）。
>
> chrome直接播放的hls有些会出现只有声音，没有画面；一些非标准的hls目前chrome还是无法直接播放，例如链接中不含.m3u8关键字，同时其响应头中content-type是text/plain。而使用其他播放器如potplayer和本扩展则不存在这些问题（本扩展虽也会出现有声无画，但比chrome原生较少，它的播放能力上限取决于[hls.js](https://github.com/video-dev/hls.js/blob/master/README.md)项目）。


## http
> 一些http开头的源播放失败可能与浏览器开启了自动https有关（只影响在浏览器地址栏输入的链接）


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
