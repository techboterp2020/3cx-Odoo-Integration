from odoo import models, fields, api
import requests
import time
import time
import logging
import traceback
import json
import hashlib
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from odoo.exceptions import UserError
import base64
# -----------------------------------


from . import get_product as product_api
from . import get_category as category_api
from . import create_product as create_product_api


_logger = logging.getLogger(__name__)


class TemuInstance(models.Model):
    _name = 'temu.intance'
    _description = "Temu Integration Instance"

    name = fields.Char(string='Name')
    temu_endpoint_url = fields.Char(string='Temu API Endpoint URL')
    temu_app_key = fields.Char(string='Temu App Key')
    temu_app_secret = fields.Char(string='Temu App Secret')
    temu_access_token = fields.Char(string='Temu Access Token')
    temu_auto_update_fulfillment = fields.Boolean(string="Auto-Update Fulfillment", default=True)
    fetch_category_date = fields.Datetime(string='Last Category Sync')
    fetch_product_date = fields.Datetime(string='Last Product Sync')
    create_product_last_date = fields.Datetime(string='Last Create Product Sync')
    fetch_order_date = fields.Datetime(string='Last Order Sync Date')
    next_no = fields.Integer(string='Next Number', default=1)
# -------------------------------------------------------------------------
    # fetch category
    # def fetch_category(self):
        
    #     if not self.temu_endpoint_url:
    #         instance = self.env['temu.intance'].search([],limit=1)
    #         temu_endpoint_url = instance.temu_endpoint_url
    #         temu_app_key = instance.temu_app_key
    #         temu_access_token = instance.temu_access_token
    #         temu_app_secret = instance.temu_app_secret

    #     else:
    #         temu_endpoint_url = self.temu_endpoint_url
    #         temu_app_key = self.temu_app_key
    #         temu_access_token = self.temu_access_token
    #         temu_app_secret = self.temu_app_secret

        
    #     category_api_obj = category_api.Get_Category(
    #         temu_endpoint_url,
    #         temu_app_key,
    #         temu_access_token,
    #         temu_app_secret
    #     )
        
    #     data = category_api_obj.get_leaf_categories()
    #     if not data:
    #         return

    #     leaf_list = self.create_category_from_api(data)

    #     while leaf_list:
    #         # Collect all child categories for next iteration
    #         next_level_leaves = []

    #         # Fetch children only for non-leaf categories
    #         non_leaf_ids = [rec['catId'] for rec in leaf_list if not rec.get('leaf')]
    #         if not non_leaf_ids:
    #             break
    #         count = 0
    #         for cat_id in non_leaf_ids:
    #             count +=1

    #             if count == 20:
    #                 break

    #             child_data = category_api_obj.get_leaf_categories(cat_id)
    #             if not child_data:
    #                 continue

    #             child_leaves = self.create_category_from_api(child_data, parent_cat_id=cat_id)
    #             if child_leaves:
    #                 next_level_leaves.extend(child_leaves)

    #         # move to next level
    #         leaf_list = next_level_leaves
            

    # def create_category_from_api(self, data, parent_cat_id=None):
    #     if not data:
    #         return []

    #     # Map of existing Temu IDs for fast lookup
    #     existing_temu_ids = set(
    #         self.env['product.category'].search([('temu_id', 'in', [rec['catId'] for rec in data])]).mapped('temu_id')
    #     )

    #     # Preload parent_id once (if applicable)
    #     parent_id = False
    #     if parent_cat_id:
    #         parent = self.env['product.category'].search([('temu_id', '=', parent_cat_id)], limit=1)
    #         parent_id = parent.id if parent else False

    #     # Prepare category creation list
    #     categories_to_create = []
    #     created_list = []

    #     for rec in data:
    #         cat_id = rec.get('catId')
    #         if cat_id in existing_temu_ids:
    #             continue

    #         categories_to_create.append({
    #             "name": rec.get('catName'),
    #             "temu_id": cat_id,
    #             "parent_id": parent_id,
    #         })

    #         created_list.append({
    #             "catId": cat_id,
    #             "leaf": rec.get('leaf'),
    #         })

    #     # Bulk create for performance
    #     if categories_to_create:
    #         print("created!")
    #         self.env['product.category'].create(categories_to_create)

    #     return created_list
    def fetch_category(self, max_api_calls=None, batch_create_size=500, sleep_between_batches=0.1):
        """
        max_api_calls: optional limit on number of category API calls this run will make
                    (useful to keep runtime short when called from cron)
        batch_create_size: how many categories to create with one ORM create() call
        sleep_between_batches: pause between each API batch (seconds)
        """
        # --- prepare credentials (same as your original)
        if not self.temu_endpoint_url:
            instance = self.env['temu.intance'].search([], limit=1)
            if not instance:
                raise UserError("No Temu instance found.")
            temu_endpoint_url = instance.temu_endpoint_url
            temu_app_key = instance.temu_app_key
            temu_access_token = instance.temu_access_token
            temu_app_secret = instance.temu_app_secret
        else:
            temu_endpoint_url = self.temu_endpoint_url
            temu_app_key = self.temu_app_key
            temu_access_token = self.temu_access_token
            temu_app_secret = self.temu_app_secret

        category_api_obj = category_api.Get_Category(
            temu_endpoint_url,
            temu_app_key,
            temu_access_token,
            temu_app_secret
        )

        # --- initial fetch (same as your original)
        data = category_api_obj.get_leaf_categories()
        if not data:
            _logger.info("No root leaf categories returned by API.")
            return

        # create first level in bulk
        leaf_list = self.create_category_from_api(data, batch_create_size=batch_create_size)

        api_calls = 1  # we already called get_leaf_categories() once
        # BFS loop through levels
        while leaf_list:
            next_level_leaves = []

            # collect non-leaf ids for next level
            non_leaf_ids = [rec['catId'] for rec in leaf_list if not rec.get('leaf')]
            if not non_leaf_ids:
                break

            # process non_leaf_ids in batches (we will call API for each id, but grouped)
            # you used a count==20 earlier — we'll instead batch API calls in groups of size 20
            # so we don't do extremely many parallel calls.
            for i in range(0, len(non_leaf_ids), 20):
                batch_ids = non_leaf_ids[i:i + 20]
                all_child_data = []

                for cat_id in batch_ids:
                    # Optional limit of API calls per run
                    if max_api_calls and api_calls >= max_api_calls:
                        _logger.info("Max API calls reached (%s). Stopping further fetches for this run.", max_api_calls)
                        break

                    child_data = category_api_obj.get_leaf_categories(cat_id)
                    api_calls += 1

                    if child_data:
                        # attach parentCatId so child knows its parent (API might already include it)
                        for rec in child_data:
                            # ensure parentCatId exists — if API doesn't send it, set it
                            if 'parentCatId' not in rec or not rec.get('parentCatId'):
                                rec['parentCatId'] = cat_id
                        all_child_data.extend(child_data)

                    # small sleep to avoid hammering API
                    if sleep_between_batches:
                        time.sleep(0.01)

                # If we hit the max_api_calls and want to stop gracefully:
                if max_api_calls and api_calls >= max_api_calls:
                    # create whatever we fetched so far and return; next cron run continues.
                    if all_child_data:
                        created = self.create_category_from_api(all_child_data, batch_create_size=batch_create_size)
                        if created:
                            next_level_leaves.extend(created)
                    # return early to avoid timeout — next run resumes
                    _logger.info("Stopping run after reaching api_calls limit; will resume next run.")
                    return

                # Bulk create for this batch of children (and record which got created)
                if all_child_data:
                    created = self.create_category_from_api(all_child_data, batch_create_size=batch_create_size)
                    if created:
                        next_level_leaves.extend(created)

                # be polite between 20-id batches
                if sleep_between_batches:
                    time.sleep(sleep_between_batches)

            # proceed to next BFS level
            leaf_list = next_level_leaves


    def create_category_from_api(self, data, parent_cat_id=None, batch_create_size=500):
        """
        Accepts a list of category dicts (each should include 'catId', 'catName', 'leaf', and optionally 'parentCatId')
        Returns list of {'catId': <id>, 'leaf': <bool>} for the newly-created OR existing categories discovered.
        This function is bulk-oriented and will:
        - check existing temu_id in one search per call
        - create missing categories in batches
        - set parent_id to parent_cat_id if provided OR to rec.get('parentCatId') if available and exists already
        """
        if not data:
            return []

        Category = self.env['product.category']

        # collect all temu ids in this batch
        temu_ids = [rec.get('catId') for rec in data if rec.get('catId')]

        # single search for existing categories in this data set
        existing = Category.search([('temu_id', 'in', temu_ids)])
        existing_temu_ids = set(existing.mapped('temu_id')) if existing else set()

        # preload parent mapping for any parentCatId present in this batch
        parent_temu_ids = set(
            rec.get('parentCatId') for rec in data if rec.get('parentCatId')
        )
        parent_map = {}
        if parent_temu_ids:
            parents = Category.search([('temu_id', 'in', list(parent_temu_ids))])
            parent_map = {p.temu_id: p.id for p in parents}

        categories_to_create = []
        created_list = []

        for rec in data:
            cat_id = rec.get('catId')
            if not cat_id:
                continue
            if cat_id in existing_temu_ids:
                # already exists; still include it in created_list so BFS can move forward
                created_list.append({'catId': cat_id, 'leaf': rec.get('leaf')})
                continue

            # determine parent_id:
            parent_id = False
            # priority 1: explicit parent_cat_id passed to function (same parent for whole batch)
            if parent_cat_id:
                # try to find parent by temu_id (was created earlier)
                parent_record = Category.search([('temu_id', '=', parent_cat_id)], limit=1)
                parent_id = parent_record.id if parent_record else False
            else:
                # priority 2: per-record parentCatId if available and exists already
                rec_parent_temu = rec.get('parentCatId')
                if rec_parent_temu:
                    parent_id = parent_map.get(rec_parent_temu, False)

            categories_to_create.append({
                "name": rec.get('catName') or 'Unnamed',
                "temu_id": cat_id,
                "parent_id": parent_id,
                "is_leaf_category":rec.get('leaf', False)
            })
            created_list.append({'catId': cat_id, 'leaf': rec.get('leaf')})

        # Bulk create in chunks for safety
        if categories_to_create:
            for i in range(0, len(categories_to_create), batch_create_size):
                chunk = categories_to_create[i:i + batch_create_size]
                try:
                    Category.create(chunk)
                except Exception as e:
                    _logger.exception("Failed to create category batch: %s", e)
                    # fallback: try creating one by one (to isolate bad records)
                    for vals in chunk:
                        try:
                            Category.create(vals)
                        except Exception as e2:
                            _logger.error("Failed to create single category %s: %s", vals.get('temu_id'), e2)
                # commit every chunk to avoid long transaction and reduce time pressure
                try:
                    self.env.cr.commit()
                except Exception:
                    # sometimes commit can fail in restricted contexts; ignore to continue
                    pass

        return created_list


# ------------------------------------------------------------------------------------------
    def fetch_leaf_products(self):
        """Optimized fetch of leaf categories from Temu"""

        intance = self or self.env['temu.intance'].search([], limit=1)
        if not intance:
            return

        category_api_obj = category_api.Get_Category(
            intance.temu_endpoint_url,
            intance.temu_app_key,
            intance.temu_access_token,
            intance.temu_app_secret
        )

        Category = self.env['product.category']
        non_leaf_cats = Category.search([('is_leaf_category', '=', False),('temu_id', '!=', 0)])
        
        # Cache existing category temu_ids → record.id
        existing_cats = {
            c.temu_id: c.id for c in Category.search([]).filtered(lambda x: x.temu_id)
        }

        
        # Batch storage for all new records
        all_new_records = []

        for rec in non_leaf_cats:
            
            if not rec.temu_id:
                continue

            
            data = category_api_obj.get_leaf_categories(rec.temu_id)
                
            
            # Prepare records efficiently
            print("rec.temu_id",data)
            if data:
                for cat in data:
                    cat_id = cat.get('catId')
                    parent_id = existing_cats.get(cat.get('parentId'))

                    if not cat_id or cat_id in existing_cats:
                        continue  # Skip if already exists

                    all_new_records.append({
                        "name": cat.get('catName') or 'Unnamed',
                        "temu_id": cat_id,
                        "parent_id": parent_id,
                        "is_leaf_category": cat.get('leaf', False),
                    })

        # --- Bulk Create (1 ORM call only)
        if all_new_records:
            Category.create(all_new_records)
            _logger.info("✅ Created %s new leaf categories.", len(all_new_records))
        else:
            _logger.info("ℹ️ No new leaf categories found.")

                        
  
# -----------------------------------------------------------------------------------------
    # products
    def fetch_products(self):
        intance = self
        if not intance:
            intance = self.env['temu.intance'].search([])


        object = product_api.Get_products(intance.temu_endpoint_url,intance.temu_app_key,intance.temu_access_token,intance.temu_app_secret)
        no = intance.next_no
        
        obj = object.call_api(no)
        if not obj:
            intance.next_no = 1
        else:
            self.create_product_from_api(obj)

            intance.next_no = no+1



        self.fetch_product_date  = fields.Datetime.now()
    
    #create PRoduct
    def create_product_from_api(self, datas):
        ProductTemplate = self.env['product.template']
        # Check if product already exists (based on goodsId or name)
        lis = []
        for data  in datas:
            
            existing_product = ProductTemplate.search([('temu_id', '=', str(data.get('goodsId')))], limit=1)
            if existing_product:
                return existing_product

            # Download image
            image_base64 = False
            image_url = data.get('thumbUrl')
            if image_url:
                try:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        image_base64 = base64.b64encode(response.content)
                except Exception as e:
                    _logger.warning("Failed to load image: %s", e)

            # Create Product Template
            catid = self.env['product.category'].search([('temu_id','=',data.get('catId'))],limit=1)

            product_vals = {
                'name': data.get('goodsName'),
                'default_code': str(data.get('goodsId')),  # use external ID as SKU
                'temu_id':str(data.get('goodsId')),
                'list_price': float(data.get('price', 0.0)),
                'standard_price': float(data.get('retailPrice', {}).get('amount', 0.0)),
                # 'type': 'product',
                'currency_id': self.env['res.currency'].search([('name', '=', data.get('currency', 'GBP'))], limit=1).id,
                'image_1920': image_base64,
                "categ_id": catid.id if catid else 1
            
            }
            lis.append(product_vals)
        product = ProductTemplate.create(lis)
        # Optional: create product variant for spec/color
        # if data.get('specName'):
        #     value = 
        #     if self.env['product.attribute.value'].search([('name', '=', data['specName'])], limit=1):


        #     product.write({'attribute_line_ids': [(0, 0, {
        #         'attribute_id': self.env['product.attribute'].search([('name', '=', 'Color')], limit=1).id,
        #         'value_ids': [(6, 0, [self.env['product.attribute.value'].search([('name', '=', data['specName'])], limit=1).id])]
        #     })]})

        return product


# product_odoo_to_shopify
# -------------------------------------------------------------------------------------

    def update_product_odoo_to_shopify(self,proudct_id=None):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            proudct_id = self.env['product.template'].browse(active_ids)
        
        
        if not proudct_id:
            proudct_id = self.env['product.template'].search([('temu_id','=',"")])
        
        

        if not self.temu_endpoint_url:
            instance = self.env['temu.intance'].search([],limit=1)
            temu_endpoint_url = instance.temu_endpoint_url
            temu_app_key = instance.temu_app_key
            temu_access_token = instance.temu_access_token
            temu_app_secret = instance.temu_app_secret

        else:
            temu_endpoint_url = self.temu_endpoint_url
            temu_app_key = self.temu_app_key
            temu_access_token = self.temu_access_token
            temu_app_secret = self.temu_app_secret




        if proudct_id:
            for rec in proudct_id: 
                if not rec.temu_id:
                    object = create_product_api.CreateProductAPI(temu_endpoint_url,temu_app_key,temu_access_token,temu_app_secret)
                    data = object._call_api(rec)
                    if data.get('success'):
                        good = data.get('result')
                        rec.write({
                            "temu_id":str(good.get("goodsId")),
                            
                        })
                        self.create_product_last_date = fields.Datetime.now()
                    else:
                        _logger.info(data.get('errorMsg'))

                    


# ----------------------------------------------------------------------------------------------
# fetch_order_from_temu

    def fetch_order_from_temu(self):
        def generate_sign(params, app_secret):
            """Generate MD5 sign based on Temu rules"""
            sorted_items = sorted(params.items(), key=lambda x: x[0])
            concatenated = "".join(f"{k}{v}" for k, v in sorted_items)
            sign_string = f"{app_secret}{concatenated}{app_secret}"
            return hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()

        timestamp = int(time.time())
        intance = self
        if not intance:
            intance = self.env['temu.intance'].search([])

        url = intance.temu_endpoint_url
        
        # Step 1: dictionary (not json.dumps yet)
        payload = {
            "type": "bg.order.list.v2.get",
            "app_key": intance.temu_app_key,
            "access_token": intance.temu_access_token,
            "timestamp": timestamp,
            "data_type": "JSON",
            "version": "1.0",
            "biz_content": json.dumps({"page_no": 1, "page_size": 5})
        }
        
        # Step 2: add signature
        payload["sign"] = generate_sign(payload, intance.temu_app_secret)
        
        headers = {
            'Content-Type': 'application/json',
            'Cookie': 'api_uid=CpIo+mjFd+VnYwA+LGVDAg=='
        }
        # Step 3: dump after adding sign
        response = requests.post(url, headers=headers, data=json.dumps(payload)).json()
        
    
        self.process_api_response(response)

        self.fetch_order_date = fields.Datetime.now()
    
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

     