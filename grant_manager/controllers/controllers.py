# -*- coding: utf-8 -*-
from openerp import http

# class Grant(http.Controller):
#     @http.route('/grant/grant/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/grant/grant/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('grant.listing', {
#             'root': '/grant/grant',
#             'objects': http.request.env['grant.grant'].search([]),
#         })

#     @http.route('/grant/grant/objects/<model("grant.grant"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('grant.object', {
#             'object': obj
#         })