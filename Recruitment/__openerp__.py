# -*- coding: utf-8 -*-
{
    'name': "Recruitment",

    'summary': """
        招聘考核模块""",

    'description': """
        Long description of module's purpose
    """,

    'author': "duwenbo",
    'website': "http://erp.oracleoaec.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','mail'],

    # always loaded
    'data': [
        'views/recruitment.xml',
        'views/menu.xml', 
  
    ],
    # only loaded in demonstration mode
    'demo': [
        
    ],
    'application':True,
    'installable':True,
    'auto_install': False,
}