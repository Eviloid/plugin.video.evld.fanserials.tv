#!/usr/bin/python
# -*- coding: utf-8 -*-
# Eviloid, 24.08.2019

import binascii, base64, urllib, urllib2
import re, json

from Cryptodome.Cipher import AES

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'

def encrypt(data, keyhex, ivhex):
    try:
        key = binascii.unhexlify(keyhex)
        def pad(s): return s+chr(16-len(s) % 16)*(16-len(s) % 16)
        iv = binascii.unhexlify(ivhex)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_64 = base64.standard_b64encode(
                cipher.encrypt(pad(data).encode("utf-8")))
        return encrypted_64
    except:
        pass

    return ''


def get_data(frame_url, referer):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': referer,
                'User-Agent': USER_AGENT}
    data = []

    html = ''
    conn = urllib2.urlopen(urllib2.Request(frame_url, headers=headers))
    html = conn.read()
    conn.close()

    s = re.search(r'var video_balancer_options = ({.*?});', html, re.I and re.S)
    if s:
        a = s.group(1).replace(r"'", r'"')
        a = re.sub(r'([^\w\"\.])(\w+)\s*:', r'\1"\2":', a)
        a = re.sub(r'("\w+")\s*:\s*([\w\.]+)', r'\1:"\2"', a)
        a = re.sub(r'(,\s*)(})', r'\2', a)

        data = json.loads(a)

    return data


def get_url(frame_url, referer, key='', iv=''):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': referer,
                'User-Agent': USER_AGENT}

    data = get_data(frame_url, referer)

    if len(data) > 0:
        payload = '{"a":%s,"b":%s,"c":false,"d":"moonwalk","e":"%s","f":"%s"}' % (data['partner_id'], data['domain_id'], data['video_token'], USER_AGENT)

        crypted = encrypt(payload, key, iv) 

        post_url = data['proto'] + data['host'] + '/vs'

        params = {}

        post = {'q':crypted, 'ref':data['ref']}

        html = ''
        conn = urllib2.urlopen(urllib2.Request(post_url, urllib.urlencode(post), headers=headers))
        html = conn.read()
        conn.close()

        if 'm3u8' in html:
            data = json.loads(html)
            return data

    return []
