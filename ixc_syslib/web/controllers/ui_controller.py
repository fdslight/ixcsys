#!/usr/bin/env python3
"""session文件格式,文件名为session.json
"""

import os, json, time, random, sys, importlib
import pywind.web.appframework.app_handler as app_handler
import pywind.lib.tpl.Template as template


class controller(app_handler.handler):
    __LANG = None
    __user = None
    __auto_auth = None
    __session_dir = None
    # 保存用户会话信息
    __users_session_info_file = None
    __session_timeout = None

    def load_lang(self, name: str):
        lang_dir = "%s/web/languages" % os.getenv("IXC_MYAPP_DIR")
        path = "%s/%s.json" % (lang_dir, name,)
        if not os.path.isfile(path):
            path = "%s/default.json" % lang_dir
        if not os.path.isfile(path): return {}

        with open(path, "r", encoding="iso-8859-1") as f:
            s = f.read()
        f.close()

        return json.loads(s)

    def set_auto_auth(self, b: bool):
        """是否开启自动认证,需要在myinit函数中设置才能生效
        """
        self.__auto_auth = b

    def __update_users_session_info(self, users_session: dict):
        with open(self.__users_session_info_file, "w") as f:
            f.write(json.dumps(users_session))
        f.close()

    def __get_users_session_info(self):
        if not os.path.isfile(self.__users_session_info_file): return {}
        with open(self.__users_session_info_file, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def __drop_expire_sessions(self):
        """丢弃过期的会话
        """
        files = os.listdir(self.__session_dir)
        now_t = time.time()

        del_files = []

        for file in files:
            fpath = "%s/%s" % (self.__session_dir, file,)
            if fpath == self.__users_session_info_file: continue
            with open(fpath, "r") as f:
                s = f.read()
            f.close()

            o = json.loads(s)
            last_time = float(o["last_time"])
            if now_t - last_time > self.__session_timeout: del_files.append(fpath)

        users_session = self.__get_users_session_info()

        for fpath in del_files:
            with open(fpath, "r") as f:
                s = f.read()
            f.close()
            o = json.loads(s)
            username = o["username"]
            if username in users_session: del users_session[username]
            os.remove(fpath)

    def __init_session(self):
        self.__session_timeout = 900
        self.__session_dir = "/tmp/ixcsys_sessions"
        self.__users_session_info_file = "%s/users_session_info.json" % self.__session_dir

        if not os.path.isdir(self.__session_dir): os.mkdir(self.__session_dir)
        self.__drop_expire_sessions()

    def __get_session_id(self):
        sset = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
        size = len(sset)
        i_max = size - 1
        seq = []

        for i in range(16):
            n = random.randint(0, i_max)
            seq.append(sset[n])

        return "".join(seq)

    def initialize(self):
        self.__user = {}
        self.__LANG = self.load_lang(self.match_lang())
        self.__auto_auth = True
        self.__init_session()

        rs = self.myinit()
        if not rs: return False

        # 开启自动认证并且未登录那么重定向到首页
        if self.__auto_auth and not self.is_signed() and self.request.environ["PATH_INFO"] != "/":
            self.redirect("/")
            return False

        return True

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
        """检查用户是否已经登录
        """
        user_id = self.request.cookie.get("USER_ID", None)
        if not user_id: return False

        fpath = "%s/%s" % (self.__session_dir, user_id,)
        if not os.path.isfile(fpath): return False

        with open(fpath, "r") as f:
            s = f.read()
        f.close()

        users_session = self.__get_users_session_info()
        o = json.loads(s)
        username = o["username"]
        self.__user = users_session[username]

        return True

    def signin(self, username: str):
        while 1:
            session_id = self.__get_session_id()
            fpath = "%s/%s" % (self.__session_dir, session_id,)
            if os.path.isfile(fpath): continue
            break

        users_session = self.__get_users_session_info()
        users_session[username] = {
            "last_ip": self.request.environ["REMOTE_ADDR"]
        }
        self.__update_users_session_info(users_session)
        with open(fpath, "w") as f:
            f.write(json.dumps({"last_time": time.time(), "username": username}))
        f.close()
        self.set_cookie("USER_ID", session_id, expires=self.__session_timeout)

    @property
    def user(self):
        return self.__user

    def LA(self, name: str):
        """语言翻译
        :return:
        """
        return self.__LANG.get(name, name)

    @property
    def staticfile_prefix(self):
        return "/%s/staticfiles" % os.getenv("IXC_MYAPP_NAME")

    @property
    def my_app_name(self):
        return os.getenv("IXC_MYAPP_NAME")

    @property
    def my_app_dir(self):
        return os.getenv("IXC_MYAPP_DIR")

    @property
    def app_dir(self):
        return os.getenv("IXC_APP_DIR")

    @property
    def url_prefix(self):
        """URL前缀
        :return:
        """
        return "/%s" % self.my_app_name

    @property
    def my_config_dir(self):
        """获取配置目录
        """
        return "%s/%s" % (os.getenv("IXC_CONF_DIR"), self.my_app_name,)

    @property
    def my_app_relative_dir(self):
        """相对应用目录
        """
        return os.getenv("IXC_MYAPP_RELATIVE_DIR")

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
            "url_prefix": self.url_prefix,
            "widget": self.widget
        })
        tpl.set_find_directories([
            "%s/web/templates" % os.getenv("IXC_MYAPP_DIR")
        ])
        return tpl

    def render(self, uri, content_type="text/html;charset=utf-8", **kwargs):
        s = self.get_tpl_render_result(uri, **kwargs)
        self.finish_with_bytes(content_type, s.encode("iso-8859-1"))

    def get_tpl_render_result(self, uri: str, **kwargs):
        """获取模板渲染结果
        """
        tpl = self.__get_tpl()
        s = tpl.render(uri, **kwargs)
        return s

    def get_str_render_result(self, s: str, **kwargs):
        """获取字符串渲染结果
        """
        tpl = self.__get_tpl()
        s = tpl.render_string(s, **kwargs)
        return s

    def render_string(self, s: str, content_type="text/html;charset=utf-8", **kwargs):
        s = self.get_str_render_result(s, **kwargs)
        self.finish_with_bytes(content_type, s.encode("iso-8859-1"))

    def widget(self, name: str, *args, **kwargs):
        """
        """
        if self.my_app_relative_dir == "/":
            s = self.my_app_relative_dir[0:-1]
        else:
            s = self.my_app_relative_dir
        s = "%s/web/ui_widgets/%s" % (s, name,)
        module_path = s.replace("/", ".")

        if module_path in sys.modules:
            module = sys.modules[module_path]
            importlib.reload(module)
        else:
            try:
                importlib.import_module(module_path)
            except ImportError:
                return ""
            module = sys.modules[module_path]
        cls = module.widget(self.request, self)
        is_tpl, tpl, results = cls.handle(*args, **kwargs)
        if is_tpl:
            render_result = self.get_tpl_render_result(tpl, **results)
        else:
            render_result = self.get_str_render_result(tpl, **results)
        return render_result
