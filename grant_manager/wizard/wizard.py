# -*- coding: utf-8 -*-

import datetime
from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_split,DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from openerp.exceptions import ValidationError,UserError

class GrantWizard(osv.osv_memory):
    _name = 'grant.wizard'

    _columns = {
        'portal_id': fields.many2one('res.groups', required=True, string='Portal'),
        'user_ids': fields.one2many('grant.wizard.user', 'wizard_id', string='Users'),
    }

    def _default_portal(self, cr, uid, context):
        portal_ids = self.pool.get('res.groups').search(cr, uid, [('is_portal', '=', True)], context=context)
        return portal_ids and portal_ids[0] or False

    _defaults = {
        'portal_id': _default_portal,
    }

    # 以客户的发票操作历史，查找其负责的会计，并略过管理员（可能我们后台操作过发票）
    def get_account_by_partner(self, cr, uid, partner_id, context=None):
        users = []
        orders = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', partner_id),('amount_grant', '!=', False)])
        for order in orders:
            order_info = self.pool.get('sale.order').browse(cr, uid, order, context=context)
            invoices = self.pool.get('account.invoice').search(cr, uid, [('origin', '=', order_info[0].name)], context=context)
            for invoice in invoices:
                invoice_info = self.pool.get('account.invoice').browse(cr, uid, invoice, context=context)
                aa = str(invoice_info.message_ids)
                for message in invoice_info.message_ids:
                    if message.create_uid.id != 1:
                        users.append(message.create_uid.id)
        try:
            reduce(lambda x,y:x if y in x else x + [y], [[], ] + users)
            return users[0]
        except:
            return False

    # 默认放入批处理的客户，班主任仅可操作自己的学生
    def onchange_portal_id(self, cr, uid, ids, portal_id, context=None):
        res_partner = self.pool.get('res.partner')
        partner_ids = context and context.get('active_ids') or []
        contact_ids = set()
        user_changes = []
        for partner in res_partner.browse(cr, SUPERUSER_ID, partner_ids, context):
            for contact in (partner.child_ids or [partner]):
                if contact.id not in contact_ids:
                    # 多选后，班主任仅能看见自己的学生，可去除，对邮件无影响，见106行
                    if contact.kehu_id.class_leader.user_id.id == uid and contact.sale_grant_state != 'none':
                        contact_ids.add(contact.id)
                        user_changes.append((0, 0, {
                            'partner_id': contact.id,
                            'grant_change_sale_number_wizard': contact.grant_change_sale_number_wizard,
                            'kehu_id': contact.kehu_id,
                            'state': contact.sale_grant_state,
                            'amount_grant_rate': contact.amount_grant_rate,
                            'account_user': self.get_account_by_partner(cr, uid, contact.id, context),
                            }))
        return {'value': {'user_ids': user_changes}}


    def action_update(self, cr, uid, ids, context=None):
        #修改客户的总期数
        result = self.action_apply(cr, uid, ids, context)
        #之后更新其订单的总期数
        if result:
            self.update_sale_amount(cr, uid, ids, context)
            self.send_grant_mail(cr, uid, ids, context)
        else:
            raise ValidationError('操作失败')
        
    def action_apply(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        portal_user_ids = [user.id for user in wizard.user_ids]
        try:
            self.pool.get('grant.wizard.user').action_apply(cr, uid, portal_user_ids, context)        
            return {'type': 'ir.actions.act_window_close'}
        except:
            return False

    # 将客户相应做修改
    @api.one
    def update_sale_amount(self):
        for partner in self.user_ids:
            if (partner.partner_id.sale_grant_state == 'draft') and (partner.partner_id.grant_change_sale_number_wizard > 0):
                orders = self.env['sale.order'].search([('partner_id','=',partner.partner_id.id),('amount_grant_state','=','draft')])
                timestamp = datetime.datetime.strftime(datetime.datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
                for order in orders:
                    order.amount_grant_number = partner.partner_id.grant_change_sale_number_wizard
                    routine = order.amount_grant / order.amount_grant_number
                    order.update({
                        'amount_grant_rate': partner.amount_grant_rate,
                        })
                    last = routine - (order.amount_grant * (order.amount_grant_rate / 100.0))

                    pay = last if (order.amount_grant_number == 1) else routine

                    order.update({
                        'amount_grant_surplus_next': pay,
                        'amount_grant_surplus_all': order.amount_grant * (1 - order.amount_grant_rate/100),
                        'amount_grant_state': 'in',
                        'amount_grant_confirm': '第1/' + str(order.amount_grant_number) + '期▶' + str(pay) + '￥',
                        })
                    partner.partner_id.sale_order_grant_message = str(order.name) + ':' + order.amount_grant_confirm

                partner.partner_id.sale_grant_state = 'in'

    @api.one
    def send_email(self,**kw):
        mail_mail_obj = self.env['mail.mail']
        mail = mail_mail_obj.create(kw)
        mail.send()

    # 邮件准备
    # 如果补助发起人不再只是班主任，提醒邮件将会把多个班级的学生将分为若干个班主任发至其班主任
    @api.multi
    def send_grant_mail(self):
        user_name = self.env['hr.employee'].search([('user_id','=', self.env.user.id)])
        subject = u'''【%s%s】已将以下申请补贴的客户移入发放期'''% (self.env.user.name, user_name[0].name)
        email_to_leader = {}
        email_to_account = {}
        for partner in self.user_ids:
            if (partner.state == 'draft') and (partner.grant_change_sale_number_wizard > 0):
                pa = {}
                orders = self.env['sale.order'].search([('partner_id','=',partner.partner_id.id),('amount_grant_state','in',('draft','in','done'))])
                count = 0
                for order in orders:
                   count = order.amount_grant

                student = [
                        partner.partner_id.name,
                        partner.partner_id.kehu_id.name,
                        count,
                        partner.grant_change_sale_number_wizard,
                    ]

                if email_to_leader.has_key(partner.partner_id.kehu_id.class_leader.user_id.email):
                    email_to_leader[partner.partner_id.kehu_id.class_leader.user_id.email].append(student)
                else:
                    email_to_leader[partner.partner_id.kehu_id.class_leader.user_id.email] = [student]

                if email_to_account.has_key(partner.account_user.email):
                    email_to_account[partner.account_user.email].append(student)
                else:
                    email_to_account[partner.account_user.email] = [student]

        if email_to_leader:
            for leader,partners in email_to_leader.items():
                body = u'''以下客户已进入补贴发放期，请在每期补贴发放后于ERP更新补贴状态'''
                body += u'''<br/>
                    <table cellspacing="0" cellpadding="0" style="border:0.5px solid #000;">
                        <tr style="text-align:center;font-weight:bold;">
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="200">姓名</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">班级</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">补贴总额</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">补贴期数</td>
                        </tr>
                '''
                color = True #行变色
                for fields in partners:
                    if color:
                        body +=  u'''
                                    <tr style="text-align:center;" bgcolor="#ffcc33">
                                    '''
                        color = False
                    else:
                        body +=  u'''
                                    <tr style="text-align:center;" bgcolor="#ffffcc">
                                        '''
                        color = True
                    for value in fields:
                        body +=  u'''
                                    <td style="border:1px solid #000;">%s</td>
                                    '''% (value)
                    body += u'''</tr>'''
                body +=  u'''
                        </table>
                        '''
                try:
                    vals = {'subject':subject,'body_html':body,'email_from':self.env.user.email,'email_to':leader}
                    self.send_email(**vals)
                except:
                    continue

        if email_to_account:
            for account,partners in email_to_account.items():
                body = u'''以下客户已进入补贴发放期，请在每期补贴发放后于ERP更新补贴状态'''
                body += u'''<br/>
                    <table cellspacing="0" cellpadding="0" style="border:0.5px solid #000;">
                        <tr style="text-align:center;font-weight:bold;">
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="200">姓名</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">班级</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">补贴总额</td>
                            <td style="border:0.5px solid #000;" bgcolor="#99ccff" width="160">补贴期数</td>
                        </tr>
                '''
                color = True #行变色
                for fields in partners:
                    if color:
                        body +=  u'''
                                    <tr style="text-align:center;" bgcolor="#ffcc33">
                                    '''
                        color = False
                    else:
                        body +=  u'''
                                    <tr style="text-align:center;" bgcolor="#ffffcc">
                                        '''
                        color = True
                    for value in fields:
                        body +=  u'''
                                    <td style="border:1px solid #000;">%s</td>
                                    '''% (value)
                    body += u'''</tr>'''
                body +=  u'''
                        </table>
                        '''
                try:
                    vals = {'subject':subject,'body_html':body,'email_from':self.env.user.email,'email_to':account}
                    self.send_email(**vals)
                except:
                    continue
        else:
            raise ValidationError('操作无效，无可操作客户，或请填写客户的总期数')

# 单独使用tree视图+editable属性会造成修改无效的问题，所以在批量和原模型之间加入额外的一个模型，达成效果
class GrantWizardUser(osv.osv_memory):
    _name = 'grant.wizard.user'

    _columns = {
        'wizard_id': fields.many2one('grant.wizard', string='Wizard', required=True),
        'partner_id': fields.many2one('res.partner', string='姓名'),
        'grant_change_sale_number_wizard': fields.integer(string='总期数', size=240),
        'kehu_id': fields.many2one('classto.account',string='班级'),
        'state' : fields.selection([('none','无'),('draft','待确认'),('in','发放中'),('done','已完毕'),('other','异常')], string='补贴进度'),
        'amount_grant_rate' : fields.float(string='税点(%)', requird=True, digits=(16, 3),default = 5.0),
        'account_user': fields.many2one('res.users',string='相关会计')
    }

    # 这里检查客户状态，完成状态和无补贴的客户无法修改总期数
    def check_sale_grant_state(self, cr, uid, ids, partner_id, grant_change_sale_number_wizard, context=None):
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        if partner.sale_grant_state == 'draft' and  grant_change_sale_number_wizard <= 0:
            values = {
                'amount_grant_rate': partner.amount_grant_rate,
            }
            return {'value': values}
        if partner.sale_grant_state in ('in','done','other'):
            values = {
                'grant_change_sale_number_wizard':  partner.grant_change_sale_number_wizard,
                'amount_grant_rate': partner.amount_grant_rate,
            }
            return {'value': values}

    #确认后修改值
    def action_apply(self, cr, uid, ids, context=None):
        for wizard_user in self.browse(cr, SUPERUSER_ID, ids, dict(context, active_test=False)):
            if wizard_user.partner_id.grant_change_sale_number_wizard != wizard_user.grant_change_sale_number_wizard:
                wizard_user.partner_id.write({
                    'grant_change_sale_number_wizard': wizard_user.grant_change_sale_number_wizard,
                    'amount_grant_rate': wizard_user.amount_grant_rate,
                    })

    # 筛选出会计,本公司的会计
    def get_account_partner(self, cr, uid, context):
        res = {}
        res['domain'] = {}
        user = self.pool.get('res.users').browse(cr, uid,uid, context=context)
        groups = self.pool.get('res.groups').search(cr, uid, [('name','in',['Accountant','Billing','Adviser'])], context=context)
        accounts = self.pool.get('res.users').search(cr, uid, [('groups_id','=',groups),('company_id','=',user.company_id.id)], context=context)
        accounts = list(reversed(accounts))
        res['domain']['account_user'] = [('id', 'in', accounts)]
        return res

    # 下拉列表仅显示操作过客户的会计
    # def get_account_partner(self, cr, uid, partner_id, context=None):
    #     users = []
    #     res = {}
    #     res['domain'] = {}
    #     orders = self.pool.get('sale.order').search(cr, uid, [('partner_id', '=', partner_id),('amount_grant', '!=', False)])
    #     for order in orders:
    #         order_info = self.pool.get('sale.order').browse(cr, uid, order, context=context)
    #         invoices = self.pool.get('account.invoice').search(cr, uid, [('origin', '=', order_info[0].name)], context=context)
    #         for invoice in invoices:
    #             invoice_info = self.pool.get('account.invoice').browse(cr, uid, invoice, context=context)
    #             aa = str(invoice_info.message_ids)
    #             for message in invoice_info.message_ids:
    #                 if message.create_uid.id != 1:
    #                     users.append(message.create_uid.id)
    #     try:
    #         reduce(lambda x,y:x if y in x else x + [y], [[], ] + users)
    #         return [('id','in',users)]
    #     except:
    #         return False