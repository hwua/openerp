odoo.define('office_manager.script', function (require) {
    var ListView = require('web.ListView')
    var Model = require('web.Model');

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
