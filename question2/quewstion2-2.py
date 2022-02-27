class Strategy(StrategyBase):
    def __init__(self):
        # strategy attributes
        self.period = 60 * 60*6*4
        self.subscribed_books = {
            'Binance': {
                'pairs': ['BTC-USDT'],
            },
        }
        self.options = {}

        # define your attributes here
        self.history_candles = CA.get_history_candles(500, self.period)
        self.first_call=0
        self.his_data=[]
        #### 支撐阻力的list
        self.support_pressure=[]
        self.n_range=5
        #### 開倉相關
        self.fib_high=0
        self.fib_low=0
        self.now_up=0
        self.now_down=0
        self.position=0
        #### 移動止損
        self.buy_price=0
        self.trailing_sell_price=0

    def on_order_state_change(self,  order):
        # CA.log('yee')
        CA.log(str(order.time))
        CA.log(str(order.status))


    def first_save(self,exchange,pair):
        CA.log('初始儲存')
        if self.history_candles:
            for i in range(0,500):
                if i==0:
                    self.his_data=pd.DataFrame(columns=self.history_candles[exchange][pair][i],data=None)
                if i==len(self.history_candles[exchange][pair]):
                    break
                self.his_data=self.his_data.append(self.history_candles[exchange][pair][i],ignore_index=True)
            CA.log(str(self.his_data.shape))
        return
####確認支撐阻力
    def fibonacci(self,period):
        now_index=self.his_data.shape[0]-1
        df=self.his_data.copy()
        df=df.drop(index=range(0,df.shape[0]-period))
        CA.log(str(df.shape))
        temp_high=df.sort_values(by=['high'],inplace=False,axis='index')
        temp_low=df.sort_values(by=['low'],inplace=False,axis='index')
        #### 欄位順序Index(['close', 'high', 'low', 'open', 'result', 'table', 'time', 'volume', 'atr', 'ema'], dtype='object')
        CA.log(str(temp_high.iloc[period-1,6]))
        CA.log(str(temp_high.iloc[period-1,1]))
        CA.log(str(temp_low.iloc[0,6]))
        CA.log(str(temp_low.iloc[0,2]))
        if temp_high.iloc[period-1,6]>temp_low.iloc[0,6]:
            CA.log('low to high 上漲趨勢')
            self.fib_high=temp_high.iloc[period-1,1]
            self.fib_low=temp_low.iloc[0,2]
            fib_range=self.fib_high-self.fib_low
            self.support_pressure=[]
            self.support_pressure.append(self.fib_low)
            self.support_pressure.append(self.fib_low+(1-0.786)*fib_range)
            self.support_pressure.append(self.fib_low+(1-0.618)*fib_range)
            self.support_pressure.append(self.fib_low+(1-0.5)*fib_range)
            self.support_pressure.append(self.fib_low+(1-0.382)*fib_range)
            self.support_pressure.append(self.fib_low+(1-0.236)*fib_range)
            self.support_pressure.append(self.fib_high)

        else :
            CA.log('high to low 下跌趨勢')
            self.fib_high=temp_high.iloc[period-1,1]
            self.fib_low=temp_low.iloc[0,2]
            fib_range=self.fib_high-self.fib_low
            self.support_pressure=[]
            self.support_pressure.append(self.fib_low)
            self.support_pressure.append(self.fib_low+(0.236)*fib_range)
            self.support_pressure.append(self.fib_low+(0.382)*fib_range)
            self.support_pressure.append(self.fib_low+(0.5)*fib_range)
            self.support_pressure.append(self.fib_low+(0.618)*fib_range)
            self.support_pressure.append(self.fib_low+(0.786)*fib_range)
            self.support_pressure.append(self.fib_high)
        
        pass
        

    def trade(self, candles):
        #####印出資產狀態
        exchange, pair, base, quote = CA.get_exchange_pair()
        exchange, pair, base, quote = CA.get_exchange_pair()
        base_balance = CA.get_balance(exchange, base)
        quote_balance = CA.get_balance(exchange, quote)
        available_base_amount = base_balance.available
        available_quote_amount = quote_balance.available
        total_base_amount = base_balance.total
        total_quote_amount = quote_balance.total
        CA.log('available ' + str(base) + ' amount: ' + str(available_base_amount))
        CA.log('available ' + str(quote) + ' amount: ' + str(available_quote_amount))
        # CA.log('total ' + str(base) + ' amount: ' + str(total_base_amount))
        # CA.log('total ' + str(quote) + ' amount: ' + str(total_quote_amount))
        close_price = candles[exchange][pair][0]['close']
        ####初始儲存
        if self.first_call==0:
            self.first_save(exchange,pair)
            self.ini_fund=total_quote_amount
            self.first_call=1
        self.his_data=self.his_data.append(candles[exchange][pair][0],ignore_index=True)
        self.his_data['atr']=talib.ATR(high=self.his_data['high'],low=self.his_data['low'],close=self.his_data['close'],timeperiod=14)
        self.his_data['ema']=talib.EMA(self.his_data['close'],timeperiod=200)
        now_index=self.his_data.shape[0]-1
        ####初始儲存後找出初始支撐阻力
        #### 欄位順序Index(['close', 'high', 'low', 'open', 'result', 'table', 'time', 'volume', 'atr', 'ema'], dtype='object')
        self.fibonacci(500)
        # CA.log(str(self.his_data.columns))
        CA.log(str(self.support_pressure))
        ####
        temp=np.copy(self.support_pressure)
        temp=temp.tolist()
        temp.append(close_price)
        temp=sorted(temp)
        now=temp.index(close_price)
        ###
        # if close_price<self.his_data.loc[now_index,'ema']:
        #     if self.position==1:
        #         CA.sell(exchange,pair,available_base_amount,CA.OrderType.MARKET)
        #         self.position=0
        #         return
        #     return
        ###
        if self.position==0 and self.now_down==0 and self.now_up==0:
            self.now_up=temp[now+1]
            self.now_down=temp[now-1]
        if self.position==0:
            if close_price<=self.now_down*1.025 :
                CA.log('買入')
                CA.buy(exchange,pair,0.9*available_quote_amount/close_price,CA.OrderType.MARKET)
                self.position=1
                self.buy_price=close_price
                self.trailing_sell_price=close_price-self.his_data.loc[now_index,'atr']*2
        if self.position==1:
            CA.log('移動止損/停利點為: '+str(self.trailing_sell_price))
            if close_price<=self.trailing_sell_price:
                CA.log('停利/損')
                CA.sell(exchange,pair,available_base_amount,CA.OrderType.MARKET)
                self.position=0
                self.now_down=0
                self.now_up=0
            if close_price>self.his_data.loc[now_index-1,'close']:
                self.trailing_sell_price+=self.his_data.loc[now_index,'atr']*0.5


        
