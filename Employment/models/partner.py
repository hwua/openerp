# -*- coding: utf-8 -*-
import logging
import ldap
import ldap.modlist as modlist
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError
from openerp.http import request

_logger = logging.getLogger(__name__)

class ManagerCenterPartnerAddStatu(models.Model):
	_inherit = 'res.partner'

	employment_state = fields.Selection((('ia','在读'),('ha','休学'),('na','退学'),('se','自主就业'),('ne','待就业'),('he','已就业')), string=u'学员状态', default='ia', track_visibility='onchange')
	employment_job = fields.Char(string="就业岗位", track_visibility='onchange')

	employment_company = fields.Many2one('res.partner', no_quick_create=True, track_visibility='onchange')
	employment_custom_company = fields.Char('就业单位', track_visibility='onchange')
	employment_show_company = fields.Char('就业单位', track_visibility='onchange')
	company_jobs = fields.One2many('company_jobs','job_id',string="就业岗位", track_visibility='onchange')
	employment_salary = fields.Char(string="就业薪资", track_visibility='onchange')
	employment_date = fields.Date(string="就业时间", track_visibility='onchange')
	employment_area = fields.Char(string="就业城市", track_visibility='onchange')
	interview_record = fields.One2many('interview_record','interview_record_id',string="面试记录", track_visibility='onchange')
	employment_way = fields.Selection((('te','推荐'),('se','自荐')), string="就业形式", default='se', track_visibility='onchange')

	res_professional_planner = fields.Many2one('hr.employee',string="职业规划师", no_quick_create=True, track_visibility='onchange')

	contect_name = fields.Char(string="联系人姓名", track_visibility='onchange')

	company_size = fields.Selection((('a','<50'),('b','50-150'),('c','150-500'),('d','500-1000'),('e','1000-3000'),('f','>3000')),string="规模", track_visibility='onchange')

	@api.onchange('employment_company')
	def set_company(self):
		self.employment_show_company = self.employment_company.name

	@api.onchange('employment_custom_company')
	def set_custom_company(self):
		self.employment_show_company = self.employment_custom_company

	@api.constrains('employment_state')
	def check_employment(self):
		if self.employment_state in ('ia','ha','na'):
			self.employment_way = 'se'
	
	@api.onchange('employment_way')
	def check_employment_way(self):
		self.employment_company = self.employment_custom_company = self.employment_show_company = False

	@api.onchange('employment_state')
	def check_employment_state(self):
		if self.employment_state in ('ia','ha','na','se'):
			self.employment_way = 'se'
			if self.employment_company or self.employment_custom_company:
				self.employment_company = self.employment_company
				self.employment_custom_company = self.employment_custom_company
		else:
			if self.employment_way:
				self.employment_way = self.employment_way
				if self.employment_company or self.employment_custom_company:
					self.employment_company = self.employment_company
					self.employment_custom_company = self.employment_custom_company

		if self.cuid != '/':
			con = self._get_ldap_connection()[0]
			if self.employment_state:
				try:
					dn = "mail=%s,%s" % (self.res_email or self.email,self._get_ldap_basedn()[0])

					new = {'objectClass':['inetOrgPerson','mailUser','shadowAccount','amavisAccount','perfectInfo']}
					old = {'objectClass':' '}
					ldif = modlist.modifyModlist(old,new)
					con.modify_s(dn,ldif)

					con.modify_s(dn,[(ldap.MOD_REPLACE,'employmentState',self.employment_state.encode('utf-8'))])
				except ldap.LDAPError,e:
					_logger.info(u'%s' % e.message)
				finally:
					con.unbind_s()

	# 从'学生管理'——'企业管理'处新建partner时，默认选择'机构'
	def get_res_company_type_default_value(self):
		# 取partner form表单链接的action（视图决定action的id，这里的views是继承模型并新建的视图），所以和其余partner form的action不同，故可以作为条件使用，以达成默认勾选'机构'

		if request.params.has_key('kwargs'):
			if request.params['kwargs']['context'].has_key('params'):
				if request.params['kwargs']['context']['params'].has_key('action'):
					if  str(request.params['kwargs']['context']['params']['action']) == '954':
						return 'res_company'
		return 'res_student'

	res_company_type = fields.Selection([('res_student','个人'),('res_company','机构'),('res_person','其他'),], string=u'客户', default = get_res_company_type_default_value, required=True)

	def get_customer_default_value(self):

		if request.params.has_key('kwargs'):
			if request.params['kwargs']['context'].has_key('params'):
				if request.params['kwargs']['context']['params'].has_key('action'):
					if  str(request.params['kwargs']['context']['params']['action']) == '954':
						return False
		return True

	customer = fields.Boolean('是客户',default = get_customer_default_value)