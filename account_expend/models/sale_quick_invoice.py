# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError
from openerp.osv import fields, osv
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class SaleQuickInvoiceConfirm(osv.TransientModel):
    _name = 'quick.invoice.confirm'

    def del_the_confirm(self, cr, uid, ids , context=None):
        for confirm_id in ids:
            self.unlink(cr, uid, confirm_id, context)
        return {'type': 'ir.actions.act_window_close'}

    def _get_info(self, cr, uid, ids, field_name, arg, context=None):
        down_payment_id = self.pool['ir.values'].get_default(cr ,uid,'sale.config.settings', 'deposit_product_id_setting')

        res = dict(map(lambda x: (x,0), ids))
        for confirm_order in self.browse(cr, uid, ids, context):
            down_payment = discount = should_total = not_receivable = 0.0
            for line in confirm_order.sale_quick_invoice_lines:
                if field_name == 'show' and line:
                    lsp = line.sale_order_line.product_id

                    down_payment += line.price_total if  lsp.id == down_payment_id else 0.0
                    discount += line.price_total if lsp.name == u'价格优惠' else 0.0
                    should_total += line.price_total if ((lsp.id != down_payment_id) or (lsp.name == u'价格优惠')) else 0.0

            not_receivable +=  confirm_order.sale_order_id.not_receivable
            should_total = should_total + discount

            res[confirm_order.id] = (
                '<table class="mid">\
                    <tbody>\
                        <tr>\
                            <th>预付</th>\
                            <td>%s</td>\
                        </tr>\
                        <tr>\
                            <th>优惠</th>\
                            <td>%s</td>\
                        </tr>\
                        <tr>\
                            <th>应收总款</th>\
                            <td>%s</td>\
                        </tr>\
                        <tr>\
                            <th>待收款</th>\
                            <td>%s</td>\
                        </tr>\
                    </tbody>\
                </table>' % (down_payment, discount, should_total - discount, not_receivable))

        return res
    
    _columns = {
        'sale_order_id': fields.many2one('sale.order'),
        'sale_quick_invoice_lines': fields.one2many('sale.quick.invoice.confirm.line', 'quick_invoice_line', string='销售产品', readonly=True, ondelete='cascade'),
        'account_quick_invoices': fields.one2many('account.quick.invoice.confirm.line', 'quick_invoice_line', string='收款记录', ondelete='cascade'),
        'show': fields.function(_get_info, type='html', string='收款信息')
    }

# 快速开票，sale
class SaleQuickInvoiceConfirmLine(osv.TransientModel):
    _name = 'sale.quick.invoice.confirm.line'

    def _get_order_line_info(self, cr, uid, ids, field_name, arg, context=None):
        down_payment_id = self.pool['ir.values'].get_default(cr ,uid,'sale.config.settings', 'deposit_product_id_setting')

        res = dict(map(lambda x: (x,0), ids))
        for line in self.browse(cr, uid, ids, context):
            if line.sale_order_line:
                sol = line.sale_order_line

                if field_name == 'product_id':
                    res[line.id] = sol.product_id.name
                if field_name == 'sequence':
                    res[line.id] = sol.sequence
                if field_name == 'price_unit':
                    res[line.id] = sol.price_unit
                if field_name == 'price_total':
                    if line.identification != 'discount':
                        res[line.id] = sol.price_unit if (sol.product_id.id == down_payment_id) else sol.price_total
                    else:
                        res[line.id] = sol.price_total
                if field_name == 'product_uom_qty':
                    res[line.id] = sol.product_uom_qty
                if field_name == 'qty_invoiced' and line.identification == 'commodity':
                    res[line.id] = sol.qty_invoiced
                if field_name == 'balance':
                    invoice_total = 0.0
                    for invoice in sol.invoice_lines:
                        if line.identification == 'discount':
                            invoice_total += -invoice.price_subtotal
                        else:
                            invoice_total += invoice.price_subtotal
                    res[line.id] = (line.price_total - invoice_total) if line.identification == 'discount' else (line.price_total - invoice_total)

        return res

    _columns = {
        'quick_invoice_line' : fields.many2one('quick.invoice.confirm', required=True, ondelete='cascade'),
        'sale_order_line' : fields.many2one('sale.order.line', string='订单行ID', required=True, ondelete='cascade'),
        'product_id' : fields.function(_get_order_line_info, string='产品', type='char'),
        'sequence' : fields.function(_get_order_line_info,string='序号', type='integer'),
        'price_unit' : fields.function(_get_order_line_info, string='单价', type='float'),
        'price_total': fields.function(_get_order_line_info, string='小计', type='float'),
        'product_uom_qty' : fields.function(_get_order_line_info, string='数量', type='float'),
        'qty_invoiced' : fields.function(_get_order_line_info, string='收款次数', type='float'),
        'balance': fields.function(_get_order_line_info, string='余款', type='float'),
        'amount': fields.float(string='本次收款'),
        'comment': fields.text(string='说明'),
        'invoice_number': fields.char(string='收据号'),
        'date_invoice': fields.date(string='收款日期'),
        'identification': fields.selection([
            ('down_payment','预付'),
            ('discount', '优惠'),
            ('commodity', '产品')],string='类型'),
    }

    @api.multi
    def create_new_invoice(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account_expend.act_sale_quick_invoice_confirm')
        form_view_id = imd.xmlid_to_res_id('account_expend.view_sale_quick_invoice_confirm_line_from')

        result = {
            'res_id': self.id,
            'name': '收款信息',
            'type': action.type,
            'view_type': 'form',
            'view_model': 'form',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'views_id': form_view_id,
            'target': 'new',
        }

        return result

    @api.multi
    def confirm_cancel(self):
        qid = self.quick_invoice_line.id
        return self.env['sale.order'].confirm_cancel(qid)

    # 覆盖sale_make_invoice_advance的发票创建方法
    @api.multi
    def action_invoice_create(self, order_ids, order_line_id, grouped=False, final=False):
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        orders = self.env['sale.order'].browse(order_ids)
        invoices = {}

        for order in orders:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)

            line = self.env['sale.order.line'].browse(order_line_id)

            if line:

                # if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                #     continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()

                    if self.invoice_number:
                        inv_data['invoice_number'] = self.invoice_number
                    if self.date_invoice:
                        inv_data['date_invoice'] = self.date_invoice
                    if self.comment:
                        inv_data['comment'] = self.comment
                    # 如果产品为优惠，那么建立退款收据
                    if  line.product_id.name == u'价格优惠':
                        inv_data['type'] = 'out_refund'
                    invoice = inv_obj.create(inv_data)
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    
                    invoices[group_key].write(vals)
                    
                    # if not float_is_zero(qty, precision_digits=precision):
                vals = self._prepare_invoice_line(qty=line.product_uom_qty)
                vals.update({'invoice_id': invoices[group_key].id, 'sale_line_ids': [(6, 0, [line.id])]})

                self.env['account.invoice.line'].create(vals)

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))

            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = line.quantity

            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)

            invoice.compute_taxes()

            # 调用验证按钮的工作流
            if invoice.state not in ('draft', 'proforma', 'proforma2'):
                pass
            invoice.signal_workflow('invoice_open')

        return [inv.id for inv in invoices.values()]

    @api.multi
    def _prepare_invoice_line(self, qty):
        sol = self.sale_order_line
        product = sol.product_id
        order_id = sol.order_id

        res = {}
        account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not account:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') % \
                            (product.name, product.id, product.categ_id.name))

        fpos = order_id.fiscal_position_id or order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        # 因为收款改为手写，当出现数量大于1时，一定有计算的必要，变为计算单价的方式
        res = {
            'name': sol.name,
            'sequence': sol.sequence,
            'origin': sol.order_id.name,
            'account_id': account.id,
            'price_unit': self.amount/qty,
            'quantity': qty,
            'price_subtotal': self.amount,
            'discount': sol.discount,
            'uom_id': sol.product_uom.id,
            'product_id': product.id or False,
            'invoice_line_tax_ids': [(6, 0, sol.tax_id.ids)],
            'account_analytic_id': sol.order_id.project_id.id,
        }

        return res

    @api.multi
    def create_invoice(self):
        if self.identification == 'commodity':
            self.amount = abs(self.amount)
        if self.amount <= 0.0:
            raise ValidationError(u'收款不能小于或等于0.0')
        if self.identification != 'discount' and self.amount > self.balance:
            raise ValidationError(u'收款不能大于余款')

        new_invoices = self.action_invoice_create([self.sale_order_line.order_id.id], self.sale_order_line.id, grouped=True)

        invoices = []
        for new_invoice in new_invoices:
            self.env['account.quick.invoice.confirm.line'].create({
                'quick_invoice_line': self.quick_invoice_line.id,
                'invoice_id': new_invoice
                })

        return self.confirm_cancel()

# 快速开票，account
class AccountQuickInvoiceConfirmLine(osv.TransientModel):
    _name = 'account.quick.invoice.confirm.line'

    def _get_invoice_info(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        for line in self.browse(cr, uid, ids, context):
            if line.invoice_id:
                if field_name == 'invoice_line_ids':
                    invoice_text = ''
                    for invoice_line in line.invoice_id.invoice_line_ids:
                        invoice_text += invoice_line.product_id.name + u'；'
                    res[line.id] = invoice_text
                if field_name == 'total':
                    invoice_total = 0.0
                    for invoice_line in line.invoice_id.invoice_line_ids:
                        invoice_total += invoice_line.price_subtotal
                    res[line.id] = invoice_total
                if field_name == 'cdate':
                    res[line.id] = line.invoice_id.create_date

        return res

    # 实体字段使用constrain获取
    @api.constrains('invoice_id')
    def _get_enity_invoice_field(self):
        self.write({
            'invoice_number': self.invoice_id.invoice_number,
            'date_invoice': self.invoice_id.date_invoice,
            'state': self.invoice_id.state
            })

    _columns = {
        'quick_invoice_line' : fields.many2one('quick.invoice.confirm', required=True, ondelete='cascade', readonly=True),
        'invoice_id' : fields.many2one('account.invoice', string='付款ID', required=True, ondelete='cascade', readonly=True),
        'invoice_line_ids': fields.function(_get_invoice_info, type='html', string='目标产品'),
        'total': fields.function(_get_invoice_info, type='float', string='收款'),
        'cdate': fields.function(_get_invoice_info, type='datetime', string='创建时间'),
        'invoice_number' : fields.char(string='收据号'),
        'date_invoice' : fields.date(string='收款日期'),
        'state': fields.selection([
            ('draft','草稿'),
            ('proforma', '形式'),
            ('proforma2', '形式2'),
            ('open', '确认(待收)'),
            ('paid', '已收'),
            ('cancel', '已取消')],string='状态', readonly=True),
    }

    @api.multi
    def confirm_cancel(self):
        qid = self.quick_invoice_line.id
        return self.env['sale.order'].confirm_cancel(qid)

    @api.multi
    def action_invoice(self):
        vals = {}
        if self.invoice_number:
            vals['invoice_number'] = self.invoice_number
        if self.date_invoice:
            vals['date_invoice'] = self.date_invoice
        self.env['account.invoice'].browse(self.invoice_id.id).write(vals)

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_account_invoice_payment')
        form_view_id = imd.xmlid_to_res_id('account.view_account_payment_invoice_form')

        result = {
            'res_id': False,
            'name': '确认',
            'type': action.type,
            'view_type': 'form',
            'view_model': 'form',
            'res_model': action.res_model,
            'views': [(form_view_id, 'form')],
            'views_id': form_view_id,
            'context': {'default_invoice_ids': [(4, self.invoice_id.id, None)]},
            'target': 'new',
        }

        return result