# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

class config_loan_project(models.Model):
	_name = 'config_project'

	company_id = fields.Char()
	name = fields.Char(string=u'模式')
	mo = fields.Char(string=u'名称', required=True)
	month1 = fields.Integer(required=True)
	month2 = fields.Integer(required=True)
	rate1 = fields.Float(string=u'前期利率', requird=True, digits=(16, 3))
	repayment_rate1 = fields.Float(string=u'还款率', digits=(16, 3))
	rate2 = fields.Float(string=u'后期利率', requird=True, digits=(16, 3))
	repayment_rate2 = fields.Float(string=u'还款率', digits=(16, 3))
	remarks = fields.Char(string=u'备注')
	active = fields.Boolean(string=u'有效',default=True)

	@api.onchange('mo','month1','month2','remarks')
	def _get_info_by_name(self):
		month = str(self.month1) + '+' + str(self.month2)
		if self.remarks:
			self.name = "%s, %s , %s" % (self.mo, month, self.remarks)
		else:
			self.name = "%s, %s" % (self.mo, month)