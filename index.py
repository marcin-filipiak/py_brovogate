#!/usr/bin/env python

from BeautifulSoup import BeautifulSoup as bs
from mod_python import util
import httplib
import urllib
import base64
import mimetypes
import os
from urlparse import urljoin
from urlparse import urlparse

#sciezka do tego pliku na serwerze
SCRIPT_PATH = "/var/www/gate/"
#czy ma byc wlaczone keszowanie plikow
CACHE = True

#dodanie domeny do linku by byl prawodlowy adres
def full_url(url,base):
	"""
	if url.find("http") == -1:
		url = "http://"+domain+"/"+url
	"""
	url = urljoin(base, url)
	return url

#pobranie zawartosci z podanego url przez lokalny proxy privoxy
def get_content(url):
	#polaczenie z privoxy
	h = httplib.HTTPConnection("127.0.0.1", 8118)
	h.connect()
	#polaczenie ze wskazanym url
	h.request("GET",url)
	resp = h.getresponse()
	#pobranie danych
	page = resp.read()
	h.close()
	return page

#pobranie obrazkow i podlaczenie ich jako base64 w kodzie strony
def get_images_base64(html_content,url):
	soup = bs(html_content)
	#przegladanie wszystkich <img src="foo.bar"/> w dokumencie
	for image in soup.findAll("img"):
		#pobranie parametru src
		img_src = "%(src)s" %image
		mimetypes.init()
		#wykrycie typu mime pliku np. png
		file_type = (mimetypes.guess_type(full_url(img_src,url)))[0]
		#pobranie pliku w formie base64
		img_b64 = base64.b64encode(get_content(full_url(img_src,url)))
		#zamiana pliku z lokalizacji url w src na dane w base64
		html_content = html_content.replace(img_src,"data:"+file_type+";base64,"+img_b64)
	return html_content

#pobranie obrazkow do cache i podlaczenie ich do strony
def get_images_cache(html_content,url):
	soup = bs(html_content)
	#przegladanie wszystkich <img src="foo.bar"/> w dokumencie
	for image in soup.findAll("img"):
		#pobranie parametru src
		img_src = "%(src)s" %image
		#pobranie rozszerzenia pliku
		file_extension = img_src.split(".")[-1]
		#wygenerowanie losowej nazwy pliku
		file_random_name = base64.b64encode(os.urandom(4))[:7]
		#stworzenie pliku w keszu
		f = open(SCRIPT_PATH+"cache/"+file_random_name+"."+file_extension, 'w')
		#zapisanie zawartosci do pliku z sieci
		f.write(get_content(full_url(img_src,url)))
		f.close()
		#podlaczenie w trsci strony pliku z lokalizacja z keszu
		html_content = html_content.replace(img_src,"cache/"+file_random_name+"."+file_extension)
	return html_content

#przekierowanie linkow na zapytania przez bramke
def redirect_ahref(html_content,url):
	soup = bs(html_content)
	for a in soup.findAll("a"):
		href = "%(href)s" %a
		html_content = html_content.replace(href,"?url="+full_url(href,url))
	return html_content

#dodanie paska z adresem strony napisanym w js
def add_bar(page):
	page = page.replace("</head>","<script type='text/javascript' src='js/jquery-1.7.1.min.js'></script>\n<script type='text/javascript' src='js/bar.js'></script>\n</head>")
	return page

#strona
def index(req):
	#pobranie parametru GET[url]
	form = util.FieldStorage(req, keep_blank_values=1)
   	url = form.getfirst("url")
	
	try:	
		url = urllib.url2pathname(url)
		#wyciaganie domeny z url
		domain = urlparse(url).netloc
		#pobranie tresci strony
		page = get_content(url)
		#zdeponowanie w utf8
		page = page.decode('utf-8')
		#jesli dolaczone media nie maja byc keszowane
		if (CACHE == False):
			#dopisanie do tresci strony obrazka w formie base64
			page = get_images_base64(page,url)
		#keszowanie zawartosci
		else:
			#zapisanie obrazka w keszu i podlaczenie pod strone
			page = get_images_cache(page,url)
		page = redirect_ahref(page,url)
	#pojawil sie blad w polaczeniu lub nie podano url
	except:
		#pusta strona startowa
		page = "<html><head></head><body>  </body></html>"
		#podlaczenie paska z polem do wpisania url
		page = add_bar(page)
	return page
