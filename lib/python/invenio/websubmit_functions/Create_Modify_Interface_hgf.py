## This file is part of Invenio.
## Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011 CERN.
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
"""
This is the Create_Modify_Interface function (along with its helpers).
It is used by WebSubmit for the "Modify Bibliographic Information" action.
"""
__revision__ = "$Id$"

import os
import re
import time
import pprint

from invenio.dbquery import run_sql
from invenio.websubmit_config import InvenioWebSubmitFunctionError
from invenio.websubmit_functions.Retrieve_Data import Get_Field
from invenio.errorlib import register_exception
from invenio.config import * #(local-conf)

from invenio.bibdocfile import BibRecDocs

def Create_Modify_Interface_getfieldval_fromfile(cur_dir, fld=""):
    """Read a field's value from its corresponding text file in 'cur_dir' (if it exists) into memory.
       Delete the text file after having read-in its value.
       This function is called on the reload of the modify-record page. This way, the field in question
       can be populated with the value last entered by the user (before reload), instead of always being
       populated with the value still found in the DB.
    """
    fld_val = ""
    if len(fld) > 0 and os.access("%s/%s" % (cur_dir, fld), os.R_OK|os.W_OK):
        fp = open( "%s/%s" % (cur_dir, fld), "r" )
        fld_val = fp.read()
        fp.close()
        try:
            os.unlink("%s/%s"%(cur_dir, fld))
        except OSError:
            # Cannot unlink file - ignore, let WebSubmit main handle this
            pass
        fld_val = fld_val.strip()
    return fld_val

def read_javascript_includes():
	"""return javascript includes for autosuggest as text"""
	if "CFG_PREFIX" in globals(): 
		js_filepath = os.path.join(CFG_PREFIX,"var/www/js/jquery/jquery-lib.html")
		if os.path.exists(js_filepath):
			f = open(js_filepath,"r")
			js_text = f.read()
			f.close()
			return js_text
		else: return ""
	else: return ""      

def insert_docfiles_in_modify_form(recid):
	bibrecdocs = BibRecDocs(recid)
	# Create the list of files based on current files and performed
	# actions
	bibdocs = bibrecdocs.display()
	bibdocs = bibdocs.replace("<small><b>hgf_file</b> file(s):</small>","") #delete that part et the beginning of html
	return bibdocs #bibdocs already html formatted 
	
	
def prefill_radio_checkbox(modifytext,value):
	modifytext = modifytext.replace('checked="checked"','').replace("checked","")   
	if isinstance(value,list): # a list with all checked values (for checkboxfield with more than one checked values)
		for val in value:
			if not val in modifytext: continue
			modifytext = modifytext.replace('value="%s"' %val,'value="%s" checked="checked"' %val)		
	else: 
		modifytext = modifytext.replace('value="%s"' %value,'value="%s" checked="checked"' %value)
	return modifytext
	
def Create_Modify_Interface_getfieldval_fromDBrec(fieldcode, recid):
    """Read a field's value from the record stored in the DB.
       This function is called when the Create_Modify_Interface function is called for the first time
       when modifying a given record, and field values must be retrieved from the database.
    """
    fld_val = ""
    if fieldcode != "":
        for next_field_code in [x.strip() for x in fieldcode.split(",")]:
            fld_val += "%s\n" % Get_Field(next_field_code, recid)
        fld_val = fld_val.rstrip('\n')
    return fld_val
	
def Create_Modify_Interface_transform_date(fld_val):
    """Accept a field's value as a string. If the value is a date in one of the following formats:
          DD Mon YYYY (e.g. 23 Apr 2005)
          YYYY-MM-DD  (e.g. 2005-04-23)
       ...transform this date value into "DD/MM/YYYY" (e.g. 23/04/2005).
    """
    if re.search("^[0-9]{2} [a-z]{3} [0-9]{4}$", fld_val, re.IGNORECASE) is not None:
        try:
            fld_val = time.strftime("%d/%m/%Y", time.strptime(fld_val, "%d %b %Y"))
        except (ValueError, TypeError):
            # bad date format:
            pass
    elif re.search("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", fld_val, re.IGNORECASE) is not None:
        try:
            fld_val = time.strftime("%d/%m/%Y", time.strptime(fld_val, "%Y-%m-%d"))
        except (ValueError,TypeError):
            # bad date format:
            pass
    return fld_val


def Create_Modify_Interface_hgf(parameters, curdir, form, user_info=None):
    """
    Create an interface for the modification of a document, based on
    the fields that the user has chosen to modify. This avoids having
    to redefine a submission page for the modifications, but rely on
    the elements already defined for the initial submission i.e. SBI
    action (The only page that needs to be built for the modification
    is the page letting the user specify a document to modify).

    This function should be added at step 1 of your modification
    workflow, after the functions that retrieves report number and
    record id (Get_Report_Number, Get_Recid). Functions at step 2 are
    the one executed upon successful submission of the form.

    Create_Modify_Interface expects the following parameters:

       * "fieldnameMBI" - the name of a text file in the submission
        working directory that contains a list of the names of the
        WebSubmit fields to include in the Modification interface.
        These field names are separated by"\n" or "+".

    Given the list of WebSubmit fields to be included in the
    modification interface, the values for each field are retrieved
    for the given record (by way of each WebSubmit field being
    configured with a MARC Code in the WebSubmit database).  An HTML
    FORM is then created. This form allows a user to modify certain
    field values for a record.

    The file referenced by 'fieldnameMBI' is usually generated from a
    multiple select form field): users can then select one or several
    fields to modify

    Note that the function will display WebSubmit Response elements,
    but will not be able to set an initial value: this must be done by
    the Response element iteself.

    Additionally the function creates an internal field named
    'Create_Modify_Interface_DONE' on the interface, that can be
    retrieved in curdir after the form has been submitted.
    This flag is an indicator for the function that displayed values
    should not be retrieved from the database, but from the submitted
    values (in case the page is reloaded). You can also rely on this
    value when building your WebSubmit Response element in order to
    retrieve value either from the record, or from the submission
    directory.
    """
    global sysno,rn
    t = ""
    # variables declaration
    fieldname = parameters['fieldnameMBI']
    # Path of file containing fields to modify

    the_globals = {
        'doctype' : doctype,
        'action' : action,
        'act' : action, ## for backward compatibility
        'step' : step,
        'access' : access,
        'ln' : ln,
        'curdir' : curdir,
        'uid' : user_info['uid'],
        'uid_email' : user_info['email'],
        'rn' : rn,
        'last_step' : last_step,
        'action_score' : action_score,
        '__websubmit_in_jail__' : True,
        'form': form,
        'sysno': sysno,
        'user_info' : user_info,
        '__builtins__' : globals()['__builtins__'],
        'Request_Print': Request_Print
    }

    # We need to create SuE and it has to contain the email of the
    # current user at the end. Either, the current user is the owner,
    # so it is the same as before modify OR it is different, then the
    # current user has some special permissions and she should get
    # ownership for the record in question.
    fp = open( "%s/%s" % (curdir, "SuE"), "w" )
    fp.write(uid_email)
    fp.close()

    if os.path.exists("%s/%s" % (curdir, fieldname)):
        fp = open( "%s/%s" % (curdir, fieldname), "r" )
        fieldstext = fp.read()
        fp.close()
        fieldstext = re.sub("\+","\n", fieldstext)
        fields = fieldstext.split("\n")
    else:
        res = run_sql("SELECT fidesc FROM sbmFIELDDESC WHERE  name=%s", (fieldname,))
        if len(res) == 1:
            fields = res[0][0].replace(" ", "")
            fields = re.findall("<optionvalue=.*>", fields)
            regexp = re.compile("""<optionvalue=(?P<quote>['|"]?)(?P<value>.*?)(?P=quote)""")
            fields = [regexp.search(x) for x in fields]
            fields = [x.group("value") for x in fields if x is not None]
            fields = [x for x in fields if x not in ("Select", "select")]
        else:
            raise InvenioWebSubmitFunctionError("cannot find fields to modify")
    #output some text
    t += '<script type="text/javascript" src="%s/js/jquery.min.js"></script>' %CFG_SITE_URL
    t += "<fieldset id=\"submissionfields\">"
     
    t2 = "<script>function prefill() {" 
    for field in fields:
        subfield = ""
        value = ""
        marccode = ""
        text = ""
        # retrieve the marc code associated with the field
        res = run_sql("SELECT marccode FROM sbmFIELDDESC WHERE name=%s", (field,))
        if len(res) > 0:
            marccode = res[0][0]
        # then retrieve the previous value of the field
	
        if os.path.exists("%s/%s" % (curdir, "Create_Modify_Interface_DONE")):
            # Page has been reloaded - get field value from text file on server, not from DB record
            value = Create_Modify_Interface_getfieldval_fromfile(curdir, field)
#            if os.path.isfile(os.path.join(curdir,field)):
 #               fd = open(os.path.join(curdir,field),"r")
  #              value = fd.read().replace("\n","").replace("\r","")
   #             fd.close()   
        else:
            # First call to page - get field value from DB record
            value = Create_Modify_Interface_getfieldval_fromDBrec(marccode, sysno)
        # If field is a date value, transform date into format DD/MM/YYYY:
        #print "field:%s,value:%s" %(field,value)
        # retrieve and display the modification text
        res = run_sql("SELECT modifytext FROM sbmFIELDDESC WHERE  name=%s", (field,))
        if len(res)>0:
	    # the html representation of a hgf field is stored in modifytext!
            modifytext = run_sql("SELECT fitext FROM sbmFIELD where subname='SBI%s' and fidesc='%s'" %(doctype,field))[0][0]
            if (('type="radio"' in modifytext) or ('type="checkbox"' in modifytext)): 
                modifytext = prefill_radio_checkbox(modifytext,value)
	    	
            t += modifytext + "\n"
        
        #value = Create_Modify_Interface_transform_date(value)
        res = run_sql("SELECT * FROM sbmFIELDDESC WHERE name=%s", (field,))
        if len(res) > 0:
            element_type = res[0][3]
            numcols = res[0][6]
            numrows = res[0][5]
            size = res[0][4]
            maxlength = res[0][7]
            val = res[0][8]
            fidesc = res[0][9]
            if element_type == "T":
                text = "<TEXTAREA name=\"%s\" rows=%s cols=%s wrap>%s</TEXTAREA>" % (field, numrows, numcols, value)
            elif element_type == "F":
                text = "<INPUT TYPE=\"file\" name=\"%s\" size=%s maxlength=\"%s\">" % (field, size, maxlength)
            elif element_type == "I":
                value = re.sub("[\n\r\t]+", "", value)
                text = "<INPUT name=\"%s\" size=%s value=\"%s\"> " % (field, size, val)
                text = text + "<SCRIPT>document.forms[0].%s.value=\"%s\";</SCRIPT>" % (field, value)
            elif element_type == "H":
                text = "<INPUT type=\"hidden\" name=\"%s\" value=\"%s\">" % (field, val)
                text = text + "<SCRIPT>document.forms[0].%s.value=\"%s\";</SCRIPT>" % (field, value)
            elif element_type == "S":
                values = re.split("[\n\r]+", value)
                text = fidesc
                if re.search("%s\[\]" % field, fidesc):
                    multipletext = "[]"
                else:
                    multipletext = ""
                if len(values) > 0 and not(len(values) == 1 and values[0] == ""):
                    text += "<SCRIPT>\n"
                    text += "var i = 0;\n"
                    text += "el = document.forms[0].elements['%s%s'];\n" % (field, multipletext)
                    text += "max = el.length;\n"
                    for val in values:
                        text += "var found = 0;\n"
                        text += "var i=0;\n"
                        text += "while (i != max) {\n"
                        text += "  if (el.options[i].value == \"%s\" || el.options[i].text == \"%s\") {\n" % (val, val)
                        text += "    el.options[i].selected = true;\n"
                        text += "    found = 1;\n"
                        text += "  }\n"
                        text += "  i=i+1;\n"
                        text += "}\n"
                        #text += "if (found == 0) {\n"
                        #text += "  el[el.length] = new Option(\"%s\", \"%s\", 1,1);\n"
                        #text += "}\n"
                    text += "</SCRIPT>\n"
            elif element_type == "D":
	        if field == "hgf_preview": text += fidesc #add field preview to modify form
                if value.startswith("\"") and value.endswith("\""): value = value[1:-1] 
                #text = text + "<SCRIPT>document.forms[0].%s.value=\"%s\";</SCRIPT>" % (field, value)
                jsval = value
                jsval = jsval.replace("\\", "\\\\")
                jsval = jsval.replace("\n", "\\n") #escape real newlines
                jsval = jsval.replace("\r", "\\r")
                
                # Do not escape " as we use '
                # jsval = jsval.replace('"', '\\"')
		#if jsval.startswith('"') and jsval.endswith('"'): jsval = jsval.replace('"', '')
                jsval = jsval.replace("'", "\\'")
                
		#INITIALIZE values for HGF!!!!!!
                if value.startswith("["): 
                    t2 += "$('#%s').val(\'%s\');\n" %(field.replace("hgf_","I"),jsval)
                else: t2 += "$('#%s').val(\'%s\');\n" %(field.replace("hgf_","I"),jsval)
            elif element_type == "R":
                try:
                    co = compile(fidesc.replace("\r\n", "\n"), "<string>", "exec")
                    ## Note this exec is safe WRT global variable because the
                    ## Create_Modify_Interface has already been parsed by
                    ## execfile within a protected environment.
                    the_globals['text'] = ''
                    exec co in the_globals
                    text = the_globals['text']
                except:
                    msg = "Error in evaluating response element %s with globals %s" % (pprint.pformat(field), pprint.pformat(globals()))
                    register_exception(req=None, alert_admin=True, prefix=msg)
                    raise InvenioWebSubmitFunctionError(msg)
            else:
                text = "%s: unknown field type" % field

            t += text
    t2 += "}</script>"
    t += t2
    
    t += "</fieldset>%s" % read_javascript_includes()
    t += insert_docfiles_in_modify_form(sysno)
    # output our flag field
    t += '<input type="hidden" name="Create_Modify_Interface_DONE" value="DONE\n" />'
    # output some more text
    t = t + "<br /><br /><script>prefill();</script><CENTER><small><INPUT type=\"button\" width=400 height=50 name=\"End\" value=\"END\" onClick=\"document.forms[0].step.value = 2;user_must_confirm_before_leaving_page = false;document.forms[0].submit();\"></small></CENTER></H4>"

    return t

