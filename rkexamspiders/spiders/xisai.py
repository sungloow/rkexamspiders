import glob
import os
import hashlib
import time
import ddddocr
import requests
import scrapy
import json
import base64
from copy import deepcopy
from urllib.parse import urlencode, unquote
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from scrapy.exceptions import CloseSpider, NotConfigured
from rkexamspiders.output_path import build_output_file_path
import uuid
import logger as _logger_setup  # noqa: F401  触发 setup_logging()，使 xisai 日志写入文件


# ── 工具函数 ──────────────────────────────────────────────

def get_uuid() -> int:
    return uuid.uuid4().int & (10**8 - 1)


def hex_md5(s: str) -> str:
    m = hashlib.md5()
    m.update(s.encode("utf-8"))
    return m.hexdigest()


def get_sscc(sid: str, img_code) -> str:
    return hex_md5(unquote(sid) + str(img_code))


def sort_ascii(obj: dict) -> str:
    keys = sorted(obj.keys())
    return "&".join(f"{k}={obj[k]}" for k in keys)


def get_ascii_key(query_str: str) -> str:
    obj = {}
    for pair in query_str.split("&"):
        name, value = pair.split("=")
        obj[unquote(name)] = unquote(value)
    ascii_str = sort_ascii(obj)
    return ascii_str[::3]


def aes_ecb_decrypt(encrypted_b64: str, key: str) -> str:
    """AES-ECB + PKCS7 解密，与前端 CryptoJS 实现对应"""
    key_bytes = key.encode("utf-8")
    data = base64.b64decode(encrypted_b64)
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
    return decrypted.decode("utf-8")


# ── 常量 ─────────────────────────────────────────────────

_UA_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
)
_UA_LINUX = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class XisaiSpider(scrapy.Spider):
    name = "xisai"
    allowed_domains = ["wangxiao.xisaiwang.com"]

    BASE_URL = "https://wangxiao.xisaiwang.com/stuapi"
    PRODUCT_API_BASE_URL = "https://wangxiao.xisaiwang.com/productapi"
    FRONT_URL = "https://wangxiao.xisaiwang.com/nstu"
    LOGIN_HOST = "https://wangxiao.xisaiwang.com"

    PAPER_TYPE_NAME_MAP = {
        "125": "知识点练习",
        "63": "模拟试卷",
        "62": "章节练习",
        "60": "历年真题",
    }
    PAPER_LIST_TYPES = {"60", "62", "63"}
    KNOWLEDGE_TYPE = "125"

    _COMMON_HEADERS = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": _UA_LINUX,
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://wangxiao.xisaiwang.com",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "clientType": "PC",
        "v": "1.0.1",
        "iar": "iar",
        "market": "s1:101:131:_mweb_v1.0.1",
    }

    def __init__(
        self,
        subject_path=None,
        subject_name=None,
        exam_root_name=None,
        paper_type=None,
        crawl_tasks=None,
        skip_existing=None,
        filter_keywords=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.paper_buffers = {}
        self.subject_path_arg = subject_path
        self.subject_name_arg = subject_name
        self.exam_root_name_arg = exam_root_name
        self.paper_type_arg = paper_type
        self.crawl_tasks_arg = crawl_tasks
        self.skip_existing_arg = skip_existing
        self.filter_keywords_arg = filter_keywords

    # ── 登录流程 ──────────────────────────────────────────

    def __init_session(self) -> requests.Session:
        """访问首页，建立 session 并获取初始 Cookie"""
        session = requests.Session()
        session.get(
            self.LOGIN_HOST,
            headers={
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                    "application/signed-exchange;v=b3;q=0.7"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "max-age=0",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": _UA_WIN,
            },
        )
        return session

    def __fetch_captcha(self, session: requests.Session) -> tuple[str, int]:
        """获取验证码图片，返回 (图片本地路径, img_key)"""
        img_key = get_uuid()
        url = "https://base.xisaiwang.cn/verify/code/r/image.do"
        resp = session.get(
            url,
            params={"key": img_key},
            headers={
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": f"{self.LOGIN_HOST}/",
                "User-Agent": _UA_LINUX,
            },
        )
        captcha_dir = "data/captcha"
        os.makedirs(captcha_dir, exist_ok=True)
        for old in glob.glob(os.path.join(captcha_dir, "*.png")):
            os.remove(old)
        img_path = os.path.join(captcha_dir, f"{img_key}.png")
        with open(img_path, "wb") as f:
            f.write(resp.content)
        return img_path, img_key

    def __do_login(
        self,
        session: requests.Session,
        username: str,
        password: str,
        img_code: str,
        img_key: int,
        sk: str = "imgCode",
    ) -> bool:
        """提交登录表单，返回是否成功"""
        login_url = f"{self.LOGIN_HOST}/ucenter2/user/doLogin.do"
        data = {
            "loginName": username,
            "password": password,
            "imgCode": img_code,
            "imgKey": img_key,
            "sk": sk,
        }
        sid = session.cookies.get_dict().get("_sid_", "")
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "DNT": "1",
            "Origin": self.LOGIN_HOST,
            "Referer": f"{self.LOGIN_HOST}/ucenter2/login.html",
            "User-Agent": _UA_WIN,
            "X-Requested-With": "XMLHttpRequest",
            "sid": sid,
            "sscc": get_sscc(sid, img_code),
            "sscc2": get_ascii_key(urlencode(data)),
        }
        session.get(f"{self.LOGIN_HOST}/ping/pang.do")
        resp = session.post(login_url, headers=headers, data=data, timeout=10)
        try:
            body = resp.json()
            if body.get("resultCode") == "SUCCESS":
                self.logger.info("登录成功")
                return True
            self.logger.error("登录失败：%s", body.get("resultMsg"))
            return False
        except Exception as exc:
            self.logger.error("登录响应解析异常：%s", exc)
            return False

    def login(self, username: str, password: str) -> dict | None:
        """带验证码识别的登录入口，最多重试 5 次，成功返回 Cookie 字典"""
        ocr = ddddocr.DdddOcr(show_ad=False)
        session = self.__init_session()
        img_path, img_key = self.__fetch_captcha(session)

        for attempt in range(1, 6):
            try:
                with open(img_path, "rb") as f:
                    img_code = ocr.classification(f.read())
            except Exception as exc:
                self.logger.warning("OCR 识别异常（第 %d 次）：%s", attempt, exc)
                img_code = None

            if not img_code:
                self.logger.warning("OCR 未识别到验证码，重试（第 %d 次）", attempt)
                time.sleep(1)
                img_path, img_key = self.__fetch_captcha(session)
                continue

            if self.__do_login(session, username, password, img_code, img_key):
                return {"raw_cookies": session.cookies.get_dict()}

            self.logger.info("验证码错误，刷新后重试（第 %d 次）", attempt)
            time.sleep(1)
            img_path, img_key = self.__fetch_captcha(session)

        self.logger.error("账号 %s 登录失败，已达最大重试次数", username)
        return None

    # ── Scrapy 生命周期 ───────────────────────────────────

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)

        from config import get_config
        try:
            cfg = get_config()
        except Exception as exc:
            raise NotConfigured(f"读取 config.toml 失败：{exc}") from exc

        spider._auth_contexts = {}  # username -> auth dict，已登录账号复用
        spider._xisai_accounts = cfg.get("xisai", {})  # subject_name -> {username, password}

        spider.CRAWL_TASKS = spider._load_crawl_tasks(crawler)

        raw_skip = spider.skip_existing_arg
        if raw_skip is None:
            raw_skip = crawler.settings.get("XISAI_SKIP_EXISTING_PAPERS", True)
        spider.SKIP_EXISTING_PAPERS = spider._is_truthy(raw_skip)

        return spider

    def _is_truthy(self, value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def _load_crawl_tasks(self, crawler) -> list:
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
        subject_path = str(raw["subject_path"]).strip() if raw.get("subject_path") else None
        subject_name = str(raw["subject_name"]).strip() if raw.get("subject_name") else None
        exam_root_name = str(raw["exam_root_name"]).strip() if raw.get("exam_root_name") else None
        paper_type = str(raw["paper_type"]).strip() if raw.get("paper_type") else None

        if not subject_path and not subject_name:
            raise NotConfigured(f"任务 {idx} 缺少科目配置：请提供 subject_path 或 subject_name")
        if not paper_type:
            raise NotConfigured(f"任务 {idx} 缺少题型配置：请提供 paper_type")
        if paper_type not in self.PAPER_TYPE_NAME_MAP:
            raise NotConfigured(
                f"任务 {idx} 的 paper_type={paper_type} 暂不支持，仅支持 60/62/63/125"
            )

        # 按 subject_name 从 config.toml [xisai."科目名"] 查找账号密码
        acct = self._xisai_accounts.get(subject_name, {}) if subject_name else {}
        username = acct.get("username")
        password = acct.get("password")
        if not username or not password:
            raise NotConfigured(
                f"任务 {idx}（{subject_name}）在 config.toml [xisai.\"{subject_name}\"] 中未找到账号配置"
            )

        # 任务级过滤关键字，不填则不过滤
        raw_filter = raw.get("filter_keywords")
        filter_keywords = raw_filter if isinstance(raw_filter, list) else []

        return {
            "task_id": f"task_{idx}",
            "subject_path": subject_path,
            "subject_name": subject_name,
            "exam_root_name": exam_root_name,
            "paper_type": paper_type,
            "paper_type_name": self.PAPER_TYPE_NAME_MAP[paper_type],
            "filter_keywords": filter_keywords,
            "username": username,
            "password": password,
        }

    # ── Auth 上下文 ───────────────────────────────────────

    def _ensure_auth_context(self, task: dict) -> dict:
        """按账号缓存登录结果，同一 username 只登录一次"""
        username = task["username"]
        if username not in self._auth_contexts:
            result = self.login(username, task["password"])
            if not result:
                raise CloseSpider(f"账号 {username} 登录失败，无法继续爬取")
            self._auth_contexts[username] = result
            self.logger.info("账号 %s 登录完成，已缓存", username)
        return self._auth_contexts[username]

    def _headers(self, task: dict, referer: str = "") -> dict:
        auth = self._ensure_auth_context(task)
        h = dict(self._COMMON_HEADERS)
        h["cstk"] = auth.get("cstk", "")
        h["cid"] = auth.get("cid", "")
        if referer:
            h["Referer"] = referer
        return h

    def _cookies(self, task: dict) -> dict:
        auth = self._ensure_auth_context(task)
        return auth.get("raw_cookies", {})

    # ── Paper Buffer ──────────────────────────────────────

    def _init_paper_buffer(self, paper_meta: dict, total_count: int, task: dict) -> str:
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

    def _append_question(self, buffer_key: str, item: dict) -> dict | None:
        paper = self.paper_buffers[buffer_key]
        paper["questions"].append(item)
        paper["done"] += 1

        if paper["done"] < paper["expected"]:
            return None

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

    # ── 第一步：翻页获取试卷列表 ──────────────────────────

    def start_requests(self):
        # 提前完成所有不同账号的登录，避免并发时重复登录
        seen_usernames = set()
        for task in self.CRAWL_TASKS:
            if task["username"] not in seen_usernames:
                self._ensure_auth_context(task)
                seen_usernames.add(task["username"])

        pending_tasks = []
        for task in self.CRAWL_TASKS:
            if task.get("subject_path"):
                yield from self._start_task_requests(deepcopy(task))
            else:
                pending_tasks.append(deepcopy(task))

        if pending_tasks:
            yield self._subject_tree_request(pending_tasks)

    def _subject_tree_request(self, pending_tasks):
        # 科目树与账号无关，使用第一个任务的 session 即可
        task = pending_tasks[0]
        referer = f"{self.FRONT_URL}/pages/exam/index/index"
        return scrapy.Request(
            url=f"{self.PRODUCT_API_BASE_URL}/app/v2/classify/examClassifyTree.do",
            method="POST",
            headers=self._headers(task, referer),
            body=urlencode({"vip": "Y"}),
            cookies=self._cookies(task),
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
                "任务 %s 自动解析科目：name=%s, subject_path=%s, paper_type=%s",
                task["task_id"], task["subject_name"], task["subject_path"], task["paper_type"],
            )
            yield from self._start_task_requests(task)

    def _start_task_requests(self, task: dict):
        paper_type = task.get("paper_type")
        if paper_type in self.PAPER_LIST_TYPES:
            yield self._paper_list_request(page=1, task=task)
        elif paper_type == self.KNOWLEDGE_TYPE:
            yield self._knowledge_section_request(task=task)
        else:
            raise CloseSpider(f"任务 {task.get('task_id')} 的题型 {paper_type} 暂不支持")

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
            found = self._find_node_by_name(node.get("children") or [], name)
            if found:
                return found
        return None

    def _paper_list_request(self, page: int, task: dict):
        return scrapy.Request(
            url=f"{self.BASE_URL}/tiku/paper/list.do",
            method="POST",
            headers=self._headers(task, f"{self.FRONT_URL}/"),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "pageNum": str(page),
                "pageSize": "20",
            }),
            cookies=self._cookies(task),
            callback=self.parse_paper_list,
            cb_kwargs={"page": page, "task": task},
        )

    def _knowledge_section_request(self, task: dict):
        referer = f"{self.FRONT_URL}/sub/exam/knowledgeNode/knowledgeNode"
        return scrapy.Request(
            url=f"{self.BASE_URL}/tiku/section/userSectionlist.do",
            method="POST",
            headers=self._headers(task, referer),
            body=urlencode({"subjectPath": task["subject_path"]}),
            cookies=self._cookies(task),
            callback=self.parse_knowledge_sections,
            cb_kwargs={"task": task},
        )

    def parse_paper_list(self, response, page: int, task: dict):
        data = response.json()
        papers = data.get("model", {}).get("datas", [])
        if not papers:
            self.logger.info("任务 %s 第 %s 页无数据，列表抓取完毕", task["task_id"], page)
            return

        self.logger.info(
            "任务 %s 第 %s 页获取到 %s 套试卷（科目=%s, 题型=%s）",
            task["task_id"], page, len(papers),
            task.get("subject_name") or task.get("subject_path"),
            task["paper_type_name"],
        )

        filter_keywords = task.get("filter_keywords") or []
        if filter_keywords:
            papers = [
                p for p in papers
                if any(kw in (p.get("paperName") or "") for kw in filter_keywords)
            ]
            self.logger.info("任务 %s 关键字过滤后剩余 %s 套试卷", task["task_id"], len(papers))

        for p in papers:
            if self.SKIP_EXISTING_PAPERS:
                file_path = build_output_file_path(
                    subject_name=task.get("subject_name"),
                    subject_path=task.get("subject_path"),
                    paper_type_name=task["paper_type_name"],
                    paper_type=task["paper_type"],
                    paper_name=p.get("paperName"),
                    paper_id=p.get("id"),
                )
                if file_path.exists():
                    self.logger.info("任务 %s 跳过已存在试卷：%s", task["task_id"], file_path)
                    continue
            yield self._check_zuoti_request(p, task)

        yield self._paper_list_request(page=page + 1, task=task)

    def parse_knowledge_sections(self, response, task: dict):
        data = response.json()
        sections = (data.get("model") or {}).get("sectionTreeResponseList") or []
        if not isinstance(sections, list):
            self.logger.warning("任务 %s 知识点章节响应结构异常", task["task_id"])
            return

        self.logger.info(
            "任务 %s 获取到 %s 个知识点大节（科目=%s）",
            task["task_id"], len(sections),
            task.get("subject_name") or task.get("subject_path"),
        )

        for section in sections:
            if not isinstance(section, dict):
                continue
            # 只处理顶级节点（parentId=0），用父节点 id 请求时会包含所有子节点题目
            if section.get("parentId") != 0:
                continue

            section_id = section.get("id")
            section_name = section.get("name") or f"section_{section_id}"
            if self.SKIP_EXISTING_PAPERS:
                file_path = build_output_file_path(
                    subject_name=task.get("subject_name"),
                    subject_path=task.get("subject_path"),
                    paper_type_name=task["paper_type_name"],
                    paper_type=task["paper_type"],
                    paper_name=section_name,
                    paper_id=section_id,
                )
                if file_path.exists():
                    self.logger.info("任务 %s 跳过已存在知识点大节：%s", task["task_id"], file_path)
                    continue

            section_meta = {"id": section_id, "paperName": section_name}
            yield self._check_zuoti_request(section_meta, task)

    # ── 第二步：检查权限 ──────────────────────────────────

    def _check_zuoti_request(self, paper_meta: dict, task: dict):
        paper_id = str(paper_meta["id"])
        paper_name = paper_meta["paperName"]
        referer = (
            f"{self.FRONT_URL}/sub/exam/maths/dailyPracticeTestPaper/"
            f"dailyPracticeTestPaper?paperId={paper_id}&paperName={paper_name}"
        )
        return scrapy.Request(
            url=f"{self.BASE_URL}/user/checkZuoti.do",
            method="POST",
            headers=self._headers(task, referer),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "dataId": paper_id,
            }),
            cookies=self._cookies(task),
            callback=self.start_exam,
            cb_kwargs={"paper_meta": paper_meta, "task": task},
        )

    # ── 第三步：开启考试会话，获取 paperLogId ─────────────

    def start_exam(self, response, paper_meta: dict, task: dict):
        body = response.json()
        if body.get("resultCode") != "SUCCESS":
            self.logger.warning(
                "检查权限失败，paperId=%s，响应：%s", paper_meta["id"], response.text
            )
            return

        key = body.get("model", {}).get("key")
        if not key:
            self.logger.warning("未获取到 key，paperId=%s", paper_meta["id"])
            return

        paper_id = str(paper_meta["id"])
        paper_name = paper_meta["paperName"]
        referer = (
            f"{self.FRONT_URL}/sub/exam/maths/dailyPracticeTestPaper/"
            f"dailyPracticeTestPaper?paperId={paper_id}&paperName={paper_name}"
        )
        yield scrapy.Request(
            url=f"{self.BASE_URL}/zuoti/startExam.do",
            method="POST",
            headers=self._headers(task, referer),
            body=urlencode({
                "subjectPath": task["subject_path"],
                "paperType": task["paper_type"],
                "dataId": paper_id,
                "testModel": "Exercise",
                "paperName": paper_name,
                "key": key,
            }),
            cookies=self._cookies(task),
            callback=self.load_scantron,
            cb_kwargs={"paper_meta": paper_meta, "task": task},
        )

    # ── 第四步：加载答题卡（含加密题目）─────────────────────

    def load_scantron(self, response, paper_meta: dict, task: dict):
        paper_log_id = response.json().get("model", {}).get("paperLogId")
        if not paper_log_id:
            self.logger.warning(
                "未获取到 paperLogId，paperId=%s，响应：%s", paper_meta["id"], response.text
            )
            return

        referer = f"{self.FRONT_URL}/sub/exam/answerKey/answerKey?paperLogId={paper_log_id}"
        yield scrapy.Request(
            url=f"{self.BASE_URL}/zuoti/loadScantron.do",
            method="POST",
            headers=self._headers(task, referer),
            body=urlencode({
                "paperLogId": paper_log_id,
                "subjectPath": task["subject_path"],
            }),
            cookies=self._cookies(task),
            callback=self.parse_scantron,
            cb_kwargs={
                "paper_meta": paper_meta,
                "paper_log_id": paper_log_id,
                "task": task,
            },
        )

    # ── 第五步：AES 解密并提取题目 ────────────────────────

    def parse_scantron(self, response, paper_meta: dict, paper_log_id: str, task: dict):
        model = response.json().get("model", {})
        sign_key = model.get("signKey")
        scantron_list = model.get("scantronList")

        if not sign_key or not scantron_list:
            self.logger.warning("缺少加密字段，paperId=%s", paper_meta["id"])
            return

        try:
            questions_raw = json.loads(aes_ecb_decrypt(scantron_list, sign_key))
        except Exception as exc:
            self.logger.error("解密失败 paperId=%s: %s", paper_meta["id"], exc)
            return

        if not isinstance(questions_raw, list):
            self.logger.warning(
                "解密结果不是预期列表结构，paperId=%s，类型=%s",
                paper_meta["id"], type(questions_raw),
            )
            return

        total_count = sum(
            len(group.get("xiaotiList") or [])
            for group in questions_raw
            if isinstance(group, dict)
        )
        self.logger.info("试卷 [%s] 共解析到 %s 题", paper_meta["paperName"], total_count)

        buffer_key = self._init_paper_buffer(paper_meta, total_count, task)
        if total_count == 0:
            yield self._empty_paper_item(paper_meta, task)
            self.paper_buffers.pop(buffer_key, None)
            return

        for group in questions_raw:
            if not isinstance(group, dict):
                continue
            group_name = group.get("tigan")
            questions = group.get("xiaotiList") or []
            self.logger.info("%s 道 %s", len(questions), group_name)

            for question in questions:
                shiti = question.get("shitiDTO") or {}
                options = {
                    opt.get("key"): opt.get("value")
                    for opt in (shiti.get("questionList") or [])
                    if isinstance(opt, dict) and opt.get("key") is not None
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

                if not item["question_id"]:
                    paper_item = self._append_question(buffer_key, item)
                    if paper_item:
                        yield paper_item
                    continue

                referer = f"{self.FRONT_URL}/sub/exam/answerKey/answerKey?paperLogId={paper_log_id}"
                yield scrapy.Request(
                    url=f"{self.BASE_URL}/zuoti/analysis.do",
                    method="POST",
                    headers=self._headers(task, referer),
                    body=urlencode({
                        "paperLogId": paper_log_id,
                        "stId": str(item["question_id"]),
                    }),
                    cookies=self._cookies(task),
                    callback=self.parse_analysis,
                    cb_kwargs={
                        "paper_meta": paper_meta,
                        "item": item,
                        "buffer_key": buffer_key,
                    },
                )

    def parse_analysis(self, response, paper_meta: dict, item: dict, buffer_key: str):
        model = (response.json().get("model") or {})
        item["answer"] = model.get("answer") or item.get("answer")
        item["analysis"] = model.get("analysis")
        paper_item = self._append_question(buffer_key, item)
        if paper_item:
            yield paper_item

    # ── 内部辅助 ──────────────────────────────────────────

    def _empty_paper_item(self, paper_meta: dict, task: dict) -> dict:
        return {
            "subject_name": task.get("subject_name"),
            "subject_path": task.get("subject_path"),
            "paper_type": task.get("paper_type"),
            "paper_type_name": task.get("paper_type_name"),
            "paper_id": paper_meta["id"],
            "paper_name": paper_meta["paperName"],
            "paper_year": paper_meta.get("paperYear"),
            "questions": [],
        }
