#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DHCP"):
            configs = RPC.fn_call("DHCP", "/dhcp_server", "get_configs")
            b = bool(int(configs["public"]["enable"]))
            configs["public"]["enable"] = bool(int(b))

            pub_cfg = configs["public"]

            if "boot_file" not in pub_cfg:
                pub_cfg["boot_file"] = "ipxe.efi"
            if "x64_efi_boot_file" not in pub_cfg:
                pub_cfg["x64_efi_boot_file"] = "ipxe.efi"
            if "x86_pc_boot_file" not in pub_cfg:
                pub_cfg["x86_pc_boot_file"] = "undionly.kpxe"

            uri = "dhcp-server.html"
            rs = configs
        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DHCP"}

        return True, uri, rs
