## This file is part of Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

__revision__ = "$Id$"

   ##
   ## Name:          Mail_Submitter.py
   ## Description:   function Mail_Submitter
   ##                This function sends a confirmation email to the submitter
   ##             of the document
   ## Author:         T.Baron
   ##
   ## PARAMETERS:    authorfile: name of the file containing the author
   ##             titleFile: name of the file containing the title
   ##             emailFile: name of the file containing the email
   ##             status: one of "ADDED" (the document has been integrated
   ##                     into the database) or "APPROVAL" (an email has
   ##                 been sent to a referee - simple approval)
   ##             edsrn: name of the file containing the reference
   ##             newrnin: name of the file containing the 2nd reference
   ##                     (if any)
   ## OUTPUT: HTML
   ##

import os
import re

from invenio.config import CFG_SITE_NAME, \
     CFG_SITE_URL, \
     CFG_SITE_SUPPORT_EMAIL, \
     CFG_SITE_NAME_INTL

from invenio.websubmit_config import CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN
from invenio.mailutils import send_email
from invenio.websubmit_functions.Shared_Functions import get_nice_bibsched_related_message
from invenio.websubmit_functions.Create_hgf_record_json import washJSONinput

try: import json
except ImportError: import simplejson as json

def read_json(curdir,fieldname):
    """read json-file and return dict"""
    fr = open(os.path.join(curdir,fieldname), "r")
    text = fr.read()
    fr.close
    #if isinstance(eval(text),list): pass
    if text.startswith("["): pass #we have a list
    else: text = '[' + text +']' 
    jsontext = washJSONinput(text)
    jsondict_list = json.loads(jsontext, 'utf8')
    return jsondict_list
	
def Mail_Submitter_hgf(parameters, curdir, form, user_info=None):
    """
    This function send an email to the submitter to warn him the
    document he has just submitted has been correctly received.

    Parameters:

      * authorfile: Name of the file containing the authors of the
                    document

      * titleFile: Name of the file containing the title of the
                   document

      * emailFile: Name of the file containing the email of the
                   submitter of the document

      * status: Depending on the value of this parameter, the function
                adds an additional text to the email.  This parameter
                can be one of: ADDED: The file has been integrated in
                the database.  APPROVAL: The file has been sent for
                approval to a referee.  or can stay empty.

      * edsrn: Name of the file containing the reference of the
               document

      * newrnin: Name of the file containing the 2nd reference of the
                 document (if any)
    """
    FROMADDR = '%s Submission Engine <%s>' % (CFG_SITE_NAME_INTL["en"],CFG_SITE_SUPPORT_EMAIL)
    # retrieve report number
    edsrn = parameters['edsrn']
    newrnin = parameters['newrnin']
    fp = open("%s/%s" % (curdir,edsrn),"r")
    rn = fp.read()
    fp.close()
    rn = re.sub("[\n\r]+","",rn)
    if newrnin != "" and os.path.exists("%s/%s" % (curdir,newrnin)):
        fp = open("%s/%s" % (curdir,newrnin),"r")
        additional_rn = fp.read()
        fp.close()
        additional_rn = re.sub("[\n\r]+","",additional_rn)
        fullrn = "%s and %s" % (additional_rn,rn)
    else:
        fullrn = rn
    fullrn = fullrn.replace("\n"," ")
    # The title is read from the file specified by 'titlefile'
    m_title = "-"
    try:
        if os.path.exists(os.path.join(curdir,"hgf_245__")):
            jsondict_list = read_json(curdir,"hgf_245__")
            for dict in jsondict_list:
                if not "a" in dict.keys(): continue
                m_title = dict["a"].encode("utf-8")
                break
    except: m_title = "-"
    # The name of the author is read from the file specified by 'authorfile'
    m_author = "-"
    try:
        if os.path.exists(os.path.join(curdir,"hgf_1001_")):
            jsondict_list = read_json(curdir,"hgf_1001_")
            for dict in jsondict_list:
                if not "a" in dict.keys(): continue 
                m_author = dict["a"].encode("utf-8")
                break
    except:
        m_author = "-"
    # The submitters email address is read from the file specified by 'emailFile'
    try:
        fp = open("%s/%s" % (curdir,parameters['emailFile']),"r")
        m_recipient = fp.read().replace ("\n"," ")
        fp.close()
    except:
        m_recipient = ""
    # create email body
    email_txt = "Dear Sir or Madam, \nThe document %s\nTitle: %s\nAuthor(s): %s\n\nhas been correctly received\n\n" % (fullrn,m_title,m_author)
    # The user is either informed that the document has been added to the database, or sent for approval
    if parameters['status'] == "APPROVAL":
        email_txt =  email_txt + "An email has been sent to the referee. You will be warned by email as soon as the referee takes his/her decision regarding your document.\n\n"
    elif parameters['status'] == "ADDED":
        email_txt = email_txt + "It will be soon added to our Document Server.\n\nOnce inserted, you will be able to check the  bibliographic information and the quality of the electronic documents at this URL:\n<%s/record/%s>\nIf you detect an error please let us know by sending an email to %s. \n\n" % (CFG_SITE_URL,sysno,CFG_SITE_SUPPORT_EMAIL)
    email_txt += get_nice_bibsched_related_message(curdir)
    email_txt = email_txt + "Thank you for using %s Submission Interface.\n" % CFG_SITE_NAME


    # send the mail
    send_email(FROMADDR, m_recipient.strip(), "%s: Document Received" % fullrn, email_txt, copy_to_admin=CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN,header="",html_header="")
    return ""

