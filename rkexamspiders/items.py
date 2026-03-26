import scrapy


class QuestionItem(scrapy.Item):
    paper_id = scrapy.Field()
    paper_name = scrapy.Field()
    paper_year = scrapy.Field()
    questions = scrapy.Field()
