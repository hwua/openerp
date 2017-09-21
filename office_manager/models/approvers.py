# -*- coding: utf-8 -*-
from openerp import models, fields, api, SUPERUSER_ID
from openerp.exceptions import ValidationError

class DeparmentApprovalSeries(models.Model):
    _inherit = 'hr.department'

    series = fields.Integer(default = 1,string='账号审批级数',help='入职/离职审批的向上审批级数，0为无限向上审批，1为仅本部门经理审批', track_visibility='onchange')
    os_department_id = fields.Integer(string='OS部门术语',help='OS端部门术语')

class officeManagerApprovers(models.Model):
    _name = 'hr.employee.approvers'

    a_id = fields.Many2one('hr.employee')
    approver = fields.Many2one('hr.employee', string='审批人')
    name = fields.Many2one('res.users', string='审批人账号')
    department = fields.Many2one('hr.department', string='部门')
    post = fields.Selection(selection=[('superior', '上级'),('administrative', '行政'),('information', 'IT'),('personnel', '人事')],string='审批职责')
    state = fields.Selection(selection=[('notthrough','未通过'),('through','通过')],string= '审批状态')

    # 完善审批人
    @api.one
    @api.constrains('approver')
    def set_approver(self):
        self.write({
            'name': self.approver.user_id.id if self.approver.user_id else False,
            'department': self.approver.department_id.id if self.approver.department_id else False
            })

    # js调用，查询当前用户是否审批人，否则不显示关闭按钮
    def get_hr_employee_approver(self, cr, uid, lines):
        approvers = self.search(cr, SUPERUSER_ID, ['&','&',('post','=','personnel'),('name','=', uid),('id', 'in', [line[1] for line in lines])])
        return False if approvers == [] else True


class LeavingConfirm(models.TransientModel):
    _name = 'hr.employee.leaving.confirm'

    # 开始离职，套用入职审批流程，加入额外审批人的方式
    @api.multi
    def confirm(self):
        approvers = {
            'administrative' : self.administrative.id if self.administrative else False, 
            'information' : self.information.id if self.information else False,
            'personnel' : self.personnel.id if self.personnel else False,
        }

        employee = self.env['hr.employee'].browse(self._context.get('active_id',False))
        if employee and employee.set_approval(other_approvers=approvers):
            employee.start_approval(act='leave')

    # 已选员工不能在其他地方选择
    @api.onchange('administrative','information','personnel')
    def get_employee(self):
        res = {}
        cant_choice = [
            self.administrative.id if self.administrative else False,
            self.information.id if self.information else False,
            self.personnel.id if self.personnel else False,
        ]
        res['domain'] = {
            'administrative': ['|',('id', 'not in', cant_choice),('id', '=', self.administrative.id)],
            'information': ['|',('id', 'not in', cant_choice),('id', '=', self.information.id)],
            'personnel': ['|',('id', 'not in', cant_choice),('id', '=', self.personnel.id)],
        }
        return res

    administrative = fields.Many2one('hr.employee',string="行政")
    information = fields.Many2one('hr.employee',string="IT")
    personnel = fields.Many2one('hr.employee',string="人事")