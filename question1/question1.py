class Strategy(StrategyBase):
    def __init__(self):
        # strategy attributes
        self.period = 60 * 60 * 4 *6
        self.subscribed_books = {
            'Binance': {
                'pairs': ['BTC-USDT'],
            },
        }
        self.options = {}
        self.history_candles = CA.get_history_candles(500, self.period)
        self.first_call=0
        self.his_data=[]
        self.broke=0
        self.ini_fund=0
        self.roll=0
        self.position=0
        self.buy_price=0
        self.roll_rate=1.7
        # define your attributes here
    def on_order_state_change(self,  order):
        pass

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

    def trade(self, candles):
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

       
        if self.first_call==0:
            self.first_save(exchange,pair)
            self.ini_fund=total_quote_amount
            self.first_call=1
        self.his_data=self.his_data.append(candles[exchange][pair][0],ignore_index=True)

        now_index=self.his_data.shape[0]-1
        self.his_data['ema']=talib.EMA(self.his_data['close'],timeperiod=180)
        self.his_data['ema30']=talib.EMA(self.his_data['close'],timeperiod=30)
        self.his_data['di+']=talib.PLUS_DI(high=self.his_data['high'],low=self.his_data['low'],close=self.his_data['close'],timeperiod=21)
        self.his_data['di-']=talib.MINUS_DI(high=self.his_data['high'],low=self.his_data['low'],close=self.his_data['close'],timeperiod=21)
        self.his_data['atr']=talib.ATR(high=self.his_data['high'],low=self.his_data['low'],close=self.his_data['close'],timeperiod=21)
         ######移動停利
        
        if close_price>self.buy_price*self.roll_rate and close_price>self.roll and self.buy_price!=0:
            if self.his_data.loc[now_index,'close']>self.his_data.loc[now_index-1,'close']:
                self.roll=close_price-self.his_data.loc[now_index,'atr']*0.5
        if self.roll>0:
            if close_price<self.roll:
                CA.sell(exchange,pair,total_base_amount,CA.OrderType.LIMIT,close_price)
                self.buy_price=0
                self.position=0
                self.roll=0
                CA.log('移動停利')
                CA.log(str(self.his_data.loc[now_index,'high']))
                return
        ##############移動停利EXIT
        if self.his_data.loc[now_index,'ema30']+self.his_data.loc[now_index,'atr']*2<self.his_data.loc[now_index,'ema'] and self.position==0:
            CA.buy(exchange, pair, available_quote_amount/close_price, CA.OrderType.MARKET)
            self.buy_price=close_price
            self.position=1
            CA.log('emabuy')
            self.roll_rate=1.5
            return
        
        
        #####
        if self.his_data.loc[now_index,'close']<self.his_data.loc[now_index,'ema'] and \
            self.his_data.loc[now_index-1,'close']<self.his_data.loc[now_index-1,'ema']:
            if self.position==1 and self.broke==0:
                CA.log(str('跌破200'))
                CA.sell(exchange, pair,total_base_amount, CA.OrderType.MARKET)
                self.buy_price=0
                self.position=0
                self.broke=1
                return
            elif self.position==0 and self.broke==1:
                if self.his_data.loc[now_index,'di-']>31:
                    CA.log(str('跌破買回'))
                    CA.buy(exchange, pair, available_quote_amount/close_price, CA.OrderType.MARKET)
                    self.buy_price=close_price
                    self.position=1
            return
        self.broke=0
        if self.position==0 and (self.his_data.loc[now_index,'di-']>16 or self.his_data.loc[now_index,'di+']>35):
            if self.his_data.loc[now_index,'ema']>self.his_data.loc[now_index,'close']:
                return
            else:
                CA.log('buy')
                CA.buy(exchange,pair,0.995*available_quote_amount/close_price,CA.OrderType.LIMIT,close_price)
                self.buy_price=close_price
                self.position=1
                return
       
        elif self.position==1:
            if self.his_data.loc[now_index,'di+']>40 and self.his_data.loc[now_index,'di-']<10  \
                and self.his_data.loc[now_index,'di-']>self.his_data.loc[now_index-1,'di-']:
                CA.log('sell')
                self.buy_price=close_price
                CA.sell(exchange,pair,total_base_amount,CA.OrderType.LIMIT,close_price)
                self.position=0
        if self.his_data.loc[now_index,'di-']>37 and self.his_data.loc[now_index,'di+']<15 and self.position==0:
            CA.buy(exchange,pair,available_quote_amount/close_price,CA.OrderType.MARKET)
            CA.log('buy3')
            self.position=1
            self.buy_price=close_price

