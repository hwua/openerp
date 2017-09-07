# -*- coding: utf-8 -*-
from openerp import http

# class AccountExpend(http.Controller):
#     @http.route('/account_expend/account_expend/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_expend/account_expend/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_expend.listing', {
#             'root': '/account_expend/account_expend',
#             'objects': http.request.env['account_expend.account_expend'].search([]),
#         })

#     @http.route('/account_expend/account_expend/objects/<model("account_expend.account_expend"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_expend.object', {
#             'object': obj
#         })