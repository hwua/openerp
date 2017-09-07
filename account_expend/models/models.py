# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import re
import time
import logging
_logger = logging.getLogger(__name__)
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        # 修改全款显示方式，原显示收款默认发票是一张全款，不计算开票总款，所以一张发票计算结束
        # 现在我们需要多张发票对应一个产品，需要计算发票合计，再得出已收全款
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        down_payment_id = self.env['ir.values'].get_default('sale.config.settings', 'deposit_product_id_setting')

        lines = []
        status = {}

        for line in self:
            status[line.order_id.id] = []

            if line.product_id.id == down_payment_id:
                line.invoice_status = 'invoiced'

            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            # elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
            #     line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and\
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:

                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                # 比较收款数额，较大就修改为待收款
                subtotal = 0.0
                for invoice in line.invoice_lines:                
                    subtotal += invoice.price_subtotal
                if subtotal < line.price_total:
                    line.invoice_status = 'to invoice'
                elif subtotal == line.price_total:
                    line.invoice_status = 'invoiced'
                elif subtotal > line.price_total:
                    line.invoice_status = 'upselling'

            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) < 0:
                subtotal = 0.0
                if line.product_id.name == u'价格优惠':
                    for invoice in line.invoice_lines:                
                        subtotal += invoice.price_subtotal
                    if subtotal > 0.0:
                        line.invoice_status = 'invoiced'
                else:
                    line.invoice_status = 'no'

            else:
                line.invoice_status = 'no'

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # 监视订单行产品状态，修改订单状态
    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced(self):
        for order in self:
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id').filtered(lambda r: r.type in ['out_invoice', 'out_refund'])
            # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
            # 'account.invoice.refund')
            # use like as origin may contains multiple references (e.g. 'SO01, SO02')
            refunds = invoice_ids.search([('origin', 'like', order.name)]).filtered(lambda r: r.type in ['out_invoice', 'out_refund'])
            invoice_ids |= refunds.filtered(lambda r: order.name in [origin.strip() for origin in r.origin.split(',')])
            # Search for refunds as well
            refund_ids = self.env['account.invoice'].browse()
            if invoice_ids:
                for inv in invoice_ids:
                    refund_ids += refund_ids.search([('type', '=', 'out_refund'), ('origin', '=', inv.number), ('origin', '!=', False), ('journal_id', '=', inv.journal_id.id)])

            line_invoice_status = [line.invoice_status for line in order.order_line]

            # if order.state not in ('sale', 'done'):
            #     invoice_status = 'no'
            if any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                invoice_status = 'invoiced'
            elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
                invoice_status = 'upselling'
            elif all(invoice_status == 'no' for invoice_status in line_invoice_status):
                invoice_status = 'no'
            elif all(invoice_status in ['invoiced', 'no'] for invoice_status in line_invoice_status):
                invoice_status = 'to invoice'
            else:
                invoice_status = 'no'

            order.update({
                'invoice_count': len(set(invoice_ids.ids + refund_ids.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids,
                'invoice_status': invoice_status
            })

    # 重写欠款计算
    not_receivable = fields.Monetary(string=u'欠款',compute='not_receivable_com',store=True)

    @api.depends('amount_total','invoice_count')
    def not_receivable_com(self):
        if self.invoice_count > 0:
            invoice_amount = 0.0
            for invoice in self.invoice_ids:
                    for invoice_line in invoice.invoice_line_ids:
                            if invoice_line.product_id.name == u'价格优惠':
                                invoice_amount -= invoice_line.price_subtotal
                            else:
                                invoice_amount += invoice_line.price_subtotal
            self.not_receivable = self.amount_total - invoice_amount
        else:
            self.not_receivable = self.amount_total

    @api.multi
    def action_sale_quick_invoice_confirm(self):
        down_payment_id = self.env['ir.values'].get_default('sale.config.settings', 'deposit_product_id_setting')
        
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account_expend.act_sale_invoice_confirm')
        form_view_id = imd.xmlid_to_res_id('account_expend.view_sale_invoice_confirm_from')

        sale_quick = self.env['quick.invoice.confirm'].search([('sale_order_id','=',self.id)])
        sale_quick_id = sale_quick[0].id if len(sale_quick) else False

        if (not sale_quick_id) and self.order_line:
            quick_order_lines = []
            quick_invoices = []
            for line in self.order_line:
                if line.product_id.name == u'价格优惠':
                    identification = 'discount'
                elif line.product_id.id == down_payment_id:
                    line.qty_invoiced = 1.0
                    identification = 'down_payment'
                else:
                    identification = 'commodity'

                quick_line = {
                    'sale_order_line': line.id,
                    'identification': identification
                }
                quick_order_lines.append((0, 0, quick_line))
                
                for invoice_line in line.invoice_lines:
                    invoice = (0, 0, {
                        'invoice_id': invoice_line.invoice_id.id
                    })
                    if invoice not in quick_invoices:
                        quick_invoices.append(invoice)
            vals = {
                'sale_order_id': self.id,
                'sale_quick_invoice_lines': quick_order_lines,
                'account_quick_invoices': quick_invoices
            }

            sale_quick = self.env['quick.invoice.confirm'].create(vals)
            sale_quick_id = sale_quick.id

        result = {
            'res_id': sale_quick_id if sale_quick_id else False,
            'name': action.name,
            'type': action.type,
            'view_type': 'form',
            'view_model': 'form',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'context': action.context,
            'views_id': form_view_id,
            'target': 'new',
        }

        return result

    @api.multi
    def confirm_cancel(self, qid=False):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account_expend.act_sale_invoice_confirm')
        form_view_id = imd.xmlid_to_res_id('account_expend.view_sale_invoice_confirm_from')

        result = {
            'res_id': qid,
            'name': action.name,
            'type': action.type,
            'view_type': 'form',
            'view_model': 'form',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'context': action.context,
            'views_id': form_view_id,
            'target': 'new',
        }

        return result

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    invoice_number = fields.Char(string='收据号')

    # 发票中状态改变，同步至quick.invoice
    @api.constrains('state')
    def change_qick_invoice_state(self):
        qick_invoices = self.env['account.quick.invoice.confirm.line'].search([('invoice_id','=',self.id)])
        for qick_invoice in qick_invoices:
            try:
                qick_invoice.state = self.state
            except:
                pass


from openerp.osv import fields, osv
class SaleOrderFilter(osv.Model):
    _inherit = 'sale.order'

    # 此字段暂时不用显示正确内容，所以计算的值为id
    def _get_accounts_invoice_date(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        for sale in self.browse(cr, uid, ids, context):
            if field_name == 'account_invoices_date':
                res[sale.id] = sale.id

        return res

    # 依照开票月份，搜索
    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        date_filter = False
        filter_date = ''
        for arg in args:
            if arg[0] == 'account_invoices_date' and arg[1] == 'ilike':
                filter_date = arg[2]
                date_filter = True
        if date_filter:
            date = re.split(r'[-/\\]',filter_date)
            if len(date) == 2:
                date_search = [('date_invoice','>=', '%s-%s-01' % (date[0],date[1]))]
                if date[1] == '12':
                    date[0] = int(date[0]) + 1
                    date[1] = 1
                else:
                    date[1] = int(date[1]) + 1
                date_search.append(('date_invoice','<', '%s-%s-01' % (date[0],date[1])))
            
            elif len(date) == 3:
                is_date = False
                try:
                    the_date = time.strptime('%s-%s-%s' % (date[0],date[1],date[2]), "%Y-%m-%d")
                    is_date = True
                except:
                    return []
                
                if is_date:
                    date_search = [('date_invoice','=', '%s-%s-%s' % (date[0],date[1],date[2]))]

            res = super(SaleOrderFilter, self).search(cr, uid, args, offset=0, limit=0, order=None, context=context, count=False)
            invoices = self.pool['account.invoice'].search(cr, uid, date_search)
            invoice_lines = self.pool['account.invoice.line'].search(cr, uid, [('invoice_id','in',invoices)])
            order_lines = self.pool['sale.order.line'].search(cr, uid, [('invoice_lines','in',invoice_lines)])
            res = self.pool['sale.order'].search(cr, uid, [('order_line','in',order_lines), ('id','in',res)])

            if count:
                return len(res)
            elif limit:
                return res[offset: offset + limit]
            return res
        else:
            return super(SaleOrderFilter, self).search(cr, uid, args, offset, limit, order, context, count)

    _columns = {
        'account_invoices_date': fields.function(_get_accounts_invoice_date, type='char', string='开票年月（列如2017-8）'),
    }