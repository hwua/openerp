# -*- coding: utf-8 -*-
import logging
import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _
from openerp.exceptions import UserError,ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)

class RecruitmentInformation(models.Model):
	_name = 'recruitment.information'
	_inherit = ['mail.thread']
	_description = u'招聘需求模型'

	name = fields.Char(string=u'招聘需求',compute='_change_name')
	@api.one
	def _change_name(self):
		self.name = self.shenqingresuser.name
	shenqingstartdate = fields.Date(string=u'申请日期',default=datetime.date.today(),track_visibility=True)
	yaoqiudate = fields.Date(string=u'要求到岗日期',track_visibility=True)
	shenqingdepartment_id = fields.Many2one('hr.department',string=u'申请部门')
	shenqingresuser = fields.Many2one('res.users',string=u'申请人' ,default=lambda self: self.env.user)
	shenqinggangwei = fields.Char(string=u'申请岗位',track_visibility=True)
	beizhu = fields.Char(string=u'备注',track_visibility=True)
	username = fields.Char(string=u'入职员工姓名',track_visibility=True)
	guangweishangji = fields.Many2one('hr.employee',string=u'岗位直属上级')
	xuqiurenshu = fields.Integer(string=u'需求人数',default=1)
	wagesyusuan = fields.Float(string=u'薪酬预算',track_visibility=True)
	@api.constrains('wagesyusuan')
	def _complete_shu(self):
		if self.wagesyusuan == 0.0:
			raise ValidationError(u"薪酬预算不能为0")

	lasttime = fields.Date(string=u'到期时间',compute='_complete_lasttime')

	def str_to_date(self,str_data):
		DATE_FORMAT = "%Y-%m-%d"
		d = datetime.datetime.strptime(str_data, DATE_FORMAT).date()
		return d

	@api.one
	def _complete_lasttime(self):
		if self.shenqingstartdate:
			if self.str_to_date(self.shenqingstartdate).day<=9:
				self.lasttime = self.str_to_date(self.shenqingstartdate)+relativedelta(day=self.str_to_date(self.shenqingstartdate).day + 21)
			else:
				self.lasttime = self.str_to_date(self.shenqingstartdate)+relativedelta(month=self.str_to_date(self.shenqingstartdate).month + 1)+relativedelta(day=self.str_to_date(self.shenqingstartdate).day-9)

	shenqingreason = fields.Selection([
	('extends',u'扩大编制'),
	('vacancy',u'岗位空缺'),
	('supplement',u'离职补充'),
	('reserve',u'储备人员'),
	('other',u'其他')
	],string = u'申请理由' ,track_visibility=True)
	reasontext = fields.Text(string=u'关闭或拒绝理由' ,track_visibility=True)
	workduty = fields.Text(string=u'主要工作职责' ,track_visibility=True)
	workqualifications = fields.Text(string=u'任职资格' ,track_visibility=True)
	partbianzhinumber = fields.Integer(string=u'部门编制人数')
	partshijinumber = fields.Integer(string=u'该部门实际人数')
	gangweibianzhinumber = fields.Integer(string=u'该岗位编制人数')
	gangweishijinumber = fields.Integer(string=u'该岗位实际人数')
	koufenterm = fields.Integer(string=u'扣分数值',track_visibility=True)
	jiafenterm = fields.Integer(string=u'加分数值',track_visibility=True)

	hrgettime = fields.Date(string=u'拟入职日期',track_visibility=True)
	lasttimedao = fields.Date(string=u'实际到岗日期',track_visibility=True)
	yaoqiuzhaorendays = fields.Integer(string=u'要求招聘天数',track_visibility=True,compute='data_yaoqiuzhaorendays')
	@api.one
	def data_yaoqiuzhaorendays(self):
		if not self.yaoqiudate:
			self.yaoqiuzhaorendays = 21
		else:
			if (self.str_to_date(self.yaoqiudate)-self.str_to_date(self.shenqingstartdate)).days<=21:
				self.yaoqiuzhaorendays = 21
			else:
				self.yaoqiuzhaorendays = (self.str_to_date(self.yaoqiudate)-self.str_to_date(self.shenqingstartdate)).days


	zhaorendays = fields.Integer(string=u'招聘天数',track_visibility=True,compute='data_zhaorendays')
	@api.one
	def data_zhaorendays(self):
		if self.lasttimedao and self.shenqingstartdate:
			self.zhaorendays = (self.str_to_date(self.lasttimedao)-self.str_to_date(self.shenqingstartdate)).days
			
	zhipaiuser = fields.Many2one('hr.employee',string=u'所属中心HR',track_visibility=True)
	HRmanage = fields.Many2one('hr.employee',string=u'HR主管',compute='complete_HRmanage')
	@api.one
	def complete_HRmanage(self):
		hr_department_model = self.env['hr.department']
		hr_department = hr_department_model.search([('name', '=', '集团中心人力资源部')])
		self.HRmanage = hr_department.manager_id.id


	recruitmentstate = fields.Selection([('yes',u'是'),('no',u'否')],string = u'是否己经招到人')
	state = fields.Selection([('draft',u'提交'),
	('wait',u'处理中'),
	('fankui',u'待确认'),
	('done',u'完成'),
	('off',u'关闭'),
	('refuse',u'拒绝')],string = u'状态',default="draft",track_visibility=True)

	is_user = fields.Boolean(string=u'是否是所属中心HR',compute='onchange_is_user')
	def onchange_is_user(self):
		if self.zhipaiuser.user_id == self.env.user:
			self.is_user = True
		else:
			self.is_user = False

	is_done = fields.Boolean(string=u'是否完成',compute='onchange_is_user')
	def onchange_is_user(self):
		if self.state == "done":
			self.is_done = True
		else:
			self.is_done = False

	is_usershen = fields.Boolean(string=u'是否是申请人',compute='onchange_is_usershen')
	def onchange_is_usershen(self):
		if self.shenqingresuser == self.env.user:
			self.is_usershen = True
		else:
			self.is_usershen = False

	is_HRmanage = fields.Boolean(string=u'是否是HRmanage',compute='onchange_is_HRmanage')
	def onchange_is_HRmanage(self):
		if self.HRmanage.user_id == self.env.user:
			self.is_HRmanage = True
		else:
			self.is_HRmanage = False
#提交，所属中心HR，给申请人和主管发邮件。所属中心HR修改状态，给申请人和主管发邮件。
#拒绝，关闭，发送邮件。
#完成发送邮件
	@api.multi
	def send_email_user(self):
		if self.zhipaiuser.work_email and self.HRmanage.work_email:
			self.send_recruitment_email(self.zhipaiuser.work_email,self.HRmanage.work_email)
			raise ValidationError(u'邮件推送成功!')

	@api.constrains('recruitmentstate')
	def change_recr(self):
		if self.recruitmentstate=="yes" and self.shenqingresuser.email and self.HRmanage.work_email:
			self.send_recruitment_email(self.shenqingresuser.email,self.HRmanage.work_email)

	@api.constrains('state')
	def onchange_state(self):
		if self.state == "draft":
			self.write({'beizhu':'这是一个新的需求，如果明确请修改状态为，处理中！'})
			if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
				self.send_recruitment_email(self.shenqingresuser.email,self.zhipaiuser.work_email)
				self.send_recruitment_email(self.shenqingresuser.email,self.HRmanage.work_email)	
		elif self.state == "wait":
			self.write({'beizhu':'已收到需求，处理中！'})
			if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
				self.send_recruitment_email(self.zhipaiuser.work_email,self.shenqingresuser.email)
				self.send_recruitment_email(self.zhipaiuser.work_email,self.HRmanage.work_email)
		elif self.state == "fankui":
			self.write({'beizhu':'已经招到人。请修改，是否已经招到人，字段，为是！'})
			if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
				self.send_recruitment_email(self.zhipaiuser.work_email,self.shenqingresuser.email)
				self.send_recruitment_email(self.zhipaiuser.work_email,self.HRmanage.work_email)
		elif self.state == "done":
			self.write({'beizhu':'该需求已完成'})
			if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
				self.send_recruitment_email(self.HRmanage.work_email,self.shenqingresuser.email)
				self.send_recruitment_email(self.HRmanage.work_email,self.zhipaiuser.work_email)
		elif self.state == "off":
			self.write({'beizhu':'申请人关闭该需求'})
			if not self.reasontext:
				raise ValidationError(u"请填写理由！")
			else:
				if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
					self.send_recruitment_email(self.zhipaiuser.work_email,self.shenqingresuser.email)
					self.send_recruitment_email(self.zhipaiuser.work_email,self.HRmanage.work_email)
		elif self.state == "refuse":
			self.write({'beizhu':'所属中心HR拒绝该需求'})
			if not self.reasontext:
				raise ValidationError(u"请填写理由！")
			else:
				if self.shenqingresuser.email and self.zhipaiuser.work_email and self.HRmanage.work_email:
					self.send_recruitment_email(self.shenqingresuser.email,self.zhipaiuser.work_email)
					self.send_recruitment_email(self.shenqingresuser.email,self.HRmanage.work_email)
		else:
			pass

	def update_recruitment(self, cr, uid, ids,context=None):
		recruitment_information_models = self.pool.get('recruitment.information')
		recruitment_information_ids = recruitment_information_models.search(cr, uid, [('id', '!=', False)])
		for partner in recruitment_information_ids:
			recruitment_information = recruitment_information_models.browse(cr, uid, partner)
			if recruitment_information.lasttime:
				if recruitment_information.lasttime == datetime.date.today():
					if recruitment_information.recruitmentstate:
						if recruitment_information.recruitmentstate != 'yes':
							if recruitment_information.shenqingresuser.email and recruitment_information.zhipaiuser.work_email and recruitment_information.HRmanage.work_email:
								recruitment_information.send_recruitment_email(recruitment_information.zhipaiuser.work_email,recruitment_information.shenqingresuser.email)
								recruitment_information.send_recruitment_email(recruitment_information.zhipaiuser.work_email,recruitment_information.HRmanage.work_email)
					else:
						if recruitment_information.shenqingresuser.email and recruitment_information.zhipaiuser.work_email and recruitment_information.HRmanage.work_email:
							recruitment_information.send_recruitment_email(recruitment_information.zhipaiuser.work_email,recruitment_information.shenqingresuser.email)
							recruitment_information.send_recruitment_email(recruitment_information.zhipaiuser.work_email,recruitment_information.HRmanage.work_email)
	
	# @api.constrains('shenqingdepartment_id')
	# def update_test(self, cr, uid, ids,context=None):
		# hr_department_model = self.pool.get('hr.department')
		# hr_department = hr_department_model.search(cr, uid, [('id', '!=', False)])
		# lst = []
		# for per in hr_department:
			# hr_department_ids = hr_department_model.browse(cr, uid, per)
			# lst.append(hr_department_ids.manager_id.user_id.id)
		# if uid not in lst:
			# raise ValidationError("只有部门主管有创建权限！")


