import re,os
import pandas as pd
#importing packages

# Snippet 1:
def function_pre_lower(data):     #function to Convert the whole string to lower case except the data which is in single quotes 
    data = data.lower()
    return data

input_1 = "the Data had the ' The data Main forum ' values Main to Copy"
output_1 = function_pre_lower(input_1)
#print(output_1)
#output:
"""
the data had the ' The data Main forum ' values main to copy """


# Snippet 2:
def data_remove_comments(read_text):          #This function is used to remove comments in the data
    dir_all = re.findall(r'\/\*([\s\S]*?)\*/', read_text)
    for j in dir_all:
        read_text = read_text.replace('/*' + j + '*/', '')
    read_text_split = read_text.split('\n')
    dash_comments_list = []
    if len(read_text_split):
        for whole_lines in read_text_split:
            if not whole_lines.strip().lstrip().startswith('dbms.') or whole_lines.strip().lstrip().startswith('dbms_'):
                dash_comments = re.findall(r'--.*', whole_lines)
                dash_comments_list.append(dash_comments)
        remov_dash_empty_list = [ele for ele in dash_comments_list if ele != []]
        for i in remov_dash_empty_list:
            read_text = read_text.replace(i[0], '')
    return read_text

input_2 = """
create or replace function p_addedocpatient (iclob_patientdetails text, in_registrationtype registrationmaster.registrationtype%type, iv_registrationsource registrationmaster.registrationsource%type, iv_registrationdesc registrationmaster.registrationdescription%type, iv_loginid registrationmaster.updatedby%type, on_registrationid inout numeric) AS $body$
DECLARE
 lv_patient numeric;
sequencename varchar(100);
v_location numeric;

--fugidkbvdfnvfldbnfdbf
/* fudsgdskhfkdlgndknfdlkbnfdlb */
"""
output_2 = data_remove_comments(input_2)
#print(output_2)
#Output:
"""
create or replace function p_addedocpatient (iclob_patientdetails text, in_registrationtype registrationmaster.registrationtype%type, iv_registrationsource registrationmaster.registrationsource%type, iv_registrationdesc registrationmaster.registrationdescription%type, iv_loginid registrationmaster.updatedby%type, on_registrationid inout numeric) AS $body$
DECLARE
 lv_patient numeric;
sequencename varchar(100);
v_location numeric; """


# Snippet 3:
def commonlogicextract(kimberly, x):#this function is used to search for 'x' and returns list of all the instances from 'x' values till closed braket
    startIndex = [m.start() for m in re.finditer(rf'\b{x}\(', kimberly)]
    listdata = []
    for index in startIndex:
        current = []
        bracket_level = 0
        for s in kimberly[index + len(x) + 1:]:
            if s != '(' and s != ')' and bracket_level >= 0:
                current.append(s)
            elif s == '(':
                current.append(s)
                bracket_level += 1
            elif s == ')':
                bracket_level -= 1
                if bracket_level < 0:
                    current.append(s)
                    break
                else:
                    current.append(s)
        listdata.append(x + '(' + ''.join(current))
    return listdata

input_3 = """
    trim(both extract(v_patient, '/RegistrationRequest/Patient/@Gender') .getstringval()),
    trim(both extract(v_patient, '/RegistrationRequest/Patient/@Title') .getstringval()) 
"""
output_3 = commonlogicextract(input_3, 'extract')
#print(output_3)
# Output:
''' [extract(v_patient, '/RegistrationRequest/Patient/@TransactionId'),extract(v_patient, '/RegistrationRequest/Patient/@Gender')] '''


# snippet 4:
def split_main(s):        #This function used to ignore comma inside the brackets while splitting the data with comma and returns a list
    parts = []
    bracket_level = 0
    current = []
    for c in (s + ","):
        if c == "," and bracket_level == 0:
            parts.append("".join(current))
            current = []
        else:
            if c == "(":
                bracket_level += 1
            elif c == ")":
                bracket_level -= 1
            current.append(c)
    current = ''.join(current).replace(',', '')
    parts.append(current)
    return parts

input_4= """ SELECT lv_patient,
 extract(value(li) , '/currentaddress/@AddressTypeID')  .getnumberval() ,
 extract(value(li) , '/currentaddress/@Street')  .getnumberval() ; """
output_4 = split_main(input_4)
#print(output_4)
# Output:
""" ['SELECT lv_patient', "\n extract(value(li) , '/currentaddress/@AddressTypeID')  .getnumberval() ",
    "\n extract(value(li) , '/currentaddress/@Street')  .getnumberval() "] """


# Snippet 5:
def function_pre_lower(data):           #This function will search for data present in single quotes and makes other data to lower
    singlequoye = re.findall(r"\'.*?\'", data)
    extractpartsdictformat = {}
    if len(singlequoye):
        arya = 0
        for arc1 in singlequoye:
            data = data.replace(arc1, 'sngqx' + str(arya) + 'sngqx', 1)
            extractpartsdictformat['sngqx' + str(arya) + 'sngqx'] = arc1
            arya = arya + 1
    data = data.lower()

    if len(extractpartsdictformat):
        for barc in extractpartsdictformat:
            data = data.replace(barc, extractpartsdictformat[barc], 1)
    return data

input_5 = """ SET CLIENT_ENCODING TO 'UTF8'
        FDGDUIDFHGDKFLGNLFK 'UGFDKK' djhfdFHDHDGH """
output_5 =function_pre_lower(input_5)
#print(output_5)
# Output:
""" set client_encoding to 'UTF8'
        fdgduidfhgdkflgnlfk 'UGFDKK' djhfdfhdhdgh
"""


# Snippet 6:
def select_funname(data, cschema_type):       #This function is used to retrieve function names from data and replace it by adding schema name to it
    data = re.sub(r' +', ' ', data)
    split_data = data.split('create or replace function')[1].split('(')[0].strip()
    data = data.replace(split_data, str(cschema_type + '.' + split_data))
    return data

input_6 = """
SET search_path = crm,public;
create or replace function p_addedocpatient (iclob_patientdetails text) AS $body$
DECLARE
 lv_patient numeric; """
output_6 = select_funname(input_6,'HRPAY')
#print(output_6)
# Output:
"""
SET search_path = crm,public;
create or replace function HRPAY.p_addedocpatient (iclob_patientdetails text) AS $body$
DECLARE
 lv_patient numeric; """


# Snippet 7:
def xml_extract_3(data): # This function will search for extract keyword from insert statement and constructs a statement by retirieving values from extract statement
    insert_data = re.findall(r'\binsert into\b.*?;',data,flags=re.I | re.DOTALL)
    for ins in insert_data:
        
        modified_string = ins
        ins = ins.casefold().replace('extract', 'EXTRACT').replace('values', 'VALUES').replace('getnumberval',
                                                                                    'GETNUMBERVAL').replace(
            'getstringval', 'GETSTRINGVAL').replace('to_date', 'TO_DATE')
        if ("EXTRACT" in ins) and ('VALUES' in ins) and (';' in ins):
            ins = re.sub(r'values\s+\(','values(',ins,flags=re.I)
            values_data = re.findall(r'\bvalues\((.*?)\);',ins,flags=re.I | re.DOTALL)
            comma_split=split_main(values_data[0])
            for sp in comma_split:
                sp = sp.replace("( '","('").replace("' )","')")
                if ("EXTRACT" in sp) and ("TO_DATE" not in sp):
                    a = re.findall(r'(.*?)\.',sp,flags=re.I | re.DOTALL)[0].strip()
                    b = re.findall(r'\(\'(.*?)\'\)',sp,flags=re.I | re.DOTALL)[0].strip()
                    if ".GETNUMBERVAL()" in sp:
                        statement ='\n' + "(UNNEST(XPATH('" + b + "'," + a + ")))" + "::VARCHAR::NUMERIC"
                        ins = ins.replace(sp,statement)
                    if ".GETSTRINGVAL()" in sp:
                        statement ='\n' +  "(UNNEST(XPATH('" + b + "'," + a + ")))" + "::VARCHAR"
                        ins = ins.replace(sp, statement)

                if ("EXTRACT" in sp) and ("TO_DATE" in sp):
                    a = re.findall(r'(.*?)\.', sp, flags=re.I | re.DOTALL)[0].strip()
                    b = re.findall(r'\(\'(.*?)\'\)', sp, flags=re.I | re.DOTALL)[0].strip()
                    if ".GETSTRINGVAL()" in sp:
                        statement ='\n' + "TO_DATE(UNNEST(XPATH('" + b + "'," + a + "))''dd-mm-yyyy HH24:MI:SS'))" + "::text::date"
                        ins = ins.replace(sp, statement)
        data = data.replace(modified_string,ins)
    return data

input_7 = """
  CREATE OR REPLACE PROCEDURE "HR"."P_ADDEMPLOYEEDETAILS_NEW" (IC_EMPLOYEEDETAILS IN CLOB,
 AS
  LX_EMPLOYEEDETAILS    XMLTYPE;
 BEGIN
 INSERT INTO EMPLOYEE_MAIN_DETAILS
    (EMPLOYEEID,
     EMPLOYEECODE,
	 TITLEID)
	VALUES
    (LN_EMPLOYEENUMBER,
     LX_EMPLOYEEDETAILS.EXTRACT('EmployeeBasicDetails/@employeecode')
     .GETSTRINGVAL(),
     LX_EMPLOYEEDETAILS.EXTRACT('EmployeeBasicDetails/@TitleID')
     .GETNUMBERVAL());
 INSERT INTO EMPLOYEE_AUXILIARY_DETAILS
    (EMP_AUX_ID,
     MADIAN_NAME_OTHER_NAME,
     MARRIAGE_DATE,
	VALUES
    (LN_EMPAUXILLARYNUMBER,
     LX_EMPLOYEEDETAILS.EXTRACT('EmployeeBasicDetails/@MaidenName')
     .GETSTRINGVAL(),
     TO_DATE(LX_EMPLOYEEDETAILS.EXTRACT('EmployeeBasicDetails/@MarriageDate')
             .GETSTRINGVAL(),
             'dd-mm-yyyy HH24:MI:SS'));
 END;
 """
output_7 = xml_extract_3(input_7)
#print(output_7)
# Output:
"""
  CREATE OR REPLACE PROCEDURE "HR"."P_ADDEMPLOYEEDETAILS_NEW" (IC_EMPLOYEEDETAILS IN CLOB,
 AS
  LX_EMPLOYEEDETAILS    XMLTYPE;
 BEGIN
 INSERT INTO EMPLOYEE_MAIN_DETAILS
    (EMPLOYEEID,
     EMPLOYEECODE,
	 TITLEID)
values(ln_employeenumber,
(UNNEST(XPATH('employeebasicdetails/@employeecode',lx_employeedetails)))::VARCHAR,
(UNNEST(XPATH('employeebasicdetails/@titleid',lx_employeedetails)))::VARCHAR::NUMERIC;
 INSERT INTO EMPLOYEE_AUXILIARY_DETAILS
    (EMP_AUX_ID,
     MADIAN_NAME_OTHER_NAME,
     MARRIAGE_DATE,
values(ln_empauxillarynumber,
       (UNNEST(XPATH('employeebasicdetails/@maidenname', lx_employeedetails)))::VARCHAR,
        TO_DATE(UNNEST(XPATH('employeebasicdetails/@marriagedate',TO_DATE(lx_employeedetails))''dd-mm-yyyy HH24:MI:SS'))::text::date;
 END; """


# Snippet 8:
def create_and_append_sqlfile_single(data):   #This function can be used to write the data into a file specified
    with open('packageindexfile.txt', 'a') as f:
        data = data.strip()
        f.write("{}\n".format(data))
        f.close()


# Snippet 9:
def create_and_append_configfile(config_path, data):      #This function can be used to write the data into a file in a specified path
    with open(config_path, 'w') as f:
        f.write("{}\n".format(data))


# Snippet 10: This is used to read data in a excel file from specific path
'''path = os.path.dirname(os.path.realpath(__file__))
tables_list_xl = path + '/' + 'tables_list.xlsx'
excel_data = pd.read_excel(tables_list_xl)
list_data = excel_data['OBJECT_NAME'].tolist() '''

#Examples of regular expressions:
'''
dec_begin = re.findall(r'\bdeclare\b.*?\bbegin\b', data, flags=re.DOTALL | re.I)-----Used to retrieve data from declare and begin
phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d')-----Regex to get the digits
haRegex = re.compile(r'(Ha){3}')-----Regex to repeat the number of search in the statements.
data = re.sub(r"\b(?<!')(\w+)(?!')\b", lambda match: match.group().lower(), data)-----Converts everything into lower case except the data in single quotes.
begin_when_data = re.search(r'\bbegin(.*?)when\b', data,re.DOTALL).group(1)------Search the data between begin and when
open_execute = re.findall(r'open\s+\S+\s+for\s+execute\s+select', data)-----finding the data from open to select.
begin_end_data_str = re.findall(r'\bbegin\b.*?\bend\b', data, re.DOTALL)-----taking data from begin to end including the begin and end.
dir_all = re.findall(r'\/\*[\s\S]*?\*/', data)------taking the data from /* to */
[abc] – will find all occurrences of a or b or c.
[a-z] will find all occurrences of a to z.
[a-z0–9A-Z] will find all occurrences of ato z , A to Z, o to 9.
pattern = '\d+' has all the patterns for digits,
\s search for spaces
\S search for non spaces
'''

# Steps to write new module:
'''
1.	Develop a feature function for the input
2.	Use comments while writing function definition for everybody understanding
3.	Do not use lower functions for whole input string in writing features. We can use in that lower function in conditions.
4.	After writing feature function, put that code in a python file(with same name as function) which will become a Module
5.	Module name should be same as feature name
6.	Use input string and schema parameters while developing feature, as we are using schema name parameter while calling feature functions in driver program.
'''

# function  main
def main(source_code):
    # start writing code here
    return source_code

# calling main function here
#if __name__ == '__main__':
output = main(source_code)






