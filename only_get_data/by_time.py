import sys
import pandas
import win32com.client
import pandas as pd
import ctypes  # 관리자 권한 확인
import os
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')  # plus 연결 확인
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')  # 주문 초기화 확인

def InitPlusCheck():
    # 프로세스가 관리자 권한으로 실행 여부
    if ctypes.windll.shell32.IsUserAnAdmin():
        print('정상: 관리자권한으로 실행된 프로세스입니다.')
    else:
        print('오류: 일반권한으로 실행됨. 관리자 권한으로 실행해 주세요')
        return False

    # 연결 여부 체크
    if (g_objCpStatus.IsConnect == 0):
        print("PLUS가 정상적으로 연결되지 않음. ")
        return False

    # 주문 관련 초기화
    if (g_objCpTrade.TradeInit(0) != 0):
        print("주문 초기화 실패")
        return False

    return True

# CpStockBid: 시간대별 조회
class CpStockBid:
    def __init__(self):
        if(InitPlusCheck() == False):
            exit(-1)
        self.objSBid = win32com.client.Dispatch("Dscbo1.StockBid")
        return

    def Request(self, code):
        # 현재가 통신
        self.objSBid.SetInputValue(0, code)
        self.objSBid.SetInputValue(2, 80)  # 요청개수 (최대 80)
        self.objSBid.SetInputValue(3, ord('C'))  # C 체결가 비교 방식 H 호가 비교방식

        times = []
        curs = []
        diffs = []
        tvols = []
        offers = []
        bids = []
        vols = []
        offerbidFlags = []  # 체결 상태 '1' 매수 '2' 매도
        volstrs = []  # 체결강도
        marketFlags = []  # 장구분 '1' 동시호가 예상체결' '2' 장중

        # 누적 개수 - 300 개까지만 하자
        sumCnt = 0
        time = 0
        while True:
            if int(time) > 153000:
                continue
            if int(time) < 90000 and time != 0:
                break
            ret = self.objSBid.BlockRequest()
            if self.objSBid.GetDibStatus() != 0:
                print("통신상태", self.objSBid.GetDibStatus(), self.objSBid.GetDibMsg1())
                return False

            cnt = self.objSBid.GetHeaderValue(2)
            sumCnt += cnt
            if cnt == 0:
                break

            strcur = ""
            strflag = ""
            strflag2 = ""
            for i in range(cnt):
                time = self.objSBid.GetDataValue(9, i)
                if int(time) > 153000:
                    continue
                if int(time) < 90000 and time != 0:
                    break
                times.append(time)
                cur = self.objSBid.GetDataValue(4, i)
                diffs.append(self.objSBid.GetDataValue(1, i))
                vols.append(self.objSBid.GetDataValue(5, i))
                tvols.append(self.objSBid.GetDataValue(6, i))
                offers.append(self.objSBid.GetDataValue(2, i))
                bids.append(self.objSBid.GetDataValue(3, i))
                flag = self.objSBid.GetDataValue(7, i)
                if (flag == ord('1')):
                    strflag = "체결매수"
                else:
                    strflag = "체결매도"
                offerbidFlags.append(strflag)
                volstrs.append(self.objSBid.GetDataValue(8, i))
                flag = self.objSBid.GetDataValue(10, i)
                if (flag == ord('1')):
                    strflag2 = "예상체결"
                    # strcur = '*' + str(cur)
                else:
                    strflag2 = "장중"
                    # strcur = str(cur)
                marketFlags.append(strflag2)
                curs.append(cur)

            if (sumCnt > 1200):
                break

            if self.objSBid.Continue == False:
                break

        if len(times) == 0:
            return False

        # sBidCol = {'1time': times,
        #            'cur': curs,
        #            'diff': diffs,
        #            'vol': vols,
        #            'tvol': tvols,
        #            'offer': offers,
        #            'bid': bids,
        #            'flag': offerbidFlags,
        #            'market': marketFlags,
        #            'volstr': volstrs}

        sBidCol = {'1time': times,
                   'cur': curs,
                   'diff': diffs,
                   'vol': vols,
                   'tvol': tvols,
                   'offer': offers,
                   'bid': bids,
                   'volstr': volstrs}
        # 추가 : 호가 현황

        df = pd.DataFrame(sBidCol)
        df = df.iloc[::-1]
        print(df)
        if not (os.path.isdir("my_data_total")):
            os.makedirs("my_data_total")
        df.to_csv("my_data_total/data.csv", index=False)
        return True

if __name__=="__main__":
    InstBid = CpStockBid()
    code = "A088350"
    if(InstBid.Request(code) == True):
        print("complete")