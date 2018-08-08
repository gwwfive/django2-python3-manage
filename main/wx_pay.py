# -*- coding: utf-8 -*-
import hashlib
import random
import string
import time
import urllib.request
import urllib.error
import requests
import datetime
import decimal
import json
import re
from main import config
from django.conf import settings
from django import forms

try:
    from flask import request
except ImportError:
    request = None

try:
    from xml.etree import cElementTree as ETree
except ImportError:
    from xml.etree import ElementTree as ETree


class WxPayError(Exception):
    def __init__(self, msg):
        super(WxPayError, self).__init__(msg)


class PicForm(forms.Form):
    value = forms.CharField(max_length=100)
    image = forms.FileField()


class WxPay(object):
    def __init__(self, wx_notify_url=''):
        self.opener = urllib.request.build_opener(urllib.request.HTTPSHandler())
        self.WX_APP_ID = config.c_app_id
        self.WX_MCH_ID = config.c_mch_id
        self.WX_MCH_KEY = config.c_merchant_key
        self.WX_NOTIFY_URL = wx_notify_url

    @staticmethod
    def user_ip_address():
        return request.remote_addr if request else None

    @staticmethod
    def nonce_str(length=32):
        char = string.ascii_letters + string.digits
        return "".join(random.choice(char) for _ in range(length))

    @staticmethod
    def to_utf8(raw):
        return raw.encode("utf-8") if isinstance(raw, str) else raw  # 再python3总str包含了 unicode

    @staticmethod
    def to_dict(content):
        # content=re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", content)
        raw = {}
        root = ETree.fromstring(content)
        for child in root:
            raw[child.tag] = child.text
        return raw

    @staticmethod
    def to_dict_refund(content):
        content = re.sub(u"[\x00-\x08\x0b-\x0c\x0e-\x1f]+", u"", content)
        raw = {}
        root = ETree.fromstring(content)
        for child in root:
            raw[child.tag] = child.text
        return raw

    @staticmethod
    def random_num(length):
        digit_list = list(string.digits)
        random.shuffle(digit_list)
        return ''.join(digit_list[:length])

    def sign(self, raw):
        """
        生成签名
        参考微信签名生成算法
        https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=4_3
        """
        raw = [(k, str(raw[k]) if isinstance(raw[k], (int, float)) else raw[k]) for k in sorted(raw.keys())]
        s = "&".join("=".join(kv) for kv in raw if kv[1])
        s += "&key={0}".format(self.WX_MCH_KEY)
        # return s
        return hashlib.md5(self.to_utf8(s)).hexdigest().upper()
        # return hashlib.md5(s).hexdigest().upper()

    def check(self, raw):
        """
        验证签名是否正确
        """
        sign = raw.pop("sign")
        return sign == self.sign(raw)

    def to_xml(self, raw):
        s = ""
        for k, v in raw.items():
            # s += "<{0}>![CDATA[{1}]]</{0}>".format(k, self.to_utf8(v), k)
            s += "<{0}>{1}</{0}>".format(k, v, k)
        return WxPay.to_utf8("<xml>{0}</xml>".format(s))
        # return "<xml>{0}</xml>".format(s)

    def fetch(self, url, data):
        # req = urllib.request(url, data=self.to_xml(data))  python3 中不能这样用了
        # return self.to_xml(data)
        try:
            resp = self.opener.open(url, self.to_xml(data), timeout=20)
            # resp = self.opener.open(url, self.to_utf8(s), timeout=20)
        except urllib.error.HTTPError as e:
            resp = e
        re_info = resp.read()
        try:
            return self.to_dict(re_info)
        except ETree.ParseError:
            return re_info

    def fetch_with_ssl(self, url, data, api_client_cert_path, api_client_key_path):
        req = requests.post(url, data=self.to_xml(data),
                            cert=(api_client_cert_path, api_client_key_path))
        return self.to_dict(req.content)

    def reply(self, msg, ok=True):
        code = "SUCCESS" if ok else "FAIL"
        data = dict(return_code=code, return_msg=msg)
        return self.to_xml(data)

    @staticmethod
    def get_token(app_id, secret):
        # 判断缓存
        url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + app_id + \
              "&secret=" + secret
        f = urllib.request.urlopen(url)
        s = f.read()
        # 读取json数据
        j = json.loads(s.decode('utf-8'))
        # j.keys()
        token = j['access_token']
        f.close()
        return token

    # 模拟post请求
    # @staticmethod
    def post_data(self, url, para_dct):
        para_data = para_dct
        req = urllib.request.Request(url, headers=para_data)
        f = urllib.request.urlopen(req).encode(encoding='UTF8')
        # f = urllib.request.urlopen(url, self.to_utf8(para_data))
        content = f.read()
        f.close()

        return content

    def do_push(self, touser, template_id, url, data, prepay_id):
        dict_arr = {'touser': touser, 'template_id': template_id, 'page': url, "form_id": prepay_id, 'data': data}
        json_template = json.dumps(dict_arr, cls=CJsonEncoder)
        # return json_template
        # return dict_arr
        if config.c_access_token is None:
            access_token = WxPay.get_token(config.c_app_id, config.c_secret)
            config.set_token(access_token)
        else:
            access_token = config.c_access_token
        # return {"access_token":config.c_access_token}	https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token=ACCESS_TOKEN
        access_url = "https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token=" + access_token
        # content = self.post_data(access_url, dict_arr)
        res = requests.post(access_url, data=json_template)
        # 读取json数据
        j = json.loads((res.content).decode('utf-8'))
        # j.keys()
        # errcode = j['errcode']
        # errmsg = j['errmsg']
        return j

    def unified_order(self, data):
        """
        统一下单
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_1

        :param data: out_trade_no, body, total_fee, trade_type
            out_trade_no: 商户订单号
            body: 商品描述
            total_fee: 标价金额, 整数, 单位 分
            trade_type: 交易类型
            user_ip 在flask框架下可以自动填写, 非flask框架需传入spbill_create_ip
        :return: 统一下单生成结果
        """
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"

        # 必填参数
        if "out_trade_no" not in data:
            raise WxPayError(u"缺少统一支付接口必填参数out_trade_no")
        if "body" not in data:
            raise WxPayError(u"缺少统一支付接口必填参数body")
        if "total_fee" not in data:
            raise WxPayError(u"缺少统一支付接口必填参数total_fee")
        if "trade_type" not in data:
            raise WxPayError(u"缺少统一支付接口必填参数trade_type")

        # 关联参数
        if data["trade_type"] == "JSAPI" and "openid" not in data:
            raise WxPayError(u"trade_type为JSAPI时，openid为必填参数")
        if data["trade_type"] == "NATIVE" and "product_id" not in data:
            raise WxPayError(u"trade_type为NATIVE时，product_id为必填参数")
        user_ip = self.user_ip_address()
        if not user_ip and "spbill_create_ip" not in data:
            raise WxPayError(u"当前未使用flask框架，缺少统一支付接口必填参数spbill_create_ip")

        data.setdefault("appid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        # data.setdefault("mch_id", '10727209')
        data.setdefault("notify_url", self.WX_NOTIFY_URL)
        # data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("nonce_str", 'bXUYIESvPnJ0yVOZQYt10bkRZlL7bxVJ')
        data.setdefault("spbill_create_ip", "119.29.134.149")
        # return self.sign(data)
        data.setdefault("sign", self.sign(data))
        # return data
        # return self.to_xml(data)
        out_trade_no = data["out_trade_no"]
        raw = self.fetch(url, data)
        if raw["return_code"] == "SUCCESS" and raw["result_code"] == "SUCCESS":  # 如果成功
            # 校验签名
            if self.check(raw):  # 如果签名校验成功
                # 对数据进行处理然后返回
                package = 'prepay_id=' + raw["prepay_id"]
                res = {'appId': self.WX_APP_ID, 'timeStamp': str(int(time.time())), 'nonceStr': self.nonce_str(),
                       'package': package, 'signType': 'MD5'}
                res.setdefault("paySign", self.sign(res))
                res.setdefault("out_trade_no", out_trade_no)
                res.setdefault("prepay_id", raw["prepay_id"])
                res.setdefault("return_code", "SUCCESS")
                return res
            else:
                return raw.setdefault("msg", '签名校验错误')
        else:
            return raw
        # if raw["return_code"] == "FAIL":
        #     raise WxPayError(raw["return_msg"])
        # err_msg = raw.get("err_code_des")
        # if err_msg:
        #     raise WxPayError(err_msg)

    def js_pay_api(self, **kwargs):
        """
        生成给JavaScript调用的数据
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=7_7&index=6

        :param kwargs: openid, body, total_fee
            openid: 用户openid
            body: 商品名称
            total_fee: 标价金额, 整数, 单位 分
            out_trade_no: 商户订单号, 若未传入则自动生成
        :return: 生成微信JS接口支付所需的信息
        """
        kwargs.setdefault("trade_type", "JSAPI")
        if "out_trade_no" not in kwargs:
            kwargs.setdefault("out_trade_no", self.nonce_str())
        raw = self.unified_order(**kwargs)
        package = "prepay_id={0}".format(raw["prepay_id"])
        timestamp = int(time.time())
        nonce_str = self.nonce_str()
        raw = dict(appId=self.WX_APP_ID, timeStamp=timestamp,
                   nonceStr=nonce_str, package=package, signType="MD5")
        sign = self.sign(raw)
        return dict(package=package, appId=self.WX_APP_ID,
                    timeStamp=timestamp, nonceStr=nonce_str, sign=sign)

    def order_query(self, data):
        """
        订单查询
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_2

        :rtype:
        :param data: out_trade_no, transaction_id至少填一个
            out_trade_no: 商户订单号
            transaction_id: 微信订单号
        :return: 订单查询结果
        """
        url = "https://api.mch.weixin.qq.com/pay/orderquery"

        if "out_trade_no" not in data and "transaction_id" not in data:
            raise WxPayError(u"订单查询接口中，out_trade_no、transaction_id至少填一个")
        data.setdefault("appid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("sign", self.sign(data))

        raw = self.fetch(url, data)
        if raw["return_code"] == "FAIL":
            raise WxPayError(raw["return_msg"])
        elif raw["return_code"] == "SUCCESS" and raw["result_code"] == "SUCCESS":
            return raw
        else:
            raise WxPayError(raw["err_code"])
        return raw

    def close_order(self, out_trade_no):
        """
        关闭订单
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_3

        :param out_trade_no: 商户订单号
        :return: 申请关闭订单结果
        """
        url = "https://api.mch.weixin.qq.com/pay/closeorder"
        data = {
            'out_trade_no': out_trade_no,
            'appid': self.WX_APP_ID,
            'mch_id': self.WX_MCH_ID,
            'nonce_str': self.nonce_str(),
        }
        data["sign"] = self.sign(data)
        raw = self.fetch(url, data)
        if raw["return_code"] == "FAIL":
            raise WxPayError(raw["return_msg"])
        return raw

    def refund(self, api_cert_path, api_key_path, data):
        """
        申请退款
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_4

        :param api_cert_path: 微信支付商户证书路径，此证书(apiclient_cert.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        :param api_key_path: 微信支付商户证书路径，此证书(apiclient_key.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        :param data: out_trade_no、transaction_id至少填一个, out_refund_no, total_fee, refund_fee
            out_trade_no: 商户订单号
            transaction_id: 微信订单号
            out_refund_no: 商户退款单号（若未传入则自动生成）
            total_fee: 订单金额
            refund_fee: 退款金额
        :return: 退款申请返回结果
        """
        url = "https://api.mch.weixin.qq.com/secapi/pay/refund"
        if "out_trade_no" not in data and "transaction_id" not in data:
            raise WxPayError(u"订单查询接口中，out_trade_no、transaction_id至少填一个")
        if "total_fee" not in data:
            raise WxPayError(u"退款申请接口中，缺少必填参数total_fee")
        if "refund_fee" not in data:
            raise WxPayError(u"退款申请接口中，缺少必填参数refund_fee")
        if "out_refund_no" not in data:
            data.setdefault("out_refund_no", self.nonce_str())

        data.setdefault("appid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        data.setdefault("op_user_id", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("sign", self.sign(data))
        # data.setdefault("sign", '0CB01533B8C1EF103065174F50BCA001')
        raw = self.fetch_with_ssl(url, data, api_cert_path, api_key_path)
        if raw["result_code"] == "FAIL" and raw.get("err_code") == 'SYSTEMERROR':  # 如果提交业务失败，且原因是系统繁忙，重试
            raw = self.fetch_with_ssl(url, data, api_cert_path, api_key_path)
            # raise WxPayError(raw["return_msg"])
        return raw

    def refund_query(self, **data):
        """
        查询退款
        提交退款申请后，通过调用该接口查询退款状态。退款有一定延时，
        用零钱支付的退款20分钟内到账，银行卡支付的退款3个工作日后重新查询退款状态。
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_5

        :param data: out_refund_no、out_trade_no、transaction_id、refund_id四个参数必填一个
            out_refund_no: 商户退款单号
            out_trade_no: 商户订单号
            transaction_id: 微信订单号
            refund_id: 微信退款单号

        :return: 退款查询结果
        """
        url = "https://api.mch.weixin.qq.com/pay/refundquery"
        if "out_refund_no" not in data and "out_trade_no" not in data \
                and "transaction_id" not in data and "refund_id" not in data:
            raise WxPayError(u"退款查询接口中，out_refund_no、out_trade_no、transaction_id、refund_id四个参数必填一个")

        data.setdefault("appid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("sign", self.sign(data))

        raw = self.fetch(url, data)
        if raw["return_code"] == "FAIL":
            raise WxPayError(raw["return_msg"])
        return raw

    def download_bill(self, bill_date, bill_type=None):
        """
        下载对账单
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_6

        :param bill_date: 对账单日期
        :param bill_type: 账单类型(ALL-当日所有订单信息，[默认]SUCCESS-当日成功支付的订单, REFUND-当日退款订单)

        :return: 数据流形式账单
        """
        url = "https://api.mch.weixin.qq.com/pay/downloadbill"
        data = {
            'bill_date': bill_date,
            'bill_type': bill_type if bill_type else 'SUCCESS',
            'appid': self.WX_APP_ID,
            'mch_id': self.WX_MCH_ID,
            'nonce_str': self.nonce_str()
        }
        data['sign'] = self.sign(data)
        raw = self.fetch(url, data)
        return raw

    def send_red_pack(self, api_cert_path, api_key_path, **data):
        """
        发给用户微信红包
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/tools/cash_coupon.php?chapter=13_4&index=3

        :param api_cert_path: 微信支付商户证书路径，此证书(apiclient_cert.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        :param api_key_path: 微信支付商户证书路径，此证书(apiclient_key.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        :param data: send_name, re_openid, total_amount, wishing, client_ip, act_name, remark
            send_name: 商户名称 例如: 天虹百货
            re_openid: 用户openid
            total_amount: 付款金额
            wishing: 红包祝福语 例如: 感谢您参加猜灯谜活动，祝您元宵节快乐！
            client_ip: 调用接口的机器Ip地址, 注：此地址为服务器地址
            act_name: 活动名称 例如: 猜灯谜抢红包活动
            remark: 备注 例如: 猜越多得越多，快来抢！
        :return: 红包发放结果
        """
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack"
        if "send_name" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数send_name")
        if "re_openid" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数re_openid")
        if "total_amount" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数total_amount")
        if "wishing" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数wishing")
        if "client_ip" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数client_ip")
        if "act_name" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数act_name")
        if "remark" not in data:
            raise WxPayError(u"向用户发送红包接口中，缺少必填参数remark")

        data.setdefault("wxappid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("mch_billno", u'{0}{1}{2}'.format(
            self.WX_MCH_ID, time.strftime('%Y%m%d', time.localtime(time.time())), self.random_num(10)
        ))
        data.setdefault("total_num", 1)
        data.setdefault("scene_id", 'PRODUCT_4')
        data.setdefault("sign", self.sign(data))

        raw = self.fetch_with_ssl(url, data, api_cert_path, api_key_path)
        if raw["return_code"] == "FAIL":
            raise WxPayError(raw["return_msg"])
        return raw

    def enterprise_payment(self, data):
        """
        使用企业对个人付款功能
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/tools/mch_pay.php?chapter=14_2

        # :param api_cert_path: 微信支付商户证书路径，此证书(apiclient_cert.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        # :param api_key_path: 微信支付商户证书路径，此证书(apiclient_key.pem)需要先到微信支付商户平台获取，下载后保存至服务器
        :param data: openid, check_name, re_user_name, amount, desc, spbill_create_ip
            openid: 用户openid
            check_name: 是否校验用户姓名
            re_user_name: 如果 check_name 为True，则填写，否则不带此参数
            amount: 金额: 企业付款金额，单位为分
            desc: 企业付款描述信息
            spbill_create_ip: 调用接口的机器Ip地址, 注：此地址为服务器地址
        :return: 企业转账结果
        """
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"
        if "openid" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数openid")
        if "check_name" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数check_name")
        if data['check_name'] and "re_user_name" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数re_user_name")
        if "amount" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数amount")
        if "desc" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数desc")
        if "spbill_create_ip" not in data:
            raise WxPayError(u"企业付款申请接口中，缺少必填参数spbill_create_ip")
        if "partner_trade_no" not in data:
            data.setdefault("partner_trade_no", u'{0}{1}{2}'.format(
                self.WX_MCH_ID, time.strftime('%Y%m%d', time.localtime(time.time())), self.random_num(10)
            ))
            # raise WxPayError(u"企业付款申请接口中，缺少必填参数partner_trade_no")

        data.setdefault("mch_appid", self.WX_APP_ID)
        data.setdefault("mchid", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())

        data['check_name'] = 'FORCE_CHECK' if data['check_name'] else 'NO_CHECK'
        data.setdefault("sign", self.sign(data))

        raw = self.fetch_with_ssl(url, data, config.c_api_cert_path, config.c_api_key_path)
        count = 5  # 以下为如果是系统繁忙则重新提交申请
        while 1:
            count = count - 1
            if raw["return_code"] == "FAIL" and raw["result_code"] == "FAIL" and raw.get("err_code") == "SYSTEMERROR":
                raw = self.fetch_with_ssl(url, data, config.c_api_cert_path, config.c_api_key_path)
            elif raw["return_code"] == "SUCCESS" and raw.get("err_code") == "SYSTEMERROR":
                raw = self.fetch_with_ssl(url, data, config.c_api_cert_path, config.c_api_key_path)
            else:  # 如果业务失败但不是系统繁忙，或者请求成功，但其他错误，例如签名错误，则直接退出
                break
            if count < 1 or raw["return_code"] == "SUCCESS" and raw["result_code"] == "SUCCESS":
                # 如果系统繁忙并且重试了5次仍然是系统繁忙，则直接退出
                break
            # raise WxPayError(raw["return_msg"])
        return raw

    def swiping_card_payment(self, **data):
        """
        提交刷卡支付
        详细规则参考 https://pay.weixin.qq.com/wiki/doc/api/micropay.php?chapter=9_10&index=1

        :param data: body, out_trade_no, total_fee, auth_code, (可选参数 device_info, detail, goods_tag, limit_pay)
            body: 商品描述
            *out_trade_no: 商户订单号
            total_fee: 标价金额, 整数, 单位 分
            auth_code: 微信支付二维码扫描结果
            *device_info: 终端设备号(商户自定义，如门店编号)
            user_ip 在flask框架下可以自动填写, 非flask框架需传入spbill_create_ip
        :return: 统一下单生成结果
        """
        url = "https://api.mch.weixin.qq.com/pay/micropay"

        # 必填参数
        if "body" not in data:
            raise WxPayError(u"缺少刷卡支付接口必填参数body")
        if "total_fee" not in data:
            raise WxPayError(u"缺少刷卡支付接口必填参数total_fee")
        if "out_trade_no" not in data:
            data.setdefault("out_trade_no", self.nonce_str())

        user_ip = self.user_ip_address()
        if not user_ip and "spbill_create_ip" not in data:
            raise WxPayError(u"当前未使用flask框架，缺少刷卡支付接口必填参数spbill_create_ip")

        data.setdefault("appid", self.WX_APP_ID)
        data.setdefault("mch_id", self.WX_MCH_ID)
        data.setdefault("nonce_str", self.nonce_str())
        data.setdefault("spbill_create_ip", user_ip)
        data.setdefault("sign", self.sign(data))

        raw = self.fetch(url, data)
        if raw["return_code"] == "FAIL":
            raise WxPayError(raw["return_msg"])
        err_msg = raw.get("err_code_des")
        if err_msg:
            raise WxPayError(err_msg)
        return raw


class CJsonEncoder(json.JSONEncoder):  # json 日期处理类
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)
# print(WxPay.random_num(8))
