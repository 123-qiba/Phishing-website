# features.py
import re
import socket
from urllib.parse import urlparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import whois
import dns.resolver
from functools import lru_cache
import os


# 30 个特征名称（最后一个是标签，在这里不生成）
FEATURE_NAMES = [
    "having_IP_Address",
    "URL_Length",
    "Shortining_Service",
    "having_At_Symbol",
    "double_slash_redirecting",
    "Prefix_Suffix",
    "having_Sub_Domain",
    "SSLfinal_State",
    "Domain_registeration_length",
    "Favicon",
    "port",
    "HTTPS_token",
    "Request_URL",
    "URL_of_Anchor",
    "Links_in_tags",
    "SFH",
    "Submitting_to_email",
    "Abnormal_URL",
    "Redirect",
    "on_mouseover",
    "RightClick",
    "popUpWidnow",
    "Iframe",
    "age_of_domain",
    "DNSRecord",
    "web_traffic",
    "Page_Rank",
    "Google_Index",
    "Links_pointing_to_page",
    "Statistical_report",
]


# ---------------------------------------------------
# 一些工具函数
# ---------------------------------------------------

SHORTENING_SERVICES = [
    "bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "t.co",
    "is.gd", "buff.ly", "adf.ly", "bit.do", "cutt.ly"
]

def get_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def get_scheme(url):
    try:
        return urlparse(url).scheme.lower()
    except Exception:
        return ""

def get_path(url):
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""

# ---------------------------------------------------
# 1. having_IP_Address
# ---------------------------------------------------
def feat_having_IP_Address(url):
    domain = get_domain(url)
    # 匹配 IPv4 或 IPv6
    ipv4_pattern = r"^\d{1,3}(\.\d{1,3}){3}$"
    ipv6_pattern = r"^\[?[0-9a-fA-F:]+\]?$"
    if re.match(ipv4_pattern, domain) or re.match(ipv6_pattern, domain):
        return 1
    return -1

# ---------------------------------------------------
# 2. URL_Length
# ---------------------------------------------------
def feat_URL_Length(url):
    length = len(url)
    if length < 54:
        return -1
    elif 54 <= length <= 75:
        return 0
    else:
        return 1

# ---------------------------------------------------
# 3. Shortining_Service
# ---------------------------------------------------
def feat_Shortining_Service(url):
    domain = get_domain(url)
    if any(svc in domain for svc in SHORTENING_SERVICES):
        return 1
    return -1

# ---------------------------------------------------
# 4. having_At_Symbol
# ---------------------------------------------------
def feat_having_At_Symbol(url):
    return 1 if "@" in url else -1

# ---------------------------------------------------
# 5. double_slash_redirecting
# ---------------------------------------------------
def feat_double_slash_redirecting(url):
    # 查找除 "http://" 之外的 "//" 位置
    pos = url.find("//", 7)
    if pos != -1:
        return 1
    return -1

# ---------------------------------------------------
# 6. Prefix_Suffix（域名中使用 - ）
# ---------------------------------------------------
def feat_Prefix_Suffix(url):
    domain = get_domain(url)
    if "-" in domain.split(".")[0]:
        return 1
    return -1

# ---------------------------------------------------
# 7. having_Sub_Domain
# ---------------------------------------------------
def feat_having_Sub_Domain(url):
    domain = get_domain(url)
    # 去掉端口
    domain = domain.split(":")[0]
    dots = domain.count(".")
    if dots <= 1:
        return -1
    elif dots == 2:
        return 0
    else:
        return 1

# ---------------------------------------------------
# 8. SSLfinal_State（简化版）
# ---------------------------------------------------
def feat_SSLfinal_State(url):
    scheme = get_scheme(url)
    if scheme != "https":
        return 1
    # 简单认为 https 就给 -1，复杂一点可以加证书检查
    return -1

# ---------------------------------------------------
# 9. Domain_registeration_length（WHOIS，简化）
# ---------------------------------------------------
def feat_Domain_registeration_length(url):
    domain = get_domain(url).split(":")[0]
    try:
        w = whois.whois(domain)
        exp = w.expiration_date
        if isinstance(exp, list):
            exp = exp[0]
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not exp or not created:
            return 0
        if (exp - created).days / 365.0 <= 1:
            return 1
        else:
            return -1
    except Exception:
        return 0  # 未知

# ---------------------------------------------------
# 10. Favicon（简化：favicon 是否在同域）
# ---------------------------------------------------
def feat_Favicon(url, soup):
    try:
        domain = get_domain(url)
        icon_link = soup.find("link", rel=lambda x: x and "icon" in x.lower())
        if not icon_link or not icon_link.get("href"):
            return 0
        href = icon_link["href"]
        parsed = urlparse(href)
        icon_domain = parsed.netloc or domain
        if domain in icon_domain:
            return -1
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 11. port
# ---------------------------------------------------
def feat_port(url):
    parsed = urlparse(url)
    port = parsed.port
    scheme = parsed.scheme
    if port is None:
        return -1  # 默认端口
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return -1
    return 1

# ---------------------------------------------------
# 12. HTTPS_token（域名中滥用 https 字样）
# ---------------------------------------------------
def feat_HTTPS_token(url):
    domain = get_domain(url)
    scheme = get_scheme(url)
    if "https" in domain and scheme != "https":
        return 1
    return -1

# ---------------------------------------------------
# 13. Request_URL（外部资源比例）
# ---------------------------------------------------
def feat_Request_URL(url, soup):
    try:
        domain = get_domain(url)
        total = 0
        external = 0
        tags = soup.find_all(["img", "audio", "video", "embed", "iframe"])
        for tag in tags:
            src = tag.get("src")
            if not src:
                continue
            total += 1
            src_domain = urlparse(src).netloc
            if src_domain and domain not in src_domain:
                external += 1
        if total == 0:
            return -1
        ratio = external / total
        if ratio < 0.22:
            return -1
        elif 0.22 <= ratio <= 0.61:
            return 0
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 14. URL_of_Anchor
# ---------------------------------------------------
def feat_URL_of_Anchor(url, soup):
    try:
        domain = get_domain(url)
        anchors = soup.find_all("a")
        if not anchors:
            return -1
        unsafe = 0
        for a in anchors:
            href = a.get("href")
            if not href or href == "#" or href.startswith("javascript:"):
                unsafe += 1
                continue
            href_domain = urlparse(href).netloc
            if href_domain and domain not in href_domain:
                unsafe += 1
        ratio = unsafe / len(anchors)
        if ratio < 0.31:
            return -1
        elif 0.31 <= ratio <= 0.67:
            return 0
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 15. Links_in_tags（meta/script/link）
# ---------------------------------------------------
def feat_Links_in_tags(url, soup):
    try:
        domain = get_domain(url)
        tags = []
        tags += soup.find_all("meta")
        tags += soup.find_all("script")
        tags += soup.find_all("link")

        if not tags:
            return -1

        total = 0
        external = 0
        for t in tags:
            for attr in ["src", "href", "content"]:
                v = t.get(attr)
                if not v:
                    continue
                if "http" in v:
                    total += 1
                    v_domain = urlparse(v).netloc
                    if v_domain and domain not in v_domain:
                        external += 1

        if total == 0:
            return -1
        ratio = external / total
        if ratio < 0.17:
            return -1
        elif 0.17 <= ratio <= 0.81:
            return 0
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 16. SFH（表单提交地址）
# ---------------------------------------------------
def feat_SFH(url, soup):
    try:
        domain = get_domain(url)
        forms = soup.find_all("form")
        if not forms:
            return -1
        suspicious = 0
        for f in forms:
            action = f.get("action")
            if action is None or action == "" or action == "about:blank":
                return 1
            if "http" in action:
                a_domain = urlparse(action).netloc
                if domain not in a_domain:
                    suspicious += 1
        if suspicious == 0:
            return -1
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 17. Submitting_to_email
# ---------------------------------------------------
def feat_Submitting_to_email(soup):
    try:
        forms = soup.find_all("form")
        for f in forms:
            action = f.get("action", "")
            if "mailto:" in action:
                return 1
        # JS 中 mail()
        if "mailto:" in soup.get_text():
            return 1
        return -1
    except Exception:
        return 0

# ---------------------------------------------------
# 18. Abnormal_URL（WHOIS 中无该域名等，简化）
# ---------------------------------------------------
def feat_Abnormal_URL(url):
    domain = get_domain(url).split(":")[0]
    try:
        w = whois.whois(domain)
        if w.domain_name:
            return -1
        else:
            return 1
    except Exception:
        return 1

# ---------------------------------------------------
# 19. Redirect（HTTP 跳转次数）
# ---------------------------------------------------
def feat_Redirect(url):
    try:
        resp = requests.get(url, timeout=10, verify=False, allow_redirects=True)
        # resp.history 里保存了中间跳转的响应
        redirects = len(resp.history)
        if redirects <= 1:
            return -1
        elif redirects == 2:
            return 0
        else:
            return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 20. on_mouseover（JS）
# ---------------------------------------------------
def feat_on_mouseover(soup):
    try:
        scripts = soup.find_all("script")
        for s in scripts:
            txt = s.get_text().lower()
            if "onmouseover" in txt and ("window.status" in txt or "location.href" in txt):
                return 1
        return -1
    except Exception:
        return 0

# ---------------------------------------------------
# 20. RightClick（禁用右键）
# ---------------------------------------------------
def feat_RightClick(soup):
    try:
        scripts = soup.find_all("script")
        for s in scripts:
            txt = s.get_text().lower()
            if "event.button==2" in txt or "contextmenu" in txt:
                return -1
        body = soup.find("body")
        if body and ("contextmenu" in body.attrs or "oncontextmenu" in body.attrs):
            return 1
        return -1
    except Exception:
        return 0

# ---------------------------------------------------
# 21. popUpWidnow（弹窗）
# ---------------------------------------------------
def feat_popUpWidnow(soup):
    try:
        scripts = soup.find_all("script")
        for s in scripts:
            txt = s.get_text().lower()
            if "alert(" in txt or "window.open(" in txt:
                return 1
        return -1
    except Exception:
        return 0

# ---------------------------------------------------
# 22. Iframe
# ---------------------------------------------------
def feat_Iframe(soup):
    try:
        iframes = soup.find_all("iframe")
        if not iframes:
            return -1
        # 简单：存在 iframe 就认为可疑
        return 1
    except Exception:
        return 0

# ---------------------------------------------------
# 23. age_of_domain（WHOIS，简化）
# ---------------------------------------------------
def feat_age_of_domain(url):
    domain = get_domain(url).split(":")[0]
    try:
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if not created:
            return 0
        age_months = (datetime.now() - created).days / 30.0
        if age_months < 6:
            return 1
        else:
            return -1
    except Exception:
        return 0

# ---------------------------------------------------
# 24. DNSRecord
# ---------------------------------------------------
def feat_DNSRecord(url):
    domain = get_domain(url).split(":")[0]
    try:
        dns.resolver.resolve(domain, "A")
        return -1
    except Exception:
        return 1

# ---------------------------------------------------
# 25. web_traffic（无Alexa等API时：不再默认未知=0）
# 规则：
# - 有可用的“tranco排名文件”就按排名分段
# - 没有排名数据：默认返回 1（不因缺数据扣分）
# ---------------------------------------------------

@lru_cache(maxsize=20000)
def _load_tranco_map():
    """
    可选：如果你放一个 Tranco top list 文件到 data/tranco_top1m.csv
    格式：rank,domain   (例如：1,google.com)
    就能启用“流量/热度”近似判断。
    """
    candidates = [
        os.path.join(os.path.dirname(__file__), "data", "tranco_top1m.csv"),
        os.path.join(os.path.dirname(__file__), "tranco_top1m.csv"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return None

    m = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            rank_s, dom = line.split(",", 1)
            dom = dom.strip().lower()
            try:
                m[dom] = int(rank_s)
            except Exception:
                continue
    return m

def feat_web_traffic(url):
    domain = get_domain(url).split(":")[0].lower()
    tranco = _load_tranco_map()
    if not tranco:
        return -1  # 关键：无数据时不扣分，避免模型因“全0”偏向钓鱼

    rank = tranco.get(domain)
    if rank is None:
        return 0  # 不在榜单：信息不足，给0而不是-1
    if rank <= 100000:
        return -1
    elif rank <= 1000000:
        return 0
    else:
        return 1


# ---------------------------------------------------
# 26. Page_Rank（无搜索引擎API：用“tranco排名”近似）
# 规则：同上，越热门越像正常
# ---------------------------------------------------
def feat_Page_Rank(url):
    domain = get_domain(url).split(":")[0].lower()
    tranco = _load_tranco_map()
    if not tranco:
        return -1  # 无数据时不扣分

    rank = tranco.get(domain)
    if rank is None:
        return 0
    if rank <= 200000:
        return -1
    elif rank <= 1000000:
        return 0
    else:
        return 1


# ---------------------------------------------------
# 27. Google_Index（不爬谷歌：用站点自身“noindex”信号判断）
# 规则：
# - 页面显式声明 noindex / X-Robots-Tag:noindex => -1
# - 否则 => 1（不再默认0）
# ---------------------------------------------------
def feat_Google_Index(url):
    try:
        resp = requests.get(url, timeout=10, verify=False, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0"
        })
        # HTTP头 noindex
        xrt = resp.headers.get("X-Robots-Tag", "")
        if "noindex" in xrt.lower():
            return 1

        soup = BeautifulSoup(resp.text or "", "html.parser")
        meta = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "robots"})
        if meta and meta.get("content") and "noindex" in meta["content"].lower():
            return 1

        return -1
    except Exception:
        return 0  # 真访问失败时才给0


# ---------------------------------------------------
# 28. Links_pointing_to_page（不做外部反链API：改为“站内引用强度”近似）
# 规则：
# - 能抓到页面：统计“内部链接数量”
#   内部链接很多 => 更像正常（1）
#   少量 => 0
#   几乎没有且页面很像落地页 => -1（谨慎）
# - 抓不到页面 => 0
# ---------------------------------------------------
def feat_Links_pointing_to_page(url):
    try:
        domain = get_domain(url).split(":")[0].lower()
        resp = requests.get(url, timeout=10, verify=False, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0"
        })
        soup = BeautifulSoup(resp.text or "", "html.parser")
        anchors = soup.find_all("a")
        if not anchors:
            return 0

        internal = 0
        for a in anchors:
            href = a.get("href") or ""
            if not href:
                continue
            d = urlparse(href).netloc.lower()
            # 相对链接 or 同域
            if (not d) or (domain in d):
                internal += 1

        if internal >= 15:
            return -1
        elif internal >= 5:
            return 0
        else:
            # 内链极少：谨慎给 1（但不“一刀切”）
            return 1
    except Exception:
        return 0


# ---------------------------------------------------
# 29. Statistical_report（不默认未知=0，支持本地黑名单）
# 规则：
# - 若存在 blacklist.txt（一行一个domain），命中 => -1
# - 未命中或无文件 => 1（不扣分）
# ---------------------------------------------------
@lru_cache(maxsize=1)
def _load_blacklist():
    candidates = [
        os.path.join(os.path.dirname(__file__), "blacklist.txt"),
        os.path.join(os.path.dirname(__file__), "data", "blacklist.txt"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return set()

    s = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            d = line.strip().lower()
            if d and not d.startswith("#"):
                s.add(d)
    return s

def feat_Statistical_report(url):
    domain = get_domain(url).split(":")[0].lower()
    bl = _load_blacklist()
    if not bl:
        return -1
    return 1 if domain in bl else -1


# ---------------------------------------------------
# 主函数：给定 URL，返回 29 个特征的 dict
# ---------------------------------------------------
def extract_features(url):
    features = [0]*30

    # 尝试获取网页内容
    soup = None
    try:
        resp = requests.get(url, timeout=10, verify=False)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        # 无法访问页面时，和内容相关的特征用 None / 0
        soup = BeautifulSoup("", "html.parser")

    features[0] = feat_having_IP_Address(url)
    features[1] = feat_URL_Length(url)
    features[2] = feat_Shortining_Service(url)
    features[3] = feat_having_At_Symbol(url)
    features[4] = feat_double_slash_redirecting(url)
    features[5] = feat_Prefix_Suffix(url)
    features[6] = feat_having_Sub_Domain(url)
    features[7] = feat_SSLfinal_State(url)
    features[8] = feat_Domain_registeration_length(url)
    features[9] = feat_Favicon(url, soup)
    features[10] = feat_port(url)
    features[11] = feat_HTTPS_token(url)
    features[12] = feat_Request_URL(url, soup)
    features[13] = feat_URL_of_Anchor(url, soup)
    features[14] = feat_Links_in_tags(url, soup)
    features[15] = feat_SFH(url, soup)
    features[16] = feat_Submitting_to_email(soup)
    features[17] = feat_Abnormal_URL(url)
    features[18] = feat_Redirect(url)
    features[19] = feat_on_mouseover(soup)
    features[20] = feat_RightClick(soup)
    features[21] = feat_popUpWidnow(soup)
    features[22] = feat_Iframe(soup)
    features[23] = feat_age_of_domain(url)
    features[24] = feat_DNSRecord(url)
    features[25] = feat_web_traffic(url)
    features[26] = feat_Page_Rank(url)
    features[27] = feat_Google_Index(url)
    features[28] = feat_Links_pointing_to_page(url)
    features[29] = feat_Statistical_report(url)

    return features
