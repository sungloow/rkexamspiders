import json
from import_to_oems.add_node_oems import add_node_date, create_dict_from_folder
from import_to_oems.import_question_to_oems import import_process
from import_to_oems.replace_pic import process
from logger import logger
from utils.json_handle import extract_bottom_level_keys, read_json
import logging

logger = logging.getLogger("oems")



def test_replace_xisai_pic():
    logger.info("开始替换希赛图片")
    input_folder = "output/软件评测师"
    process(input_folder=input_folder, is_xisai=True)
    logger.info("替换希赛图片完成")

def test_add_node():
    # # 增量导入的时候需要将以前的oems_node_structure传入，在add node的时候跳过已有的节点
    # already_imported_node_structure = read_json(
    #     f"data/oems_node_structure_production_51CTO软考25年下半年.json"
    # )
    # # 将结构中的所有底层的key提取出来
    # already_imported_node_list = extract_bottom_level_keys(
    #     already_imported_node_structure
    # )
    # logger.info(f"需要跳过的节点：{already_imported_node_list}")

    sub = "软件设计师"
    folder_path = "output/软件设计师_replaced/软件设计师"
    data_dict = create_dict_from_folder(
        folder_path, skip_keys=None
    )
    logger.info(data_dict)
    # # 生产环境 parent_lft：3198，测试环境 parent_lft：3212
    folder_path_list = folder_path.split("/")
    data = data_dict[folder_path_list[0]][folder_path_list[1]]
    add_node_date(data, "3704")
    # 保存为JSON文件
    with open(
        "data/oems_node_structure_production_{}.json".format(sub),
        mode="w",
        encoding="utf-8",
    ) as f:
        json.dump(data_dict, f, indent=4, ensure_ascii=False)

def test_import_xisai():
    from import_to_oems.db_pool import pool

    sub = "软件设计师"
    folder_path = "output/软件设计师_replaced/软件设计师"

    node_structure = read_json(f"data/oems_node_structure_production_{sub}.json")
    db = pool.connection()

    folder_path_list = folder_path.split("/")
    data = node_structure[folder_path_list[0]][folder_path_list[1]][folder_path_list[2]]
    import_process(data, folder_path, is_xisai=True, db=db)
    db.close()

if __name__ == "__main__":
    test_replace_xisai_pic()
    # test_add_node()
    # test_import_xisai()