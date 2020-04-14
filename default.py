#!/usr/bin/python
# -*- coding: utf-8 -*-
# Eviloid, 22.08.2019

import os, urllib, sys, urllib2, re, cookielib, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import CommonFunctions

import sqlite3 as sql
import moonwalk as moon

PLUGIN_NAME = 'FanSerials'

common = CommonFunctions
common.plugin = PLUGIN_NAME

try:handle = int(sys.argv[1])
except:pass

addon = xbmcaddon.Addon(id='plugin.video.evld.fanserials.tv')

Pdir = addon.getAddonInfo('path')
icon = xbmc.translatePath(os.path.join(Pdir, 'icon.png'))
fanart = xbmc.translatePath(os.path.join(Pdir, 'fanart.jpg'))
db = xbmc.translatePath(os.path.join(Pdir, 'serials.db'))

BASE_URL = 'http://' + addon.getSetting('host')
IMG_URL_PATTERN = BASE_URL.strip('/') + '/storage/serials/%s/v2/%s.jpg'
ART_URL_PATTERN = BASE_URL.strip('/') + '/storage/serials/%s/h2/%s.jpg'


sound_mode = int(addon.getSetting('sound'))

proxy = ''

if addon.getSetting('UseProxy') == 'true':
    proxy = addon.getSetting('Proxy')

def main_menu():
    add_item('[B]Сериалы[/B]', params={'mode':'abc', 't':'0'}, fanart=fanart, isFolder=True)
    add_item('[B]Аниме[/B]', params={'mode':'abc', 't':'2'}, fanart=fanart, isFolder=True)
    add_item('[B]Мультсериалы[/B]', params={'mode':'abc', 't':'1'}, fanart=fanart, isFolder=True)
#    add_item('[B]Дорамы[/B]', params={'mode':'abc', 't':'5'}, fanart=fanart, isFolder=True)
    add_item('[B]Документальное[/B]', params={'mode':'abc', 't':'3'}, fanart=fanart, isFolder=True)
    add_item('[B]ТВ-шоу[/B]', params={'mode':'abc', 't':'6'}, fanart=fanart, isFolder=True)
    add_item('[B]Новые сериалы[/B]', params={'mode':'new_serials'}, fanart=fanart, isFolder=True)

    # новинки
    html = get_html(BASE_URL + '/new/')

    container = common.parseDOM(html, 'div', attrs={'id':'episode_list'})
    episodes = common.parseDOM(container, 'div', attrs={'class':'item-serial'})

    if len(episodes) > 0:
        for episode in episodes:

            img = common.parseDOM(episode, 'div', attrs={'class':'field-img'}, ret='style')[0]
            img = img[23:-3]

            desc = common.parseDOM(episode, 'div', attrs={'class':'field-description'})[0]
            desc = common.parseDOM(desc, 'a')[0]
            plot = common.replaceHTMLCodes(desc)

            desc = common.parseDOM(episode, 'div', attrs={'class':'field-title'})[0]
            desc = common.parseDOM(desc, 'a')[0]
            title = '[COLOR=yellow]%s[/COLOR] [COLOR=gray]%s[/COLOR]' % (common.replaceHTMLCodes(desc), plot)

            u = common.parseDOM(episode, 'a', ret='href')[0]
            menu = [('Все серии', 'Container.Update("%s?mode=jump&u=%s")' % (sys.argv[0], urllib.quote_plus(u)))]

            add_item(title, params={'mode':'episode', 'u':u}, plot=plot, thumb=img, fanart=fanart, isFolder=sound_mode==1, isPlayable=sound_mode==0, menu=menu)

    add_item('[B]Поиск[/B]', params={'mode':'search'}, fanart=fanart, icon='DefaultAddonsSearch.png', isFolder=True)

    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle)


def get_description(url, id, force=False):
    plot = db_restore(id)

    if plot is None or force:
        html = get_html('%s/%s/' % (BASE_URL, url))
        desc = common.parseDOM(html, 'div', attrs={'class':'body', 'itemprop':'description'})
        if len(desc) > 0:
            plot = common.stripTags(desc[0])
        else:
            plot = ''

        db_store(id, plot)

    return plot


def search(params):
    keyword = ''

    kbd = xbmc.Keyboard('', 'Поиск:')
    kbd.doModal()
    if kbd.isConfirmed():
        keyword = kbd.getText()

    if keyword:
        html = get_html('%s/search/' % BASE_URL, params={'query':keyword})

        serials = common.parseDOM(html, 'div', attrs={'class':'item-search-serial'})

        if len(serials) > 0:
            for serial in serials:
                img = common.parseDOM(serial, 'img', ret='src')[0].replace('/v1','/v2')
                title = common.parseDOM(serial, 'img', ret='alt')[0]
                u = common.parseDOM(serial, 'a', ret='href')[0].strip('/')
                desc = common.parseDOM(serial, 'p', attrs={'class':'textailor'})[0]

                add_item(title, params={'mode':'seasons', 'u':u}, poster=img, fanart=fanart, plot=desc, isFolder=True)

        xbmcplugin.setContent(handle, 'tvshows')
        xbmcplugin.endOfDirectory(handle)


def jump_to_seasons(params):
    url = BASE_URL + params['u']
    html = get_html(url)

    container = common.parseDOM(html, 'ul', attrs={'class':'breadcrumbs'})
    hrefs = common.parseDOM(container, 'a', attrs={'itemprop':'item'}, ret='href')

    if len(hrefs) > 1:
        params['mode'] = 'seasons'
        params['u'] = hrefs[1].strip('/')
        show_seasons(params)


def new_serials(params):
    html = get_html('%s/new-serials/' % BASE_URL)

    container = common.parseDOM(html, 'div', attrs={'class':'block-new-serials[ a-z0-9-]*'})

    serials = common.parseDOM(container, 'div', attrs={'class':'new-serials-poster'})
    hrefs = common.parseDOM(container, 'a', attrs={'class':'field-poster'}, ret='href')

    if len(serials) > 0:
        for i, serial in enumerate(serials):
            img = common.parseDOM(serial, 'img', ret='src')[0].replace('/v1', '/v2')
            title = common.parseDOM(serial, 'img', ret='alt')[0]
            ids = common.parseDOM(serial, 'a', attrs={'class':'popover-btn'}, ret='data-serial-id')
            u = hrefs[i].strip('/')
            desc = get_description(u, ids[0])
            id = ids[0][-4:-20:-1][::-1]
            id = id if id else '0'
            fan = ART_URL_PATTERN % (id, u)

            menu = [('Обновить описание', 'Container.Update("%s?mode=description&u=%s&id=%s", False)' % (sys.argv[0], urllib.quote_plus(u), ids[0]))]
            add_item(title, params={'mode':'seasons', 'u':u, 'i':ids[0]}, poster=img, fanart=fan, plot=desc, isFolder=True, menu=menu)

    xbmcplugin.setContent(handle, 'tvshows')
    xbmcplugin.endOfDirectory(handle)


def ABClist(params):
    t = params.get('t', '0')

    html = json.loads(get_html('%s/alphabet/%s/' % (BASE_URL, t)))['alphabet']

    alphabet = common.parseDOM(html, 'ul', attrs={'id':'letters-list'})
    abc = common.parseDOM(alphabet, 'a')
    hrefs = common.parseDOM(alphabet, 'a', ret='href')

    for i, letter in enumerate(abc):
        title = letter
        add_item(title, params={'mode':'serials', 't':t, 'letter':hrefs[i][1:]}, fanart=fanart, isFolder=True)

    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle)


def show_serials(params):
    t = params.get('t', '0')

    html = json.loads(get_html('%s/alphabet/%s/' % (BASE_URL, t)))['alphabet']

    alphabet = common.parseDOM(html, 'div', attrs={'class':'literal', 'id':urllib.unquote_plus(params['letter'])})
    serials = common.parseDOM(alphabet, 'li', attrs={'class':'literal__item not-loaded'})
    ids = common.parseDOM(alphabet, 'li', attrs={'class':'literal__item not-loaded'}, ret='data-id')

    for i, serial in enumerate(serials):
        title = common.parseDOM(serial, 'a')[0]

        u = common.parseDOM(serial, 'a', ret='href')[0].strip('/')

        id = ids[i][-4:-20:-1][::-1]
        id = id if id else '0'

        img = IMG_URL_PATTERN % (id, u)
        fan = ART_URL_PATTERN % (id, u)

        desc = get_description(u, ids[i])

        menu = [('Обновить описание', 'Container.Update("%s?mode=description&u=%s&id=%s", False)' % (sys.argv[0], urllib.quote_plus(u), ids[i]))]
        add_item(title, params={'mode':'seasons', 'u':u, 'i':ids[i]}, poster=img, fanart=fan, plot=desc, isFolder=True, menu=menu)

    xbmcplugin.setContent(handle, 'tvshows')
    xbmcplugin.endOfDirectory(handle)


def show_seasons(params):
    url = '%s/%s/' % (BASE_URL, params['u'])

    html = get_html(url)

    params['i'] = params.get('i', common.parseDOM(html, 'div', attrs={'class':'serial-item-rating clickonce'}, ret='data-id')[0])

    id = params['i'][-4:-20:-1][::-1]
    id = id if id else '0'

    img = IMG_URL_PATTERN % (id, params['u'])
    fan = ART_URL_PATTERN % (id, params['u'])
    plot = get_description(params['u'], params['i'])

    container = common.parseDOM(html, 'div', attrs={'itemprop':'containsSeason'})
    seasons = common.parseDOM(container[0] if len(container) > 1 else container, 'li')

    if len(seasons) > 0:
        for season in seasons:
            title = 'Сезон ' + common.parseDOM(season, 'span', attrs={'itemprop':'seasonNumber'})[0].encode('utf8')

            u = common.parseDOM(season, 'a', ret='href')[0].strip('/')

            add_item(title, params={'mode':'season', 'u':u}, plot=plot, poster=img, fanart=fan, isFolder=True)
    else:
        # moonwalk
        data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
        if data:
            o = 0 if sound_mode == 0 else int(params.get('o', -1))
            if o == -1:
                show_sounds(url, params)
                return

            data = json.loads(data.group(1))
            seasons = sorted(data[o]['seasons'])
            for season in seasons:
                title = 'Сезон ' + str(season)
                add_item(title, params={'mode':'season', 'u':params['u'], 's':season, 'o':o}, plot=plot, poster=img, fanart=fan, isFolder=True)

    if len(seasons) == 0:
        show_season(params)
        return

    xbmcplugin.setContent(handle, 'seasons')
    xbmcplugin.endOfDirectory(handle)


def show_sounds(url, params):

    html = get_html(url)

    playable = '.html' in url

    data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
    if data:
        data = json.loads(data.group(1))
        for i, player in enumerate(data):
            params['o'] = i
            add_item(player['name'], params, icon=icon, fanart=fanart, isPlayable=playable, isFolder= not playable)

        xbmcplugin.setContent(handle, 'videos')
        xbmcplugin.endOfDirectory(handle)


def show_season(params):

    page = int(params.get('page', 1))

    url = '%s/%s/page/%s/' % (BASE_URL, params['u'], page) if page > 1 else '%s/%s/' % (BASE_URL, params['u'])
    html = get_html(url, {'order':'asc'})

    container = common.parseDOM(html, 'ul', attrs={'id':'episode_list'})
    episodes = common.parseDOM(container, 'div', attrs={'class':'item-serial'})

    if len(episodes) > 0:
        for episode in episodes:

            img = common.parseDOM(episode, 'div', attrs={'class':'field-img'}, ret='style')[0]
            img = img[23:-3]

            desc = common.parseDOM(episode, 'div', attrs={'class':'field-description'})[0]
            desc = common.parseDOM(desc, 'a')[0]
            title = common.replaceHTMLCodes(desc)
            u = common.parseDOM(episode, 'a', ret='href')[0]

            add_item(title, params={'mode':'episode', 'u':u}, thumb=img, fanart=fanart, isFolder=sound_mode==1, isPlayable=sound_mode==0)

        # pagination
        p = common.parseDOM(html, 'span', attrs={'class':'icon-chevron-thin-right'})
        if len(p) > 0:
            params['page'] = page + 1
            add_item('Далее > %d' % params['page'], params=params, fanart=fanart, isFolder=True)

    else:
        # moonwalk
        data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
        if data:
            o = int(params.get('o', 0))
            data = json.loads(data.group(1))
            episodes = sorted(data[o]['seasons'][params['s']]['episodes'])
            for episode in episodes:
                title = 'Серия ' + str(episode)
                add_item(title, params={'mode':'episode', 'u':'/%s/' % params['u'], 's':params['s'], 'e':episode, 'o':o}, icon=icon, fanart=fanart, isPlayable=True)

    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle)


def play_episode(params):

    url = BASE_URL + params['u']

    o = 0 if sound_mode == 0 else int(params.get('o', -1))

    if o == -1:
        show_sounds(url, params)
        return

    html = get_html(url)

    block = common.parseDOM(html, 'div', attrs={'class':'limited-block-content'})
    if block:
        content = common.parseDOM(block, 'div', attrs={'class':'heading'})[0]
        xbmcgui.Dialog().notification(PLUGIN_NAME, content, icon, 2000, True)
        return

    purl = ''
    surls = []

    data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
    if data:
        data = json.loads(data.group(1))
        iframe = data[o]['player']

        if 'moonwalk' in iframe:
            if 'e' in params.keys():
                iframe = re.search(r"(.*)\?", iframe)
                if iframe:
                    src = '%s?season=%s&episode=%s&nocontrols=1' % (iframe.group(1), params['s'], params['e'])
            else:
                src = iframe

            key = addon.getSetting('key')
            iv = addon.getSetting('iv')

            data = moon.get_url(src, url, key, iv)
            if 'subtitles' in data.keys():
                if data['subtitles']:
                    surl = data['subtitles']['master_vtt']
                    if surl[:2] == '//': surl = src.split("//")[0] + surl
                    surls.append(surl)

            if 'm3u8' in data.keys():
                purl = data['m3u8']

        elif 'vio.to' in iframe:
            html = get_html(iframe)
            s = re.search(r"link:.?'(.*?)'", html)
            if s:
                html = get_html(s.group(1))
                s = re.findall(r"{url:.?'(.*?)'", html, re.I and re.S)
                if s:
                    item = xbmcgui.ListItem(path='https:' + s[-1] + '|referer=https://vio.to/')
                    xbmcplugin.setResolvedUrl(handle, True, item)

        elif 'stormo.tv' in iframe:
            html = get_html(iframe)
            s = re.search(r'file:"(\[.*?\](.*?)\/[,\"\n\r]+){1,}', html)
            if s:
                item = xbmcgui.ListItem(path=s.group(2))
                xbmcplugin.setResolvedUrl(handle, True, item)

        elif 'ok.ru' in iframe:
            html = get_html(re.sub(r'^//', 'https://', iframe))
            s = re.search(r'data-module="OKVideo" data-options="(.*?)" data-player-container-id', html)
            if s:
                data = s.group(1)
                data = data.replace('\\\\', '\\')
                data = data.replace('&quot;', '"')
                data = data.replace('\\u0026', '&')
                data = data.replace('\\"', '"')

                url = re.search(r'"hlsManifestUrl":"(.*?)",', data).group(1)
                item = xbmcgui.ListItem(path=url)
                xbmcplugin.setResolvedUrl(handle, True, item)

        else:
            html = get_html(iframe)
            s = re.search(r'"hls":"(.*?\.m3u8)', html)
            if s:
                purl = s.group(1).replace(r'\/', '/').replace(r'\r', '').replace(r'\n', '')

            s = re.search(r'data-ru_subtitle="(.*?)"', html)
            if s:
                surls.append(fix_sub(s.group(1)))

            s = re.search(r'data-en_subtitle="(.*?)"', html)
            if s:
                surls.append(fix_sub(s.group(1), 'en_'))

        if purl:
            item = xbmcgui.ListItem(path=purl)
            surls = [i for i in surls if i]
            if surls:
                item.setSubtitles(surls)
            else:
                item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            xbmcplugin.setResolvedUrl(handle, True, item)


def fix_sub(surl, prefix='ru_'):

    if surl:
        vtt = get_html(surl)

        fixed = []

        first = True

        if vtt:
            for i, line in enumerate(vtt.split('\n')):
                if i == 0 and line != 'WEBVTT':
                    break
                if re.search(r'\d+:\d+:\d+.\d+', line) and first:
                    break
                s = re.findall(r'((\d+):)*(\d+:\d+\.\d+)', line)
                if s:
                    fixed.append('%s:%s --> %s:%s' % (s[0][1].zfill(2), s[0][2], s[1][1].zfill(2), s[1][2]))
                    first = False
                else:
                    fixed.append(line)
            else:
                temp_name = os.path.join(xbmc.translatePath('special://masterprofile'), prefix + 'fsubs.vtt')
                temp_file = open(temp_name, "w")
                temp_file.write('\n'.join(fixed))
                temp_file.close()
                surl = temp_name
    return surl


def get_html(url, params={}, post={}, noerror=True):
    headers = {'Referer':url, 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'}

    html = ''

    try:
        request = urllib2.Request('%s?%s' % (url, urllib.urlencode(params)), headers=headers)

        if proxy:
            ph = urllib2.ProxyHandler({'https':proxy, 'http':proxy})
            opener = urllib2.build_opener(ph)
            conn = opener.open(request)
        else:
            conn = urllib2.urlopen(request)

        html = conn.read()
        conn.close()

    except urllib2.HTTPError, err:
        if not noerror:
            html = err.code

        if err.code == 404:
            xbmc.log('Fanserials: Not found ' + url.encode('utf-8'), xbmc.LOGWARNING)
        elif err.code == 403:
            xbmc.log('Fanserials: Forbidden ' + url.encode('utf-8'), xbmc.LOGWARNING)
        else:
            pass

    return html 


def add_item(title, params={}, icon='', banner='', fanart='', poster='', thumb='', plot='', isFolder=False, isPlayable=False, url=None, menu=None):
    if url is None: url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))

    item = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb)
    item.setInfo(type='video', infoLabels={'title': title, 'plot': plot})

    if isPlayable:
        item.setProperty('isPlayable', 'true')
        item.setProperty('mediatype', 'video')

    if banner != '':
        item.setArt({'banner': banner})
    if fanart != '':
        item.setArt({'fanart': fanart})
    if poster != '':
        item.setArt({'poster': poster})
    if thumb != '':
        item.setArt({'thumb': thumb})

    if menu:
        item.addContextMenuItems(menu)

    xbmcplugin.addDirectoryItem(handle, url=url, listitem=item, isFolder=isFolder)


connect = sql.connect(database=db)
cursor = connect.cursor()

def db_store(n, plot):
    plot = plot.replace("'","XXCC").replace('"',"XXDD")
    id = "n" + n
    try:
        cursor.execute('CREATE TABLE IF NOT EXISTS {0} (plot VARCHAR(512), i VARCHAR(1));'.format(id))
        connect.commit()
    except:
        pass 
    else:
        cursor.execute('DELETE FROM {0};'.format(id))
        connect.commit()
        cursor.execute('INSERT INTO {0} (plot, i) VALUES ("{1}", "1");'.format(id, plot.encode('utf-8')))
        connect.commit()

def db_restore(n):
    id = "n" + n
    plot = None
    try:
        cursor.execute('SELECT plot FROM {0};'.format(id))
        connect.commit()
        data = cursor.fetchall()

        if len(data) > 0:
            plot = data[0][0].replace("XXCC","'").replace("XXDD",'"')
    except:
        pass

    return plot


params = common.getParameters(sys.argv[2])

mode = params['mode'] = params.get('mode', '')

if mode == '':
    main_menu()

if mode == 'search':
    search(params)

if mode == 'jump':
    jump_to_seasons(params)

if mode == 'description':
    get_description(params['u'], params['id'], True)
    xbmcplugin.endOfDirectory(handle, False, True, False)
    xbmc.executebuiltin('Container.Refresh')

if mode == 'new_serials':
    new_serials(params)

if mode == 'abc':
    ABClist(params)

if mode == 'serials':
    show_serials(params)

if mode == 'seasons':
    show_seasons(params)

if mode == 'season':
    show_season(params)

if mode == 'episode':
    play_episode(params)

if mode == 'cleancache':
    from tccleaner import TextureCacheCleaner as tcc
    tcc().remove_like('%fanimg.site%', True)
    tcc().remove_like('%fanserials%', True)

if mode == 'updatekeys':
    res = common.fetchPage({'link':'https://raw.githubusercontent.com/WendyH/PHP-Scripts/master/moon4crack.ini'})
    if res['content']:
        data = {k.strip(): v.strip().strip('"') for i in [l for l in res['content'].splitlines() if l.strip() != ''] for k, v in [i.split('=')]}
        addon.setSetting('key', data['key'])
        addon.setSetting('iv', data['iv'])
        xbmcgui.Dialog().notification(PLUGIN_NAME, 'Ключи обновлены', icon, 2000, False)

connect.close()
