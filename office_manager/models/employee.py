# -*- coding: utf-8 -*-
import base64
import ldap
from openerp import models, fields, api, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import ValidationError

import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)
class EmployeeMassageId(models.Model):
    # fetchmail.server，和对应的ir.model，新建信息
    _name = 'employee.id'
    _description = u'入职消息ID'
    _order = 'msg_id desc,id desc'
    _inherit = ['mail.thread','ir.needaction_mixin']

class osRole(models.Model):
    _name = 'hr.employee.os'
    name = fields.Char('角色名')
    o_id = fields.Integer('角色ID')

    # 同步所有未存档员工账号信息至ldap
    def update_users_role(self, cr, uid, context=None):
        employees = self.pool.get('hr.employee').search(cr, SUPERUSER_ID, [('active','=',True),('role','!=',False)],context=context)
        for employee in employees:
            self.pool.get('hr.employee').update_ldap(cr, SUPERUSER_ID, employee, context=context)

class officeManager(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'ir.needaction_mixin']

    role = fields.Many2many('hr.employee.os', 'hr_employee_os_rel', 'id', 'o_id',string='OS权限', track_visibility='onchange')
    # 将员工信息作为依据在之后的入职中建立账号
    create_mail = fields.Boolean(string=u'是否创建账号')
    default_password = fields.Char(string=u'初始密码', readonly=True)

    survey_questions = fields.Many2many('survey.survey', 'hr_employee_survey_rel', 'id', 'sid',string='测试问卷')

    # 显示人数
    @api.model
    def _needaction_count(self, domain=None):
        if domain:
            return self.search_count(domain or [])

    # 保存按钮
    @api.multi
    def action_save(self):
        val = {
            'image': self.image,
            'name': self.name,
            'department_id': self.department_id.id,
            'parent_id': self.parent_id.id,
            'coach_id': self.coach_id.id,
            'hr_worktime_from': self.hr_worktime_from,
            'company_id': self.company_id.id,
            'create_mail': self.create_mail
        }

        if self.id:
            employee = self.write(val)
        else:
            employee = self.create(val)

        rid = self._context.get('active_id',False)
        if rid:
            self.env['recruitment.information'].browse(rid).write({
                'employee_id': self.id
                })

        return {'type': 'ir.actions.act_window_close'}

    # 重置按钮
    def action_reset(self, cr, uid, ids , context=None):
        for employee in ids:
            self.unlink(cr, uid, employee, context)
        return {'type': 'ir.actions.act_window_close'}

    # 弹出框用来建立账号
    @api.multi
    def want_approval(self):
        if self.department_id.os_department_id == 0:
            raise ValidationError('此部门缺少OS部门术语,请更换部门,或者联系管理员')
        if self.test_ldap() == False:
            raise ValidationError('此公司的ldap出现错误,重试或者检查ldap配置')

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('office_manager.act_hr_employee_set_approval_confirm')
        form_view_id = imd.xmlid_to_res_id('office_manager.view_hr_employee_set_approval_confirm_form')

        result = {
                'res_id': False,
                'name': action.name,
                'type': action.type,
                'view_type': 'form',
                'view_model': 'form',
                'res_model': action.res_model,
                'views': [(form_view_id, 'form')],
                'views_id': form_view_id,
                'target': 'new',
                'context': {
                    'default_first_name': self.hr_englishname,
                    'default_company_id': self.company_id.id if self.company_id else False
                }
            }

        return result

    # 获得ldap链接
    def connect(self, conf):
        try:
            uri = 'ldap://%s:%d' % (conf.ldap_server, conf.ldap_server_port)
            con = ldap.initialize(uri)
            if conf.ldap_tls:
                con.start_tls_s()
            ldap_binddn = conf.ldap_binddn or ''
            ldap_password = conf.ldap_password or ''
            con.simple_bind_s(ldap_binddn.encode('utf-8'), ldap_password.encode('utf-8'))
        except ldap.INVALID_CREDENTIALS:
            _logger.error('LDAP bind failed.')
        except ldap.LDAPError, e:
            _logger.error('An LDAP exception occurred: %s', e)
        return con or False

    state = fields.Selection([('draft','待审核'),('underway','审核中'),('ready','待到岗'),('exam','入职考试')],string='审批状态', track_visibility='onchange')

    # def notify_perso_domain(self, cr, uid, ids, context=None):
    #     res = {}
    #     res['domain'] = {}
    #     group1, res_id1 = self.pool.get('ir.model.data').get_object_reference(cr, SUPERUSER_ID, 'base', 'group_hr_user')
    #     group2, res_id2 = self.pool.get('ir.model.data').get_object_reference(cr, SUPERUSER_ID, 'base', 'group_hr_manager')

    #     accounts = self.pool.get('res.users').search(cr, SUPERUSER_ID, [('groups_id','=',[res_id1,res_id2])], context=context)
    #     accounts = list(reversed(accounts))
    #     res['domain']['notify_person'] = [('id', 'in', accounts)]
    #     return res

    # notify_person = fields.Many2one('res.users', string='通知人', help='通常是账号开通申请的发件人', required=True)
    approvers_line = fields.One2many('hr.employee.approvers', 'a_id', track_visibility='onchange')

    #因为源码onchange写在view，所以@api.onchange无效，重写此函数
    def onchange_department_id(self, cr, uid, ids, department_id, context=None):
        value = {'parent_id': False}
        department = self.pool.get('hr.department').browse(cr, uid, department_id, context)
        value['parent_id'] = department.manager_id.id
        # 修改部门后删除审批人
        commands = []
        for eid in ids:
            employee = self.pool.get('hr.employee').browse(cr, uid, eid, context)
            commands = [(2, line_id.id) for line_id in employee.approvers_line]#删除主从链接关系，删除内容
            value['approvers_line'] = commands
            if employee.state=='underway':
                value['state'] = 'draft'
        return {'value': value}

    #测试ldap连接是否成功
    def test_ldap(self, employee=None):
        con = False
        if employee:
            for conf in employee.company_id.ldaps:
                try:
                    con = self.connect(conf)
                except:
                    pass
            return con or False
        else:
            for conf in self.company_id.ldaps:
                try:
                    con = self.connect(conf)
                except:
                    pass
            return con or False

    @api.one
    @api.constrains('department_id')
    def set_approval(self):
        if self.department_id:
            for info in self:
                department = info.department_id
                series = department.series
                commands = [(2, line_id.id, False) for line_id in info.approvers_line]
                if series == 0:
                    while department:
                        if department.manager_id.user_id.id != False:
                            vals = (0, 0, {
                            'a_id': info.id,
                            'approver': department.manager_id.id,
                            })
                            # if vals not in commands:
                            commands.append(vals)#添加主从链接关系
                        department = department.parent_id
                if series > 0:
                    for num in range(0, series):
                        if department.manager_id.user_id.id != False:
                            vals = (0, 0, {
                            'a_id': info.id,
                            'approver': department.manager_id.id,
                            })
                            # if vals not in commands:
                            commands.append(vals)#添加主从链接关系
                        department = department.parent_id
                info.write({
                    'approvers_line' : commands
                    })

    #更新ldap端字段
    @api.multi
    def update_ldap(self, employee_id):
        employees = self.env['hr.employee'].browse(employee_id)

        for employee in employees:
            # OS权限角色
            osrole = []
            for roles in employee.role:
                rid = roles.o_id
                osrole.append(str(rid))

            #上级邮箱
            manager = employee.department_id.manager_id.user_id if employee.department_id.manager_id.user_id else None

            searchFilter = "mail=%s" % (employee.user_id.email or employee.user_id.login)
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = ['objectclass']

            for conf in employee.company_id.ldaps:#遍历账号所属公司ldap配置，向LDAP修改objectClass、中文名、OS权限、
                con = self.connect(conf)
                con.protocal_version = ldap.VERSION3
                ldap_result_id = con.search(conf.ldap_base, searchScope, searchFilter, retrieveAttributes) 
                result_type, result_data = con.result(ldap_result_id, 0) 
                objectclass = result_data[0][1]['objectClass']
                objectclass.append('perfectInfo')

                atts = {
                    'objectclass': list(set(objectclass)),
                    'chineseName': employee.name.encode('utf-8') or None,
                    'osRole': osrole or None,
                    'superior' : (manager.email.encode('utf-8') or manager.login.encode('utf-8')) if manager else None,
                    'departmentNumber': str(employee.department_id.os_department_id) or None,
                }

                dn = "%s,%s" % (searchFilter, conf.ldap_base)
                update_att = []
                for att in atts:
                    if att != None:
                        tup = (ldap.MOD_REPLACE, att, atts[att])
                        update_att.append(tup)
                try:
                    con.modify_s(dn,update_att)
                except ldap.LDAPError,e:
                    _logger.error(u'%s' % e.message)
                finally:
                    con.unbind_s()

    # 发送审批邮件至审批人，把“被审批员工id-收件审批人id-yes/no“加密为base64密文，作为回复内容
    # 新增fetchmail.server，和对应的ir.model和ir.actions.server
    # ir.actions.server代码为：
    #       message = self.pool['mail.message'].search(cr, uid, [('model','=','employee.id'),('res_id','=',obj.id)],context=context)
    #       self.pool['hr.employee'].set_pass_by_mail(cr, uid, message[0], context=context)
    @api.one
    def start_approval(self):
        for approver in self.approvers_line:
            info = str(self.id) + '-' + str(approver.name.id) + '-' + 'through'
            body_yes = base64.encodestring(info)

            info = str(self.id) + '-' + str(approver.name.id) + '-' + 'notthrough'
            body_no = base64.encodestring(info)

            subject = u"""新员工%s入职申请，请审批""" % (self.name or '')
            body = u"""
                <!DOCTYPE html>
                <html>  
                <head>
                  <style type="text/css"> 
                    body { 
                        font: normal 11px auto "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
                        padding: 0;
                        margin: 0;
                    }
                    table {
                        width: 700px;
                        padding: 0;
                        margin: 0 4 0 4;
                    }
                    caption {
                        padding: 0 0 5px 0;
                        width: 700px;
                        font: italic 11px "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
                        text-align: right;
                    }
                    th {
                        font: bold 11px "Trebuchet MS", Verdana, Arial, Helvetica, sans-serif;
                        color: #4f6b72;
                        border-right: 1px solid #C1DAD7;
                        border-bottom: 1px solid #C1DAD7;
                        border-top: 1px solid #C1DAD7;
                        letter-spacing: 2px;
                        text-transform: uppercase;
                        text-align: left;
                        padding: 6px 6px 6px 12px;
                    }
                    tr {
                        background: #E6EAE9;
                    }
                    td {
                        border-right: 1px solid #C1DAD7;
                        border-bottom: 1px solid #C1DAD7;
                        background: #fff;
                        font-size:11px;
                        padding: 6px 6px 6px 12px;
                        color: #4f6b72;
                    }
                    a {
                        font-size: 27px;
                    }
                </style>
                </head>
                <body>
                  <a href="mailto:@@@@@@@@@@@@@@@@@@@@@@@@?subject=employee/%s&amp;body=Send**this**code**to**say**YES:((%s))">通过</a>
                  <a href="mailto:@@@@@@@@@@@@@@@@@@@@@@@@?subject=employee/%s&amp;body=Send**this**code**to**say**NO:((%s))">拒绝</a>
                  <table>
                      <tr>
                        <th>员工编号</th>
                        <th>邮箱</th>
                        <th>职位级别</th>
                        <th>姓名</th>
                        <th>公司</th>
                        <th>所属中心</th>
                        <th>部门</th>
                        <th>岗位</th>
                        <th>直接上级</th>
                      </tr>
                    <tbody>
                      <tr>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                      </tr>
                    </tbody>
                  </table>
                  <table class="table"> 
                      <tr>
                        <th>试用期基本工资</th>
                        <th>试用期岗位津贴</th>
                        <th>试用期岗位绩效</th>
                        <th>试用期小计</th>
                        <th>转正基本工资</th>
                        <th>转正岗位津贴</th>
                        <th>转正岗位绩效</th>
                        <th>转正小计</th>
                        <th>拟入职时间</th>
                        <th>转正日期</th>
                        <th>备注</th>
                        <th>内部推荐</th>
                        <th>如认识我司在职或离职员工，姓名及关系</th>
                      </tr>
                    <tbody>
                      <tr>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                        <td>%s</td>
                      </tr>
                    </tbody>
                  </table>
                </body>
                </html>
                  """ % (
                    self.id,
                    body_yes,
                    self.id,
                    body_no,
                    self.hr_number or '',
                    self.work_email or '',
                    self.hr_level or '',
                    self.name or '',
                    self.company_id.name or '',
                    self.center_id.name or '',
                    self.department_id.name or '',
                    self.job_id.name or '',
                    self.coach_id.name or '',
                    self.basewages or '',
                    self.gangweijintiebasewages or '',
                    self.gangweijixiaobasewages or '',
                    self.basewages + self.gangweijintiebasewages + self.gangweijixiaobasewages or '',
                    self.basewageshou or '',
                    self.gangweijintiebasewageshou or '',
                    self.gangweijixiaobasewageshou or '',
                    self.basewageshou + self.gangweijintiebasewageshou + self.gangweijixiaobasewageshou or '',
                    self.hr_worktime_from or '',
                    self.hr_worktime_zheng or '',
                    self.notes or '',
                    self.recommendation or '',
                    self.referrer or '',
                    )

            try:
                vals = {'subject':subject,'body_html':body,'email_from':self.env.user.email,'email_to':approver.name.email or approver.name.login,'reply_to':False}
                mail_mail_obj = self.env['mail.mail']
                mail = mail_mail_obj.create(vals)
                mail.send()
            except:
                continue

        self.state = 'underway'

    #直接通过
    def pass_approval(self, cr, uid, ids, context=None):
        for eid in ids:
            employee = self.browse(cr, uid, eid)
            employee.update({
                'state': 'ready',
                })

    # 审批通过，强转密文为数组，修改对应审批人
    def set_pass_by_mail(self, cr, SUPERUSER_ID, message, context=None):
        message = self.pool['mail.message'].browse(cr, SUPERUSER_ID, message, context=context)
        stri = message.body
        s_state = stri.find('((')
        s_end = stri.find('))')
        express = base64.decodestring(stri[s_state+2 : s_end])
        info = express.split('-')

        employee = self.pool['hr.employee'].browse(cr, SUPERUSER_ID, int(info[0]), context=context)
        approver_id = int(info[1])
        if employee.approvers_line:
            con = True
            for approver in employee.approvers_line:
                if approver.name.id == approver_id:
                    approver.state = info[2]

                if approver.state != 'through':
                    con = False
                    break

            if con == True:
                employee.update({
                    'state': 'ready',
                    })

    # 弹出框用来发送测试邮件
    @api.multi
    def give_notice(self, spare_mail):
        if not self.survey_questions:
            raise ValidationError('请先勾选需要发送的测试')
        if not self.user_id:
            raise ValidationError('此员工没有设置对应账号，请联系管理员')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('office_manager.act_recruitment_survey_notice')
        form_view_id = imd.xmlid_to_res_id('office_manager.view_recruitment_survey_notice_form')

        result = {
            'res_id': False,
            'name': action.name,
            'type': action.type,
            'view_type': 'form',
            'view_model': 'tree',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'views_id': form_view_id,
            'target': 'new',
            'context': {
                'default_mail_to': self.id,
                'user': self.user_id.id,
                'name': self.name,
                'survey_ids': self.survey_questions.ids
            }
        }

        return result

    # 处于入职测验状态的员工,大部分字段被隐藏,使用这个弹出框查看所有页面
    @api.multi
    def see_all(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hr.open_view_employee_list_my')
        form_view_id = imd.xmlid_to_res_id('hr.view_employee_form')

        result = {
            'res_id': self.id,
            'name': action.name,
            'type': action.type,
            'view_type': 'form',
            'view_model': 'tree',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'views_id': form_view_id,
        }

        return result

    # @api.one
    # def start_leaving(self):
    #     raise ValidationError('尽请期待')

# 这里是账号信息，放在按钮上
from openerp.osv import fields, osv
class EmployeeUserInfo(osv.Model):
    _inherit = 'hr.employee'

    @api.multi
    def action_go_to_user(self):
        user = self.mapped('user_id')
        form_view_id = self.env['ir.model.data'].xmlid_to_res_id('base.view_users_form')
        result = {
            'name': '账号',
            'type': 'ir.actions.act_window',
            'views': [(form_view_id, 'form')],
            'target': 'new',
            'res_model': 'res.users',
            'flags': {'form': {'action_buttons': True}}
        }
        if user:
            result['res_id'] = user.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def _get_user_info(self, cr, uid, ids, field_name, arg, context=None):
        ui = self.pool.get('survey.user_input')

        res = dict(map(lambda x: (x,0), ids))
        for employee in self.browse(cr, uid, ids, context):
            if field_name == 'user_info_mail':
                res[employee.id] = employee.user_id.email
            if field_name == 'user_info_create_time':
                res[employee.id] = employee.user_id.create_date
            if field_name == 'user_info_login_time':
                res[employee.id] = employee.user_id.login_date
            if field_name == 'user_info_role':
                g = ''
                for group in employee.user_id.groups_id:
                    if not group.category_id:
                        g += '<p style="color:green;margin:0;padding:0">' + group.name + '</p>'
                res[employee.id] = g

            # one2many字段需要双向对应，即employee_id与input_id，没有employee模型参与，故使用function计算
            if field_name == 'survey_ids':
                res[employee.id] = self.pool["survey.user_input"].search(cr, uid, [('create_uid', '=', employee.user_id.id),('state','=','done')])

        return res

    _columns = {
        'user_info_mail': fields.function(_get_user_info, type='char', string='用户账号'),
        'user_info_create_time': fields.function(_get_user_info, type='char', string='创建时间'),
        'user_info_login_time': fields.function(_get_user_info, type='char' , string='登录时间'),
        'user_info_role': fields.function(_get_user_info, type='html', string='权限'),
        'survey_ids': fields.function(_get_user_info, type='one2many', relation='survey.user_input', string='已完成')
    }

    def create(self, cr, uid, vals, context=None):
        vals['state'] = 'draft'
        vals['active'] = False
        return super(EmployeeUserInfo, self).create(cr, uid, vals)