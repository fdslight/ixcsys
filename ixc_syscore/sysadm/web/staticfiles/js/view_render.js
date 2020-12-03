/**
 视图渲染插件
 <p class="ixc-view_render"></p>
 */
(function ($) {

    function render(cls_prefix, name, v) {
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

        }
    };
})(jQuery);