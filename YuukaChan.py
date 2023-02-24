# DPTech FW Series SSH Operator YuukaChan
# Powered By Luckykeeper <luckykeeper@luckykeeper.site | https://luckykeeper.site>

from netmiko import ConnectHandler
# from pprint import pprint

import re
import time

# EXCEL reader
import xlrd
#  CLI
import argparse

# DPTech FW 取消分页，输出所有结果
def DPTechFWShell_withoutPaging(dev, cmd, enableMode):
    with ConnectHandler(**dev) as conn:
        # 存放回显的变量
        output = ''
        # 判断回显结束的正则
        output_end_pattern = r'<\S+>'
        if enableMode == "enable":
            output_end_pattern = "endTagByHayaseYuuka"
        # 判断分页交互的正则
        more_pattern = ' --More(CTRL+C break)--'

        # 超时时间，隧道中读取内容的间隔时间，根据二者计算的循环次数
        timeout = conn.timeout
        loop_delay = 0.2
        loops = timeout / loop_delay
        i = 0
        # 通过write_channel发送命令，命令后追加一个回车换行符
        print(time.strftime("%Y-%m-%d %H:%M:%S",
              time.localtime()), "模拟用户输入以下指令", cmd)
        if enableMode == "enable":
            print("enableMode:True")
            conn.write_channel('{}{}'.format("conf", conn.RETURN))
            conn.write_channel('{}{}'.format("", conn.RETURN))
            conn.write_channel('{}{}'.format(cmd, conn.RETURN))
            conn.write_channel('{}{}'.format("", conn.RETURN))
            # 手动输入 endTag ，辅助识别
            conn.write_channel('{}{}'.format("endTagByHayaseYuuka and Powered By Luckykeeper <luckykeeper@luckykeeper.site | https://luckykeeper.site>", conn.RETURN))
        else:
            conn.write_channel('{}{}'.format(cmd, conn.RETURN))
        # 进入循环，读取隧道中信息
        while i <= loops:
            # 读取隧道中的信息，放入chunk_output
            chunk_output = conn.read_channel()
            # 判断是否有分页交互提示
            if more_pattern in chunk_output:
                # 回显中的分页提示去除,去除一些影响回显展示的空格
                chunk_output = chunk_output.replace(
                    more_pattern, '').replace('               ', '')
                # 拼接回显
                output += chunk_output
                # 发送回车换行符
                conn.write_channel(conn.RETURN)
            # 根据提示符判断是否回显结束
            elif re.search(output_end_pattern, chunk_output):
                # 拼接回显 并跳出循环
                output += chunk_output
                break
            # 停顿loop_delay秒
            time.sleep(loop_delay)
            i += 1
        # 如果超过了，则证明超时，我们可以自己抛出异常
        if i > loops:
            raise Exception('执行命令"{}"超时'.format(cmd))
        return output


# 业务流程
def HayaseYuuka(debugYuuka):

    global interfacesInfo
    interfacesInfo = {}

    if debugYuuka:
        print("Debug 标记：", debugYuuka, "，以调试环境模式启动")
    else:
        # Debug
        print("Debug 标记：", debugYuuka, "，以生产环境模式启动")

    # 读取 EXCEL 基本信息表
    YuukaBook = xlrd.open_workbook('./YuukaChan.xls')
    if debugYuuka:
        print("xls文件加载状态：",YuukaBook.sheet_loaded(0))
        print("Sheet列表：",YuukaBook.sheet_names())
    basicInfoSheet = YuukaBook.sheet_by_name('设备信息')
    NATServerSheet = YuukaBook.sheet_by_name('基于接口IP的NATServer端口映射表')

    # 定时执行任务
    while True:
        try:
            # 获取基本信息
            # 行、列数均从 0 开始计
            YuukaDeviceIp=str(basicInfoSheet.row(4)[1].value)
            YuukaDeviceApiAccount=str(basicInfoSheet.row_values(4)[2])
            YuukaDeviceApiPassword=str(basicInfoSheet.row_values(4)[3])
            YuukaDeviceWANPorts=str(basicInfoSheet.row_values(4)[4])
            HayaseYuukaSleepTime=str(basicInfoSheet.row_values(4)[5])

            # 解析出接口名称
            YuukaDeviceWANPortList=YuukaDeviceWANPorts.split(",")

            if debugYuuka:
                print("设备信息")
                print("设备IP：",YuukaDeviceIp)
                print("API账户名：",YuukaDeviceApiAccount)
                print("API账户密码：",YuukaDeviceApiPassword)
                print("出接口名称列表：",YuukaDeviceWANPortList)
                print("优香酱休息时间：",HayaseYuukaSleepTime,"分")
                print("出接口：",YuukaDeviceWANPortList)

            DPTechFW = {
                "device_type": "cisco_ios",
                "host": YuukaDeviceIp,
                "username": YuukaDeviceApiAccount,
                "password": YuukaDeviceApiPassword,
            }

            # 获取接口信息
            # 执行 show brief 获取指定网卡 IP
            interfacesInfo = DPTechFWShell_withoutPaging(DPTechFW, 'show ip interf brief',"")
            if debugYuuka:
                print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()), "interfacesInfo - DPTech FW 返回接口信息：")
                # print(interfacesInfo)

            # 分析回显信息
            word = ""
            global printTag
            printTag = 0
            # 判断是否需要把数据加入列表的 Tag
            global joinTag
            joinTag = 0

            wanIntfInfoList={}
            YuukaWanIntfInfoListAll=[]

            for line in interfacesInfo:
                # 反转义，发现终端的输出存在大量的 \x00 和 \x08 ，影响正常搜索，下面目前已经处理
                # print(repr(line))
                if re.search(" ", line) or re.search(r"\r", line) or re.search(r"\n", line):
                    if re.search("[A-Z]|[a-z]|[0-9]",word):
                        if word=="null":
                            if debugYuuka:
                                print("ipAddr:",word)
                            printTag = printTag - 1

                        elif len(word) != 0:
                            # print(word,",",len(word))

                            if printTag == 4:
                                if joinTag == 1:
                                    wanIntfInfoList["phyStat"] = word
                                if debugYuuka:
                                    print("phyStat:",word)
                                printTag = printTag - 1
                            elif printTag == 3:
                                if joinTag == 1:
                                    wanIntfInfoList["protoStat"] = word
                                if debugYuuka:
                                    print("protoStat:",word)
                                printTag = printTag - 1
                            elif printTag == 2:
                                if joinTag == 1:
                                    wanIntfInfoList["ipAddr"] = word
                                if debugYuuka:
                                    print("ipAddr:",word)
                                printTag = printTag - 1
                            elif printTag == 1:
                                if joinTag == 1:
                                    wanIntfInfoList["descr"] = word
                                if debugYuuka:
                                    print("descr:",word)
                                printTag = printTag - 1
                            elif re.match("vlan|gige|ppp",word) and printTag == 0:
                                for intf in YuukaDeviceWANPortList:
                                    print("word:",word)
                                    print("intf:",intf)
                                    if word == intf:
                                        joinTag = 1
                                        wanIntfInfoList["intf"] = word
                                if debugYuuka:
                                    print("______")
                                    print("intf:",word)
                                printTag = 4

                    # 输出完成
                    # 用 if 可判断字典是否为空
                    if wanIntfInfoList and printTag == 0:
                        # 加入并清空
                        YuukaWanIntfInfoListAll.append(wanIntfInfoList)
                        wanIntfInfoList = {}

                    word = ""

                else:
                    word = word + line
                    word = word.replace("\x00", "")
                    word = word.replace("\x08", "")

                    if re.match("--", word):
                        word = "null"

            # 获取所要接口信息
            if debugYuuka:
                print("YuukaWanIntfInfoListAll:",YuukaWanIntfInfoListAll)
                # print("debugYuukaType:",type(YuukaWanIntfInfoListAll))

            # 获取目的 NAT 配置信息
            natSettingsInfo = DPTechFWShell_withoutPaging(DPTechFW, 'show run | inc destination-nat',"")
            # natSettingsInfo = DPTechFWShell_withoutPaging(DPTechFW, 'show run | inc destination-nat')
            if debugYuuka:
                print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()), "natSettingsInfo - DPTech FW 返回目的 NAT 信息：")
                # print(natSettingsInfo)

            # 解析目的 NAT
            printTag = 18
            natPolicyInfo={}
            YuukaNatPolicyListAll=[]
            for line in natSettingsInfo:
                # 反转义，发现终端的输出存在大量的 \x00 和 \x08
                # 此处的输出似乎不会存在 \x00 和 \x08 ，只保留部分预防措施
                # nat destination-nat test interface ppp2 global-address 1.1.1.1 service tcp 222 to 222 local-address 2.2.2.2 to 2.2.2.2 local-port 222
                # print(repr(line))
                # time.sleep(0.5)
                if re.search(" ", line) or re.search(r"\r", line) or re.search(r"\n", line):
                    if re.search("[A-Z]|[a-z]|[0-9]",word):
                        if len(word) != 0:
                            # print(word,",",len(word))
                            # Start - 开始读取策略
                            # 230223：策略量大时会导致原本当地排版混乱，前面会多几个空格影响判断，也会存在 \x00 和 \x08，通过 re 判断 nat 记录起始点
                            if printTag == 18 and re.search("nat", word):
                                natPolicyInfo={}
                                # nat - pass
                                printTag = printTag - 1
                                # print("[nat]:",word)
                            elif printTag == 17:
                                # destination-nat - pass
                                printTag = printTag - 1
                            elif printTag == 16:
                                # name - log
                                natPolicyInfo["natPolicyName"]=word
                                printTag = printTag - 1
                            elif printTag == 15:
                                # intf - pass
                                printTag = printTag - 1
                            elif printTag == 14:
                                # intfName - log
                                natPolicyInfo["outBoundIntf"]=word
                                printTag = printTag - 1
                            elif printTag == 13:
                                # global-address - pass
                                printTag = printTag - 1
                            elif printTag == 12:
                                # outBoundIPAddr - log
                                natPolicyInfo["outBoundIPAddr"]=word
                                printTag = printTag - 1
                            elif printTag == 11:
                                # Service - pass
                                printTag = printTag - 1    
                            elif printTag == 10:
                                # Protocol - log
                                natPolicyInfo["protocol"]=word
                                printTag = printTag - 1
                            elif printTag == 9:
                                # OutBoundPortStart - log
                                natPolicyInfo["outBoundPortStart"]=word
                                printTag = printTag - 1
                            elif printTag == 8:
                                # to - pass
                                printTag = printTag - 1
                            elif printTag == 7:
                                # OutBoundPortEnd - log
                                natPolicyInfo["outBoundPortEnd"]=word
                                printTag = printTag - 1
                            elif printTag == 6:
                                # local-address - pass
                                printTag = printTag - 1
                            elif printTag == 5:
                                # LocalIPAddrStart - pass
                                natPolicyInfo["localIPAddrStart"]=word
                                printTag = printTag - 1
                            elif printTag == 4:
                                # to - pass
                                printTag = printTag - 1
                            elif printTag == 3:
                                # LocalIPAddrEnd - pass
                                natPolicyInfo["localIPAddrEnd"]=word
                                printTag = printTag - 1
                            elif printTag == 2:
                                # local-port - pass
                                printTag = printTag - 1
                            elif printTag == 1:
                                # local-portNum - log
                                natPolicyInfo["localPort"]=word
                                # 结束 - 进行重置
                                # print("reset - DebugYuuka:",natPolicyInfo)
                                YuukaNatPolicyListAll.append(natPolicyInfo)
                                printTag = 18
                                

                    word = ""

                else:
                    word = word + line
                    word = word.replace("\x00", "")
                    word = word.replace("\x08", "")

            # 输出测试结果
            if debugYuuka:
                print("YuukaNatPolicyListAll:",YuukaNatPolicyListAll)

            # 获取用户设置
            # 获取基于接口 IP 的 NAT Server 端口映射表设置
            YuukaNatServersSettings=[]

            NATServerSheetTotalColCount=NATServerSheet.nrows-4

            for i in range(0,NATServerSheetTotalColCount):
                YuukaPolicyName=str(NATServerSheet.row(4+i)[1].value)
                YuukaServerIPv4=str(NATServerSheet.row_values(4+i)[3])
                YuukaServerProtocol=str(NATServerSheet.row_values(4+i)[4])
                YuukaServerOutBoundInterface=str(NATServerSheet.row_values(4+i)[5])
                YuukaWANPort=str(NATServerSheet.row_values(4+i)[6])
                YuukaServerPort=str(NATServerSheet.row_values(4+i)[8])

                YuukaNatServerSetting={}
                YuukaNatServerSetting["YuukaPolicyName"]=YuukaPolicyName
                YuukaNatServerSetting["YuukaServerIPv4"]=YuukaServerIPv4
                if YuukaServerProtocol == "6":
                    YuukaNatServerSetting["YuukaServerProtocol"]="tcp"
                elif YuukaServerProtocol == "17":
                    YuukaNatServerSetting["YuukaServerProtocol"]="udp"
                YuukaNatServerSetting["YuukaServerOutBoundInterface"]=YuukaServerOutBoundInterface
                YuukaNatServerSetting["YuukaWANPort"]=YuukaWANPort
                YuukaNatServerSetting["YuukaServerPort"]=YuukaServerPort
                YuukaNatServerSetting["needCreate"]=True
                # YuukaNatServerSetting["needModify"]=False
                YuukaNatServersSettings.append(YuukaNatServerSetting)

            if debugYuuka:
                print("YuukaNatServersSettings:",YuukaNatServersSettings)

            # 遍历比较用户提供的 NAT 策略及系统内的 NAT 策略（均为目的 NAT ）
            for policy in YuukaNatServersSettings:
                for policyFromYuukaDevice in YuukaNatPolicyListAll:
                    if policy["YuukaPolicyName"] == policyFromYuukaDevice["natPolicyName"]:
                        # 同名策略存在，不需要创建
                        policy["needCreate"]=False
                        # 比较同名策略的内容
                        if policy["YuukaServerIPv4"] == policyFromYuukaDevice["localIPAddrStart"] and \
                            policy["YuukaServerIPv4"] == policyFromYuukaDevice["localIPAddrEnd"] and \
                            policy["YuukaServerProtocol"] == policyFromYuukaDevice["protocol"] and \
                            policy["YuukaServerOutBoundInterface"] == policyFromYuukaDevice["outBoundIntf"] and \
                            policy["YuukaWANPort"] == policyFromYuukaDevice["outBoundPortStart"] and \
                            policy["YuukaWANPort"] == policyFromYuukaDevice["outBoundPortEnd"] and \
                            policy["YuukaServerPort"] == policyFromYuukaDevice["localPort"]:
                            # policy["needModify"] = False
                            for intf in YuukaWanIntfInfoListAll:
                                if intf["intf"] == policy["YuukaServerOutBoundInterface"]:
                                    if intf["ipAddr"][:-3] == policyFromYuukaDevice["outBoundIPAddr"]:
                                        policy["needModify"] = False
                                    # 同名策略公网 IP 不同，修改
                                    else:
                                        policy["needModify"] = True
                        # 同名策略内容不同，修改
                        else:
                            policy["needModify"] = True

            global dataChanged
            dataChanged = False
            for policy in YuukaNatServersSettings:
                if policy["needCreate"]:
                    if debugYuuka:
                        print("willCreate:",policy)
                    for intf in YuukaWanIntfInfoListAll:
                        if intf["intf"] == policy["YuukaServerOutBoundInterface"]:
                            policy["outBoundIPAddr"] = intf["ipAddr"][:-3]
                    createDesNatCMD = "nat destination-nat "+policy["YuukaPolicyName"]+" interface "+policy["YuukaServerOutBoundInterface"] \
                        +" global-address "+policy["outBoundIPAddr"]+" service "+policy["YuukaServerProtocol"]+" "+policy["YuukaWANPort"]+" to "+policy["YuukaWANPort"] \
                        +" local-address "+policy["YuukaServerIPv4"]+" to "+policy["YuukaServerIPv4"]+" local-port "+policy["YuukaServerPort"]
                    createDesNat = DPTechFWShell_withoutPaging(DPTechFW, createDesNatCMD,"enable")
            
                    dataChanged = True

                    if debugYuuka:
                        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()), "createDesNat - DPTech FW 返回新建目的 NAT 结果信息：",createDesNat)
                
                elif policy["needModify"]:
                    if debugYuuka:
                        print("willModify:",policy)
                    for intf in YuukaWanIntfInfoListAll:
                        if intf["intf"] == policy["YuukaServerOutBoundInterface"]:
                            policy["outBoundIPAddr"] = intf["ipAddr"][:-3]
                    undoDesNatCMD = "no nat des "+policy["YuukaPolicyName"]
                    delDesNat = DPTechFWShell_withoutPaging(DPTechFW, undoDesNatCMD,"enable")

                    if debugYuuka:
                        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()), "delDesNat - DPTech FW 返回删除目的 NAT 结果信息：",delDesNat)
                    
                    createDesNatCMD = "nat destination-nat "+policy["YuukaPolicyName"]+" interface "+policy["YuukaServerOutBoundInterface"] \
                        +" global-address "+policy["outBoundIPAddr"]+" service "+policy["YuukaServerProtocol"]+" "+policy["YuukaWANPort"]+" to "+policy["YuukaWANPort"] \
                        +" local-address "+policy["YuukaServerIPv4"]+" to "+policy["YuukaServerIPv4"]+" local-port "+policy["YuukaServerPort"]
                    createDesNat = DPTechFWShell_withoutPaging(DPTechFW, createDesNatCMD,"enable")
            
                    dataChanged = True
            
                    if debugYuuka:
                        print(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()), "createDesNat - DPTech FW 返回新建目的 NAT 结果信息：",createDesNat)
                    

            # 全部完成，保存数据
            if dataChanged:
                writeFile = DPTechFWShell_withoutPaging(DPTechFW, "wr f","enable")

                print("本阶段操作成功完成！ DPTech FW 返回的数据保存结果为：",writeFile)
            print ("当前时间 :", time.strftime("%Y-%m-%d %H:%M:%S",
                time.localtime()),"本周期任务运行顺利结束！")
            print ("————————————————————————————————————————")
            time.sleep(int(HayaseYuukaSleepTime)*60)

        except:
            print("如果需要退出程序，请再次按下 Ctrl+C ")
            print("程序出错，可能是 DPTech FW 连接失败，等待 60 秒后重试")
            time.sleep(60)
            print("开始重试")


# CLI
def cli():
    parser = argparse.ArgumentParser(description="YuukaChan@DPTech ——"+
            " 让可爱的优香酱使用 SSH 管理 DPTech FW 系列设备")
    subparsers = parser.add_subparsers(metavar='subCommand')

    # 启动服务（生产环境）
    runProd_parser = subparsers.add_parser('runProd', help='启动服务（生产环境）')
    runProd_parser.set_defaults(handle=handle_runProd)
    # 启动服务（调试环境）
    runDebug_parser = subparsers.add_parser('runDebug', help='启动服务（调试环境）')
    runDebug_parser.set_defaults(handle=handle_runDebug)
    # # 调试功能
    # debug_parser = subparsers.add_parser('info', help='编程中调试功能')
    # debug_parser.set_defaults(handle=handle_info)
    # 解析命令
    args = parser.parse_args()
    # 1.第一个命令会解析成handle，使用args.handle()就能够调用
    if hasattr(args, 'handle'):
        args.handle(args)
    # 2.如果没有handle属性，则表示未输入子命令，则打印帮助信息
    else:
        parser.print_help()

def handle_runProd(args):
    HayaseYuuka(False)

def handle_runDebug(args):
    HayaseYuuka(True)

# 设备基本信息，迪普 FW 可兼容 iOS
if __name__ == '__main__':
    print("欢迎使用优香酱 DPTech 系列设备管理小工具~")
    print("目前支持功能：【NAT Server 根据接口 IP 动态配置服务器映射列表设置】")
    print("Powered By Luckykeeper <luckykeeper@luckykeeper.site | https://luckykeeper.site>")
    print("YuukaChan@DPtech Ver1.0.0_20230223")
    print("HayaseYuuka：“如我所算，完美~♪”")
    print("————————————————————————————————————————")
    print("————————⚠警告信息⚠————————")
    print("注意调用本工具会对设备上的当前设定信息做保存(write file)操作！！！")
    print("如果你不希望保存当前设定信息，请立刻多次按下“Ctrl+C”取消运行！！！")
    print("小工具将在 5s 后开始运行！！！")
    print("————————⚠警告信息⚠————————")
    time.sleep(5)

    cli()
