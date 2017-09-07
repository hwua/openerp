# -*- coding: utf-8 -*-
import openerp
import openerp.modules.registry
import ast
import logging

from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.web.controllers.main import Home
from openerp import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class Home(Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        super(Home, self).web_login(redirect, **kw)
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])

            if uid is not False:

                # 查找账号对应员工，如果员工hr.employee在草稿或者审批中，抛出错误。
                admin_group_id = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID,'base.group_configuration')
                request.cr.execute("SELECT uid FROM res_groups_users_rel WHERE gid=%s and uid=%s", (admin_group_id,uid))
                admin_id = request.cr.dictfetchall()
                # 网站设置管理员除外，不验证
                if not admin_id:
                    request.cr.execute("SELECT id FROM resource_resource WHERE user_id=%s"%uid)
                    employee_ids = request.cr.dictfetchall()
                    if employee_ids:
                        for employee_id in employee_ids[0]:
                            request.cr.execute("SELECT id,state FROM hr_employee WHERE resource_id=%s and (state=%s or state=%s)", (employee_ids[0][employee_id],'underway','draft'))
                            results = request.cr.dictfetchall()
                            if results:
                                values['error'] = _("您的账号正在入职审批流程中，暂时无法使用，请耐心等待审批完成")
                                return request.render('web.login', values)

                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = _("Wrong login/password")
        return request.render('web.login', values)