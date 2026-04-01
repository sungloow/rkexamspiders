import base64
from datetime import datetime
import json
import os
import re
import subprocess
from typing import Optional
import uuid

from curl_cffi import requests
from bs4 import BeautifulSoup

from import_to_oems import logger
from utils.json_handle import read_json, write_json


# 全局变量
COOKIES_51CTO = None
HEADERS_51CTO = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "dnt": "1",
    # 注释掉可能导致304的头部
    # "if-modified-since": "Wed, 09 Apr 2025 06:25:45 GMT",
    # "if-none-match": '"d37e99a79f9dbf21558b00319448120a-1"',
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


def scp(img_path: str) -> Optional[str]:
    if not os.path.exists(img_path):
        logger.warning(f"错误：文件 '{img_path}' 不存在")
        return None
    # 使用scp命令上传图片到服务器, 服务器地址为 192.168.31.11, username 为 pic, 返回上传后的图片路径
    try:
        # command = f"scp {img_path} pic@192.168.31.11:/home/pic/images/"
        command = f"scp {img_path} root@172.26.14.36:/home/root/images/51cto/"
        subprocess.run(command, shell=True, capture_output=True, check=True)
        img_name = os.path.basename(img_path)
        return img_name
    except subprocess.CalledProcessError as e:
        logger.error(f"scp 命令执行失败: {e.stderr.decode('utf-8')}")
        return None
    except Exception as e:
        logger.error(f"发生未知错误: {e}")
        return None


def upload_image_to_server(img_path, max_attempts=3):
    base_url = "http://172.26.14.34/images/51cto/"
    for attempt in range(1, max_attempts + 1):
        img_name = scp(img_path)
        if img_name is not None:
            img_url = base_url + img_name
            return img_url
        logger.error(f"第 {attempt} 次上传图片失败")
    raise Exception("scp 上传图片失败")


def download_image(url, download_path):
    try:
        # 判断download_path文件夹是否存在, 不存在则创建
        if not os.path.exists(os.path.dirname(download_path)):
            os.makedirs(os.path.dirname(download_path))
        if COOKIES_51CTO is not None:
            response = requests.get(url, cookies=COOKIES_51CTO, headers=HEADERS_51CTO)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.6",
            }
            response = requests.get(
                url,
                headers=headers,
                impersonate="chrome136",   # 很关键
                timeout=20
            )
        if response.status_code == 200:
            with open(download_path, "wb") as f:
                f.write(response.content)
        else:
            raise Exception(
                f"下载图片失败：{url}, status code not 200, status code：{response.status_code}, response: {response.text}"
            )
    except Exception as e:
        raise Exception(f"下载图片失败：{url}, 错误信息：{e}")


def replace_img_url_to_server(html_str, source="51cto"):
    if html_str is None:
        return html_str
    soup = BeautifulSoup(html_str, "html.parser")
    img_array = soup.find_all("img", {"src": True})
    if len(img_array) == 0:
        return html_str
    pattern = re.compile(r".*(https?://docimg\d+\.docs\.qq\.com).*")
    for img in img_array:
        img_url = img.get("src")
        if img_url.startswith("data:image"):
            continue
        # 如果 url 包含 https://docimg7.docs.qq.com，不进行替换
        if pattern.search(img_url):
            continue
        # 如果 url 包含 alidocs.dingtalk.com，不进行替换
        if "alidocs.dingtalk.com" in img_url:
            logger.info(f"【跳过】alidocs.dingtalk.com图片，img_url: {img_url}")
            continue
        # file:// 本地图片，不进行替换
        if img_url.startswith("file://"):
            logger.info(f"【跳过】file://本地图片，img_url: {img_url}")
            continue
        try:
            img_name = os.path.basename(img_url)
            uuid_str = str(uuid.uuid4())
            img_name = datetime.now().strftime("%Y%m%d_%H%M") + "_" + uuid_str + "_" + img_name
            # download_path = os.path.join(os.getcwd(), source, img_name)
            download_path = os.path.join(os.getcwd(), "data/picture", source, img_name)
            download_image(img_url, download_path)
            # new_img_url = upload_image_to_server(download_path)
            # img['src'] = new_img_url
            # os.remove(download_path)  # 删除下载的图片

            # 把图片下载到本地，后面统一上传到服务器
            base_url = f"http://172.26.14.34/images/{source}/"
            new_img_url = base_url + img_name
            img["src"] = new_img_url
        except Exception as e:
            raise e
    return str(soup)


def convert_image_to_base64(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    img_array = soup.find_all("img", {"src": True})
    if len(img_array) == 0:
        return html_str
    for img in img_array:
        img_url = img.get("src")
        if img_url.startswith("data:image"):
            continue
        res = requests.get(img_url)
        base64_data = base64.b64encode(res.content)
        s = base64_data.decode()
        s_base64 = "data:image/jpeg;base64,%s" % s
        img["src"] = s_base64
    return str(soup)


def handle_pic(input_file, output_file, func: str):
    try:
        json_data = read_json(input_file)
        for question in json_data:
            question_title = question.get("question_title", "")
            analyze = question.get("analyze", "")
            answer_list = question.get("answer", [])
            option_list = question.get("option", [])
            if func == "upload":
                new_question_title = replace_img_url_to_server(question_title)
                new_analyze = replace_img_url_to_server(analyze)
                if not answer_list:
                    option_list = []
                new_answer_list = [
                    replace_img_url_to_server(answer) for answer in answer_list
                ]
                if not option_list:
                    option_list = []
                new_option_list = [
                    replace_img_url_to_server(option) for option in option_list
                ]
            elif func == "base64":
                new_question_title = convert_image_to_base64(question_title)
                new_analyze = convert_image_to_base64(analyze)
                new_answer_list = [
                    convert_image_to_base64(answer) for answer in answer_list
                ]
                new_option_list = [
                    convert_image_to_base64(option) for option in option_list
                ]
            else:
                new_question_title = question_title
                new_analyze = analyze
                new_answer_list = answer_list
                new_option_list = option_list
            question["question_title"] = new_question_title
            question["analyze"] = new_analyze
            question["answer"] = new_answer_list
            question["option"] = new_option_list
    except Exception as e:
        raise e
    else:
        write_json(output_file, json_data)


def handle_pic_xs(input_file, output_file, func: str):
    source = "xisai"
    try:
        json_data = read_json(input_file)
        for question in json_data.get("questions", []):
            tigan = question.get("tigan")
            cTigan = question.get("cTigan")
            analyze = question.get("analysis", "")
            old_answer = question.get("answer")
            choice_map = question.get("options", {})
            if func == "upload":
                new_tigan = replace_img_url_to_server(tigan, source=source)
                new_cTigan = replace_img_url_to_server(cTigan, source=source)
                new_analyze = replace_img_url_to_server(analyze, source=source)
                if isinstance(old_answer, list):
                    new_answer_list = [
                        replace_img_url_to_server(answer, source=source)
                        for answer in old_answer
                    ]
                elif isinstance(old_answer, str):
                    new_answer_list = replace_img_url_to_server(
                        old_answer, source=source
                    )
                else:
                    logger.warning(f"错误：old_answer 类型为 {type(old_answer)}")
                    raise Exception
                if isinstance(choice_map, dict):
                    for key, value in choice_map.items():
                        choice_map[key] = replace_img_url_to_server(
                            value, source=source
                        )
                elif isinstance(choice_map, list):
                    for index, choice in choice_map:
                        choice_map[index] = replace_img_url_to_server(
                            choice, source=source
                        )
                else:
                    logger.warning(f"错误：choice_map 类型为 {type(choice_map)}")
                    raise Exception
            elif func == "base64":
                new_question_title = convert_image_to_base64(question_title)
                new_analyze = convert_image_to_base64(analyze)
                if isinstance(old_answer, list):
                    new_answer_list = [
                        replace_img_url_to_server(answer, source=source)
                        for answer in old_answer
                    ]
                elif isinstance(old_answer, str):
                    new_answer_list = replace_img_url_to_server(
                        old_answer, source=source
                    )
                else:
                    logger.warning(f"错误：old_answer 类型为 {type(old_answer)}")
                    raise Exception
                if isinstance(choice_map, dict):
                    for key, value in choice_map.items():
                        choice_map[key] = replace_img_url_to_server(
                            value, source=source
                        )
                elif isinstance(choice_map, list):
                    for index, choice in choice_map:
                        choice_map[index] = replace_img_url_to_server(
                            choice, source=source
                        )
                else:
                    logger.warning(f"错误：choice_map 类型为 {type(choice_map)}")
                    raise Exception
            else:
                new_tigan = tigan
                new_cTigan = cTigan
                new_analyze = analyze
                new_answer_list = old_answer
            question["tigan"] = new_tigan
            question["cTigan"] = new_cTigan
            question["analysis"] = new_analyze
            question["answer"] = new_answer_list
    except Exception as e:
        logger.exception(e)
        raise e
    else:
        write_json(output_file, json_data)


def process(input_folder: str, is_xisai: bool = False, cookies: dict = None):
    # 获取输入文件夹的父目录
    parent_dir = os.path.dirname(input_folder)
    last_folder_name = os.path.basename(input_folder)
    replace_folder_name = f"{last_folder_name}_replaced"
    output_folder_name = f"{replace_folder_name}/{last_folder_name}"
    log_folder_name = f"{replace_folder_name}/replace_pic_log"
    # 创建输出和日志文件夹路径
    _output_folder = os.path.join(parent_dir, output_folder_name)
    _log_folder = os.path.join(parent_dir, log_folder_name)

    # 创建输出和日志文件夹
    os.makedirs(_output_folder, exist_ok=True)
    os.makedirs(_log_folder, exist_ok=True)

    # 遍历输入文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(input_folder):
        # 创建相应的子文件夹结构在输出文件夹和日志文件夹中
        for dir_name in dirs:
            os.makedirs(
                os.path.join(
                    _output_folder, os.path.relpath(root, input_folder), dir_name
                ),
                exist_ok=True,
            )
            os.makedirs(
                os.path.join(
                    _log_folder, os.path.relpath(root, input_folder), dir_name
                ),
                exist_ok=True,
            )
        # 处理每个文件
        for file_name in files:
            input_file = os.path.join(root, file_name)
            output_file = os.path.join(
                _output_folder, os.path.relpath(root, input_folder), file_name
            )
            log_file_success = os.path.join(
                _log_folder,
                os.path.relpath(root, input_folder),
                file_name + ".success",
            )
            # 检查是否为json文件
            if input_file.lower().endswith(".json"):
                # 检查是否已经成功处理过该文件
                if os.path.exists(log_file_success):
                    logger.info(f"Skipping already processed file: {input_file}")
                    continue
                try:
                    logger.info(f"Start processing: {input_file}")
                    if is_xisai:
                        handle_pic_xs(input_file, output_file, "upload")  # 处理希赛
                    else:
                        global COOKIES_51CTO
                        COOKIES_51CTO = cookies
                        handle_pic(input_file, output_file, "upload")

                    # 创建成功标记文件
                    open(log_file_success, "w").close()
                    logger.info(f"Processed successfully: {input_file}")
                except Exception as e:
                    logger.error(f"Error processing: {input_file}, error: {e}")
            else:
                # 如果不是json文件
                logger.warning(
                    f"This file is not a json file, Skip. File: {input_file}"
                )
