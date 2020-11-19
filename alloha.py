# -*- coding: utf-8 -*-

import urllib, urllib2, urlparse
import re, json, base64

try:
    from Cryptodome.Cipher import AES
except ImportError:
    from Crypto.Cipher import AES

from hashlib import md5

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'


class AllohaBalancer(object):
    file3_separator = '##'

    def __init__(self, url):
        self.url = url
        self.season = None
        self.episode = None
        self.translation = None

    def make_url(self):
        parsed_url = urlparse.urlsplit(self.url)
        params = dict(urlparse.parse_qsl(parsed_url.query))

        if self.season:
            params.update({'season': self.season})

        if self.episode:
            params.update({'episode': self.episode})

        if self.translation:
            params.update({'translation': self.translation})

        return '%s://%s%s?%s' % (parsed_url.scheme, parsed_url.netloc, parsed_url.path, urllib.urlencode(params))

    def fetch(self):
        url = self.make_url()

        headers = {'UserAgent':USER_AGENT, 'Referer':self.url}

        request = urllib2.Request(url, headers=headers)
        conn = urllib2.urlopen(request)

        result = conn.read()
        conn.close()

        return result

    def _get_data(self, type):
        result = []
        html = self.fetch()

        data = re.findall(r'<div class="baron__scroller">(.*?)</div>', html)
        for d in data:
            if type in d:
                result = re.findall(r'%s="(\d+)".+?>(.*?)</button' % type, d)

        return result

    def get_seasons(self):
        result = []
        seasons = self._get_data('data-seasons')
        for s in seasons:
            result.append({'id':s[0], 'title': s[1]})
        return result

    def get_episodes(self):
        result = []
        episodes = self._get_data('data-episode')
        for e in episodes:
            result.append({'id':e[0], 'title': e[1]})
        return result

    def get_translations(self):
        result = []
        translations = self._get_data('data-translation')
        for t in translations:
            result.append({'id':t[0], 'title': t[1]})
        return result

    @staticmethod
    def __decode_fd2(x):
        a = x[2:]

        # bk0, bk1...bk4
        bk = ['?|;^^|*>*>??>^|^<|>|?!*№(|;!?^№>', '?;>)!(*;||>|*<^|*|^*`>?|(|*>||~][|>|*^*', '<`^*`*>|№**№]?[*;||>|*№;^*`№*>', '|[>*№>^?[;||>|*<**№]||^<**|', ';!?^№>*^*`||^<*№||^*`^**|№*~][|>|']

        for k in reversed(bk):
            a = a.replace(AllohaBalancer.file3_separator + base64.standard_b64encode(k), '')

        try:
            result = base64.standard_b64decode(a)
        except:
            result = ''

        return result

    @staticmethod
    def __decode_fd3(ciphertext, password, iv, salt):
        def unpad(x):return x[:-ord(x[len(x) - 1:])]
        def derive(password, salt, key_length=32):
            d = d_i = ''
            while len(d) < key_length:
                d_i = md5(d_i + password + salt).digest()
                d += d_i
            return d[:key_length]

        key = derive(password, salt.decode('hex'))
        cipher = AES.new(key, AES.MODE_CBC, iv.decode('hex'))
        return unpad(cipher.decrypt(base64.b64decode(ciphertext)))

    @staticmethod
    def __decode_packed(p, a, c, k, e, d):
        def to_base(n, b):
            return '0' if not n else to_base(n//b, b).lstrip('0') + '0123456789abcdefghijklmnopqrstuvwxyz'[n%b]

        k = k.split('|')

        def decode_e(c):
            return ('' if c < a else decode_e(c//a)) + (chr(c % a + 29) if c % a > 35 else to_base(c % a, 36))

        while c > 0:
            c = c - 1
            d[decode_e(c)] = k[c] or decode_e(c)

        if d['0']:
            p = re.sub(r'\b\w+\b', lambda x: d[x.group()], p)

        return p

    @staticmethod
    def __decode_hunter(h, u, n, t, e, r):
        def decode(d, e, f):
            g = list('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/')
            h = g[:e]
            i = g[:f]
            j = list(d)
            j.reverse()

            a = 0
            for c, b in enumerate(j):
                if b in h:
                    a = a + h.index(b) * pow(e, c) 

            j = a
        
            k = ''
            while j > 0:
                k = i[j % f] + k
                j = (j - (j % f)) / f

            return int(k or 0)

        r = ''
        s = ''
        for i in list(h):
            if i != n[e]:
                s = s + i
            else:
                for j, m in enumerate(list(n)):
                    s = s.replace(m, str(j))
                r = r + chr(decode(s, e, 10) - t)
                s = ''

        return r


    @classmethod
    def _get_url(cls, html):
        result = ''

        s = re.search(r'= new Playerjs\("(.+?)"', html)

        if s:
            if s.group(1)[:2] == '#9':
                data = cls.__decode_fd2(s.group(1).replace(r'\/', '/'))
                data = json.loads(data)

                data = data['file'].split(cls.file3_separator)

                # get password
                while True:
                    decoded = False

                    p = re.search(r'escape\(r\)\)}\("(.+?)",(\d+),"(.+?)",(\d+).*,(\d+),(\d+)\)\)', html)
                    if p:
                        html = cls.__decode_hunter(p.group(1), int(p.group(2)), p.group(3), int(p.group(4)), int(p.group(5)), p.group(6))
                        decoded = True

                    p = re.search(r'function\(p,a,c,k,e,d\).+return p}\((\'.*?\'),(\d+),(\d+),\'(.*?\')', html)
                    if p:
                        html = cls.__decode_packed(p.group(1), int(p.group(2)), int(p.group(3)), p.group(4), 0, {})
                        decoded = True

                    html = re.sub(r"(\w)'\|", "\\1\\|", html.decode('string-escape'))

                    v = re.findall(r'=\s*["\'](.*?)[\'"]', html)

                    if v and len(v) == 7 and v[4]:
                        password = v[4]
                        break
                    else:
                        password = ''
                        if not decoded:
                            break

                if password:
                    result = cls.__decode_fd3(data[0][2:], password, data[1], data[2]).replace(r'\/', '/')

        return result.strip('"')


    def get_video(self):
        html = self.fetch()
        return AllohaBalancer._get_url(html)

