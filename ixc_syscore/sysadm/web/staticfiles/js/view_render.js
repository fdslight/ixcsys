/**
 视图渲染插件
 <p class="ixc-view_render"></p>
 */
(function ($) {
    function is_json(s) {
        try {
            JSON.parse(s);
        } catch (e) {
            return false;
        }
        return true;
    }

    function render_atrribute(selector, cls_prefix, name, v) {
        /// 对标签属性进行渲染
        let found = selector.find("*");
        for (let n = 0; n < found.length; n++) {
            let o = found[n];

            for (let attr_name of o.getAttributeNames()) {
                let attr_val = $(o).attr(attr_name);
                let match_str = "{{" + cls_prefix + name + "}}";

                attr_val = attr_val.replace(match_str, v);
                $(o).attr(attr_name, attr_val);
            }
        }
    }

    function render_text(selector, cls_prefix, name, v) {
        /// 渲染标签内的html文本
        let found = selector.find("*");
        for (let n = 0; n < found.length; n++) {
            let o = found[n];
            let attr = $(o).attr('class');

            let has_attr = false;
            if (typeof attr !== typeof undefined && attr !== false) has_attr = true;
            if (!has_attr) continue;

            let cls_name = cls_prefix + name;
            if (attr.indexOf(cls_name) < 0) continue;
            $(o).html(v);
        }
    }

    $.fn.view_render = function (cls_prefix, json_data) {
        let selector = $(this);
        for (let name in json_data) {
            let v = json_data[name];
            render_atrribute(selector, cls_prefix, name, v);
            render_text(selector, cls_prefix, name, v);
        }
    };
})(jQuery);