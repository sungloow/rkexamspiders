import json
from pathlib import Path
from itemadapter import ItemAdapter
from rkexamspiders.output_path import build_output_file_path


class JsonWriterPipeline:
    def open_spider(self, spider):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        file_path = build_output_file_path(
            output_dir=self.output_dir,
            subject_name=adapter.get("subject_name") or getattr(spider, "SUBJECT_NAME", None),
            subject_path=adapter.get("subject_path") or getattr(spider, "SUBJECT_PATH", None),
            paper_type_name=adapter.get("paper_type_name") or getattr(spider, "PAPER_TYPE_NAME", None),
            paper_type=adapter.get("paper_type") or getattr(spider, "PAPER_TYPE", None),
            paper_name=adapter.get("paper_name"),
            paper_id=adapter.get("paper_id"),
        )

        target_dir = file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(adapter.asdict(), file, ensure_ascii=False, indent=2)
        return item
