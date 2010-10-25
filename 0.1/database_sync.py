#!/usr/bin/python
from trac.env import Environment
import os
# modify the env_path to the trac environment that you want to install this plugin to
#e.g. env_path='/var/www/code/trac/projects/ddd'
env_path='/var/www/trac/projects/master'
env=Environment(env_path)
cnx=env.get_db_cnx()
cur=cnx.cursor()
#create a table named 'project' to manage the trac projects that the users may apply
create_project_table='''
CREATE TABLE project(
    id integer PRIMARY KEY,
    owner text,
    email text,
    proj_name text,
    proj_full_name text,
    description text,
    apply_time integer,
    exam_time integer,
    stat integer
         );
'''
create_project_change_table='''
CREATE TABLE project_change(
    id integer PRIMARY KEY,
    who text,
    change text,
    time integer
    );
'''
# add PROJECT_CREATE PROJECT_APPROVE PROJECT_REJECT PROJECT_DELETE to a particular username ,
# generally we add them to one who has the TRAC_ADMIN action,please modify the username here.
#e.g. username='admin'

#username='superman'
#actions=['PROJECT_CREATE','PROJECT_APPROVE','PROJECT_REJECT','PROJECT_DELETE']
print '**********************************************************'
print "            START SYNCHRONIZING DATABASE                          \n\n"
try:
    cur.execute(create_project_table)
    print create_project_table,'\nDONE'
    cur.execute(create_project_change_table)
    print create_project_change_table,'\nDONE'
except:
    pass


#for action in actions:
#    add_actions="insert into permission values ('%s','%s');"%(username,action)
#    try:
#        cur.execute(add_actions)
#        print add_actions, '\nDONE'
#    except:
#        pass
cur.close()
cnx.commit()
cnx.close()
print "SYNCHRONIZE DATABASE DONE!"
print '**********************************************************'











            

