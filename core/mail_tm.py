"""
Mail.tm 临时邮箱模块
从 codex_register 提取，自动创建邮箱 + 轮询验证码
"""
import re
import time
import random
import string
from curl_cffi.requests import Session
from typing import Optional, Tuple, Callable

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def _rand_str(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _rand_password():
    """生成高强度随机密码"""
    special = "!@#$%^&*.-"
    base = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(special),
    ]
    base += [random.choice(string.ascii_letters + string.digits + special) for _ in range(12)]
    random.shuffle(base)
    return "".join(base)


def _request(method, path, json_data=None, token=None, proxy=None):
    """通用 mail.tm 请求"""
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": UA,
        "pragma": "no-cache",
    }
    if token:
        headers["authorization"] = f"Bearer {token}"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        with Session(proxies=proxies) as s:
            return s.request(method, f"https://api.mail.tm{path}", json=json_data, headers=headers, timeout=20)
    except:
        return None


def _get_otp(token, proxy=None, keywords=None, timeout_sec=480):
    """
    轮询等待验证码
    keywords: 关键词列表，匹配 subject 或 intro
    """
    if keywords is None:
        keywords = ["verification", "code", "confirm", "OpenAI", "ChatGPT"]

    for _ in range(timeout_sec // 8):
        r = _request("GET", "/messages", token=token, proxy=proxy)
        if r and r.status_code == 200:
            try:
                dat = r.json()
            except:
                time.sleep(8)
                continue

            msgs = dat.get("hydra:member", []) if isinstance(dat, dict) else dat
            if not isinstance(msgs, list):
                msgs = []

            for m in msgs:
                if not isinstance(m, dict):
                    continue
                sb = m.get("subject", "")
                intro = m.get("intro", "")

                # 匹配关键词
                if any(kw in sb or kw in intro for kw in keywords):
                    rb = _request("GET", f"/messages/{m.get('id')}", token=token, proxy=proxy)
                    if rb and rb.status_code == 200:
                        txt = rb.json().get("text", "")
                        # 提取 6 位数字验证码
                        match = re.search(r"(\d{6})", txt) or re.search(r"(\d{6})", sb)
                        if match:
                            return match.group(1)
        time.sleep(8)
    return None


def create_temp_mail(proxy=None, keywords=None) -> Optional[Tuple[str, str, Callable]]:
    """
    创建临时邮箱，返回 (email, password, fetch_code_func)
    fetch_code_func: 调用后阻塞等待验证码返回

    用法:
        email, password, fetch_code = create_temp_mail()
        # ... 做注册操作，触发发送验证码 ...
        code = fetch_code()  # 阻塞等待，返回 6 位验证码
    """
    mail_pw = "at41rvxgptye"

    # 1. 获取可用域名
    domain_res = _request("GET", "/domains", proxy=proxy)
    if not domain_res or domain_res.status_code != 200:
        print("  [!] 无法获取 mail.tm 域名")
        return None

    try:
        js = domain_res.json()
        domains = js if isinstance(js, list) else js.get("hydra:member", [])
        if not domains:
            print("  [!] 域名列表为空")
            return None
        domain = domains[0].get("domain")
    except Exception as e:
        print(f"  [!] 解析域名失败: {e}")
        return None

    # 2. 注册邮箱
    email = f"{_rand_str(10)}@{domain}"
    r = _request("POST", "/accounts", {"address": email, "password": mail_pw}, proxy=proxy)
    if not r or r.status_code not in [200, 201]:
        print(f"  [!] 邮箱注册失败: {r.text if r else '无响应'}")
        return None

    # 3. 获取 Token
    r = _request("POST", "/token", {"address": email, "password": mail_pw}, proxy=proxy)
    if not r or r.status_code != 200:
        print("  [!] 获取邮箱 Token 失败")
        return None

    mail_token = r.json().get("token")
    password = _rand_password()

    def fetch_code():
        print(f"  [*] 等待验证码到 {email} ...")
        return _get_otp(mail_token, proxy=proxy, keywords=keywords)

    return email, password, fetch_code
