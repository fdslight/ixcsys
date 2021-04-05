#!/usr/bin/env/python3
"""UI部分组件类
"""


class widget(object):
    __request = None
    __request_handler = None

    def __init__(self, request_object, request_hanlder):
        self.__request = request_object
        self.__request_handler = request_hanlder

    @property
    def request_environ(self):
        return self.__request.environ

    @property
    def request_handler(self):
        return self.__request_handler

    @property
    def app_name(self):
        return self.__request_handler.my_app_name

    @property
    def my_conf_dir(self):
        return self.__request_handler.my_config_dir

    @property
    def my_app_dir(self):
        return self.__request_handler.my_app_dir

    @property
    def my_app_relative_dir(self):
        """应用相对目录
        """
        return self.__request_handler.my_app_relative_dir

    @property
    def app_dir(self):
        """应用目录
        """
        return self.__request_handler.app_dir

    @property
    def sys_dir(self):
        return self.__request_handler.sys_dir

    def LA(self, s: str):
        """语言翻译
        """
        return self.__request_handler.LA(s)

    def get_argument(self, name: str, default=None, is_qs=True, is_seq=False):
        """获取请求参数
        """
        return self.__request.get_argument(name, default=default, is_qs=is_qs, is_seq=is_seq)

    def handle(self, *args, **kwargs):
        """重写这个方法
        :return (is_render_tpl,tpl,kwargs),如果is_render_tpl为True,tpl的值为模板URI,否则为待渲染的字符串,kwargs表示模板语法的变量值
        """
        return False, "", {}
