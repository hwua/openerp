#-*- coding:utf-8 -*-

import logging
import ldap
import ldap.modlist as modlist

from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'
	_order = 'id desc'
	
	@api.one
	def _compute_judge_done(self):
		sale_ids = self.env['sale.order'].search([('partner_id','=',self.id)])
		if sale_ids:
			for sale_obj in sale_ids:
				_logger.info(u'self.invoice_status is %s' % str(sale_obj.invoice_status))
				if sale_obj.invoice_status == 'invoiced':
					_logger.info(u'发票状态:已开具全额发票')
					self.judge_done = True
				else:
					_logger.info(u'发票状态:未开具全额发票')
					self.judge_done = False

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
				# Bind/authenticate with a user with apropriate rights to add objects
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

	#点击查看客户的时候，才会计算执行
	judge_done = fields.Boolean(string=u'是否全款',compute='_compute_judge_done',help=u'显示交款状况')
	
	#客户编号
	cuid = fields.Char(string=u'编号',compute='_compute_bianhao',default='/')

	@api.one
	def _compute_bianhao(self):
		if len(str(self.id)) == 1:
			self.cuid = 'CU000'+u'%s' % str(self.id)
		elif len(str(self.id)) == 2:
			self.cuid = 'CU00'+u'%s' % str(self.id)
		elif len(str(self.id)) == 3:
			self.cuid = 'CU0'+u'%s' % str(self.id)
		else:
			self.cuid = 'CU'+u'%s' % str(self.id)

	#监控邮箱的变化,重写Ldap
	@api.one
	#@api.onchange('email')
	def fllow_email_change(self):
		_logger.info(u'当邮箱发生改变时，重写Ldap邮箱字段')
		_logger.info(u'当前邮箱地址是%s' % (self.email))
		if self.cuid == '/':
			return None
		_logger.info('change email set Ldap')
		if self.email: 
			con = self._get_ldap_connection()[0]
			try:
				mail = self.res_email or self.email
				dn = "mail=%s,%s" % (mail,self._get_ldap_basedn()[0])
				new = {'mail':self.email.encode('utf-8')}
				old = {'mail':' '}

				ldif = modlist.modifyModlist(old,new)
				con.modify_s(dn,ldif)
			except ldap.LDAPError,e:
				_logger.error(u'%s' % e.message)
				return False
			finally:
				con.unbind_s()
		else:
			raise UserError(u'用户邮箱不能设置为空,请重新修改保存!')
			return False

	#监控客户班级字段变化，重写Ldap
	@api.one
	@api.onchange('kehu_id')
	def fllow_kehuclass_change(self):
		_logger.info(u'当客户班级改变时，重写Ldap班级字段')
		_logger.info(u'当前客户关联班级字段是%s' % self.kehu_id.name)
		if self.cuid == '/':
			return None
		con = self._get_ldap_connection()[0]
		try:
			mail = self.res_email or self.email
			dn = "mail=%s,%s" % (mail,self._get_ldap_basedn()[0])
			#如果更换班级,修改Ldap对应的班级字段,否则设置为None
			new={}
			if self.kehu_id.class_number:
				new['roomNumber'] = self.kehu_id.class_number.encode('utf-8')
				old = {'roomNumber':' '}

				ldif = modlist.modifyModlist(old,new)
				con.modify_s(dn,ldif)
			else:
				new['roomNumber'] = 'None'.encode('utf-8')
				old = {'roomNumber':' '}

				ldif = modlist.modifyModlist(old,new)
				con.modify_s(dn,ldif)

		except ldap.LDAPError,e:
			_logger.error(u'注意%s' % e.message)
			raise UserError(u'您提前为此客户归属了班级，请悉知，并继续您的下一步')
			return False
		finally:
			con.unbind_s()
	
	#监控客户名字字段变化，重写Ldap
	@api.one
	@api.onchange('name')
	def fllow_name_change(self):
		_logger.info(u'当客户名字字段发生改变时，重写Ldap名字字段')
		_logger.info(u'当前客户名字字段是%s' % self.name)
		if self.cuid == '/':
			return None
		con = self._get_ldap_connection()[0]
		if self.name:
			try:
				mail = self.res_email or self.email
				dn = "mail=%s,%s" % (mail,self._get_ldap_basedn()[0])
				new = {'sn':self.name.encode('utf-8'),'cn':self.name.encode('utf-8')}
				old = {'sn':' ','cn':' '}

				ldif = modlist.modifyModlist(old,new)
				con.modify_s(dn,ldif)
			except ldap.LDAPError,e:
				_logger.error(u'%s' % e.message)
				return False
			finally:
				con.unbind_s()
			
	#监控客户电话字段变化，重写Ldap
	@api.one		
	@api.onchange('phone')
	def fllow_phone_change(self):
		_logger.info(u'当客户电话字段发生改变时，重写Ldap名字字段')
		_logger.info(u'当前客户电话字段是%s' % self.phone) 
		if self.cuid == '/':
			return None
		con = self._get_ldap_connection()[0]
		if self.phone:
			try:
				mail = self.res_email or self.email
				dn = "mail=%s,%s" % (mail,self._get_ldap_basedn()[0])
				new = {'telephoneNumber':self.phone.encode('utf-8')}
				old = {'telephoneNumber':' '}

				ldif = modlist.modifyModlist(old,new)
				con.modify_s(dn,ldif)
			except ldap.LDAPError,e:
				_logger.info(u'%s' % e.message)
			finally:
				con.unbind_s()

class SaleOrder(models.Model):
	_name = 'sale.order'
	_inherit = ['sale.order','mail.thread']


	html='''
	<html>
		<body>
			<p>This is A Test.</p>
		</body>
		</html>
	'''
	#Connect Ldap
	@api.one
	def _connect_ldap_configure(self):
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
				# Bind/authenticate with a user with apropriate rights to add objects
				con.simple_bind_s(ldap_args.get('ldap_binddn'),ldap_args.get('ldap_password'))
				return con
		else:
			raise ValidationError(u'Ldap配置发生错误，请联系您的管理员!')
			return False
		
	@api.one
	def _get_ldap_base(self):
		ldap_ids = self.env['ldap.configure'].search([('is_available','=',True)])
		ldapbase = None
		if len(ldap_ids) == 1:
			for rec in ldap_ids:
				ldapbase = rec.ldap_base
			else:
				_logger.info(u'要添加客户信息的基组是%s' % ldapbase)
				return ldapbase 
		else:		
			raise ValidationError(u'Ldap配置发生错误，请联系您的管理员!')
			return False

	#点击确认订单写Ldap账号信息
	@api.one
	def action_confirm(self): #--->sale.order-->button-->object.fuction()-->重载方法 重载，覆盖，隐藏，多态
		_logger.info(u'当确认订单时，写客户信息到LDAP')
		if self.partner_id:
			_logger.info(u'当前客户的编号%s' % self.partner_id.cuid)
			_logger.info(u'当前客户的姓名%s' % self.partner_id.name)
			_logger.info(u'当前客户的性别%s' % self.partner_id.res_sex)
			_logger.info(u'当前客户的身份证号%s' % self.partner_id.res_identity_id)
			_logger.info(u'当前客户的qq%s' % self.partner_id.res_qq)
			_logger.info(u'当前客户的email%s' % self.partner_id.res_email)
			_logger.info(u'当前客户的电话%s' % self.partner_id.phone)
			_logger.info(u'当前客户的班级名称%s' % self.partner_id.kehu_id.name)

			li = []
			product_list = ''
			#遍历订单行，过滤产品名称
			for line in self.order_line:
				if line.product_id.type == 'course':
					_logger.info('----------course-----------------')
					li.append(line.product_id.name.encode('utf-8'))
				if line.product_id.type == 'coupon':
					_logger.info('----------coupon-----------------')
			product_list = ';'.join(li)
			default_password = None
			ldap_ids = self.env['ldap.configure'].search([('is_available','=',True)])
			if len(ldap_ids) == 1:
				for rec in ldap_ids:
					default_password = rec.student_password
				else:
					_logger.info(u'客户默认密码属性值是%s' % default_password)
			else:
				raise UserError('无法获取LDAP默认密码，请联系您的管理员!')
				return False

			stuinfo = {}
			stuinfo['uid'] = self.partner_id.cuid.encode('utf-8')
			if self.partner_id.name:
				stuinfo['username'] = self.partner_id.name.encode('utf-8')
			else:
				stuinfo['username'] = None
			if self.partner_id.res_email:
				stuinfo['mail'] = self.partner_id.res_email.encode('utf-8')
			else:
				stuinfo['mail'] = None
			if default_password:
				stuinfo['userPassword'] = default_password.encode('utf-8')
			else:
				stuinfo['userPassword'] = None
			if self.partner_id.res_identity_id:
				stuinfo['memberOfGroup'] = self.partner_id.res_identity_id.encode('utf-8')
			else:
				stuinfo['memberOfGroup'] = None
			if self.partner_id.phone:
				stuinfo['telephoneNumber'] = self.partner_id.phone.encode('utf-8')
			else:
				stuinfo['telephoneNumber'] = None
			if self.partner_id.kehu_id:
				stuinfo['roomNumber'] = self.partner_id.kehu_id.class_number.encode('utf-8')
			else:
				stuinfo['roomNumber'] = 'None'.encode('utf-8')
			if product_list:
				stuinfo['description'] = product_list
			else:
				stuinfo['description'] = []
			try:
				stuinfo['employmentState'] = self.partner_id.employment_state.encode('utf-8')
			except:
				stuinfo['employmentState'] = 'ia'.encode('utf-8')

			#查找学生条目，不存在则增加学生条目，否则则给出提示信息--->写学生信息到Ldap
			self.__search_ldap_entry(**stuinfo)
			'''#确认订单的时候，发送须知邮件-->发邮件
			kwargs = {}
			kwargs['name'] = self.partner_id.name.encode('utf-8')
			if self.partner_id.res_email:
				kwargs['email'] = self.partner_id.res_email.encode('utf-8')
			if product_list:
				kwargs['products'] = product_list
			if kwargs.has_key('email') and kwargs.has_key('products'):
				self.__send_email_student(**kwargs)'''
	
		return super(SaleOrder,self).action_confirm()

	@api.one
	def __send_email_student(self,**kw):
		from jinja2 import Environment,FileSystemLoader
		mail_mail_obj = self.env['mail.mail']

		import os
		BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR,"templates")))
		template = env.get_template('student.html')

		ctx = {
			'name':kw.get('name'),
			'products':kw.get('products'),
		}
		vals = {
			'subject':u'须知邮件',
			'body_html':template.render(ctx),
			'email_from':'@@@@@@@@@@@@@@',
			'email_to':kw.get('email'),
		}
		mail = mail_mail_obj.create(vals)
		mail.send()

	@api.one
	def __add_ldap_entry(self,**kw):		
		_logger.info(u'Enter into __add_ldap_entry')
		_logger.info(u'基组%s' % self._get_ldap_base()[0])
		l = self._connect_ldap_configure()[0]

		attrs = {}
		try:
			dn = "mail=%s,%s" % (kw.get('mail'),self._get_ldap_base()[0])
			attrs['objectClass'] = ['inetOrgPerson','mailUser','shadowAccount','amavisAccount','perfectInfo']
			attrs['uid'] = kw.get('uid')
			attrs['accountStatus'] = 'active'
			if kw.get('username'):
				attrs['cn'] = attrs['sn'] = kw.get('username')
			if kw.get('mail'):
				attrs['mail'] = kw.get('mail')
			if kw.get('userPassword'):
				attrs['userPassword'] = kw.get('userPassword')
			if kw.get('telephoneNumber'):
				attrs['telephoneNumber'] = kw.get('telephoneNumber')
			if kw.get('memberOfGroup'):
				attrs['memberOfGroup'] = kw.get('memberOfGroup')
			if kw.get('roomNumber'):
				attrs['roomNumber'] = kw.get('roomNumber')
			if not len(kw.get('description')) ==0:
				attrs['description'] = kw.get('description')
			if kw.get('employmentState'):
				attrs['employmentState'] =  kw.get('employmentState')

			ldif = modlist.addModlist(attrs)
			l.add_s(dn,ldif)
		except ldap.LDAPError,e:
			_logger.error(u'%s' % e.message)
			return False
		else:
			return True
		finally:
			l.unbind_s()

	# 确认订单的时，ldap用mail与uid做判断用户重复, 同一个用户会进行复写，不同则报错
	@api.one
	def __update_ldap_entry(self,kw,attribute):
		l = self._connect_ldap_configure()[0]
		dn = "mail=%s,%s" % (kw.get('mail'),self._get_ldap_base()[0])

		del kw['username'],kw['uid'],kw['userPassword'],kw['mail']
		del attribute['cn'],attribute['sn'],attribute['objectClass'],attribute['userPassword'],attribute['uid'],attribute['mail']

		update_att = []

		for field in kw:
			value = kw[field]
			if attribute.has_key(field) and value:
				tup = (ldap.MOD_REPLACE, field, kw[field])
				update_att.append(tup)
				continue
			if not attribute.has_key(field) and value:
				tup = (ldap.MOD_ADD, field, kw[field])
				update_att.append(tup)
				continue
			if attribute.has_key(field) and ((kw[field] == None) or (not value)):
				tup = (ldap.MOD_DELETE, field, attribute[field])
				update_att.append(tup)
				continue
		try:
			l.modify_s(dn,update_att)
		except ldap.LDAPError,e:
			_logger.error(u'%s' % e.message)
		finally:
			l.unbind_s()


	@api.one
	def __search_ldap_entry(self,**kw):
		_logger.info(u'Enter into __search_ldap_entry')
		_logger.info(u'基组%s' % self._get_ldap_base()[0])

		l = self._connect_ldap_configure()[0]
		try:
			baseDN = "%s" % self._get_ldap_base()[0]
			searchScope = ldap.SCOPE_SUBTREE
			#None表示搜索所有属性,['cn']表示只搜索cn属性
			retrieveAttributes = None
			#设置过滤属性
			if self.partner_id.res_email:
				searchFilter = "(mail=%s)" % kw.get('mail')
			else:
				raise ValidationError(u'请填写客户邮箱!')
				return False

			ldap_result = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
			result_type, result_data = l.result(ldap_result, 0)

			if len(result_data) != 0:
				result_user = result_data[0][1]
				if result_user['uid'][0] == kw['uid']:
					self.__update_ldap_entry(kw,result_user)
					return True
				else:
					_logger.warning(u'当前客户账号信息更新入Ldap!')
					error = "此邮箱已被客户'%s'作为账号使用，请确认客户是否重复创建，联系您的管理员获得帮助" % result_user['cn'][0]
					raise ValidationError(error)
					return None
			else:
				_logger.info(u'写客户账号信息到Ldap')
				if self.__add_ldap_entry(**kw):
					_logger.info('add ldap entry succfully!')		
				else:
					_logger.info('add ldap entry failed!')
				return None
		except ldap.LDAPError,e:
			print e.message
			return False
		finally:
			pass
			l.unbind_s()

#添加产品分类字段
class ProductTemplate(models.Model):
	_name = 'product.template'
	_inherit = 'product.template'

	def _get_product_template_type(self, cr, uid, context=None):
		 return [('consu', 'Consumable'), ('service', 'Service'),('course',u'课程'),('coupon',u'优惠券')]
		 #return [('course',u'课程'),('coupon',u'优惠券')]
	
	type = fields.Selection(default='course')

#sale.orer.line
class SaleOrderLineObj(models.Model):
	_name = 'sale.order.line'
	_inherit = 'sale.order.line'

    #price_unit = fields.Float(readonly=True,compute='_compute_price_unit',store=True,)

	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		if not self.order_id.partner_id:
			raise ValidationError(u'请先选择销售订单客户!')
		return super(SaleOrderLineObj,self).product_id_change()

'''     
        #计算单价
        #@api.one
        #@api.depends('product_id')
        #def _compute_price_unit(self):
        #    product = self.product_id.with_context(
        #        lang=self.order_id.partner_id.lang,
        #        partner=self.order_id.partner_id.id,
        #        quantity=self.product_uom_qty,
        #        date=self.order_id.date_order,
        #        pricelist=self.order_id.pricelist_id.id,
        #        uom=self.product_uom.id
        #    )
        #
        #    self._compute_tax_id()
        #
        #    if self.order_id.pricelist_id and self.order_id.partner_id:
        #        self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)'''


if __name__ == '__main__':
	import os 
	print os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


