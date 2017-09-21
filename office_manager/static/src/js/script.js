odoo.define('office_manager.script', function (require) {
    var ListView = require('web.ListView')
    var Model = require('web.DataModel');// 异步

    ListView.include({
        render_buttons: function() {
            this._super.apply(this, arguments)
            if (this.$buttons) {
                var btn = this.$buttons.find('.update_users_role')
            }
            btn.on('click', this.proxy('do_new_button'))
        },
        do_new_button: function() {
            (new Model('hr.employee.os')).call('update_users_role', [[]]);
        }
    });
})

odoo.define('office_manager.close_account', function (require) {
    'use strict';
    var Model = require('web.DataModel'),
    form_common = require('web.form_common');

    form_common.AbstractField.include({
        start: function() {
            this._super();
            var fm = this.field_manager
            if (fm.model == "hr.employee"){
                var state = fm.get_field_value('state');

                if (state == 'leaving') {
                    new Model('hr.employee.approvers').call('get_hr_employee_approver', [this.field_manager.get_field_value("approvers_line")]).done(function(result) {
                        if (result == true){
                            $('.close_account').removeClass('o_form_invisible');
                        }
                        else{
                            $('.close_account').addClass('o_form_invisible');
                        }
                    });
                }

                $('.btn').on('click', function () {
                    setTimeout(function () {
                        if (state == 'leaving') {
                            new Model('hr.employee.approvers').call('get_hr_employee_approver', [fm.get_field_value("approvers_line")]).done(function(result) {
                                if (result == true){
                                    $('.close_account').removeClass('o_form_invisible');
                                }
                                else{
                                    $('.close_account').addClass('o_form_invisible');
                                }
                            });
                        };
                    }, 200);
                });
            }
        },
    });
});