import requests
import time
import json
import hashlib
import uuid



class Get_products():
    def __init__(self,URL,APP_KEY,ACCESS_TOKEN,APP_SECRET):
        self.url = URL
        self.appkey = APP_KEY
        self.access_token = ACCESS_TOKEN
        self.app_secret = APP_SECRET
    



    def generate_sign(self,params, app_secret):
            """Generate MD5 sign based on Temu rules (adapted to user method)"""
            temp = []
            # Sort parameters by key
            sorted_items = sorted(params.items())
            
            for k, v in sorted_items:
                # Always JSON dump
                v = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
                # Strip only outer quotes if string
                temp.append(str(k) + str(v.strip('"')))
            
            un_sign = f"{app_secret}{''.join(temp)}{app_secret}"
            # print(">>> Sign string before MD5:", un_sign)  # Debugging
            return hashlib.md5(un_sign.encode("utf-8")).hexdigest().upper()


    def call_api(self,no):
        headers = {
            "content-type": "application/json"
        }
        payload = {
    
            "goodsSearchType": 5,
            
            "pageSize": 5,
            "type": "bg.local.goods.list.query",
            "version": "1.0",
            "access_token": self.access_token,
            "app_key": self.appkey,
            "goodsStatusFilterType": 1,
            "pageNo": no,
            "data_type": "JSON",
            
            "timestamp": str(int(time.time()))
        }
        payload["sign"] = self.generate_sign(payload, self.app_secret)
        response = requests.post(self.url, headers=headers, data=json.dumps(payload)).json()

        # print("Status Code:", response.status_code)

        data = response.get("result", {}).get("goodsList", [])

        return data 


