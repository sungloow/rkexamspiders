# -*- coding: utf-8 -*-

import json
import os


def write_json(file_path, json_obj):
    """
    :description:写入json
    @param file_path: 文件路径
    @param json_obj: json对象
    """
    # 如果文件夹不存在则创建
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    json_str = json.dumps(json_obj, ensure_ascii=False, indent=2)
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(json_str)


def read_json(file_path):
    """
    :description:读取json
    @param file_path: 文件路径
    @:return json obj
    """

    with open(file_path, mode="r", encoding="utf-8") as d:
        return json.load(d)


def extract_bottom_level_keys(data, bottom_keys=None):
    """
    递归提取JSON数据中所有最底层的key（即值不是字典的key）

    :param data: 要处理的JSON数据（字典或其他类型）
    :param bottom_keys: 用于收集底层key的列表（内部使用）
    :return: 包含所有底层key的列表
    """
    if bottom_keys is None:
        bottom_keys = []

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                # 如果值是字典，继续递归
                extract_bottom_level_keys(value, bottom_keys)
            else:
                # 如果值不是字典，这就是底层key
                bottom_keys.append(key)

    return bottom_keys


def extract_bottom_level_values(data, bottom_values=None):
    """
    递归提取JSON数据中所有最底层的值（即不是字典的值）

    :param data: 要处理的JSON数据（字典或其他类型）
    :param bottom_values: 用于收集底层值的列表（内部使用）
    :return: 包含所有底层值的列表
    """
    if bottom_values is None:
        bottom_values = []

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                # 如果值是字典，继续递归
                extract_bottom_level_values(value, bottom_values)
            else:
                # 如果值不是字典，这就是底层值
                bottom_values.append(value)

    return bottom_values


def extract_bottom_level_key_value_pairs(data, bottom_pairs=None):
    """
    递归提取JSON数据中所有最底层的key-value对（即值不是字典的键值对）

    :param data: 要处理的JSON数据（字典或其他类型）
    :param bottom_pairs: 用于收集底层键值对的列表（内部使用）
    :return: 包含所有底层键值对的列表，每个元素是(key, value)元组
    """
    if bottom_pairs is None:
        bottom_pairs = []

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                # 如果值是字典，继续递归
                extract_bottom_level_key_value_pairs(value, bottom_pairs)
            else:
                # 如果值不是字典，这就是底层键值对
                bottom_pairs.append((key, value))

    return bottom_pairs


def remove_empty_dicts(data):
    """
    递归移除JSON数据中的空字典层级

    :param data: 要处理的JSON数据
    :return: 移除空字典后的数据
    """
    if isinstance(data, dict):
        # 递归处理字典中的所有值
        cleaned_dict = {}
        for key, value in data.items():
            cleaned_value = remove_empty_dicts(value)
            # 只保留非空的值
            if (
                cleaned_value
                or cleaned_value == 0
                or cleaned_value == ""
                or cleaned_value is False
            ):
                # 对于字典类型，只有非空字典才保留
                if isinstance(cleaned_value, dict):
                    if cleaned_value:  # 非空字典
                        cleaned_dict[key] = cleaned_value
                else:
                    # 非字典类型的值都保留（包括None、0、""、False等）
                    cleaned_dict[key] = cleaned_value
        return cleaned_dict
    elif isinstance(data, list):
        # 递归处理列表中的所有元素
        cleaned_list = []
        for item in data:
            cleaned_item = remove_empty_dicts(item)
            # 对于列表项，只有非空字典才需要特殊处理
            if isinstance(cleaned_item, dict):
                if cleaned_item:  # 非空字典才添加
                    cleaned_list.append(cleaned_item)
            else:
                # 非字典类型的项都保留
                cleaned_list.append(cleaned_item)
        return cleaned_list
    else:
        # 非字典和列表类型直接返回
        return data


def remove_empty_dicts_keep_structure(data):
    """
    递归移除JSON数据中的空字典层级，但保留有子节点的中间层级结构

    :param data: 要处理的JSON数据
    :return: 移除空字典后的数据
    """
    if isinstance(data, dict):
        cleaned_dict = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # 递归处理子字典
                cleaned_value = remove_empty_dicts_keep_structure(value)
                # 如果处理后的字典不为空，则保留
                if cleaned_value:
                    cleaned_dict[key] = cleaned_value
            else:
                # 非字典类型的值直接保留
                cleaned_dict[key] = value
        return cleaned_dict
    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = remove_empty_dicts_keep_structure(item)
            if isinstance(cleaned_item, dict):
                if cleaned_item:  # 非空字典才添加
                    cleaned_list.append(cleaned_item)
            else:
                cleaned_list.append(cleaned_item)
        return cleaned_list
    else:
        return data
