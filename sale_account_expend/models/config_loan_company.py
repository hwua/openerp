# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

#贷款方案
class config_loan_company(models.Model):
	_name = 'config_company'

	name = fields.Char(string=u'贷款公司名称', required=True)
	remarks = fields.Text(string=u'备注')
	project = fields.One2many('config_project','company_id', string=u'金融方案', ondelete='cascade')
	active = fields.Boolean(string=u'有效',default=True)