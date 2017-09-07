# -*- coding: utf-8 -*-
{
    'name': "account_expend",

    'summary': """
        简化会计操作流程""",

    'description': """
        发票加入销售订单行,销售订单内容计入发票，财务仅操作一张发票就可以完成收款
    """,

    'author': "winton",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','account','refund','bank'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'template.xml',
        'views/views.xml',
        # 'views/account_buckup_order_line.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}