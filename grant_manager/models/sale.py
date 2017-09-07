# -*- coding: utf-8 -*-
import datetime
from openerp import api, fields, models, _
from openerp.exceptions import ValidationError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class SaleOrderGrantExpond(models.Model):
    _inherit = 'sale.order'

    amount_grant_number = fields.Integer(string='总期数',readonly=True)
    amount_grant_already_number = fields.Integer(string='已出期数',readonly=True)
    amount_grant_surplus_next = fields.Monetary(string='下期发放',readonly=True)
    amount_grant_surplus_all = fields.Monetary(string='剩余发放',readonly=True)
    amount_grant_rate = fields.Float(string=u'税点', requird=True, digits=(16, 3),readonly=True)
    amount_grant_confirm = fields.Char(string='下期发放情况',help='这是本期补助发放情况，双方全部确认后，即认为本次客户这正常获得补助',readonly=True)
    amount_grant_confirm_a = fields.Selection([('yes','已确认'),('no','未确认')],readonly=True)
    amount_grant_confirm_b = fields.Selection([('yes','已确认'),('no','未确认')],readonly=True)
    amount_grant_state = fields.Selection([('draft','待确认'),('in','发放中'),('done','已完毕'),('other','退费')],string='补贴进度',readonly=True)
    amount_grant_state_backup = fields.Selection([('draft','待确认'),('in','发放中'),('done','已完毕'),('other','退费')],string='补贴进度',readonly=True,help='用作在退款时备份补贴进度字段，可做撤销用')

    # 清空补贴金额以后，清空补贴相关字段
    @api.constrains('amount_grant','amount_grant_number')
    @api.onchange('amount_grant','amount_grant_number')
    def check_amount_grant(self):
        self.update({
            'amount_grant_already_number': 0,
            'amount_grant_surplus_next': 0.0,
            'amount_grant_confirm': False,
            'amount_grant_state':False,
            })
        self.partner_id.write({'sale_order_grant_message': False})
        if self.amount_grant == 0.0:
            self.update({
                'amount_grant_rate': 5.0,
                'amount_grant_surplus_all': 0.0,
                'amount_grant_confirm_a':False,
                'amount_grant_confirm_b':False,
                })
        elif self.amount_grant > 0.0:
            rate = self.amount_grant_rate if (self.amount_grant_rate != 0.0) else 5.0
            self.update({
                'amount_grant_rate': 5.0,
                'amount_grant_surplus_all': self.amount_grant - self.amount_grant * (rate / 100.0),
                'amount_grant_confirm_a':'no',
                'amount_grant_confirm_b':'no',
                })

    @api.onchange('amount_grant_number')
    def _check_amount_grant_number(self):
        if self.amount_grant_number > 0.0:
            self.check_amount_grant()
            self.amount_grant_surplus_all = self.amount_grant - self.amount_grant * (self.amount_grant_rate / 100.0)

    # 重载'确认销售'按钮，使点击时客户的补助状态随补助数值显示为'无'或者'带确认'
    @api.one
    def action_confirm(self):
        self.write({
            'amount_grant_confirm_a': 'no',
            'amount_grant_confirm_b': 'no'
            })
        if self.amount_grant == 0.0:
            self.partner_id.write({
                'sale_grant_state': 'none'
                })
        elif self.amount_grant > 0.0:
            self.amount_grant_surplus_all = self.amount_grant - self.amount_grant * (self.amount_grant_rate / 100.0)
            self.amount_grant_state = 'draft'
            self.partner_id.write({
                'sale_grant_state': 'draft'
                })
        return super(SaleOrderGrantExpond,self).action_confirm()

    # 重载'取消'按钮，使点击时客户的补助状态变为none,因为无论何种情况下，报价单状态这个字段始终为'无'
    # 取消当前订单时，还需要判断该用户是否有其他补贴在流程中，若存在，则不重置客户状态为'无'
    @api.multi
    def action_cancel(self):
        self.update({
            'amount_grant_state': False,
            })
        orders = self.env['sale.order'].search([('id','!=',self.id),('partner_id','=',self.partner_id.id),('amount_grant_state','in',('draft','in','done'))])
        if len(orders) == 0:
            self.partner_id.write({
                'sale_grant_state': 'none',
                'grant_change_sale_number_wizard': False,
                })
            self.check_amount_grant()

        return super(SaleOrderGrantExpond,self).action_cancel()

    # 当退费发起，先查询该客户是否有正常的订单，有则仅将本订单补贴状态异常，无则同时将客户补贴状态异常
    @api.multi
    def state_apply(self):
        self.amount_grant_state_backup = self.amount_grant_state
        self.write({'amount_grant_state':'other'})
        orders = self.env['sale.order'].search([('id','!=',self.id),('partner_id','=',self.partner_id.id),('amount_grant_state','in',('draft','in','done'))])
        if len(orders) == 0:
            self.partner_id.write({'sale_grant_state':'other'})
        return super(SaleOrderGrantExpond,self).state_apply()

    # 当退费发起，先查询该客户是否有正常的订单，有则仅将本订单补贴状态异常，无则同时将客户补贴状态异常
    @api.multi
    def state_sale_to(self):
        self.amount_grant_state = self.amount_grant_state_backup
        orders = self.env['sale.order'].search([('id','!=',self.id),('partner_id','=',self.partner_id.id),('amount_grant_state','in',('draft','in','done'))])
        if len(orders) == 0:
            self.partner_id.write({'sale_grant_state':self.amount_grant_state})
        return super(SaleOrderGrantExpond,self).state_sale_to()

    # 财务与班主任每一期点击确认，双方确认后，一期通过，直到最后一期完成
    @api.multi
    def _change_number_state(self):
        if self.amount_grant_confirm_a and (self.amount_grant_already_number < self.amount_grant_number):
            self.amount_grant_already_number += 1
            routine = self.amount_grant / self.amount_grant_number
            last = routine - (self.amount_grant * (self.amount_grant_rate / 100.0))
            timestamp = datetime.datetime.strftime(datetime.datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)

            # 确认全部已完成，订单'补贴进度'、客户'补贴进度'为完成，同时清空下次补贴和剩余补贴
            if self.amount_grant_already_number == self.amount_grant_number:
                self.update({
                    'amount_grant_state': 'done',
                    'amount_grant_surplus_next':0.0,
                    'amount_grant_surplus_all':0.0,
                    'amount_grant_confirm':'全' + str(self.amount_grant_already_number) + '/' + str(self.amount_grant_number) + '期▶全部完成于' + timestamp,
                    })
                self.partner_id.write({
                    'sale_grant_state': 'done',
                    'sale_order_grant_message': self.name + ':' + self.amount_grant_confirm,
                    })

            # 未完成最后一期，每期就会计算字段
            if self.amount_grant_already_number < self.amount_grant_number:
                if self.amount_grant_number == (self.amount_grant_already_number + 1) :
                    self.amount_grant_surplus_next = last
                    self.amount_grant_surplus_all = last
                else:
                    self.amount_grant_surplus_next = routine
                    self.amount_grant_surplus_all = self.amount_grant_surplus_all - self.amount_grant_surplus_next

                self.update({
                    'amount_grant_state': 'in',
                    'amount_grant_confirm_a': 'no',
                    'amount_grant_confirm_b': 'no',
                    'amount_grant_confirm': '第' + str(self.amount_grant_already_number + 1) + '/' + str(self.amount_grant_number) + '期▶' + str(self.amount_grant_surplus_next) + '￥▶上期' + timestamp + '完成',
                    })
                self.partner_id.sale_order_grant_message = self.name + ':' + self.amount_grant_confirm
    
    # 财务按钮动作
    @api.multi
    def change_already_number_by_a(self):
        self.amount_grant_confirm_a = 'yes'
        if self.amount_grant_confirm_a == self.amount_grant_confirm_b == 'yes':
            self._change_number_state()
        else:
            timestamp = datetime.datetime.strftime(datetime.datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
            self.amount_grant_confirm = '第' + str(self.amount_grant_already_number + 1) + '/' + str(self.amount_grant_number) + '期▶' + str(self.amount_grant_surplus_next) + '￥▶财务' + timestamp + '确认'
            self.partner_id.write({
                'sale_order_grant_message': self.name + ':' + self.amount_grant_confirm
                })


    #班主任按钮动作
    @api.multi
    def change_already_number_by_b(self):
        self.amount_grant_confirm_b = 'yes'
        if self.amount_grant_confirm_a == self.amount_grant_confirm_b == 'yes':
            self._change_number_state()
        else:
            timestamp = datetime.datetime.strftime(datetime.datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
            self.amount_grant_confirm = '第' + str(self.amount_grant_already_number + 1) + '/' + str(self.amount_grant_number) + '期▶' + str(self.amount_grant_surplus_next) + '￥▶班主任' + timestamp + '确认'
            self.partner_id.write({
                'sale_order_grant_message': self.name + ':' + self.amount_grant_confirm
                })

        #生成草稿付款单
        user = self.env.user.employee_ids
        pay_type = self.env['expense.type'].search([('name','=','学员补贴款')])
        ticket_type = self.env['invoice.type'].search([('name','=','内部票据')])
        did = False
        dmid = False
        try:
            for employee in self.user_id.employee_ids:
                department = employee.department_id
            did = department.id
        except:
            did = False

        try:
            for employee in self.user_id.employee_ids:
                department = employee.department_id
            dmid = department.manager_id.id
        except:
            dmid = False
        vals = {
        'leixing_sel' : 'c',
        'leixing' : self.env['email.type'].search([('name','=','学员生活补助费')]).id,
        'name': self.env.user.id,
        'department': did,
        'center': self.env.user.company_id.id,
        'chinese_name': user.name,
        'pay_danwei': self.partner_id.name,
        'pay_mode': 'zhuangzhang', 
        'department_manager': dmid,
        'pay_date': datetime.date.today(),
        'kaihu': self.bankaddress,
        'zhanghu': self.banknumber,
        'pay_ids': [((0, 0, {
            'pay_type': pay_type.id,
            'pay_money': self.amount_grant_surplus_next,
            'whether_ticket': 'Yes',
            'ticket_type': ticket_type.id,
            'pay_reason': '学员生活补贴',
            }))]
         }
        pay_account = self.env['pay.account'].create(vals)

from openerp.osv import fields,osv

class sale_order_loan_grant_schedule(osv.osv):
    _inherit = 'sale.order'
    
    def _amount_grant_schedule_number(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        for orders in self.browse(cr, uid, ids, context):
            res[orders.id] = str(orders.amount_grant_already_number) + '/' + str(orders.amount_grant_number)
        return res

    _columns = {
        'amount_grant_schedule_number': fields.function(_amount_grant_schedule_number, string='已完成/总进度', type='char'),
    }
