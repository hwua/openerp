# -*- coding: utf-8 -*-
import logging
import time
from openerp import api, fields, models, _
from openerp.exceptions import UserError,ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Vendor Refund
}

# 销售订单增加贷款方案
class sales_orders_loan(models.Model):
    _inherit = 'sale.order'

    is_loan = fields.Boolean(string=u'是否贷款')
    company = fields.Many2one('config_company', string=u'贷款机构')
    company_project = fields.Many2one('config_project', string=u'金融方案')

    down_payment = fields.Monetary(string=u'首付款/定金')
    amount_down_payment = fields.Monetary(string=u'首付款/定金', compute='_amount_all')
    amount_grant = fields.Monetary(string=u'生活补助款')
    amount_rate1 = fields.Float(string=u'宽限期利率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_repayment_rate1 = fields.Float(string=u'宽限期还款率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_rate2 = fields.Float(string=u'还款期利率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_repayment_rate2 = fields.Float(string=u'还款期还款率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_month1 = fields.Integer(string=u'宽限期', compute="_get_project_info", readonly=True)
    amount_month2 = fields.Integer(string=u'还款期', compute='_get_project_info', readonly=True)
    amount_loan_total = fields.Monetary(string=u'贷款额总计', compute = '_amount_all', readonly=True, store=True, track_visibility='always')
    amount_installment1 = fields.Monetary(string=u'宽限期分期付', compute='_amount_all', readonly=True)
    amount_installment2 = fields.Monetary(string=u'还款期分期付', compute='_amount_all', readonly=True)

    @api.constrains('down_payment')
    def _get_down_payment(self):
        down_payment_id = self.env['ir.values'].get_default('sale.config.settings', 'deposit_product_id_setting')
        lines = self.env['sale.order.line'].search([('order_id','=',self.id),('product_id.id','=',down_payment_id)])
        if lines and self.down_payment:
            down_pay = self.down_payment
            self.write({
                'order_line' : [(1,lines[0].id,{'price_unit':down_pay})]
                })
        else:
            if self.down_payment > 0.0:
                values = {
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'product_id': down_payment_id,
                    'price_unit': self.down_payment,
                    'product_uom_qty': 0
                }
                self.write({"order_line": [(0, 0, values)]})

    @api.multi
    @api.constrains('partner_id')
    def check_partner_email(self):
        if self.partner_id.res_email == False:
            raise ValidationError(_('请填写客户邮箱！'))

    # 添加预付款和贷款总计，覆盖原总价计算
    @api.onchange('down_payment','amount_grant','amount_loan_total')
    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            loan_total = 0.0
            amount_down_payment = amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                if line.product_id.name == "Down payment" and line.price_subtotal == 0.0:
                        amount_down_payment += line.price_unit
            total = amount_untaxed + amount_tax

            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': total,
                'amount_down_payment': order.pricelist_id.currency_id.round(amount_down_payment)
            })

            if (order.is_loan==True) and (order.amount_month2 > 0) :
                count = total + order.amount_grant - amount_down_payment
                if order.down_payment:
                    count = total + order.amount_grant - amount_down_payment - order.down_payment                    
                #存在月还款率，以月还款率优先
                if (order.amount_repayment_rate1 > 0.0) or (order.amount_repayment_rate2 > 0.0):
                    rate1 = order.amount_repayment_rate1 / 100.0
                    rate2 = order.amount_repayment_rate2 / 100.0
                    order.amount_installment1 = count * rate1
                    order.amount_installment2 = count * rate2

                    loan_total = order.amount_installment1 * order.amount_month1 + order.amount_installment2 * order.amount_month2
                else:
                    rate2 = order.amount_rate2 / 100.0

                    #前期等于0.0，月本金就是商品总价/还款期月份数
                    if order.amount_rate1 == 0.0:
                        rate1 = 0.0
                        month_capital = count / order.amount_month2
                        order.amount_installment1 = 0.0

                    #前期大于0.0，月本金就是商品总价/全部月份数
                    else:
                        rate1 = order.amount_rate1 / 100.0
                        month_capital = count / (order.amount_month1 + order.amount_month2)
                        order.amount_installment1 = count * rate1 + month_capital

                    order.amount_installment2 = count * rate2 + month_capital
                    loan_total = count * rate1 * order.amount_month1 + count * rate2 * order.amount_month2 + count

                order.update({
                    'amount_loan_total': loan_total
                })

    #限制补助款3000一下
    #@api.onchange('amount_grant')
    #@api.constrains('amount_grant')
    #def _check_max_amount_grant(self):
    #    if self.amount_grant > 5000:
    #        raise UserError(_("生活补助款最高额度为5000"))

    #取消贷款后清空方案
    @api.onchange('is_loan','company')
    def _empty_all(self):
        if self.is_loan == False:
            self.update({
                'company': False,
                'company_project': False,
                'amount_down_payment': 0.0,
                'amount_grant': 0.0,
                'amount_loan_total': 0.0,
                'amount_installment1': 0.0,
                'amount_installment2': 0.0,
                })
        else:
            self.company_project = False

    @api.onchange('company_project')
    def _get_project_info(self):
        for order in self:
            order.amount_rate1 = order.company_project.rate1
            order.amount_rate2 = order.company_project.rate2
            order.amount_month1 = order.company_project.month1
            order.amount_month2 = order.company_project.month2
            order.amount_repayment_rate1 = order.company_project.repayment_rate1
            order.amount_repayment_rate2 = order.company_project.repayment_rate2

    #覆盖原销售订单新增发票
    #新增条目
    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'journal_id': journal_id,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'is_loan': self.is_loan,
            'amount_down_payment': self.down_payment,
            'company': self.company.id,
            'company_project': self.company_project.id,
            'amount_grant': self.amount_grant,
            'amount_loan_total': self.amount_loan_total,
            }
        return invoice_vals

#会计发票新增贷款方案
class account_invoice_loan(models.Model):
    _inherit = 'account.invoice'

    is_loan = fields.Boolean(string=u'是否贷款')
    company = fields.Many2one('config_company', string=u'贷款机构')
    company_project = fields.Many2one('config_project', string=u'金融方案')

    amount_down_payment = fields.Monetary(string=u'首付款/定金', readonly=True)
    amount_grant = fields.Monetary(string=u'生活补助款',readonly=True)
    amount_rate1 = fields.Float(string=u'宽限期利率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_repayment_rate1 = fields.Float(string=u'宽限期还款率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_rate2 = fields.Float(string=u'还款期利率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_repayment_rate2 = fields.Float(string=u'还款期还款率', compute='_get_project_info', digits=(16, 3), readonly=True)
    amount_loan_total = fields.Monetary(string=u'贷款额总计', compute = '_count_loan', readonly=True)
    amount_month1 = fields.Integer(string=u'宽限期', compute="_get_project_info", readonly=True)
    amount_month2 = fields.Integer(string=u'还款期', compute='_get_project_info', readonly=True)

    #@api.onchange('amount_grant')
    #@api.constrains('amount_grant')
    #def _check_max_amount_grant(self):
    #    if self.amount_grant > 5000:
    #        raise UserError(_("生活补助款最高额度为5000"))

    @api.onchange('is_loan','company')
    def _empty_all(self):
        if self.is_loan == False:
            self.update({
                'company': False,
                'company_project': False,
                'amount_down_payment': 0.0,
                'amount_grant': 0.0,
                'amount_loan_total': 0.0,
                })
        else:
            self.company_project = False


    @api.onchange('company')
    def _empty_project(self):
        if self.company_project:
            self.company_project = False

    @api.onchange('company_project')
    def _get_project_info(self):
        self.amount_rate1 = self.company_project.rate1
        self.amount_rate2 = self.company_project.rate2
        self.amount_month1 = self.company_project.month1
        self.amount_month2 = self.company_project.month2
        self.amount_repayment_rate1 =self.company_project.repayment_rate1
        self.amount_repayment_rate2 =self.company_project.repayment_rate2

    @api.onchange('is_loan','amount_grant','amount_total','company_project')
    def _count_loan(self):
        try:
            if self.is_loan and self.amount_total:
                count = self.amount_total + self.amount_grant - self.amount_down_payment
                if (self.amount_repayment_rate1 > 0.0) or (self.amount_repayment_rate2 > 0.0):
                    rate1 = self.amount_repayment_rate1 / 100.0
                    rate2 = self.amount_repayment_rate2 / 100.0
                    self.amount_installment1 = count * rate1
                    self.amount_installment2 = count * rate2

                    self.amount_loan_total = self.amount_installment1 * self.amount_month1 + self.amount_installment2 * self.amount_month2
                else:
                    rate2 = self.amount_rate2 / 100.0
                    rate1 = self.amount_rate1 / 100.0

                    self.amount_loan_total = count * rate1 * self.amount_month1 + count * rate2 * self.amount_month2 + count
        except:
            return False

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = {}
        for field in ['name', 'reference', 'comment', 'date_due', 'partner_id', 'company_id', 'account_id', 'currency_id', 'payment_term_id', 'user_id', 'fiscal_position_id', 'is_loan' , 'company', 'company_project']:
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = filter(lambda l: l.manual, invoice.tax_line_ids)
        values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.number

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values

