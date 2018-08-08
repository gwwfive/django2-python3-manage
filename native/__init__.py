import pymysql
# from vinceBus.celery import app as celery_app
pymysql.install_as_MySQLdb()

# 打开数据库连接
db = pymysql.connect("localhost", "root", "1106", "native")
# 使用cursor方法获取操作游标
cursor = db.cursor()

# 使用execute方法执行SQL语句
cursor.execute("SELECT VERSION()")
# 使用 fetchone() 方法获取一条数据库
data = cursor.fetchone()

print("Database version: %s" % data)

# 关闭数据库连接
db.close()