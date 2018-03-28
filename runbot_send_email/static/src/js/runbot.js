odoo.define('runbot.followers', function (require) {
    "use strict";
    var rpc = require('web.rpc');

    require('web.dom_ready');

    $('.update_followers').each( function() {
        $(this).on('click', function () {
            var $btn = $(this),
                record = $btn.data('record'),
                model = $btn.data('model');
            rpc.query({
                model: model,
                method: 'update_followers',
                args: [record]
            }).then( function (result) {
                $btn.empty();
                $btn.html(result ? 'Unwatch ' : 'Watch ');
                var type = result ? 'success' : 'warning';
                $('<i>').addClass('fa fa-eye text-' + type).appendTo($btn);
                if (model === 'runbot.repo') {
                    $('a.update_followers').each( function () {
                        $(this).empty();
                        $(this).html(result ? 'Unwatch ' : 'Watch ');
                        $('<i>').addClass('fa fa-eye text-' + type).appendTo(this);
                    });
                }
            });
        });
    });
});
