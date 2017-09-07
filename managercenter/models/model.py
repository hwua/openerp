#-*- coding:utf-8 -*-
import logging
from openerp import models, fields, api
from openerp.exceptions import ValidationError

import ldap
import ldap.modlist as modlist

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class ResPartnerClass(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'

	kehu_id = fields.Many2one('classto.account',string=u'班级名称',help=u'显示客户班级名称', track_visibility='onchange')

class SaleOrderClass(models.Model):
	_name = 'sale.order'
	_inherit = 'sale.order'

	sale_classid = fields.Many2one('classto.account',string=u'班级名称',help=u'显示关联客户的班级名称')

	#从关联客户计算订单班级名称字段
	@api.one
	@api.onchange('sale_classid')
	def _compute_kehu_banji(self):
		if self.partner_id:
			res_ids = self.env['res.partner'].search([('name','=',self.partner_id.name)])
			for res_obj in res_ids:
				res_obj.write({'kehu_id':self.sale_classid.id})

	#当关联客户改变时，清空班级名称
	@api.onchange('partner_id')
	def _compute_partner_id(self):
		if self.sale_classid:
			self.sale_classid = False
		
class LdapConfiger(models.Model):
	_name = 'ldap.configure'

	ldap_server = fields.Char(string=u'LDAP服务器地址',required=True,)
	ldap_binddn = fields.Char(string=u'LDAP binddn',required=True,)
	ldap_base = fields.Char(string=u'LDAP 基节点',required=True,)
	ldap_server_port = fields.Char(string=u'LDAP 服务器端口',required=True)
	ldap_password = fields.Char(string=u'LDAP 密码',required=True,help=u'输入LDAP服务器对应的明文密码')
	student_password = fields.Char(string=u'客户默认密码',required=True,help=u'Ldap密码属性默认值')
	is_available = fields.Boolean(string=u'是否可用',help=u'设置当前Ldap配置是否可用')

	#创建基组
	@api.one
	def create_base_group(self):
		_logger.info('Enter into create_base_group')

		con = ldap.open(self.ldap_server)
		con.protocol_version = ldap.VERSION3
		con.set_option(ldap.OPT_REFERRALS, 0)
		# Bind/authenticate with a user with apropriate rights to add objects
		con.simple_bind_s(self.ldap_binddn,self.ldap_password)

		try:
			dn = "%s" % self.ldap_base
			attrs = {}
			attrs['objectclass'] = ['organization']
			attrs['o'] = self.ldap_base.split(',')[0].split('=')[1].encode('utf-8')
			
			ldif = modlist.addModlist(attrs)
			con.add_s(dn,ldif)
		except ldap.LDAPError,e:
			_logger.error(u'%s' % e.message)
			raise ValidationError(u'创建基组出错,详细描述:%s!' % e.message.get('desc'))
		else:
			raise ValidationError(u'创建基组成功!')
			_logger.info(u'创建基组成功!')
		finally:
			# Its nice to the server to disconnect and free resources when done
			con.unbind_s()






