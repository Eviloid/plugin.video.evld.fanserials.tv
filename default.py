#!/usr/bin/python
# -*- coding: utf-8 -*-
# Eviloid, 22.08.2019

import os, urllib, sys, urllib2, re, cookielib, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import CommonFunctions

import sqlite3 as sql
import moonwalk as moon

PLUGIN_NAME   = 'FanSerials'

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
IMG_URL_PATTERN = 'http://fanimg.site/serials/%s/v2/%s.jpg'
ART_URL_PATTERN = 'http://fanimg.site/serials/%s/h2/%s.jpg'

def main_menu():
    add_item('[B]Сериалы[/B]', params={'mode':'abc', 't':'0'}, fanart=fanart, isFolder=True)
    add_item('[B]Аниме[/B]', params={'mode':'abc', 't':'2'}, fanart=fanart, isFolder=True)
    add_item('[B]Мультсериалы[/B]', params={'mode':'abc', 't':'1'}, fanart=fanart, isFolder=True)
    add_item('[B]Дорамы[/B]', params={'mode':'abc', 't':'5'}, fanart=fanart, isFolder=True)
    add_item('[B]Документальное[/B]', params={'mode':'abc', 't':'3'}, fanart=fanart, isFolder=True)
    add_item('[B]ТВ-шоу[/B]', params={'mode':'abc', 't':'6'}, fanart=fanart, isFolder=True)

    # новинки
    html = get_html(BASE_URL + '/new/')

    container = common.parseDOM(html, 'div', attrs={'id':'"episode_list"'})
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

            add_item(title, params={'mode':'episode', 'u':u}, plot=plot, thumb=img, fanart=fanart, isPlayable=True)    

    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle)


def get_description(url, id):
    plot = db_restore(id)

    if plot == None:
        html = get_html('%s/%s/' % (BASE_URL, url))
        desc = common.parseDOM(html, 'div', attrs={'class':'body', 'itemprop':'description'})
        if len(desc) > 0:
            plot = common.stripTags(desc[0])
        else:
            plot = ''

        db_store(id, plot)

    return plot


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
        fanart = ART_URL_PATTERN % (id, u)

        desc = get_description(u, ids[i])

        add_item(title, params={'mode':'seasons', 'u':u, 'i':ids[i]}, poster=img, fanart=fanart, plot=desc, isFolder=True)

    xbmcplugin.setContent(handle, 'tvshows')
    xbmcplugin.endOfDirectory(handle)


def show_seasons(params):
    url = '%s/%s/' % (BASE_URL, params['u'])

    html = get_html(url)

    container = common.parseDOM(html, 'div', attrs={'itemprop':'containsSeason'})
    seasons = common.parseDOM(container, 'li')

    id = params['i'][-4:-20:-1][::-1]
    id = id if id else '0'

    img = IMG_URL_PATTERN % (id, params['u'])
    fanart = ART_URL_PATTERN % (id, params['u'])
    plot = get_description(params['u'], params['i'])

    if len(seasons) > 0:
        for season in seasons:
            title = 'Сезон ' + common.parseDOM(season, 'span', attrs={'itemprop':'seasonNumber'})[0].encode('utf8')

            u = common.parseDOM(season, 'a', ret='href')[0].strip('/')

            add_item(title, params={'mode':'season', 'u':u}, plot=plot, poster=img, fanart=fanart, isFolder=True)
    else:
        # moonwalk
        # !!TODO!! для moonwalk тут надо делать выбор озвучки, до выбора сезона!
        data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
        if data:
            data = json.loads(data.group(1))
            seasons = sorted(data[0]['seasons'])
            for season in seasons:
                title = 'Сезон ' + str(season)
                add_item(title, params={'mode':'season', 'u':params['u'], 's':season}, plot=plot, poster=img, fanart=fanart, isFolder=True)
    
    if len(seasons) == 0:
        show_season(params)
        return

    xbmcplugin.setContent(handle, 'seasons')
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

            add_item(title, params={'mode':'episode', 'u':u}, thumb=img, fanart=fanart, isPlayable=True)

        # pagination
        p = common.parseDOM(html, 'span', attrs={'class':'icon-chevron-thin-right'})
        if len(p) > 0:
            params['page'] = page + 1
            add_item('Далее > %d' % params['page'], params=params, fanart=fanart, isFolder=True)

    else:
        # пробуем moonwalk
        data = re.search(r"window\.playerData = '(\[.*\])';<", html, re.I and re.S)
        if data:
            data = json.loads(data.group(1))
            episodes = sorted(data[0]['seasons'][params['s']]['episodes'])
            for episode in episodes:
                title = 'Серия ' + str(episode)
                add_item(title, params={'mode':'episode', 'u':'/%s/' % params['u'], 's':params['s'], 'e':episode}, icon=icon, fanart=fanart, isPlayable=True)

    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle)


def play_episode(params):
    url = BASE_URL + params['u']

    html = get_html(url)

    src = common.parseDOM(html, 'iframe', attrs={'id':'iframe-player'}, ret='src')[0]

    purl = ''

    if 'moonwalk' in src:
        if 'e' in params.keys():
            iframe = re.search(r"(.*)\?", src)
            if iframe:
                src = '%s?season=%s&episode=%s&nocontrols=1' % (iframe.group(1), params['s'], params['e'])

        key = addon.getSetting('key')
        iv = addon.getSetting('iv')

        purl = moon.get_url(src, url, key, iv)

    else:
        html = get_html(src)
        s = re.search(r'"hls":"(.*?\.m3u8)', html)
        if s:
            purl = s.group(1).replace(r'\/', '/').replace(r'\r', '').replace(r'\n', '')

    if purl:
        item = xbmcgui.ListItem(path=purl)
        item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        xbmcplugin.setResolvedUrl(handle, True, item)


def get_html(url, params={}, post={}, noerror=True):
    headers = {'Referer':url, 'User-Agent':'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'}

    html = ''

    try:
        conn = urllib2.urlopen(urllib2.Request('%s?%s' % (url, urllib.urlencode(params)), headers=headers))
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


def add_item(title, params={}, icon='', banner='', fanart='', poster='', thumb='', plot='', isFolder=False, isPlayable=False, url=None):
    if url == None: url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))

    item = xbmcgui.ListItem(title, iconImage = icon, thumbnailImage = thumb)
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

    xbmcplugin.addDirectoryItem(handle, url=url, listitem=item, isFolder=isFolder)


connect = sql.connect(database=db)
cursor = connect.cursor()

def db_store(n, plot):
    plot = plot.replace("'","XXCC").replace('"',"XXDD")
    id = "n" + n
    try:
        cursor.execute("CREATE TABLE " + id + " (plot VARCHAR(512), i VARCHAR(1));")
        connect.commit()
    except:
        pass 
    else:
        cursor.execute('INSERT INTO ' + id + ' (plot, i) VALUES ("' + plot + '", "1");')
        connect.commit()

def db_restore(n):
    id = "n" + n
    plot = None
    try:
        cursor.execute('SELECT plot FROM ' + id + ';')
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
    tcc().remove_like('%fanimg.site/serials/%', True)

if mode == 'updatekeys':
    res = common.fetchPage({'link':'https://raw.githubusercontent.com/WendyH/PHP-Scripts/master/moon4crack.ini'})
    if res['content']:
        data = {k.strip(): v.strip().strip('"') for i in [l for l in res['content'].splitlines() if l.strip() != ''] for k, v in [i.split('=')]}
        addon.setSetting('key', data['key'])
        addon.setSetting('iv', data['iv'])
        xbmcgui.Dialog().notification(PLUGIN_NAME, 'Ключи обновлены', icon, 2000, False)

connect.close()
