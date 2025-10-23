# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    temu_product_id = fields.Char(string='Temu Product ID', copy=False, index=True)
    
    _sql_constraints = [
        ('temu_product_id_uniq', 'unique(temu_product_id)', 'Temu Product ID must be unique!')
    ]