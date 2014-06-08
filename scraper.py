# This is a template for a Python scraper on Morph (https://morph.io)
# including some code snippets below that you should find helpful

import scraperwiki
import mechanize
import lxml.html
import urllib, urlparse, urllib2
import re, json, time

# scraper now searches per known address for much faster response
# microwiki

url = "http://www.styrevervregisteret.no/"

# year = "2011"

cj = mechanize.CookieJar()
br = mechanize.Browser()
br1 = mechanize.Browser()
ua = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
br.addheaders = [('User-agent', ua)]
br.set_cookiejar(cj)
br1.addheaders = [('User-agent', ua)]
br1.set_cookiejar(cj)


def Main():
    response = br.open(url)
#    for a in br.links():
#        if a.text == 'Click here to execute Client Query':
#            link = a
#    response = br.follow_link(link)
    
    # create the displaygrid index page which contains the addr1s that we will search against
    if False:
        br.select_form("aspnetForm")
        br["ddlQYear"] = [year]
        request = br.click()
        response1 = br1.open(request)
        htmlI = response1.read()
        print htmlI
        ldata = ParseHtable(htmlI)
        scraperwiki.sqlite.save(["year", "addr1"], ldata, "displaygrid")


    # now find the list of client names we will search on (use a join to filter out)
    sqlobb = "select displaygrid.addr1 from displaygrid left join indivlobb on indivlobb.addr1=displaygrid.addr1 where indivlobb.addr1 is null"
    laddr1 = [ x[0]  for x in scraperwiki.sqlite.execute(sqlobb)["data"] ]
    print laddr1 
    for addr1 in laddr1:
        br.select_form("form1")
        br["txtQCName"] = addr1
        response = br.submit()
        htmlI = response.read()
        dgvs = re.findall("DisplayGrid_0_15_(\d+)\$ViewBTN", htmlI)
        maxgridbutton = dgvs and max(map(int, dgvs)) or 0
        print "Found %d entries for client: %s" % (maxgridbutton, addr1)
        lidata = [ ]
        for d in range(maxgridbutton):
            html2 = GetLobbyGrid(d)
            lidata.append({"d":d, "addr1":addr1, "html2":html2})
        scraperwiki.sqlite.save(["addr1", "d"], lidata, "indivlobb")

#scraperwiki.sqlite.execute("drop table indivlobb"); scraperwiki.sqlite.execute("create table indivlobb (addr1 text)")


def GetLobbyGrid(d):
    br.select_form("aspnetForm")
    br.set_all_readonly(False)
    dt = 'DisplayGrid_0_15_%d$ViewBTN' % d
    br["__EVENTTARGET"] = dt
    br["__EVENTARGUMENT"] = ''
    br.find_control("btnSearch").disabled = True
    #print br.form
    request = br.click()
    #print request
    response1 = br1.open(request)
    
    # find the window open hidden in the script
    html1 = response1.read()
    root1 = lxml.html.fromstring(html1)
    for s in root1.cssselect("script"):
        if s.text:
            ms = re.match("var myWin;myWin=window.open\('(LB_HtmlCSR.aspx\?.*?)',", s.text)
            if ms:
                loblink = ms.group(1)
    uloblink = urlparse.urljoin(br1.geturl(), loblink)
    response2 = br1.open(uloblink)
    html2 = response2.read()
    #print "LobbyGrid", dt, len(html2)
    return html2


def ParseHtable(htable):
    mhtable = re.search("(?s)DisplayGrid.Data =\s*(\[\[.*?\]\])", htable)
    jtable = mhtable.group(1)
    jtable = jtable.replace("\\'", ";;;APOS;;;")
    jtable = jtable.replace("'", '"')
    jtable = jtable.replace(";;;APOS;;;", "'")
    jtable = jtable.replace(",]", "]")
    jdata = json.loads(jtable)
    # ['Hordaland','Halden Kommune','Amundsen, Ole Roald','Folkevalgt, vara','Halden kommune, Senterpartiet']
    headers = ["fylke", "kommune", "navn", "type", "beskrivelse"]
    ldata = [ ]
    for jt in jdata:
        assert len(jt) == len(headers), (headers, jt)
        data = dict(zip(headers, jt))
        ldata.append(data)
    return ldata


# try again if the server has failed
for i in range(3):
    try:
        Main()
    except urllib2.HTTPError, e:
        print i, e
        time.sleep(10)

