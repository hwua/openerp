# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError,ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

class ShebaoFuction(models.Model):
	_name = 'shebao.fuction'
	_description = u'社保计算公式'

	name = fields.Char(string=u'社保缴费公司',compute='_change_name')
	@api.one
	def _change_name(self):
		self.name = self.shebaocompany_id.name
	shebaocompany_id = fields.Many2one('res.company',string=u'员工公司',store=True)

	shebaogerenpercentage1 = fields.Float(string=u'养老个人系数', digits=(16, 3))
	shebaogerenpercentage2 = fields.Float(string=u'失业个人系数', digits=(16, 3))
	shebaogerenpercentage3 = fields.Float(string=u'医疗个人系数', digits=(16, 3))
	shebaogerenpercentage4 = fields.Float(string=u'补交个人系数', compute='_amount_allmy', digits=(16, 3))
	shebaocomypercentage1 = fields.Float(string=u'养老公司系数', digits=(16, 3))
	shebaocomypercentage2 = fields.Float(string=u'失业公司系数', digits=(16, 3))
	shebaocomypercentage3 = fields.Float(string=u'医疗公司系数', digits=(16, 3))
	shebaocomypercentage5 = fields.Float(string=u'生育公司系数', digits=(16, 3))
	shebaocomypercentage4 = fields.Float(string=u'工伤公司系数', digits=(16, 3))
	shebaocomypercentage6 = fields.Float(string=u'补交公司系数', compute='_amount_allmy', digits=(16, 3))

	gerenpercentage = fields.Float(string=u'公积金个人缴纳系数',digits=(16, 3))
	gongsipercentage = fields.Float(string=u'公积金公司缴纳系数',digits=(16, 3))
	gonggerenmoneybase = fields.Float(string=u'公积金个人缴纳基数')
	gongcompanymoneybase = fields.Float(string=u'公积金公司缴纳基数')

	@api.one
	def _amount_allmy(self):
			self.shebaogerenpercentage4 = self.shebaogerenpercentage1+self.shebaogerenpercentage2+self.shebaogerenpercentage3
			self.shebaocomypercentage6 =self.shebaocomypercentage1+self.shebaocomypercentage2+self.shebaocomypercentage3+self.shebaocomypercentage4+self.shebaocomypercentage5