#!/usr/bin/env python3

import pywind.web.appframework.app_handler as app_handler


class controller(app_handler.handler):
    def handle(self):
        self.finish_with_json({"hello": "x"})
