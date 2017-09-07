# -*- coding: utf-8 -*-
import ldap
import re
import cStringIO
import pycurl
import json
import hashlib
import urllib
from openerp import models, fields, api, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from random import choice
import string

import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

class set_approval(models.TransientModel):
    # 弹出框原本可以直接使用res.user，但是模型本身不含password字段,所以定义新模型
    _name = 'hr.employee.set.approval.confirm'

    first_name = fields.Char(string="英文名", required=True)
    last_name = fields.Char(string="中文姓", required=True)
    account = fields.Char(string="账号", required=True)
    domainName = fields.Char(string="域名", required=True)
    mail = fields.Char(string="邮箱", required=True)
    password = fields.Char(string="密码", required=True)
    company_id = fields.Many2one('res.company', string="公司", required=True)

    @api.multi
    # 检查邮箱地址存在
    def check_email(self):
        url="httpshttpshttpshttps%s" % (self.mail.encode('ascii'))
        cbuffer = cStringIO.StringIO()
        curl = pycurl.Curl()
        # 忽略证书
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEFUNCTION, cbuffer.write)
        curl.perform()
        result = cbuffer.getvalue()
        body = json.loads(result)
        cbuffer.close()
        if body['status'] == 'success':
            return 'success'
        return 'failed'

    def get_password(self):
        passwd = []
        while (len(passwd) < 9):
            if len(passwd) < 4:
                passwd.append(choice(string.ascii_uppercase))
            elif len(passwd) < 5:
                passwd.append(choice(string.punctuation))
            elif len(passwd) < 9:
                passwd.append(choice(string.digits))
        return ''.join(passwd)

    # 拼接邮箱
    @api.onchange('first_name','last_name','company_id')
    def set_account(self):
        self.update({
            'first_name': re.sub('[^a-zA-Z]','',self.first_name).capitalize() if self.first_name else False,
            'last_name': re.sub('[^a-zA-Z]','',self.last_name).capitalize() if self.last_name else False
        })

        account = domainName = mail =''
        if self.first_name and self.last_name and self.company_id:
            for ldap in self.company_id.ldaps:
                ldap_base = eval("{'" + ldap.ldap_base.replace("=","':'").replace(',',"','") + "'}")
                if ldap_base.get('domainName',False):
                    account = self.first_name.lower() + '.' + self.last_name.lower()
                    domainName = ldap_base['domainName']
                    mail = account + '@' + domainName
                    break
                else:
                    continue

            self.update({
                    'account': account,
                    'domainName': domainName,
                    'mail': mail,
                    'password': self.get_password()
                    })

    # 建立本地账号
    @api.multi
    def new_user(self):
        open_user = self.env['res.users'].search([('login','=',self.mail)])
        close_user = self.env['res.users'].search([('login','=',self.mail),('active','=',False)])
        if open_user:
            return open_user[0].id
        elif close_user:
            close_user.active = True
            return close_user[0].id
        else:
            user_info = {
                'name': self.first_name + ' ' + self.last_name,
                'email': self.mail,
                'login': self.mail,
                'company_ids': {(4,self.company_id.id)},
                'company_id': self.company_id.id,
                'notify_email': 'none'
            }
            user = self.env['res.users'].create(user_info)
            return user.id if user else False

    # 建立新邮箱账号
    @api.multi
    def new_email(self):
        sign = hashlib.sha1(("%s+%s+%s" % (self.account, self.password, 'A8zru02G+y3zI9AyZtZG8w0UwTqGbbecujjGhmf8IJU='))).hexdigest()

        mkdir_str = {
            'domainName': self.domainName,
            'username': self.account,
            'newpw': self.password,
            'confirmpw': self.password,
            'cn': self.first_name + ' ' + self.last_name,
            'first_name': self.last_name,
            'last_name': self.first_name,
            'preferredLanguage': 'zh_CN',
            'mailQuota': 1024,
            'oldMailQuota': 1024,
            'submit_add_user': '添加',
            'sign': sign
        }

        url = "httpshttpshttpshttpshttps"

        cbuffer = cStringIO.StringIO()
        curl = pycurl.Curl()
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        curl.setopt(pycurl.POSTFIELDS, urllib.urlencode(mkdir_str))
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEFUNCTION, cbuffer.write)
        curl.perform()

        result = cbuffer.getvalue()
        body = json.loads(result)
        cbuffer.close()
        if body['status'] == 'success':
            return 'success', None
        return 'failed', body['message']

    # 补全账号信息，修改sn为姓，增加givenName为名，把公司ldap_filter中的邮件组添加进账号
    @api.multi
    def new_email_completion(self):
        searchFilter = "mail=%s" % (self.mail)
        memberOfGroup = []
        for conf in self.company_id.ldaps:#遍历账号所属公司ldap配置，向LDAP修改objectClass、中文名、OS权限、
            con = self.env['hr.employee'].connect(conf)
            con.protocal_version = ldap.VERSION3

            regex = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}\b", re.IGNORECASE)
            mails = re.findall(regex, conf.ldap_filter)

            atts = {
                'sn': self.last_name.encode('utf-8'),
                'givenName': self.first_name.encode('utf-8'),
            }

            dn = "%s,%s" % (searchFilter, conf.ldap_base)
            update_att = []
            for k,v in atts.iteritems():
                tup = (ldap.MOD_REPLACE, k, v)
                update_att.append(tup)
            update_att.append((ldap.MOD_ADD, 'memberOfGroup', list(map(lambda x:x.encode('utf-8'), mails))))

            try:
                con.modify_s(dn,update_att)
            except ldap.LDAPError,e:
                _logger.error(u'%s' % e.message)
            finally:
                con.unbind_s()
    
    @api.multi
    def new_encryption(self):
        user = {
            'objectClass': json.dumps(['inetOrgPerson','amavisAccount','mailUser'], ensure_ascii=False, encoding='UTF-8'),
            'mail': self.mail,
            'cn': self.first_name + ' ' + self.last_name,
            'uid': self.first_name.lower() + '.' + self.last_name.lower(),
            'sn': self.last_name,
            'accountStatus': 'active',
            'userPassword': self.password,
        }

        url = "httpshttpshttpshttpshttps"

        cbuffer = cStringIO.StringIO()
        curl = pycurl.Curl()
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        curl.setopt(pycurl.POSTFIELDS, urllib.urlencode(user))
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEFUNCTION, cbuffer.write)
        curl.perform()

        result = cbuffer.getvalue()
        body = json.loads(result)
        cbuffer.close()
        return body


    # 验证本地、ldap是否存在账号
    # 考虑员工复聘情况下需要恢复账号，加入active=False可以搜索到归档账号，另外情况新员工账号和已删除邮箱相同，这时无法判断是否为同一人，取消账号归档不是好方案，所以放弃复聘的功能
    # 写入user或者邮箱，如果出错，抛出自带异常
    @api.multi
    def action_save(self):
        eids = self._context.get('active_id','') 
        employee = self.env['hr.employee'].browse(eids)
        test = self.env['hr.employee'].test_ldap(employee)
        if test:
            status = self.check_email()
            if status == 'failed':
                user_id = self.new_user()

                if user_id:
                    employee.user_id = user_id

                    if employee.user_id:
                        email, message = self.new_email()
                        if email == 'failed':
                            raise ValidationError(message)
                        else:
                            self.new_email_completion()
                            self.new_encryption()
                            self.env['hr.employee'].update_ldap(eids)
                            employee.write({
                                'state': 'exam',
                                'active': True,
                                'work_email': self.mail,
                                'default_password': self.password,
                                })
                            # self.env['recruitment.survey.notice'].with_context({
                            #     'default_mail_to': self.id,
                            #     'user': user_id.id,
                            #     'name': employee.name,
                            #     'survey_ids': self.survey_questions.ids
                            #     }).notice_mail()
            else:
                raise ValidationError('邮箱地址已经存在')
        else:
            raise ValidationError('此公司的ldap出现错误,重试或者检查ldap配置')

class recruitment(models.Model):
    _inherit = 'recruitment.information'

    # 判断有无账号
    employee_id = fields.Many2one('hr.employee',string=u'员工',readonly=True)

    # 创建招聘状态的员工用作入职
    @api.multi
    def create_new_employee(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hr.open_view_employee_list_my')
        form_view_id = imd.xmlid_to_res_id('office_manager.view_employee_quick_form')

        result = {
                'res_id': self.employee_id.id if self.employee_id else False,
                'name': '预定义员工',
                'type': action.type,
                'view_type': 'form',
                'view_model': 'form',
                'res_model': action.res_model,
                'views': [(form_view_id, 'form')],
                'views_id': form_view_id,
                'target': 'new',
            }

        if not self.employee_id:
            result['context'] = {
                    'default_state': 'draft',
                    'default_name': self.username,
                    'default_department_id': self.shenqingdepartment_id.id if self.shenqingdepartment_id else False,
                    'default_parent_id': self.shenqingdepartment_id.manager_id.id if self.shenqingdepartment_id else False,
                    'default_coach_id': self.guangweishangji.id if self.guangweishangji else False,
                    'default_hr_worktime_from': self.hrgettime,
                    'default_company_id': self.shenqingdepartment_id.company_id.id if self.shenqingdepartment_id else False,
                    'default_create_mail': True,
                    'default_active': False
                }

        return result

class recruitmentSurveyNotice(models.TransientModel):
    _name = 'recruitment.survey.notice'
    
    def _set_subject(self):
        return ('%s，您的入职测试有未完成考卷，请尽快完成' % self._context.get('name','').encode('utf-8'))

    def _set_body(self):
        surveys = self.env['survey.survey'].browse(self._context.get('survey_ids',''))
        url = ''
        for survey in surveys:
            result = self.env['survey.user_input'].search([('create_uid', '=', self._context.get('user','')),('state', '=', 'done'),('survey_id','=',survey.id)])
            if not result:
                url += u"""
                        <tr>
                            <td style='border-right: 1px solid #C1DAD7;
                                    border-bottom: 1px solid #C1DAD7;
                                    background: #fff;
                                    font-size:11px;
                                    padding: 6px 6px 6px 12px;'>
                                %s
                            </td>
                            <td style='border-right: 1px solid #C1DAD7;
                                    border-bottom: 1px solid #C1DAD7;
                                    background: #fff;
                                    font-size:11px;
                                    padding: 6px 6px 6px 12px;'>
                                %s
                            </td>
                        </tr>
                        """% (survey.title, survey.public_url_html)

        body = u"""
            <!DOCTYPE html>
            <html>
                <body style='font: normal 11px auto "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif; padding: 0; margin: 0;'>
                    <table style='width: 700px; padding: 0; margin: 0 4 0 4; border-left: 1px solid #C1DAD7;'>
                        <tbody>
                            <tr>
                                <th colspan=2 style='font: bold 11px "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
                                        border-right: 1px solid #C1DAD7;
                                        border-bottom: 1px solid #C1DAD7;
                                        border-top: 1px solid #C1DAD7;
                                        letter-spacing: 2px;
                                        text-transform: uppercase;
                                        text-align: left;
                                        padding: 6px 6px 6px 12px;'>
                                    <h3>你好，%s：</h3>
                                    <p style="padding: 10px 20px;">您在ERP有部分测试没有完成</p>
                                </th>
                            </tr>
                            %s
                        </tbody>
                    </table>
                </body>
            </html>

            """ % (self._context.get('name',''),  url)

        return body

    subject = fields.Char(string="主题",default=_set_subject)
    mail_to = fields.Many2one('hr.employee', string="收件人", readonly=True)
    other_mail_to = fields.Char(string="备用收件人")
    body = fields.Html(string="内容",default=_set_body)


    @api.multi
    def notice_mail(self):
        vals = {'subject':self.subject,'body_html':self.body,'email_from':self.env.user.email,'email_to':self.mail_to.user_id.email or self.mail_to.user_id.login,'reply_to':False}
        try:
            mail_mail_obj = self.env['mail.mail']
            mail = mail_mail_obj.create(vals)
            mail.send()

            if self.other_mail_to:
                vals['email_to'] = self.other_mail_to
                mail2 = mail_mail_obj.create(vals)
                mail2.send()
        except:
            pass