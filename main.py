import json
import re
import time
import os
# pip install opencv-python
import cv2
# pip install fastapi
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
# pip install nonebot2
from nonebot import logger
# pip install pillow
from PIL import Image, ImageFilter

# 文件夹配置
library_path = "./example_media_library/"
app_path = "./file/"

# 以下内容无需修改
info_default = {
    "名称": "默认名称",
    "id": {"type": "none", "id": None},
    "类型": "默认类型",
    "分组": "默认分组",
    "观看状态": "默认状态"
}
movies: dict | None = None
numbers = "0123456789"
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def movie_library(request: Request):
    movies = await load_movies()
    user_agent = request.headers.get("user-agent")
    html_file = open(f"{app_path}main.html", "r", encoding="UTF-8")
    html = html_file.read()
    html_file.close()

    # 判断设备类型
    if "iPhone" in user_agent:
        platform = "iPhone"
    elif "iPad" in user_agent:
        platform = "iPad"
    elif "Windows" in user_agent:
        platform = "Windows"
    else:
        platform = None

    # 设置大小
    if platform == "Windows":
        html = html.replace("{{replace-width-replace}}", "250px")
    elif platform == "iPad":
        html = html.replace("{{replace-width-replace}}", "200px")
    elif platform == "iPhone":
        html = html.replace("{{replace-width-replace}}", "145px")
    else:
        html = html.replace("{{replace-width-replace}}", "200px")

    # 为每部电影添加HTML内容
    html_movies = ""
    for movie_path_name in movies.keys():
        html_movies += f"""
        <div class="movie">
            <a href="/info/{movie_path_name}">
                <img src="/image/poster/{movie_path_name}" alt="{movies[movie_path_name]['名称']} Poster">
            </a>
            <h2>{movies[movie_path_name]['名称']}</h2>
            <h5>{movies[movie_path_name]["id"]['type']}: {movies[movie_path_name]["id"]['id']}</h5>
            <p>类型: {movies[movie_path_name].get('类型')}</p>
            <p>分组: {movies[movie_path_name].get('分组')}</p>
            <p> </p>
        </div>
        """
    html = html.replace("{{replace-movies-replace}}", html_movies)

    # 返回html内容
    return HTMLResponse(html)


@app.get("/info/{movie_path}", response_class=HTMLResponse)
async def movie_library(movie_path: str):
    movies = await load_movies()
    if movie_path not in movies.keys():
        return "电影不在列表中"
    html_file = open(f"{app_path}info.html", "r", encoding="UTF-8")
    html = html_file.read()
    html_file.close()

    # 背景图
    background_url = f"/image/background/{movie_path}"

    # 番剧信息
    movie_html = f"""
        <h1>{movies[movie_path].get("名称")}</h1>
        <div class="movie-poster">
            <img src="/image/poster/{movie_path}" alt="电影海报">
        </div>
        <div class="movie-info">
            <p><strong>类型：</strong>{movies[movie_path].get("类型")}</p>
            <p><strong>{movies[movie_path]["id"].get("type")}：</strong>{movies[movie_path]["id"].get("id")}</p>
            <p><strong>分组：</strong>{movies[movie_path].get("分组")}</p>
            <p><strong>观看状态：</strong>{movies[movie_path].get("观看状态")}</p>
        </div>
        <div class="clear"></div>
    """

    # 分集列表
    movie_list_html = ""
    sections = {}
    section_list = os.listdir(f"{library_path}{movie_path}/")
    for section in section_list:
        if not os.path.isdir(f"{library_path}{movie_path}/{section}"):
            continue
        sections[section] = section

    for section_path in sections.keys():
        name = section_path.lower()
        if name.startswith("s"):
            if name.startswith("session"):
                name = name[7:]
            else:
                name = name[1:]
            if start_with_list(name, [" ", "."]) is True:
                name = name[1:]
            if start_with_list(name, numbers) is True:
                num = 0
                for n in name:
                    if n in numbers:
                        num += 1
                    else:
                        break
                session_number = str(int(name[:num]))
                name = name[num:]
                if start_with_list(name, [" ", "."]) is True:
                    name = name[1:]
                sections[section_path] = f"- 第{session_number}季 -<br>{name}"
        elif name.startswith("第"):
            if "季" in name:
                names = name.split("季", 1)
                section_name = names[0].removeprefix("第")
                if all(t in numbers for t in section_name):
                    session_number = str(int(section_name))

                    name = names[1]
                    if start_with_list(name, [" ", "."]) is True:
                        name = name[1:]
                    sections[section_path] = f"- 第{session_number}季 -<br>{name}"

    for section_path in sections.keys():
        movie_list_html += f"""
            <div class="session-item">
                <a href="/info/{movie_path}/{section_path}">
                    <img src="/image/display/session-buttons" alt="{sections[section_path]}">
                    <div class="session-title">
                        {sections[section_path]}
                    </div>
                    <div class="session-title">
                        {sections[section_path]}
                    </div>
                </a>
            </div>
        """

    # 替换html中的内容
    html = html.replace("{{replace-background_url-replace}}", background_url)
    html = html.replace("{{replace-movie_html-replace}}", movie_html)
    html = html.replace("{{replace-movie_list_html-replace}}", movie_list_html)

    return HTMLResponse(html)


@app.get("/info/{movie_path}/{session_path}", response_class=HTMLResponse)
async def movie_library(request: Request, movie_path: str, session_path: str):
    if not os.path.exists(f"{library_path}{movie_path}/{session_path}"):
        return "不存在此影片"
    file_list = os.listdir(f"{library_path}{movie_path}/{session_path}")

    # 获取列表
    episodes = {}
    type_list = [".mp4", ".mov", ".wmv", ".flv", ".avi", ".webm", ".mkv", "."]
    for f in file_list:
        for t in type_list:
            if f.lower().endswith(t):
                episodes[f] = f

    # 提取集名
    for file_name in episodes.keys():
        extracted_corrected = re.findall(r'\[.*?]|[^.\[\]]+', file_name)
        extracted_corrected = [item.strip('[]') for group in extracted_corrected for item in group.split('][')]

        for name in extracted_corrected:
            if all(char in numbers for char in name):
                episodes[file_name] = f"第{name}集"
                break
    user_agent = request.headers.get("user-agent")
    html_file = open(f"{app_path}info_session.html", "r", encoding="UTF-8")
    html = html_file.read()
    html_file.close()

    # 判断设备类型
    if "iPhone" in user_agent:
        platform = "iPhone"
    elif "iPad" in user_agent:
        platform = "iPad"
    elif "Windows" in user_agent:
        platform = "Windows"
    else:
        platform = None

    # 设置大小
    if platform == "Windows":
        html = html.replace("{{replace-width-replace}}", "250px")
    elif platform == "iPad":
        html = html.replace("{{replace-width-replace}}", "200px")
    elif platform == "iPhone":
        html = html.replace("{{replace-width-replace}}", "145px")
    else:
        html = html.replace("{{replace-width-replace}}", "200px")

    # 添加顶栏
    navbar_html = f"""
    <a href="/">
        <img src="/image/display/session-buttons" alt="Logo" style="width:70px;height:50px;">
    </a>
    <a href="/">主页</a>
    <a href="/info/{movie_path}">番剧详情</a>
    """

    # 为每部电影添加HTML内容
    html_movies = ""
    for episode in episodes.keys():
        html_movies += f"""
        <div class="movie">
            <a href="/play/{movie_path}/{session_path}/{episode}">
            <img src="/image/keyframe/{movie_path}<>-<>{session_path}<>-<>{episode}" alt="{episodes[episode]} Poster">
            </a>
            <h2>{episodes[episode]}</h2>
        </div>
        """

    html = html.replace("{{replace-movie_name-replace}}", "电影名称")
    html = html.replace("{{replace-navbar-replace}}", navbar_html)
    html = html.replace("{{replace-movie_list_html-replace}}", html_movies)

    # 返回html内容
    return HTMLResponse(html)


@app.get("/play/{movie_path}/{session_path}/{episode}", response_class=FileResponse)
async def movie_library(movie_path: str, session_path: str, episode: str):
    file_path = f"{library_path}{movie_path}/{session_path}/{episode}"
    if not os.path.exists(file_path):
        return "不存在文件"
    return FileResponse(file_path)


@app.get("/image/{type_}/{name}", response_class=HTMLResponse)
async def movie_library(type_: str, name: str):
    if type_ == "poster":
        if name == "None":
            return FileResponse(f"{app_path}none_post.jpg")

        poster_name = None
        for n in ["poster.jpg", "poster.png", "poster.webp", "post.jpg", "post.png", "post.webp"]:
            if os.path.exists(f"{library_path}{name}/{n}"):
                poster_name = n
        if poster_name is None:
            return FileResponse(f"{app_path}none_post.jpg")

        poster_path = f"{library_path}{name}/{poster_name}"
        poster_path_810 = f"{library_path}{name}/{poster_name.split('.')[0]}-810.{poster_name.split('.')[1]}"
        if os.path.exists(poster_path_810):
            return FileResponse(poster_path_810)
        poster = Image.open(poster_path, "r")
        x, y = poster.size
        x2 = 810
        y2 = int(810 * y / x)
        poster = poster.resize((x2, y2))
        image = Image.new("RGB", (810, 1215), (0, 0, 0, 0))
        image.paste(poster, (0, int((1215 - y2) / 2)))
        image.save(poster_path_810)
        return FileResponse(poster_path_810)
    elif type_ == "background":
        if name == "None":
            return FileResponse(f"{app_path}none_background.jpg")
        if os.path.exists(f"{library_path}{name}/background.jpg"):
            return FileResponse(f"{library_path}{name}/background.jpg")
        elif os.path.exists(f"{library_path}{name}/background.png"):
            return FileResponse(f"{library_path}{name}/background.png")
        elif os.path.exists(f"{library_path}{name}/background.webp"):
            return FileResponse(f"{library_path}{name}/background.webp")

        image_path = None
        for n in ["poster.jpg", "poster.png", "poster.webp", "post.jpg", "post.png", "post.webp"]:
            if os.path.exists(f"{library_path}{name}/{n}"):
                image_path = f"{library_path}{name}/{n}"
        if image_path is None:
            return FileResponse(f"{app_path}none_background.jpg")

        background_path = f"{library_path}{name}/background.jpg"
        image = Image.open(image_path, "r")
        image = image.filter(ImageFilter.GaussianBlur(radius=70))
        image = image.resize((2000, 400))

        mask_image = Image.new("RGBA", (2000, 400), (0, 0, 0, 100))
        image.paste(mask_image, (0, 0), mask_image)

        image.save(background_path)
        return FileResponse(background_path)
    elif type_ == "display":
        if os.path.exists(f"{app_path}{name}.jpg"):
            return FileResponse(f"{app_path}{name}.jpg")
        raise "无法找到文件"
    if type_ == "keyframe":
        if name == "None" or "<>-<>"not in name:
            return FileResponse(f"{app_path}none_keyframe.jpg")
        names = name.split("<>-<>", 2)

        if os.path.exists(f"{app_path}{names[0]}/{names[1]}/{names[2]}_keyframe.jpg"):
            return FileResponse(f"{app_path}{names[0]}/{names[1]}/{names[2]}_keyframe.jpg")
        # 生成关键帧
        keyframe_path = f"{app_path}{names[0]}/{names[1]}/"
        if not os.path.exists(keyframe_path):
            os.makedirs(keyframe_path)
        keyframe_path += f"{names[2]}_keyframe.jpg"
        movie_path = f"{library_path}{names[0]}/{names[1]}/{names[2]}"

        try:
            # 使用cv2.VideoCapture读取视频文件
            cap = cv2.VideoCapture(movie_path)

            # 检查视频是否打开成功
            if not cap.isOpened():
                raise "Error: Could not open video."
            else:
                # 初始化帧计数器
                frame_count = 0

                # 循环读取帧直到第100帧
                while frame_count <= 12:
                    ret, frame = cap.read()

                    # 如果读取帧失败或到达视频末尾，则退出循环
                    if not ret:
                        raise "Error: Could not read a frame from the video."

                    # 增加帧计数器
                    frame_count += 1

                    # 当到达第100帧时
                    if frame_count >= 10:
                        logger.info("保存帧")
                        cv2.imshow('Frame', frame)

                        # 保存这一帧为图片文件
                        if cv2.imwrite(keyframe_path, frame):
                            logger.success(f"成功保存关键帧")
                        else:
                            logger.error(f"保存关键帧错误 {keyframe_path}")
                            logger.error(f"尝试使用英文路径")

                        # cv2.waitKey(0)
                        break

                # 释放视频捕获器并关闭所有窗口
                cap.release()
                cv2.destroyAllWindows()

            if os.path.exists(keyframe_path):
                return FileResponse(keyframe_path)
            else:
                return FileResponse(f"{app_path}none_keyframe.jpg")

        except Exception as e:
            logger.error("生成关键帧失败")
            logger.error(f"{app_path}{names[0]}/{names[1]}/{names[2]}_keyframe.jpg")
            logger.error(e)
            return FileResponse(f"{app_path}none_keyframe.jpg")

    raise "未定义图片类型"


async def load_movies(load: bool | None = True) -> dict:
    """
    加载电影数据
    :param load: True：强制加载， False：使用缓存， None：每1小时刷新（减少硬盘加载次数）
    :return: 番剧数据
    """
    global movies
    if load is None:
        if movies is not None and movies["time"] - int(time.time()) < 3600:
            return movies["data"]
    elif load is False:
        return movies["data"]
    movies = {
        "time": int(time.time()),
        "data": {}
    }
    path_list = os.listdir(library_path)

    for path_name in path_list:
        movie_info_default = info_default
        movie_info_default["名称"] = path_name
        try:
            if os.path.exists(f"{library_path}{path_name}/media.json"):
                file = open(f"{library_path}{path_name}/media.json", "r", encoding="UTF-8")
                movie_info = json.loads(file.read())
                file.close()
            else:
                movie_info = movie_info_default
                file = open(f"{library_path}{path_name}/media.json", "w", encoding="UTF-8")
                file.write(json.dumps(movie_info, ensure_ascii=False))
                file.close()
        except Exception as e:
            logger.error(f"读取元信息失败， {path_name}")
            logger.error(e)
            movie_info = movie_info_default

        movie_info_default.update(movie_info)
        movies["data"][path_name] = movie_info_default
    logger.debug(f"movies: {movies['data']}")
    return movies["data"]


def write_info(move_path: str, data: dict):
    if not os.path.exists(f"{library_path}{move_path}/"):
        raise "路径不存在"
    file = open(f"{library_path}{move_path}/media.json", "w")
    file.write(json.dumps(data))
    file.close()


def start_with_list(a_str: str, b_list: list[str] | str) -> bool:
    for b in b_list:
        if a_str.startswith(b):
            return True
    return False
