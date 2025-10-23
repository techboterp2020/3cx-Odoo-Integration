# -*- coding: utf-8 -*-

from odoo import models, fields

class ConfigurationTemu(models.Model):
    _name = 'temu.configuration'

    temu_endpoint_url = fields.Char(
        string='Temu API Endpoint URL',
    )
    temu_app_key = fields.Char(
        string='Temu App Key',
    )
    temu_app_secret = fields.Char(
        string='Temu App Secret',
    )
    temu_access_token = fields.Char(
        string='Temu Access Token',
    )
    temu_auto_update_fulfillment = fields.Boolean(
        string="Auto-Update Fulfillment",
        default=True,
    )



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    temu_endpoint_url = fields.Char(
        string='Temu API Endpoint URL',
        config_parameter='temu.endpoint_url'
    )
    temu_app_key = fields.Char(
        string='Temu App Key',
        config_parameter='temu.app_key'
    )
    temu_app_secret = fields.Char(
        string='Temu App Secret',
        config_parameter='temu.app_secret'
    )
    temu_access_token = fields.Char(
        string='Temu Access Token',
        config_parameter='temu.access_token'
    )
    temu_auto_update_fulfillment = fields.Boolean(
        string="Auto-Update Fulfillment",
        config_parameter='temu.auto_update_fulfillment',
        default=True,
    )