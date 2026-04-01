import json
import os

import requests
from import_to_oems import logger
from utils.json_handle import remove_empty_dicts_keep_structure


def create_dict_from_folder(path, skip_keys=None):
    data = {}
    for root, dirs, files in os.walk(path):
        current = data
        for dir in root.split(os.sep):
            if dir:
                current = current.setdefault(dir, {})
        for file in files:
            file_name = os.path.splitext(file)[0]  # 移除文件后缀名
            if skip_keys and file_name in skip_keys:
                continue
            current[file_name] = None
    # 移除空字典的层级
    data = remove_empty_dicts_keep_structure(data)
    return data


def add_node_to_oems(node_name, lft, _type):
    # return {
    #     "id": 111,
    #     "name": node_name,
    #     "code": None,
    #     "lft": lft,
    #     "rgt": None,
    #     "pId": None,
    #     "category": "none"
    # }
    # _type: nbthr  添加兄弟节点
    # _type: lchld  添加叶子节点
    # url = "http://localhost:8080/oems_war/sys/node/add"
    # 生产环境！！！！begin
    url = "http://172.26.66.92/oems/sys/node/add"
    # 生产环境！！！！end
    payload = {"name": node_name, "lft": lft, "type": _type, "category": "none"}
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en-CN;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "DNT": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "^sec-ch-ua": "^^Chromium^^;v=^^122^^, ^^Not(A:Brand^^;v=^^24^^, ^^Google",
        "sec-ch-ua-mobile": "?0",
        "^sec-ch-ua-platform": "^^Windows^^^",
        "Cookie": "JSESSIONID=68CB8B25D90B77F84E9A90F0611D14BC",
    }
    # {
    #     "id": "3055",
    #     "name": "new node1",
    #     "code": null,
    #     "lft": "3219",
    #     "rgt": "3220",
    #     "pId": "3050",
    #     "category": "none"
    # }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()


def add_node_date(_dict, parent_lft):
    # 添加节点
    for key, value in _dict.items():
        logger.info("添加节点：{}".format(key))
        rkey = add_node_to_oems(key, parent_lft, "lchld")
        logger.info("添加结果：", rkey)
        lft = rkey["lft"]
        logger.info("======================")
        for k, v in value.items():
            logger.info("添加节点：{}/{}".format(key, k))
            rk = add_node_to_oems(k, lft, "lchld")
            logger.info("添加结果：", rk)
            lft_k = rk["lft"]
            logger.info("======================")
            if type(v) is dict:
                for kk, vv in v.items():
                    logger.info("添加节点：{}/{}/{}".format(key, k, kk))
                    rkk = add_node_to_oems(kk, lft_k, "lchld")
                    logger.info("添加结果：", rkk)
                    lft_kk = rkk["lft"]
                    logger.info("======================")
                    if type(vv) is dict:
                        for kkk, vvv in vv.items():
                            logger.info("添加节点：{}/{}/{}/{}".format(key, k, kk, kkk))
                            rkkk = add_node_to_oems(kkk, lft_kk, "lchld")
                            logger.info("添加结果：", rkkk)
                            _dict[key][k][kk][kkk] = rkkk["id"]
                            logger.info("======================")
                    else:
                        _dict[key][k][kk] = rkk["id"]
            else:
                _dict[key][k] = rk["id"]
