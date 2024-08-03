# python\_film\_scraping

使用python+fastapi手动刮削番剧



# 前言

q：为何有此项目出现

a：1.之前用过kodi，感觉界面不是很好看，而且需要打开一个图形界面，也不太会使用。

&#x20;     2.python是最好的语言（确信

q：有没有打算完善此项目

a：不，此项目大概在这里就结束了。jellyfin真的很好用，推荐

## 运行

1.下载仓库

2.安装必要包

    pip install fastapi uvicorn opencv-python nonebot2 pillow

3.在项目根目录运行此程序

    uvicorn main:app --reload --port 8080 --host 0.0.0.0
