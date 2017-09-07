#-*- coding:utf-8 -*-

import logging
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'

	res_company_type = fields.Selection([
		('res_student','个人'),
		('res_company','机构'),
		('res_person','其他'),
	],string=u'客户',default='res_student')
	#个人信息
	res_address = fields.Char(string=u'地址')
	res_sex = fields.Selection([
	('boy','男'),
	('girl','女')
	],string=u"性别",default='boy')
	res_from = fields.Selection([
	('58','58同城'),
	('zl','智联'),
	('bd','百度推广'),
	('gx','高校讲座'),
	('51','51job'),
	('kb','口碑推荐'),
	('zp','招聘会'),
	('py','朋友介绍'),
	('qt','其他')
	],string=u"来源")
	res_phone = fields.Char(string=u'座机',size=100,)
	@api.one
	@api.onchange('res_mobile')
	def fllow_res_phone_change(self):
		self.phone = self.res_mobile
	res_mobile = fields.Char(string=u'手机',size=100,)
	res_identity_id = fields.Char(string=u'身份证号',size=100,)
	res_qq = fields.Char(string='QQ',size=100,)
	@api.one
	@api.onchange('res_email')
	def fllow_res_email_change(self):
		self.email = self.res_email
	res_email = fields.Char(string=u'邮箱',size=100,)
	res_website = fields.Char(string=u'网站',size=100)
	res_title = fields.Many2one('res.partner.title',string=u'称谓')

	# 工作学习情况 
	res_biye = fields.Char(string=u'毕业院校',size=100,)
	res_zhuanye = fields.Char(string=u'专业',size=100,)
	res_nianfen = fields.Date(string=u'毕业年份',)
	res_edu = fields.Selection([
		('gz','高中'),	
		('dz','大专'),
		('bk','本科'),
		('si','硕士')
	],string=u'学历',)
	res_work_experience = fields.Selection([
		('y','有'),
		('w','无')
	],string='工作经历',default='w')
	res_trained_experience = fields.Selection([
		('y','有'),
		('w','无')
	],string='培训经历',default='w')
	#紧急联系人
	res_guanxi = fields.Char(string=u'与学生关系',size=100,)
	res_jinji = fields.Char(string=u'紧急联系人',size=100,)
	res_fangshi = fields.Char(string=u'联系方式',size=100,)





