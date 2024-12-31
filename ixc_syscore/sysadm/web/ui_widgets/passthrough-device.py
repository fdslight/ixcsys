#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        router_configs = RPC.fn_call("router", "/config", "router_config_get")
        passthrough_devices = router_configs["passthrough"]
        devices = []

        for hwaddr, enable_with_comment in passthrough_devices.items():
            p = enable_with_comment.find("|")
            if p != 1:
                is_passdev = False
                comment = enable_with_comment
            else:
                try:
                    is_passdev = bool(int(enable_with_comment[0:p]))
                    p += 1
                    comment = enable_with_comment[p:]
                except ValueError:
                    comment = enable_with_comment
                    is_passdev = False
                ''''''
            if is_passdev:
                s = '是'
            else:
                s = '否'
            devices.append(
                (hwaddr, s, comment)
            )

        uri = "passthrough-device.html"
        print(devices)
        return True, uri, {"devices": devices}
