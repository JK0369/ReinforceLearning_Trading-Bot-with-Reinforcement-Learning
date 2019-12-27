# LSTM구현
# def __init__(self):
#     super(PPO, self).__init__()
#     self.data = []
#
#     self.fc1 = nn.Linear(4, 64)
#     self.lstm = nn.LSTM(64, 32)
#     self.fc_pi = nn.Linear(32, 2)
#     self.fc_v = nn.Linear(32, 1)
#     self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)
#
#
# def pi(self, x, hidden):
#     x = F.relu(self.fc1(x))
#     x = x.view(-1, 1, 64)
#     x, lstm_hidden = self.lstm(x, hidden)
#     x = self.fc_pi(x)
#     prob = F.softmax(x, dim=2)
#     return prob, lstm_hidden
#
#
# def v(self, x, hidden):
#     x = F.relu(self.fc1(x))
#     x = x.view(-1, 1, 64)
#     x, lstm_hidden = self.lstm(x, hidden)
#     v = self.fc_v(x)
#     return v



import gym
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical

# Hyperparameters
learning_rate = 0.0005
gamma = 0.98
lmbda = 0.95
# GAE(Generalized Advantage Estimation)
# 보통의 Advantage값 말고 GAE쓰는게 성능 더 높음
# TD-error와 lmbda곱해서 이용

eps_clip = 0.1
K_epoch = 3  # time step(20번)을 몇 번 반복해서 학습할지,
T_horizon = 20  # 몇 time step동안 data를 모을지

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

# on-policy라 중간중간 update->20step 간 후 경험 쌓고.. 진행

class PPO(nn.Module):
    def __init__(self):
        super(PPO, self).__init__()
        self.data = []

        self.fc1 = nn.Linear(9, 64)
        self.lstm = nn.LSTM(64, 32)
        self.fc_pi = nn.Linear(32, 3)
        self.fc_v = nn.Linear(32, 1)
        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

    # network
    """
            V:1                 Pi : 3
    (fully connected)   (fully connected, softmax)
                    H1:256 H2:256
           (Fully connected, Relu)
                    Input:9
    """

    def pi(self, x, hidden):
        # softmax_dim = batch처리 하기 위함(sample을 모아서
        # env 경험 쌓을 때 sample한 개 들어감 => softmax_dim=0
        # [s1, s2, s3,,] 행렬로 한 꺼번에 들어가면 -> softmax dim=1
        # simulation시 0, 학습 할 때는 1
        """
        soft max dim == 0 : 1행,2행 합이 1
        soft max dim == 1 : 1열,2열 합이 1
        """

        x = F.relu(self.fc1(x))
        x = x.view(-1, 1, 64)
        x, lstm_hidden = self.lstm(x, hidden)
        x = self.fc_pi(x)
        prob = F.softmax(x, dim=2)
        return prob, lstm_hidden

    # value
    def v(self, x, hidden):
        x = F.relu(self.fc1(x))
        x = x.view(-1, 1, 64)
        x, lstm_hidden = self.lstm(x, hidden)
        v = self.fc_v(x)
        return v

    # 데이터 넣는 것
    def put_data(self, transition):
        self.data.append(transition)

    # 리스트형 자료를 .tensor 형태로 바꾸어 주는 것
    def make_batch(self):
        s_lst, a_lst, r_lst, s_prime_lst, prob_a_lst, hidden_lst, done_lst = [], [], [], [], [], [], []
        for transition in self.data:
            s, a, r, s_prime, prob_a, hidden, done = transition

            s_lst.append(s)
            a_lst.append([a])  # 대괄호 이유 : s는 numpy array임-->[0.3, -0.2,..] // a는 int 값임 -> 그래서 대괄호로 만들어줌
            r_lst.append([r])  # dimension을 맞춰 주기 위해 괄호 안에 넣음
            s_prime_lst.append(s_prime)
            prob_a_lst.append([prob_a])
            hidden_lst.append(hidden)
            done_mask = 0 if done else 1
            done_lst.append([done_mask])

        # prob_a : 실제 내가 한 action의 확률 (old_policy)
        # torch.tensor : 행렬로 만드는 것 ... 행렬 계산시 쉬워짐
        s, a, r, s_prime, done_mask, prob_a = torch.tensor(s_lst, dtype=torch.float).to(device), torch.tensor(a_lst).to(
            device), \
                                              torch.tensor(r_lst).to(device), torch.tensor(s_prime_lst,
                                                                                           dtype=torch.float).to(
            device), \
                                              torch.tensor(done_lst, dtype=torch.float).to(device), torch.tensor(
            prob_a_lst).to(device)
        self.data = []
        return s, a, r, s_prime, done_mask, prob_a, hidden_lst[0]

    def train_net(self):
        s, a, r, s_prime, done_mask, prob_a, (h1, h2) = self.make_batch()
        # done_mask는 끝남을 위함 -> 끝났을 때 0을 가지며 곱했을 때 0만듦
        first_hidden = (h1.detach(), h2.detach())

        # GAE 계산
        for i in range(K_epoch):
            v_prime = self.v(s_prime, first_hidden).squeeze(1).to(device)
            td_target = r.float() + gamma * v_prime * done_mask.float()
            v_s = self.v(s, first_hidden).float().squeeze(1).to(device)
            delta = td_target - v_s
            delta = delta.detach().cpu().numpy()  # detach()를 안할 시, 고정되지 않고 그것도 업데이트 되므로(gradient)
            # gpu의 loss 계산되어 있지만, numpy로 바꾸려하면 오류가 뜸
            # sol) delta.detach().numpy() -> delta.detach().cpu().numpy()

            # v를 두 번만 호출해도 delta 계산 가능

            advantage_lst = []
            advantage = 0.0
            # loss함수 계산 GAE
            for delta_t in delta[::-1]:
                advantage = gamma * lmbda * advantage + delta_t[0]
                advantage_lst.append([advantage])
            advantage_lst.reverse()
            advantage = torch.tensor(advantage_lst, dtype=torch.float).to(device)

            pi, _ = self.pi(s, first_hidden)  # network로 확률 뽑는 것
            pi = pi.to(device)

            pi_a = pi.squeeze(1).gather(1,a)  # network중에서 실제 했었던 action a에 대한 확률
            # 인덱스 1에 실제 했던 action a가 모여 있는 것
            # (1,a) 의미: 1은 axis임 -> 첫 번째 축에서 고르라는 것
            # shape : [batch_size, 2] == 1은 두 번째 값임(2를 의미) // 0은 batch_size를 의미
            ratio = torch.exp(torch.log(pi_a) - torch.log(prob_a))  # a/b == exp(log(a)-log(b))

            surr1 = ratio * advantage
            surr2 = torch.clamp(ratio, 1 - eps_clip, 1 + eps_clip) * advantage
            loss = -torch.min(surr1, surr2) + F.smooth_l1_loss(v_s, td_target.detach())
            #  F.smooth_l1_loss(td_target.detach(), self.v(s)) : torch에서 제공하는 loss

            self.optimizer.zero_grad()  # optimizer의 gradient를 0으로 초기화
            loss.mean().backward(retain_graph=True)  # loss의 평균값에 gradient값 구함
            self.optimizer.step()  # gradient반영된 것에 weight 업데이트