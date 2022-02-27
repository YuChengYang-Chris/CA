class Strategy(StrategyBase):
    def __init__(self):
        # strategy attributes
        self.period = 60 * 60*4
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
        self.now_up=0
        self.now_low=0
        self.position=0
        #### 移動止損
        self.buy_price=0
        self.trailing_sell_price=0

    def on_order_state_change(self,  order):
        CA.log('yee')
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
    def check(self,location):
        max_index=self.his_data.shape[0]-1
        now=self.his_data.loc[location,'close']
        pressure=1
        support=1
        if location+self.n_range>max_index or location-self.n_range<0:
                return
        for i in range(1,self.n_range+1):
            ##### 檢查阻力
            if self.his_data.loc[location+i,'close']>now or self.his_data.loc[location-i,'close']>now:
                pressure=0
            ##### 檢查支撐
            if self.his_data.loc[location+i,'close']<now or self.his_data.loc[location-i,'close']<now:
                support=0
        if pressure==1 or support==1:
            # CA.log(str(now in self.support_pressure))
            if (now in self.support_pressure) ==False:
                self.support_pressure.append(now)
                # CA.log(str(self.support_pressure))
        

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

        ####初始儲存後找出初始支撐阻力
        if self.his_data.shape[0]<502:
            for i in range(0,self.his_data.shape[0]):
                self.check(i)
        #### 每次呼叫確認N天前的價格是否是支撐或阻力
        now_index=self.his_data.shape[0]-1
        self.check(now_index-self.n_range)
        # CA.log('長度:'+str(len(self.support_pressure)))
        temp=np.copy(self.support_pressure)
        temp=temp.tolist()
        temp.append(close_price)
        # CA.log(str(len(temp)))
        temp=sorted(temp)
        # CA.log(str(temp))
        # CA.log(str(close_price))
        now=temp.index(close_price)
        # CA.log(str(now))


        if close_price<self.his_data.loc[now_index,'ema']:
            if self.position==1:
                CA.sell(exchange,pair,available_base_amount,CA.OrderType.MARKET)
                self.position=0
            return

### 移動停利/損
        if self.position==1:
            ### 參考海龜交易法
            self.trailing_sell_price+=self.his_data.loc[now_index,'atr']*0.5
            ### 先檢查是否需要停利/損
            if close_price<self.trailing_sell_price:
                CA.log('做多賣出停損/利')
                CA.sell(exchange,pair,available_base_amount,CA.OrderType.MARKET)
                self.now_low=0
                self.now_up=0
                self.position=0
            ####這裡可以考慮觸發後是否需要return =>停利止損後休息一回合

        # if self.position==-1:
        #     self.trailing_sell_price-=self.his_data.loc[now_index,'atr']*0.5
        #     if close_price>self.trailing_sell_price:
        #         CA.log('做空買入停利/損')
        #         CA.buy_to_cover(exchange,pair,available_base_amount*-1,CA.OrderType.MARKET)
        #         self.now_low=0
        #         self.now_up=0
        #         self.position=0
            ####這裡可以考慮觸發後是否需要return =>停利止損後休息一回合
            

###空手且已經有儲存最近的支撐以及阻力(!=0) 
        if self.now_up!=0 and self.now_low!=0 and self.position==0:
            ###突破開倉多
            if close_price>self.now_up:
                CA.log('買入')
                CA.buy(exchange,pair,0.1*available_quote_amount/close_price,CA.OrderType.LIMIT,close_price)
                # CA.log("??")
                self.buy_price=close_price
                self.trailing_sell_price=close_price-self.his_data.loc[now_index,'atr']
                self.position=1
                return 
            ###跌破做空

            # if close_price<self.now_low:
            #     CA.log('做空')
            #     CA.sell_short(exchange,pair,0.1*available_quote_amount/close_price,CA.OrderType.MARKET)
            #     CA.log('???')
            #     self.buy_price=close_price
            #     self.trailing_sell_price=close_price+self.his_data.loc[now_index,'atr']
            #     self.position=-1
            #     return 
### 空手
        if self.position==0:
            self.now_up=temp[now+1]
            self.now_low=temp[now-1]
        

        pass
