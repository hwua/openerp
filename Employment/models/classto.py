# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)

class ClasstoChangePartnerStatuByClassStatu(models.Model):
	_name = 'classto.account'
	_inherit = ['classto.account', 'mail.thread']

	class_professional_planner = fields.Many2one('hr.employee',string="职业规划师", track_visibility='onchange')

	@api.one
	def update_partner_state(self):
		self.class_statu = 'graduation'
		for partner in self.kehu_ids:
			partner.employment_state = 'ne'

	@api.one
	def reset_partner_state(self):
		self.class_statu = 'start'
		for partner in self.kehu_ids:
			partner.employment_state = 'ia'