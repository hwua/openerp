# -*- coding: utf-8 -*-
import logging
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError

class EvaluateGetEmployment(models.Model):
	_inherit = "evaluate.account"

	@api.onchange('name')
	def _get_default_value(self):
		self.unit = self.name.employment_company.name if self.name.employment_company.name else False
		self.salary = self.name.employment_salary if self.name.employment_salary else False