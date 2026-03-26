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
    scantronList="2ovkABqgvKyW35LRGsvMwB956CZIil7XUtDs/TYdJKi8HoEtqICB5rW1ES8u/xYYzxUYL1NjchFNo/ao4rNjlOdQqCuuj6g7qWaha4XiX1EJFHz7wbrBsFkqiIFBmOBveK+Ib8IhxEgF8nEx0cr1gh+RC2n9Jb8kYdEd59h+oYG7FdK5278ealBqKWoSBOF3PwKQswJbtGLWbm0ttQwOfHoCtU4T/ZOGwYAMroTqzX7axuAWahPD7eY+WidmwlUdRk8uVLCIeEdoGlT73mNmZ45u2DSOVG79mhh44xegsdY7uqR0imLCloiKVxf0GNeAVW3l/sig+l0zbzzEdpoqg/BGOFVVJD2f/TvJeEAg7PoYfthI+7A3UOqhiyv3KT8T3/gw3wALGY7VZVV2MhSIrI2e584qlOiySm3dQ6YjpfOOvNkGUGn2QnkLY1icZlNbJDrr+uFm5V3Ieu6BKop5ngGax0xNM4ZMVBWPAzrNO7ymSaSHf7cocAZe12VFnw6r4N5I26RaA5Qh/OL271Eqz97w2gesp4xaWQHsjEraqUPLTXO/erXdexOvldBumIdYxcyrZG+zinwgycYnJJFfj0Fu+0nb41BRoAr6Gq97qyu7EEa80Ck7KgKuiADSoTG2ZU7ftgbmI0FEDRPdHQC4jGzSKuL2GvgHqG8FDHwDEYVMGLiMfjNKqlkqpnuvcAp5riPc2OfNs8kzxRd2XQEgNZoZVwrUsDB9ZRsb5FHIzJg5hoRqUc4qemgUn4JYyjw5l8mRRRf001fuP9VI4u2/8hvvaS7yurgaHl+B4Ivgp/rys4UYwD1UtEl0D7nNzxUNfpAABzad0TmoToHcGaYaICRWRnbPMqgR+keMoGcfoahfmdBG6Cr9QlX6V7Il1AYbC9c4FoLG4pwd6T580CcgAu1YqM76P83NAtF/D1HTK0iK77qRnlw+2TTqhOJ9jVi5kEi38BEGAE2CR11dP1MIfH6QAAc2ndE5qE6B3BmmGiAtE3eUhd8XmaHgcWlrvXlV3ctN7MpgYftARKFhLHVQuiQOo85c7wIyqF6n+sz8VrVAThNwWKjZPU6C90tMt/D8i6vj3n7MaQhznxniGkBgB5KYR4WaMjcpcVVSb4nzaCtg6XNertNNOl+y8qq/grFo/Ec4wX8f4gdPyuXk21Z2nekiJqTReJXpRkCUuWPl3XsBIVWyENaFKP6Ljn0D4C1nRwPDT2f9hHPOJ8C/MgTkVw=="
    signKey="b95kR8C8Sc7ECahI"
    print(aes_ecb_decrypt(scantronList, signKey))