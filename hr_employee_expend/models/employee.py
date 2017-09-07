#-*- coding:utf-8 -*- 

import logging
import datetime

from dateutil.relativedelta import relativedelta
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError


_logger = logging.getLogger(__name__)

# 员工继承字段
class HrEmployee2(models.Model):
	_inherit = 'hr.employee'

#公开信息——联系信息
	hr_worktime_from = fields.Date(string=u'入职时间')#start_date
	hr_worktime_zheng = fields.Date(string=u'转正时间')
	hr_worktime_to = fields.Date(string=u'离职时间')
	center_id = fields.Many2one("center.company",string=u'所属中心')
	wagesmodel_id = fields.Many2one('wages.model', string='工资单')

	shebaofuction_id = fields.Many2one('shebao.fuction',string=u'社保缴费公司')

	basewages = fields.Float(string=u'现在基本工资标准')
	gangweijintiebasewages = fields.Float(string=u'现在岗位津贴标准')
	gangweijixiaobasewages = fields.Float(string=u'现在岗位绩效标准')
	guanlijixiaobasewages = fields.Float(string=u'现在管理绩效标准')

	basewageshou = fields.Float(string=u'调薪后基本工资标准')
	gangweijintiebasewageshou = fields.Float(string=u'调薪后岗位津贴标准')
	gangweijixiaobasewageshou = fields.Float(string=u'调薪后岗位绩效标准')
	guanlijixiaobasewageshou = fields.Float(string=u'调薪后管理绩效标准')

	tiaoxinriqi = fields.Date(string=u'调薪日期')
	ruzhitime = fields.Integer(string=u'司龄',compute='_complete_ruzhitime')
	ruzhitime_date = fields.Date(string="今天",default=datetime.date.today())

	shebaocompanymoneybase1 = fields.Float(string=u'养老公司缴费基数')
	shebaocompanymoneybase2 = fields.Float(string=u'失业公司缴费基数')
	shebaocompanymoneybase3 = fields.Float(string=u'医疗公司缴费基数')
	shebaocompanymoneybase4 = fields.Float(string=u'工伤公司缴费基数')
	shebaocompanymoneybase5 = fields.Float(string=u'生育公司缴费基数')
	gongcompanymoneybase = fields.Float(string=u'公积金公司缴纳基数')

	gerenpercentage = fields.Float(string=u'公积金个人缴纳系数',compute='_change_shebaofuction_id',digits=(16, 3))
	gongsipercentage = fields.Float(string=u'公积金公司缴纳系数',compute='_change_shebaofuction_id',digits=(16, 3))

	shebaogerenpercentage1 = fields.Float(string=u'养老个人系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaogerenpercentage2 = fields.Float(string=u'失业个人系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaogerenpercentage3 = fields.Float(string=u'医疗个人系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaogerenpercentage4 = fields.Float(string=u'补交个人系数',compute='_change_shebaofuction_id', digits=(16, 3))

	shebaocomypercentage1 = fields.Float(string=u'养老公司系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaocomypercentage2 = fields.Float(string=u'失业公司系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaocomypercentage3 = fields.Float(string=u'医疗公司系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaocomypercentage4 = fields.Float(string=u'工伤公司系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaocomypercentage5 = fields.Float(string=u'生育公司系数',compute='_change_shebaofuction_id', digits=(16, 3))
	shebaocomypercentage6 = fields.Float(string=u'补交公司系数',compute='_change_shebaofuction_id', digits=(16, 3))

	recommendation = fields.Text()
	referrer = fields.Text()

	@api.one
	def _change_shebaofuction_id(self):
		self.shebaogerenpercentage1 = self.shebaofuction_id.shebaogerenpercentage1
		self.shebaogerenpercentage2 = self.shebaofuction_id.shebaogerenpercentage2
		self.shebaogerenpercentage3 = self.shebaofuction_id.shebaogerenpercentage3
		self.shebaogerenpercentage4 = self.shebaofuction_id.shebaogerenpercentage4
		self.shebaocomypercentage1 = self.shebaofuction_id.shebaocomypercentage1
		self.shebaocomypercentage2 = self.shebaofuction_id.shebaocomypercentage2
		self.shebaocomypercentage3 = self.shebaofuction_id.shebaocomypercentage3
		self.shebaocomypercentage4 = self.shebaofuction_id.shebaocomypercentage4
		self.shebaocomypercentage5 = self.shebaofuction_id.shebaocomypercentage5
		self.shebaocomypercentage6 = self.shebaofuction_id.shebaocomypercentage6	
		self.gerenpercentage = self.shebaofuction_id.gerenpercentage
		self.gongsipercentage = self.shebaofuction_id.gongsipercentage

	def str_to_date(self,str_data):
		DATE_FORMAT = "%Y-%m-%d"
		d = datetime.datetime.strptime(str_data, DATE_FORMAT).date()
		return d

	@api.one
	def _complete_ruzhitime(self):
		if isinstance(self.hr_worktime_from, str):
			self.ruzhitime=(self.str_to_date(self.ruzhitime_date)-self.str_to_date(self.hr_worktime_from)).days/365



