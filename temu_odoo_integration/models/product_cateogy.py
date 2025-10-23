from odoo import models,fields


class ProductCategory(models.Model):
    _inherit = 'product.category' 


    temu_id = fields.Integer(string="Temu ID")
    external_cat_id = fields.Char("External Category ID", index=True)
    is_leaf_category = fields.Boolean(string='is Leaf Category')





class ProductTemplate(models.Model):
    _inherit = 'product.template'


    temu_id = fields.Char(string='Temu')
    specId = fields.Integer(string='specId')