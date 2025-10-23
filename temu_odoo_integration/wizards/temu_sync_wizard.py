# -*- coding: utf-8 -*-

from odoo import models, fields

class TemuSyncWizard(models.TransientModel):
    _name = 'temu.sync.wizard'
    _description = 'Temu Manual Synchronization Wizard'

    sync_products = fields.Boolean(string="Sync Products", default=True)
    sync_orders = fields.Boolean(string="Sync Orders", default=True)
    sync_inventory = fields.Boolean(string="Sync Inventory", default=True)

    def action_run_sync(self):
        self.ensure_one()
        connector = self.env['temu.connector']
        
        if self.sync_products:
            connector.sync_products()
        if self.sync_orders:
            connector.sync_orders()
        if self.sync_inventory:
            connector.update_inventory()
            
        return {'type': 'ir.actions.act_window_close'}