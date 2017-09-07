# -*- coding: utf-8 -*-
import logging
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError

class Coreto(models.Model):
	_name = 'coreto.account'
	_description = u'中心管理'

	name = fields.Char(string=u'中心名称',required=True)
	core_number=fields.Char(string=u'中心编号')
	admin_name = fields.Many2one('hr.employee',string='行政负责人')
	address = fields.Char(string=u'地址')
	code = fields.Char(string=u'邮编')

