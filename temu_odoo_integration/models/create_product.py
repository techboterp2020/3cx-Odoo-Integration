import requests
import time
import json
import hashlib
import uuid




class CreateProductAPI():
    def __init__(self,URL,APP_KEY,ACCESS_TOKEN,APP_SECRET):
        self.url = URL
        self.appkey = APP_KEY
        self.access_token = ACCESS_TOKEN
        self.app_secret = APP_SECRET
    

    def api_sign_method(self,app_secret, request_params):
        temp = []
        # Sort parameters by key
        request_params = sorted(request_params.items())

        for k, v in request_params:
            v = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
            temp.append(str(k) + str(v.strip('"')))

        un_sign = ''.join(temp)
        un_sign = str(app_secret) + un_sign + str(app_secret)
        sign = hashlib.md5(un_sign.encode('utf-8')).hexdigest().upper()
        return sign
    
    def _call_api(self,data=None):
        original_payload2 = {
                "goodsBasic": {
                    "goodsName": data.name,
                    "catId": data.categ_id.temu_id
                },
                "goodsServicePromise": {
                    "shipmentLimitDay": 1,
                    "fulfillmentType": 1,
                    "costTemplateId": "LFT-11710564721090680779"
                },
                "goodsProperty": {
                    "goodsProperties": [
                                    {
                                "specId": 10005,
                                    
                            }
                    ]
                },
                "skuList": [
                    {
                        "price": {
                            "basePrice": {
                                "amount": "99.00",
                                "currency": "GBP"
                            },
                            "listPriceType": 1
                        },
                        "quantity": 1,
                        "specIdList": [
                            10005,
                            
                        ],
                        "weight": "1",
                        "weightUnit": "g",
                        "length": "1",
                        "width": "1",
                        "height": "1",
                        "volumeUnit": "cm",
                        "images": [
                            "https://img-eu.kwcdn.com/local-goods-img/c1fdc695/3c29a2da-1d42-45dc-8dfa-cb6a1200de16.jpeg",
                        ]
                        # "externalProductType": 3,
                        # "externalProductId": "9780061120084"
                    }
                ]
            }
        
        timestamp = int(time.time())
        request_params = {
            "app_key": self.appkey,
            "data_type": 'JSON',
            "access_token": self.access_token,
            "timestamp": timestamp,
            "type": "bg.local.goods.add",
            "version": '1.0'
        }
        
        request_params = {**request_params, **original_payload2}

        sign = self.api_sign_method(self.app_secret, request_params)
        headers = {
                "Content-Type": "application/json"
            }

        payload = {
            **request_params,
            "sign": sign
        }
        response = requests.post(self.url, headers=headers, data=json.dumps(payload))

        response_json = response.json()
        return response_json