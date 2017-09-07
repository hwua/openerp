# -*- coding: utf-8 -*-
import logging
import datetime
import ldap
import ldap.modlist as modlist
from openerp import models, fields, api
from openerp.exceptions import ValidationError

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class SetEmploymentWizard(models.Model):
	_name = 'employment.wizard'

	_description = u'设置就业状态'

	name = fields.Selection((('ia','在读'),('ha','休学'),('na','退学'),('se','自主就业'),('ne','待就业'),('he','已就业'),('oc','失联')), string=u'学员状态', required=True)
	employment_way = fields.Selection((('te','推荐'),('se','自荐')), string="就业形式", default='se')
	employment_company = fields.Many2one('res.partner', no_quick_create=True)
	employment_custom_company = fields.Char()
	employment_show_company = fields.Char('就业单位')

	jobs_ids = fields.Many2many('res.partner','employment_res_res_partner','employment_wizard_view_id','res_partner_id', string=u'学生')


	@api.onchange('employment_company')
	def set_company(self):
		self.employment_show_company = self.employment_company.name

	@api.onchange('employment_custom_company')
	def set_custom_company(self):
		self.employment_show_company = self.employment_custom_company

	@api.constrains('name')
	def check_employment(self):
		if self.name in ('ia','ha','na'):
			self.employment_way = 'se'
	
	@api.onchange('employment_way')
	def check_employment_way(self):
		self.employment_company = self.employment_custom_company = self.employment_show_company = False

	@api.onchange('name')
	def check_employment_state(self):
		if self.name in ('ia','ha','na','se'):
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

	@api.one
	def _get_ldap_connection(self):
		ldap_args = {}
		ldap_ids = self.env['ldap.configure'].search([('is_available','=',True)])
		if len(ldap_ids) == 1:
			for rec in ldap_ids:
				_logger.info(u'LDAP服务器地址:%s'% rec.ldap_server)
				ldap_args['ldap_server'] = rec.ldap_server.encode('utf-8')

				_logger.info(u'LDAP binddn:%s' % rec.ldap_binddn)
				ldap_args['ldap_binddn'] = rec.ldap_binddn.encode('utf-8')
				
				_logger.info(u'LDAP 密码:%s' % rec.ldap_password)
				ldap_args['ldap_password'] = rec.ldap_password.encode('utf-8')
			else:	
				con = ldap.open(ldap_args.get('ldap_server'))
				con.protocol_version = ldap.VERSION3
				con.set_option(ldap.OPT_REFERRALS, 0)
				con.simple_bind_s(ldap_args.get('ldap_binddn'),ldap_args.get('ldap_password'))
				return con
		else:
			raise ValidationError(u'Ldap配置发生错误，仅且只能配置一个生效!')
			return False

	@api.one
	def _get_ldap_basedn(self):
		ldap_ids = self.env['ldap.configure'].search([('is_available','=',True)])
		ldapbasedn = None
		if len(ldap_ids) == 1:
			for rec in ldap_ids:
				ldapbasedn = rec.ldap_base
			else:
				_logger.info(u'要添加客户信息的基组是%s' % ldapbasedn)
				return ldapbasedn
		else:
			raise ValidationError(u'Ldap配置发生错误，仅且只能配置一个生效!')
			return False

	@api.one
	def set_employment_state(self):
		for record in self.jobs_ids:
			if record.res_company_type != 'res_company':
				record.employment_state = self.name
				record.employment_way = self.employment_way
				record.employment_company = self.employment_company
				record.employment_custom_company = self.employment_custom_company
				record.employment_show_company = self.employment_show_company
				
				con = self._get_ldap_connection()[0]
				try:
					dn = "mail=%s,%s" % (record.res_email or record.email,self._get_ldap_basedn()[0])
					
					new = {'objectClass':['inetOrgPerson','mailUser','shadowAccount','amavisAccount','perfectInfo']}
					old = {'objectClass':' '}
					ldif = modlist.modifyModlist(old,new)
					con.modify_s(dn,ldif)
					
					con.modify_s(dn,[(ldap.MOD_REPLACE,'employmentState',record.employment_state.encode('utf-8'))])
				except ldap.LDAPError,e:
					_logger.info(u'%s' % e.message)
				finally:
					con.unbind_s()

			if record.employment_company != False:
				record.employment_company = self.employment_company
			
	def default_get(self, cr,uid,fields,context=None):
		if context is None:
			context = {}
		res = super(SetEmploymentWizard,self).default_get(cr,uid,fields,context)
		if context.get('active_model') == 'res.partner' and context.get('active_ids'):
			res['jobs_ids'] = context['active_ids']
		return res
