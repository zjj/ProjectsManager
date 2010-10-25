# -*- coding: utf-8 -*-
#!/usr/bin/python
import re
import os
import time
import shutil
from email.mime.text import MIMEText
from genshi.builder import tag
from trac.util.presentation import Paginator
from trac import perm, util
from trac.env import Environment
from trac.core import *
from trac.perm import IPermissionRequestor
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util.datefmt import from_utimestamp, to_utimestamp
from trac.util.translation import _, tag_
from trac.util.datefmt import format_datetime
from trac.config import BoolOption, ExtensionOption, IntOption, Option
from trac.notification import NotificationSystem,NotifyEmail
from trac.search import ISearchSource, search_to_sql, shorten_result
from trac.timeline.api import ITimelineEventProvider
from trac.web.chrome import add_link,INavigationContributor

class ManageProject(Component):
    """projects manager"""
    
    implements(INavigationContributor,ITemplateProvider,IRequestHandler,ISearchSource,IPermissionRequestor,ITimelineEventProvider)
    
    def get_active_navigation_item(self, req):
        if req.authname and req.authname!='anonymous':
            return 'manage'
        else:
            return 'project'

    def get_navigation_items(self, req):
        if req.authname and req.authname!='anonymous':
            yield('mainnav', 'manage',tag.a(_('Projects Manage'), href=req.href.manage()))
        else:
            yield('mainnav', 'project',tag.a(_('Projects'), href=req.href.project()))
    
    def match_request(self, req):
        return (re.match(r'/manage(?:/([^/]+)(?:/([^/]+)(?:/(.+))?)?)?$', req.path_info)
                or re.match(r'/project(?:/(?:([0-9]+)|-1))?$',req.path_info))

    def process_request(self, req):
        data={}
        data['base_url']=self.env.config.get('projectsmanager','base_url')
        if  req.authname and req.authname!='anonymous':
            if 'PROJECT_ADMIN' in req.perm:
                pending_projects=self._pending_projects()
                approved_projects=self._approved_projects()
                rejected_projects=self._rejected_projects()
                # to get the particular items on that page
                if req.method=="POST":
                    p=int(req.args.get('p','1'))
                    a=int(req.args.get('a','1'))
                    r=int(req.args.get('r','1'))
                    results_p=Paginator(pending_projects,p-1,max_per_page=10)
                    data['pending_projects']=results_p.items
                    results_a=Paginator(approved_projects,a-1,max_per_page=10)
                    data['approved_projects']=results_a.items
                    results_r=Paginator(rejected_projects,r-1,max_per_page=10)
                    data['rejected_projects']=results_r.items
                    for i in data['pending_projects']:
                        action=req.args.get(i['proj_name'])
                        if action=='approve':
                            self._approve_a_project(self,i['proj_name'],req)
                            self._create_a_project(self,i['owner'],i['proj_name'],i['proj_full_name'],i['description'],req)
                        if action=='reject':
                            self._reject_a_project(i['proj_name'],req)
                    for i in data['approved_projects']:
                        action=req.args.get(i['proj_name'])
                        if action=='delete':
                            self._delete_a_project(i['proj_name'],req)
                    for i in data['rejected_projects']:
                        action=req.args.get(i['proj_name'])
                        if action=='delete':
                            self._delete_a_project(i['proj_name'],req)
                        if action=='approve':
                            self._approve_a_project(self,i['proj_name'],req)
                            self._create_a_project(self,i['owner'],i['proj_name'],i['proj_full_name'],i['description'],req)
                    req.redirect(req.href.manage(p=p,a=a,r=r))
                else:
                    p=int(req.args.get('p','1'))
                    a=int(req.args.get('a','1'))
                    r=int(req.args.get('r','1'))
                   
                   #page pending
                    results1=Paginator(pending_projects,p-1,max_per_page=10)
                    pagedata1=[]
                    data['p']=results1
                    shown_pages1 = results1.get_shown_pages(21)
                    for shown_page in shown_pages1:
                        page_href = req.href.manage(p=shown_page,a=a,r=r)
                        pagedata1.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
                    fields1 = ['href', 'class', 'string', 'title']
                    results1.shown_pages = [dict(zip(fields1, i)) for i in pagedata1]
                    results1.current_page = {'href': None, 'class': 'current',
                                                'string': str(results1.page + 1),
                                                                                'title':None}
                    if results1.has_next_page:
                        next_href=req.href.manage(p=p+1,a=a,r=r)
                        data['next_href1']=next_href
                    if results1.has_previous_page:
                        prev_href=req.href.manage(p=p-1,a=a,r=r)
                        data['prev_href1']=prev_href
                    data['pending_projects']=results1.items
                    
                    #page approved
                    results2=Paginator(approved_projects,a-1,max_per_page=10)
                    pagedata2=[]
                    data['a']=results2
                    shown_pages2 = results2.get_shown_pages(21)
                    for shown_page in shown_pages2:
                        page_href = req.href.manage(p=p,a=shown_page,r=r)
                        pagedata2.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
                    fields2 = ['href', 'class', 'string', 'title']
                    results2.shown_pages = [dict(zip(fields2, i)) for i in pagedata2]
                    results2.current_page = {'href': None, 'class': 'current',
                                                'string': str(results2.page + 1),
                                                                                'title':None}
                    if results2.has_next_page:
                        next_href=req.href.manage(p=p,a=a+1,r=r)
                        data['next_href2']=next_href
                    if results2.has_previous_page:
                        prev_href=req.href.manage(p=p,a=a-1,r=r)
                        data['prev_href2']=prev_href
                    data['approved_projects']=results2.items

                    #page rejected
                    results3=Paginator(rejected_projects,r-1,max_per_page=10)
                    pagedata3=[]
                    data['r']=results3
                    shown_pages3 = results3.get_shown_pages(21)
                    for shown_page in shown_pages3:
                        page_href = req.href.manage(p=p,a=a,r=shown_page)
                        pagedata3.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
                    fields3 = ['href', 'class', 'string', 'title']
                    results3.shown_pages = [dict(zip(fields3, i)) for i in pagedata3]
                    results3.current_page = {'href': None, 'class': 'current',
                                                'string': str(results3.page + 1),
                                                                               'title':None}
                    if results3.has_next_page:
                        next_href=req.href.manage(p=p,a=a,r=r+1)
                        data['next_href3']=next_href
                    if results3.has_previous_page:
                        prev_href=req.href.manage(p=p,a=a,r=r-1)
                        data['prev_href3']=prev_href
                    data['rejected_projects']=results3.items
                    data['page_href']=req.href.manage()
                    data['current_pending_page']=p
                    data['current_approved_page']=a
                    data['current_rejected_page']=r
                    return "projects_manage.html",data,None
            else:
                # for authorized username
                items=self._approved_projects()
                page=int(req.args.get('page','1'))
                results=Paginator(items,page-1,max_per_page=10)
                pagedata=[]
                data['paginator']=results
                shown_pages = results.get_shown_pages(21)
                for shown_page in shown_pages:
                    page_href = req.href.manage(page=shown_page)
                    pagedata.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
                fields = ['href', 'class', 'string', 'title']
                results.shown_pages = [dict(zip(fields, p)) for p in pagedata]
                results.current_page = {'href': None, 'class': 'current',
                                                'string': str(results.page + 1),
                                                                                'title':None}
                if results.has_next_page:
                    next_href=req.href.manage(page=page+1)
                    add_link(req,'next',next_href,_('Next Page'))
                if results.has_previous_page:
                    prev_href=req.href.manage(page=page-1)
                    add_link(req,'prev',prev_href,_('Previous Page'))
                data['page_href']=req.href.manage()
                data['approved_projects']=results.items
                return "auth_index.html",data,None
        else:
            #page for anonymous
            items=self._approved_projects()
            page=int(req.args.get('page','1'))
            results=Paginator(items,page-1,max_per_page=10)
            pagedata=[]
            data['paginator']=results
            shown_pages = results.get_shown_pages(21)
            for shown_page in shown_pages:
                page_href = req.href.project(page=shown_page)
                pagedata.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
            fields = ['href', 'class', 'string', 'title']
            results.shown_pages = [dict(zip(fields, p)) for p in pagedata]
            results.current_page = {'href': None, 'class': 'current',
                                                'string': str(results.page + 1),
                                                                                'title':None}
            if results.has_next_page:
                next_href=req.href.project(page=page+1)
                add_link(req,'next',next_href,_('Next Page'))
            if results.has_previous_page:
                prev_href=req.href.project(page=page-1)
                add_link(req,'prev',prev_href,_('Previous Page'))
            data['page_href']=req.href.project()
            data['approved_projects']=results.items
            return 'anonymous.html',data,None

    #pending projects
    def _pending_projects(self):
        pending_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=0 order by apply_time desc;")
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            tmp['owner']=i[1]
	    #just show the fitst 15 chars
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['email']=i[2]
            tmp['apply_time']=format_datetime(i[6])
            tmp['stat']="pending"
            pending_projects.append(tmp)
        return pending_projects
        
    #approved projects
    def _approved_projects(self):
        approved_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=1 order by exam_time desc;")
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            tmp['owner']=i[1]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['email']=i[2]
            tmp['apply_time']=format_datetime(i[6])
            tmp['exam_time']=format_datetime(i[7])
            tmp['stat']='approved'
            approved_projects.append(tmp)
        return approved_projects

    #rejected projects
    def _rejected_projects(self):
        rejected_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=-1 order by exam_time desc;")
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            tmp['owner']=i[1]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['email']=i[2]
            tmp['apply_time']=format_datetime(i[6])
            tmp['exam_time']=format_datetime(i[7])
            tmp['stat']='rejected'
            rejected_projects.append(tmp)
        return rejected_projects
    #to create a project
    @staticmethod
    def _create_a_project(self,owner,proj_name,proj_full_name,description,req):
        if "PROJECT_CREATE" in req.perm:
            inherit_file=self.env.config.get('projectsmanager','inherit_file')
            options=[
                      ('project','name',proj_full_name),
                      ('project','descr',description),
                      ('inherit','file',inherit_file)
                      ]
            (projects_root_dir,_)=os.path.split(self.env.path)
            path = os.path.join(projects_root_dir,proj_name)
            self.log.debug('starting to create the environment.')
            Environment(path,True,options)
            env=Environment(path)# cmd: trac-admin path permission add XX TRAC_ADMIN
            cnx=env.get_db_cnx()
            cur=cnx.cursor()
            cur.execute("insert into permission values ('%s','TRAC_ADMIN');"%\
                            owner)
            cur.close()
            cnx.commit()
            cnx.close()
        else:
            pass

    # to approve a project
    @staticmethod
    def _approve_a_project(self,proj_name,req):
        if 'PROJECT_APPROVE' in req.perm:
            now=time.time()
            try:
                cnx=self.env.get_db_cnx()
                cur=cnx.cursor()
                cur.execute("select proj_full_name from project where proj_name='%s';"%proj_name)
                proj_full_name=list(cur)[0][0]
                cur.execute("update project set stat=1,exam_time=%d  where proj_name='%s';"%\
                                (now,proj_name))
                
                cur.execute("INSERT into project_change (who,change,time) values ('%s','%s',%d);"%\
                    (req.authname,'Project %s was approved'%proj_full_name,int(now*1000000)))

                cur.close()
                cnx.commit()
                cnx.close()
            except:
                pass 
            try:
                self._notify_via_email(proj_name,'approve',req)
            except:
                pass

    #to reject a project
    def _reject_a_project(self,proj_name,req):
        if 'PROJECT_REJECT' in req.perm:
            now=time.time()
            try:
                cnx=self.env.get_db_cnx()
                cur=cnx.cursor()
                cur.execute("select proj_full_name from project where proj_name='%s';"%proj_name)
                proj_full_name=list(cur)[0][0]
                cur.execute("update project set stat=-1,exam_time=%d where proj_name='%s';"%\
                                (now,proj_name))

                cur.execute("INSERT into project_change (who,change,time) values ('%s','%s','%d');"%\
                                          (req.authname,'Project %s was rejected'%proj_full_name,int(now*1000000)))

                cur.close()
                cnx.commit()
                cnx.close()
            except:
                pass
            try:
                self._notify_via_email(proj_name,'reject',req)
            except:
                pass
    # to delete a project 
    def _delete_a_project(self,proj_name,req):
        if 'PROJECT_DELETE' in req.perm:
            try:
                self._notify_via_email(proj_name,'delete',req)
            except:
                pass
            try:
                cnx=self.env.get_db_cnx()
                cur=cnx.cursor()
                cur.execute("select proj_full_name from project where proj_name='%s';"%proj_name)
                proj_full_name=list(cur)[0][0]
                cur.execute("delete from project where proj_name='%s';"%proj_name)
                cur.execute("INSERT into project_change (who,change,time) values ('%s','%s','%d');"%\
                                                    (req.authname,'Project %s was deleted'%proj_full_name,int(time.time()*1000000)))

                cur.close()
                cnx.commit()
                cnx.close()
                (projects_root_dir,_)=os.path.split(self.env.path)
                path=os.path.join(projects_root_dir,proj_name)
                shutil.rmtree(path)
            except:
                pass

    def _notify_via_email(self,proj_name,action,req):
        if action == 'approve':
            notify=ApproveEmailSender(self.env)
            cnx=self.env.get_db_cnx()
            cur=cnx.cursor()
            cur.execute("select * from project where proj_name='%s';"%proj_name)
            project=list(cur)
            detail=project[0]
            username=detail[1]
            proj_name=detail[3]
            proj_full_name=detail[4]
            apply_time=format_datetime(detail[6])
            exam_time=format_datetime(detail[7])
            email_from=self.env.config.get('notification','smtp_from')
            email_to=detail[2]
            cur.close()
            cnx.commit()
            cnx.close()
            url=self.env.config.get('projectsmanager','base_url')+'/%s'%proj_name
            notify.notify(username,proj_full_name,apply_time,req.authname,exam_time,url)
            notify.send(email_from,email_to)
        elif action=='reject':
            notify=RejectEmailSender(self.env)
            cnx=self.env.get_db_cnx()
            cur=cnx.cursor()
            cur.execute("select * from project where proj_name='%s';"%proj_name)
            project=list(cur)
            detail=project[0]
            username=detail[1]
            proj_name=detail[3]
            proj_full_name=detail[4]
            apply_time=format_datetime(detail[6])
            exam_time=format_datetime(detail[7])
            email_from=self.env.config.get('notification','smtp_from')
            email_to=detail[2]
            cur.close()
            cnx.commit()
            cnx.close()
            notify.notify(username,proj_full_name,apply_time,req.authname,exam_time)
            notify.send(email_from,email_to)
        elif action=='delete':
            notify=DeleteEmailSender(self.env)
            cnx=self.env.get_db_cnx()
            cur=cnx.cursor()
            cur.execute("select * from project where proj_name='%s';"%proj_name)
            project=list(cur)
            detail=project[0]
            username=detail[1]
            proj_name=detail[3]
            proj_full_name=detail[4]
            apply_time=format_datetime(detail[6])
            exam_time=format_datetime(detail[7])
            email_from=self.env.config.get('notification','smtp_from')
            email_to=detail[2]
            cur.close()
            cnx.commit()
            cnx.close()
            notify.notify(username,proj_full_name,apply_time,req.authname,exam_time)
            notify.send(email_from,email_to)
        else:
            pass
    
    #IPermissionRequestor Method
    def get_permission_actions(self):
        actions = ['PROJECT_APPROVE','PROJECT_CREATE','PROJECT_DELETE','PROJECT_REJECT']
        return actions+[('PROJECT_ADMIN',actions)]

    #ISearchSource Method
    def get_search_filters(self,req):
        yield ('project',_('project'))

    def get_search_results(self,req,terms,filters):
        db = self.env.get_db_cnx()
        sql_query, args = search_to_sql(db, ['owner','proj_name','proj_full_name','description'],terms)
        cursor=db.cursor()
        cursor.execute('select owner, proj_name,proj_full_name,description,exam_time from project where stat=1 and'+ sql_query, args)
        for owner, proj_name, proj_full_name,description,exam_time in cursor:
            yield (
                    self.env.config.get('projectsmanager','base_url')+'/%s'%proj_name,
                    proj_full_name,
                    from_utimestamp(exam_time*1000000),
                    owner,
                    shorten_result("Description: "+description,terms,maxlen=100)
                    )
    
    #ITimelineEventProvider Method
    def get_timeline_filters(self, req):
        yield ('project changes',_('project changes'))

    def get_timeline_events(self, req, start, stop, filters):
        if 'project changes' in filters:
            cnx=self.env.get_db_cnx()
            cur=cnx.cursor()
            cur.execute("select who,change,time from project_change where time>=%s AND time<=%s"%\
                         (to_utimestamp(start), to_utimestamp(stop)));
            for who,change,ts in cur:
                yield('project',from_utimestamp(ts),who,change)

    def render_timeline_event(self, context, field, event):
        if field=='url':
            return None
        elif field=='title':
            return tag.em(event[3])
        elif field=='description':
            return event[3]
    
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    
class ApplyNewProject(Component):
    """
    Apply a new project
    """
    implements(ITemplateProvider,IRequestHandler)

    def match_request(self, req):
        return re.match(r'/apply(?:/([^/]+)(?:/([^/]+)(?:/(.+))?)?)?$', req.path_info)

    def process_request(self, req):
        data={}
        data['base_url']=self.env.config.get('projectsmanager','base_url')
        if req.authname and req.authname!='anonymous':
            if req.method=='POST':
                email_patt="\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*"
                proj_name_patt="^[\w][.\-\w]+$"
                owner=req.authname
                email=req.args.get('email')
                proj_name=req.args.get('proj_name')
                proj_full_name=req.args.get('proj_full_name')
                description=req.args.get('description')
                apply_time=int(time.time())
                if re.match(email_patt,email) and re.match(proj_name_patt,proj_name):
                    if self._boolExist(proj_name) or self.env.project_name==proj_name:
                        return "apply_fail.html",data,None
                    else:
                        self._apply_a_project(owner,email,proj_name,proj_full_name,description,apply_time,req)
                        if 'PROJECT_CREATE' in req.perm:
                            data['proj_name_apply']=proj_name
                            return "apply_create_success.html",data,None
                        else:
                            return "apply_success.html",data,None
                else:
                    return "illegal_input.html",data,None
            else:
                return "apply.html",data,None
        else:
            req.redirect(req.href.login())
    
    def _apply_a_project(self,owner,email,proj_name,proj_full_name,description,apply_time,req):
        stat=0
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("INSERT INTO project (owner,email,proj_name,proj_full_name,description,apply_time,stat) \
                            values ('%s','%s','%s','%s','%s','%d','%d');"%\
                            (owner,email,proj_name,proj_full_name,description,apply_time,stat))

        cur.execute("INSERT into project_change (who,change,time) values ('%s','%s',%d);"%\
                            (owner,'Project %s was applied'%proj_full_name,apply_time*1000000))
        cur.close()
        cnx.commit()
        cnx.close()
        try:
            ManageProject._approve_a_project(self,proj_name,req)
            ManageProject._create_a_project(self,owner,proj_name,proj_full_name,description,req)
        except:
            pass

    def _boolExist(self,proj_name):
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where proj_name='%s';"%proj_name)
        cur.close()
        cnx.commit()
        cnx.close()
        ret=0
        for i in cur:
            ret+=1
        if ret>0:
            return True
        return False
    
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
        
class MyProject(Component):
    """
    For authorized users to check out their projects
    """
    implements(ITemplateProvider,IRequestHandler)

    def match_request(self, req):
        return re.match(r'/myproject(?:/([^/]+)(?:/([^/]+)(?:/(.+))?)?)?$', req.path_info)

    def process_request(self, req):
        data={}
        if req.authname and req.authname!='anonymous':
            my_all_projects=self._all_my_projects(req.authname)  #all approved projects
            data['projects_to_show']=my_all_projects
            if req.method=="POST":
                pending=req.args.get('pending','off')
                approved=req.args.get('approved','off')
                rejected=req.args.get('rejected','off')
                if pending=='on' or approved=='on' or rejected=='on':
                    cnx=self.env.get_db_cnx()
                    cur=cnx.cursor()
                    projects_to_show=[]
                    if pending=='on':
                        projects_to_show+=self._my_pending_projects(req.authname)
                    if approved=='on':
                        projects_to_show+=self._my_approved_projects(req.authname)
                    if rejected=='on':
                        projects_to_show+=self._my_rejected_projects(req.authname)
                    data['projects_to_show']=projects_to_show
                else:
                    data['projects_to_show']=self._all_my_projects(req.authname)
                #paginate
                items=data['projects_to_show']
                quote_to_show=items
                page=int(req.args.get('page','1'))
                results=Paginator(items,page-1,max_per_page=10)
                pagedata=[]
                shown_pages = results.get_shown_pages(21)
                for shown_page in shown_pages:
                    page_href = req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=shown_page)
                    pagedata.append([page_href,None, str(shown_page),
                                             'page ' + str(shown_page)])
                fields = ['href', 'class', 'string', 'title']
                results.shown_pages = [dict(zip(fields, p)) for p in pagedata]
                results.current_page = {'href': None, 'class': 'current',
                                                'string': str(results.page + 1),
                                                                                'title':None}
                if results.has_next_page:
                    next_href=req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=page+1)
                    add_link(req,'next',next_href,_('Next Page'))
                if results.has_previous_page:
                    prev_href=req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=page-1)
                    add_link(req,'prev',prev_href,_('Previous Page'))
                data['page_href']=req.href.myproject()
                data['projects_to_show']=results.items
                data['paginator']=results
                return "my_projects.html",data,None
            else:
                pending=req.args.get('pending','on')
                approved=req.args.get('approved','on')
                rejected=req.args.get('rejected','on')

                if pending=='on' or approved=='on' or rejected=='on':
                    cnx=self.env.get_db_cnx()
                    cur=cnx.cursor()
                    projects_to_show=[]
                    if pending=='on':
                        projects_to_show+=self._my_pending_projects(req.authname)
                    if approved=='on':
                        projects_to_show+=self._my_approved_projects(req.authname)
                    if rejected=='on':
                        projects_to_show+=self._my_rejected_projects(req.authname)
                    data['projects_to_show']=projects_to_show
                else:
                    data['projects_to_show']=self._all_my_projects(req.authname)
                items=data['projects_to_show']
                page=int(req.args.get('page','1'))
                results=Paginator(items,page-1,max_per_page=10)
                pagedata=[]
                shown_pages = results.get_shown_pages(21)
                for shown_page in shown_pages:
                    page_href = req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=shown_page)
                    pagedata.append([page_href,None, str(shown_page),
                                         'page ' + str(shown_page)])
                fields = ['href', 'class', 'string', 'title']
                results.shown_pages = [dict(zip(fields, p)) for p in pagedata]
                results.current_page = {'href': None, 'class': 'current',
                                                'string': str(results.page + 1),
                                                                                'title':None}
                if results.has_next_page:
                    next_href=req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=page+1)
                    add_link(req,'next',next_href,_('Next Page'))
                if results.has_previous_page:
                    prev_href=req.href.myproject(pending=pending,approved=approved,rejected=rejected,page=page-1)
                    add_link(req,'prev',prev_href,_('Previous Page'))
                data['page_href']=req.href.myproject()
                data['projects_to_show']=results.items
                data['paginator']=results

                return "my_projects.html",data,None
        else:
            req.redirect(req.href.login())
     
    def _my_approved_projects(self,owner):
        approved_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=1 and owner='%s' order by exam_time desc;"%owner)
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['apply_time']=format_datetime(i[6])
            tmp['exam_time']=format_datetime(i[7])
            tmp['stat']='approved'
            approved_projects.append(tmp)
        return approved_projects
    
    def _my_pending_projects(self,owner):
        pending_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=0 and owner='%s' order by apply_time desc;"%owner)
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['apply_time']=format_datetime(i[6])
            tmp['stat']='pending'
            pending_projects.append(tmp)
        return pending_projects
    
    def _my_rejected_projects(self,owner):
        rejected_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where stat=-1 \
                     and owner='%s' order by exam_time desc;"%\
                     owner)
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['apply_time']=format_datetime(i[6])
            tmp['exam_time']=format_datetime(i[7])
            tmp['stat']='rejected'
            rejected_projects.append(tmp)
        return rejected_projects

    def _all_my_projects(self,owner):
        all_my_projects=[]
        cnx=self.env.get_db_cnx()
        cur=cnx.cursor()
        cur.execute("select * from project where owner='%s'order by id desc;"%owner)
        cur.close()
        cnx.commit()
        cnx.close()
        for i in cur:
            tmp={}
            tmp['proj_full_name']=i[4]
            tmp['proj_name']=i[3]
            if len(i[5])>20:
                tmp['short_description']=i[5][:19]+'...'
            else:
                tmp['short_description']=i[5]
            tmp['description']=i[5]
            tmp['apply_time']=format_datetime(i[6]) #format_datatime(None) is  equal to format_date
            if i[7] is None:
                tmp['exam_time']=''
            else:
                tmp['exam_time']=format_datetime(i[7])
            if i[8]==0:
                tmp['stat']='pending'
            elif i[8]==1:
                tmp['stat']='approved'
            else:
                tmp['stat']='rejected'

            all_my_projects.append(tmp)
        return all_my_projects

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

class ApproveEmailSender(NotifyEmail):
    template_name='approve_a_project.txt'

    def notify(self,username,proj_full_name,apply_time,superuser,exam_time,url):
        self.data.update({
            'username':username,
            'proj_full_name':proj_full_name,
            'apply_time':apply_time,
            'superuser':superuser,
            'exam_time':exam_time,
            'url':url})

    def send(self,email_from,email_to):
        from email.mime.text import MIMEText
        stream = self.template.generate(**self.data)
        body=stream.render('text')
        msg=MIMEText(body,'plain')
        msg.set_charset(self._charset)
        headers={}
        headers['Subject']='A mail from the master trac project!'
        headers['From']=self.env.config.get('notification','smtp_from')
        self.add_headers(msg,headers)
        msgtext=msg.as_string()
        NotificationSystem(self.env).send_email(email_from,email_to,msgtext)
      
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

class RejectEmailSender(ApproveEmailSender):
    template_name='reject_a_project.txt'
    def notify(self,username,proj_full_name,apply_time,superuser,exam_time):
        self.data.update({    
            'username':username,
            'proj_full_name':proj_full_name,
            'superuser':superuser,
            'apply_time':apply_time,
            'exam_time':exam_time,})
 
class DeleteEmailSender(RejectEmailSender):
    template_name='delete_a_project.txt'

