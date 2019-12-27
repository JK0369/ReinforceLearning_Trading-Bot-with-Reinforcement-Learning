import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import datetime
import os

def dfToList(df, cur_name):
    d = df[cur_name]
    length = len(d)
    lst = [d[i] for i in range(length)]
    return lst

def getData():
    data = pd.read_csv('C:\\Users\\com\\AppData\\Local\\Programs\\Python\\option\\my_data_total\\data.csv')
    return data

def getDeposit():
    data = pd.read_csv('C:\\Users\com\\PycharmProjects\\ThBot\myData\\cur_deposit.csv', usecols=[1], header=None)
    return int(np.array(data[1]))

def getScaler(env):
    low = [0] * 9
    high = []

    max_price = env.stock_price.max()
    max_cash = env.init_invest
    max_stock_owned = max_cash // max_price

    # obs[3] = self.bid
    # obs[4] = self.diff
    # obs[5] = self.offer
    # obs[6] = self.tvol
    # obs[7] = self.vol
    # obs[8] = self.volstr

    max_bid = env.bid.max()
    max_diff = env.diff.max()
    max_offer = env.offer.max()
    max_tvol = env.tvol.max()
    max_vol = env.vol.max()
    max_volstr = env.volstr.max()

    high.append(max_stock_owned)
    high.append(max_price)
    high.append(max_cash)

    high.append(max_bid)
    high.append(max_diff)
    high.append(max_offer)
    high.append(max_tvol)
    high.append(max_vol)
    high.append(max_volstr)

    scaler = StandardScaler()  # transform to means=0, std=1
    scaler.fit([low, high])
    return scaler

def drawLine(src_data, score_stack):
    plt.title("score")
    plt.xlabel("time")
    plt.ylabel("price")

    src_t = range(len(src_data))
    plt.subplot(2, 1, 1)
    plt.plot(src_t, src_data)

    t = range(len(score_stack))
    plt.subplot(2, 1, 2)
    plt.plot(t, score_stack)

    time = getCurTime()
    plt.savefig(getDir()+"/"+time+".png")
    plt.show()

def getDir():
    abs = os.path.dirname(os.path.realpath(__file__))
    path = abs+"/model"
    if not os.path.isdir(path):
        os.makedirs(path)
    return path

def getCurTime():
    time = datetime.datetime.now()
    time = str(time.month)+ "월" + str(time.day)+ "일, "+ str(time.hour)+" 시" + str(time.minute) +"분"
    return time