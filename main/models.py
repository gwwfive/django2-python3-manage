# from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class User(models.Model):
    nickName = models.CharField(max_length=100, default='')  # 昵称
    gender = models.PositiveSmallIntegerField(default=1)  # 性别
    avatarUrl = models.URLField(blank=True, null=True)  # 头像
    phoneNum = models.CharField(max_length=20, default='')  # 电话
    createTime = models.DateTimeField(auto_now_add=True)  # 创建时间
    openId = models.CharField(max_length=100, default='')
    isAgent = models.BooleanField(default=False)  # 是否代理商
    province = models.CharField(max_length=100,default='')  # 省份
    city = models.CharField(max_length=100, default='')  # 城市
    score = models.PositiveIntegerField(default=0)  # 积分数量
    agentId = models.PositiveIntegerField(default=0)  # 代理人id
    fansLevel = models.PositiveSmallIntegerField(default=1)  # 1级 2级
    sharedStatus = models.BooleanField(default=False)  # 被分享状态


class MemberDiscount(models.Model):  # 会员的折扣
    score = models.PositiveIntegerField(default=0)  # 达到这个分数
    memberName = models.CharField(max_length=100, default='')  # 会员昵称，例如青铜会员
    level = models.PositiveSmallIntegerField(default=0)  # 等级
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 会员折扣


# 优惠券
class Coupon(models.Model):
    couponType = models.PositiveSmallIntegerField(default=0)  # 0满减 1立减 2折扣 3指定商品
    fullAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 满多少 couponType = 0 有效
    reduceAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 减多少 couponType = 0 有效
    onceAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 立刻减多少 couponType = 1有效
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 折扣
    disCountUpLimit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 折扣上限
    # disCountDownLimit = models.PositiveSmallIntegerField(default=0)  # 折扣下限 满多少才有折扣
    couponNum = models.PositiveSmallIntegerField(default=0)  # 优惠券总数量
    couponResNum = models.PositiveSmallIntegerField(default=0)  # 优惠券剩余数量
    timeType = models.PositiveSmallIntegerField(default=0)  # 时间类型 0为某一个时间段有效 1固定每周某日有效 2固定某月有效
    startTime = models.DateTimeField(blank=True, null=True)  # 优惠券开始时间
    endTime = models.DateTimeField(blank=True, null=True)  # 优惠券结束时间
    perWeekDay = models.PositiveSmallIntegerField(default=0)  # 固定每周某日有效
    perMonthDay = models.PositiveSmallIntegerField(default=0)  # 固定每月某日有效

    createTime = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(default=1)  # 1为发行 2为暂停
    # 时间段的只能领一次，固定时间的可以每次领取
    # userLimit = models.PositiveSmallIntegerField(default=1)  # 1用户只可以领取一次，0为无限张，但每日只可以领取一张


class UserCoupon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(default=0)  # 0未使用(含过期) 1为已使用
    createTime = models.DateTimeField(auto_now_add=True)  # 领券时间，可以用户判断是否过期


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    province = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=20, default='')
    area = models.CharField(max_length=20, default='')
    # town = models.CharField(max_length=20, default='')
    address = models.CharField(max_length=200, default='')
    name = models.CharField(max_length=20, default='')
    phoneNum = models.CharField(max_length=20, default='')
    isNormal = models.BooleanField(default=False)


class Shop(models.Model):
    shopName = models.CharField(max_length=100, default='')
    shopAddress = models.CharField(max_length=200, default='')
    lat = models.CharField(max_length=50, default='0.000000')
    lng = models.CharField(max_length=50, default='0.000000')
    shopIntroduce = models.TextField(default='')
    shopPhoneNum = models.CharField(max_length=11, default='')
    # shopRate = models.DecimalField(max_digits=2, decimal_places=1)
    shopSaleNum = models.PositiveIntegerField(default=0)
    # shopCategory = models.CharField(max_length=50, default='特产')
    shopImgUrl = models.URLField(default='')
    # createTime = models.DateTimeField()


class Category(models.Model):  # 分类
    # shop = models.ForeignKey(Shop, on_delete=models.CASCADE)  # 某一个商店的分类
    value = models.CharField(max_length=100, default='')  # 分类的名称
    label = models.CharField(max_length=100, default='')
    fatherId = models.PositiveSmallIntegerField(default=0)  # 父级分类
    index = models.PositiveIntegerField(default=0)  # 排序
    status = models.PositiveSmallIntegerField(default=0)  #0未上线 1线上，2下线


class Product(models.Model):  # 产品
    imgUrl = models.URLField(default='')  # 产品的主图
    productName = models.CharField(max_length=100, default='')  # 商品名称
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # 商品分类
    categoryList = models.CharField(max_length=100, default='')
    # shop = models.ForeignKey(Shop, default=1, on_delete=models.CASCADE)
    sellPoint = models.CharField(max_length=50, default='')  # 商品的卖点
    keyWords = models.CharField(max_length=100, default='')  # 商品关键词
    introduce = models.TextField(max_length=1000, default='')  # 商品的介绍
    price = models.DecimalField(max_digits=20, decimal_places=2)  # 列表价
    createTime = models.DateTimeField(auto_now_add=True)
    originPrice = models.DecimalField(max_digits=20, decimal_places=2)  # 原始价格
    rate = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)  # 商品评分
    saleNum = models.PositiveIntegerField(default=0)
    status = models.PositiveSmallIntegerField(default=0)  # 0 没发布 1上架 2已经下架


# 用户收藏的商品
class UserProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class ProductFormat(models.Model):  # 产品的规格
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    formatName = models.CharField(max_length=100, default='')
    formatValue = models.CharField(max_length=100, default='')
    index = models.PositiveSmallIntegerField(default=0)  # 排序


# 商品图片表P
class Picture(models.Model):
    picUrl = models.URLField(default='')  # 图片地址
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(default=0)  # 图片位置
    # isLunBo = models.BooleanField(default=False)  # 是否是轮播图
    isVideo = models.BooleanField(default=False)  # 是否是视频
    createTime = models.DateTimeField(auto_now_add=True)


# 商品sku表
class SKU(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    residualNum = models.PositiveIntegerField(default=0)  # 剩余数量
    sellPrice = models.DecimalField(max_digits=20, decimal_places=2)  # 现价
    originPrice = models.DecimalField(max_digits=20, decimal_places=2)  # 原价
    status = models.PositiveSmallIntegerField(default=1)  # 0下架 1上架
    skuName = models.CharField(max_length=100, default='')  # sku 名称
    attrValueName = models.CharField(max_length=100, default='')  # 属性值字符串
    saleNum = models.PositiveIntegerField(default=0)
    # barCode = models.CharField(max_length=100, default='')  #条码，一般从扫描枪中扫描出的是Barcode，然后我们需要进行一些处理才会得到SKU
    # productCode = models.CharField(max_length=100, default='')  # 货码
    commentNum = models.PositiveSmallIntegerField(default=0)  # 评论数
    rate = models.PositiveIntegerField(default=0)  # 评分总数


# # 属性名表
# class AttrName(models.Model):
#     attrName = models.CharField(max_length=100, default='')  # 属性名称
#     category = models.ForeignKey(Category, on_delete=models.CASCADE)  # 所属类目Id,必须的
#     isSearch = models.BooleanField(default=False)  # 是否是搜搜属性
#     isNeed = models.BooleanField(default=False)  # 是否必须
#     isMulti = models.BooleanField(default=False)  # 是否多选
#     state = models.PositiveSmallIntegerField(default=0)  # 状态
#     index = models.PositiveSmallIntegerField(default=0)  # 排序
#     createTime = models.DateTimeField(auto_now_add=True)


# # 属性值表
# class AttrValue(models.Model):
#     attrValue = models.CharField(max_length=100, default='')  # 属性值名称
#     attrName = models.ForeignKey(AttrName, on_delete=models.CASCADE)
#     state = models.PositiveSmallIntegerField(default=0)  # 状态
#     index = models.PositiveSmallIntegerField(default=0)  # 排序
#     # category = models.ForeignKey(Category, blank=True, null=True)
#     createTime = models.DateTimeField(auto_now_add=True)


# # 产品基本属性表
# class AttrOfSKU(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     attrName = models.ForeignKey(AttrName, on_delete=models.CASCADE)  # 属性名
#     attrValue = models.ForeignKey(AttrValue, on_delete=models.CASCADE)  # 属性值
#     isSKU = models.BooleanField(default=True)  # 是否sku  如果不是，那么将时全局属性
#     sku = models.ForeignKey(SKU, blank=True, null=True, on_delete=models.CASCADE)  # isSKU 为真是，该值才有效


# 订单表
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    realTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 会员折扣
    createTime = models.DateTimeField()
    # skuNum = models.PositiveSmallIntegerField(default=1)
    prepay_id = models.CharField(max_length=100, default='')
    out_trade_no = models.CharField(max_length=100, default='')
    # out_refund_no = models.CharField(max_length=100,default='')  # 退款单号
    order_code = models.CharField(max_length=100, default='')  # 订单号
    status = models.PositiveSmallIntegerField(
        default=9)  # 0未支付 1支付完成(未发货) 2商家已发货(未收货) 3收货完成(待评价) 4(评价完成-订单完成) 5(取消支付或者支付超时(取消订单)) 6(未点签收时)(申请退款中) 7(退款完成) 8(组成拼团成功待收货) 9结算临时订单，如果用户调起支付则变为0，从而变为1;10用户已经支付了，但是服务器还没有收到成功通知
    orderType = models.PositiveSmallIntegerField(default=0)  # 0购买 1拼团
    collagerId = models.PositiveIntegerField(default=0)  # 团长Id orderType = 1有效
    province = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=20, default='')
    area = models.CharField(max_length=20, default='')
    # town = models.CharField(max_length=20, default='')
    address = models.CharField(max_length=200, default='')
    name = models.CharField(max_length=20, default='')
    phoneNum = models.CharField(max_length=20, default='')
    userCoupon = models.ForeignKey(UserCoupon, on_delete=models.CASCADE, null=True, blank=True)  # 优惠券
    payTime = models.DateTimeField(blank=True, null=True)  # 支付时间 createTime 就是订单创建时间
    prePayTime = models.DateTimeField(blank=True, null=True)  # 预支付时间，用户每调起一次支付，该时间刷新一次
    # 快递信息
    express = models.CharField(max_length=50, default='')
    expressCode = models.CharField(max_length=50,default='')  # 快递公司的简码
    expressNo = models.CharField(max_length=50, default='')
    expressTime = models.DateTimeField(null=True, blank=True)  # 发货时间
    receiveTime = models.DateTimeField(null=True, blank=True)  # 收货时间
    notifyStatus = models.PositiveSmallIntegerField(default=0)  # 0没有任何通知 1已经支付成功通知 2已经发送发货通知了

    collageTime = models.DateTimeField(null=True, blank=True)  # 成团时间

    # 申请退款时间
    #


# 一个订单可以有很多的商品
class OrderSku(models.Model):  # 订单的商品
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    skuPrice = models.CharField(max_length=20, default='')
    skuNum = models.PositiveSmallIntegerField(default=1)
    skuName = models.CharField(max_length=100, default='')
    productName = models.CharField(max_length=100, default='')
    imgUrl = models.URLField(default='')  # 商品url
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    cartSkuId = models.PositiveSmallIntegerField(default=0)  # 购车skuId


# class OrderAddress(models.Model):  # 订单地址
#     order = models.ForeignKey(Order, on_delete=models.CASCADE)
#     province = models.CharField(max_length=20, default='')
#     city = models.CharField(max_length=20, default='')
#     area = models.CharField(max_length=20, default='')
#     # town = models.CharField(max_length=20, default='')
#     address = models.CharField(max_length=200, default='')
#     name = models.CharField(max_length=20, default='')
#     phoneNum = models.CharField(max_length=20, default='')


# 购物车的商品
class CartSku(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)
    skuNum = models.PositiveSmallIntegerField(default=1)


class Admin(models.Model):
    account = models.CharField(max_length=100, default='')
    passWord = models.CharField(max_length=100, default='')
    avatarUrl = models.URLField(default='')
    city = models.CharField(max_length=100, default='')
    createTime = models.DateTimeField(auto_now_add=True)
    isRoot = models.BooleanField(default=False)


class Comment(models.Model):  # 评价，评分
    order = models.ForeignKey(Order, on_delete=models.CASCADE)  # 订单
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)  # 商品的sku
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 用户
    isAnonymous = models.BooleanField(default=True)  # 是否匿名
    # product = models.ForeignKey(Product, on_delete=models.CASCADE)
    content = models.CharField(max_length=300, default='')
    rate = models.PositiveSmallIntegerField(default=5)  # 评分
    createTime = models.DateTimeField(auto_now_add=True)


class CommentImage(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    imgUrl = models.URLField(default='')


# 数据统计 商家端
# 总额
class Count(models.Model):
    allSale = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    allUserNum = models.PositiveIntegerField(default=0)  # 用户
    allOrderNum = models.PositiveIntegerField(default=0)  # 订单


# 日统计
class CountDay(models.Model):
    sale = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    userNum = models.PositiveIntegerField(default=0)
    orderNum = models.PositiveIntegerField(default=0)
    day = models.DateField(null=True, blank=True)


# 拼团

class Collage(models.Model):
    startTime = models.DateTimeField()  # 开始时间
    endTime = models.DateTimeField()  # 结束时间
    effectiveTime = models.PositiveSmallIntegerField(default=12)  # 成团有效时间。如果超过12小时那么此次拼团作废。
    # product = models.ManyToManyField(Product)  # 关联商品Id 一个团可以包含多个商品
    collagePeople = models.PositiveSmallIntegerField(default=2)  # 成团人数
    collageLimit = models.PositiveSmallIntegerField(default=1)  # 每人限购
    status = models.PositiveSmallIntegerField(default=0)  # 活动的状态 0 为未上线 1为上线 2暂停 3过期
    createTime = models.DateTimeField(auto_now_add=True)  # 创建时间
    collageTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 活动营收

    # handleStatus = models.PositiveSmallIntegerField(default=0)  # 0未处理完，1已处理完


# 拼团sku
class CollageSku(models.Model):
    collage = models.ForeignKey(Collage, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    sku = models.ForeignKey(SKU, on_delete=models.CASCADE)

    collagePrice = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    collageNum = models.PositiveSmallIntegerField(default=1)  # 团的数量,可以组成多少个团
    residualNum = models.PositiveSmallIntegerField(default=1)  # 剩余团的数量，用户拼团时会根据这个数量进行判断是否可以组成团


# 拼团用户表
class CollageUser(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 商品id
    collageSku = models.ForeignKey(CollageSku, on_delete=models.CASCADE)  # 拼团的sku
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    isCollage = models.BooleanField(default=False)  # 是否是团长
    attendTime = models.DateTimeField()  # 参团时间
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0.00)  # 付款金额
    collageNo = models.CharField(max_length=20, default='')  # 拼团的单号
    # 团长id
    collagerId = models.PositiveIntegerField(default=0)  # 团长id
    status = models.PositiveSmallIntegerField(default=0)  # 1已经支付成功 2已经拼团成功 3平团失败退款（包括商家不发货，到期无人参加）


# 代理人
class Agent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # userId = models.PositiveIntegerField(default=1)
    realName = models.CharField(max_length=50, default='')
    phoneNum = models.CharField(max_length=50, default='')
    createTime = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(default=0)  # 0停止代理 1开始代理
    total = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)  # 总金额
    residue = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)  # 剩余
    firstFans = models.PositiveIntegerField(default=0)  # 一级粉丝数
    secondFans = models.PositiveIntegerField(default=0)  # 二级粉丝数
    avatarUrl = models.URLField()


# 代理申请
class AgentApply(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    realName = models.CharField(max_length=100, default='')
    phoneNum = models.CharField(max_length=20, default='')
    createTime = models.DateTimeField(auto_now_add=True)
    city = models.CharField(max_length=20, default='')
    gender = models.PositiveSmallIntegerField(default=1)
    province = models.CharField(max_length=20, default='')
    avatarUrl = models.URLField()


    status = models.PositiveSmallIntegerField(default=0)  # 0未审核 1通过 2不通过


# 提现记录
class CashApply(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(default=0)  # 0未处理 1允许 2拒绝
    cash = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)  # 申请总额
    name = models.CharField(max_length=20, default='')  # 姓名
    wxCode = models.CharField(max_length=50, default='')  # 微信号
    phoneNum = models.CharField(max_length=20, default='')  # 电话
    applyTime = models.DateTimeField(auto_now_add=True)

    partner_trade_no = models.CharField(max_length=50, default='')  # 商户支付好


# 代理月统计表 -- 舍去，不采用这种方案了
# class AgentCountMonth(models.Model):
#     agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
#     total = models.DecimalField(max_digits=10, decimal_places=2, default='')  # 月收益
#     firstFans = models.PositiveSmallIntegerField(default=0)  # 月新增一级粉丝
#     secondFans = models.PositiveSmallIntegerField(default=0)  # 月新增二级粉丝
#     month = models.DateField(null=True,blank=True)

# 代理日统计
class AgentCountDay(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 日收益
    firstFans = models.PositiveSmallIntegerField(default=0)  # 日新增一级粉丝
    secondFans = models.PositiveSmallIntegerField(default=0)  # 日新增二级粉丝
    day = models.DateField(null=True, blank=True)


# 代理收益记录表
class AgentProfitRecord(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    even = models.CharField(max_length=50, default='')  # 事件
    createTime = models.DateTimeField(auto_now_add=True)  # 创建时间
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 收益值


# 主页轮播图
class Carousel(models.Model):
    url = models.URLField(default='')


# 签到表
class SignDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  #
    date = models.DateField()


# 积分记录表
class ScoreRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    even = models.CharField(max_length=20, default='')  # 事件
    createTime = models.DateTimeField(auto_now_add=True)  # 创建时间
    value = models.PositiveSmallIntegerField(default=0)  # 获得的积分


# 分销规则
class Distribution(models.Model):
    firstProfit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    firstLimit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    secondProfit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    secondLimit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
