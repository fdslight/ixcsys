#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        errlog = RPC.fn_call("init", "/syslog", "errlog_get")
        errlog = errlog.replace("<", "&lt;")
        errlog = errlog.replace(">", "&gt;")

        syslog = RPC.fn_call("init", "/syslog", "syslog_get")

        for _dict in syslog:
            message = _dict["message"]
            message = message.replace("<", "&lt;")
            message = message.replace(">", "&gt;")
            _dict["message"] = message

        # 按时间由大到小排序
        syslog.reverse()

        return True, "syslog.html", {"error": errlog, "syslog": syslog}
