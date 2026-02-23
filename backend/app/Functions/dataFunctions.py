import os, dotenv, base64, requests, json
import pandas as pd



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
        '''
        toDate, fromDate = pd.to_datetime(toDate).isoformat(), pd.to_datetime(fromDate).isoformat()
        headers = {'accept': 'application/json', 'Authorization': f'Bearer {self.token}'}
        data = pd.DataFrame()
        for id in ids:
            url = f'{self.url}/{variable}/{id}/values?from={fromDate}&to={toDate}&aggregation={agg}'
            response = requests.request("GET", url, headers=headers)
            if response.status_code == 200:
                data_value = json.loads(response.content)
                # Create DataFrame from Dictionary
                df_value = pd.DataFrame.from_dict(data_value['measurements'])
                if len(df_value)>0:
                    if variable=='flow': # Using Flow
                        df_ = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                            'level (m)':df_value['l'].values, 'velocity (m/s)':df_value['v'].values,
                            'discharge (m³/s)':df_value['q'].values})
                    elif variable=='level': # Using Level
                        df_ = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                            'level (m)':df_value['l'].values})
                    elif variable=='overflow': # Using Overflow
                        pass
                    elif variable=='temperature': # Using Temperature
                        pass
                    elif variable=='rain': # Using Rainfall
                        df_ = pd.DataFrame(data={'timestamp':pd.to_datetime(df_value['t'].values),
                            'rainfall (m)':df_value['r'].values})
                    elif variable=='evaporation': # Using Evaporation
                        pass
                    elif variable=='weir': # Using Weir
                        pass
                    data = pd.concat([data, df_])
        data.reset_index(inplace=True, drop=True)
        data = data.replace(float("nan"), None) # Fill NaN values
        return data