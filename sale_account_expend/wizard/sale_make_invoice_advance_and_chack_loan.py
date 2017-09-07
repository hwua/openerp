# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
import time

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

class SaleAdvancePaymentInvAdded(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.model
    def _get_advance_payment_method(self):
        return super(SaleAdvancePaymentInvAdded, self)._get_advance_payment_method()

    advance_payment_method = fields.Selection([
        ('fixed', 'Down payment (fixed amount)'),
        ('delivered', 'Invoiceable lines'),
        ('all', 'Invoiceable lines (deduct down payments)')
        ], string='What do you want to invoice?', default=_get_advance_payment_method, required=True)

    @api.onchange('advance_payment_method')
    def _get_down_payment_when_fixed(self):
        payment = 0.0
        if (self.advance_payment_method == 'fixed') and (self._count() == 1):
            lines = self.env['sale.order.line'].search([('order_id','=',(self._context.get('active_ids'))[0])])
            for line in lines:
                if line.product_id.id == self.env['ir.values'].get_default('sale.config.settings', 'deposit_product_id_setting'):
                    payment += line.price_unit
        self.amount = payment

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                else:
                    tax_ids = taxes.ids

                pay = down_pay = 0.0
                down_payment_id = self.env['ir.values'].get_default('sale.config.settings', 'deposit_product_id_setting')
                lines = self.env['sale.order.line'].search([('order_id','=',order.id),('product_id.id','=',down_payment_id)])

                if len(lines):
                    update_lines = []

                    
                    if len(lines) > 1:
                        num = 0
                        for line in lines:
                            pay += line.price_unit
                            if num > 0:
                                update_lines.append((2,line.id))
                            num += 1
                        update_lines.append((1,lines[0].id,{'price_unit':pay}))
                        down_pay = pay
                    else:
                        if lines[0].price_unit != amount:
                            update_lines.append((1,lines[0].id,{'price_unit':amount}))
                            down_pay = amount 
                    if update_lines != []:
                        order.write({
                            'order_line' : update_lines
                            })
                    if down_pay:
                        order.write({'down_payment': down_pay})
                    so_line = lines[0]


                if not len(lines):
                    order.write({'down_payment': amount})

                    so_line = sale_line_obj.create({
                        'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                        'price_unit': amount,
                        'product_uom_qty': 0.0,
                        'order_id': order.id,
                        'discount': 0.0,
                        'product_uom': self.product_id.uom_id.id,
                        'product_id': self.product_id.id,
                        'tax_id': [(6, 0, tax_ids)],
                    })

                self._create_invoice(order, so_line, amount)
                sale_orders._amount_all()#计算总额、贷款等等
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


