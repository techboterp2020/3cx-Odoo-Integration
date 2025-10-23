# -*- coding: utf-8 -*-

from odoo import models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        auto_update = self.env['ir.config_parameter'].sudo().get_param('temu.auto_update_fulfillment')
        if auto_update:
            for picking in self:
                if picking.sale_id and picking.sale_id.temu_order_id:
                    try:
                        self.env['temu.connector'].update_fulfillment(picking)
                    except Exception as e:
                        picking.message_post(body=_(f"Failed to send fulfillment update to Temu: {e}"))
        return res