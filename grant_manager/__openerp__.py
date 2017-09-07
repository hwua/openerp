# -*- coding: utf-8 -*-
{
    'name': "grant",

    'description': """
        这是一个补贴管理模块，对销售中的补贴收发情况进行跟踪
    """,

    'author': "Winton.he",
    'website': "http://www.harmonywin.com",
    'summary': """grant""",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale_account_expend','refund'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'template.xml',
        'views/sale.xml',
        'views/res_partner.xml',
        'views/grant.xml',
        'views/managercenter.xml',
        'wizard/wizard.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}