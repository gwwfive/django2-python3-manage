from django.shortcuts import render
from main.models import *
from django.shortcuts import HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.forms.models import model_to_dict
from main.config import *
# from trip.models import *
# from cos_lib3.cos import CosAuth
import datetime
import decimal
import requests
import json
import math
import os
import re
from itertools import chain
from django.conf import settings
from main.wx_pay import WxPay
from main.AESTool import md5key, decrypt
import time


# from trip.wx_pay import WxPay, PicForm

class CJsonEncoder(json.JSONEncoder):  # json 日期处理类
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, datetime.time):
            return obj.strftime("%H:%M")
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


# Create your views here.

# 后台管理
@csrf_exempt
def index(request):
    return render(request, 'index.html')


# 搜索
@csrf_exempt
def search(request):
    if request.method == 'GET':
        searchKey = request.GET.get('searchKey')
        product = list(Product.objects.filter(Q(productName__icontains=searchKey) | Q(sellPoint__icontains=searchKey),
                                              status=1).values())
        return HttpResponse(json.dumps({'status': 1, 'list': product},cls=CJsonEncoder))


# 登录
@csrf_exempt
def login(request):
    if request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        admin = Admin.objects.filter(account=req.get('user_name'))
        if admin:
            if admin[0].passWord == req.get('password'):
                request.session['admin'] = req.get('user_name')
                return HttpResponse(json.dumps({'status': 1, 'success': '登录成功'}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': '账号或密码错误'}))
        else:
            return HttpResponse(json.dumps({'status': 0, 'message': '账号不存在'}))


# 登出
@csrf_exempt
def logout(request):
    try:
        del request.session['admin']
        return HttpResponse(json.dumps({'status': 1, 'success': '退出成功了'}))
    except Exception as e:
        return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 加载管理员信息
@csrf_exempt
def admin_info(request):
    if request.method == 'GET':
        if request.session.get('admin', False):
            admin = Admin.objects.get(account=request.session['admin'])
            return HttpResponse(json.dumps({'status': 1, 'adminInfo': model_to_dict(admin)}))
        else:
            return HttpResponse(json.dumps({'status': 0, 'message': '获取管理员信息错误', 'type': 'session过期'}))


@csrf_exempt
def admin(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.GET.get('offset') and request.GET.get('limit'):
                offset = int(request.GET.get('offset'))
                limit = int(request.GET.get('limit'))
                admin = Admin.objects.all().values('account', 'avatarUrl', 'isRoot', 'id', 'createTime', 'city')[
                        offset:offset + limit]
                return HttpResponse(json.dumps({'status': 1, 'admins': list(admin)}, cls=CJsonEncoder))
            else:
                return HttpResponse(json.dumps({'status': 1, 'count': Admin.objects.all().count()}))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        if Admin.objects.filter(account=req.get('accountName')):
            return HttpResponse(json.dumps({'status': 0, 'message': '账号已存在'}))
        else:
            Admin.objects.create(account=req.get('accountName'),
                                 passWord=req.get('passWord'),
                                 isRoot=req.get('isRoot'),
                                 avatarUrl=req.get('imagePath'))
            return HttpResponse(json.dumps({'status': 1, 'success': '创建成功'}))


# 统计数据
@csrf_exempt
def count(request):
    if request.method == 'GET':
        req = request.GET
        if int(req.get('type', 0)) == 1:
            if req.get('date'):
                date = datetime.datetime.strptime(req.get('date'), '%Y-%m-%d')
                # nextdate = date + datetime.timedelta(days=1)
                # userCount = User.objects.filter(createTime__lte=nextdate, createTime__gte=date).count()
                countDay = CountDay.objects.filter(day=date)
                if countDay:
                    countDay = {'status': 1, 'userCount': countDay[0].userNum, 'orderCount': countDay[0].orderNum,
                                'saleCount': countDay[0].sale}
                else:
                    countDay = {'status': 1, 'userCount': 0, 'orderCount': 0, 'saleCount': 0}
                return HttpResponse(json.dumps(countDay, cls=CJsonEncoder))
            else:
                count = Count.objects.filter()
                if count:
                    count = {'status': 1, 'userCount': count[0].userNum, 'orderCount': count[0].orderNum,
                             'saleCount': count[0].sale}
                else:
                    count = {'status': 1, 'userCount': 0, 'orderCount': 0, 'saleCount': 0}
                return HttpResponse(json.dumps(count, cls=CJsonEncoder))


# 分销
@csrf_exempt
def distribution(request):
    if request.method == 'GET':
        req = request.GET
        if int(req.get('type', 0)) == 1:
            distribution = Distribution.objects.filter()
            if distribution:
                distribution = model_to_dict(distribution[0])
            else:
                distribution = {
                }
            return HttpResponse(json.dumps({'status': 1, 'distribution': distribution}, cls=CJsonEncoder))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        try:
            with transaction.atomic():
                distribution = Distribution.objects.filter()
                for d in distribution:
                    d.delete()
                Distribution.objects.create(firstProfit=decimal.Decimal(req.get('firstProfit')),
                                            firstLimit=decimal.Decimal(req.get('firstLimit')),
                                            secondProfit=decimal.Decimal(req.get('secondProfit')),
                                            secondLimit=decimal.Decimal(req.get('secondLimit')))
                return HttpResponse(json.dumps({'status': 1}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


@csrf_exempt
def user(request):
    if request.method == 'GET':
        req = request.GET
        if int(request.GET.get('type', 0)) == 1:
            if req.get('date'):  # 根据日期返回数据
                if request.session.get('admin', False):
                    date = datetime.datetime.strptime(req.get('date'), '%Y-%m-%d')
                    # nextdate = date + datetime.timedelta(days=1)
                    # userCount = User.objects.filter(createTime__lte=nextdate, createTime__gte=date).count()
                    countDay = CountDay.objects.filter(day=date)
                    if countDay:
                        userCount = countDay[0].userNum
                    else:
                        userCount = 0
                    return HttpResponse(json.dumps({'count': userCount, 'status': 1}))
                else:
                    return HttpResponse(json.dumps({'message': '登录过期，请重新登录', 'status': 0}))
            elif req.get('limit') and req.get('offset'):
                limit = int(req.get('limit', 20))
                offset = int(req.get('offset', 0))
                user = User.objects.all().values().order_by('-createTime')[
                       offset:offset + limit]
                return HttpResponse(json.dumps({'status': 1, 'users': list(user)}, cls=CJsonEncoder))
            elif req.get('province') and req.get('city'):  # 根据省份城市返回用户数据
                userCount = User.objects.filter(province=req.get('province'), city=req.get('city')).count()
                return HttpResponse(json.dumps({'status': 1, 'count': userCount}))
            elif req.get('province'):  # 根据省份返回用户数据
                userCount = User.objects.filter(province=req.get('province')).count()
                return HttpResponse(json.dumps({'status': 1, 'count': userCount}))
            else:
                count = Count.objects.filter()
                if count:
                    num = count[0].allUserNum
                else:
                    num = 0
                return HttpResponse(json.dumps({'status': 1, 'count': num}))
        else:  # 是小程序端
            code = request.GET.get('code')
            print(code)
            if code:
                # 拼接url
                url_str = "https://api.weixin.qq.com/sns/jscode2session?appid=" + c_app_id \
                          + "&secret=" + c_secret \
                          + "&js_code=" + code \
                          + "&grant_type=" + c_grant_type
                # 发送请求获得openid
                print(url_str)
                # return
                res = requests.get(url_str).json()  # 返回的是dict格式的数据
                # print(res)
                if 'openid' in res.keys():
                    res1 = {}
                    open_id = res["openid"]
                    try:
                        user = User.objects.get(openId=open_id)
                        res1["userId"] = user.id
                    except User.DoesNotExist:  # 用户不存在
                        try:
                            with transaction.atomic():
                                user = User.objects.create(
                                    openId=open_id
                                )
                                # 商家总用户+1
                                count = Count.objects.filter()
                                if count:
                                    count = count[0]
                                else:
                                    count = Count.objects.create()
                                count.allUserNum += 1
                                count.save()
                                # 商家日用户+1
                                countDay = CountDay.objects.filter(day=datetime.datetime.now().date())
                                if countDay:
                                    countDay = countDay[0]
                                else:
                                    countDay = CountDay.objects.create(day=datetime.datetime.now().date())
                                countDay.userNum += 1
                                countDay.save()
                        except Exception as e:
                            pass

                        res1["userId"] = user.id
                    return HttpResponse(json.dumps(res1))
                else:
                    return HttpResponse(json.dumps(res))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        flag = int(req.get('flag', 0))
        if flag == 0:
            user = User.objects.get(id=req.get('userId'))
            if req.get('avatarUrl'):
                user.avatarUrl = req.get('avatarUrl')
            if req.get('nickName'):
                user.nickName = req.get('nickName')
            if req.get('phoneNum'):
                user.phoneNum = req.get('phoneNum')
            if req.get('gender'):
                user.gender = req.get('gender')
            if req.get('city'):
                user.city = req.get('city')
            if req.get('province'):
                user.province = req.get('province')
            user.save()
            res = {'status': 1}
        elif flag == 1:  # 分享者信息
            try:
                with transaction.atomic():
                    user = User.objects.get(id=req.get('userId'))
                    if not user.sharedStatus:
                        agent = Agent.objects.filter(user_id=req.get('shareId'))
                        if agent:  # 分享者是代理
                            agent = agent[0]
                            user.fansLevel = 1
                            user.agentId = agent.id
                            # 一级粉丝+1
                            agent.firstFans += 1
                            agent.save()
                            # 更新当日的代理粉丝数据
                            agentCountDay = AgentCountDay.objects.filter(agent_id=agent.id,
                                                                         day=datetime.datetime.now().date())
                            if agentCountDay:  # 存在
                                agentCountDay = agentCountDay[0]
                            else:
                                agentCountDay = AgentCountDay.objects.create(agent_id=agent.id,
                                                                             day=datetime.datetime.now().date())
                            agentCountDay.firstFans += 1
                            agentCountDay.save()
                            pass
                        else:  # 分享者不是代理
                            shareUser = User.objects.filter(id=req.get('shareId'))
                            if shareUser:  # 如果分享者是用户（shareId可能为0）
                                shareUser = shareUser[0]
                                if shareUser.agentId != 0:  # 分享者是某代理的粉丝
                                    agent = Agent.objects.get(id=shareUser.agentId)
                                    user.fansLevel = 2
                                    user.agentId = shareUser.agentId
                                    agent.secondFans += 1
                                    agent.save()
                                    # user.sharedStatus = True
                                    # 更新当日的代理粉丝数据
                                    agentCountDay = AgentCountDay.objects.filter(agent_id=agent.id,
                                                                                 day=datetime.datetime.now().date())
                                    if agentCountDay:  # 存在
                                        agentCountDay = agentCountDay[0]
                                    else:
                                        agentCountDay = AgentCountDay.objects.create(agent_id=agent.id,
                                                                                     day=datetime.datetime.now().date())
                                    agentCountDay.secondFans += 1
                                    agentCountDay.save()
                                    pass
                            # else:  # 分享者可能还没有被代理。那么不管
                        user.sharedStatus = True  # 初次访问这条记录会把sharedStatus设为true
                        user.save()
                    res = {'status': 1}
            except Exception as e:
                res = {'status': 0, 'message': str(e)}
            # return HttpResponse(json.dumps({res}))
        else:
            res = {'return_code': 'FAIL'}
        return HttpResponse(json.dumps(res))


@csrf_exempt
def sale(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                if request.GET.get('date'):  # 根据日期返回数据
                    date = datetime.datetime.strptime(request.GET.get('date'), '%Y-%m-%d')
                    # nextdate = date + datetime.timedelta(days=1)
                    # orders = Order.objects.filter(createTime__lte=nextdate, createTime__gte=date, status=1)
                    # sale = 0
                    # for o in orders:
                    #     sale += o.total
                    countDay = CountDay.objects.filter(day=date)
                    if countDay:
                        sale = countDay[0].sale
                    else:
                        sale = 0
                    return HttpResponse(json.dumps({'count': sale, 'status': 1}, cls=CJsonEncoder))
                count = Count.objects.all()
                if count:
                    count = count[0].allSale
                else:
                    count = 0
                return HttpResponse(json.dumps({'status': 1, 'count': count}, cls=CJsonEncoder))
            else:
                return HttpResponse(json.dumps({'message': '登录过期，请重新登录', 'status': 0}))


@csrf_exempt
def shop(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                shop = Shop.objects.filter()
                if shop:
                    shop = shop[0]
                else:
                    shop = Shop.objects.create()
                return HttpResponse(json.dumps({'status': 1, 'shop': model_to_dict(shop)}))
            return HttpResponse(json.dumps({'status': 0, 'message': '登录过期'}))
        else:
            shop = Shop.objects.filter()
            if shop:
                shop = shop[0]
                return HttpResponse(json.dumps({'status': 1, 'shop': model_to_dict(shop)}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': '没有商店信息'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        shop = Shop.objects.filter()
        if shop:
            shop = shop[0]
        else:
            shop = Shop.objects.create()
        shop.shopName = req.get('name')
        shop.shopAddress = req.get('address')
        shop.shopPhoneNum = req.get('contact')
        shop.shopImgUrl = req.get('imageUrl')
        shop.shopIntroduce = req.get('desc')
        if req.get('lat') and req.get('lng'):
            shop.lat = str(req.get('lat'))
            shop.lng = str(req.get('lng'))
        else:
            # 根据地址返回经纬度
            url = 'https://apis.map.qq.com/ws/geocoder/v1/?address=' + req.get(
                'address') + '&key=DG2BZ-7XEKK-V5WJ7-AF5Z4-YQNL5-MYFLU'
            res = requests.get(url=url)
            res = json.loads(res.content.decode('utf-8'))
            if res.get('status') == 0:
                shop.lat = str(res.get('result').get('location').get('lat'))
                shop.lng = str(res.get('result').get('location').get('lng'))
            else:
                return HttpResponse({'status': 0, 'message': '找不到该地址'})
        shop.save()
        return HttpResponse(json.dumps({'status': 1}))


# 上传图片
@csrf_exempt
def upload_image(request):
    if request.method == 'POST':
        img = request.FILES.get('img')
        print(request.FILES)
        floder = os.path.join(settings.STATIC_ROOT, 'tempImg')
        if not os.path.exists(floder):
            os.makedirs(floder)
        filename = str(datetime.datetime.now().timestamp()) + img.name
        dest = os.path.join(floder, filename).replace("\\", "/")
        if os.path.exists(dest):
            os.remove(dest)
        with open(dest, 'wb') as f:
            for chrunk in img.chunks():
                f.write(chrunk)
            f.close()
        # 上传cos
        bucket = cos.get_bucket("native")
        data = bucket.upload_file(real_file_path=dest, file_name=filename)
        access_url = eval(data).get('access_url')
        if access_url:
            os.remove(dest)
            return HttpResponse(json.dumps({'status': 1, 'imageUrl': access_url}))
        else:
            return HttpResponse(json.dumps({'status': 0, 'msg': '上传cos失败'}))


# 加载商品分类
@csrf_exempt
def category(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                flag = int(request.GET.get('flag', 0))
                if flag == 0:
                    fCategory = list(Category.objects.filter(fatherId=0).values())
                    for fc in fCategory:
                        scategory = list(Category.objects.filter(fatherId=fc.get('id')).values())
                        for sc in scategory:
                            sscategory = list(Category.objects.filter(fatherId=sc.get('id')).values())
                            if sscategory:
                                sc.setdefault('children', sscategory)
                        if scategory:
                            fc.setdefault('children', scategory)
                    return HttpResponse(json.dumps({'status': 1, 'category': fCategory}))
                elif request.GET.get('limit') and request.GET.get('offset') and flag == 1:
                    limit = int(request.GET.get('limit'))
                    offset = int(request.GET.get('offset'))
                    category = list(Category.objects.filter(fatherId=0).values()[offset:offset + limit])
                    for c in category:
                        c.setdefault('productNum', Product.objects.filter(category_id=c.get('id')).count())
                    return HttpResponse(json.dumps({'status': 1, 'category': category}, cls=CJsonEncoder))
                elif flag == 2:
                    return HttpResponse(
                        json.dumps({'status': 1, 'category': Category.objects.filter(fatherId=0).count()},
                                   cls=CJsonEncoder))

            return HttpResponse(json.dumps({'status': 0, 'message': '登录过期'}))
        else:
            fCategory = list(Category.objects.filter(fatherId=0, status=1).values())
            # for fc in fCategory:
            #     scategory = list(Category.objects.filter(fatherId=fc.get('id')).values())
            #     for sc in scategory:
            #         sscategory = list(Category.objects.filter(fatherId=sc.get('id')).values())
            #         if sscategory:
            #             sc.setdefault('children', sscategory)
            #     if scategory:
            #         fc.setdefault('children', scategory)
            for f in fCategory:
                f.setdefault('productNum', Product.objects.filter(category_id=f.get('id')).count())
            return HttpResponse(json.dumps({'status': 1, 'category': fCategory}))
        return HttpResponse(json.dumps({'status': 0, 'message': '类型错误'}))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:
            category = req.get('category')
            # shopId = req.get('shopId')
            fatherId = req.get('fatherId', 0)
            categorys = category.split('；')
            for c in categorys:
                if not Category.objects.filter(label=c, fatherId=fatherId).exists():
                    c = Category.objects.create(label=c, fatherId=fatherId)
                    c.value = str(c.id)
                    c.save()
            return HttpResponse(json.dumps({'status': 1, 'success': '添加分类成功'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        category = Category.objects.get(id=req.get('categoryId'))
        if req.get('status'):
            category.status = int(req.get('status'))
        if req.get('label'):
            category.label = req.get('label')
        category.save()
        return HttpResponse(json.dumps({'status': 1}))
    elif request.method == 'DELETE':
        try:
            req = json.loads(request.body.decode('utf-8'))
            category = Category.objects.get(id=req.get('categoryId'))
            category.delete()
            return HttpResponse(json.dumps({'status': 1}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 添加产品
@csrf_exempt
def product(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                if request.GET.get('offset') and request.GET.get('limit'):
                    offset = int(request.GET.get('offset'))
                    limit = int(request.GET.get('limit'))
                    # print(int(request.GET.get('shopId', 0)))
                    # shopId = int(request.GET.get('shopId', 0))
                    # if shopId:
                    #     product = Product.objects.filter(shop_id=shopId).values()[offset:offset + limit]
                    # else:
                    product = list(Product.objects.all().values()[offset:offset + limit])
                    # product = list(product)
                    for p in product:
                        print(p)
                        # shop = Shop.objects.get(id=p.get('shop_id'))
                        category = Category.objects.get(id=p.get('category_id'))
                        # p.setdefault('shopName', shop.shopName)
                        p.setdefault('categoryName', category.label)
                        # p.setdefault('shopAddress', shop.shopAddress)
                    return HttpResponse(json.dumps({'status': 1, 'products': product}, cls=CJsonEncoder))
                elif request.GET.get('productId'):
                    product = Product.objects.get(id=request.GET.get('productId'))
                    productFormat = ProductFormat.objects.filter(product_id=product.id).values()
                    sku = SKU.objects.filter(product_id=product.id).values()
                    pricture = Picture.objects.filter(product_id=product.id).values()
                    product = model_to_dict(product)
                    product.setdefault('catrgorySelect', eval(product.get('categoryList')))
                    product.setdefault('specs', list(sku))
                    product.setdefault('formats', list(productFormat))
                    product.setdefault('sellPoints', (product.get('sellPoint')).split(';'))
                    product.setdefault('carousels', list(pricture))
                    return HttpResponse(json.dumps({'status': 1, 'product': product}, cls=CJsonEncoder))
                else:
                    return HttpResponse(json.dumps(
                        {'status': 1, 'count': Product.objects.all().count()}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': '登录过期'}))
        else:
            flag = int(request.GET.get('flag', 0))
            page = int(request.GET.get('page', 0))
            if flag == 1:  # 获取推荐列表
                products = list(Product.objects.filter(status=1).order_by('saleNum', 'rate')[0:10].values())
                return HttpResponse(json.dumps({'status': 1, 'products': products}, cls=CJsonEncoder))
            elif flag == 2:  # 加载单个产品的信息，非团购信息
                product = Product.objects.get(id=request.GET.get('id'))
                pics = list(Picture.objects.filter(product_id=product.id).values())
                sku = list(SKU.objects.filter(product_id=product.id, status=1).values())
                productFormat = list(ProductFormat.objects.filter(product_id=product.id).values())
                product = model_to_dict(product)
                product.setdefault('carousel', pics)
                product.setdefault('sku', sku)
                product.setdefault('format', productFormat)
                product.setdefault('isCollect', UserProduct.objects.filter(user_id=request.GET.get('userId', 0),
                                                                           product_id=product.get('id')).exists())
                saleNum = 0
                for s in sku:
                    saleNum += s.get('saleNum')
                product['saleNum'] = saleNum
                return HttpResponse(json.dumps({'status': 1, 'product': product}, cls=CJsonEncoder))
            elif flag == 3:  # 根据类型id 返回产品
                categoryId = request.GET.get('categoryId')
                page = int(request.GET.get('page'))
                products = list(
                    Product.objects.filter(categoryList__contains=categoryId, status=1).values()[
                    page * 20:(page + 1) * 20])
                return HttpResponse(json.dumps({'status': 1, 'products': products}, cls=CJsonEncoder))
            elif flag == 4:  # 返回用户收藏的商品
                userProduct = list(UserProduct.objects.filter(user_id=
                                                              request.GET.get('userId'))
                                   .values('product_id',
                                           'product__productName',
                                           'product__imgUrl',
                                           'product__category__label',
                                           'product__originPrice',
                                           'product__status')[page * 20:(page + 1) * 20])
                return HttpResponse(json.dumps({'status': 1, 'userProduct': userProduct}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:
            if request.session.get('admin', False):
                try:
                    with transaction.atomic():
                        sellPoint = ''
                        for s in req.get('sellPoint'):
                            sellPoint += s + ';'
                        if not sellPoint:
                            sellPoint = ''
                        print(sellPoint)
                        specs = req.get('specs')
                        product = Product.objects.create(productName=req.get('name'),
                                                         imgUrl=req.get('imageUrl'),
                                                         # shop_id=req.get('shopId'),
                                                         category_id=req.get('categorySelect')[
                                                             len(req.get('categorySelect')) - 1],
                                                         categoryList=str(req.get('categorySelect')),
                                                         sellPoint=sellPoint,
                                                         introduce=req.get('productDetail', 0),
                                                         price=decimal.Decimal(specs[0].get('price')),
                                                         originPrice=decimal.Decimal(specs[0].get('market_price')),
                                                         )
                        for s in req.get('formats'):
                            if s.get('name') and s.get('value'):
                                ProductFormat.objects.create(formatName=s.get('name'), formatValue=s.get('value'),
                                                             product_id=product.id)
                        for c in req.get('carousels'):
                            Picture.objects.create(picUrl=c, product_id=product.id)
                        for f in specs:
                            SKU.objects.create(product_id=product.id, residualNum=f.get('sku_num'),
                                               sellPrice=decimal.Decimal(f.get('price')),
                                               originPrice=decimal.Decimal(f.get('market_price')),
                                               skuName=f.get('specs'))
                        return HttpResponse(json.dumps({'status': 1, 'success': '添加成功'}))

                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:
            if request.session.get('admin', False):
                flag = int(req.get('flag', 0))
                if flag == 0:  # 提交修改的商品（要区分上线后和没有上线）
                    try:
                        with transaction.atomic():
                            sellPoint = ''
                            for s in req.get('sellPoint'):
                                sellPoint += s + ';'
                            if not sellPoint:
                                sellPoint = ''
                            print(sellPoint)
                            specs = req.get('specs')
                            product = Product.objects.get(id=req.get('productId'))
                            if req.get('name'):
                                product.productName = req.get('name')
                            if req.get('imageUrl'):
                                product.imgUrl = req.get('imageUrl')
                            if req.get('categorySelect'):
                                product.category_id = req.get('categorySelect')[
                                    len(req.get('categorySelect')) - 1]
                                product.categoryList = str(req.get('categorySelect'))
                            if sellPoint:
                                product.sellPoint = sellPoint
                            if req.get('productDetail', ''):
                                product.introduce = req.get('productDetail')
                            if specs:
                                product.price = decimal.Decimal(specs[0].get('price'))
                                product.originPrice = decimal.Decimal(specs[0].get('market_price'))
                                if product.status == 0:  # 没有过的线
                                    skus = SKU.objects.filter(product_id=product.id)
                                    for sku in skus:
                                        sku.delete()
                                    for f in specs:
                                        SKU.objects.create(product_id=product.id, residualNum=f.get('sku_num'),
                                                           sellPrice=decimal.Decimal(f.get('price')),
                                                           originPrice=decimal.Decimal(f.get('market_price')),
                                                           skuName=f.get('specs'))
                                elif product.status == 2:  # 是编辑
                                    for f in specs:
                                        sku = SKU.objects.filter(id=f.get('id'))
                                        if sku:  # 是修改的
                                            sku = sku[0]
                                            print(f.get('sku_num'))
                                            print(f)
                                            if f.get('sku_num') or f.get('sku_num') == 0:
                                                sku.residualNum = f.get('sku_num')
                                            if f.get('price'):
                                                sku.sellPrice = decimal.Decimal(f.get('price'))
                                            if f.get('market_price'):
                                                sku.originPrice = decimal.Decimal(f.get('market_price'))
                                            if f.get('specs'):
                                                sku.skuName = f.get('specs')
                                            sku.save()
                                        else:  # 是新增的
                                            SKU.objects.create(product_id=product.id, residualNum=f.get('sku_num'),
                                                               sellPrice=decimal.Decimal(f.get('price')),
                                                               originPrice=decimal.Decimal(f.get('market_price')),
                                                               skuName=f.get('specs'))
                            pfs = ProductFormat.objects.filter(product_id=product.id)
                            for pf in pfs:
                                pf.delete()
                            for s in req.get('formats', []):
                                if s.get('name') and s.get('value'):
                                    ProductFormat.objects.create(formatName=s.get('name'), formatValue=s.get('value'),
                                                                 product_id=product.id)
                            pcs = Picture.objects.filter(product_id=product.id)
                            for pc in pcs:
                                pc.delete()
                            for c in req.get('carousels', []):
                                Picture.objects.create(picUrl=c, product_id=product.id)
                            product.save()
                            return HttpResponse(json.dumps({'status': 1, 'success': '修改成功'}))
                    except Exception as e:
                        return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
                elif flag == 1:  # 修改单个sku 的状态
                    sku = SKU.objects.get(id=req.get('skuId'))
                    sku.status = int(req.get('status'))
                    sku.save()
                    return HttpResponse(json.dumps({'status': 1}))
                elif flag == 2:  # 修改商品状态
                    product = Product.objects.get(id=req.get('productId'))
                    product.status = int(req.get('status'))
                    product.save()
                    return HttpResponse(json.dumps({'status': 1}))
        else:
            if req.get('userId') and req.get('productId'):
                userProduct = UserProduct.objects.filter(user_id=req.get('userId'), product_id=req.get('productId'))
                if userProduct:
                    userProduct = userProduct[0]
                    userProduct.delete()
                else:
                    UserProduct.objects.create(user_id=req.get('userId'), product_id=req.get('productId'))
                return HttpResponse(json.dumps({'status': 1, 'message': '操作成功'}))


# 订单
@csrf_exempt
def order(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                if request.GET.get('offset') and request.GET.get('limit'):
                    offset = int(request.GET.get('offset'))
                    limit = int(request.GET.get('limit'))
                    index = int(request.GET.get('index', 0))
                    if index == 0:  # 支付完成未发货
                        orders = list(Order.objects.filter(Q(status=1, orderType=0) | Q(status=8, orderType=1)).values(
                            'user_id',
                            'user__nickName',
                            'province',
                            'city',
                            'area',
                            'address',
                            'name',
                            'phoneNum',
                            'total',
                            'realTotal',
                            'createTime',
                            # 'skuNum',
                            'status',
                            'id',
                            'out_trade_no',
                            'order_code',
                            'orderType',
                            'prepay_id',

                        ).order_by('-payTime')[
                                      offset:offset + limit])
                    elif index == 1:  # 发货，未收货
                        orders = list(Order.objects.filter(status=2).values(
                            'user_id',
                            'user__nickName',
                            'province',
                            'city',
                            'area',
                            'address',
                            'name',
                            'phoneNum',
                            'total',
                            'realTotal',
                            'createTime',
                            # 'skuNum',
                            'status',
                            'id',
                            'out_trade_no',
                            'order_code',
                            'orderType',
                            'prepay_id',
                            'express',
                            'expressNo',
                            'expressTime',
                        ).order_by('-expressTime')[
                                      offset:offset + limit])
                        # res = {'status': 1, 'orders': list(orders)}
                    elif index == 2:  # 收货完成
                        orders = list(Order.objects.filter(Q(status=3) | Q(status=4)).values(
                            'user_id',
                            'user__nickName',
                            'province',
                            'city',
                            'area',
                            'address',
                            'name',
                            'phoneNum',
                            'total',
                            'realTotal',
                            'createTime',
                            # 'skuNum',
                            'status',
                            'id',
                            'out_trade_no',
                            'order_code',
                            'orderType',
                            'prepay_id',
                            'express',
                            'expressNo',
                            'expressTime',
                        ).order_by('-receiveTime')[
                                      offset:offset + limit])
                        # res = {'status': 1, 'orders': list(orders)}
                    elif index == 3:  # 申请退款
                        orders = list(Order.objects.filter(status=6).values(
                            'user_id',
                            'user__nickName',
                            'province',
                            'city',
                            'area',
                            'address',
                            'name',
                            'phoneNum',
                            'total',
                            'realTotal',
                            'createTime',
                            # 'skuNum',
                            'status',
                            'id',
                            'out_trade_no',
                            'order_code',
                            'orderType',
                            'prepay_id', 'express',
                            'expressNo',
                            'expressTime', )[
                                      offset:offset + limit])
                        # res = {'status': 1, 'orders': list(orders)}
                    elif index == 4:  # 全部
                        orders = list(Order.objects.filter(~(Q(status=9) | Q(status=0))).values(
                            'user_id',
                            'user__nickName',
                            'province',
                            'city',
                            'area',
                            'address',
                            'name',
                            'phoneNum',
                            'total',
                            'realTotal',
                            'createTime',
                            # 'skuNum',
                            'status',
                            'id',
                            'out_trade_no',
                            'order_code',
                            'orderType',
                            'prepay_id', 'express',
                            'expressNo',
                            'expressTime', ).order_by('-id')[
                                      offset:offset + limit])
                        # res = {'status': 1, 'orders': list(orders)}
                    else:
                        # res = {'status': 0, 'message': '没有此列表'}
                        orders = []
                    for o in orders:
                        orderSkus = list(OrderSku.objects.filter(order_id=o.get('id')).values())
                        o.setdefault('orderSkus', orderSkus)
                    res = {'status': 1, 'orders': orders}
                    return HttpResponse(json.dumps(res, cls=CJsonEncoder))
                elif request.GET.get('date'):  # 根据日期返回数据
                    date = datetime.datetime.strptime(request.GET.get('date'), '%Y-%m-%d')
                    # nextdate = date + datetime.timedelta(days=1)
                    # orderCount = Order.objects.filter(createTime__lte=nextdate, createTime__gte=date,
                    #                                   status=1).count()
                    countDay = CountDay.objects.filter(day=date)
                    if countDay:
                        orderCount = countDay[0].orderNum
                    else:
                        orderCount = 0
                    return HttpResponse(json.dumps({'count': orderCount, 'status': 1}))
                    # return HttpResponse(json.dumps({'status': 1, 'count': Order.objects.filter(state=1).count()}))
                elif request.GET.get('index'):
                    index = int(request.GET.get('index', 0))
                    if index == 0:
                        res = {'status': 1, 'count': Order.objects.filter(
                            Q(status=1, orderType=0) | Q(status=8, orderType=1)).count()}
                    elif index == 1:
                        res = {'status': 1, 'count': Order.objects.filter(status=2).count()}
                    elif index == 2:
                        res = {'status': 1, 'count': Order.objects.filter(Q(status=3) | Q(status=4)).count()}
                    elif index == 3:
                        res = {'status': 1, 'count': Order.objects.filter(tatus=6).count()}
                    elif index == 4:
                        res = {'status': 1, 'count': Order.objects.filter(~Q(status=0)).count()}
                    else:
                        res = {'status': 0, 'message': '没有此栏'}
                    return HttpResponse(json.dumps(res))
                else:
                    count = Count.objects.filter()
                    if count:
                        num = count[0].allOrderNum
                    else:
                        num = 0
                    res = {'status': 1,
                           'count': num}
                    return HttpResponse(json.dumps(res))
            return HttpResponse(json.dumps({'status': 0, 'message': '登录过期'}))
        else:
            if request.GET.get('orderId'):
                order = Order.objects.get(id=request.GET.get('orderId'))
                orderSku = list(OrderSku.objects.filter(order_id=order.id).values())
                order = model_to_dict(order)
                order.setdefault('orderSku', orderSku)
                return HttpResponse(json.dumps({'status': 1, 'order': order}, cls=CJsonEncoder))
            else:
                flag = int(request.GET.get('flag', 0))
                page = int(request.GET.get('page', 0))
                if flag == 0:  # 加载用户所有订单
                    orders = list(
                        Order.objects.filter(~Q(status=9)).values().order_by('-createTime')[page * 10:(page + 1) * 10])
                    for order in orders:
                        orderSku = list(OrderSku.objects.filter(order_id=order.get('id')).values())
                        order.setdefault('orderSku', orderSku)
                    return HttpResponse(json.dumps({'status': 1, 'orders': orders}, cls=CJsonEncoder))
                if flag == 1:  # 加载用户待付款订单
                    orders = list(
                        Order.objects.filter(Q(status=0) | Q(status=10)).values().order_by('-createTime')[
                        page * 10:(page + 1) * 10])
                    for order in orders:
                        orderSku = list(OrderSku.objects.filter(order_id=order.get('id')).values())
                        order.setdefault('orderSku', orderSku)
                    return HttpResponse(json.dumps({'status': 1, 'orders': orders}, cls=CJsonEncoder))
                if flag == 2:  # 加载用户待收货订单
                    orders = list(
                        Order.objects.filter(Q(status=1) | Q(status=2)).values().order_by('-createTime')[
                        page * 10:(page + 1) * 10])
                    for order in orders:
                        orderSku = list(OrderSku.objects.filter(order_id=order.get('id')).values())
                        order.setdefault('orderSku', orderSku)
                    return HttpResponse(json.dumps({'status': 1, 'orders': orders}, cls=CJsonEncoder))
                if flag == 3:  # 加载用户待评价订单
                    orders = list(
                        Order.objects.filter(Q(status=3)).values().order_by('-createTime')[
                        page * 10:(page + 1) * 10])
                    for order in orders:
                        orderSku = list(OrderSku.objects.filter(order_id=order.get('id')).values())
                        order.setdefault('orderSku', orderSku)
                    return HttpResponse(json.dumps({'status': 1, 'orders': orders}, cls=CJsonEncoder))
                if flag == 4:  # 加载用户已完成订单
                    orders = list(
                        Order.objects.filter(Q(status=4)).values().order_by('-createTime')[
                        page * 10:(page + 1) * 10])
                    for order in orders:
                        orderSku = list(OrderSku.objects.filter(order_id=order.get('id')).values())
                        order.setdefault('orderSku', orderSku)
                    return HttpResponse(json.dumps({'status': 1, 'orders': orders}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        flag = int(req.get('flag', 0))
        if flag == 0:
            try:
                with transaction.atomic():
                    order = Order.objects.filter(user_id=req.get('userId'), status=9)
                    if order:
                        order = order[0]
                    else:
                        order = Order.objects.create(user_id=req.get('userId'), createTime=datetime.datetime.now())
                    orderskus = OrderSku.objects.filter(order_id=order.id)
                    for os in orderskus:
                        os.delete()
                    if req.get('selectSku'):
                        for s in req.get('selectSku'):
                            # product = Product.objects.filter(pr)
                            OrderSku.objects.create(sku_id=s.get('skuId'), cartSkuId=s.get('cartId'),
                                                    skuPrice=s.get('price'),
                                                    skuNum=s.get('skuNum'),
                                                    skuName=s.get('skuName'),
                                                    productName=s.get('productName'),
                                                    order_id=order.id,
                                                    imgUrl=s.get('imgUrl'))
                    elif req.get('orderId'):  # 再次购买
                        # onceOrder = Order.objects.get(id=req.get('orderId'))
                        onceOrderSku = OrderSku.objects.filter(order_id=req.get('orderId'))
                        for s in onceOrderSku:
                            # product = Product.objects.filter(pr)
                            OrderSku.objects.create(sku_id=s.sku_id, cartSkuId=s.cartSkuId,
                                                    skuPrice=s.skuPrice,
                                                    skuNum=s.skuNum,
                                                    skuName=s.skuName,
                                                    productName=s.productName,
                                                    order_id=order.id,
                                                    imgUrl=s.imgUrl)
                    return HttpResponse(json.dumps({'status': 1, 'order': order.id}))
            except Exception as e:
                return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
        elif flag == 1:  # 是立即支付
            try:
                with transaction.atomic():
                    sku = SKU.objects.get(id=req.get('skuId'))
                    if sku.residualNum > 0:
                        sku.residualNum -= 1
                        sku.save()
                        order = Order.objects.create(
                            user_id=req.get('userId'),
                            total=sku.sellPrice,
                            realTotal=sku.sellPrice,
                            createTime=datetime.datetime.now(),
                            out_trade_no=str(int(datetime.datetime.now().timestamp())) + str(
                                WxPay.random_num(8)),
                            order_code=str(int(datetime.datetime.now().timestamp())) + str(
                                WxPay.random_num(3)),
                            status=9,
                            orderType=0,
                            collagerId=0,
                            province=req.get('province'),
                            city=req.get('city'),
                            area=req.get('area'),
                            address=req.get('address'),
                            name=req.get('name'),
                            phoneNum=req.get('phoneNum'),
                        )
                        # 3.生成orderSku
                        # sku = SKU.objects.get(id=collageSku.sku_id)
                        product = Product.objects.get(id=sku.product_id)
                        OrderSku.objects.create(
                            sku_id=sku.id,
                            skuPrice=sku.sellPrice,
                            skuNum=1,
                            skuName=sku.skuName,
                            productName=product.productName,
                            imgUrl=product.imgUrl,
                            order_id=order.id,
                        )
                        # 4.发起预支付
                        user = User.objects.get(id=req.get('userId'))
                        data = {
                            'body': '商品-订单',  # 商品描述
                            'out_trade_no': order.out_trade_no,  # 商户订单号
                            'total_fee': int(order.realTotal * 100),
                            'spbill_create_ip': c_sp_bill_create_ip,
                            # 'notify_url': c_notify_url,
                            'trade_type': c_trade_type,
                            'openid': user.openId, }
                        wx_pay = WxPay(c_notify_url)
                        res = wx_pay.unified_order(data)
                        # 把购物车清空
                        order.prePayTime = datetime.datetime.now()
                        if res.get("prepay_id"):
                            order.prepay_id = res["prepay_id"]
                            order.status = 10  # 预支付成功
                            order.save()
                            res = {'status': 1, 'message': '支付成功', 'res': res}
                        else:
                            raise Exception('预支付失败')
                            # order.status = 0  # 支付失败(未支付)
                            # order.save()
                            # res = {'status': 3, 'message': '支付失败', 'res': res}
                    else:
                        res = {'status': 2, 'message': '余量不足'}
            except Exception as e:
                res = {'status': 0, 'message': str(e)}
            return HttpResponse(json.dumps(res))
        # 1.用户
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:  # 是电脑端
            order = Order.objects.get(id=req.get('orderId'))
            order.express = req.get('expressType').get('label')
            order.expressCode = req.get('expressType').get('value')
            order.expressNo = req.get('expressNo')
            order.expressTime = datetime.datetime.now()
            order.status = 2
            order.save()
            return HttpResponse(json.dumps({'status': 1, 'message': '成功'}))
        else:
            flag = int(req.get('flag', 0))
            if req.get('out_trade_no') and flag == 0:  # 用户取消支付时
                order = Order.objects.get(out_trade_no=req.get('out_trade_no'))
                if int(req.get('status')) == 5 and order.orderType == 1:  # 是取消订单
                    collageUser = CollageUser.objects.get(user_id=order.user_id, collagerId=order.collagerId)
                    collageUser.delete()
                    order.status = int(req.get('status'))
                    order.save()
                else:
                    order.status = int(req.get('status'))
                    order.save()
                return HttpResponse(json.dumps({'status': 1, 'message': '修改成功'}))
            elif req.get('orderId') and req.get('userId') and flag == 1:  # 重新支付
                try:
                    with transaction.atomic():
                        order = Order.objects.filter(id=req.get('orderId'), status=0)
                        if order:
                            order = order[0]
                        else:
                            raise Exception('订单已经过期或取消')
                        user = User.objects.get(id=req.get('userId'))
                        out_trade_no = str(int(datetime.datetime.now().timestamp())) + str(
                            WxPay.random_num(8))
                        data = {
                            'body': '商品-订单',  # 商品描述
                            'out_trade_no': out_trade_no,  # 商户订单号
                            'total_fee': int(order.realTotal * 100),
                            'spbill_create_ip': c_sp_bill_create_ip,
                            # 'notify_url': c_notify_url,
                            'trade_type': c_trade_type,
                            'openid': user.openId, }
                        order.out_trade_no = out_trade_no
                        wx_pay = WxPay(c_notify_url)
                        res = wx_pay.unified_order(data)
                        order.prePayTime = datetime.datetime.now()
                        if res.get("prepay_id"):
                            order.prepay_id = res["prepay_id"]
                            order.status = 10  # 预支付成功
                            order.save()
                            return HttpResponse(json.dumps({'status': 1, 'message': '支付成功', 'res': res}))
                        else:
                            order.status = 0  # 支付失败(未支付)
                            order.save()
                            return HttpResponse(json.dumps({'status': 2, 'message': '支付失败', 'res': res}))
                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
            elif req.get('orderId') and req.get('userId') and flag == 2:  # 首次支付
                order = Order.objects.get(id=req.get('orderId'))
                try:
                    with transaction.atomic():
                        # 校验余量是否充足
                        orderSkus = OrderSku.objects.filter(order_id=order.id)
                        for o in orderSkus:
                            sku = SKU.objects.filter(id=o.sku_id, residualNum__gte=o.skuNum)
                            if sku:
                                sku = sku[0]
                                sku.residualNum -= o.skuNum
                                sku.save()
                            else:
                                raise Exception(o.skuName + '余量不足')
                        # 如果有优惠券，那么把优惠券改为已使用
                        if req.get('coupon'):
                            userCoupon = UserCoupon.objects.get(user_id=req.get('userId'),
                                                                coupon_id=req.get('coupon').get('id'))
                            userCoupon.status = 1
                            userCoupon.save()
                        order.total = decimal.Decimal(req.get('total'))
                        order.realTotal = decimal.Decimal(req.get('realTotal'))
                        order.discount = decimal.Decimal(req.get('discount', 0.00))
                        order.out_trade_no = str(int(datetime.datetime.now().timestamp())) + str(
                            WxPay.random_num(8))
                        order.order_code = str(int(datetime.datetime.now().timestamp() * 1000)) + str(
                            WxPay.random_num(3))
                        order.createTime = datetime.datetime.now()  # 认为订单只有在支付的时候才算新的订单生成

                        order.province = req.get('address').get('province')
                        order.city = req.get('address').get('city')
                        order.area = req.get('address').get('area')
                        order.phoneNum = req.get('address').get('phoneNum')
                        order.name = req.get('address').get('name')
                        order.address = req.get('address').get('address')
                        # order.save()
                        user = User.objects.get(id=req.get('userId'))
                        data = {
                            'body': '商品-订单',  # 商品描述
                            'out_trade_no': order.out_trade_no,  # 商户订单号
                            'total_fee': int(order.realTotal * 100),
                            'spbill_create_ip': c_sp_bill_create_ip,
                            # 'notify_url': c_notify_url,
                            'trade_type': c_trade_type,
                            'openid': user.openId, }
                        wx_pay = WxPay(c_notify_url)
                        res = wx_pay.unified_order(data)
                        # 把购物车清空
                        orderSkus = OrderSku.objects.filter(order_id=order.id)
                        for orderSku in orderSkus:
                            cartSku = CartSku.objects.filter(id=orderSku.cartSkuId)
                            for cs in cartSku:
                                cs.delete()
                        order.prePayTime = datetime.datetime.now()
                        if res.get("prepay_id"):
                            order.prepay_id = res["prepay_id"]
                            order.status = 10  # 预支付成功
                            order.save()
                            return HttpResponse(json.dumps({'status': 1, 'message': '支付成功', 'res': res}))
                        else:
                            order.status = 0  # 支付失败(未支付)
                            order.save()
                            return HttpResponse(json.dumps({'status': 2, 'message': '支付失败', 'res': res}))
                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
            elif req.get('orderId') and flag == 3:  # 用户确认收货
                try:
                    with transaction.atomic():
                        order = Order.objects.get(id=req.get('orderId'))
                        order.status = 3
                        order.save()
                        if order.orderType == 0:  # 是普通订单
                            user = User.objects.get(id=order.user_id)
                            # 该用户是否是某代理的粉丝
                            if user.agentId != 0:
                                # 代理人信息
                                agent = Agent.objects.get(id=user.agentId)
                                if agent.status == 1:  # 正在代理
                                    distribution = Distribution.objects.filter()
                                    if distribution:  # 商家设置了分销
                                        distribution = distribution[0]
                                        even = ''
                                        if user.fansLevel == 1:  # 是一级粉丝
                                            # 计算分销利益
                                            profit = decimal.Decimal((distribution.firstProfit * order.realTotal) / 100)
                                            if profit > distribution.firstLimit:
                                                profit = distribution.firstLimit
                                            even = '一级粉丝购买商品'
                                        elif user.fansLevel == 1:  # 是二级粉丝
                                            # 计算分销利益
                                            profit = decimal.Decimal(
                                                (distribution.secondProfit * order.realTotal) / 100)
                                            if profit > distribution.secondLimit:
                                                profit = distribution.secondLimit
                                            even = '二级粉丝购买商品'
                                        else:
                                            profit = decimal.Decimal('0.00')
                                        if profit != 0:  # 分销利益不为0,创建记录同时相加
                                            AgentProfitRecord.objects.create(agent_id=agent.id, even=even, value=profit)
                                            agent.total += profit
                                            agent.residue += profit
                                            agent.save()
                                            # 日数据
                                            # 更新当日的代理收益数据
                                            agentCountDay = AgentCountDay.objects.filter(agent_id=agent.id,
                                                                                         day=datetime.datetime.now().date())
                                            if agentCountDay:  # 存在
                                                agentCountDay = agentCountDay[0]
                                            else:
                                                agentCountDay = AgentCountDay.objects.create(agent_id=agent.id,
                                                                                             day=datetime.datetime.now().date())
                                            agentCountDay.total += profit
                                            agentCountDay.save()

                        return HttpResponse(json.dumps({'status': 1, 'message': '成功'}))
                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': req}))


# 主页轮播图
@csrf_exempt
def carousel(request):
    if request.method == 'GET':
        carousels = Carousel.objects.filter().values('url')
        return HttpResponse(json.dumps({'status': 1, 'carousels': list(carousels)}))
    elif request.method == 'PUT':
        try:
            with transaction.atomic():
                carousels = Carousel.objects.all()
                for c in carousels:
                    c.delete()
                req = json.loads(request.body.decode('utf-8'))
                pics = req.get('carousels')
                for p in pics:
                    Carousel.objects.create(url=p)
                return HttpResponse(json.dumps({'status': 1, 'success': '修改成功'}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 拼团
@csrf_exempt
def collage(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:
            if request.session.get('admin', False):
                if request.GET.get('collageId'):
                    collage = Collage.objects.get(id=request.GET.get('collageId'))
                    collageSku = list(
                        CollageSku.objects.filter(collage_id=collage.id).values('id', 'sku_id', 'sku__skuName',
                                                                                'sku__originPrice'
                                                                                , 'sku__sellPrice', 'product_id',
                                                                                'product__productName',
                                                                                'collagePrice', 'collageNum', ))
                    collage = model_to_dict(collage)
                    collage.setdefault('product', collageSku)
                    return HttpResponse(json.dumps({'status': 1, 'collage': collage}, cls=CJsonEncoder))
                elif request.GET.get('offset') and request.GET.get('limit'):
                    limit = int(request.GET.get('limit'))
                    offset = int(request.GET.get('offset'))
                    collages = list(Collage.objects.filter().values()[offset:offset + limit])
                    for c in collages:
                        c.setdefault('collageProductNum', CollageSku.objects.filter(collage_id=c.get('id')).count())
                    return HttpResponse(json.dumps({'status': 1, 'collages': collages}, cls=CJsonEncoder))
                else:
                    return HttpResponse(json.dumps({'status': 1, 'count': Collage.objects.all().count()}))
            return HttpResponse(json.dumps({'status': 0, 'message': '登录过期'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if req.get('collageId'):  # 是修改
            collage = Collage.objects.get(id=req.get('collageId'))
            if req.get('date'):
                collage.startTime = datetime.datetime.strptime(req.get('date')[0], '%Y-%m-%d')
                collage.endTime = datetime.datetime.strptime(req.get('date')[1], '%Y-%m-%d')
            if req.get('collageHour'):
                collage.effectiveTime = int(req.get('collageHour'))
            if req.get('collagePeople'):
                collage.collagePeople = req.get('collagePeople')
            if req.get('collageLimit'):
                collage.collageLimit = req.get('collageLimit')
            if req.get('status'):
                collage.status = req.get('status')
            collage.save()
            # res = {'status', 'collageId':collage.id}
        elif req.get('collageId') and req.get('status'):
            collage = Collage.objects.get(id=req.get('collageId'))
            collage.status = int(req.get('status'))
            collage.save()
        else:
            collage = Collage.objects.create(startTime=datetime.datetime.strptime(req.get('date')[0], '%Y-%m-%d %H-%M'),
                                             endTime=datetime.datetime.strptime(req.get('date')[1], '%Y-%m-%d %H-%M'),
                                             effectiveTime=req.get('collageHour'),
                                             collagePeople=req.get('collagePeople'),
                                             collageLimit=req.get('collageLimit'))
        res = {'status': 1, 'collageId': collage.id}
        return HttpResponse(json.dumps(res))
    elif request.method == 'DELETE':
        print(request.body.decode('utf-8'))
        req = json.loads(request.body.decode('utf-8'))
        collage = Collage.objects.get(id=req.get('collageId'))
        if collage.status == 0:
            collageSku = CollageSku.objects.filter(collage_id=req.get('collageId'))
            try:
                for cs in collageSku:
                    cs.delete()
                collage.delete()
                res = {'status': 1}
            except Exception as e:
                res = {'status': 0, 'message': str(e)}
        else:
            res = {'status': 0, 'message': '无法删除'}
        return HttpResponse(json.dumps(res))


# 根据商品名搜索商品的id 和商品名
@csrf_exempt
def searchId(request):
    if request.method == 'GET':
        searchKey = request.GET.get('searchKey')
        if searchKey:
            products = list(Product.objects.filter(productName__contains=searchKey).values('id', 'productName'))[0:10]
            productIds = []
            for p in products:
                productIds.append({'value': p.get('id'), 'label': p.get('productName')})
            return HttpResponse(json.dumps({'status': 1, 'productIds': productIds}))
        else:
            return HttpResponse(json.dumps({'status': 1, 'productIds': []}))


# 返回商品的sku
@csrf_exempt
def sku(request):
    if request.method == 'GET':
        select = request.GET.get('select')
        if select:
            productSku = SKU.objects.filter(product_id=select)
            skus = []
            for ps in productSku:
                skus.append({
                    'value': ps.id,
                    'label': ps.skuName,
                    'originPrice': ps.originPrice,
                    'sellPrice': ps.sellPrice,
                })
            return HttpResponse(json.dumps({'status': 1, 'skus': skus}, cls=CJsonEncoder))
        else:
            return HttpResponse(json.dumps({'status': 1, 'skus': []}))


# 添加拼团商品
@csrf_exempt
def collage_product(request):
    if request.method == 'GET':
        if request.GET.get('collageSkuId'):  # 加载参团团长
            collageSku = CollageSku.objects.get(id=request.GET.get('collageSkuId'))
            collage = Collage.objects.get(id=collageSku.collage_id)
            guoqitime = datetime.datetime.now() - datetime.timedelta(hours=collage.effectiveTime)
            page = int(request.GET.get('page', 0))
            # 查找未过期团长
            collageUser = list(
                CollageUser.objects.filter(collageSku_id=collageSku.id, attendTime__gt=guoqitime, status=1,
                                           isCollage=True).values('user__nickName', 'user__avatarUrl', 'collageSku_id',
                                                                  'id'))
            return HttpResponse(json.dumps({'status': 1, 'collageUser': collageUser}))
        if request.GET.get('id'):  # 加载某一个单品的数据
            collageSku = CollageSku.objects.get(id=request.GET.get('id'))
            collage = model_to_dict(Collage.objects.get(id=collageSku.collage_id))
            product = model_to_dict(Product.objects.get(id=collageSku.product_id))
            productFormat = list(ProductFormat.objects.filter(product_id=collageSku.product_id).values())
            pics = list(Picture.objects.filter(product_id=collageSku.product_id).values())

            sku = model_to_dict(SKU.objects.get(id=collageSku.sku_id))
            product.setdefault('collageSku', model_to_dict(collageSku))
            product.setdefault('carousel', pics)
            product.setdefault('collageUser', )
            product.setdefault('sku', sku)
            product.setdefault('collage', collage)
            product.setdefault('format', productFormat)
            return HttpResponse(json.dumps({'status': 1, 'product': product}, cls=CJsonEncoder))
        page = int(request.GET.get('page', 0))
        # 加载拼团 过期的不要加载
        collage = list(
            Collage.objects.filter(status=1, endTime__gt=datetime.datetime.now()).order_by('startTime').values()[
            page * 10:(page + 1) * 10])
        for c in collage:
            collageSku = list(CollageSku.objects.filter(collage_id=c.get('id')).values('id', 'product_id', 'sku_id',
                                                                                       'product__productName',
                                                                                       'product__imgUrl',
                                                                                       'collagePrice', 'sku__sellPrice',
                                                                                       'sku__skuName',
                                                                                       'residualNum', ))
            c.setdefault('collageSku', collageSku)
        return HttpResponse(json.dumps({'status': 1, 'collage': collage}, cls=CJsonEncoder))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if req.get('id'):  # 是修改
            collageSku = CollageSku.objects.get(id=req.get('id'))
            if req.get('productId'):
                collageSku.product_id = req.get('productId')
            if req.get('skuId'):
                collageSku.sku_id = req.get('skuId')
            if req.get('collagePrice'):
                collageSku.collagePrice = decimal.Decimal(req.get('collagePrice'))
            if req.get('collageNum'):
                collageSku.collageNum = req.get('collageNum')
            collageSku.save()
        else:
            collageSku = CollageSku.objects.create(product_id=req.get('productId'),
                                                   sku_id=req.get('skuId'),
                                                   collagePrice=req.get('collagePrice'),
                                                   collageNum=req.get('collageNum'),
                                                   collage_id=req.get('collageId'),
                                                   residualNum=req.get('collageNum'))
        return HttpResponse(json.dumps({'status': 1, 'collageSkuId': collageSku.id}))


# 拼团订单
@csrf_exempt
def collage_order(request):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':  # 创建拼图订单
        req = json.loads(request.body.decode('utf-8'))
        flag = int(req.get('flag', 0))
        if flag == 0:  # 创建团长
            try:
                with transaction.atomic():
                    collageSku = CollageSku.objects.get(id=req.get('collageSkuId'))
                    if collageSku.residualNum > 0:  # 数量充足
                        collage = Collage.objects.get(id=collageSku.collage_id)
                        if collage.endTime > datetime.datetime.now():  # 时间够
                            # 判断对于该平团sku,是否存在未超过拼团有效时间小时并被退款了的订单
                            guoqitime = datetime.datetime.now() - datetime.timedelta(hours=collage.effectiveTime)
                            collageUser = CollageUser.objects.filter(user_id=req.get('userId'),
                                                                     collageSku_id=req.get('collageSkuId'),
                                                                     attendTime__gt=guoqitime, status=1)
                            if not collageUser:  # 不存在未完成拼团，可以发起拼团
                                # 预先减库存
                                collageSku.residualNum -= 1
                                collageSku.save()
                                # 1.创建拼团用户
                                collager = CollageUser.objects.create(product_id=collageSku.product_id,
                                                                      collageSku_id=req.get('collageSkuId'),
                                                                      user_id=req.get('userId'),
                                                                      isCollage=True,
                                                                      attendTime=datetime.datetime.now(),
                                                                      price=collageSku.collagePrice,
                                                                      collageNo=WxPay.random_num(10))

                                # 2.生成订单
                                # orders = Order.objects.filter(status=9,user_id=)
                                order = Order.objects.create(
                                    user_id=req.get('userId'),
                                    total=collageSku.collagePrice,
                                    realTotal=collageSku.collagePrice,
                                    createTime=datetime.datetime.now(),
                                    out_trade_no=str(int(datetime.datetime.now().timestamp())) + str(
                                        WxPay.random_num(8)),
                                    order_code=str(int(datetime.datetime.now().timestamp())) + str(
                                        WxPay.random_num(3)),
                                    status=9,
                                    orderType=1,
                                    collagerId=collager.id,
                                    province=req.get('province'),
                                    city=req.get('city'),
                                    area=req.get('area'),
                                    address=req.get('address'),
                                    name=req.get('name'),
                                    phoneNum=req.get('phoneNum'),
                                )
                                # 3.生成orderSku
                                sku = SKU.objects.get(id=collageSku.sku_id)
                                product = Product.objects.get(id=sku.product_id)
                                OrderSku.objects.create(
                                    sku_id=sku.id,
                                    skuPrice=collageSku.collagePrice,
                                    skuNum=1,
                                    skuName=sku.skuName,
                                    productName=product.productName,
                                    imgUrl=product.imgUrl,
                                    order_id=order.id
                                )
                                # 4.发起预支付
                                user = User.objects.get(id=req.get('userId'))
                                data = {
                                    'body': '商品-订单',  # 商品描述
                                    'out_trade_no': order.out_trade_no,  # 商户订单号
                                    'total_fee': int(order.realTotal * 100),
                                    'spbill_create_ip': c_sp_bill_create_ip,
                                    # 'notify_url': c_notify_url,
                                    'trade_type': c_trade_type,
                                    'openid': user.openId, }
                                wx_pay = WxPay(c_notify_url)
                                res = wx_pay.unified_order(data)
                                # 把购物车清空
                                order.prePayTime = datetime.datetime.now()
                                if res.get("prepay_id"):
                                    order.prepay_id = res["prepay_id"]
                                    order.status = 10  # 预支付成功
                                    order.save()
                                    res = {'status': 1, 'message': '支付成功', 'res': res}
                                else:
                                    # order.status = 0  # 支付失败(未支付)
                                    # order.save()
                                    raise Exception('预支付失败')
                                    res = {'status': 3, 'message': '支付失败', 'res': res}
                            else:  # 存在当前未完成的拼团
                                res = {'status': 2, 'message': '存在未完成拼团'}
                        else:
                            res = {'status': 2, 'message': '活动已过期'}
                    else:
                        res = {'status': 2, 'message': '拼团数量不足'}
            except Exception as e:
                res = {'status': 0, 'message': str(e)}
            return HttpResponse(json.dumps(res))
        elif flag == 1:  # 创建团员
            collageSku = CollageSku.objects.get(id=req.get('collageSkuId'))
            # 该团是不是本人发起的？

            if CollageUser.objects.filter(id=req.get('collagerId'), user_id=req.get('userId')).exists():
                res = {'status': 2, 'message': '你不能参加自己的团'}
            else:
                # 判断是否还能参团
                if collageSku.residualNum > 0:  # 数量充足
                    collage = Collage.objects.get(id=collageSku.collage_id)
                    # 判断对于该平团sku,是否存在未超过拼团有效时间小时并被退款了的订单
                    guoqitime = datetime.datetime.now() - datetime.timedelta(hours=collage.effectiveTime)
                    collageUser = CollageUser.objects.filter(id=req.get('collagerId'),
                                                             attendTime__gt=guoqitime, status=1)  # 团长
                    if collageUser:  # 团长发起的团未过期
                        collageUser = collageUser[0]
                        # 查找已经跟随团长的团员人数
                        collageUserNum = CollageUser.objects.filter(collagerId=collageUser.id).count()
                        if collageUserNum < collage.collagePeople - 1:
                            # 可以参团
                            # 不需要进行减库存，只有拼团成功才减
                            # 1.创建拼团用户
                            CollageUser.objects.create(product_id=collageSku.product_id,
                                                       collageSku_id=req.get('collageSkuId'),
                                                       user_id=req.get('userId'),
                                                       isCollage=True,
                                                       attendTime=datetime.datetime.now(),
                                                       price=collageSku.collagePrice,
                                                       collageNo=WxPay.random_num(10),
                                                       collagerId=collageUser.id)
                            # 2.生成订单
                            order = Order.objects.create(
                                user_id=req.get('userId'),
                                total=collageSku.collagePrice,
                                realTotal=collageSku.collagePrice,
                                createTime=datetime.datetime.now(),
                                out_trade_no=str(int(datetime.datetime.now().timestamp())) + str(
                                    WxPay.random_num(8)),
                                order_code=str(int(datetime.datetime.now().timestamp())) + str(
                                    WxPay.random_num(3)),
                                status=9,
                                orderType=1,
                                collagerId=collageUser.id,
                                province=req.get('province'),
                                city=req.get('city'),
                                area=req.get('area'),
                                address=req.get('address'),
                                name=req.get('name'),
                                phoneNum=req.get('phoneNum'),
                            )
                            # 3.生成orderSku
                            sku = SKU.objects.get(id=collageSku.sku_id)
                            product = Product.objects.get(id=sku.product_id)
                            OrderSku.objects.create(
                                sku_id=sku.id,
                                skuPrice=collageSku.collagePrice,
                                skuNum=1,
                                skuName=sku.skuName,
                                productName=product.productName,
                                imgUrl=product.imgUrl,
                                order_id=order.id,
                            )
                            # 4.发起预支付
                            user = User.objects.get(id=req.get('userId'))
                            data = {
                                'body': '商品-订单',  # 商品描述
                                'out_trade_no': order.out_trade_no,  # 商户订单号
                                'total_fee': int(order.realTotal * 100),
                                'spbill_create_ip': c_sp_bill_create_ip,
                                # 'notify_url': c_notify_url,
                                'trade_type': c_trade_type,
                                'openid': user.openId, }
                            wx_pay = WxPay(c_notify_url)
                            res = wx_pay.unified_order(data)
                            # 把购物车清空
                            order.prePayTime = datetime.datetime.now()
                            if res.get("prepay_id"):
                                order.prepay_id = res["prepay_id"]
                                order.status = 10  # 预支付成功
                                order.save()
                                res = {'status': 1, 'message': '支付成功', 'res': res}
                            else:
                                raise Exception('预支付失败')
                                # order.status = 0  # 支付失败(未支付)
                                # order.save()
                                # res = {'status': 3, 'message': '支付失败', 'res': res}
                        else:
                            res = {'status': 1, 'message': '人数已满'}
                    else:  # 存在当前未完成的拼团
                        res = {'status': 2, 'message': '存在未完成拼团'}
                else:
                    res = {'status': 2, 'message': '拼团数量不足'}

            return HttpResponse(json.dumps(res))


# 返回建议的地址
@csrf_exempt
def address_suggest(request):
    if request.method == 'GET':
        if request.GET.get('searchKey'):
            # 访问腾讯api
            url = 'https://apis.map.qq.com/ws/place/v1/suggestion/?keyword=' + request.GET.get(
                'searchKey') + '&key=DG2BZ-7XEKK-V5WJ7-AF5Z4-YQNL5-MYFLU'
            res = requests.get(url=url)
            return HttpResponse(res.content)


# 购物车
@csrf_exempt
def cart(request):
    if request.method == 'GET':
        page = int(request.GET.get('page', 0))
        cartSkus = list(CartSku.objects.filter(user_id=request.GET.get('userId')).values('id',
                                                                                         'user_id',
                                                                                         'sku_id',
                                                                                         'sku__skuName',
                                                                                         'sku__sellPrice',
                                                                                         'sku__originPrice',
                                                                                         'sku__product__imgUrl',
                                                                                         'sku__product__productName',
                                                                                         'skuNum')[
                        page * 10:(page + 1) * 10])
        return HttpResponse(json.dumps({'status': 1, 'cart': cartSkus}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        cartSku = CartSku.objects.filter(sku_id=req.get('skuId'), user_id=req.get('userId'))
        if cartSku:
            return HttpResponse(json.dumps({'status': 2, 'message': '商品已存在购物车'}))
        else:
            CartSku.objects.create(sku_id=req.get('skuId'), skuNum=int(req.get('skuNum', 1)), user_id=req.get('userId'))
            return HttpResponse(json.dumps({'status': 1, 'message': '添加成功'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        cartSku = CartSku.objects.get(id=req.get('cartSkuId'))
        if req.get('skuNum'):
            cartSku.skuNum = req.get('skuNum')
        cartSku.save()
        return HttpResponse(json.dumps({'status': 1, 'message': '更改成功'}))
    elif request.method == 'DELETE':
        req = json.loads(request.body.decode('utf-8'))
        cartSku = CartSku.objects.get(id=req.get('skuId'))
        cartSku.delete()
        return HttpResponse(json.dumps({'status': 1, 'message': '删除成功'}))


# 用户添加地址
@csrf_exempt
def address(request):
    if request.method == 'GET':
        if request.GET.get('addressId'):
            return HttpResponse(json.dumps(
                {'status': 1, 'address': model_to_dict(UserAddress.objects.get(id=request.GET.get('addressId')))}))
        elif request.GET.get('isNormal'):
            userAddress = list(UserAddress.objects.filter(user_id=request.GET.get('userId'), isNormal=True).values())
            if userAddress:
                return HttpResponse(json.dumps(
                    {'status': 1, 'address': userAddress[0]}))
            else:
                return HttpResponse(json.dumps(
                    {'status': 2, 'address': {}}))

        page = int(request.GET.get('page', 0))
        userAddress = list(UserAddress.objects.filter(user_id=request.GET.get('userId')).values())
        return HttpResponse(json.dumps({'status': 1, 'addressList': userAddress}))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        addressId = int(req.get('addressId', 0))
        if addressId == 0:
            UserAddress.objects.create(user_id=req.get('userId'),
                                       name=req.get('name'),
                                       province=req.get('province'),
                                       city=req.get('city'),
                                       area=req.get('area'),
                                       address=req.get('address'),
                                       phoneNum=req.get('phoneNum'),
                                       )
        else:
            userAddress = UserAddress.objects.get(id=addressId)
            if req.get('name'):
                userAddress.name = req.get('name')
            if req.get('province'):
                userAddress.province = req.get('province')
            if req.get('city'):
                userAddress.city = req.get('city')
            if req.get('area'):
                userAddress.area = req.get('area')
            if req.get('address'):
                userAddress.address = req.get('address')
            if req.get('phoneNum'):
                userAddress.phoneNum = req.get('phoneNum')
            userAddress.save()
        return HttpResponse(json.dumps({'status': 1, 'message': '保存成功'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        try:
            with transaction.atomic():
                userAddress = UserAddress.objects.get(id=req.get('addressId'))
                if req.get('isNormal'):
                    userAddresses = UserAddress.objects.filter(user_id=req.get('userId'), isNormal=True)
                    for us in userAddresses:
                        us.isNormal = False
                        us.save()
                    userAddress.isNormal = True
                    userAddress.save()
                else:
                    userAddress.isNormal = False
                    userAddress.save()
                return HttpResponse(json.dumps({'status': 1, 'message': '修改成功'}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
    elif request.method == 'DELETE':
        req = json.loads(request.body.decode('utf-8'))
        userAddress = UserAddress.objects.get(id=req.get('addressId'))
        userAddress.delete()
        return HttpResponse(json.dumps({'status': 1, 'message': '删除成功'}));


# 加载会员信息
@csrf_exempt
def member(request):
    if request.method == 'GET':
        req = request.GET
        if int(req.get('type', 0)) == 1:
            if req.get('offset') and req.get('limit'):
                offset = int(req.get('offset'))
                limit = int(req.get('limit'))
                member = list(MemberDiscount.objects.filter().values()[offset:offset + limit])
                return HttpResponse(json.dumps({'status': 1, 'members': member}, cls=CJsonEncoder))
            else:
                return HttpResponse(json.dumps({'status': 1, 'count': MemberDiscount.objects.all().count()}))
        else:
            userId = request.GET.get('userId')
            if userId:
                user = User.objects.get(id=userId)
                memberDiscount = MemberDiscount.objects.filter(score__lte=user.score).order_by('-score')
                isSign = SignDay.objects.filter(user_id=userId, date=datetime.datetime.today()).exists()
                if memberDiscount:
                    memberDiscount = memberDiscount[0]
                    return HttpResponse(json.dumps(
                        {'status': 1, 'member': model_to_dict(memberDiscount), 'score': user.score, 'isSign': isSign},
                        cls=CJsonEncoder))
                else:
                    return HttpResponse(json.dumps({'status': 2, 'message': '没有会员信息'}))
            else:
                member = list(MemberDiscount.objects.filter().all().values().order_by('score'))
                return HttpResponse(json.dumps({'status': 1, 'members': member}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        if req.get('memberId'):  # 是修改
            member = MemberDiscount.objects.get(id=req.get('memberId'))
            if req.get('level'):
                member.level = req.get('level')
            if req.get('memberName'):
                member.memberName = req.get('memberName')
            if req.get('score'):
                member.score = req.get('score')
            if req.get('discount'):
                member.discount = req.get('discount')
            member.save()
            return HttpResponse(json.dumps({'status': 1}))
        else:
            MemberDiscount.objects.create(level=req.get('level'), memberName=req.get('memberName'),
                                          score=req.get('score'),
                                          discount=decimal.Decimal(req.get('discount')))
            return HttpResponse(json.dumps({'status': 1, 'message': '成功'}))


# 订单评论-获得积分 用户折扣
@csrf_exempt
def order_comment(request):
    if request.method == 'GET':
        req = request.GET
        if int(req.get('type', 0)) == 1:
            pass
        else:
            flag = int(req.get('flag', 0))
            page = int(req.get('page', 0))
            comment = []
            if flag == 0:  # 加载好评
                comment = list(
                    Comment.objects.filter(rate=5, sku__product_id=req.get('productId')).values('user__nickName',
                                                                                                'isAnonymous',
                                                                                                'content',
                                                                                                'createTime',
                                                                                                'rate',
                                                                                                'id')[
                    page * 10:(page + 1) * 10])
                for c in comment:
                    commentImage = list(CommentImage.objects.filter(comment_id=c.get('id')).values())
                    c.setdefault('commentImages', commentImage)

            elif flag == 1:  # 加载中评
                comment = list(Comment.objects.filter(rate__range=[3, 4], sku__product_id=req.get('productId')).values(
                    'user__nickName',
                    'isAnonymous',
                    'content',
                    'createTime',
                    'rate',
                    'id')[
                               page * 10:(page + 1) * 10])
                for c in comment:
                    commentImage = list(CommentImage.objects.filter(comment_id=c.get('id')).values())
                    c.setdefault('commentImages', commentImage)
            elif flag == 2:  # 加载差评
                comment = list(Comment.objects.filter(rate__range=[1, 2], sku__product_id=req.get('productId')).values(
                    'user__nickName',
                    'isAnonymous',
                    'content',
                    'createTime',
                    'rate',
                    'id')[
                               page * 10:(page + 1) * 10])
                for c in comment:
                    commentImage = list(CommentImage.objects.filter(comment_id=c.get('id')).values())
                    c.setdefault('commentImages', commentImage)
            elif flag == 3:  # 加载全部
                comment = list(Comment.objects.filter(sku__product_id=req.get('productId')).values('user__nickName',
                                                                                                   'isAnonymous',
                                                                                                   'content',
                                                                                                   'createTime',
                                                                                                   'rate',
                                                                                                   'id')[
                               page * 10:(page + 1) * 10])
                for c in comment:
                    commentImage = list(CommentImage.objects.filter(comment_id=c.get('id')).values())
                    c.setdefault('commentImages', commentImage)
            return HttpResponse(json.dumps({'status': 1, 'comments': list(comment)}, cls=CJsonEncoder))
        pass
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        try:
            with transaction.atomic():
                for resc in req.get('comments'):
                    comment = Comment.objects.create(order_id=req.get('orderId'), user_id=req.get('userId'),
                                                     sku_id=resc.get('skuId'),
                                                     isAnonymous=resc.get('isCheck'), content=resc.get('content', ''),
                                                     rate=resc.get('rate'))
                    sku = SKU.objects.get(id=resc.get('skuId'))
                    sku.commentNum += 1
                    sku.rate += int(resc.get('rate'))
                    sku.save()
                    for ci in resc.get('imgUrl'):
                        CommentImage.objects.create(imgUrl=ci, comment_id=comment.id)
                # 订单状态
                order = Order.objects.get(id=req.get('orderId'))
                order.status = 4
                order.save()
                # 加积分-默认一元一积分 默认10积分
                user = User.objects.get(id=req.get('userId'))
                user.score += 10
                user.save()
                return HttpResponse(json.dumps({'status': 1, 'message': '评价成功', 'score': 10}))
        except Exception as e:
            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 签到
@csrf_exempt
def sign_day(request):
    if request.method == 'GET':
        userId = request.GET.get('userId')
        page = int(request.GET.get('page'))
        sr = list(ScoreRecord.objects.filter(user_id=userId).values())
        return HttpResponse(json.dumps({'status': 1, 'list': sr}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        signDay = SignDay.objects.filter(user_id=req.get('userId'), date=datetime.datetime.today())
        if signDay:
            return HttpResponse(json.dumps({'status': 2, 'message': '今天已经签到了'}))
        else:
            try:
                with transaction.atomic():
                    SignDay.objects.create(user_id=req.get('userId'), date=datetime.datetime.today())
                    ScoreRecord.objects.create(user_id=req.get('userId'), value=5, even='签到')
                    user = User.objects.get(id=req.get('userId'))
                    user.score += 5
                    user.save()
                    return HttpResponse(json.dumps({'status': 1, 'message': '签到成功'}))
            except Exception as e:
                return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 处理代理信息
@csrf_exempt
def agent(request):
    if request.method == 'GET':
        if int(request.GET.get('type', 0)) == 1:  # 是网页端
            if request.GET.get('count'):
                count = int(request.GET.get('count'))
                applyCount = 0
                if count == 0:  # 加载新的申请的数目
                    applyCount = AgentApply.objects.filter(status=0).count()
                elif count == 1:  # 加载所有申请的数目
                    applyCount = AgentApply.objects.all().count()
                elif count == 2:  # 加载申请人的数目
                    applyCount = Agent.objects.all().count()
                elif count == 3:  # 加载新申请的数目
                    applyCount = CashApply.objects.filter(status=0).count()
                elif count == 4:  # 加载所有提现申请的数目
                    applyCount = CashApply.objects.all().count()
                return HttpResponse(json.dumps({'status': 1, 'count': applyCount}))
            else:
                offset = int(request.GET.get('offset'))
                limit = int(request.GET.get('limit'))
                index = int(request.GET.get('index', 0))
                applys = []
                if index == 0:  # 加载新申请
                    applys = list(
                        AgentApply.objects.filter(status=0).values().order_by('-createTime')[offset:offset + limit])
                elif index == 1:  # 加载所有申请
                    applys = list(AgentApply.objects.all().values().order_by('-createTime')[offset:offset + limit])
                elif index == 2:
                    applys = list(Agent.objects.all().values().order_by('-createTime'))
                elif index == 3:  # 加载新提现申请
                    applys = list(CashApply.objects.filter(status=0).order_by('-applyTime').values('agent__avatarUrl',
                                                                                                   'applyTime', 'name',
                                                                                                   'phoneNum',
                                                                                                   'wxCode',
                                                                                                   'cash', 'status',
                                                                                                   'id', 'agent_id')[
                                  offset:offset + limit])

                elif index == 4:  # 加载所有提现申请
                    applys = list(CashApply.objects.all().order_by('-applyTime').values('agent__avatarUrl',
                                                                                        'applyTime', 'name',
                                                                                        'phoneNum',
                                                                                        'wxCode',
                                                                                        'cash', 'status',
                                                                                        'id', 'agent_id')[
                                  offset:offset + limit])
                return HttpResponse(json.dumps({'status': 1, 'applys': applys}, cls=CJsonEncoder))
        userId = request.GET.get('userId')
        agentId = request.GET.get('agentId')
        page = int(request.GET.get('page', 0))
        fans = request.GET.get('fans')
        if agentId:  # 加载该代理的月新增信息
            flag = int(request.GET.get('flag', 0))
            today = datetime.datetime.today().date()
            aprs = []
            if flag == 1:  # 加载月收益
                acm = list(AgentCountDay.objects.filter(agent_id=agentId, day__month=today.month).values())
                return HttpResponse(
                    json.dumps({'status': 1, 'agentCount': acm}, cls=CJsonEncoder))
            elif flag == 0:  # 加载日收益
                acd = AgentCountDay.objects.filter(agent_id=agentId, day=today)
                if acd:
                    acd = acd[0]
                else:
                    acd = AgentCountDay.objects.create(agent_id=agentId, day=today, total=0.00)
                return HttpResponse(
                    json.dumps({'status': 1, 'agentCount': model_to_dict(acd)}, cls=CJsonEncoder))
            elif flag == 2:  # 加载全部收益
                agent = Agent.objects.get(id=agentId)
                return HttpResponse(
                    json.dumps({'status': 1, 'agentCount': {'total': agent.total, 'firstFans': agent.firstFans,
                                                            'secondFans': agent.secondFans}}, cls=CJsonEncoder))
            elif flag == 3:  # 加载日收益明细
                print(datetime.datetime.now())
                aprs = list(AgentProfitRecord.objects.filter(agent_id=agentId, createTime__gte=today).order_by(
                    '-createTime').values()[page * 20:(page + 1) * 20])
            elif flag == 4:  # 加载月收益明细
                aprs = list(AgentProfitRecord.objects.filter(agent_id=agentId, createTime__month=today.month,
                                                             createTime__year=today.year).order_by(
                    '-createTime').values()[page * 20:(page + 1) * 20])
            elif flag == 5:  # 加载全部收益明细
                aprs = list(AgentProfitRecord.objects.filter(agent_id=agentId).order_by(
                    '-createTime').values()[page * 20:(page + 1) * 20])
            elif flag == 6:  # 加载提现记录
                aprs = list(
                    CashApply.objects.filter(agent_id=agentId).order_by('applyTime').values()[
                    page * 20:(page + 1) * 20])
            return HttpResponse(json.dumps({'status': 1, 'agentProfitRecord': aprs}, cls=CJsonEncoder))
        if fans:
            fans = int(fans)
            agent = Agent.objects.get(user_id=userId)
            if fans == 0:  # 一级粉丝数
                # agent = Agent.objects.get(userId=userId)
                return HttpResponse(json.dumps({'status': 1, 'fansCount': agent.firstFans}))
            elif fans == 1:  # 二级粉丝数
                # agent = Agent.objects.get(userId=userId)
                return HttpResponse(json.dumps({'status': 1, 'fansCount': agent.secondFans}))
            elif fans == 2:  # 一级粉丝详情
                user = list(User.objects.filter(agentId=agent.id, fansLevel=1).values('avatarUrl', 'createTime',
                                                                                      'gender').order_by('-createTime')[
                            page * 20:(page + 1) * 20])
                return HttpResponse(json.dumps({'status': 1, 'fans': user}, cls=CJsonEncoder))
            elif fans == 3:  # 二级粉丝详情
                user = list(User.objects.filter(agentId=agent.id, fansLevel=2).values('avatarUrl', 'createTime',
                                                                                      'gender').order_by('-createTime')[
                            page * 20:(page + 1) * 20])
                return HttpResponse(json.dumps({'status': 1, 'fans': user}, cls=CJsonEncoder))
        agent = Agent.objects.filter(user_id=userId)
        agentApply = AgentApply.objects.filter(user_id=userId)
        if agent:
            agent = agent[0]
            user = User.objects.get(id=userId)
            return HttpResponse(json.dumps(
                {'status': 1, 'agent': model_to_dict(agent), 'isAgent': True, 'isApply': True, 'applyStatus': 1,
                 'score': user.score}, cls=CJsonEncoder, ))
        else:
            if agentApply:
                return HttpResponse(
                    json.dumps({'status': 1, 'isAgent': False, 'isApply': True, 'applyStatus': agentApply[0].status}))
            else:
                return HttpResponse(json.dumps({'status': 1, 'isAgent': False, 'isApply': False, 'applyStatus': 0}))
    elif request.method == 'POST':  # 成为代理
        req = json.loads(request.body.decode('utf-8'))
        if req.get('cash'):  # 代理提现
            # 查看是否存在上次未处理申请
            cashApply = CashApply.objects.filter(agent_id=req.get('agentId'), status=0)
            if cashApply:
                return HttpResponse(json.dumps({'status': 2, 'message': '上次申请未处理'}))
            else:
                wx_pay = WxPay()
                CashApply.objects.create(agent_id=req.get('agentId'), status=0, name=req.get('name'),
                                         phoneNum=req.get('phoneNum'), wxCode=req.get('wxCode'),
                                         cash=decimal.Decimal(req.get('cash')),
                                         partner_trade_no=u'{0}{1}{2}'.format(wx_pay.WX_MCH_ID,
                                                                              time.strftime('%Y%m%d', time.localtime(
                                                                                  time.time())),
                                                                              wx_pay.random_num(10)))

                return HttpResponse(json.dumps({'status': 1, 'message': '申请成功'}))
        agentApply = AgentApply.objects.filter(user_id=req.get('userId'))
        if agentApply:
            return HttpResponse(json.dumps({'status': 1, 'message': '已经提交了申请'}))
        else:
            user = User.objects.get(id=req.get('userId'))
            AgentApply.objects.create(user_id=req.get('userId'),
                                      city=req.get('city'),
                                      province=req.get('province'),
                                      gender=req.get('gender'),
                                      phoneNum=req.get('phoneNum'),
                                      realName=req.get('name'),
                                      avatarUrl=user.avatarUrl)
            return HttpResponse(json.dumps({'status': 1, 'message': '提交成功'}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:
            if req.get('applyId'):  # 审核代理
                try:
                    with transaction.atomic():
                        apply = AgentApply.objects.get(id=req.get('applyId'))
                        apply.status = req.get('status')
                        apply.save()
                        if apply.status == 1:
                            agent = Agent.objects.filter(user_id=apply.user_id)
                            if not agent:
                                Agent.objects.create(user_id=apply.user_id, status=1, avatarUrl=apply.avatarUrl,
                                                     realName=apply.realName,
                                                     phoneNum=apply.phoneNum)
                        return HttpResponse(json.dumps({'status': 1, 'message': '操作成功'}))
                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
            elif req.get('agentId'):
                agent = Agent.objects.get(id=req.get('agentId'))
                agent.status = req.get('status')
                agent.save()
                return HttpResponse(json.dumps({'status': 1, 'message': '修改成功'}))
            elif req.get('cashId'):  # 审核提现申请
                try:
                    with transaction.atomic():
                        cashApply = CashApply.objects.get(id=req.get('cashId'))
                        cashApply.status = req.get('status')
                        cashApply.save()
                        agent = Agent.objects.get(id=cashApply.agent_id)
                        user = User.objects.get(id=agent.user_id)
                        # user = User.objects.filter(agent__cashapply__id=cashApply.id)
                        if cashApply.status == 1:  # 允许，进行企业付款
                            wx_pay = WxPay(c_notify_url)
                            data = {
                                'check_name': 'FORCE_CHECK',
                                'openid': user.openId,
                                'amount': int(cashApply.cash * 100),
                                're_user_name': cashApply.name,
                                'desc': '提现',
                                'spbill_create_ip': c_sp_bill_create_ip,
                                'partner_trade_no': cashApply.partner_trade_no,
                            }
                            # res = wx_pay.unified_order(data)
                            res = wx_pay.enterprise_payment(data)
                            if res.get('return_code') == "SUCCESS" and res.get('result_code') == "SUCCESS":
                                # 付款成功 更改代理余额
                                agent.residue -= cashApply.cash
                                agent.save()
                            elif res.get('return_code') == "SUCCESS" and res.get('result_code') == "FAIL":
                                raise Exception(res.get('err_code_des'))
                            else:
                                raise Exception('通信失败')
                        return HttpResponse(json.dumps({'status': 1, 'message': '成功'}))

                except Exception as e:
                    return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))


# 下载二维码
@csrf_exempt
def download_qr(request):
    if request.method == 'GET':
        pass


# 优惠券
@csrf_exempt
def coupon(request):
    if request.method == 'GET':
        req = request.GET
        if int(req.get('type', 0)) == 1:
            if req.get('limit') and req.get('offset'):
                offset = int(req.get('offset'))
                limit = int(req.get('limit'))
                coupons = list(Coupon.objects.all().values().order_by('-createTime')[offset:offset + limit])
                return HttpResponse(json.dumps({'status': 1, 'coupons': coupons}, cls=CJsonEncoder))
            else:
                return HttpResponse(json.dumps({'status': 1, 'count': Coupon.objects.all().count()}))
        else:
            flag = int(req.get('flag', 0))
            page = int(req.get('page', 0))
            print(page)
            today = datetime.datetime.today().date()
            if flag == 0:  # 加载未使用优惠券

                coupons = list(UserCoupon.objects.filter(
                    Q(coupon__timeType=1, createTime__day=today.day, createTime__month=today.month,
                      createTime__year=today.year) |
                    Q(coupon__timeType=2, createTime__day=today.day, createTime__month=today.month,
                      createTime__year=today.year) |
                    Q(coupon__timeType=0, coupon__endTime__gt=datetime.datetime.now()),
                    user_id=req.get('userId'), status=0).values('user_id', 'coupon_id', 'status', 'createTime',
                                                                'coupon__couponType', 'coupon__fullAmount',
                                                                'coupon__onceAmount', 'coupon__reduceAmount',
                                                                'coupon__discount', 'coupon__disCountUpLimit',
                                                                'coupon__timeType', 'coupon__startTime',
                                                                'coupon__endTime',
                                                                'coupon__perWeekDay', 'coupon__perMonthDay').order_by(
                    '-createTime')[
                               page * 10:(page + 1) * 10])
                return HttpResponse(json.dumps({'status': 1, 'coupons': coupons}, cls=CJsonEncoder))
            elif flag == 1:  # 已经使用
                coupons = list(UserCoupon.objects.filter(
                    user_id=req.get('userId'), status=1).values('user_id', 'coupon_id', 'status', 'createTime',
                                                                'coupon__couponType', 'coupon__fullAmount',
                                                                'coupon__onceAmount', 'coupon__reduceAmount',
                                                                'coupon__discount', 'coupon__disCountUpLimit',
                                                                'coupon__timeType', 'coupon__startTime',
                                                                'coupon__endTime',
                                                                'coupon__perWeekDay', 'coupon__perMonthDay').order_by(
                    '-createTime')[
                               page * 10:(page + 1) * 10])
                return HttpResponse(json.dumps({'status': 1, 'coupons': coupons}, cls=CJsonEncoder))
            elif flag == 2:  # 已经过期

                coupons = list(
                    UserCoupon.objects.filter(
                        Q(coupon__timeType=0, coupon__endTime__lte=datetime.datetime.now()) |
                        Q(coupon__timeType=1, createTime__lt=today) |
                        Q(coupon__timeType=2, createTime__lt=today),
                        user_id=req.get('userId'),
                        status=0).values('user_id',
                                         'coupon_id',
                                         'status',
                                         'createTime',
                                         'coupon__couponType',
                                         'coupon__fullAmount',
                                         'coupon__onceAmount',
                                         'coupon__reduceAmount',
                                         'coupon__discount',
                                         'coupon__disCountUpLimit',
                                         'coupon__timeType',
                                         'coupon__startTime',
                                         'coupon__endTime',
                                         'coupon__perWeekDay',
                                         'coupon__perMonthDay').order_by(
                        '-createTime')[page * 10:(page + 1) * 10])
                return HttpResponse(json.dumps({'status': 1, 'coupons': coupons}, cls=CJsonEncoder))
            elif flag == 3:  # 未使用数量
                couponsCount = UserCoupon.objects.filter(
                    Q(coupon__timeType=1, createTime__day=today.day, createTime__month=today.month,
                      createTime__year=today.year) |
                    Q(coupon__timeType=2, createTime__day=today.day, createTime__month=today.month,
                      createTime__year=today.year) |
                    Q(coupon__timeType=0, coupon__endTime__gt=datetime.datetime.now()),
                    user_id=req.get('userId'), status=0).count()
                return HttpResponse(json.dumps({'status': 1, 'count': couponsCount}))
            elif flag == 4:  # 加载已使用数量
                count = UserCoupon.objects.filter(
                    user_id=req.get('userId'), status=1).count()
                return HttpResponse(json.dumps({'status': 1, 'count': count}))
            elif flag == 5:  # 加载已过期数量
                count = UserCoupon.objects.filter(
                    Q(coupon__timeType=0, coupon__endTime__lte=datetime.datetime.now()) |
                    Q(coupon__timeType=1, createTime__lt=today) |
                    Q(coupon__timeType=2, createTime__lt=today),
                    user_id=req.get('userId'),
                    status=0).count()
                return HttpResponse(json.dumps({'status': 1, 'count': count}))
            elif flag == 10:
                today = datetime.datetime.today()
                coupons = list(Coupon.objects.filter(
                    Q(timeType=0, endTime__gt=datetime.datetime.now()) | Q(timeType=1,
                                                                           perWeekDay=(today.weekday() + 1)) | Q(
                        timeType=2, perMonthDay=today.day),
                    status=1).values()[page * 10:(page + 1) * 10])
                for c in coupons:
                    if c.get('timeType') == 0:
                        c.setdefault('hasReceive', UserCoupon.objects.filter(user_id=req.get('userId'),
                                                                             coupon_id=c.get('id')).exists())
                    else:
                        today = datetime.datetime.today().date()
                        # 理念 上次领取的优惠券如还没有使用则过期
                        # 查找时间类型为1，2 的未使用的优惠券 如果用户使用了优惠券，又去领取要判断不能领取(每次只能领取一张)
                        c.setdefault('hasReceive',
                                     UserCoupon.objects.filter(user_id=req.get('userId'), coupon_id=c.get('id'),
                                                               createTime__day=today.day, createTime__year=today.year,
                                                               createTime__month=today.month).exists())
                return HttpResponse(json.dumps({'status': 1, 'coupons': coupons}, cls=CJsonEncoder))
    elif request.method == 'POST':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:  # 商家添加优惠券
            c = Coupon.objects.create(couponType=req.get('couponType', 0),
                                      fullAmount=decimal.Decimal(req.get('fullAmount', 0.00)),
                                      reduceAmount=decimal.Decimal(req.get('reduceAmount', 0.00)),
                                      onceAmount=decimal.Decimal(req.get('onceAmount', 0.00)),
                                      discount=decimal.Decimal(req.get('discount', '0.00')),
                                      disCountUpLimit=req.get('disCountUpLimit', 0),
                                      couponNum=req.get('couponNum', 0),
                                      couponResNum=req.get('couponNum', 0),
                                      timeType=req.get('timeType', 0),
                                      perWeekDay=req.get('perWeekDay', 0),
                                      perMonthDay=req.get('perMonthDay', 0),
                                      )
            if req.get('dateRange'):
                c.startTime = datetime.datetime.strptime(req.get('dateRange')[0], '%Y-%m-%d %H:%M:%S')
                c.endTime = datetime.datetime.strptime(req.get('dateRange')[1], '%Y-%m-%d %H:%M:%S')
                c.save()
            return HttpResponse(json.dumps({'status': 1, 'message': '添加成功'}))
        else:
            if req.get('userId') and req.get('couponId'):  # 用户领取优惠券
                coupon = Coupon.objects.get(id=req.get('couponId'))
                if coupon.timeType == 0:
                    userCoupon = UserCoupon.objects.filter(user_id=req.get('userId'), coupon_id=req.get('couponId'))
                    if userCoupon:
                        return HttpResponse(json.dumps({'status': 1, 'message': '已经领取了'}))
                    else:  # 判断数量
                        try:
                            with transaction.atomic():
                                if coupon.couponResNum > 0:
                                    coupon.couponResNum -= 1
                                    coupon.save()
                                    UserCoupon.objects.create(user_id=req.get('userId'), coupon_id=req.get('couponId'))
                                    return HttpResponse(json.dumps({'status': 1, 'message': '领取成功'}))
                                else:
                                    return HttpResponse(json.dumps({'status': 2, 'message': '数量不足'}))
                        except Exception as e:
                            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
                else:
                    today = datetime.datetime.today().date()
                    userCoupon = UserCoupon.objects.filter(user_id=req.get('userId'), coupon_id=req.get('couponId'),
                                                           createTime__day=today.day, createTime__month=today.month,
                                                           createTime__year=today.year)
                    if userCoupon:
                        return HttpResponse(json.dumps({'status': 1, 'message': '已经领取了'}))
                    else:
                        try:
                            with transaction.atomic():
                                if coupon.couponResNum > 0:
                                    coupon.couponResNum -= 1
                                    coupon.save()
                                    UserCoupon.objects.create(user_id=req.get('userId'), coupon_id=req.get('couponId'))
                                    return HttpResponse(json.dumps({'status': 1, 'message': '领取成功'}))
                                else:
                                    return HttpResponse(json.dumps({'status': 2, 'message': '数量不足'}))
                        except Exception as e:
                            return HttpResponse(json.dumps({'status': 0, 'message': str(e)}))
    elif request.method == 'PUT':
        req = json.loads(request.body.decode('utf-8'))
        if int(req.get('type', 0)) == 1:
            coupon = Coupon.objects.get(id=req.get('couponId'))
            coupon.status = req.get('status')
            coupon.save()
            return HttpResponse(json.dumps({'status': 1, 'message': '修改成功'}))


# 订单支付通知
@csrf_exempt
def pay_action_notify(request):
    if request.method == "POST":
        dict_req = WxPay.to_dict(request.body.decode('utf-8'))
        print('recievenotify')
        if dict_req["return_code"] == 'SUCCESS' and dict_req["result_code"] == 'SUCCESS':
            try:
                with transaction.atomic():
                    # 1.更改订单状态
                    out_trade_no = dict_req["out_trade_no"]
                    order = Order.objects.get(out_trade_no=out_trade_no, status=10)
                    if order.notifyStatus != 0:  # 已经通知过了
                        raise Exception('已经通知了')
                    user = User.objects.get(id=order.user_id)
                    orderType = ''
                    # 2.用户下单成功后可以获得20积分,只有通知成功才能获得
                    if order.orderType == 0:
                        orderType = '单买'
                        # user = User.objects.get(id=order.user_id)
                        user.score += 20
                        user.save()
                        order.status = 1  # 支付成功的订单
                    elif order.orderType == 1:  # 是拼团订单
                        orderType = '团购'
                        # 所有平团成员
                        collager = CollageUser.objects.get(id=order.collagerId)  # 团长
                        if collager.user_id == order.user_id:  # 是团长的通知消息
                            order.status = 1
                            order.save()
                            collager.status = 1
                            collager.save()
                        else:  # 是其他人的通知消息
                            collageSku = CollageSku.objects.get(id=collager.collageSku_id)
                            collage = Collage.objects.get(id=collageSku.collage_id)
                            collageUsers = CollageUser.objects.filter(collagerId=order.collagerId,
                                                                      status=1)  # 查找下单成功了的拼团用户
                            collageUser = CollageUser.objects.get(user_id=order.user_id,
                                                                  collagerId=order.collagerId)  # 当前通知者
                            if collage.collagePeople == len(collageUsers) + 1 + 1:  # 团是够人数了的（下单成功+团长+本人）
                                collager.status = 2
                                # collager.save()
                                collageUser.status = 2
                                collageUser.save()
                                for cu in collageUsers:
                                    cu.status = 2
                                    cu.save()
                                # 查找所有该团的订单，并设置为8 表示拼团成功
                                collageOrders = Order.objects.filter(collagerId=order.collagerId)
                                now = datetime.datetime.now()
                                for co in collageOrders:
                                    co.status = 8
                                    co.collageTime = now
                                    co.save()
                                order.status = 8
                                order.collageTime = now
                                # 活动营收+
                                collage.collageTotal += (collage.collagePeople * collageSku.collagePrice)
                                collage.save()
                            else:
                                # 还不够人数开团
                                collageUser.status = 1
                                collageUser.save()
                                order.status = 1  # 支付成功的订单
                    order.payTime = datetime.datetime.now()
                    wechat_push = WxPay()
                    orderContent = ''
                    orderSkus = OrderSku.objects.filter(order_id=order.id)
                    for oks in orderSkus:
                        orderContent += oks.productName + ' ' + str(oks.skuName) + '×' + str(oks.skuNum) + '  '
                        # 3.商品的销量对应相加
                        sku = SKU.objects.get(id=oks.sku_id)
                        sku.saleNum += oks.skuNum
                        sku.save()
                    # 商家总销售额和订单数量+1
                    count = Count.objects.filter()
                    if count:
                        count = count[0]
                    else:
                        count = Count.objects.create()
                    count.allOrderNum += 1
                    count.allSale += order.realTotal
                    count.save()
                    # 商家日销售额和订单数量+1
                    countDay = CountDay.objects.filter(day=datetime.datetime.now().date())
                    if countDay:
                        countDay = countDay[0]
                    else:
                        countDay = CountDay.objects.create(day=datetime.datetime.now().date())
                    countDay.orderNum += 1
                    countDay.sale += order.realTotal
                    countDay.save()
                    # 开始写消息模板
                    data = {  # "first": {"value": "同渡旅行告诉你有新的通知", "color": "#173177"},
                        "keyword1": {"value": order.order_code, "color": "#173177"},
                        "keyword2": {"value": order.realTotal, "color": "#173177"},
                        "keyword3": {"value": orderType, "color": "#173177"},
                        "keyword4": {"value": orderContent, "color": "#173177"},
                        "keyword5": {"value": order.province + order.city + order.area + order.address,
                                     "color": "#173177"},
                        "keyword6": {"value": order.createTime, "color": "#173177"},
                    }
                    res = wechat_push.do_push(user.openId,
                                              c_templateID_order_success,
                                              c_page,
                                              data,
                                              order.prepay_id, )
                    # print(res)
                    if res.get('errcode') == 0 and res.get('errmsg') == 'ok':  # 成功
                        order.notifyStatus = 1
                        pass
                    else:
                        print(res)
                    order.save()

                    response1 = {'return_code': "SUCCESS", 'msg': 'ok'}
            except Exception as e:
                print('通知出错了：' + str(e))
                response1 = {'return_code': "SUCCESS", 'msg': str(e)}
        elif dict_req["return_code"] == 'SUCCESS' and dict_req["result_code"] == 'FAIL':  # 如果某些原因导致支付不成功
            out_trade_no = dict_req["out_trade_no"]
            order = Order.objects.get(out_trade_no=out_trade_no)
            order.status = 0
            order.save()
            response1 = {'return_code': "SUCCESS", 'msg': 'ok'}
            pass
        else:
            response1 = {'return_code': "SUCCESS", 'msg': 'ok'}
        wx_pay = WxPay()
        return HttpResponse(wx_pay.to_xml(response1))


# 13.退款结果通知接口

@csrf_exempt
def refund_action_notify(refund_action_notify_request):
    if refund_action_notify_request.method == 'POST':
        dict_req = WxPay.to_dict(refund_action_notify_request.body.decode('utf-8'))
        return_code = dict_req.get("return_code")
        if return_code == 'SUCCESS':  # 通信成功
            req_info = dict_req.get("req_info")  # 获得加密信息
            # 对接收的数据进行解码
            password = md5key(c_merchant_key)
            # ase_data = decode_a_to_b(req_info)  # 获得加密字符串B
            # return HttpResponse(ase_data)
            xml_data = decrypt(req_info, password)  # 得到xml的数据
            data = WxPay.to_dict_refund(xml_data)  # 得到字典
            # return HttpResponse(json.dumps(data))
            if data.get("refund_status") == "SUCCESS":  # 退款成功
                try:
                    with transaction.atomic():  # 进行事务的管理，进行数据库的回滚
                        # if len(data["out_trade_no"]) == 28:
                        #     order = Orders.objects.get(Out_Trade_No=data["out_trade_no"])  # 修改订单
                        #     order.State = 7  # 退款成功
                        #     order.save()
                        #     ticket = Ticket.objects.select_for_update().get(id=order.Ticket_id)
                        #     ticket.remainingNumber = ticket.remainingNumber + order.TicketNumber
                        #     ticket.save()
                        # elif len(data["out_refund_no"]) == 18:  # 是活动退款
                        #     activityOrder = ActivityOrders.objects.get(out_trade_no=data["out_refund_no"])
                        #     activityOrder.state = 7  # 退款成功
                        #     activityOrder.save()
                        #     subOrders = SubOrders.objects.filter(activityOrders_id=activityOrder.id)
                        #     for sub in subOrders:
                        #         sub.state = 0
                        #         sub.save()
                        # elif len(data["out_refund_no"]) == 20:  # 是子订单退款
                        #     sub = SubOrders.objects.get(out_refund_no=data["out_refund_no"])
                        #     sub.state = 0
                        #     sub.save()
                        #     subNum = SubOrders.objects.filter(Q(state=1) | Q(state=3),
                        #                                       activityOrders_id=sub.activityOrders_id)
                        #     if len(subNum) == 0:
                        #         activityOrder = ActivityOrders.objects.get(id=sub.activityOrders_id)
                        #         activityOrder.state = 7
                        #         activityOrder.save()
                        js_res = {'return_code': 'SUCCESS', 'return_msg': 'OK'}
                except Exception as e:
                    js_res = {'return_code': 'SUCCESS', 'return_msg': str(e)}
                    print(e)
                    pass
                res = WxPay().to_xml(js_res)
                return HttpResponse(res)
            elif data.get("refund_status") == "CHANGE":  # 退款异常
                try:
                    with transaction.atomic():
                        # if len(data["out_trade_no"]) == 28:
                        #     order = Orders.objects.get(Out_Trade_No=data["out_trade_no"])  # 修改订单
                        #     order.State = 1  # 退款不成功，订单状态要修改为原来的状态
                        #     order.save()
                        # elif len(data["out_refund_no"]) == 18:  # 是活动退款
                        #     activityOrder = ActivityOrders.objects.get(out_trade_no=data["out_refund_no"])
                        #     activityOrder.state = 1  # 退款不成功
                        #     activityOrder.save()
                        #     subOrders = SubOrders.objects.filter(activityOrders_id=activityOrder.id)
                        #     for sub in subOrders:
                        #         sub.state = 1
                        #         sub.save()
                        # elif len(data["out_refund_no"]) == 20:  # 是子订单退款
                        #     sub = SubOrders.objects.get(out_refund_no=data["out_refund_no"])
                        #     sub.state = 1
                        #     sub.save()
                        #     subNum = SubOrders.objects.filter(Q(state=1) | Q(state=9),
                        #                                       activityOrders_id=sub.activityOrders_id)
                        #     if subNum:
                        #         activityOrder = ActivityOrders.objects.get(id=sub.activityOrders_id)
                        #         activityOrder.state = 1
                        #         activityOrder.save()
                        js_res = {'return_code': 'SUCCESS', 'return_msg': 'OK'}
                except Exception as e:
                    js_res = {'return_code': 'SUCCESS', 'return_msg': str(e)}
                    print(e)
                res = WxPay().to_xml(js_res)
                return HttpResponse(res)
            else:
                js_res = {'return_code': 'SUCCESS', 'return_msg': '退款关闭'}
                res = WxPay().to_xml(js_res)
                return HttpResponse(res)
        else:
            js_res = {'return_code': 'FAIL', 'return_msg': '通信不成功'}
            res = WxPay().to_xml(js_res)
            return HttpResponse(res)


@csrf_exempt
def express(request):
    if request.method == 'GET':
        req = request.GET
        # url = 'http://api.56jiekou.com/index.php/openapi-api.html?key=54faeaeee7ff89fadc04f91e07170eca&num=437889771953&exp=zhongtong'
        url = 'http://api.56jiekou.com/index.php/openapi-api.html?key=54faeaeee7ff89fadc04f91e07170eca&num=' + req.get(
            'expressNo') + '&exp=' + req.get('expressCode')
        res = requests.get(url=url)
        return HttpResponse(res.content)
