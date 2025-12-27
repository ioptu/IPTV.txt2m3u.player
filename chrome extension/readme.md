---
- 打开"开发者模式"后，"加载已解压的扩展"即可。
---

## .m3u8
- chrome已经原生支持播放.m3u8的链接。即使是链接中不含.m3u8关键字的hls类型视频也能播放。这些链接的共性是响应头中都含有“content-type application/vnd.apple.mpegurl”字段（vnd.apple.mpegurl是hls的mime类型之一）。

- chrome直接播放的hls有些会出现只有声音，没有画面；一些非标准的hls目前chrome还是无法直接播放，比如链接中不含.m3u8关键字的hls类型视频，同时其响应头中content-type是text/plain。而使用其他播放器如potplayer则不存在这些问题，本扩展虽也会出现有声无画，但比chrome原生较少（本扩展的播放能力上限取决于[hls.js](https://github.com/video-dev/hls.js/blob/master/README.md)项目）。


## http
- 一些http开头的源播放失败可能与浏览器开启了自动https有关 


## 离线安装crx
- [利用组策略启用离线安装的crx（edge示例）](https://learn.microsoft.com/zh-cn/deployedge/microsoft-edge-manage-extensions-policies#allow-or-block-extensions-in-group-policy)

- [安装组策略模板（edge示例）](https://learn.microsoft.com/zh-cn/deployedge/configure-microsoft-edge)

- [下载组策略模板 edge](https://aka.ms/EdgeEnterprise)

- [下载组策略模板 chrome](https://www.chromium.org/administrators/policy-templates/)
