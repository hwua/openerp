# -*- coding: utf-8 -*-
import logging
from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

class ClasstoMailTemplate(models.Model):
	_name = 'classto.email.template'

	name = fields.Char(string=u'标题', required=True)
	mode = fields.Boolean(string=u'查看代码')
	body_text = fields.Text(string=u'内容')
	body_editor = fields.Html(string=u'内容', sanitize=False, required=True)
	email_from = fields.Char(string=u'发件人')

	@api.onchange('body_text')
	def _check_body_editor(self):
		self.body_editor = self.body_text

	@api.onchange('body_editor')
	def _check_body_text(self):
		self.body_text = self.body_editor