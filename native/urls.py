"""native URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main import views as mainViews

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/admin/', mainViews.admin),
    path('v1/admin/info', mainViews.admin_info),
    path('v1/admin/login', mainViews.login),
    path('v1/admin/logout', mainViews.logout),
    path('v1/user/', mainViews.user),
    path('v1/order/', mainViews.order),
    path('v1/sale/', mainViews.sale),
    path('v1/shop/', mainViews.shop),
    path('v1/upload/image/', mainViews.upload_image),
    path('v1/category/', mainViews.category),
    path('v1/product/', mainViews.product),
    path('v1/order/', mainViews.order),
    path('v1/order/comment/', mainViews.order_comment),
    path('v1/carousel/', mainViews.carousel),
    path('v1/collage/', mainViews.collage),
    path('v1/collage/order/', mainViews.collage_order),
    path('v1/id/search/', mainViews.searchId),
    path('v1/sku/', mainViews.sku),
    path('v1/collage/product/', mainViews.collage_product),
    path('v1/address/suggest/', mainViews.address_suggest),
    path('v1/cart/', mainViews.cart),
    path('v1/address/', mainViews.address),
    path('v1/member/', mainViews.member),
    path('v1/sign/', mainViews.sign_day),
    path('v1/agent/', mainViews.agent),
    path('v1/coupon/', mainViews.coupon),
    path('v1/pay/notify/', mainViews.pay_action_notify),
    path('v1/refund/notify/', mainViews.refund_action_notify),
    path('v1/express/', mainViews.express),
    path('v1/count/', mainViews.count),
    path('v1/distribution/', mainViews.distribution),
    path('v1/index/', mainViews.index),
    path('v1/search/', mainViews.search)
]
