
from cos_lib3.cos import Cos
root = ''  # yourweb
c_pay_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
c_app_id = ''  # 你的小程序appId
c_secret = ''  # 你的小程序密匙
c_grant_type = 'authorization_code'
c_str_body = '商城-订单'

c_mch_id = ''  # 商户号
c_sp_bill_create_ip = ''# 服务器主机的地址
c_notify_url = root+'v1/pay/notify/'  # 支付成功通知 
c_re_notify_url = root+'v1/refund/notify/'  # 退款成功通知

c_trade_type = 'JSAPI'

c_key = '&key=商户支付key'
c_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'  # // 统一下单API接口链接
c_templateID_order_success = '模板通知id'  # //支付成功通知
c_templateID_order_send = '模板通知Id'  # 订单发货通知


c_access_token_url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET'
c_sendTemplateMessage_url = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=ACCESS_TOKEN'
c_ip = "服务器主机的地址"
c_path = 'C:/cert/'
c_mch_url = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers'  # //商户转账给个人

c_merchant_key = '商户支付key'
c_access_token = None
c_page = 'pages/index/index'
c_api_cert_path = 'C:/cert/apiclient_cert.pem'  # 支付证书存放
c_api_key_path = 'C:/cert/apiclient_key.pem'  # 支付证书存放

# 账户的密匙
app_id = ''  #腾讯云账号
secret_id = ''  # 密匙Id
secret_key = ''  # 密匙key

cos = Cos(app_id=app_id, secret_id=secret_id, secret_key=secret_key, region='gz')  # 

showimgjs = """<script type="text/javascript">
        function showImg(url) {
            var frameid = 'frameimg' + Math.random();
            console.debug(frameid);
            console.debug(url);
            window.img = '<img id="img" style="width:100%" src=\\\'' + url + '?' + Math.random() + '\\\' /><script>window.onload = function() { parent.document.getElementById(\\\'' + frameid + '\\\').height = document.getElementById(\\\'img\\\').height+\\\'px\\\'; }<' + '/script>';
            document.write('<iframe id="' + frameid + '" src="javascript:parent.img;" frameBorder="0" scrolling="no" width="100%"></iframe>');
        }
    </script>"""
showimgjs1 = """<script type="text/javascript">
        showImg(\'"""

showimgjs2 = """\')</script>"""


# showimgjs 是用户转化微信公众号文章的，你懂的
def set_token(token):
    global c_access_token
    c_access_token = token


def get_token():
    return c_access_token
