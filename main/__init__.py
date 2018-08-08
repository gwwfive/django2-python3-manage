# 3.0 以上版本的apscheduler的定时方法
from apscheduler.schedulers.background import BackgroundScheduler
from main.tasks import *

# global scheduler
scheduler = BackgroundScheduler()
if scheduler and scheduler.running:
    print('scheduler is running')
else:
    scheduler = BackgroundScheduler()
    # 定时执行更行access_token
    scheduler.add_job(updata_access_token, 'interval', seconds=7000)
    # 每天备份数据库
    scheduler.add_job(backupDataBase, 'cron', hour=3, minute=10)
    # # 每分钟执行一次
    scheduler.add_job(update_order_a, 'interval', seconds=60)
    # # 每10分钟执行一次
    scheduler.add_job(update_order_b, 'interval', seconds=60)
    scheduler.start()
# 2.0 版本的apscheduler的定时方法
# from apscheduler.scheduler import Scheduler
# from trip.tasks import updata_access_token, backupDataBase
# global sched
# sched = Scheduler()
#
# @sched.interval_schedule(seconds=7000)  # 只有访问了url 才会执行
# def mytask():
#     updata_access_token()
#
# # 每天凌晨3:10am 备份
# @sched.cron_schedule(day_of_week='0-6', hour='3', minute='10')
# def backup():
#     backupDataBase()
# sched.start()
