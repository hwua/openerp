# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError
import openerp.http as http
import requests
import json
import datetime
import time
_logger = logging.getLogger(__name__)

class ExaminationStudent(models.Model):
	_name ='examination.student'

	name = fields.Char(string='学生考试信息')
	testid = fields.Char(string='学生试卷id')
	post_time = fields.Datetime(string='提交时间')
	mail = fields.Char(string='邮箱')
	score = fields.Char(string='分数')
	url_result = fields.Char(string='考试结果')
	teacher = fields.Char(string='老师')
	studentname = fields.Many2one('res.partner', string=u"学员姓名")
	classtoaccount_id = fields.Many2one('classto.account', string=u"学生班级", auto_join=True, ondelete='cascade',)

class ExaminationInformation(models.Model):
	_name ='examination.information'

	name = fields.Char(string='考试信息',compute='_change_name')
	@api.one
	def _change_name(self):
		self.name = self.title
	paperid = fields.Char(string='试卷ID')
	papername = fields.Char(string='课程名称')
	Examinationinformation_id = fields.Many2one('classto.account', string=u"学生班级", auto_join=True, ondelete='cascade',)
	title = fields.Char(string='试卷名称')
	post_student = fields.Char(string='考试人数')
	user = fields.Char(string='出卷人')
	location = fields.Char(string='地区')
	teacher = fields.Char(string='老师')
	averg_score = fields.Char(string='平均分')
	total_student = fields.Char(string='学生总数')
	sid = fields.Char(string='课程')
	url_view = fields.Char(string='试题内容')
	url_preview = fields.Char(string='试卷预览')
	url_student = fields.Char(string='学生名单')
	url_detail = fields.Char(string='考试详情')

	def update_examination(self, cr, uid, ids, context=None):
		allclassid = []
		teacherclassid = []
		erpclassid = []
		studentclassid = [] 
		addclassid = [] 
		testidcld = [] 
		testiderp = [] 
		testidadd = [] 
		examinationstumodel = self.pool.get('examination.student')
		examinationstu_ids = examinationstumodel.search(cr, uid, [('testid', '!=', None)])
		examinationstu_id = examinationstumodel.browse(cr, uid, examinationstu_ids,context)
		for per in examinationstu_id:
			testiderp.append(per.testid)

		examinationmodel = self.pool.get('examination.information')
		examination_ids = examinationmodel.search(cr, uid, [('paperid', '!=', None)])
		examination_id = examinationmodel.browse(cr, uid, examination_ids,context)
		for per in examination_id:
			erpclassid.append(per.paperid)
		examinationjson = json.loads(requests.get('http://cloud.oracleoaec.com/cloud/openapi/exams').content)
		for k, v in examinationjson.items():#k,获得的所有ID。
			allclassid.append(k)
			if v.get("class", None) == u'老师考试班级':
				teacherclassid.append(k)
		studentclassid = list(set(allclassid).difference(set(teacherclassid)))
		addclassid = list(set(studentclassid).difference(set(erpclassid)))
		classtoaccountmodel = self.pool.get('classto.account')
		classtoaccount_ids = classtoaccountmodel.search(cr, uid, [('id', '!=', None)])
		classtoaccount_id = classtoaccountmodel.browse(cr, uid, classtoaccount_ids,context)
		respartnermodel = self.pool.get('res.partner')
		url_rr = 'http://cloud.oracleoaec.com/cloud/openapi/exams/class/'
		session = requests.Session()
		for k, v in examinationjson.items():#k,获得的所有ID。
			for per in classtoaccount_id:
				if per.class_number == v.get("class", None):
					if k in addclassid:
						vls={
							'paperid': k,
							'papername': v.get("cid", None),
							'url_preview': v.get("url_preview", None),
							'url_detail': v.get("url_detail", None),
							'title': v.get("title", None),
							'post_student': v.get("post_student", None),
							'user': v.get("user", None),
							'location': v.get("location", None),
							'teacher': v.get("teacher", None),
							'averg_score': v.get("averg_score", None),
							'url_student': v.get("url_student", None),
							'url_view': v.get("url_view", None),
							'total_student': v.get("total_student", None),
							'sid': v.get("sid", None),
							'Examinationinformation_id': per.id,
							}
						examinationmodel.create(cr,uid,vls)
			newurl_rr = url_rr + k
			rr = session.post(newurl_rr)
			hhjson = json.loads(rr.content)
			if type(hhjson)==dict:
				for hhk,hhv in hhjson.items():
					testidcld.append(hhk)
					testidadd = list(set(testidcld).difference(set(testiderp)))
					if len(testidadd)!=0:
						if hhk in testidadd:
							respartner_ids = respartnermodel.search(cr, uid, [('res_email', '=', hhv.get("mail", None))])
							if not respartner_ids:
								_logger.info("erp没有该邮箱学员信息")
							else:
								respartner_id = respartnermodel.browse(cr, uid, respartner_ids,context)
								_logger.info("_______________________%s"%respartner_id[0].id)
								vls={
									'testid': hhk,
									'post_time': time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(float(hhv.get("post_time", None)))),
									'mail': hhv.get("mail", None),
									'score': hhv.get("score", None),
									'name': hhv.get("name", None),
									'teacher': hhv.get("teacher", None),
									'url_result': hhv.get("url_result", None),
									'studentname': respartner_id[0].id,
									'classtoaccount_id': respartner_id[0].kehu_id.id,
									}
								examinationstumodel.create(cr,uid,vls)
			else:
				continue

class ManagerceterExpend(models.Model):
	_name = 'managercenter.activity'
	_inherit = ['mail.thread']

	name = fields.Char(string='活动',compute='_change_name')
	@api.one
	def _change_name(self):
		self.name = self.managercenteractivity_id.class_number
	studentname = fields.Many2one('res.partner', string=u"学员姓名",track_visibility='onchange')
	activitytime = fields.Char(string='时间',track_visibility='onchange')
	activitydate = fields.Date(string='日期',track_visibility='onchange')
	activitybei = fields.Char(string='备注',track_visibility='onchange')
	activitynumber = fields.Char(string='平均分',track_visibility='onchange')
	activityurl = fields.Char(string='活动链接',track_visibility='onchange')
	activityadress = fields.Char(string='区域',track_visibility='onchange')
	classteacher = fields.Many2one('hr.employee',string='班级管理员',track_visibility='onchange')
	activitytype = fields.Char(string='活动类型',track_visibility='onchange')
	activitycenter = fields.Char(string='中心',track_visibility='onchange')
	managercenteractivity_id = fields.Many2one('classto.account', string=u"学生班级", auto_join=True, ondelete='cascade',track_visibility='onchange')
	# shenqingreason = fields.Selection([
	# ('extends',u'扩大编制'),
	# ],string = u'申请理由' ,track_visibility=True)

class ManagerceterExpendInterview(models.Model):
	_name = 'managercenter.interview'
	_inherit = ['mail.thread']

	@api.constrains('studentname','name')
	def _set_name(self):
		self.name = '%s'%(self.studentname.name)

	name = fields.Char(string='访谈记录',compute="_set_name")
	teachername = fields.Many2one('hr.employee', string=u"职业规划师")
	studentname = fields.Many2one('res.partner', string=u"学员姓名",track_visibility='onchange')
	interviewtime = fields.Date(string='日期',track_visibility='onchange')
	interviewtype = fields.Char(string='沟通方式',default="一对一",track_visibility='onchange')
	interviewpre = fields.Char(string='沟通前问题',track_visibility='onchange')
	interviewresult = fields.Text(string='沟通结果',track_visibility='onchange')
	interviewfeedneed = fields.Char(string='需要反馈点',track_visibility='onchange')
	interviewfeedjie = fields.Date(string='反馈日间截点',track_visibility='onchange')
	interviewfeedselt = fields.Boolean(string='是否需要再沟通',track_visibility='onchange')
	interviewfeedteach = fields.Boolean(string='是否反馈任课老师',track_visibility='onchange')
	interviewbei = fields.Char(string='备注',track_visibility='onchange')
	managercenterinterview_id = fields.Many2one('classto.account', string=u"学生班级", auto_join=True, ondelete='cascade',track_visibility='onchange')

class InheritClassaccounttt(models.Model):
	_inherit = 'classto.account'

	Examinationinformation_ids = fields.One2many('examination.information','Examinationinformation_id',string='考试信息')
	managercenterinterview_ids = fields.One2many('managercenter.interview','managercenterinterview_id',string='访谈记录')
	managercenteractivity_ids = fields.One2many('managercenter.activity','managercenteractivity_id',string='活动')
	interview_records = fields.One2many('interview_record','interview_id',string='活动')

class InheritCourseAccountTot(models.Model):
	_inherit = 'course.account.to'

	time =  fields.Date(string='代课时间起')
	timeto =  fields.Date(string='代课时间止')

class InheritResPartnermanager(models.Model):
	_inherit = 'res.partner'

	resinterview_ids = fields.One2many('managercenter.interview','studentname',string='访谈记录')
	resactivity_ids = fields.One2many('managercenter.activity','studentname',string='活动')
	resinformation_ids = fields.One2many('examination.student','studentname',string='考试信息')
	resattendance_ids = fields.One2many('classto.attendance.line','name',string='考勤信息',readonly=True)

class InheritInterviewRecord(models.Model):
	_inherit = 'interview_record'

	studentname = fields.Many2one('res.partner', string=u"学员姓名")
	interview_id = fields.Many2one('classto.account', string=u"学员班级")

