import requests
import time
import json
import hashlib
import uuid
import logging
_logger = logging.getLogger(__name__)




class Get_Category():
    def __init__(self,URL,APP_KEY,ACCESS_TOKEN,APP_SECRET):
        self.url = URL
        self.appkey = APP_KEY
        self.access_token = ACCESS_TOKEN
        self.app_secret = APP_SECRET
    
    def generate_sign(self, params, app_secret):
        temp = []
        for k, v in sorted(params.items()):
            v = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
            temp.append(str(k) + str(v.strip('"')))
        un_sign = f"{app_secret}{''.join(temp)}{app_secret}"
        return hashlib.md5(un_sign.encode("utf-8")).hexdigest().upper()


    def _call_api(self, method, params):
        payload = {
            "type": str(method),
            "app_key": self.appkey,
            "access_token": self.access_token,
            "timestamp": str(int(time.time())),
            "data_type": "JSON",
            "version": "1.0",
        }

        clean_params = {}
        for k, v in params.items():
            if isinstance(v, (dict, list)):
                clean_params[k] = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
            else:
                clean_params[k] = str(v)
        payload.update(clean_params)
        payload["sign"] = self.generate_sign(payload, self.app_secret)

        try:
            response = requests.post(
                self.url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=20
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _logger.error(f"❌ Temu API call failed: {str(e)}")
            return None
    

    def get_leaf_categories(self,parent_cat_id=0):
        # print(f"Searching for categories under parent ID: {parent_cat_id}...")
        params = {"parentCatId": parent_cat_id}
        resp_data = self._call_api("bg.local.goods.cats.get", params)
        lis = []
        if not resp_data or "result" not in resp_data:
            print("Failed to get categories or invalid response.")
            return None

        cat_list = resp_data.get("result", {}).get("goodsCatsList", [])
        return cat_list