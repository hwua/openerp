# -*- coding: utf-8 -*-
from ldap.filter import filter_format
import openerp.exceptions
from openerp import tools, SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.modules.registry import RegistryManager

class Employee(osv.osv):
    _inherit = 'res.company.ldap'

    def map_ldap_attributes(self, cr, uid, conf, login, ldap_entry):
        values = { 'name': ldap_entry[1]['cn'][0],
                   'login': login,
                   'email': login,
                   'company_id': conf['company'],
                   'notify_email': 'none',#关闭邮件通知，否则hr.employee的关注人会收到odoo的内容通知邮件，这是不必要的
                   }
        return values

    # 新账号新建员工草稿用作审批流程
    def get_or_create_user(self, cr, uid, conf, login, ldap_entry, context=None):
        user_id = False
        login = tools.ustr(login.lower().strip())
        cr.execute("SELECT id, active FROM res_users WHERE lower(login)=%s", (login,))
        res = cr.fetchone()
        if res:
            if res[1]:
                user_id = res[0]
        elif conf['create_user']:
            user_obj = self.pool['res.users']
            values = self.map_ldap_attributes(cr, uid, conf, login, ldap_entry)
            if conf['user']:
                values['active'] = True
                user_id = user_obj.copy(cr, SUPERUSER_ID, conf['user'],
                                        default=values)
            else:
                user_id = user_obj.create(cr, SUPERUSER_ID, values)

            employee = self.pool['hr.employee'].search(cr, SUPERUSER_ID, [('user_id','=',user_id)])
            if employee == []:
                values_employee = {
                            'user_id': user_id,
                            'name': values['name'],
                            'work_email': values['login'],
                            'company_id': values['company_id'],
                            'active': False,
                            'state': 'draft',
                            }
                self.pool['hr.employee'].create(cr, SUPERUSER_ID, values_employee)
        return user_id