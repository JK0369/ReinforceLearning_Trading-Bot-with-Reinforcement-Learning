import gym
from gym.utils import seeding
import numpy as np
import utils as utils

# hyperparameters
trade_charge = 0.00015
tax_charge = 0.0025

# state : [stock owned, cur price, cash in hand]
# action : sell(0), hold(1), buy(2)
class Env(gym.Env):
    def __init__(self, df, init_invest):
        self.df = df
        length = len(df.index)
        self.history_price = utils.dfToList(df, "cur")  # history는 단지, 시간에 따른 현재가격임
        self.history_bid = utils.dfToList(df, "bid")
        self.history_diff = utils.dfToList(df, "diff")
        self.history_offer = utils.dfToList(df, "offer")
        self.history_tvol = utils.dfToList(df, "tvol")
        self.history_vol = utils.dfToList(df, "vol")
        self.history_volstr = utils.dfToList(df, "volstr")

        self.n_step = length
        self.init_invest = init_invest

        # state & action space
        self.cur_step = 0
        self.stock_price = 0
        self.stock_owned = 0

        self.bid = 0
        self.cur = 0
        self.diff = 0
        self.offer = 0
        self.tvol = 0
        self.vol = 0
        self.volstr = 0

        self.cash_in_hand = init_invest
        self.action_space = [0, 1, 2]

        self._seed()
        self._reset()

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def _reset(self):
        self.cur_step = 0
        self.stock_owned = 0

        self.bid = self.history_bid[self.cur_step]
        self.cur = 0  # 이 값은 필요 없을 수도?
        self.diff = self.history_diff[self.cur_step]
        self.offer = self.history_offer[self.cur_step]
        self.tvol = self.history_tvol[self.cur_step]
        self.vol = self.history_vol[self.cur_step]
        self.volstr = self.history_volstr[self.cur_step]

        self.stock_price = self.history_price[self.cur_step]
        self.cash_in_hand = self.init_invest
        return self._get_obs()

    # state 정의
    def _get_obs(self):
        obs = [-1, -1, -1, -1, -1, -1, -1, -1, -1]
        obs[0] = self.stock_owned
        obs[1] = self.stock_price
        obs[2] = self.cash_in_hand
        obs[3] = self.bid
        obs[4] = self.diff
        obs[5] = self.offer
        obs[6] = self.tvol
        obs[7] = self.vol
        obs[8] = self.volstr

        return np.array(obs, dtype=np.float)

    def _get_val(self):
        return np.sum(self.stock_owned * self.stock_price) + self.cash_in_hand

    def _step(self, action):
        prev_val = self._get_val()
        self.cur_step += 1
        self.stock_price = self.history_price[self.cur_step]
        self._trade(action)

        cur_val = self._get_val()

        reward = cur_val - prev_val
        done = self.cur_step == (self.n_step - 1)
        info = {'cur_val' : cur_val, 'prev_val':prev_val}
        return self._get_obs(), reward, done, info

    def _trade(self, action):

        if action==0:  # sell
            value = self.stock_price * self.stock_owned
            value = value * (1 - trade_charge - trade_charge)  # 매수 매도 각각 0.015%, 매도시 0.25%
            self.cash_in_hand += value
            self.stock_owned = 0

        if action==2:
            if self.cash_in_hand > self.stock_price:
                self.stock_owned += 1
                self.cash_in_hand -= (self.stock_price * (1 + trade_charge))

    """
    1. run.py에서 observation space 없으니까 3으로 고정할 것
    2. state 정의 다시 검토할 것 -- _get_obs부분
    """