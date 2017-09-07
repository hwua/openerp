# -*- coding: utf-8 -*-
import logging
import datetime
from openerp import models, fields, api
from openerp.exceptions import ValidationError

class Course(models.Model):
	_name="course.account"
	_description=u'课程管理'

	name = fields.Char(string="课程名称",required=True)
	course_type_number=fields.Char(string="课程类型编号")
	course_name_number=fields.Char(string="课程名称编号")
	course_type=fields.Char(string="课程类型")
	course_types=fields.Char(string="课程种类")
	lesson=fields.Integer(string="课时")
	describe=fields.Text(string="描述")

        	
