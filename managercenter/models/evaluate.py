# -*- coding: utf-8 -*-
import logging
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError

class Evaluate(models.Model):
	_name="evaluate.account"
	_description=u'学生评估'

	name=fields.Many2one('res.partner',string="学生姓名",required=True)
	unit=fields.Char(string="就业单位")
	salary=fields.Integer(string="薪资")
	evaluate=fields.Text(string="综合评价")
	remarks=fields.Char(string="备注")


