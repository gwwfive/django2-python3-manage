import base64
import hashlib
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex,a2b_base64


# md5,把商户key转化为md5加密的字符串用于aes解密


def md5key(key):
    m = hashlib.md5()
    m.update(key.encode("utf-8"))
    return m.hexdigest()

# aes-ecb解码


# def decrypt(data, password):
    # bs = AES.block_size
    # if len(data) <= bs:
        # return data
    # unpad = lambda s: s[0:-ord(s[-1])]
    # iv = data[:bs]
    # cipher = AES.new(password, AES.MODE_ECB, iv)  # ecb解码
    # data = unpad(cipher.decrypt(data[bs:]))
    # return data.decode('utf-8')
# 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
def encrypt(key,text):
    cryptor = AES.new(key, AES.MODE_ECB)
    text = text.encode("utf-8")
    # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
    length = 16
    count = len(text)
    add = length - (count % length)
    text = text + (b'\0' * add)
    ciphertext = cryptor.encrypt(text)
    # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
    # 所以这里统一把加密后的字符串转化为16进制字符串
    return b2a_hex(ciphertext).decode("ASCII")

def decrypt(text,key):
    cryptor = AES.new(key, AES.MODE_ECB)
    plain_text = cryptor.decrypt(base64.b64decode(text))
    return plain_text.rstrip(b'\0').decode('utf-8')