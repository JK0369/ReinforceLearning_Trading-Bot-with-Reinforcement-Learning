# -*- coding: utf-8 -*-

# cmd -> pip install pywinauto
# anaconda prompt로 anaconda2/pkgs에 접근하여 설치
from pywinauto import application
from pywinauto import timings
import time
import win32gui

# 실행
def startCybos(app):
    app.start("C:\DAISHIN\STARTER\\ncStarter.exe /prj:cp")
    time.sleep(3)

# yes버튼 -> auto hot key로 해결 (실행시 권리자권한으로 해야 작동됨)
""" 다음 방법은 보안때문에 안됨
import win32con
# hwnd = win32gui.GetForegroundWindow()
hwnd = win32gui.FindWindow(None, u"대신증권 CYBOS FAMILY")

win32gui.SendMessage(hwnd, win32con.WM_COMMAND, win32con.IDOK, 0)
# LRESULT SendMessage(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
# 윈도우 핸들, 전달메세지, 부가정보
"""

#---------start-----------

# dlg로 바인딩하여 비번입력
app = application.Application()
startCybos(app)
title = 'CYBOS Starter'
dlg = timings.wait_until_passes(20, 0.5, lambda: app.connect(title=title)).Dialog

# print list of dlg
app.dlg.print_control_identifiers()

pass_ctrl = dlg.Edit2
time.sleep(10)
pass_ctrl.set_focus()
pass_ctrl.type_keys("eldqn7!")
cert_ctrl = dlg.Edit3
cert_ctrl.set_focus()
cert_ctrl.type_keys("gleldqn77&")
btn_ctrl = dlg.Button
btn_ctrl.click()

# "종합계좌 비밀번호 확인 입력" 팝업
title = u'종합계좌 비밀번호 확인 입력'
dlg = timings.wait_until_passes(20, 0.5, lambda: app.connect(title=title)).Dialog
app.dlg.print_control_identifiers()
pass_ctrl = dlg.Edit2
time.sleep(3)
pass_ctrl.set_focus()
pass_ctrl.type_keys("0569")
btn_ctrl = dlg.Button
btn_ctrl.click()