# from scrapy.crawler import CrawlerProcess
# from scrapy.utils.project import get_project_settings


# def main():
#     settings = get_project_settings()
#     process = CrawlerProcess(settings)
#     process.crawl("xisai")
#     process.start()


# if __name__ == "__main__":
#     main()

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def aes_ecb_decrypt(encrypted_b64: str, key: str) -> str:
    """AES-ECB + PKCS7 解密，与前端 CryptoJS 实现完全对应"""
    key_bytes = key.encode("utf-8")
    data = base64.b64decode(encrypted_b64)
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(data), AES.block_size)
    return decrypted.decode("utf-8")

if __name__ == "__main__":
    pass