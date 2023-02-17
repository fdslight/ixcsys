#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.ixc_process as process


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        processes = process.get_process()
        results = []

        for ps in processes:
            command = ps["COMMAND"]
            p = command.find("ixc_syscore/")
            if p < 0: continue
            p += len("ixc_syscore/")
            s = command[p:]
            p = s.find("/")
            if p < 0: continue
            program_name = s[0:p]
            ps["NAME"] = program_name
            ps["MEM_MB"] = str(float(int(ps["VSZ"]) / 1000))
            results.append(ps)

        return True, "system-process.html", {"processes": results}
