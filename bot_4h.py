import json
import logging
import os
import smtplib

import time

import datetime
from poloniex import Poloniex
from creds_vm import POLONIEX_API_KEY, POLONIEX_SECRET_KEY, GMAIL_USER, GMAIL_PASSWORD, TARGET

PAIRS = ['BTC_ETH', 'BTC_XRP', 'BTC_XEM', 'BTC_LTC', 'BTC_STR', 'BTC_BCN', 'BTC_DGB', 'BTC_ETC', 'BTC_SC', 'BTC_DOGE',
          'BTC_GNT', 'BTC_XMR', 'BTC_DASH', 'BTC_ARDR', 'BTC_STEEM', 'BTC_NXT', 'BTC_ZEC',
         'BTC_STRAT', 'BTC_DCR', 'BTC_NMC', 'BTC_MAID', 'BTC_BURST', 'BTC_GAME', 'BTC_FCT', 'BTC_LSK', 'BTC_FLO',
         'BTC_CLAM', 'BTC_SYS', 'BTC_GNO', 'BTC_REP', 'BTC_RIC', 'BTC_XCP', 'BTC_PPC', 'BTC_AMP', 'BTC_SJCX', 'BTC_LBC',
         'BTC_EXP', 'BTC_VTC', 'BTC_GRC', 'BTC_NAV', 'BTC_FLDC', 'BTC_POT', 'BTC_RADS', 'BTC_NAUT',
         'BTC_BTCD', 'BTC_XPM', 'BTC_NOTE', 'BTC_NXC', 'BTC_PINK', 'BTC_OMNI', 'BTC_VIA', 'BTC_XBC', 'BTC_NEOS',
         'BTC_PASC', 'BTC_BTM', 'BTC_VRC', 'BTC_BLK', 'BTC_BCY', 'BTC_XVC', 'BTC_HUC']

BUY_ENSURE_COEF = 1.5
CANDLE_PERIOD = 14400
NUM_OF_PAIRS = 9
MIN_PAIRS = 1
TRADE_AMOUNT = 0.08
DEPTH_OF_SELLING_GLASS = 200

MIN_VOLUME = 150
RATIO_OPEN_CLOSE = 1.03
SMA_NUM = 50
CANDLES_NUM = 2



class Gmail(object):
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.server = 'smtp.gmail.com'
        self.port = 587
        session = smtplib.SMTP(self.server, self.port)
        session.ehlo()
        session.starttls()
        session.ehlo
        session.login(self.email, self.password)
        self.session = session

    def send_message(self, subject, body):
        """ This must be removed """
        headers = [
            "From: " + self.email,
            "Subject: " + subject,
            "To: " + TARGET,
            "MIME-Version: 1.0",
            "Content-Type: text/html"]
        headers = "\r\n".join(headers)
        self.session.sendmail(
            self.email,
            self.email,
            headers + "\r\n\r\n" + body)


def create_poloniex_connection():
    polo = Poloniex()
    polo.key = POLONIEX_API_KEY
    polo.secret = POLONIEX_SECRET_KEY
    return polo


def add_sma(last_candle_list, sma_period):
    for i in range(len(last_candle_list)):
        if i < sma_period:
            last_candle_list[i]['sma'] = None
        else:
            last_candle_list[i]['sma'] = sum(
                [float(last_candle_list[j]['close']) for j in range(i - sma_period, i)]
            ) / sma_period
    return last_candle_list


def is_green(candle):
    return True if candle['close'] >= candle['open'] else False


def main():
    # Connect to Poloniex
    polo = create_poloniex_connection()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        filename='{}log/logger{}.log'.format(PROJECT_PATH,
                                                             time.strftime('%Y_%m_%d', datetime.datetime.now(
                                                             ).timetuple())))
    with open(PROJECT_PATH + 'bot_daily_btc_pairs.json') as data_file:
        pairs_bought = json.load(data_file)
    with open(PROJECT_PATH + 'bot_daily_btc_date.json') as data_file:
        last_bought_date = json.load(data_file)
    if pairs_bought != '':
        if pairs_bought != 'no pairs':
            balances = polo.returnBalances()
            null_balances_pairs = 0
            for pair in pairs_bought:
                altcoin_amount = float(balances[pair['name'].split('_')[-1]])
                if altcoin_amount > 0:
                    current_buy_glass = polo.returnOrderBook(pair['name'], depth=DEPTH_OF_SELLING_GLASS)['bids']
                    sum_previous = 0
                    sell_price = 0
                    for order in current_buy_glass:
                        sum_previous += float(order[1])
                        if float(sum_previous) >= BUY_ENSURE_COEF * altcoin_amount:
                            while True:
                                sell_price = float(order[0])
                                if sell_price != 0:
                                    break
                                else:
                                    logging.info('Sell price of {} = 0'.format(pair['name']))
                            break

                    if (time.time() - last_bought_date >= CANDLE_PERIOD):
                        polo.sell(pair['name'], sell_price, altcoin_amount)
                        logging.info(
                            'Selling {} {}. Price: {}'.format(altcoin_amount, pair['name'].split('_')[-1], sell_price))

                        gm = Gmail(GMAIL_USER, GMAIL_PASSWORD)
                        gm.send_message('SELL', 'Selling {} {}. Price: {}. Time: {}'.format(
                            altcoin_amount, pair['name'].split('_')[-1], sell_price, datetime.datetime.now()))
                    if float(polo.returnBalances()[pair['name'].split('_')[-1]]) > 0:
                        null_balances_pairs += 1

            if (time.time() - float(last_bought_date)) >= (CANDLE_PERIOD) and null_balances_pairs == 0:
                with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                    json.dump('', f)
        else:
            if (time.time() - float(last_bought_date)) >= (CANDLE_PERIOD):
                with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                    json.dump('', f)

    with open(PROJECT_PATH + 'bot_daily_btc_pairs.json') as data_file:
        pairs_bought = json.load(data_file)
    if pairs_bought == '':
        pairs_info = []
        currencies_info = polo.returnCurrencies()
        for pair in PAIRS:
            if currencies_info[pair.split('_')[-1]]['frozen'] == 1 or \
                            currencies_info[pair.split('_')[-1]]['delisted'] == 1:
                continue
            start_time = int(time.time()) - CANDLE_PERIOD * (CANDLES_NUM + SMA_NUM)
            four_h_data = polo.returnChartData(pair, period=CANDLE_PERIOD, start=start_time)
            candles_data = [
                {'high': float(candle['high']), 'low': float(candle['low']), 'volume': float(candle['volume']),
                 'close': float(candle['close']), 'open': float(candle['open']), 'date': float(candle['date'])}
                for candle in four_h_data
            ]
            candles_data = add_sma(candles_data, SMA_NUM)
 #           print(len(candles_data))
            candles_data = candles_data[50:]
            check_time = (int(time.time())//CANDLE_PERIOD) * CANDLE_PERIOD + 600
            if len(candles_data) != 50 and check_time < int(time.time()):
                 continue
            print(len(candles_data))
            print(pair)
            if not is_green(candles_data[1]):
                first_condition = True
            else:
                first_condition = False
            if candles_data[1]['volume'] > MIN_VOLUME:
                second_condition = True
            else:
                second_condition = False
            if candles_data[1]['volume'] > candles_data[0]['volume']:
                third_condition = True
            else:
                third_condition = False
            if max(candles_data[0]['open'], candles_data[0]['close']) / \
                    min(candles_data[0]['open'], candles_data[0]['close']) > RATIO_OPEN_CLOSE:
                fourth_condition = True
            else:
                fourth_condition = False
            if max(candles_data[1]['open'], candles_data[1]['close']) / \
                    min(candles_data[1]['open'], candles_data[1]['close']) > RATIO_OPEN_CLOSE:
                fifth_condition = True
            else:
                fifth_condition = False
            if candles_data[1]['sma'] > candles_data[1]['open']:
                sixth_condition = True
            else:
                sixth_condition = False
            if first_condition and second_condition and third_condition and\
                    fourth_condition and fifth_condition and sixth_condition:
                pairs_info.append({
                    'name': pair,
                    'coef': candles_data[1]['volume'] / candles_data[0]['volume']
                })
        logging.info('Number of pairs: {}'.format(len(pairs_info)))
        gm = Gmail(GMAIL_USER, GMAIL_PASSWORD)
        gm.send_message('PAIRS', 'Number of pairs: {}'.format(len(pairs_info)))

        pairs_info = sorted(pairs_info, key=lambda k: k['coef'], reverse=True)[:NUM_OF_PAIRS] if len(
            pairs_info) >= MIN_PAIRS else []
        balances = polo.returnBalances()
        current_btc = float(balances['BTC'])
        if len(pairs_info) > 0:
            buy_amount = TRADE_AMOUNT / len(pairs_info) if current_btc > TRADE_AMOUNT else current_btc / len(
                pairs_info)
            for pair_info in pairs_info:
                current_sell_glass = [
                    [float(order[0]), float(order[1]), float(order[0]) * float(order[1])]
                    for order in polo.returnOrderBook(pair_info['name'], depth=DEPTH_OF_SELLING_GLASS)['asks']
                ]
                sum_previous = 0
                order_price = 0
                for order in current_sell_glass:
                    sum_previous += order[2]
                    if sum_previous >= BUY_ENSURE_COEF * buy_amount:
                        order_price = order[0]
                        break
                if order_price:
                    polo.buy(pair_info['name'], order_price, buy_amount / order_price)
                    logging.info('Buying {} for {} BTC'.format(pair_info['name'].split('_')[-1], buy_amount))
                    pair_info['price'] = order_price

                    gm = Gmail(GMAIL_USER, GMAIL_PASSWORD)
                    gm.send_message(
                        'BUY_DAILY', 'Buying {}{} for {} BTC with rate {} at {}'.format(
                            buy_amount / order_price, pair_info['name'].split(
                                '_')[-1], buy_amount, order_price, datetime.datetime.now()))
            with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                json.dump([{'name': p['name'], 'price': p['price']} for p in pairs_info], f)
        else:
            with open(PROJECT_PATH + 'bot_daily_btc_pairs.json', 'w') as f:
                json.dump('no pairs', f)
        with open(PROJECT_PATH + 'bot_daily_btc_date.json', 'w') as f:
            json.dump((int(time.time())//CANDLE_PERIOD) * CANDLE_PERIOD + 60, f)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception('message')
