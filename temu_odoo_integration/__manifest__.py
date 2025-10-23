# -*- coding: utf-8 -*-
{
    'name': "Temu Odoo Integration",
    'summary': "Full-featured integration with Temu for products, inventory, orders, and fulfillment management.",
    'description': """
        This module provides a comprehensive two-way integration between Odoo and the Temu marketplace.
        Key Features:
        - Securely configure Temu API credentials in Odoo settings.
        - Two-way product synchronization.
        - Real-time inventory synchronization.
        - Order management: Automatically import new Temu orders into Odoo.
        - Fulfillment updates: Send tracking information from Odoo back to Temu.
    """,
    'author': "Your Name or Company",
    'website': "https://www.yourcompany.com",
    'category': 'Sales/Connector',
    'version': '1.3', # Version updated
    'license': 'OPL-1',
    'depends': ['base', 'sale','sale_management', 'stock', 'product', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/corn.xml',
        'views/temu_intance.xml',
        'views/server_action.xml',
        
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': ['static/description/menu.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}