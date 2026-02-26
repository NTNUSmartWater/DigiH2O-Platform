import os, dotenv, base64, requests, json
import pandas as pd
from datetime import datetime



class Regnbyge():
    def __init__(self) -> None:
        dotenv.load_dotenv()
        self.url = os.getenv('FLOW_URL')
        self.client = os.getenv('FLOW_CLIENT_ID')
        self.client_secret = os.getenv('FLOW_CLIENT_SECRET')
        self.username = os.getenv('FLOW_USERNAME')
        self.password = os.getenv('FLOW_PASSWORD')
        self.token = self.get_Token()

    def get_Token(self):
        # Encode client_id:client_secret to Base64
        auth_string = f"{self.client}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        # Define the headers
        headers = {'Authorization': f'Basic {auth_base64}',
                   'Accept': 'application/json',
                   'Content-Type': 'application/x-www-form-urlencoded'}
        # Define the body parameters (in x-www-form-urlencoded format)
        body = {'username': self.username, 'password': self.password,
                'scope': 'openid regnbyge', 'grant_type': 'password'}
        token_url = os.getenv('FLOW_URL_TOKEN')
        response = requests.request("POST", token_url, headers=headers, data=body)
        if response.status_code == 200: return response.json().get('access_token')
        else: return None

    def get_Station(self, variable):
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {self.token}'}
        url_objects = f'{self.url}/{variable}'
        response = requests.request("GET", url_objects, headers=headers)
        ids = response.json()
        if not ids: return pd.DataFrame()
        rows = []
        for station_id in ids:
            url = f'{url_objects}/{station_id}'
            res = requests.get(url, headers=headers)
            if res.status_code == 200: rows.append(res.json())
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Delete columns with all NaN values
        df.dropna(axis=1, how='all', inplace=True)
        # Delete rows with all NaN values
        df.dropna(axis=0, how='all', inplace=True)
        df.reset_index(inplace=True, drop=True)
        df = df.where(pd.notnull(df), None)
        return df
    
    def get_Values(self, variable:str, ids:list, agg:str='Raw', fromDate='', toDate=''):
        '''
        agg: Raw, Minute, FiveMinute, Hour, Day
        fromDate, toDate: 'YYYY-mm-dd HH:MM:SS'
        '''
        if toDate == '': toDate = datetime.now()
        if fromDate == '': fromDate = toDate - pd.Timedelta(hours=2)
        start = pd.to_datetime(fromDate).strftime('%Y-%m-%d %H:%M:%S')
        end = pd.to_datetime(toDate).strftime('%Y-%m-%d %H:%M:%S')
        headers = {'accept': 'application/json', 'Authorization': f'Bearer {self.token}'}
        payload = {"ids": ids, "from": start, "to": end, "aggregation": agg}
        url = f'{self.url}/{variable}/values'
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except requests.RequestException: return pd.DataFrame()
        data, data_value = pd.DataFrame(), response.json()
        for item in data_value:
            if 'measurements' not in item or not item['measurements']: continue
            df_value = pd.DataFrame(item['measurements'])
            if variable=='flow': # Using Flow
                df = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                    'level (m)':df_value['l'].values, 'velocity (m/s)':df_value['v'].values,
                    'discharge (m³/s)':df_value['q'].values})
            elif variable=='level': # Using Level
                df = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                    'level (m)':df_value['l'].values})
            elif variable=='rain': # Using Rainfall
                df = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                    'rainfall (m)':df_value['r'].values})
            # elif variable=='overflow': # Using Overflow
            #     pass
            # elif variable=='temperature': # Using Temperature
            #     pass

            # elif variable=='evaporation': # Using Evaporation
            #     pass
            # elif variable=='weir': # Using Weir
            #     pass
            df['id'] = item['id']
            data = pd.concat([data, df], ignore_index=True)
        data.reset_index(inplace=True, drop=True)
        data = data.replace(float("nan"), None) # Fill NaN values
        return data