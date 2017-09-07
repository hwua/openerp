#-*- coding:utf-8 

import logging

from openerp import models,fields,api,_
from openerp.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)


#工资邮件发送模板
class RecruitmentinformationTemplate(models.Model):
    _name = 'recruitment.information'
    _inherit = ['recruitment.information','mail.thread']
    _description = u'招聘需求模型'

    #只要该网关接收到邮件，便会建立关联模型，执行关联代码，
    #只有审批用户回复邮件，才能触发目标模型的关联信号
    subject = fields.Char(string=u'招聘需求',readonly=True,compute='_compute_email_subject')
    subject2 = fields.Char(string=u'招聘需求',readonly=True,compute='_compute_email_subject2')
    body_html = fields.Html(string=u'消息内容',readonly=True,compute='_compute_email_body')
    body_value = fields.Html(string=u'消息内容',readonly=True,compute='_compute_email_value')
    center_state = fields.Char(default=" ",)

    statelist = fields.Char(string=u'状态',readonly=True,compute='_compute_statelist')
    @api.one
    @api.depends('state')
    def _compute_statelist(self):
        if self.state == 'draft':
            self.statelist = u'草稿'
        elif self.state == 'wait':
            self.statelist = u'处理中'
        elif self.state == 'done':
            self.statelist = u'己完成'
        elif self.state == 'feedback':
            self.statelist = u'反馈中'
        elif self.state == 'off':
            self.statelist = u'关闭'
        elif self.state == 'refuse':
            self.statelist = u'拒绝'
        else:
            pass

    shenqingreasonlist = fields.Char(string=u'申请理由',readonly=True,compute='_compute_shenqingreasonlist')
    @api.one
    @api.depends('shenqingreasonlist')
    def _compute_shenqingreasonlist(self):
        if self.shenqingreason == 'extends':
            self.shenqingreasonlist = u'扩大编制'
        elif self.shenqingreason == 'vacancy':
            self.shenqingreasonlist = u'岗位空缺'
        elif self.shenqingreason == 'supplement':
            self.shenqingreasonlist = u'离职补充'
        elif self.shenqingreason == 'reserve':
            self.shenqingreasonlist = u'储备人员'
        elif self.shenqingreason == 'other':
            self.shenqingreasonlist = u'其他'
        else:
            pass
######################################这里是邮箱后缀的名字。。。。。上
    @api.one
    def _compute_email_subject(self):
        self.subject = u'招聘需求/%s' % (str(self.id))
    @api.one
    def _compute_email_subject2(self):
      self.subject2 =  u'招聘需求/%s' % (str(self.id))

    @api.one
    def send_email(self,**kw):
        mail_mail_obj = self.env['mail.mail']
        mail = mail_mail_obj.create(kw)
        mail.send()

#发送电子邮件,,,这里的函数会用到action.py文件中。提交审批用到
#调用了这个方法
    def send_recruitment_email(self,email_from,email_to,email_cc=None,tag=None):
        _logger.info(u'发送邮件的主题:%s' % self.subject)
        _logger.info(u'从%s发送电子邮件给%s' %  (email_from,email_to))
        vals = {'subject':self.subject,'body_html':self.body_html,'email_from':email_from,'email_to':email_to,'reply_to':self.shenqingresuser.email}
        self.send_email(**vals)

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #写HTML格式化布局
    @api.one
    def _compute_email_body(self):

        self.body_html = u'''
                <html lang="en">
                <head>
                    <meta charset="utf-8"/>
                </head> 
<body>                
<table border="1" cellspacing="0" cellpadding="5" width="700" style="font-size:16px;font-weight:bold;color:#000;font-family:'Microsoft YaHei';border-collapse:collapse;" >
    <tr style="text-align:center;font-weight:bold;font-size:32px;"  bgcolor="#84c1ff" >
        <td colspan="8">招聘需求</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"   >申请人</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"   >申请日期</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >申请部门</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >申请岗位</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >所属中心HR</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >申请理由</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >需求人数</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >薪酬预算</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >主要工作职责</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >任职资格</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >要求到岗时间</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >招聘天数</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >到期时间</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >状态</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >扣分值</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >加分值</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >理由</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >备注</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
</table>
</body>
</html>

''' % (self.shenqingresuser.name,str(self.shenqingstartdate),self.shenqingdepartment_id.name,
        self.shenqinggangwei,self.zhipaiuser.name,self.shenqingreasonlist,self.xuqiurenshu,
        self.wagesyusuan,self.workduty,self.workqualifications,self.yaoqiudate,self.zhaorendays,
        self.lasttime,self.statelist,self.koufenterm,self.jiafenterm,self.reasontext,self.beizhu)


#写HTML格式化布局
    @api.one
    def _compute_email_value(self):

        self.body_html = u'''
                <html lang="en">
                <head>
                    <meta charset="utf-8"/>
                </head> 
<body>                
<table border="1" cellspacing="0" cellpadding="5" width="700" style="font-size:16px;font-weight:bold;color:#000;font-family:'Microsoft YaHei';border-collapse:collapse;" >
    <tr style="text-align:center;font-weight:bold;font-size:32px;"  bgcolor="#84c1ff" >
        <td colspan="8">招聘需求</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"   >申请人</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"   >申请日期</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >申请部门</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >申请岗位</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >所属中心HR</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >申请理由</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >需求人数</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >薪酬预算</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >主要工作职责</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >任职资格</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >要求到岗时间</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >招聘天数</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >到期时间</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >状态</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >扣分值</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >加分值</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20">%s</td>
    </tr>
    <tr style="text-align:center;">
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >理由</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20"  >备注</td>
        <td style="border-right:1px solid #000;border-bottom:1px solid #000;" width="200"  height="20" >%s</td>
    </tr>   
</table>
</body>
</html>

''' % (self.shenqingresuser.name,str(self.shenqingstartdate),self.shenqingdepartment_id.name,
        self.shenqinggangwei,self.zhipaiuser.name,self.shenqingreasonlist,self.xuqiurenshu,
        self.wagesyusuan,self.workduty,self.workqualifications,self.yaoqiudate,self.zhaorendays,
        self.lasttime,self.statelist,self.koufenterm,self.jiafenterm,self.reasontext,self.beizhu)