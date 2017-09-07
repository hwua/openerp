# -*- coding: utf-8 -*-
import logging
import time
import re
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)

class ClassToMailTemplate(models.Model):
	_name = 'classto.account'
	_inherit = ['classto.account','mail.thread']

	email_template = fields.Many2one('classto.email.template', string=u'邮件模板')

	subject = fields.Char(string=u'标题',readonly=True,compute='_get_template_subject')
	body = fields.Html(string=u'内容',readonly=True,compute='_get_template_body')
	email_from = fields.Char(string=u'发件人',readonly=True,compute='_get_mail_value')
	email_time = fields.Html(string=u'发件时间',readonly=True)
	email_new_time = fields.Text(string=u'发件历史',readonly=True)

	def _get_mail_value(self):
		self.email_from = self.email_template.email_from

	@api.onchange('email_template')
	def _get_template_body(self):
		self.body = self.email_template.body_editor

	@api.onchange('email_template')
	def _get_template_subject(self):
		self.subject = self.email_template.name

	@api.multi
	def _classto_get_email(self):
		if self.subject == False:
			raise ValidationError('请选择邮件模板')
		if self.email_from == False:
			raise ValidationError('请为此邮件模板添加发件人')
		if self.body == False:
			raise ValidationError('此模板为空')
		else:
			email_to = {}
			for mail in self.kehu_ids:
				#if (mail.res_email == False) or mail.res_email.isspace():
				#	raise ValidationError('群发邮件不允许邮箱的填写错误，请检查该学生邮箱：%s'%(mail.name.encode('utf-8')))
				if mail.res_email:
					email_to[mail.res_email] =  mail.name
			if not email_to:
				raise ValidationError('此班级没有任何学生')
			return email_to

	@api.one
	def send_email(self,**kw):
		mail_mail_obj = self.env['mail.mail']

		mail = mail_mail_obj.create(kw)
		mail.send()

	@api.multi
	def send_loan_email(self):
		email_to = self._classto_get_email()
		for email, name in email_to.iteritems():
			body = self.body.replace('[name]',name)
			vals = {'subject':self.subject,'body_html':body,'email_from':self.email_from,'email_to':email}
			self.send_email(**vals)

		self.email_new_time = str(time.strftime("%Y-%m-%d",time.localtime(time.time()))) + '--%s'%(self.subject)

		if self.email_time:
			self.email_time = self.email_new_time + '<br/>' + self.email_time
		else :
			self.email_time = self.email_new_time

# 	def action_next(self,cr,uid,ids,context=None):

# 		self.pool.get('classto.account')
# 		record_ids = context and context.get('active_ids', []) or []
# 		# return {
# 		# 		'type': 'ir.actions.act_window',
# 		# 		'view_type': 'form',
# 		# 		'view_mode': 'form',
# 		# 		'res_id':self.pool["classto.account"],
# 		# 		'res_model': 'class.email.template.action',
# 		# 		'target': 'new',
# 		# 		}

# class ClasstoMailTemplateAction(models.Model):
# 	_name = 'class.email.template.action'

# 	email_template = fields.Many2one('classto.email.template', string=u'邮件模板')


#class CheckPartnerEmail(models.Model):
#	_inherit = 'res.partner'

#	@api.multi
#	@api.constrains('res_email')
#	def check_match_email(self):
#		if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", self.res_email) == None:
#			raise ValidationError(u'请填写正确邮箱，不允许空格、中文、全角符号！邮箱不明请以此格式输入：比如@@@@@@@@@@@@@2，（1999年12月12日8点12分30秒 + @@@@@@@@@@@）')
