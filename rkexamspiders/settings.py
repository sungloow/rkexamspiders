# Scrapy settings for rkexamspiders project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "rkexamspiders"

SPIDER_MODULES = ["rkexamspiders.spiders"]
NEWSPIDER_MODULE = "rkexamspiders.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "rkexamspiders (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "rkexamspiders.middlewares.RkexamspidersSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "rkexamspiders.middlewares.RkexamspidersDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "rkexamspiders.pipelines.JsonWriterPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False
CONCURRENT_REQUESTS = 32                    # 全局并发提高
CONCURRENT_REQUESTS_PER_DOMAIN = 16         # 单域名并发翻倍
DOWNLOAD_DELAY = 0.2                        # 延迟从1秒降到0.2秒

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# Xisai spider custom settings
# SUBJECT_PATH: 科目classifyId（示例：系统架构设计师 = 1:101:131:）
# 软考科目 classifyId 对照：
# 系统分析师=1:101:130:
# 信息系统项目管理师=1:101:132:
# 网络规划设计师=1:101:129:
# 系统架构设计师=1:101:131:
# 系统规划与管理师=1:101:133:
# 系统集成项目管理工程师=1:101:134:
# 软件设计师=1:101:136:
# 网络工程师=1:101:138:
# 信息系统监理师=1:101:140:
# 信息系统管理工程师=1:101:139:
# 电子商务设计师=1:101:141:
# 软件评测师=1:101:135:
# 信息安全工程师=1:101:142:
# 数据库系统工程师=1:101:137:
# 嵌入式系统设计师=1:101:143:
# 程序员=1:101:146:
# 网络管理员=1:101:144:
# 信息处理技术员=1:101:145:
# 信息系统运行管理员=1:101:147:
# 多媒体应用设计师=1:101:111799:
# XISAI_SUBJECT_PATH = "1:101:131:"

# 如果不直接配置 XISAI_SUBJECT_PATH，可配置科目名称自动解析。
# 例如：XISAI_EXAM_ROOT_NAME = "软考"、XISAI_SUBJECT_NAME = "系统架构设计师"
# XISAI_EXAM_ROOT_NAME 可选，不填则在整棵树中按名称查找。
# XISAI_SUBJECT_NAME = "系统架构设计师"
# XISAI_EXAM_ROOT_NAME = "软考"

# PAPER_TYPE: 试卷类型
# 仅支持：125=知识点练习, 63=模拟试卷, 62=章节练习, 60=历年真题
# 其中 60/62/63 使用同一试卷列表与解析流程；125 使用知识点章节接口。
# XISAI_PAPER_TYPE = "60"

# 多任务配置（推荐）：一次启动抓多个科目和不同题型。
# 每项必须包含：paper_type + (subject_path 或 subject_name)
# 账号密码按 subject_name 自动从 config.toml [xisai."科目名"] 读取。
# filter_keywords 为任务级过滤，仅对 paper_type=60（历年真题）生效，不填则不过滤。
XISAI_CRAWL_TASKS = [
    # {
    #     "subject_name": "软件设计师",
    #     "exam_root_name": "软考",
    #     "paper_type": "60",
    #     "filter_keywords": ["2026", "2025", "2024"],
    # },
    # {
    #     "subject_name": "软件设计师",
    #     "exam_root_name": "软考",
    #     "paper_type": "62",
    # },
    # {
    #     "subject_name": "软件评测师",
    #     "exam_root_name": "软考",
    #     "paper_type": "60",
    #     "filter_keywords": ["2026", "2025", "2024"],
    # },
    # {
    #     "subject_name": "信息系统项目管理师",
    #     "exam_root_name": "软考",
    #     "paper_type": "203817",
    #     "filter_keywords": ["二期"],
    # },
    # {
    #     "subject_name": "系统架构设计师",
    #     "exam_root_name": "软考",
    #     "paper_type": "203817",
    #     "filter_keywords": ["二期"],
    # },
    # {
    #     "subject_name": "系统分析师",
    #     "exam_root_name": "软考",
    #     "paper_type": "203817",
    #     "filter_keywords": ["二期"],
    # },
    # {
    #     "subject_name": "软件设计师",
    #     "exam_root_name": "软考",
    #     "paper_type": "203817",
    #     "filter_keywords": ["二期"],
    # },
    {
        "subject_name": "软件评测师",
        "exam_root_name": "软考",
        "paper_type": "203817",
    },
]

# 是否跳过已抓取的试卷（按 output/科目/题型/试卷名.json 是否存在判断）
XISAI_SKIP_EXISTING_PAPERS = True

