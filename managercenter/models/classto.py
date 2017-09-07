# -*- coding: utf-8 -*-
import logging
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError

import ldap

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class Classto(models.Model):
	_name ='classto.account'
	_description = u'班级管理'
	_rec_name = 'class_number'
	_order = 'date1 desc'
	name = fields.Char(string = u'班级名称',required = True, track_visibility='onchange')
	class_number = fields.Char(string = u'班级编号', track_visibility='onchange')
	class_leader = fields.Many2one('hr.employee',string='班主任', track_visibility='onchange')
	core = fields.Many2one('coreto.account',string = u'中心名称', track_visibility='onchange')
	class_type = fields.Char(string = u'班级类型', track_visibility='onchange')
	class_statu = fields.Selection([('prep',u'预科'),('start',u'开班'),('graduation',u'毕业')],string = u'班级状态', track_visibility='onchange')
	remarks = fields.Char(string=u'备注', track_visibility='onchange')
	date1=fields.Date(string=u'开班日期', track_visibility='onchange')	
	date2=fields.Date(string=u'毕业日期', track_visibility='onchange')
	company = fields.Many2one('res.company',string='公司名称',required = True, track_visibility='onchange')
	curriculum=fields.Many2many('course.account','classto_account_course_account_rel','classto_account_id','course_account_id',string="课程表", track_visibility='onchange')

	kehu_ids = fields.One2many('res.partner','kehu_id',string=u'班级', track_visibility='onchange')

	@api.one
	def btn_ldap(self):
		ldap_ids = self.env['ldap.configure'].search([('is_available','=',True)])
		if len(ldap_ids) == 1:
			for rec in ldap_ids:
				_logger.info(u'LDAP服务器地址:%s'% rec.ldap_server)	
				_logger.info(u'LDAP binddn:%s' % rec.ldap_binddn)
				_logger.info(u'LDAP 基节点:%s' % rec.ldap_base)
				_logger.info(u'LDAP 服务器端口:%s' % rec.ldap_server_port)
				_logger.info(u'LDAP 密码:%s' % rec.ldap_password)
				_logger.info(u'客户默认密码:%s' % rec.student_password)
			return True
		else:
			raise ValidationError(u'Ldap配置发生错误，仅且只能配置一个生效!')
			return False



