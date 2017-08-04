odoo.define('runbot.test', function (require) {
    "use strict";

var core = require('web.core');
var base = require('web_editor.base');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var Build = new Model('runbot.build');
var _t = core._t;
var Qweb = core.qweb;
Qweb.add_template('/runbot_send_email/static/src/xml/runbot_template.xml');

$("#lu_add_follower #follower-action-btn" ).on( "click", function(event) {
    var self = this;
    var build_id = $(this).data('runbot-build');
    this.$content = $(Qweb.render('AddFollower'));
    event.preventDefault;
    Build.call("select_not_subscribe_partners", [build_id], {}).then(function(data) {
        for(var i in data){
            self.$content.find("#sel1").append('<option value='+data[i]['id']+'>'+data[i]['email']+'</option>');
            }
    });
    var options = {
                title: _t("<h3>Add Followers</h3>"),
                size: 'medium',
                buttons: [
                    { text: _t("Save"), classes: 'btn-primary', close: true, click: function() {
                      var partners = [];
                      $("#sel1 option:selected").each(function(ind, element){
                           partners.push(parseInt($(element).val()));
                        });
                      Build.call("add_followers", [[build_id], partners]);
                     }
                 },
                    { text: _t("Close"), close: true }
                ],
                 $content: self.$content,
             };
     this.dialog = new Dialog(this, options).open();
     this.dialog.$content.find("#sel1").select2({
            maximumSelectionLength: 3
         });
    });
});
