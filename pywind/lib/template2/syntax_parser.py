#!/usr/bin/env python3
# 词法解析器,语法类似于DJANGO模板引擎

### 定义语句类型
# 普通文本
TEXT_TYPE_TEXT = 0
# 换行符
TEXT_TYPE_CRLF = 1
# 变量的左边边界
TEXT_TYPE_VAR_LEFT = 2
# 变量语法块
TEXT_TYPE_VAR_BLOCK = 3
# 变量的右边边界
TEXT_TYPE_VAR_RIGHT = 4
# 逻辑语句的左边边界
TEXT_TYPE_LOGIC_LEFT = 5
# 逻辑语句语法块
TEXT_TYPE_LOGIC_BLOCK = 6
# 逻辑语句的右边边界
TEXT_TYPE_LOGIC_RIGHT = 7


class SyntaxErr(Exception):
    pass


class parser(object):
    """词法解析器
    """

    def __init__(self):
        pass

    def __scan_text_for_syntax_postion(self, s: str):
        """首先对文本进行扫描,获取语法相关位置信息
        """
        line_no = 1
        results = []
        b = 0
        while 1:
            try:
                if s[b] == "\n":
                    results.append((line_no, TEXT_TYPE_CRLF, b))
                    b = b + 1
                    line_no += 1
                    continue
                ''''''
            except IndexError:
                break
            border = s[b:b + 2]

            if border == "": break
            text_type = 0
            if border == "{{":
                flags = True
                text_type = TEXT_TYPE_VAR_LEFT
            elif border == "}}":
                flags = True
                text_type = TEXT_TYPE_VAR_RIGHT
            elif border == "{%":
                flags = True
                text_type = TEXT_TYPE_LOGIC_LEFT
            elif border == "%}":
                flags = True
                text_type = TEXT_TYPE_LOGIC_RIGHT
            else:
                flags = False

            if flags: results.append((line_no, text_type, b))
            b += 1
        return results

    def __split_string_from_pos_info(self, s: str, pos_results: list):
        """通过提供的关键字信息分割字符串
        """
        results = []
        pos = 0
        last_text_type = TEXT_TYPE_TEXT
        for line_no, text_type, start_pos in pos_results:
            b = pos
            if text_type == TEXT_TYPE_CRLF:
                pos = start_pos + 1
                e = pos
            else:
                pos = start_pos + 2
                e = start_pos

            if last_text_type == TEXT_TYPE_VAR_LEFT and text_type == TEXT_TYPE_VAR_RIGHT:
                _type = TEXT_TYPE_VAR_BLOCK
            elif last_text_type == TEXT_TYPE_LOGIC_LEFT and text_type == TEXT_TYPE_LOGIC_RIGHT:
                _type = TEXT_TYPE_LOGIC_BLOCK
            else:
                _type = TEXT_TYPE_TEXT

            last_text_type = text_type
            results.append((line_no, _type, s[b:e]))

        return results

    def parse_from_string(self, s: str):
        kw_pos_results = self.__scan_text_for_syntax_postion(s)
        text_split_results = self.__split_string_from_pos_info(s, kw_pos_results)
        print(text_split_results)

    def parse_from_file(self, fpath: str):
        with open(fpath, "r") as f: s = f.read()
        f.close()
        self.parse_from_string(s)


cls = parser()
cls.parse_from_file("test.html")
