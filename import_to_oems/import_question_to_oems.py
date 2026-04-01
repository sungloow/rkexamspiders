import datetime
import inspect
import json

import pymysql

from import_to_oems import logger

from import_to_oems.custom_exceptions import DuplicateEntryError, DBError


class QuestionOptions(object):
    def __init__(self, content, sort_index):
        self.content = content
        self.sort_index = sort_index

    def __str__(self):
        return "QuestionOptions: content: %s, sort_index: %s" % (
            self.content,
            self.sort_index,
        )


class QuestionDetail(object):
    def __init__(
        self,
        score,
        answer,
        content,
        quest_analyze,
        quest_type,
        question_options: list = [],
    ):
        self.score = int(score)
        self.answer = answer
        self.content = content
        self.quest_analyze = quest_analyze
        self.quest_type = quest_type
        self.sort_index = 0
        self.question_options = question_options

    def __str__(self):
        return (
            "QuestionDetail: answer: %s, content: %s, quest_analyze: %s, quest_type: %s, sort_index: %s, "
            "question_options num: %s"
        ) % (
            self.answer,
            self.content,
            self.quest_analyze,
            self.quest_type,
            self.sort_index,
            len(self.question_options),
        )

    def set_question_options(self, _question_options: list):
        if isinstance(_question_options, list):
            self.question_options = _question_options
        else:
            raise Exception("question_options is not instance of list")


class Question(object):
    def __init__(self, quest_type, quest_detail: QuestionDetail = None):
        self.quest_type = quest_type
        self.quest_detail = quest_detail
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.create_date = current_time
        self.update_date = current_time
        self.del_flag = 0
        self.status = 3
        self.use_times = 0
        self.comp_id = 1
        self.dep_id = 2

    def __str__(self):
        return "Question: quest_type: %s, quest_detail: %s" % (
            self.quest_type,
            self.quest_detail,
        )

    def set_question_detail(self, _question_detail):
        if isinstance(_question_detail, QuestionDetail):
            self.quest_detail = _question_detail
        else:
            raise Exception("question_detail is not instance of QuestionDetail")


def save(db, question_info: Question, node_id: int):
    cursor = db.cursor()
    sql_oems_questinfo_v2 = (
        "INSERT INTO oems_questinfo_v2 "
        "(CREATE_DATE, UPDATE_DATE, DEL_FLAG, STATUS, `TYPE`, USE_TIMES, CREATE_BY, UPDATE_BY, "
        "COMP_ID, DEP_ID)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    sql_oems_qi_detail_v2 = (
        "INSERT INTO oems_qi_detail_v2 (ANSWER, CONTENT, QUEST_ANALYZE, QUEST_TYPE, SORT_INDEX, QI_ID, SCORE) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    sql_oems_questoption_v2 = "INSERT INTO oems_questoption_v2 (CONTENT, SORT_INDEX, QID_ID) VALUES (%s, %s, %s)"
    sql_oems_questinfo_node = (
        "INSERT INTO oems_questinfo_node (QUESTINFO_ID, NODE_ID) VALUES (%s, %s)"
    )
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        create_date = current_time
        update_date = current_time
        cursor.execute(
            sql_oems_questinfo_v2,
            (
                create_date,
                update_date,
                str(question_info.del_flag),
                question_info.status,
                question_info.quest_type,
                question_info.use_times,
                1,
                1,
                question_info.comp_id,
                question_info.dep_id,
            ),
        )
        oems_questinfo_v2_id = cursor.lastrowid
        cursor.execute(sql_oems_questinfo_node, (oems_questinfo_v2_id, node_id))
        question_detail = question_info.quest_detail
        cursor.execute(
            sql_oems_qi_detail_v2,
            (
                question_detail.answer,
                question_detail.content,
                question_detail.quest_analyze,
                question_detail.quest_type,
                question_detail.sort_index,
                oems_questinfo_v2_id,
                question_detail.score,
            ),
        )
        oems_qi_detail_v2_id = cursor.lastrowid
        # 选择题才需要插入选项
        if question_info.quest_type == 1:
            question_options = question_detail.question_options
            for option in question_options:
                cursor.execute(
                    sql_oems_questoption_v2,
                    (option.content, option.sort_index, oems_qi_detail_v2_id),
                )
        db.commit()
    # 主键冲突
    except pymysql.IntegrityError as e:
        db.rollback()
        raise DuplicateEntryError(e, __name__, inspect.currentframe().f_lineno)
    except pymysql.Error as e:
        db.rollback()
        raise DBError(e, __name__, inspect.currentframe().f_lineno)
    else:
        row_count = cursor.rowcount
        return oems_questinfo_v2_id
    finally:
        cursor.close()


def read_json(_path):
    with open(_path, "r", encoding="utf-8") as _f:
        _data = json.load(_f)
    return _data


def convert_answer(answer):
    if answer == "A":
        return "0"
    elif answer == "B":
        return "1"
    elif answer == "C":
        return "2"
    elif answer == "D":
        return "3"
    else:
        raise Exception("convert answer error: %s" % answer)


def convert_answer_true_false_xisai(answer):
    if answer == "A":
        return "1"
    elif answer == "B":
        return "2"
    else:
        raise Exception("convert answer error: %s" % answer)


def create_the_paper_question_xisai(question, oems_type):
    """
    创建希赛综合题
    """
    question_title = question.get("tigan") or question.get("cTigan")
    analyze = question.get("analysis", "")
    answer = question["answer"]
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_the_paper_question(question, oems_type):
    """
    创建综合题
    """
    question_title = question.get("question_title", "")
    analyze = question.get("analyze", "")
    answer = question["answer"][0]
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_the_blank_question(question, oems_type):
    """
    创建填空题
    """
    question_title = question.get("question_title", "")
    analyze = question.get("analyze", "")
    answers = question.get("answer", [])
    answer = "、".join(answers)
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_multiple_choice_question(question, oems_type):
    """
    创建多选题
    """
    question_title = question.get("question_title", "")
    analyze = question.get("analyze", "")
    answers = question.get("answer", [])
    answer_convert = []
    for answer_item in answers:
        answer_convert.append(convert_answer(answer_item))
    answer = ",".join(answer_convert)
    score = question.get("score", 0)
    option_list = question["option"]
    question_options = []
    for option in option_list:
        question_options.append(QuestionOptions(option, option_list.index(option)))
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_detail.set_question_options(question_options)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_single_choice_question(question, oems_type):
    """
    创建选择题(单选)
    """
    question_title = question.get("question_title", "")
    analyze = question.get("analyze", "")
    answer = question["answer"][0]
    answer = convert_answer(answer)
    score = question.get("score", 0)
    option_list = question["option"]
    question_options = []
    for option in option_list:
        question_options.append(QuestionOptions(option, option_list.index(option)))
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_detail.set_question_options(question_options)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_single_choice_question_xisai(question, oems_type):
    """
    创建选择题(单选)
    """
    question_title = question.get("tigan") or question.get("cTigan")
    analyze = question.get("analysis", "")
    answer = question["answer"][0]
    answer = convert_answer(answer)
    score = question.get("score", 0)
    option_map = question["options"]
    question_options = []
    for option_key, option_value in option_map.items():
        question_options.append(
            QuestionOptions(option_value, convert_answer(option_key))
        )
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_detail.set_question_options(question_options)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_true_false_question_xisai(question, oems_type):
    """
    创建希赛判断题
    """
    question_title = question.get("tigan") or question.get("cTigan")
    analyze = question.get("analysis", "")
    answer = question["answer"][0]
    answer = convert_answer_true_false_xisai(answer)
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_short_answer_question(question, oems_type):
    """
    创建简答题
    """
    question_title = question.get("question_title", "")
    analyze = question.get("analyze", "")
    answer = question["answer"][0]
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def create_short_answer_question_xisai(question, oems_type):
    """
    创建简答题
    """
    question_title = question.get("tigan") or question.get("cTigan")
    analyze = question.get("analysis", "")
    answer = question["answer"]
    score = question.get("score", 0)
    question_detail = QuestionDetail(score, answer, question_title, analyze, oems_type)
    question_info = Question(oems_type, question_detail)
    return question_info


def save_question(_db, _question_info, _node_id):
    oems_questinfo_v2_id = save(_db, _question_info, int(_node_id))
    return oems_questinfo_v2_id


def process_questions(file_path, node_id, is_xisai, db):
    logger.info(f"node_id: {node_id}, file: {file_path}")
    try:
        question_data = read_json(file_path)
    except FileNotFoundError as e:
        logger.warning(e)
        return 0, 0

    count_success = 0
    count_fail = 0

    for question in question_data["questions"]:
        question_type = int(question["question_type_code" if is_xisai else "question_type"])
# 0\3\5\7
        if question_type in [0, 1, 8, 9, 95]:  # 选择题
            oems_type = 1
            question_info = (
                create_single_choice_question(question, oems_type)
                if not is_xisai
                else create_single_choice_question_xisai(question, oems_type)
            )
        elif question_type in [5, 14, 98, 101]:  # 简答题
            oems_type = 5
            question_info = (
                create_short_answer_question(question, oems_type)
                if not is_xisai
                else create_short_answer_question_xisai(question, oems_type)
            )
        elif question_type == 2:  # 多选题
            oems_type = 2
            question_info = create_multiple_choice_question(question, oems_type)
        elif question_type in [97, 3]:  # 希赛判断题97, 3
            oems_type = 3
            question_info = create_true_false_question_xisai(question, oems_type)
        elif question_type == 4:  # 填空题
            oems_type = 4
            question_info = create_the_blank_question(question, oems_type)
        elif question_type == 6:  # 编程题
            oems_type = 6
            question_info = create_short_answer_question(question, oems_type)
        elif question_type in [15, 99, 7]:  # 论文题
            oems_type = 7
            question_info = (
                create_the_paper_question(question, oems_type)
                if not is_xisai
                else create_the_paper_question_xisai(question, oems_type)
            )
        else:
            logger.error(
                f"不支持该题型：{question_type}, file: {file_path}, index: {question['id' if is_xisai else 'index']}"
            )
            continue

        try:
            oems_questinfo_v2_id = save_question(db, question_info, node_id)
            logger.info(
                f"导入成功, oems_questinfo_v2_id: {oems_questinfo_v2_id}, file: {file_path}, index: {question['priority' if is_xisai else 'index']}"
            )
            count_success += 1
        except Exception as e:
            count_fail += 1
            logger.error(
                f"导入失败, file: {file_path}, index: {question['priority' if is_xisai else 'index']}, error: {e}"
            )

    return count_success, count_fail


def import_process(_node_structure, _root, is_xisai=False, db=None):
    def traverse(data, path):
        nonlocal total_success, total_fail
        if isinstance(data, str):  # 叶子节点
            file_path = f"{_root}/{'/'.join(path)}.json"
            logger.info(f"file_path: {file_path}")
            success, fail = process_questions(file_path, data, is_xisai, db)
            total_success += success
            total_fail += fail
        elif isinstance(data, dict):
            for key, value in data.items():
                traverse(value, path + [key])

    total_success = 0
    total_fail = 0
    traverse(_node_structure, [])
    logger.info(
        f"导入试题完成。导入成功数量: {total_success}, 导入失败数量: {total_fail}"
    )


# oems -> 单选：1，多选：2，判断：3，填空：4，简答：5，编程题：6，综合题：7
# 51CTO -> 单选：1，完形填空题：8，完形类单选题：9，多选：2，简答：5，[材料型]问答题：14，编程题：6，论文题：15，填空：4
