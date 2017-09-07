# -*- coding: utf-8 -*-
import logging
import time
from openerp import models, fields, api
from openerp.exceptions import ValidationError

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class ClassToMailWizard(models.Model):
	_name = 'tomail.wizard'

	_description = u'群发邮件'

	name = fields.Many2one('classto.email.template', string=u'邮件模板')

	checked_class = fields.Many2many('classto.account','classto_res_classto','classto_wizard_view_id','name', string=u'班级')

	body = fields.Html(readonly=True)

	@api.onchange('name')
	def check_email_body(self):
		if self.name:
			self.body = self.name.body_editor 

	@api.one
	def send_email(self,**kw):
		mail_mail_obj = self.env['mail.mail']
		mail = mail_mail_obj.create(kw)
		mail.send()

	@api.multi
	def send_loan_email(self):
		if self.name == False:
			raise ValidationError('请选择邮件模板')
		if self.name.email_from == False:
			raise ValidationError('请为此邮件模板添加发件人')
		if self.name.body_editor == False:
			raise ValidationError('此模板为空')
		else:
			for cl in self.checked_class:
				for mail in cl.kehu_ids:
					if mail.res_email:
						body = self.name.body_editor.replace('[name]',mail.name)
						vals = {'subject':self.name.name,'body_html':body,'email_from':self.name.email_from,'email_to':mail.res_email}
						self.send_email(**vals)

				cl.email_new_time = str(time.strftime("%Y-%m-%d",time.localtime(time.time()))) + '--%s'%(self.name.name)

				if cl.email_time:
					cl.email_time = cl.email_new_time + '<br/>' + cl.email_time
				else :
					cl.email_time = cl.email_new_time

	def default_get(self, cr,uid,fields,context=None):
		if context is None:
			context = {}
		res = super(ClassToMailWizard,self).default_get(cr,uid,fields,context)
		if context.get('active_model') == 'classto.account' and context.get('active_ids'):
			res['checked_class'] = context['active_ids']
		return res