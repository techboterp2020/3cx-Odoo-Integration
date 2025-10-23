# -*- coding: utf-8 -*-

from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    temu_order_id = fields.Char(string='Temu Order ID', copy=False, index=True, readonly=True)

    _sql_constraints = [
        ('temu_order_id_uniq', 'unique(temu_order_id)', 'Temu Order ID must be unique!')
    ]