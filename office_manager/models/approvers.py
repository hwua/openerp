# -*- coding: utf-8 -*-
from openerp import models, fields, api

class officeManagerApprovers(models.Model):
	_name = 'hr.employee.approvers'

	a_id = fields.Many2one('hr.employee')
	approver = fields.Many2one('hr.employee', string='审批人')
	name = fields.Many2one('res.users', string='审批人账号')
	department = fields.Many2one('hr.department', string='管理部门')
	state = fields.Selection(selection=[('notthrough','未通过'),('through','通过')],string= '审批流程')

	@api.one
	@api.constrains('approver')
	def set_approver(self):
		self.write({
			'name': self.approver.user_id.id if self.approver.user_id else False,
			'department': self.approver.department_id.id if self.approver.department_id else False
			})