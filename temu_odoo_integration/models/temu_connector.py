# -*- coding: utf-8 -*-

import requests
import json
import hashlib
import hmac
import time
import logging
from odoo import models, _
from odoo.exceptions import UserError
from datetime import datetime


_logger = logging.getLogger(__name__)

class TemuConnector(models.AbstractModel):
    _name = 'temu.connector'
    _description = 'Temu API Connector'

    def get_timestamp(self):
        timestamp = str(int(time.time()))
        return timestamp

    def generate_sign(self,params, app_secret):
        """Generate MD5 sign based on Temu rules"""
        sorted_items = sorted(params.items(), key=lambda x: x[0])
        concatenated = "".join(f"{k}{v}" for k, v in sorted_items)
        sign_string = f"{app_secret}{concatenated}{app_secret}"
        return hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()


    def _get_api_credentials(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        creds_boj = self.env['temu.configuration'].search([],limit=1)
        if creds_boj:
            creds = {
                'endpoint_url': creds_boj.temu_endpoint_url,
                'app_key': creds_boj.temu_app_key,
                'app_secret': creds_boj.temu_app_secret,
                'access_token': creds_boj.temu_access_token,
            }
            if not all(creds.values()):
                raise UserError(_("Temu API credentials are not fully configured."))
            return creds

    def _make_request(self, endpoint, method='GET', params=None, data=None):
        creds = self._get_api_credentials()
        url = f"{creds['endpoint_url'].rstrip('/')}/{endpoint.lstrip('/')}"
        
        headers = {
            'Content-Type': 'application/json;charset=utf-8',
            'X-ACCESS-TOKEN': "Bearer"+" "+creds['access_token'],
            'X-APP-KEY': creds['app_key'],
        }
        
        try:
            _logger.info(f"Temu API Request: {method} {url}")
            response = requests.request(method, url, headers=headers, params=params, json=data, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('error_code') != 0:
                _logger.error(f"Temu API returned an error: {response_data}")
                raise UserError(_(f"Temu API Error: {response_data.get('error_msg')}"))
            
            return response_data.get('result', response_data)

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request Exception calling Temu API: {e}")
            raise UserError(_(f"Could not connect to Temu API: {e}"))

    def sync_products(self):
        cred = self._get_api_credentials()
        if cred:
            url = cred['endpoint_url']
            
            # Step 1: dictionary (not json.dumps yet)
            payload = {
                "type": "bg.local.goods.sku.list.query",
                "app_key": cred['app_key'],
                "access_token": cred['access_token'],
                "timestamp": self.get_timestamp(),
                "data_type": "JSON",
                "version": "1.0",
                "biz_content": json.dumps({"page_no": 1, "page_size": 5})
            }
            
            # Step 2: add signature
            payload["sign"] = self.generate_sign(payload, cred['app_secret'])
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': 'api_uid=CpIo+mjFd+VnYwA+LGVDAg=='
            }
            # Step 3: dump after adding sign
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            

    def sync_orders(self):
        cred = self._get_api_credentials()
        if cred:
            url = cred['endpoint_url']
            
            # Step 1: dictionary (not json.dumps yet)
            payload = {
                "type": "bg.order.list.v2.get",
                "app_key": cred['app_key'],
                "access_token": cred['access_token'],
                "timestamp": self.get_timestamp(),
                "data_type": "JSON",
                "version": "1.0",
                "biz_content": json.dumps({"page_no": 1, "page_size": 5})
            }
            
            # Step 2: add signature
            payload["sign"] = self.generate_sign(payload, cred['app_secret'])
            
            headers = {
                'Content-Type': 'application/json',
                'Cookie': 'api_uid=CpIo+mjFd+VnYwA+LGVDAg=='
            }
            # Step 3: dump after adding sign
            response = requests.post(url, headers=headers, data=json.dumps(payload)).json()
            
        
            self.process_api_response(response)    
    def process_api_response(self, api_response):
        """
        Processes the JSON data from the API and creates sales orders in Odoo.
        This function should be called after you receive a successful response from the API.
        
        :param api_response: The JSON response received from the API call.
        """
        if not api_response or 'result' not in api_response:
            print("Invalid or empty API response received.")
            return

        print("Processing API response to create sales orders...")

        order_list = api_response.get('result', {}).get('pageItems', [])
        
        # You may need to create a specific customer for these orders
        # or search for an existing one.
        # For this example, we'll find a default one or a placeholder.
        partner_id = self.env['res.partner'].search([['is_company', '=', True]], limit=1).id
        
        if not partner_id:
            print("No partner found. Please create a customer to assign to these orders.")
            return
        for index,parent_order_data in enumerate(order_list):
            if index == 3:
                break

            parent_order_map = parent_order_data.get('parentOrderMap', {})
            order_items = parent_order_data.get('orderList', [])

            parent_order_sn = parent_order_map.get('parentOrderSn')
            parent_order_time_ts = parent_order_map.get('parentOrderTime')

            if not parent_order_sn:
                continue

            # Check if a sales order with this external reference already exists
            # existing_sale_order = self.env['sale.order'].search([
            #     ('client_order_ref', '=', parent_order_sn)
            # ], limit=1)
            existing_sale_order = False
            if existing_sale_order:
                print(f"Sales Order with reference '{parent_order_sn}' already exists. Skipping.")
                continue

            # Convert timestamp to a readable date
            order_date = datetime.fromtimestamp(parent_order_time_ts).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\nProcessing parent order: {parent_order_sn}...")

            # Prepare data for the main sales order
            sales_order_data = {
                'partner_id': partner_id,
                'client_order_ref': parent_order_sn,
                'date_order': order_date,
            }

            try:
                # Create the main sales order record
                sale_order = self.env['sale.order'].create(sales_order_data)
                print(f"Created sales order with ID: {sale_order.id}")
                
                # Now, create the sales order lines for each item
                for item in order_items:
                    goods_name = item.get('goodsName')
                    sku_id = str(item.get('skuId'))
                    quantity = item.get('originalOrderQuantity')
                    spec = item.get('spec')

                    if not goods_name or not quantity or not sku_id:
                        continue

                    # Find the Odoo product by SKU (Internal Reference)
                    product = self.env['product.product'].search([
                        ('default_code', '=', sku_id)
                    ], limit=1)

                    if product:
                        # Prepare data for the sales order line
                        line_data = {
                            'order_id': sale_order.id,
                            'product_id': product.id,
                            'product_uom_qty': quantity,
                            'name': f"{goods_name} - {spec}",
                        }

                        # Create the sales order line record
                        sale_order.order_line.create(line_data)
                        print(f"   -> Created line for product '{goods_name}'")
                    else:
                        print(f"   -> WARNING: Product with SKU '{sku_id}' not found in Odoo. Skipping line.")
            except Exception as e:
                print(f"An error occurred while creating order {parent_order_sn}: {e}")
        
        print("\nAll sales orders have been processed.")

                
   
    def update_fulfillment(self, picking):
        if not picking.sale_id.temu_order_id or not picking.carrier_tracking_ref:
            return False

        fulfillment_data = {
            'order_sn': picking.sale_id.temu_order_id,
            'tracking_number': picking.carrier_tracking_ref,
            'shipping_carrier': picking.carrier_id.name if picking.carrier_id else 'Other',
        }
        
        self._make_request('order/ship', method='POST', data=fulfillment_data)
        picking.sale_id.message_post(body=_(f"Fulfillment information sent to Temu."))
        return True

    def update_inventory(self):
        _logger.info("Starting Temu inventory synchronization.")
        products_to_sync = self.env['product.template'].search([('temu_product_id', '!=', False)])
        updates = []
        for product in products_to_sync:
            updates.append({
                'sku_id': product.default_code,
                'quantity': int(product.qty_available),
            })
        
        if updates:
            self._make_request('inventory/update', method='POST', data={'updates': updates})
        _logger.info("Finished Temu inventory synchronization.")