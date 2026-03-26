import scrapy
import json
import base64
from copy import deepcopy
from urllib.parse import urlencode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from scrapy.exceptions import CloseSpider, NotConfigured
from rkexamspiders.output_path import build_output_file_path


def aes_ecb_decrypt(encrypted_b64: str, key: str) -> str:
    """AES-ECB + PKCS7 解密，与前端 CryptoJS 实现完全对应"""
    key_bytes = key.encode("utf-8")
    data = base64.b64decode(encrypted_b64)
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
    return decrypted.decode("utf-8")


class XisaiSpider(scrapy.Spider):
    name = "xisai"
    allowed_domains = ["wangxiao.xisaiwang.com"]

    def __init__(
        self,
        subject_path=None,
        subject_name=None,
        exam_root_name=None,
        paper_type=None,
        crawl_tasks=None,
        skip_existing=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.paper_buffers = {}
        self.auth_context = {}
        self.subject_path_arg = subject_path
        self.subject_name_arg = subject_name
        self.exam_root_name_arg = exam_root_name
        self.paper_type_arg = paper_type
        self.crawl_tasks_arg = crawl_tasks
        self.skip_existing_arg = skip_existing

    # 默认认证信息（占位）。后续可在 login() 中替换为真实登录流程。
    DEFAULT_AUTH_CONTEXT = {
        
    }

    BASE_URL = "https://wangxiao.xisaiwang.com/stuapi"
    PRODUCT_API_BASE_URL = "https://wangxiao.xisaiwang.com/productapi"
    FRONT_URL = "https://wangxiao.xisaiwang.com/nstu"

    _COMMON_HEADERS = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://wangxiao.xisaiwang.com",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "clientType": "PC",
        "v": "1.0.1",
        "iar": "iar",
        "market": "s1:101:131:_mweb_v1.0.1",
    }

    PAPER_TYPE_NAME_MAP = {
        "125": "知识点练习",
        "63": "模拟试卷",
        "62": "章节练习",
        "60": "历年真题",
    }
    PAPER_LIST_TYPES = {"60", "62", "63"}
    KNOWLEDGE_TYPE = "125"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.CRAWL_TASKS = spider._load_crawl_tasks(crawler)
        raw_skip_existing = spider.skip_existing_arg
        if raw_skip_existing is None:
            raw_skip_existing = crawler.settings.get("XISAI_SKIP_EXISTING_PAPERS", True)
        spider.SKIP_EXISTING_PAPERS = spider._is_truthy(raw_skip_existing)
        return spider

    def _is_truthy(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def _load_crawl_tasks(self, crawler):
        task_list = []
        raw_tasks = self.crawl_tasks_arg or crawler.settings.get("XISAI_CRAWL_TASKS")

        if isinstance(raw_tasks, str) and raw_tasks.strip():
            try:
                raw_tasks = json.loads(raw_tasks)
            except json.JSONDecodeError as exc:
                raise NotConfigured(f"crawl_tasks 不是合法 JSON: {exc}") from exc

        if isinstance(raw_tasks, list) and raw_tasks:
            for idx, raw in enumerate(raw_tasks, start=1):
                if not isinstance(raw, dict):
                    raise NotConfigured(f"XISAI_CRAWL_TASKS 第 {idx} 项必须是对象")
                task_list.append(self._normalize_task(raw, idx))
        else:
            single_task = {
                "subject_path": self.subject_path_arg or crawler.settings.get("XISAI_SUBJECT_PATH"),
                "subject_name": self.subject_name_arg or crawler.settings.get("XISAI_SUBJECT_NAME"),
                "exam_root_name": self.exam_root_name_arg or crawler.settings.get("XISAI_EXAM_ROOT_NAME"),
                "paper_type": self.paper_type_arg or crawler.settings.get("XISAI_PAPER_TYPE"),
            }
            task_list.append(self._normalize_task(single_task, 1))

        return task_list

    def _normalize_task(self, raw: dict, idx: int) -> dict:
        subject_path = raw.get("subject_path")
        subject_name = raw.get("subject_name")
        exam_root_name = raw.get("exam_root_name")
        paper_type = raw.get("paper_type")

        subject_path = str(subject_path).strip() if subject_path else None
        subject_name = str(subject_name).strip() if subject_name else None
        exam_root_name = str(exam_root_name).strip() if exam_root_name else None
        paper_type = str(paper_type).strip() if paper_type else None

        if not subject_path and not subject_name:
            raise NotConfigured(
                f"任务 {idx} 缺少科目配置：请提供 subject_path 或 subject_name"
            )
        if not paper_type:
            raise NotConfigured(f"任务 {idx} 缺少题型配置：请提供 paper_type")
        if paper_type not in self.PAPER_TYPE_NAME_MAP:
            raise NotConfigured(
                f"任务 {idx} 的 paper_type={paper_type} 暂不支持，仅支持 60/62/63/125"
            )

        return {
            "task_id": f"task_{idx}",
            "subject_path": subject_path,
            "subject_name": subject_name,
            "exam_root_name": exam_root_name,
            "paper_type": paper_type,
            "paper_type_name": self.PAPER_TYPE_NAME_MAP.get(paper_type, paper_type),
        }

    def login(self) -> dict:
        """占位登录函数：当前返回固定认证信息，后续替换为真实登录逻辑。"""
        return dict(self.DEFAULT_AUTH_CONTEXT)

    def _ensure_auth_context(self):
        if self.auth_context:
            return
        self.auth_context = self.login() or {}

    def _headers(self, referer: str = "") -> dict:
        self._ensure_auth_context()
        h = dict(self._COMMON_HEADERS)
        h["cstk"] = self.auth_context.get("cstk", "")
        h["cid"] = self.auth_context.get("cid", "")
        if referer:
            h["Referer"] = referer
        return h

    def _cookies(self) -> dict:
        self._ensure_auth_context()
        result = {}
        raw_cookies = self.auth_context.get("raw_cookies", "")
        for part in raw_cookies.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def _init_paper_buffer(self, paper_meta: dict, total_count: int, task: dict):
        paper_id = str(paper_meta["id"])
        buffer_key = f"{task['task_id']}::{paper_id}"
        self.paper_buffers[buffer_key] = {
            "subject_name": task.get("subject_name"),
            "subject_path": task.get("subject_path"),
            "paper_type": task.get("paper_type"),
            "paper_type_name": task.get("paper_type_name"),
            "paper_id": paper_meta["id"],
            "paper_name": paper_meta["paperName"],
            "paper_year": paper_meta.get("paperYear"),
            "expected": total_count,
            "done": 0,
            "questions": [],
        }
        return buffer_key

    def _append_question(self, buffer_key: str, item: dict):
        paper = self.paper_buffers[buffer_key]
        paper["questions"].append(item)
        paper["done"] += 1

        if paper["done"] == paper["expected"]:
            paper["questions"].sort(key=lambda q: int(q.get("priority") or 0))
            result = {
                "subject_name": paper.get("subject_name"),
                "subject_path": paper.get("subject_path"),
                "paper_type": paper.get("paper_type"),
                "paper_type_name": paper.get("paper_type_name"),
                "paper_id": paper["paper_id"],
                "paper_name": paper["paper_name"],
                "paper_year": paper["paper_year"],
                "questions": paper["questions"],
            }
            del self.paper_buffers[buffer_key]
            return result

        return None

    # ── 第一步：翻页获取试卷列表 ──────────────────────────

    def start_requests(self):
        self._ensure_auth_context()

        pending_tasks = []
        for task in self.CRAWL_TASKS:
            if task.get("subject_path"):
                yield from self._start_task_requests(deepcopy(task))
            else:
                pending_tasks.append(deepcopy(task))

        if pending_tasks:
            yield self._subject_tree_request(pending_tasks)

    def _subject_tree_request(self, pending_tasks):
        referer = f"{self.FRONT_URL}/pages/exam/index/index"
        return scrapy.Request(
            url=f"{self.PRODUCT_API_BASE_URL}/app/v2/classify/examClassifyTree.do",
            method="POST",
            headers=self._headers(referer),
            body=urlencode({"vip": "Y"}),
            cookies=self._cookies(),
            callback=self.parse_subject_tree,
            cb_kwargs={"pending_tasks": pending_tasks},
        )

    def parse_subject_tree(self, response, pending_tasks):
        data = response.json()
        model = data.get("model")
        if not isinstance(model, list):
            raise CloseSpider("科目树响应异常：model 不是列表")

        for task in pending_tasks:
            target_name = task.get("subject_name")
            root_name = task.get("exam_root_name")
            match_node = self._find_subject_node(model, target_name, root_name)
            if not match_node:
                root_msg = f"（根节点={root_name}）" if root_name else ""
                raise CloseSpider(f"未找到科目：{target_name}{root_msg}")

            classify_id = match_node.get("classifyId") or match_node.get("examClassifyId")
            if not classify_id:
                raise CloseSpider(f"科目缺少 classifyId：{target_name}")

            task["subject_path"] = str(classify_id)
            task["subject_name"] = str(match_node.get("name") or target_name)
            self.logger.info(
                "任务 %s 已自动解析科目：name=%s, subject_path=%s, paper_type=%s",
                task.get("task_id"),
                task.get("subject_name"),
                task.get("subject_path"),
                task.get("paper_type"),
            )
            yield from self._start_task_requests(task)

    def _start_task_requests(self, task: dict):
        paper_type = task.get("paper_type")
        if paper_type in self.PAPER_LIST_TYPES:
            yield self._paper_list_request(page=1, task=task)
            return
        if paper_type == self.KNOWLEDGE_TYPE:
            yield self._knowledge_section_request(task=task)
            return
        raise CloseSpider(
            f"任务 {task.get('task_id')} 的题型 {paper_type} 暂不支持"
        )

    def _find_subject_node(self, nodes, target_name: str, root_name: str = None):
        search_nodes = nodes
        if root_name:
            root = self._find_node_by_name(nodes, root_name)
            if not root:
                return None
            search_nodes = root.get("children") or []
        return self._find_node_by_name(search_nodes, target_name)

    def _find_node_by_name(self, nodes, name: str):
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            if node.get("name") == name:
                return node
            child_match = self._find_node_by_name(node.get("children") or [], name)
            if child_match:
                return child_match
        return None

    def _paper_list_request(self, page: int, task: dict):
        return scrapy.Request(
            url=f"{self.BASE_URL}/tiku/paper/list.do",
            method="POST",
            headers=self._headers(f"{self.FRONT_URL}/"),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "pageNum": str(page),
                "pageSize": "20",
            }),
            cookies=self._cookies(),
            callback=self.parse_paper_list,
            cb_kwargs={"page": page, "task": task},
        )

    def _knowledge_section_request(self, task: dict):
        referer = f"{self.FRONT_URL}/sub/exam/knowledgeNode/knowledgeNode"
        return scrapy.Request(
            url=f"{self.BASE_URL}/tiku/section/userSectionlist.do",
            method="POST",
            headers=self._headers(referer),
            body=urlencode({
                "subjectPath": task["subject_path"],
            }),
            cookies=self._cookies(),
            callback=self.parse_knowledge_sections,
            cb_kwargs={"task": task},
        )

    def parse_paper_list(self, response, page: int, task: dict):
        data = response.json()
        papers = data.get("model", {}).get("datas", [])
        if not papers:
            self.logger.info(
                "任务 %s 第 %s 页无数据，列表抓取完毕", task.get("task_id"), page
            )
            return

        self.logger.info(
            "任务 %s 第 %s 页获取到 %s 套试卷（科目=%s, 题型=%s）",
            task.get("task_id"),
            page,
            len(papers),
            task.get("subject_name") or task.get("subject_path"),
            task.get("paper_type_name"),
        )

        for p in papers:
            if self.SKIP_EXISTING_PAPERS:
                file_path = build_output_file_path(
                    subject_name=task.get("subject_name"),
                    subject_path=task.get("subject_path"),
                    paper_type_name=task.get("paper_type_name"),
                    paper_type=task.get("paper_type"),
                    paper_name=p.get("paperName"),
                    paper_id=p.get("id"),
                )
                if file_path.exists():
                    self.logger.info(
                        "任务 %s 跳过已存在试卷：%s",
                        task.get("task_id"),
                        file_path,
                    )
                    continue
            yield self._check_zuoti_request(p, task)

        # 自动翻到下一页
        yield self._paper_list_request(page=page + 1, task=task)

    def parse_knowledge_sections(self, response, task: dict):
        data = response.json()
        model = data.get("model") or {}
        sections = model.get("sectionTreeResponseList") or []
        if not isinstance(sections, list):
            self.logger.warning(
                "任务 %s 知识点章节响应结构异常：sectionTreeResponseList 不是列表",
                task.get("task_id"),
            )
            return

        self.logger.info(
            "任务 %s 获取到 %s 个知识点大节（科目=%s）",
            task.get("task_id"),
            len(sections),
            task.get("subject_name") or task.get("subject_path"),
        )

        for section in sections:
            if not isinstance(section, dict):
                continue

            # 只处理顶级节点（parentId=0），用父节点id获取时会包含所有子节点题目
            parent_id = section.get("parentId")
            if parent_id != 0:
                continue

            section_id = section.get("id")
            section_name = section.get("name") or f"section_{section_id}"
            if self.SKIP_EXISTING_PAPERS:
                file_path = build_output_file_path(
                    subject_name=task.get("subject_name"),
                    subject_path=task.get("subject_path"),
                    paper_type_name=task.get("paper_type_name"),
                    paper_type=task.get("paper_type"),
                    paper_name=section_name,
                    paper_id=section_id,
                )
                if file_path.exists():
                    self.logger.info(
                        "任务 %s 跳过已存在知识点大节：%s",
                        task.get("task_id"),
                        file_path,
                    )
                    continue

            # 转换为兼容格式调用 _check_zuoti_request（与 60/62/63 流程相同）
            # 用父节点id去请求会自动获取该节点下所有子节点的题目
            section_meta = {
                "id": section_id,
                "paperName": section_name,
            }
            yield self._check_zuoti_request(section_meta, task)

    # ── 第二步：检查权限 ──────────────────────────────────

    def _check_zuoti_request(self, paper_meta: dict, task: dict):
        paper_id = str(paper_meta["id"])
        paper_name = paper_meta["paperName"]
        referer = (
            f"{self.FRONT_URL}/sub/exam/maths/dailyPracticeTestPaper/"
            f"dailyPracticeTestPaper?paperId={paper_id}&paperName={paper_name}"
        )
        # {
#     "model": {
#         "auth": "Y",
#         "key": "20805828_60_30414653_PC"
#     },
#     "resultCode": "SUCCESS",
#     "resultMsg": "成功",
#     "extraData": {},
#     "success": true
# }
        return scrapy.Request(
            url=f"{self.BASE_URL}/user/checkZuoti.do",
            method="POST",
            headers=self._headers(referer),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "dataId": paper_id,
            }),
            cookies=self._cookies(),
            callback=self.start_exam,
            cb_kwargs={"paper_meta": paper_meta, "task": task},
        )

    # ── 第三步：开启考试会话，获取 paperLogId ─────────────

    def start_exam(self, response, paper_meta: dict, task: dict):
        paper_id = str(paper_meta["id"])
        paper_name = paper_meta["paperName"]
        result_code = response.json().get("resultCode")
        if result_code != "SUCCESS":
            self.logger.warning(
                f"检查权限失败，paperId={paper_id}，响应：{response.text}"
            )
            return
        result_data = response.json().get("model", {})
        key = result_data.get("key")
        if not key:
            self.logger.warning(
                f"未获取到 key，paperId={paper_id}，响应：{response.text}"
            )
            return
        referer = (
            f"{self.FRONT_URL}/sub/exam/maths/dailyPracticeTestPaper/"
            f"dailyPracticeTestPaper?paperId={paper_id}&paperName={paper_name}"
        )
        yield scrapy.Request(
            url=f"{self.BASE_URL}/zuoti/startExam.do",
            method="POST",
            headers=self._headers(referer),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "dataId": paper_id,
                "testModel": "Exercise",
                "paperName": paper_name,
                "key": key,
            }),
            cookies=self._cookies(),
            callback=self.load_scantron,
            cb_kwargs={"paper_meta": paper_meta, "task": task},
        )

    # ── 第四步：加载答题卡（含加密题目）─────────────────────

    def load_scantron(self, response, paper_meta: dict, task: dict):
        data = response.json()
        paper_log_id = data.get("model", {}).get("paperLogId")

        if not paper_log_id:
            self.logger.warning(
                f"未获取到 paperLogId，paperId={paper_meta['id']}，响应：{data}"
            )
            return

        referer = (
            f"{self.FRONT_URL}/sub/exam/answerKey/answerKey"
            f"?paperLogId={paper_log_id}"
        )
        yield scrapy.Request(
            url=f"{self.BASE_URL}/zuoti/loadScantron.do",
            method="POST",
            headers=self._headers(referer),
            body=urlencode({
                "paperLogId": paper_log_id,
                "subjectPath": task["subject_path"],
            }),
            cookies=self._cookies(),
            callback=self.parse_scantron,
            cb_kwargs={
                "paper_meta": paper_meta,
                "paper_log_id": paper_log_id,
                "task": task,
            },
        )

    # ── 第五步：AES 解密并提取题目 ────────────────────────

    def parse_scantron(self, response, paper_meta: dict, paper_log_id: str, task: dict):
        data = response.json()
        model = data.get("model", {})
        sign_key = model.get("signKey")
        scantron_list = model.get("scantronList")

        if not sign_key or not scantron_list:
            self.logger.warning(
                f"缺少加密字段，paperId={paper_meta['id']}"
            )
            return

        try:
            decrypted_str = aes_ecb_decrypt(scantron_list, sign_key)
            questions_raw = json.loads(decrypted_str)
        except Exception as e:
            self.logger.error(f"解密失败 paperId={paper_meta['id']}: {e}")
            return
        if not isinstance(questions_raw, list):
            self.logger.warning(
                f"解密结果不是预期列表结构，paperId={paper_meta['id']}，类型={type(questions_raw)}"
            )
            yield {
                "_debug": True,
                "paper_id": paper_meta["id"],
                "raw_decrypted": decrypted_str[:500],
            }
            return

        total_count = sum(
            len(group.get("xiaotiList") or [])
            for group in questions_raw
            if isinstance(group, dict)
        )
        self.logger.info(
            f"试卷 [{paper_meta['paperName']}] 共解析到 {total_count} 题"
        )

        buffer_key = self._init_paper_buffer(paper_meta, total_count, task)
        if total_count == 0:
            yield {
                "subject_name": task.get("subject_name"),
                "subject_path": task.get("subject_path"),
                "paper_type": task.get("paper_type"),
                "paper_type_name": task.get("paper_type_name"),
                "paper_id": paper_meta["id"],
                "paper_name": paper_meta["paperName"],
                "paper_year": paper_meta.get("paperYear"),
                "questions": [],
            }
            self.paper_buffers.pop(buffer_key, None)
            return

        for group in questions_raw:
            if not isinstance(group, dict):
                continue

            group_name = group.get("tigan")
            group_desc = group.get("descp")
            questions = group.get("xiaotiList") or []
            self.logger.info(f"{len(questions)}道{group_name}")

            for question in questions:
                shiti = question.get("shitiDTO") or {}
                option_list = shiti.get("questionList") or []
                options = {
                    option.get("key"): option.get("value")
                    for option in option_list
                    if isinstance(option, dict) and option.get("key") is not None
                }
                item = {
                    "question_id": shiti.get("stId"),
                    "question_type": shiti.get("shitiTagName"),
                    "question_type_code": shiti.get("shitiType"),
                    "tigan": shiti.get("tigan"),
                    "options": options,
                    "answer": shiti.get("answer"),
                    "cid": shiti.get("cid"),
                    "cTigan": shiti.get("cTigan"),
                    "score": question.get("score"),
                    "stScore": question.get("stScore"),
                    "priority": shiti.get("priority"),
                    "analysis": None,
                }

                question_id = item["question_id"]
                if not question_id:
                    paper_item = self._append_question(buffer_key, item)
                    if paper_item:
                        yield paper_item
                    continue

                referer = (
                    f"{self.FRONT_URL}/sub/exam/answerKey/answerKey"
                    f"?paperLogId={paper_log_id}"
                )
                yield scrapy.Request(
                    url=f"{self.BASE_URL}/zuoti/analysis.do",
                    method="POST",
                    headers=self._headers(referer),
                    body=urlencode({
                        "paperLogId": paper_log_id,
                        "stId": str(question_id),
                    }),
                    cookies=self._cookies(),
                    callback=self.parse_analysis,
                    cb_kwargs={
                        "paper_meta": paper_meta,
                        "item": item,
                        "buffer_key": buffer_key,
                    },
                )

    def parse_analysis(self, response, paper_meta: dict, item: dict, buffer_key: str):
        data = response.json()
        model = data.get("model", {}) or {}
        item["answer"] = model.get("answer") or item.get("answer")
        item["analysis"] = model.get("analysis")
        paper_item = self._append_question(buffer_key, item)
        if paper_item:
            yield paper_item

