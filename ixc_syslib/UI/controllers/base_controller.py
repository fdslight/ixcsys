#!/usr/bin/env python3
import os, json
import pywind.web.appframework.app_handler as app_handler
import pywind.lib.tpl.Template as template


class controller(app_handler.handler):
    __LANG = None

    def load_lang(self, name: str):
        lang_dir = "%s/web/languages" % os.getenv("IXC_MYAPP_DIR")
        path = "%s/%s.json" % (lang_dir, name,)
        if not os.path.isfile(path):
            path = "%s/default.json" % lang_dir
        if not os.path.isfile(path): return {}

        with open(path, "r",encoding="iso-8859-1") as f:
            s = f.read()
        f.close()

        return json.loads(s)

    def initialize(self):
        self.__LANG=self.load_lang(self.match_lang())

        return self.myinit()

    def myinit(self):
        """重写这个方法
        :return Boolean:True表示继续执行,False表示停止执行
        """
        return True

    def match_lang(self):
        accept_lang = self.request.environ.get("HTTP_ACCEPT_LANGUAGE", None)
        if not accept_lang: return "default"

        listdir = os.listdir("%s/web/languages" % os.getenv("IXC_MYAPP_DIR"))

        accept_lang = accept_lang.replace("-", "_")
        accept_lang = accept_lang.lower()

        _list = []

        for s in listdir:
            s = s.replace(".json", "")
            _list.append(s)

        min_v = 0
        first_lang = None
        for s in _list:
            p = accept_lang.find(s)
            if p < 0: continue
            if first_lang and p > min_v: continue
            min_v = p
            first_lang = s
        if not first_lang: return "default"
        return first_lang

    def is_signed(self):
        pass

    @property
    def user(self):
        return {}

    def LA(self, name: str):
        """语言翻译
        :return:
        """
        return self.__LANG.get(name, name)

    @property
    def staticfile_prefix(self):
        return "/staticfiles/%s" % os.getenv("IXC_MYAPP_NAME")

    @property
    def my_app_name(self):
        return os.getenv("IXC_MYAPP_NAME")

    @property
    def prefix(self):
        """URL前缀
        :return:
        """
        return "/%s" % self.my_app_name

    def set_lang(self, lang: str):
        """设置语言
        :param lang:
        :return:
        """
        self.__LANG = self.load_lang(lang)

    def __get_tpl(self):
        tpl = template.template(user_exts={
            "LA": self.LA,
            "user": self.user,
            "staticfile_prefix": self.staticfile_prefix,
            "app_name": self.my_app_name,
            "prefix": self.prefix
        })
        tpl.set_find_directories([
            "%s/web/templates" % os.getenv("IXC_MYAPP_DIR")
        ])
        return tpl

    def render(self, uri, content_type="text/html;charset=utf-8", **kwargs):
        tpl = self.__get_tpl()
        s = tpl.render(uri, **kwargs)
        self.finish_with_bytes(content_type, s.encode("iso-8859-1"))

    def render_string(self, s: str, content_type="text/html;charset=utf-8", **kwargs):
        tpl = self.__get_tpl()
        s = tpl.render_string(s, **kwargs)
        self.finish_with_bytes(content_type, s.encode("iso-8859-1"))
