# 这里是定时任务
# 1.更新access_token
# 2.定时备份数据库到cos 深夜3点备份数据库

# a60s 刷新一次 b600s一次

# 1.定时超过5分钟状态为10的订单（预支付成功）a
# 2.查找支付成功但是通知失败的订单a
# 3.查找商家已发货但是用户还没有收到通知的订单b
# 4.定时去更新订单的支付状态24小时未支付自动取消,已回源b
# 5.超过七天未确认收货则默认收货b
# 6.超过15天未评价默认好评b
# 7.超过72小时商家不发货，那么订单自动退款，优惠券要不要回退呢？b
# 8.查询退款申请订单b
# 9.拼团订单超过72小时未拼成将自动退款;b
# 10拼团成功订单超过72小时商家未发货，将自动退款b
# 11 查找通知支付成功但提示未支付的订单a
# 12. 查找30分钟还没有支付的拼团订单a


from main.config import *
import urllib.request
import json
import datetime
import os
import time
import pymysql
from main.wx_pay import WxPay
from decimal import Decimal


# from main.models import *

def get_token(app_id, secret):
    # 判断缓存
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + app_id + \
          '&secret=' + secret
    f = urllib.request.urlopen(url)
    s = f.read()
    # 读取json数据
    j = json.loads(s.decode('utf-8'))
    # j.keys()
    token = ''
    if j.get("access_token"):
        token = j.get("access_token")
    f.close()
    return token


def updata_access_token():
    access_token = get_token(c_app_id, c_secret)
    set_token(access_token)
    pass
    print('access_token' + access_token + datetime.datetime.now().strftime('%H:%M:%S'))


def test():
    print('test')


# 别备份数据库
def backupDataBase():
    key = "1106"  # 设置你的数据库密码
    fileName = datetime.datetime.now().strftime('%Y-%m-%d')
    path = "c:/backup/" + fileName + '.sql'
    s = "mysqldump -uroot -p%s native> %s" % (key, path)
    state = os.system('cd C:\Program Files\MySQL\MySQL Server 5.7\\bin&&' + s + '&&exit')
    if state == 0:  # 执行命令成功
        # 上传备份文件到cos
        # print('上传cos')
        bucket = cos.get_bucket("databasebackup")  # 你的腾讯云bucket
        data = bucket.upload_file(real_file_path=path, file_name=fileName)
        access_url = eval(data).get('access_url')
        if not access_url:
            print(fileName + '备份失败')
            data = bucket.upload_file(real_file_path=path, file_name=fileName)
            print('重新上传')
            access_url = eval(data).get('access_url')
            if access_url:
                print('备份成功')

            else:
                print('重新备份失败')
        else:
            print('备份成功')
    else:  # 执行命令失败
        print('执行命令失败，重新执行')
        state = os.system('cd C:\Program Files\MySQL\MySQL Server 5.7\\bin&&' + s + '&&exit')
        if state == 0:
            bucket = cos.get_bucket("databasebackup")
            data = bucket.upload_file(real_file_path=path, file_name=fileName)
            access_url = eval(data).get('access_url')
            if not access_url:
                print(fileName + '备份失败')
                data = bucket.upload_file(real_file_path=path, file_name=fileName)
                print('重新上传')
                access_url = eval(data).get('access_url')
                if access_url:
                    print('备份成功')
                else:
                    print('重新备份失败')
            else:
                print('备份成功')
        else:
            print('此次备份失败')
    try:
        os.remove(path)  # 移除备份
    except Exception as e:
        print(str(e))


# 1.定时超过5分钟状态为10的订单（预支付成功）
def check_prepay_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 300)
    # 1查找订单状态为10 ，且是5分钟前的支付订单，判断是否支付成功，进行回源（不使用悲观锁，使用乐观锁）
    cursor.execute(
        'select id, out_trade_no,order_code,user_id,realTotal,orderType,province,city,area,address,prepay_id,prePayTime,collagerId from main_order WHERE status=10 and prePayTime < %s',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        for o in orders:
            data = {'out_trade_no': o[1], }
            res = wx.order_query(data)
            try:

                if res.get("trade_state") == "SUCCESS":  # 如果交易成功 # 更新订单信息
                    now = datetime.datetime.now()
                    cursor.execute('update main_order set status=1,payTime=%s WHERE id=%s and status=10',
                                   [now, o[0]]
                                   )
                    # 发送模板消息？
                    cursor.execute(
                        'select id, skuName,skuNum,productName,sku_id from main_ordersku WHERE order_id=%s',
                        o[0])
                    orderSkus = cursor.fetchall()
                    cursor.execute(
                        'select openId,score,id from main_user WHERE id=%s FOR UPDATE ',
                        o[3])
                    user = cursor.fetchone()
                    orderType = ''
                    if o[5] == 0:  # 是单买
                        orderType = '单买'
                        temscore = user[1] + 20
                        # 下单获得20积分
                        cursor.execute('update main_user set score=%s WHERE id=%s', [temscore, o[3]])
                    elif o[5] == 1:  # 是团购
                        orderType = '团购'
                        # print('ok1')
                        cursor.execute(
                            'select id, status,collageSku_id,user_id from main_collageuser WHERE id=%s FOR UPDATE ',
                            o[12])
                        # print(o[12])4
                        collager = cursor.fetchone()
                        if collager[4] == o[3]:  # 是团长通知
                            cursor.execute('update main_collageuser set status=1 WHERE id=%s', collager[0])
                            cursor.execute('update main_order set status=1 WHERE id=%s', o[0])
                        else:  # 是团员的通知
                            cursor.execute(
                                'select id, collage_id,collagePrice from main_collagesku WHERE id=%s FOR UPDATE ',
                                collager[2])
                            collageSku = cursor.fetchone()
                            cursor.execute(
                                'select id, collagePeople from main_collage WHERE id=%s FOR UPDATE ',
                                collageSku[1])
                            collage = cursor.fetchone()
                            cursor.execute(
                                'select id from main_collageuser WHERE collagerId=%s and status=1 FOR UPDATE ',
                                o[12])
                            collageUsers = cursor.fetchall()  # 查找支付成功的订单
                            cursor.execute(
                                'select id from main_collageuser WHERE collagerId=%s and user_id=%s FOR UPDATE ',
                                [o[12], o[3]])
                            collageUser = cursor.fetchone()  # 查找本人团员
                            if collage[1] == len(collageUsers) + 1 + 1:  # 够数开团（本人+团长+支付成功的团员）
                                profit = collage[1] * collageSku[2]
                                cursor.execute('update main_collage set collageTotal=collageTotal+%s', profit)  # 活动营收
                                cursor.execute('update main_collageuser set status=2 WHERE id=%s', collager[0])
                                cursor.execute('update main_collageuser set status=2 WHERE id=%s', collageUser[0])
                                for cu in collageUsers:
                                    cursor.execute('update main_collageuser set status=2 WHERE id=%s', cu[0])
                                cursor.execute(
                                    'select id from main_order WHERE collagerId=%s FOR UPDATE ',
                                    o[12])
                                collageOrders = cursor.fetchall()
                                now = datetime.datetime.now()
                                for co in collageOrders:
                                    cursor.execute('update main_order set status=8,collageTime=%s WHERE id=%s',
                                                   [now, co[0]])
                                cursor.execute('update main_order set status=8,collageTime=%s WHERE id=%s', [now, o[0]])
                            else:
                                # print('ok5')
                                cursor.execute('update main_collageuser set status=1 WHERE id=%s', collageUser[0])

                    orderContent = ''
                    for oks in orderSkus:
                        orderContent += oks[3] + ' ' + str(oks[1]) + '×' + str(oks[2]) + '  '
                        # 3.商品的销量对应相加
                        cursor.execute(
                            'select id,saleNum from main_sku WHERE id=%s FOR UPDATE ',
                            oks[4])
                        sku = cursor.fetchone()
                        saleNum = sku[1] + oks[2]
                        cursor.execute('update main_sku set saleNum=%s WHERE id=%s', [saleNum, o[3]])
                    # 商家总销售额和订单数量+1
                    cursor.execute('select id from main_count')
                    count = cursor.fetchall()
                    if count:
                        count = count[0]
                        cursor.execute(
                            'update main_count set allSale=allSale+%s,allOrderNum=allOrderNum+%s WHERE id=%s',
                            [o[4], 1, count[0]])
                    else:
                        cursor.execute('INSERT INTO main_coun (allSale,allOrderNum) VALUES (%s,%s)', [o[4], 1])
                    cursor.execute('select id from main_countday WHERE day=%s', datetime.datetime.now().date())
                    # 商家日销售额和订单数量+1
                    countDay = cursor.fetchall()
                    if countDay:
                        countDay = countDay[0]
                        cursor.execute('update main_countday set orderNum=orderNum+%s,sale=sale+%s WHERE id=%',
                                       [1, o[4], countDay[0]])
                    else:
                        cursor.execute('INSERT INTO main_countday (orderNum,sale)VALUES (%s,%s)',
                                       [1, o[4]])
                    # 开始写消息模板
                    data = {  # "first": {"value": "同渡旅行告诉你有新的通知", "color": "#173177"},
                        "keyword1": {"value": o[2], "color": "#173177"},
                        "keyword2": {"value": o[4], "color": "#173177"},
                        "keyword3": {"value": orderType, "color": "#173177"},
                        "keyword4": {"value": orderContent, "color": "#173177"},
                        "keyword5": {"value": o[6] + o[7] + o[8] + o[9],
                                     "color": "#173177"},
                        "keyword6": {"value": o[11], "color": "#173177"},
                    }
                    wechat_push = WxPay()
                    res = wechat_push.do_push(user[0],
                                              c_templateID_order_success,
                                              c_page,
                                              data,
                                              o[10], )
                    if res.get('errcode') == 0 and res.get('errmsg') == 'ok':  # 成功
                        # 把通知状态改为1，表示订单已经发送了通知支付成功消息
                        cursor.execute('update main_order set notifyStatus=1 WHERE id=%s and notifyStatus=0', o[0])
                        pass
                    else:
                        print('orderId' + str(o[0]) + 'prepayId' + str(o[10]))
                        print(res)
                else:  # #交易已经过期(更改订单为未付款)
                    cursor.execute('update main_order set status=0 WHERE id=%s and status=10', o[0])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('1return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 2.查找支付成功但是通知失败的订单
def check_no_notify_pay_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    # t = datetime.datetime.fromtimestamp(time.time() - 300)
    # 1查找订单状态为1 ，且通知状态为0的订单
    cursor.execute(
        'select id, out_trade_no,order_code,user_id,realTotal,orderType,province,city,area,address,prepay_id,prePayTime '
        'from main_order WHERE status=1 and notifyStatus=0')
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        for o in orders:
            try:
                # 发送模板消息？
                cursor.execute(
                    'select id, skuName,skuNum,productName from main_ordersku WHERE order_id=%s',
                    o[0])
                orderSkus = cursor.fetchall()
                cursor.execute(
                    'select openId,score,id from main_user WHERE id=%s FOR UPDATE ',
                    o[3])
                user = cursor.fetchone()
                orderContent = ''
                for oks in orderSkus:
                    orderContent += oks[3] + ' ' + str(oks[1]) + '×' + str(oks[2]) + '  '
                orderType = ''
                if o[5] == 0:
                    orderType = '单买'
                elif o[5] == 1:
                    orderType = '团购'
                # 开始写消息模板
                data = {  # "first": {"value": "同渡旅行告诉你有新的通知", "color": "#173177"},
                    "keyword1": {"value": o[2], "color": "#173177"},
                    "keyword2": {"value": o[4], "color": "#173177"},
                    "keyword3": {"value": orderType, "color": "#173177"},
                    "keyword4": {"value": orderContent, "color": "#173177"},
                    "keyword5": {"value": o[6] + o[7] + o[8] + o[9],
                                 "color": "#173177"},
                    "keyword6": {"value": o[11], "color": "#173177"},
                }
                wechat_push = WxPay()
                res = wechat_push.do_push(user[0],
                                          c_templateID_order_success,
                                          c_page,
                                          data,
                                          o[10], )
                if res.get('errcode') == 0 and res.get('errmsg') == 'ok':  # 成功
                    # 把通知状态改为1，表示订单已经发送了通知支付成功消息
                    cursor.execute('update main_order set notifyStatus=1 WHERE id=%s and notifyStatus=0', o[0])
                    pass
                else:
                    print('orderId' + str(o[0]) + 'prepayId' + str(o[10]))
                    print(res)
                connection.commit()
            except Exception as e:
                print('2return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 3.查找商家已发货但是用户还没有收到通知的订单
def check_no_notify_express_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    # t = datetime.datetime.fromtimestamp(time.time() - 300)
    # 1查找订单状态为1 ，且通知状态为0的订单
    cursor.execute(
        'select id, phoneNum,order_code,user_id,realTotal,orderType,province,city,area,address,prepay_id,express,expressNo '
        'from main_order WHERE status=2 and notifyStatus!=2')
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        for o in orders:
            try:
                # 发送模板消息？
                cursor.execute(
                    'select id, skuName,skuNum,productName from main_ordersku WHERE order_id=%s',
                    o[0])
                orderSkus = cursor.fetchall()
                cursor.execute(
                    'select openId,score,id from main_user WHERE id=%s FOR UPDATE ',
                    o[3])
                user = cursor.fetchone()
                orderContent = ''
                for oks in orderSkus:
                    orderContent += oks[3] + ' ' + str(oks[1]) + '×' + str(oks[2]) + '  '
                # 发送发货通知
                data = {  # "first": {"value": "同渡旅行告诉你有新的通知", "color": "#173177"},
                    "keyword1": {"value": o[2], "color": "#173177"},
                    "keyword2": {"value": o[4], "color": "#173177"},
                    "keyword3": {"value": orderContent, "color": "#173177"},
                    "keyword4": {"value": o[11], "color": "#173177"},
                    "keyword5": {"value": o[12], "color": "#173177"},
                    "keyword6": {"value": o[6] + o[7] + o[8] + o[9],
                                 "color": "#173177"},
                    "keyword7": {"value": o[1], "color": "#173177"},
                }
                wechat_push = WxPay()
                res = wechat_push.do_push(user[0],
                                          c_templateID_order_send,
                                          c_page,
                                          data,
                                          o[10], )
                if res.get('errcode') == 0 and res.get('errmsg') == 'ok':  # 成功
                    # 把通知状态改为2，表示订单已经发送了发货通知
                    cursor.execute('update main_order set notifyStatus=2 WHERE id=%s', o[0])
                    pass
                else:
                    print('orderId' + str(o[0]))
                    print(res)
                connection.commit()
            except Exception as e:
                print('3return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 4.定时去更新订单的支付状态24小时未支付自动取消,已回源
def check_no_pay_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 86400)  # 查找24小时之前的未付款订单
    # 1查找订单状态为10 ，且是5分钟前俞支付订单，判断是否支付成功，进行回源（不使用悲观锁，使用乐观锁）
    cursor.execute('select id, out_trade_no from main_order WHERE status=0 and prePayTime < %s FOR UPDATE', t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        for o in orders:
            try:
                cursor.execute('update main_order set status=5 WHERE id=%s and status=0', o[0])
                # 同时回源 查找订单sku
                cursor.execute('select id, skuNum,sku_id from main_ordersku WHERE order_id=%s', o[0])
                orderSkus = cursor.fetchall()  # 得到元组数据
                for oks in orderSkus:
                    cursor.execute('select id, residualNum from main_sku WHERE id=%s FOR UPDATE ', oks[0])
                    sku = cursor.fetchone()  # 得到元组数据
                    tempresidualNum = sku[1] + oks[1]
                    cursor.execute('update main_sku set residualNum=%s WHERE id=%s', [tempresidualNum, sku[0]])
                connection.commit()
            except Exception as e:
                print('4return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 5.超过七天未确认收货则默认收货
def check_no_receive_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 604800)  # 查找发货超过7天但未收货的订单
    # 查找订单状态为2 ，且是7天前的发货订单，判断是否收货成功
    cursor.execute(
        'select id, out_trade_no, user_id,realTotal,prepay_id,orderType from main_order WHERE status=2 and expressTime < %s FOR UPDATE ',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    # wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        # 查找分销设置
        cursor.execute('select firstProfit,firstLimit,secondProfit,secondLimit from main_distribution WHERE id=1')
        distribution = cursor.fetchall()  # 得到元组数据, 选择用户的代理人以及用户的等级
        if distribution:
            firstProfit = distribution[0]
            firstLimit = distribution[1]
            secondProfit = distribution[2]
            secondLimit = distribution[3]
        else:
            firstProfit = 100
            firstLimit = 0
            secondProfit = 100
            secondLimit = 0
        for o in orders:
            try:
                if o[5] == 0:  # 普通订单才会有分销
                    # 用户确认收获了代理人才有提成，这是更新代理人信息
                    cursor.execute('select id,agentId,fansLevel from main_user WHERE id=%s', o[2])
                    user = cursor.fetchone()  # 得到元组数据, 选择用户的代理人以及用户的等级
                    if user[1] != 0:  # 如果该用户是某代理人的粉丝
                        # 选择该代理人
                        cursor.execute('select id,status,total,residue from main_agent WHERE id=%s FOR UPDATE ',
                                       user[1])
                        agent = cursor.fetchone()  # 得到元组数据, 选择用户的代理人以及用户的等级
                        if agent[1] == 1:  # 正在代理
                            if user[2] == 1:  # 一级粉丝
                                addtotal = Decimal("%.2f" % (float(o[3]) * (firstProfit / 100)))
                                if addtotal > firstLimit:
                                    addtotal = firstLimit
                                even = '一级粉丝购买商品'
                            else:
                                addtotal = Decimal("%.2f" % (float(o[3]) * (secondProfit / 100)))
                                if addtotal > secondLimit:
                                    addtotal = secondLimit
                                even = '二级粉丝购买商品'
                            # 加上代理费
                            cursor.execute('update main_agent set total=total+%s,residue=residue+%s WHERE id=%s',
                                           [addtotal, addtotal, agent[0]])
                            # 增加一条收益记录
                            cursor.execute('INSERT INTO main_agentprofitrecord (agent_id,even,value) VALUES (%s,%s,%s)',
                                           [agent[0], even, addtotal])
                            # 更新日数据
                            # 更新当日的代理收益数据
                            cursor.execute(
                                'select id,total from main_agentcountday WHERE agent_id=%s and day=%s FOR UPDATE',
                                [agent[0], datetime.datetime.now().date()])
                            agentCountDay = cursor.fetchall()
                            if agentCountDay:
                                agentCountDay = agentCountDay[0]
                                cursor.execute('update main_agentcountday set total=total+%s WHERE id=%s',
                                               [addtotal, agentCountDay[0]])
                            else:
                                cursor.execute('INSERT INTO main_agentcountday (agent_id,day,total) VALUES (%s,%s,%s)',
                                               [agent[0], datetime.datetime.now(), addtotal])
                    cursor.execute('update main_order set status=3,receiveTime=%s WHERE id=%s',
                                   [datetime.datetime.now(), o[0]])
                connection.commit()
            except Exception as e:
                print('5return_msg:' + str(e))
    cursor.close()
    connection.close()  # 最后关闭数据库


# 6.超过15天未评价默认好评(普通订单)
def check_no_comment_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 604800)  # 查找收货超过15天但未评价的订单
    # 查找订单状态为3 ，且是15天前的发货订单，判断是否评价
    cursor.execute(
        'select id, user_id from main_order WHERE status=3 and orderType=0 and receiveTime < %s FOR UPDATE ', t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    if orders:
        for o in orders:
            try:
                cursor.execute('update main_order set status=4 WHERE id=%s', o[0])
                # 创建一条默认好评
                cursor.execute('select * from main_comment WHERE order_id=%s and user_id=%s', [o[0], o[1]])
                comment = cursor.fetchall()
                if not comment:
                    cursor.execute('insert into main_comment (order_id,user_id) VALUES (%s,%s)', [o[0], o[1]])
                connection.commit()
            except Exception as e:
                print('6return_msg:' + str(e))


# 7.普通订单超过72小时商家未发货，将自动退款，未回源，优惠券不回退；
def check_no_send_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 259200)  # 查找收货超过3天未发货的订单
    # 查找订单状态为3 ，且是15天前的发货订单，判断是否评价
    cursor.execute(
        'select id, user_id,orderType,out_trade_no,realTotal from main_order WHERE status=1 and orderType=0 and payTime < %s FOR UPDATE ',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    if orders:
        for o in orders:
            try:
                # 退款
                data = {
                    'out_trade_no': o[3],
                    'total_fee': int(float(o[4]) * 100),
                    'refund_fee': int(float(o[4]) * 100), }
                raw = WxPay().refund(c_api_cert_path, c_api_key_path, data)
                if raw.get("return_code") == 'SUCCESS' and raw.get('result_code') == 'SUCCESS':
                    cursor.execute('update main_order set status=6 WHERE status=1 and id=%s', o[0])
                    # 回源
                    cursor.execute('select id,skuNum,sku_id from main_ordersku WHERE order_id=%s', o[0])
                    orderSkus = cursor.fetchall()
                    for osk in orderSkus:
                        cursor.execute('select id,residualNum from main_sku WHERE id=%s FOR UPDATE ', osk[2])
                        sku = cursor.fetchone()
                        cursor.execute('update main_sku set residualNum=%s WHERE id=%s', [sku[1] + osk[1], sku[0]])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('7return_msg:' + str(e))


# 8.查询退款申请订单
def check_refund_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    # 查找订单状态为3 ，且是15天前的发货订单，判断是否评价
    cursor.execute(
        'select id, user_id,orderType,out_trade_no,realTotal from main_order WHERE status=6 FOR UPDATE ')
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    if orders:
        for o in orders:
            try:
                # 退款
                # data = {
                #     'out_trade_no': o[3]}
                raw = WxPay().refund_query(out_trade_no=o[3])
                if raw.get("return_code") == 'SUCCESS' and raw.get('result_code') == 'SUCCESS':
                    cursor.execute('update main_order set status=7 WHERE status=1 and id=%s', o[0])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('8return_msg:' + str(e))


# 9.拼团订单超过72小时未拼成将自动退款;
def check_no_collage_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 259200)  # 查找3天后仍然未拼成团的订单
    # 查找3天后仍然未拼成团的订单，
    cursor.execute(
        'select id, user_id,orderType,out_trade_no,realTotal,collagerId from main_order WHERE status=1 and orderType=1 and payTime < %s FOR UPDATE ',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    if orders:
        for o in orders:
            try:
                # 退款
                data = {
                    'out_trade_no': o[3],
                    'total_fee': int(float(o[4]) * 100),
                    'refund_fee': int(float(o[4]) * 100), }
                raw = WxPay().refund(c_api_cert_path, c_api_key_path, data)
                if raw.get("return_code") == 'SUCCESS' and raw.get('result_code') == 'SUCCESS':
                    cursor.execute('update main_order set status=6 WHERE status=1 and id=%s', o[0])
                    # 回源
                    cursor.execute('select id,user_id,collageSku_id from main_collageuser WHERE id=%s', o[5])
                    collager = cursor.fetchone()  # 团长
                    if collager[1] == o[1]:  # # 是团长回源
                        cursor.execute('select id,residualNum,sku_id from main_collagesku WHERE id=%s FOR UPDATE ',
                                       collager[2])
                        collageSku = cursor.fetchone()
                        cursor.execute('update main_collagesku set residualNum=%s WHERE id=%s',
                                       [collageSku[1] + 1, collageSku[0]])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('9return_msg:' + str(e))


# 10拼团成功订单超过72小时商家未发货，将自动退款
def check_no_send_collage_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 259200)  # 查找3天后仍然未拼成团的订单
    # 查找3天后仍然未拼成团的订单，
    cursor.execute(
        'select id, user_id,orderType,out_trade_no,realTotal,collagerId from main_order WHERE status=8 and orderType=1 and collageTime < %s FOR UPDATE ',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    if orders:
        for o in orders:
            try:
                # 退款
                data = {
                    'out_trade_no': o[3],
                    'total_fee': int(float(o[4]) * 100),
                    'refund_fee': int(float(o[4]) * 100), }
                raw = WxPay().refund(c_api_cert_path, c_api_key_path, data)
                if raw.get("return_code") == 'SUCCESS' and raw.get('result_code') == 'SUCCESS':
                    cursor.execute('update main_order set status=6 WHERE status=1 and id=%s', o[0])
                    # 回源
                    cursor.execute('select id,user_id,collageSku_id from main_collageuser WHERE id=%s', o[5])
                    collager = cursor.fetchone()  # 团长
                    if collager[1] == o[1]:  # # 是团长回源
                        cursor.execute('select id,residualNum,sku_id from main_collagesku WHERE id=%s FOR UPDATE ',
                                       collager[2])
                        collageSku = cursor.fetchone()
                        cursor.execute('update main_collagesku set residualNum=%s WHERE id=%s',
                                       [collageSku[1] + 1, collageSku[0]])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('10return_msg:' + str(e))


# 11 查找通知支付成功但提示未支付的订单
def check_no_pay_notify():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    # t = datetime.datetime.fromtimestamp(time.time() - 300)
    # 查找通知过了但是支付失败的订单
    cursor.execute(
        'select id,out_trade_no from main_order WHERE status=0 and notifyStatus = 1')
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例ret
    if orders:  # 如果存在未处理订单
        for o in orders:
            data = {'out_trade_no': o[1], }
            res = wx.order_query(data)
            try:

                if res.get("trade_state") == "SUCCESS":  # 如果交易成功 # 更新订单信息
                    now = datetime.datetime.now()
                    cursor.execute('update main_order set status=1 WHERE id=%s and notifyStatus=1',
                                   o[0]
                                   )
                else:  # 交易已经过期(更改订单为未付款)
                    cursor.execute('update main_order set notifyStatus=0 WHERE id=%s and status=0', o[0])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('11return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 12. 查找30分钟还没有支付的拼团订单
def check_no_pay_collage_order():
    connection = pymysql.connect(host='localhost',
                                 port=3306,
                                 user='root',
                                 password='1106',
                                 db='native',
                                 charset='utf8', )
    cursor = connection.cursor()  # 定义一个数据库游标
    t = datetime.datetime.fromtimestamp(time.time() - 1800)
    # 查找30分钟还没有支付的拼团订单
    cursor.execute(
        'select id,out_trade_no,collagerId,user_id '
        'from main_order WHERE '
        'status=0 and createTime < %s and orderType=1 FOR UPDATE ',
        t)
    orders = cursor.fetchall()  # 得到元组数据, 选择订单id 和 订单的交易号
    wx = WxPay()  # 生成工具类实例
    if orders:  # 如果存在未处理订单
        for o in orders:
            try:
                cursor.execute('update main_order set status=5 WHERE id=%s and status=0',
                               o[0]
                               )
                cursor.execute('delete from main_collageuser WHERE user_id=%s and collagerId=%s', [o[3], o[2]])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('12return_msg:' + str(e))
                # print(e)
    cursor.close()
    connection.close()  # 最后关闭数据库


# 每分钟执行一次
def update_order_a():
    try:
        print('start-update_order_a')
        check_prepay_order()  # 1
        check_no_notify_pay_order()  # 2
        check_no_pay_notify()  # 11
        check_no_pay_collage_order()  # 12
        print('end-update_order_a')
    except Exception as e:
        print(e)


# 每10分钟一次
def update_order_b():
    try:
        print("update_order_b_start")
        check_no_notify_express_order()  # 3
        check_no_pay_order()  # 4
        check_no_receive_order()  # 5
        check_no_comment_order()  # 6
        check_no_send_order()  # 7
        check_refund_order()  # 8
        check_no_collage_order()  # 9
        check_no_send_collage_order()  # 10
        print('update_order_b_end')
    except Exception as e:
        print(str(e))
