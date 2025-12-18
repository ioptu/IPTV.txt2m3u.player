打开"开发者模式"后，"加载已解压的扩展"即可。

## 离线安装crx
https://www.chromium.org/administrators/policy-templates/   #组策略模板 chrome

https://aka.ms/EdgeEnterprise   #组策略模板 edge

https://learn.microsoft.com/zh-cn/deployedge/configure-microsoft-edge #安装组策略模板 edge

https://learn.microsoft.com/zh-cn/deployedge/microsoft-edge-manage-extensions-policies#allow-or-block-extensions-in-group-policy #利用组策略启用离线安装的crx


## http
一些http开头的源播放失败可能与浏览器开启了自动https有关 


## .m3u8
·现在chrome已经原生支持播放.m3u8的链接。即使链接中不含.m3u8的hls类型视频也能原生支持播放。这些链接的共性是响应头中都含有“content-type application/vnd.apple.mpegurl”（hls的一种mime类型）字段。

·但是，chrome直接播放的hls有时会出现只有声音，没有画面；一些非标准的hls目前chrome还是无法直接播放，比如不含.m3u8的hls类型视频链接，其响应头中content-type是text/plain。而使用其他播放器如potplayer和本扩展则不存在这些问题。

