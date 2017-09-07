# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError,ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

class CenterCompany(models.Model):
	_name = 'center.company'

	name = fields.Char(string=u'所属中心')
	centermanger_employee = fields.Many2one("hr.employee",string=u'所属中心负责人')





