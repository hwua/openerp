# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)

class EmploymentCompanyJobs(models.Model):
	_name = 'interview_record'

	interview_record_id = fields.Integer()
	time = fields.Date(string='时间')
	record = fields.Char(string='记录')