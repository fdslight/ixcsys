#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        syslog = RPC.fn_call("init", "/syslog", "syslog_alert_get")
        content = ""
        syslog.reverse()

        for _dict in syslog:
            message = _dict["message"]
            # message = message.replace("<", "&lt;")
            # message = message.replace(">", "&gt;")
            s = _dict["time"] + "\t" + _dict["application"] + "\t" + message + "\r\n"
            content += s

        return True, "syslog-important.html", {"syslog": content}
