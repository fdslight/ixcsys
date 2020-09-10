#!/usr/bin/env python3
import pywind.web.appframework.app_handler as app_handler
import pywind.lib.tpl as tpl


class controller(app_handler.handler):
    def initialize(self):
        return self.myinit()

    def myinit(self):
        """重写这个方法
        :return Boolean:True表示继续执行,False表示停止执行
        """
        return True

    def is_signed(self):
        pass

    @property
    def user(self):
        return {}

    def LA(self, name: str):
        """语言翻译包
        :return:
        """
        return {}

    def set_lang(self, lang: str):
        """设置语言
        :param lang:
        :return:
        """
        pass

    def __get_tpl(self):
        pass

    def render(self, uri, **kwargs):
        pass

    def render_string(self, uri, **kwargs):
        pass
