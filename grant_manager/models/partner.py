# -*- coding: utf-8 -*-
from openerp import api
from openerp import SUPERUSER_ID, models
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from openerp.http import request

class res_partner(osv.Model):
    _inherit = 'res.partner'

    # sale_order_grant_count为该客户补贴总和。补贴来自客户订单中的生活补助款。首先订单需要是销售订单状态,然后补贴状态需要是待确认、发放中或者已完毕
    def _sale_order_grant_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        for partner in self.browse(cr, uid, ids, context):
                count = 0.0
                if field_name=='sale_order_grant_count':
                    for p_order in partner.sale_order_ids:
                        if p_order.amount_grant_state in ('draft','in','done','other'):
                            count += p_order.amount_grant if p_order.amount_grant else 0.0
                    for c_order in partner.mapped('child_ids.sale_order_ids'):
                        if c_order.amount_grant_state in ('draft','in','done','other'):
                            count += c_order.amount_grant if c_order.amount_grant else 0.0
                    res[partner.id] = count

                    # 如果计算结果为0，说明该客户所有订单都无补贴，将状态改为无，这也是在function字段无法筛选时，另一个筛选方法
                    # if count == 0.0:
                    #     partner.write({'sale_grant_state': 'none'})

                if field_name=='sale_order_grant_next_count':
                    for p_order in partner.sale_order_ids:
                        if p_order.amount_grant_state in ('draft','in','done','other'):
                            count += p_order.amount_grant_surplus_next if p_order.amount_grant_surplus_next else 0.0
                    for c_order in partner.mapped('child_ids.sale_order_ids'):
                        if c_order.amount_grant_state in ('draft','in','done','other'):
                            count += c_order.amount_grant_surplus_next if c_order.amount_grant_surplus_next else 0.0
                    res[partner.id] = count

                if field_name=='account_already':
                    orders = []
                    for p_order in partner.sale_order_ids:
                        orders.append(p_order.id)
                    try:
                        orders = sorted(orders, reverse=True)
                        order = self.pool.get('sale.order').browse(cr, SUPERUSER_ID, orders[0], context)
                        if order.state in ['sale','done']:
                            res[partner.id] = '<p style="color:green;margin:0;padding:0">✔</p>'
                        else:
                            res[partner.id] = '<p style="color:red;margin:0;padding:0">?</p>'
                    except:
                        res[partner.id] = '<p style="color:red;margin:0;padding:0">?</p>'

        return res

    # function字段需要处理才能变成可筛选条件，这里是它的fnct_search函数，报错，需要修改
    # def _sale_order_grant_count_search(self, cr, uid, obj, name, domain, context=None):
    #     partners = self.pool['res.partner'].search_read(cr, uid, domain, ['partner_id'], context=context)
    #     rs = [partner['partner_id'][0] for partner in partners if partner['partner_id']]
    #     return [('id', 'in', rs)]

    _columns = {
        'sale_grant_state' : fields.selection([('none','无'),('draft','待确认'),('in','发放中'),('done','已完毕'),('other','退费')], default='none', string='补贴进度', readonly=True),
        'sale_order_grant_count': fields.function(_sale_order_grant_count, string='补贴总额', type='monetary'),
        'sale_order_grant_next_count': fields.function(_sale_order_grant_count, string='下次发放', type='monetary'),
        'sale_order_grant_message': fields.char(string='下期发放'),
        'grant_change_sale_number_wizard' : fields.integer(string='补贴期数'),
        'amount_grant_rate': fields.float(string=u'税点', requird=True, digits=(16, 3),default = 5.0),
        'account_already': fields.function(_sale_order_grant_count, string="账号是否生成", type='char')
    }
