# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)

class EmploymentCompanyJobs(models.Model):
	_name = 'company_jobs'

	job_id = fields.Integer()
	name = fields.Char(string='职位',required=True)
	salary = fields.Float(string='薪资')
	work = fields.Text(string='职位需求')