# -*- coding: utf-8 -*-
from openerp import models, fields

class DeparmentApprovalSeries(models.Model):
    _inherit = 'hr.department'

    series = fields.Integer(default = 1,string='账号审批级数',help='入职/离职审批的向上审批级数，0为无限向上审批，1为仅本部门经理审批', track_visibility='onchange')
    os_department_id = fields.Integer(string='OS部门术语',help='OS端部门术语')