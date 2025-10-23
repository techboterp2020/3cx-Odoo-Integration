# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

class TemuWebhookController(http.Controller):
    @http.route('/temu/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def temu_webhook(self, **kwargs):
        data = request.jsonrequest
        if data.get('type') == 'ORDER_CREATED':
            request.env['temu.connector'].sudo().sync_orders()
        return {'status': 'received'}