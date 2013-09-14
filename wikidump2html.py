#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  wikidump2html.py
#  
#  Copyright 2013 Yaron de Leeuw   http://jaron.net/
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
import pdb
import hashlib
import os
import argparse
import sys
import subprocess

from lxml import etree, html



def fast_iter(context, func):
    # http://stackoverflow.com/questions/7171140/using-python-iterparse-for-large-xml-files
    # http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
    # original Author: Liza Daly
    # ruined by jarondl
    sys.stdout.write("0")
    for n, (event, elem) in enumerate(context):
        sys.stdout.write('\r{}'.format(n))
        func(elem)
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    del context


def fname_hash(page_name):
    m = hashlib.sha1(page_name.encode('UTF-8'))
    filename = m.hexdigest() + ".html"
    folder_name = filename[:2]
    return os.path.join(folder_name, filename)
    
def link_repl(href):
    if href.startswith("http:") or href.startswith("https:"):
        return href
    elif href.startswith("File:") or href.startswith("Image:"):
        # image file
        return href
    else:
        return "../" + fname_hash(href)

def try_table_fix(text):
    ## Removing all table stylings,
    ##
    lines = text.split("\n")
    for n in range(len(lines)):
        if lines[n].startswith("|-"):
            lines[n] = "|-"
        if lines[n].startswith("{|"):
            lines[n] = "{|"
    return "\n".join(lines)
    
def pandoc_to_html(wikipage):
    text = wikipage.pre_text
    for n in range(5):
        pro = subprocess.Popen(["pandoc", "-f","mediawiki","-t","html"], 
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = pro.communicate(text.encode('UTF-8'))
        if errs == b'':
            # No errors! we can leave the loop
            page_html = outs.decode('UTF-8')
            
            try:
                parsed_html = html.document_fromstring(page_html)
                
                # add h1 title to page
                body = parsed_html[0]
                body.insert(0, etree.Element("h1"))
                body[0].text = wikipage.title
                #add html title.
                parsed_html.insert(0, etree.Element("head"))
                parsed_html[0].insert(0, etree.Element("title"))
                parsed_html[0][0].text = wikipage.title
                
                parsed_html.rewrite_links(link_repl)
                
                return html.tostring(parsed_html, encoding='UTF-8').decode('UTF-8')
            except etree.ParserError as e:
                print(str(e))
                return outs.decode('UTF-8')
        sys.stdout.write('\r')
        print("Parse error in {}  -  {}".format(wikipage.title, fname_hash(wikipage.title)))
        print(errs.decode('UTF-8'))
        print("trying to fix and reiterate")
        new_text =  try_table_fix(text)
        if new_text == text:
            # no success
            return text
        text = new_text
        #pdb.set_trace()
    return text

class WikiPage(object):
    
    def __init__(self,elem):
        self.title = elem.findtext("{*}title")
        redir = elem.find("{*}redirect")
        self.is_redir = (redir is not None)
        if self.is_redir:
            self.redir_title = redir.get("title")

        rev = elem.find("{*}revision")
        self.pre_text = rev.findtext("{*}text")
            
    def rendered_text(self):
        
        elem_html =  pandoc_to_html(self)
        return elem_html
        
        
    def save_to_file(self, out_path = "out/"):
        target_name = os.path.join(out_path, fname_hash(self.title))
        dir_target = os.path.dirname(target_name)
        if not os.path.exists(dir_target):
            os.makedirs(dir_target)
        with open(target_name, "w") as f:
            f.write(self.rendered_text())
        # for debugging, we can output the source as well.
        #with open(target_name + ".src", "w") as f2:
        #    f2.write(self.pre_text)

def process_element(elem):
    page = WikiPage(elem)
    page.save_to_file()
    



def main():
    parser = argparse.ArgumentParser(description = __doc__,
                    formatter_class= argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dumpfile', metavar='DUMPFILE.XML', type=str,
                        help='the wiki dump file')
    args = parser.parse_args()
    context = etree.iterparse( args.dumpfile ,tag = '{*}page')
    fast_iter(context,process_element) 


if __name__ == '__main__':
    main()

