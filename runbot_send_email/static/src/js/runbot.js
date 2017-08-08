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

var _normalize_format_cache = {};
 
$("#lu_add_follower #follower-action-btn" ).on( "click", function(event) {
    
    var self = this;
    var build_id = $(this).data('runbot-build');
    this.$content = $(Qweb.render('AddFollower'));
    this.wait = new Dialog(this, {title: _t("<h3>Wait loading data partners</h3>"),
                                 size: 'medium',
                                 buttons:[],
                                 closeButton: false,
                                 $content: $('<div><i class="fa fa-spinner fa-spin" style="font-size:24px"></i></div>')});
    event.preventDefault;
    this.addfollower = function(self, $content, build_id){
        var options = {
        title: _t("<h3>Add Followers</h3>"),
        size: 'medium',
        buttons: [
                { text: _t("Save"), classes: 'btn-primary', close: true, click: function() {
                var partners = [];
                $("#sel1 option:selected").each(function(ind, element){
                    partners.push(parseInt($(element).val()));
                    var indexof = _normalize_format_cache[build_id].filter(function(elemt, index){
                    if ($(elemt).val() == $(element).val()){
                         delete _normalize_format_cache[build_id][index]
                        }
                    });
                });
                Build.call("add_followers", [[build_id], partners]);
                }
                },
            { text: _t("Close"), close: true }
            ],
            $content: $content,
             };
            self.dialog = new Dialog(self, options).open();
            self.dialog.$content.find("#sel1").select2({
            maximumSelectionLength: 3
            });
        };
    if (_normalize_format_cache[build_id]) {
         this.$content.find("#sel1").append(_normalize_format_cache[build_id]);
         this.addfollower(this, this.$content, build_id);
        } else {
        this.wait.$modal.find('.close').remove();
        this.wait.open();
        _normalize_format_cache[build_id] = [];
        Build.call("select_not_subscribe_partners", [build_id], {}).then(function(data) {
        for(var i in data){
            _normalize_format_cache[build_id].push('<option value='+data[i]['id']+'>'+data[i]['email']+'</option>');
            }
            self.$content.find("#sel1").append(_normalize_format_cache[build_id]);
            self.wait.destroy();
        }).done(function(){
         self.addfollower(this, self.$content, build_id);
        });
   };
  });
});
