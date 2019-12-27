from env import Env
import agent as PPOAgent
import utils as utils
import numpy as np
import torch
from torch.distributions import Categorical
import pandas as pd

# hyper parameters
threshold = 630  # threshold divide train_data to test_data
epochs = 3000
minibatch_size = 20
device = "cuda:0" if torch.cuda.is_available() else "cpu"
score_lst = []

# 변수 조정:
# agent에서 신경망 입력 수
# utils의 getScaler에서 low갯수 및 high에 첨가 데이터
# env의 reset, getObs에서 제외


if __name__ == "__main__":

    df = utils.getData()
    print(df)
    # df = df.iloc[:, 0:2]
    # data = np.around(df['bid'])

    env = Env(df, utils.getDeposit())

    scaler = utils.getScaler(env)  # 평균0 표준편차1로 만드는 스케일러
    # state = [stock owned, stock price, cash in hand]
    # action = [0, 1, 2]

    model = PPOAgent.PPO()
    model.to(device)  # cpu to gpu

    # print(model)
    # model.load_state_dict(torch.load('trade_model.npy'))
    # print(model.state_dict())

    for epoch in range(epochs):
        hidden = (torch.zeros([1, 1, 32], dtype=torch.float).to(device), torch.zeros([1, 1, 32], dtype=torch.float).to(device))
        score = 0.0
        s = env.reset()
        s = scaler.transform([s]) # scaler is required one dimension
        s = s[0]  # current dimension is one so re transform the (1*n) dimension
        done = False

        while not done:
            cnt = 0
            for t in range(minibatch_size):
                h_input = hidden
                cnt += 1
                prob, hidden = model.pi(torch.from_numpy(s).float().to(device), h_input)  # numpy to tensor
                m = Categorical(prob)  # prob=[0.2, 0.3, 0.5] => [0, 1, 2]
                a = m.sample().item()
                s_prime, r, done, info = env.step(a)
                s_prime = scaler.transform([s_prime])
                s_prime = s_prime[0]

                model.put_data((s, a, r / 100.0, s_prime, prob[0][0][a].item(), h_input, done))
                s = s_prime
                score = score + r
                if done:
                    break
            model.train_net()
        score_lst.append(score)
        if (epoch % 20 == 0 and epoch != 0) or (epoch+1 == epochs):
            print("epoch:{}, avg score:{}".format(epoch, score / cnt))
            print(info)
            score = 0.0

    time = utils.getCurTime()
    torch.save(model.state_dict(), utils.getDir()+'/'+time+'.npy')
    utils.drawLine(train_data, score_lst)


"""
1. save, model 후 test하는 것 구현
2. 일봉분 단위로 바꾸기, 거래량등 다양한 지표 집어넣기
3. softmax_dim을 0으로 할지, 1로 할 지 고민
"""