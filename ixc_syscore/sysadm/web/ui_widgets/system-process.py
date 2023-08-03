#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.ixc_process as process


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        processes = process.get_process()
        results = []
        tot_mem = 0.0

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
            mem_mb = float(int(ps["VSZ"]) / 1000)
            ps["MEM_MB"] = str(mem_mb)
            tot_mem += mem_mb
            results.append(ps)

        cpu_usage_list = []
        cpu_usage = process.get_cpu_usage()
        for cpu_idx, usage in cpu_usage:
            v = usage * 100
            v = round(v, 2)
            cpu_usage_list.append((cpu_idx, v))

        return True, "system-process.html", {"processes": results, "tot_used_mem": str(round(tot_mem, 2)),
                                             "cpu_usage": cpu_usage_list}
