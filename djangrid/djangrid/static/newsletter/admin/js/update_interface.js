var UpdateInterface = {
    changed: false,

    init: function(updatename) {
        var updatelink = django.jQuery(updatename);
        var initial_href = updatelink.attr('href');
        updatelink.click(function() {
            UpdateInterface.process(initial_href);
        });
        updatelink.attr('href', '#');
        django.jQuery('form:first :input').change(function() {
            UpdateInterface.changed = true;
        });
    },

    process: function(href) {
        if (UpdateInterface.changed) {
            var result = confirm(gettext('The segment has been updated. Click OK to proceed with saving, click cancel to continue editing.'));
            if (result) {
                django.jQuery('form:first [name="_continue"]').click();
            }
        } else {
            window.location = href;
        }
    }
};
