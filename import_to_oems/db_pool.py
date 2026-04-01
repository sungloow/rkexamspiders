import os
import re

import pymysql
import requests
from bs4 import BeautifulSoup
from dbutils.pooled_db import PooledDB
from config import config

_host = config.get("oems").get("host")
_user = config.get("oems").get("user")
_pwd = config.get("oems").get("password")
_database = config.get("oems").get("database")
_port = config.get("oems").get("port")


_db_connection_args = {
    "host": _host,
    "user": _user,
    "passwd": _pwd,
    "db": _database,
    "port": int(_port),
    "charset": "utf8mb4",
}

# 连接池
pool = PooledDB(pymysql, **_db_connection_args)


# 临时处理，选项中的图片未替换的问题
# def download_image(url, download_path):
#     try:
#         # 判断download_path文件夹是否存在, 不存在则创建
#         if not os.path.exists(os.path.dirname(download_path)):
#             os.makedirs(os.path.dirname(download_path))
#         response = requests.get(url)
#         if response.status_code == 200:
#             with open(download_path, 'wb') as f:
#                 f.write(response.content)
#         else:
#             raise Exception(f"下载图片失败：{url}, status code not 200, status code：{response.status_code}")
#     except Exception as e:
#         raise Exception(f"下载图片失败：{url}, 错误信息：{e}")
#
#
# def replace_img_url_to_server(html_str):
#     soup = BeautifulSoup(html_str, 'html.parser')
#     img_array = soup.find_all('img', {"src": True})
#     if len(img_array) == 0:
#         return html_str
#     pattern = re.compile(r'.*(https?://docimg\d+\.docs\.qq\.com).*')
#     for img in img_array:
#         img_url = img.get('src')
#         if img_url.startswith('data:image'):
#             continue
#         # 如果 url 包含 https://docimg7.docs.qq.com，不进行替换
#         if pattern.search(img_url):
#             continue
#         try:
#             img_name = os.path.basename(img_url)
#             download_path = os.path.join(os.getcwd(), '51cto_options', img_name)
#             download_image(img_url, download_path)
#             # new_img_url = upload_image_to_server(download_path)
#             # img['src'] = new_img_url
#             # os.remove(download_path)  # 删除下载的图片
#
#             # 把图片下载到本地，后面统一上传到服务器
#             base_url = f'http://{config.get("pic_server_base_host")}/images/51cto/'
#             new_img_url = base_url + img_name
#             img['src'] = new_img_url
#         except Exception as e:
#             raise e
#     return str(soup)
#
#
#
# db = pool.connection()
# #     查询 oems_questoption_v2 表    CONTENT like "%51cto.com/images%"
# cursor = db.cursor()
# sql_oems_questoption_v2 = "SELECT ID,CONTENT FROM oems_questoption_v2 WHERE CONTENT like '%51cto.com/images%' "
# cursor.execute(sql_oems_questoption_v2)
# options = cursor.fetchall()
# for option in options:
#     print(f'old: {option[1]}')
#     new_option = replace_img_url_to_server(option[1])
#     print(f'new: {new_option}')
#     sql_update = f"UPDATE oems_questoption_v2 SET CONTENT = '{new_option}' WHERE ID = {option[0]}"
#     cursor.execute(sql_update)
#     db.commit()
#     print(f'update success: {option[0]}')
# db.close()
