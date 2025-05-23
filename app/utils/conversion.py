from pypinyin import lazy_pinyin
from translate import Translator


def convert_to_pinyin(chinese_text: str) -> str:
    """将中文字符串转换为拼音"""
    if not chinese_text:
        return ""
    pinyin_list = lazy_pinyin(chinese_text)
    return " ".join(pinyin_list).capitalize()  # 首字母大写处理

def convert_miles_to_km(miles: float) -> float:
    """将英里转换为公里"""
    return round(miles * 1.60934, 2)

def translate_text(text: str) -> str:
    """将文本翻译为英文"""
    translator = Translator(from_lang='zh', to_lang='en')
    translation = translator.translate(text)
    return translation