# -*- coding: utf-8 -*-
import win32com.client
import copy
import os
import datetime
import csv
import ctypes
import time
from queue import PriorityQueue

# 잔고 정보 불러오기
class Cp6033:
    def __init__(self):

        self.instCpTdUtill = win32com.client.Dispatch('CpTrade.CpTdUtil')
        initCheck = self.instCpTdUtill.TradeInit(0)
        if (initCheck != 0):
            print("주문 초기화 실패")
            return

        self.acc = self.instCpTdUtill.AccountNumber[0]
        self.accFlag = self.instCpTdUtill.GoodsList(self.acc, 1)  # 주식상품 구분

        self.instCp6033 = win32com.client.Dispatch("CpTrade.CpTd6033")
        self.setValue()

        self.dicflag1 = {ord(' '): u'현금',
                         ord('Y'): u'융자',
                         ord('D'): u'대주',
                         ord('B'): u'담보',
                         ord('M'): u'매입담보',
                         ord('P'): u'플러스론',
                         ord('I'): u'자기융자',
                         }

        # sleep for continuous get balance data in requestJango
        self.g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')

    def setValue(self):
        self.instCp6033.SetInputValue(0,self.acc)  # 계좌번호
        self.instCp6033.SetInputValue(1, self.accFlag[0])  # 주식상품 구분 첫번째것
        self.instCp6033.SetInputValue(2, 50)  # 요청 건수 : 최대 50

    def checkandWait(self, type):
        remainCount = self.g_objCpStatus.GetLimitRemainCount(type)
        print(u'remain of count ', remainCount)
        if remainCount <= 0:
            print(u'sleep for continuous of playing get data in balance', self.g_objCpStatus.LimitRequestRemainTime / 1000 +1)
            time.sleep(self.g_objCpStatus.LimitRequestRemainTime / 1000 + 1)

    # 실제적인 6033 통신 처리
    def requestJango(self, caller):

        # sleep for continuous get data in balance
        self.checkandWait(0)
        self.checkandWait(1)

        self.instCp6033.BlockRequest()

        # 통신 및 통신 에러 처리
        rqStatus = self.instCp6033.GetDibStatus()
        rqRet = self.instCp6033.GetDibMsg1()
        print("6033 통신상태(rqStatus, rqRet)=", rqStatus, rqRet)

        if rqStatus != 0 or rqRet == "":
            print('*failed requestJango')
            return False

        cnt = self.instCp6033.GetHeaderValue(7)
        print('종목 수 = ',cnt)

        for i in range(cnt):
            item = {}
            item['code'] = self.instCp6033.GetDataValue(12, i)  # 종목코드
            item['name'] = self.instCp6033.GetDataValue(0, i)  # 종목명
            item['category'] = self.dicflag1[self.instCp6033.GetDataValue(1, i)]  # 신용구분
            item['num'] = self.instCp6033.GetDataValue(7, i)  # 체결잔고수량 : 가지고있는 주식수
            item['check'] = self.instCp6033.GetDataValue(15, i)  # 매도가능
            item['priceAtTrade'] = self.instCp6033.GetDataValue(17, i)  # 체결장부단가
            # item['평가금액'] = self.objRq.GetDataValue(9, i)  # 평가금액(천원미만은 절사 됨)
            # item['평가손익'] = self.objRq.GetDataValue(11, i)  # 평가손익(천원미만은 절사 됨)

            # 수익률
            # self.instCp6033.GetDataValue(11, i)  # 수익률
            # 또 다른 방법
            # object.SetInputValue(3, 2)  #  3:수익률 / 1:100%기준, 2:0%기준
            # value = object.GetHeaderValue(8)  # 수익률 반환

            item['sumPrice'] = item['priceAtTrade'] * item['num']  # 매입금액 = 장부가 * 잔고수량
            item['time'] = datetime.datetime.now()
            # 계좌정보 : (code, code/name/category/num/check/priceAtTrade/sumPrice/time)
            caller[item['code']] = item
        return True


class GetDataCybos:
    def __init__(self):

        # 연결
        self.instCpCybos = win32com.client.Dispatch("CpUtil.CpCybos")

        # 프로젝트 폴더에 저장할 폴더(my_data_list)가 없을시 생성
        self.dataSpace = self.mkdirMine("my_data_list")  # dataSpace : 폴더/my_data_list

        # 사용할 변수
        self.kospiName = {}
        self.kospiAvgPrice = {}
        self.kospiCurPrice = {}
        self.kospiLowerPrice = {}
        self.kospiCurLowerPERByLowerPrice = {}
        self.kospiBestStockByPriority = {}
        # 코스피 코드,이름 정보
        self.instCpCodeMgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")

        # 평균값, 현재값, PER 구함
        self.instStockChart = win32com.client.Dispatch("CpSysDib.StockChart")

        # PER 탐색
        self.instStockMst = win32com.client.Dispatch("dscbo1.StockMst")

        # 자동 매매
        self.instCpTdUtil = win32com.client.Dispatch("CpTrade.CpTdUtil")
        self.instCpTdUtil.TradeInit()

        self.instCpTd0311 = win32com.client.Dispatch("CpTrade.CpTd0311")

        # 계좌 정보를 불러와서, 엑셀에 정리
        self.instCp6033 = Cp6033()

    # 프로젝트 폴더에 저장할 폴더(my_data_list)가 없을시 생성
    def mkdirMine(self, dir):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        dir = os.path.join(BASE_DIR, dir)
        if not (os.path.isdir(dir)):
            os.makedirs(dir)
        return dir

    # 연결 확인
    def isConnected(self):
        if self.instCpCybos.IsConnect == 1:
            print('*succeeded connect')
        else:
            print('*failed connect')
            exit(-1)

        # 프로세스가 관리자 권한으로 실행 여부
        if ctypes.windll.shell32.IsUserAnAdmin():
            print('정상: 관리자권한으로 실행된 프로세스입니다.')
        else:
            print('오류: 일반권한으로 실행됨. 관리자 권한으로 실행해 주세요')
            exit(-1)

    # 상장중인 {코드,이름} 딕셔너리로 받아옴 (ETF와 ETN제외)
    def getKospiStockCode(self):
        codeList = self.instCpCodeMgr.GetStockListByMarket(1)
        dictionary = {}
        for i, code in enumerate(codeList):
            # secondCode = 1:주권 / 10:ETF / 17:ETN
            secondCode = self.instCpCodeMgr.GetStockSectionKind(code)

            if secondCode != 1:  # secondCode == 13 or secondCode == 17:
                continue
            name = self.instCpCodeMgr.CodeToName(code)
            dictionary[code] = name
        return dictionary

    # kospi 딕셔너리를 보기 편하게 하기 위해 엑셀에 저장
    def saveToCsv(self, kospi, title):
        dirPath= self.dataSpace + "\\"
        f = open(dirPath + title + '.csv', 'w')
        for key, value in kospi.items():
            # unicode to str
            if type(value) == type(u'1'):
                value = value.encode('euc_kr')
            key = key.encode('utf8')
            f.write("%s, %s\n" % (key, value))
        f.close()

    # 365일 기준 평균가 = (고가+저가)/2
    def setAvgStockByDay(self, code):

        self.instStockChart.SetInputValue(0, code)  # 종목코드 입력
        self.instStockChart.SetInputValue(1, ord("2"))  # 개수로 요청
        self.instStockChart.SetInputValue(4, 365)  # 365일치
        self.instStockChart.SetInputValue(6, ord("D"))  # 일 단위 데이터
        self.instStockChart.SetInputValue(5, [3, 4])  # 3:고가 / 4:저가
        self.instStockChart.SetInputValue(9, ord('1'))  # 수정 주가 사용

    # n일치 데이터의 평균가격 반환
    def getAvgPrice(self):
        # numData = n일치 데이터 수신
        # numField = 2 (고가와 저가)
        numData = self.instStockChart.GetHeaderValue(3)
        numField = self.instStockChart.GetHeaderValue(1)

        # i는 날짜 / j는 고가,저가
        avgPrice = 0.0
        for i in range(numData):
            sum = 0
            for j in range(numField):
                sum += self.instStockChart.GetDataValue(j, i)
            avgPrice += sum / 2.0
        avgPrice = avgPrice / numData
        return avgPrice

    def getAvgStockAndCurPrice(self, kospi):
        n = 0
        kospiAvgPrice = copy.deepcopy(kospi)
        kospiCurPrice = copy.deepcopy(kospi)

        print('=== getAvgStockAndCurPrice ===')
        for code, _ in kospiCurPrice.items():
            n += 1
            print(n)
            print(code, _)
            self.setAvgStockByDay(code)
            self.instStockChart.BlockRequest()
            kospiCurPrice[code] = self.instStockChart.GetHeaderValue(7)  # 현재가
            kospiAvgPrice[code] = self.getAvgPrice()  # 평균가
            # time.sleep(0.5)
        return kospiAvgPrice, kospiCurPrice

    # PER 구함
    def getLowerPER(self, targetKospi):
        kospiCurLowerPER = {}
        n = 0
        for code, _ in targetKospi.items():
            self.instStockMst.SetInputValue(0, code)  # PER구하기 위함
            self.instStockMst.BlockRequest()
            PER = self.instStockMst.GetHeaderValue(28)  # PER값
            if(PER != 0) and (PER <= 12):
                kospiCurLowerPER[code] = PER
                n += 1
                print(n)
                print(code, kospiCurLowerPER[code])
        return kospiCurLowerPER

    # 현재가가 평균값에서 떨어진 정도(평균값-평균값*퍼센트) 보다 낮은 경우 search
    # 인수는 딕셔너리
    def getLowerPrice(self, percent):
        targetDict = {}
        n = 0
        for code, _ in self.kospiCurPrice.items():
            n += 1
            if (self.kospiCurPrice[code] <= self.kospiAvgPrice[code] * percent):
                targetDict[code] = self.kospiAvgPrice[code] * percent
                self.kospiLowerPrice[code] = self.kospiAvgPrice[code] * percent
        return targetDict

    # 자동 매수
    # 객체, 종목코드, 주문수량, 주문단가
    def setAutoTradingBuying(self, code, num, price):
        accountNumber = self.instCpTdUtil.AccountNumber[0]
        self.instCpTd0311.SetInputValue(0, 2)  # 0:주문 종류 코드 / 1:매도, 2:매수
        self.instCpTd0311.SetInputValue(1, accountNumber)  # 1:계좌 번호 / 값:주문을 수행할 계좌
        self.instCpTd0311.SetInputValue(2, "10")  # 2: 상품관리 코드 / "01"실제투자, "10" 모의투자
        self.instCpTd0311.SetInputValue(3, code)  # 3:종목 코드 / 값 : 주문할 종목의 종목 코드
        self.instCpTd0311.SetInputValue(4, num)  # 4: 주문 수량 / 값 : 주문수량
        self.instCpTd0311.SetInputValue(5, price)  # 5:주문 단가 / 값 : 주문 단가
        self.instCpTd0311.SetInputValue(7, "0")  # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
        self.instCpTd0311.SetInputValue(8, "01")  # 주문호가 구분코드 - 01: 보통

    def requestAndBuying(self, code, price, num):
        ret = self.instCpTd0311.BlockRequest()
        time = datetime.datetime.now()

        # 통신 및 통신 에러 처리
        rqStatus = self.instCpTd0311.GetDibStatus()
        rqRet = self.instCpTd0311.GetDibMsg1()
        print("0311 통신상태(rqStatus, rqRet)=", rqStatus, rqRet)

        time = datetime.datetime.now()
        if rqStatus == 0 and ret == 0:
            print(time, '*매수 성공 (code,price,num) =(', code, price, num, ')')
            # self.addToCsv(code, price, num)
        else:
            print(time, '매수 실패')

    def requestAndSell(self, code, price, num):
        ret = self.instCpTd0311.BlockRequest()
        if ret == 0:
            time = datetime.datetime.now()
            print(time, '*매도 성공 =', code)

    # 자동매수
    def autoTradeBuying(self):
        weightNumList = self.getNumByWeight()  # 각 주식을 몇 개씩 매수할 것인가판단
        print(weightNumList)
        for code, per in self.kospiCurLowerPERByLowerPrice.items():
            price = self.kospiCurPrice[code]
            num = weightNumList[code]
            self.setAutoTradingBuying(code, num, price)  # 객체, 종목코드, 주문수량, 주문단가
            self.requestAndBuying(code, price, num)


        # # 자동매수 후, 계좌 정보를 액셀에 저장
        # accInfo = {}  # 현재 나의 계좌에 있는 정보가 들어갈 딕셔너리
        # isRun = self.instCp6033.requestJango(accInfo)
        # if isRun:
        #     print ('*succeed buying')
        # else :
        #     print ('*failed buying in autoTradeBuying')
        #
        # print accInfo, '-- in auto Trade Buying'
        # self.saveToCsv2(accInfo, 'accInfo.csv')

    def saveToCsv2(self, multiData, title):
        dirPath = self.dataSpace + "\\"
        path = dirPath + title + '.csv'

        # 계좌정보 : 'category', 'code': 'name', 'num': 'sumPrice', 'priceAtTrade', 'time', 'check'
        # 기존 파일이 없으면 헤더를 쓴 엑셀 생성
        infoHeader = ['category', 'code', 'name', 'num', 'sumPrice', 'priceAtTrade', 'time', 'check']
        if not os.path.isfile(path):
            f = open(path, 'w')
            wr = csv.writer(f)
            wr.writerow(infoHeader)
            f.close()

        # 데이터 저장 준비 : 행 추가
        f = open(path, 'a')
        writer = csv.writer(f)

        for key, value in multiData.items():
            listTmp = []
            for key2, value2 in value.items():
                # unicode to str
                if type(value2) == type(u'1'):
                    value2 = value2.encode('euc_kr')
                key = key.encode('utf8')
                listTmp.append(value2)
            writer.writerow(listTmp)
        f.close()

    def addToCsv(self, code, price, num):
        dir = self.dataSpace + "my_data_list\\"
        file = "accountList.csv"
        if not (os.path.isfile(dir+file)):
            open(dir + file, 'w')

        f = open(dir+file, 'a')
        writer = csv.writer(f)
        writer.writerow([code, price, num])

    # 예수금
    def getDeposit(self):
        acc = self.instCpTdUtil.AccountNumber[0]  # 계좌번호
        accFlag = self.instCpTdUtil.GoodsList(acc, 1)  # 주식상품 구분

        objRq = win32com.client.Dispatch("CpTrade.CpTdNew5331A")
        objRq.SetInputValue(0, acc)  # 계좌번호
        objRq.SetInputValue(1, accFlag[0])  # 상품구분 - 주식 상품 중 첫번째
        objRq.BlockRequest()

        t = datetime.datetime.now()
        t = str(t.year) + '.' + str(t.month) + '.' + str(t.day) + '/' + str(t.hour) + ':' + str(t.minute)
        cur_deposit = {}
        cur_deposit[t] = objRq.GetHeaderValue(47)
        self.saveToCsvBySort(cur_deposit, 'cur_deposit')

        return objRq.GetHeaderValue(47)  # 가능 예수금 조회

    # 비율에 따라 매수 갯수 구하는것
    def getNumByWeight(self):
        ratioPriceByAvg = {}
        sumRatio = 0.0
        PriceList = {}  # 형태 => code, 갯수

        # 각 비율, 총 비율 합
        for code, _ in self.kospiCurLowerPERByLowerPrice.items():
            ratioPriceByAvg[code] = self.kospiCurPrice[code] / (self.kospiAvgPrice[code] + .0)
            sumRatio += ratioPriceByAvg[code]
            PriceList[code] = 0

        # 총합이 1로되게끔 비율 조정
        for code, _ in self.kospiCurLowerPERByLowerPrice.items():
            ratioPriceByAvg[code] = ratioPriceByAvg[code] / sumRatio
            ratioPriceByAvg[code] = (round(ratioPriceByAvg[code], 1) * 10) % 10

        # 정렬 후 본격적인 카운트
        # value 기준으로 정렬
        item = sorted(ratioPriceByAvg, key=lambda k: ratioPriceByAvg[k])
        # item = {코드만 나옴}

        sum = 0
        balance = self.getDeposit()

        while (sum < balance):
            for code in item:
                n = ratioPriceByAvg[code]
                sum += self.kospiCurPrice[code] * n
                if sum < balance:
                    PriceList[code] += int(n)
                else:
                    return PriceList
        return PriceList

    # 자동 매도
    def autoTradeSell(self):
        # 자동 매도를 위해서 불러올 종목 탐색
        kospiTargetDict = self.targetDictForSell()  # 반환값 : 현재 계좌 정보 모든 것

        for code, _ in kospiTargetDict.items():
            curPrice = self.kospiCurPrice[code]
            lastPrice = kospiTargetDict[code]['priceAtTrade']
            incentive = lastPrice*(0.00015) + curPrice*(0.00015 + 0.003)
            profitForRatio = (curPrice - lastPrice - incentive + 0.0) / (curPrice)

            if profitForRatio > 0.04:  # 수익률이 4프로 이상이면 매도
                print("PV ratio is higher than 4% =>", profitForRatio * 100)
                num = kospiTargetDict[code]['num']
                self.setAutoTradingSell(code, num)
                self.instCpTd0311.BlockRequest()

                rqStatus = self.instCpTd0311.GetDibStatus()
                rqRet = self.instCpTd0311.GetDibMsg1()
                print("통신상태", rqStatus, rqRet)
                if rqStatus != 0:
                    exit()
            else:
                print("PV ratio is lower than 4% =>", profitForRatio * 100)


    # 자동 매매를 위해서 불러올 종목
    def targetDictForSell(self):
        # 자동매수 후, 계좌 정보를 액셀에 저장
        accInfo = {}  # 현재 나의 계좌에 있는 정보가 들어갈 딕셔너리
        isRun = self.instCp6033.requestJango(accInfo)
        if isRun:
            print ('*succeed loading file')
        else:
            print ('*faild loading file')
        return accInfo

    # 객체, 종목코드, 주문수량, 주문단가
    def setAutoTradingSell(self, code, num):
        accountNumber = self.instCpTdUtil.AccountNumber[0]
        self.instCpTd0311.SetInputValue(0, 1)  # 0:주문 종류 코드 / 1:매도, 2:매수
        self.instCpTd0311.SetInputValue(1, accountNumber)  # 1:계좌 번호 / 값:주문을 수행할 계좌
        self.instCpTd0311.SetInputValue(2, "10")  # 2: 상품관리 코드 / "01"실제투자, "10" 모의투자
        self.instCpTd0311.SetInputValue(3, code)  # 3:종목 코드 / 값 : 주문할 종목의 종목 코드
        self.instCpTd0311.SetInputValue(4, num)  # 4: 주문 수량 / 값 : 주문수량
        self.instCpTd0311.SetInputValue(5, self.kospiCurPrice[code])  # 5:주문 단가 / 값 : 주문 단가
        self.instCpTd0311.SetInputValue(7, "0")  # 주문 조건 구분 코드, 0: 기본 1: IOC 2:FOK
        self.instCpTd0311.SetInputValue(8, "01")  # 주문호가 구분코드 - 01: 보통

    # lower per by price 중에서 best 주식 가져옴, 형식 : {우선순위, (code, curPrice)}
    def getBestStockByQue(self, kospiCurLowerPERByLowerPrice):
        que = PriorityQueue()
        for code, per in kospiCurLowerPERByLowerPrice.items():
            # que.put((우선순위, 데이터)),, 우선순위는 수 작은게 높은 것
            curPrice = self.kospiCurPrice[code]
            priceOfPercent = self.kospiLowerPrice[code]
            ratio = (curPrice) / (priceOfPercent +0.0)  # 현재가가 작아야 우선순위 높은 것->값이 작은 것이 우선순위높
            que.put((ratio, code))

        n = 0
        while(que.qsize()):
            n += 1
            data = que.get()
            code = data[1]
            self.kospiBestStockByPriority[str(n)] = code
        return self.kospiBestStockByPriority

    # get avg price by days : information about one stock's price from past to current
    days = 365*1
    def getAvgPriceByDays(self, target_code, day=days):
        stock_avg = {}
        self.instStockChart.SetInputValue(0, target_code)  # set the stock code
        self.instStockChart.SetInputValue(1, ord("2"))  # request by num
        self.instStockChart.SetInputValue(4, day)  # day : num of information
        self.instStockChart.SetInputValue(6, ord("D"))  # data by days
        self.instStockChart.SetInputValue(5, [0, 3, 4])  # 3:high price / 4:low price
        self.instStockChart.SetInputValue(9, ord('1'))  # 수정 주가 사용
        self.instStockChart.BlockRequest()

        num_data = self.instStockChart.GetHeaderValue(3)  # get the n days data
        num_field = self.instStockChart.GetHeaderValue(1)  # get 3 (day, high price, low price)

        for get_day in range(num_data):  # get_day가 0이면 현재, 멀수록 과거

            index = str(self.instStockChart.GetDataValue(0, get_day))
            high = self.instStockChart.GetDataValue(1, get_day)
            low = self.instStockChart.GetDataValue(2, get_day)
            sum = high + low
            stock_avg[index] = sum / 2.0

        return stock_avg
    # / get avg price by days

    def saveToCsvBySort(self, dict, title):
        dirPath= self.dataSpace + "\\"
        f = open(dirPath + title + '.csv', 'w')
        sorted_lst = sorted(dict.items(), reverse=False)
        for key, value in sorted_lst:
            # unicode to str
            if type(value) == type(u'1'):
                value = value.encode('euc_kr')
            key = key.encode('utf8')
            f.write("%s, %s\n" % (key, value))
        f.close()

class Bot1():
    def run(self):
        while True:
            cybos = GetDataCybos()
            # 연결 확인
            cybos.isConnected()

            # 코스피 코드,이름 정보
            kospi = cybos.getKospiStockCode()

            # 평균값, 현재값, PER
            cybos.kospiAvgPrice, cybos.kospiCurPrice = cybos.getAvgStockAndCurPrice(kospi)

            # 평균가에 퍼센트 곱한 만큼 작은 것 탐색
            threshold = 0.5
            cybos.kospiLowerPrice = cybos.getLowerPrice(threshold)  # 0.5일시, 평균값의 50프로 이하인것 -> 평균 * 0.5
            print("threshold={}".format(threshold))

            # PER 탐색
            cybos.kospiCurLowerPERByLowerPrice = cybos.getLowerPER(cybos.kospiLowerPrice)
            cybos.saveToCsv(cybos.kospiCurLowerPERByLowerPrice, 'CurLowerPERByLowerPrice')

            # lower per by lower price된 target의 가장 좋은(현재가격이 가장낮은) 코드 불러옴
            target_stock = cybos.getBestStockByQue(cybos.kospiCurLowerPERByLowerPrice)
            cybos.saveToCsvBySort(target_stock, 'target_priority_price')
            # target_stock -> {'우선순위', code}

            # days만큼의 평균 값 가져오기
            if len(target_stock)==0:
                print("데이터 존재하지 않음 - exit")
                continue
                exit(0)

            print("threshold={}인 데이터 발견".format(threshold))
            stock_by_days = cybos.getAvgPriceByDays(target_stock['1'])
            cybos.saveToCsvBySort(stock_by_days, 'target')

            # current price save by csv
            cybos.getDeposit()

            # 자동매수
            cybos.autoTradeBuying()

            # 자동매도
            cybos.autoTradeSell()