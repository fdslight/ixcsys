#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.ixc_process as process


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        processes = process.get_process()
        results = []
        for p in processes:
            command = p["COMMAND"]
            p = command.find("ixc_syscore/")
            if p < 0: continue
            p += 1
            s = command[p:]
            p = s.find("/")
            if p < 0: continue
            program_name = s[0:p]
            p["NAME"] = program_name
            results.append(p)

        return True, "system-process.html", {"processes":results}
