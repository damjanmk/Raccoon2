#       
#           AutoDock | Raccoon2
#
#       Copyright 2013, Stefano Forli
#          Molecular Graphics Lab
#  
#     The Scripps Research Institute 
#           _  
#          (,)  T  h e
#         _/
#        (.)    S  c r i p p s
#          \_
#          (,)  R  e s e a r c h
#         ./  
#        ( )    I  n s t i t u t e
#         '
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import CADD.Raccoon2
#damjan imports
import datetime
import subprocess
from time import sleep
from zipfile import ZipFile

import RaccoonBasics as rb
import RaccoonEvents
import RaccoonServers
import RaccoonServices
import CADD.Raccoon2.HelperFunctionsN3P as hf
import RaccoonProjManTree
import os, Pmw
from PmwOptionMenu import OptionMenu as OptionMenuFix
import Tkinter as tk
import tkMessageBox as tmb
import tkFileDialog as tfd
from PIL import Image, ImageTk
# mgl modules
from mglutil.events import Event, EventHandler
from mglutil.util.callback import CallbackFunction # as cb
from compiler.pycodegen import TRY_FINALLY
#import EF_resultprocessor 
class JobManagerTab(rb.TabBase, rb.RaccoonDefaultWidget):
    """ populate and manage the job manager tab """
    
    def __init__(self, app, parent, debug=False):
        # get
        rb.TabBase.__init__(self, app, debug)
        rb.RaccoonDefaultWidget.__init__(self, parent)
        self.initIcons()
        self.resource = self.app.resource
        # Events
        self.app.eventManager.registerListener(RaccoonEvents.SetResourceEvent, self.handleResource) # set resource
        self.app.eventManager.registerListener(RaccoonEvents.ServerConnection, self._updateRequirementsSsh) # open connection
        #self.app.eventManager.registerListener(RaccoonEvents.UpdateJobHistory, self.updateJobTree)  # job history update
        self.app.eventManager.registerListener(RaccoonEvents.ServiceSelected, self.updateRequirements) # docking service is selected 
        self.app.eventManager.registerListener(RaccoonEvents.UserInputRequirementUpdate, self.updateRequirements) # data input (lig,rec...)
        self.app.eventManager.registerListener(RaccoonEvents.SearchConfigChange, self.updateRequirements) # search config change (box)
        if self.resource == "guse":
            self._buildjobscrollbar()
        else:
            self._buildjobman(self.parent)

    def _buildjobman(self, target):
        """ build the job manager tree"""        
        if hasattr(self, 'pgroup'):
            self.pgroup.pack_forget()        
        self.pgroup = Pmw.Group(target, tag_text = 'Jobs', tag_font=self.FONTbold)
        #tk.Button(pgroup.interior(), text='Refresh', image='self.'
        self.jobtree = RaccoonProjManTree.VSresultTree(self.pgroup.interior(), app = self.app, iconpath=self.iconpath)
        self.pgroup.pack(expand=1, fill='both', anchor='n', side='bottom')
        self.initJobTree()

    def _buildjobscrollbar(self):
        self.pgroup.pack_forget()
        self.pgroup = Pmw.Group(self.parent, tag_text = 'Jobs', tag_font=self.FONTbold)
        scrollbar = tk.Scrollbar(self.pgroup.interior())
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.jobResultListbox = tk.Listbox(self.pgroup.interior())
        self.jobResultListbox.pack(fill=tk.BOTH, expand=1)
        # attach listbox to scrollbar
        self.jobResultListbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.jobResultListbox.yview)
        self.pgroup.pack(expand=1, fill='both', anchor='n', side='bottom')

    def initJobTree(self, event=None):
        """ populate the tree with the history filer"""
        self.jobtree.setDataFile(self.app.getHistoryFile())

    def initIcons(self):
        """ initialize the icons for the interface"""
        self.iconpath = icon_path = CADD.Raccoon2.ICONPATH 
        f = icon_path + os.sep + 'system.png'
        self._ICON_sys = ImageTk.PhotoImage(Image.open(f))
        f = icon_path + os.sep + 'submit.png'
        self._ICON_submit = ImageTk.PhotoImage(Image.open(f))




    def handleResource(self, event=None):
        self.setResource(event.resource)


    def setResource(self, resource):
        '''adapt the job manager panel to reflect currently selected resource'''
        if resource == 'local':
            self.setLocalResource()
        elif resource == 'cluster':
            self.setClusterResource()
        elif resource == 'opal':
            self.setOpalResource()
    #damjan begin
        elif resource == 'guse':
            self.setGuseResource()
           

    def setGuseResource(self):
        self._buildjobscrollbar()
        self.resetFrame()
        self.group = Pmw.Group(self.frame, tag_text = 'gUSE submission requirements', tag_font=self.FONTbold)
        f = self.group.interior()
        #f.configure(bg='red')

        lwidth = 20
        rwidth = 60
        lbg = '#ffffff'
        rbg = '#ff8888'
        fg = 'black'

        # ligands
        tk.Label(f, text='Ligands', width=lwidth, font=self.FONT,anchor='e').grid(row=3, column=1,sticky='e',padx=5, pady=1)
        self.reqLig = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqLig.grid(row=3,column=2, sticky='w', pady=1)
        cb = CallbackFunction(self.switchtab, 'Ligands')
        self.reqLig.bind('<Button-1>', cb)

        # receptor
        tk.Label(f, text='Receptors', width=lwidth, font=self.FONT,anchor='e').grid(row=5, column=1,sticky='e',padx=5, pady=0)
        self.reqRec = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqRec.grid(row=5,column=2, sticky='w')
        cb = CallbackFunction(self.switchtab, 'Receptors')
        self.reqRec.bind('<Button-1>', cb)

        # config
        tk.Label(f, text='Config', width=lwidth, font=self.FONT,anchor='e').grid(row=7, column=1,sticky='e',padx=5, pady=1)
        self.reqConf = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqConf.grid(row=7,column=2, sticky='w', pady=1)
        cb = CallbackFunction(self.switchtab, 'Config')
        self.reqConf.bind('<Button-1>', cb)

        # submission
        self.SubmitButton = tk.Button(f, text = 'Submit...', image=self._ICON_submit, 
            font=self.FONT, compound='left',state='disabled', command=self.submit, **self.BORDER)
        self.SubmitButton.grid(row=20, column=1, sticky='we', columnspan=3, padx=4, pady=3)
        
        self.group.pack(fill='none',side='top', anchor='w', ipadx=5, ipady=5)

        self.frame.pack(expand=0, fill='x',anchor='n')
        self._updateRequirementsGuse()
    #damjan end 
    def setLocalResource(self):
        #self.frame.pack_forget()
        self.resetFrame()
        #self.frame = tk.Frame(self.group.interior())

        tk.Label(self.frame, text='(local) requirement widget 1').pack()
        tk.Label(self.frame, text='(local) requirement widget 2').pack()
        tk.Label(self.frame, text='(local) requirement widget 3').pack()
        tk.Label(self.frame, text='SUBMIT').pack()
        self.frame.pack(expand=1, fill='both')


        #print "Raccoon GUI job manager is now on :", self.app.resource

    def setClusterResource(self):
        self._buildjobman(self.parent)
        self.resetFrame()

        #self.frame.configure(bg='red')
        self.group = Pmw.Group(self.frame, tag_text = 'Cluster submission requirements', tag_font=self.FONTbold)
        f = self.group.interior()
        #f.configure(bg='red')

        lwidth = 20
        rwidth = 60
        lbg = '#ffffff'
        rbg = '#ff8888'
        fg = 'black'
        # server connection
        tk.Label(f, text='Server', width=lwidth, font=self.FONT,anchor='e').grid(row=1, column=1,sticky='e',padx=5, pady=0)
        self.reqConn = tk.Label(f, text = '[ click to connect ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqConn.grid(row=1,column=2, sticky='e')
        cb = CallbackFunction(self.switchtab, 'Setup')
        self.reqConn.bind('<Button-1>', cb)
        
        # XXX self.GUI_LigStatus.bind('<Button-1>', lambda x : self.notebook.selectpage('Ligands')) 

        # docking service
        # ligands
        tk.Label(f, text='Docking service', width=lwidth, font=self.FONT,anchor='e').grid(row=2, column=1,sticky='e',padx=5, pady=1)
        self.reqService = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqService.grid(row=2,column=2, sticky='w', pady=1)
        cb = CallbackFunction(self.switchtab, 'Setup')
        self.reqService.bind('<Button-1>', cb)


        # ligands
        tk.Label(f, text='Ligands', width=lwidth, font=self.FONT,anchor='e').grid(row=3, column=1,sticky='e',padx=5, pady=1)
        self.reqLig = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqLig.grid(row=3,column=2, sticky='w', pady=1)
        cb = CallbackFunction(self.switchtab, 'Ligands')
        self.reqLig.bind('<Button-1>', cb)

        # receptor
        tk.Label(f, text='Receptors', width=lwidth, font=self.FONT,anchor='e').grid(row=5, column=1,sticky='e',padx=5, pady=0)
        self.reqRec = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqRec.grid(row=5,column=2, sticky='w')
        cb = CallbackFunction(self.switchtab, 'Receptors')
        self.reqRec.bind('<Button-1>', cb)

        # config
        tk.Label(f, text='Config', width=lwidth, font=self.FONT,anchor='e').grid(row=7, column=1,sticky='e',padx=5, pady=1)
        self.reqConf = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        self.reqConf.grid(row=7,column=2, sticky='w', pady=1)
        cb = CallbackFunction(self.switchtab, 'Config')
        self.reqConf.bind('<Button-1>', cb)

        # scheduler
        #tk.Label(f, text='Scheduler', width=lwidth, font=self.FONT,anchor='e').grid(row=9, column=1,sticky='e',padx=5, pady=0)
        #self.reqSched = tk.Label(f, text = '[ click to select ]', fg = fg, bg=rbg, width=rwidth, font=self.FONT, **self.BORDER)
        #self.reqSched.grid(row=9,column=2, sticky='w')
        #cb = CallbackFunction(self.switchtab, 'Setup')
        #self.reqSched.bind('<Button-1>', cb)

        # submission
        self.SubmitButton = tk.Button(f, text = 'Submit...', image=self._ICON_submit, 
            font=self.FONT, compound='left',state='disabled', command=self.submit, **self.BORDER)
        self.SubmitButton.grid(row=20, column=1, sticky='we', columnspan=3, padx=4, pady=3)

        self.group.pack(fill='none',side='top', anchor='w', ipadx=5, ipady=5)

        self.frame.pack(expand=0, fill='x',anchor='n')
        self._updateRequirementsSsh()

        #print "Raccoon GUI job manager is now on :", self.app.resource


    def switchtab(self, tab, event=None):
        """ """
        self.app.notebook.selectpage(tab)

    def setOpalResource(self):
        self.resetFrame()
        self.frame = tk.Frame(self.group.interior())
        tk.Label(self.frame, text='(opal) requirement widget 1').pack()
        tk.Label(self.frame, text='(opal) requirement widget 2').pack()
        tk.Label(self.frame, text='(opal) requirement widget 3').pack()
        self.frame.pack(expand=1, fill='both')
        #print "Raccoon GUI job manager is now on :", self.app.resource

    def updateRequirements(self, event=None):
        """ update submission requirements """
        if self.app.resource == 'local':
            self._updateRequirementsLocal(event)
        elif self.app.resource == 'cluster':
            self._updateRequirementsSsh(event)
        elif self.app.resource == 'opal':
            self._updateRequirementsOpal(event)
        #damjan begin
        elif self.app.resource == 'guse':
            self._updateRequirementsGuse(event)
        #damjan end
    
        
    def submit(self, event=None, suggest={}):
        """ find out which EVENT should be triggered and how"""
        #damjan begin
        if self.app.resource == 'guse':
            self.submit_guse()
            return
        #damjan end
        jsub = JobSubmissionInterface(self.frame, jmanager=self.jobtree, app = self.app, suggest=suggest)
        job_info = jsub.getinfo()
        self.app.setBusy()
        if job_info == None:
            self.app.setReady()
            return
        if self.app.resource == 'local':
            self.submit_local(job_info)
        elif self.app.resource == 'cluster':
            self.submit_cluster(job_info)
        elif self.app.resource == 'opal':
            self.submit_opal(job_info)        
        self.app.setReady()
    
    def submit_guse(self):
#         print "\nreceptors: "
        import zipfile
        zreceptors = ZipFile("../receptors.zip", "w")
        # rec
        output_names_content = ""
        i = 1
        for r in self.app.engine.RecBook.keys():
            #receptor_name = "receptor" + str(i)
            zreceptors.write(self.app.engine.RecBook[r]['filename'], arcname=os.path.splitext(os.path.basename(self.app.engine.RecBook[r]['filename']))[0] + ".pdbqt")
            i = i + 1
            # ligand 
            llib = self.app.ligand_source
            for a in llib:
                temp_lib = a['lib']
                for b in temp_lib.get_ligands():
                    output_names_content += os.path.splitext(os.path.basename(self.app.engine.RecBook[r]['filename']))[0] + "_" + os.path.splitext(os.path.basename(b))[0] + "_out.pdbqt" + os.linesep

        zreceptors.close()

        o = open("../output_names.txt", "w")
        o.write(output_names_content)
        o.close()

        # conf
#         print "\nconf: "
#         print self.app.engine.vina_settings
        config_content = ""
        for keyword in self.app.engine.vina_settings["KEYWORD_ORDER"]:
            if keyword == "cpu" or keyword == "out":
                continue
            if keyword in self.app.engine.vina_settings["OPTIONAL"]:
                if self.app.engine.vina_settings["OPTIONAL"][keyword] == False:
                    continue                    
            else:
                config_content += keyword + " = " + str(self.app.engine.vina_settings[keyword]) + os.linesep
        f = open("../conf.txt", "w")
        f.write(config_content)
        f.close()
        self.RunGuse(self.app.engine.guseRemoteAPIURL.get(), self.app.engine.guseCredentialsId.get(), self.app.engine.guseRemoteAPIPassword.get(), 
                     self.app.engine.gusePortalUsername.get(), self.app.engine.gusePortalPassword.get())


    def prepareVinaOutputNamesZip(self):
        zin = ZipFile('../gUSE-cloud-vina.zip', 'r')
        zout = ZipFile('../gUSE-cloud-vina-new.zip', 'w')    
        workflow_xml = zin.read('workflow.xml')    
        zin.close()

        import xml.etree.ElementTree as ET
        root = ET.fromstring(workflow_xml)     
        workflow_xml_resourcename = root.find(".//execute[@key='resourcename']")
        workflow_xml_resourcename.set("value", self.app.engine.guseWhichCloudEncoded.get())
        workflow_xml_regionname = root.find(".//execute[@key='regionname']")
        workflow_xml_regionname.set("value", self.app.engine.guseWhichCloudRegionEncoded.get())        
        workflow_xml_instancetypename = root.find(".//execute[@key='instancetypename']")
        workflow_xml_instancetypename.set("value", self.app.engine.guseWhichCloudInstanceEncoded.get())
        
        zout.writestr("workflow.xml", ET.tostring(root, "utf-8"))
        zout.write("../ligands.zip", arcname="vina_output_names/4in1out/inputs/0/0")  
        zout.write("../receptors.zip", arcname="vina_output_names/4in1out/inputs/1/0")
        zout.write("../conf.txt", arcname="vina_output_names/4in1out/inputs/2/0")
        zout.write("../output_names.txt", arcname="vina_output_names/4in1out/inputs/3/0")
        
        zout.close()
        
        os.remove("../gUSE-cloud-vina.zip")
        os.rename("../gUSE-cloud-vina-new.zip", "../gUSE-cloud-vina.zip")    
    
    def process_detailsinfo(self, wfstatus, startTime):    
        i = 0
        init = 0
        running = 0
        finished = 0
        error = 0
        returnVal = 0 # 0 - suspended, not valid data. 1 - finished, error. 2 - submitted, running.
        for wfstatusSegment in wfstatus.split(";"):        
            if i == 0:
                if wfstatusSegment == "submitted":
                    self.jobResultListbox.insert(tk.END, "Raccoon execution via gUSE submitted.")
                    returnVal = 2
                elif wfstatusSegment == "running":
                    self.jobResultListbox.insert(tk.END, "Raccoon execution via gUSE running...")               
                    returnVal = 2
                elif wfstatusSegment == "finished":
                    self.jobResultListbox.insert(tk.END, "Raccoon execution via gUSE finished successfully!")
                    self.jobResultListbox.insert(tk.END, "Please open the folder \'gUSE-cloud-vina-filtered-results-\' + today\'s date (timestamp) to view the results.")
                    returnVal = 1
                elif wfstatusSegment == "error":
                    self.jobResultListbox.insert(tk.END, "Part of the Raccoon execution on the cloud had errors.")
                    returnVal = 1
                elif wfstatusSegment == "suspended":
                    self.jobResultListbox.insert(tk.END, "Raccoon execution via gUSE stopped by administrator")
                elif wfstatusSegment == "not valid data":
                    self.jobResultListbox.insert(tk.END, "Data for Raccoon execution via gUSE not valid")
                currentTime = datetime.datetime.now()                
                timeDifference = currentTime - startTime
                self.jobResultListbox.insert(tk.END, "Execution time: " + str(timeDifference))
            else:
                for jobstatus in wfstatusSegment.split(":"):
                    jobstatusList = jobstatus.split("=")            
                    if jobstatusList[0] == "init":
                        init = init + int(jobstatusList[1])
                    elif jobstatusList[0] == "running":
                        running = running + int(jobstatusList[1])
                    elif jobstatusList[0] == "finished":
                        finished = finished + int(jobstatusList[1])
                    elif jobstatusList[0] == "error":
                        error = error + int(jobstatusList[1])                    
            i = i + 1
        total = str(init + running + finished + error)    
        if init > 0:
            isare = "are"
            if init == 1:
                isare = "is"
                self.jobResultListbox.insert(tk.END, str(init) + "/" + total + " jobs " + isare + " initialising...")
            
        if running > 0:
            isare = "are"
            if running == 1:
                isare = "is"
            self.jobResultListbox.insert(tk.END,  str(running) + "/" + total + " jobs " + isare + " running...")
        if finished > 0:
            hashave = "have"
            if finished == 1:
                hashave = "has"
            self.jobResultListbox.insert(tk.END,  str(finished) + "/" + total + " jobs " + hashave + " finished.")
        if error > 0:        
            self.jobResultListbox.insert(tk.END,  str(error) + "/" + total + " jobs had some errors.")
        
        self.jobResultListbox.see(tk.END)    # scroll down automatically
        #self.jobResultListbox.insert(tk.END,  wfstatus + os.linesep)
        print wfstatus
        self.frame.update()
        return returnVal
    
    
    def RunGuse(self, gUSEurl, CredentialsId, RemoteAPIPassword, PortalUsername, PortalPassword):        
        # make certs.zip
        GuseAuthenticationFileName = 'x509up.' + CredentialsId
        authenticationFile = open(GuseAuthenticationFileName, 'w')
        authenticationFile.write("password=" + PortalPassword + os.linesep + "username=" + PortalUsername)
        authenticationFile.close()
        GuseCertsZip = ZipFile("../certs.zip", 'w')
        GuseCertsZip.write(GuseAuthenticationFileName)
        GuseCertsZip.close()
        os.remove(GuseAuthenticationFileName)
         
        self.prepareVinaOutputNamesZip()    
        workflowZip = "gUSE-cloud-vina.zip"
            
        self.jobResultListbox.insert(tk.END, "Submitting " + workflowZip + " via gUSE")
        self.frame.update()                
        guse_submit = subprocess.check_output(['curl', '-k', '-s', '-S', '-F', 'm=submit', '-F', 'pass=' + RemoteAPIPassword, '-F', 'gusewf=@../' + workflowZip, '-F', 'certs=@../certs.zip', gUSEurl])
        wfid = guse_submit.rstrip()        
        print 'wfid = ' + wfid
        currentTime = datetime.datetime.now()     
        print currentTime
        while True:
            guse_info = subprocess.check_output(['curl', '-k', '-s', '-S', '-F', 'm=detailsinfo', '-F', 'pass=' + RemoteAPIPassword, '-F', 'ID=' + wfid, gUSEurl])
            wfstatus = guse_info.rstrip()            
            wfstate = self.process_detailsinfo(wfstatus, currentTime)
            #break
            if wfstate == 0:
                break
            elif wfstate == 1:
                    with open('../gUSE-cloud-vina-results.zip', "w") as redirect_to_file:
                        subprocess.call(['curl', '-k', '-s', '-S', '-F', 'm=download', '-F', 'pass=' + RemoteAPIPassword, '-F', 'ID=' + wfid, gUSEurl], stdout=redirect_to_file)
                    
                    timestamp = datetime.datetime.now().strftime("%d-%m-%y--%H-%M-%S-%f")
                    
                    z = ZipFile('../gUSE-cloud-vina-results.zip', 'r')
                    temporary_folder = "res" + timestamp
                    os.mkdir(temporary_folder)
                    z.extractall(temporary_folder, filter(lambda f: f.endswith('output.zip'), z.namelist()))
                    output_zip_name_path = ""
                    for name in z.namelist():
                        if name.endswith("output.zip"):
                            output_zip_name_path = name
                    z.close()
                    if output_zip_name_path == "":
                        print "Error in downloading results or in the job"
                    else:
                        z = ZipFile(temporary_folder + os.sep + output_zip_name_path)
                        results_folder = "../gUSE-cloud-vina-results-" + timestamp
                        os.mkdir(results_folder)
                        z.extractall(results_folder, filter(lambda f: f.endswith(('.pdbqt_log.txt', '.pdbqt')), z.namelist()))
                        z.close()
                    
                        os.remove(temporary_folder + os.sep + output_zip_name_path)
                        last_separator = output_zip_name_path.rfind(os.sep)
                        os.removedirs(temporary_folder + os.sep + output_zip_name_path[0:last_separator])

                    os.remove("../ligands.zip")
                    os.remove("../receptors.zip")
                    os.remove("../conf.txt")
                    os.remove("../output_names.txt")
                    os.remove("../certs.zip")    
                    break                        
            else:            
                sleep(20)
    
    def submit_local(self, job_info):
        """ manage submission and feedback from local resource"""
        report = self.app.submitLocal(job_info)

    def submit_opal(self, job_info):
        """ manage submission and feedback from Opal resource"""
        report = self.app.submitOpal(job_info)

    def submit_cluster(self, job_info):
        """ manage submission and feedback from Ssh cluster resource"""
        # report = { 'submissions': [], 'server_duplicates' : [], 'local_duplicates' : [] }
        report = self.app.testSshJobs(job_info)
        sdup = report['server_duplicates']
        ldup = report['local_duplicates']
        choice = 'skip'
        #print "\n\n\nREPORT FOR DUPLICATES", report
        #print "\n\n\n"
        if len(sdup) or len(ldup):
            #print "WE HAVE DUPLICATES>", len(sdup), len(ldup)
            choice = ManageJobOverlaps(self.frame, report)
            #buttons = ('Skip', 'Modify tag', 'Auto-rename', 'Overwrite', 'Cancel'),
            if choice == 'tag':
                t = 'Submission'
                i = 'info'
                m = 'Repeat the submission specifying a different tag.'
                tmb.showinfo(parent=self.frame, title=t, message=m, icon=i)
                return
        # XXX close here the job submission manager
        if choice == 'cancel':
            return

        self.app.setBusy()
        submission = self.app.submitSsh(job_info, duplicates=choice)
        s = len(submission)
        if s>0:
            t = 'Submission'
            i = 'info'
            m = '%d jobs submitted successfully.' % (s / 2)
            tmb.showinfo(parent=self.frame, title=t, message=m, icon=i)
            self.app.setReady()
            return True
        else:
            t = 'Submission'
            i = 'error'
            m = 'No jobs have been submitted!'
            tmb.showinfo(parent=self.frame, title=t, message=m, icon=i)
            self.app.setReady()
            return False

    def _updateRequirementsLocal(self, event=None):
        """ update the check for requirements 
            of local submission
        """
        _type = event._type
        pass

    def _updateRequirementsGuse(self, event=None):
        g = 'black'
        r = 'red'
        d = '[ click to select ]'
        green = '#99ff44'
        red = '#ff4444'
        orange = '#ffcc44'

        missing = False
                
        # ligand 
        if len(self.app.ligand_source):
            libnames = ",".join([x['lib'].name() for x in self.app.ligand_source])
            t = "library selected (%s)" % libnames
            self.reqLig.configure(fg = g, text = t, bg = green)
        else:
            missing = True
            self.reqLig.configure(fg = g, text = d, bg = red)
        # rec
        if len(self.app.engine.receptors()) > 0:
            t = "%s receptors selected" % len(self.app.engine.receptors())
            self.reqRec.configure(fg = g, text = t, bg = green)
        else:
            missing = True
            self.reqRec.configure(fg = g, text = d, bg = red)
        # conf
        conf = self.app.engine.gridBox()
        if not None in conf['center'] + conf['size']:
            t = "search box defined"
            self.reqConf.configure(fg = g, text = t, bg = green)
            c = g
        else:
            missing = True
            self.reqConf.configure(fg = g, text = d, bg = red)
        if not missing:
            self.SubmitButton.configure(state='normal')
    
    def _updateRequirementsSsh(self, event=None):
        """ update the check for requirements 
            of ssh submission
        """
        g = 'black'
        r = 'red'
        d = '[ click to select ]'
        green = '#99ff44'
        red = '#ff4444'
        orange = '#ffcc44'

        missing = False
        #_type = event._type
        # check connection
        if not self.app.server == None:
            t = "connected to %s" % self.app.server.properties['name']
            # check racconized
            if self.app.server.properties['ready']:
                self.reqConn.configure(text = t, bg = green)
            else:
                t = "connected to %s (NOT RACCONIZED!)" % self.app.server.properties['name']
                self.reqConn.configure(text = t, bg = orange)
                missing = True
        else:
            missing = True
            self.reqConn.configure(text = d, bg = red)

        if not self.app.dockingservice == None:
            t = '%s' % self.app.dockingservice
            self.reqService.configure(text = t, bg = green)
        else:
            missing = True
            self.reqService.configure(text = d, bg = red)
        
        # ligand 
        if len(self.app.ligand_source):
            libnames = ",".join([x['lib'].name() for x in self.app.ligand_source])
            t = "library selected (%s)" % libnames
            self.reqLig.configure(fg = g, text = t, bg = green)
        else:
            missing = True
            self.reqLig.configure(fg = g, text = d, bg = red)
        # rec
        if len(self.app.engine.receptors()) > 0:
            t = "%s receptors selected" % len(self.app.engine.receptors())
            self.reqRec.configure(fg = g, text = t, bg = green)
        else:
            missing = True
            self.reqRec.configure(fg = g, text = d, bg = red)
        # conf
        conf = self.app.engine.gridBox()
        if not None in conf['center'] + conf['size']:
            t = "search box defined"
            self.reqConf.configure(fg = g, text = t, bg = green)
            c = g
        else:
            missing = True
            self.reqConf.configure(fg = g, text = d, bg = red)
        # sched
        #if not self.app.server == None:
        #    sched = self.app.server.systemInfo('scheduler')
        #else:
        #    missing = True
        # submit
        if not missing:
            self.SubmitButton.configure(state='normal')

    def _updateRequirementsOpal(self, event=None):
        """ update the check for requirements 
            of opal submission
        """
        _type = event._type
        pass

class JobSubmissionInterface(rb.RaccoonDefaultWidget):
    """ ask for Project, Exp, VS info..."""

    def __init__(self, parent, jmanager, app, suggest={}):
        """ parent      : tkparent
            jmanager    : job manager tree (to query current prj,exp...)
            app         : containing app
        """
        rb.RaccoonDefaultWidget.__init__(self, parent)
        self.jmanager = jmanager
        self.app = app
        self._new = '<new>'
        self.jobdata = None
        self.suggest = suggest
        self.initIcons()
        self.build()

    def initIcons(self):
        pass

    def close(self, result):
        """ close the window and decides what to do
            if OK requested, check values and start submission
        """
        if result == 'OK':
            if not self.checkinfo():
                return
            p = self.getPrj()
            e = self.getExp()
            t = self.tag_entry.getvalue().strip()
            self.jobdata = {'prj' : p, 'exp': e, 'tag':t} 
            self.win.deactivate(self.jobdata)
        else:
            self.win.deactivate(False)

    def getPrj(self):
        """ return the project name"""
        m = ('The project name is not valid.\n')
        p = self.prj_pull.getvalue() # old project
        if p == self._new:
            if not self.prj_new.valid():
                self.errorMsg(m)
                return False
            p = self.prj_new.getvalue()
        return p

    def getExp(self):
        """ return the experiment name"""
        m = ('The experiment name is not valid.\n')
        e = self.exp_pull.getvalue() # old project
        if e == self._new:
            if not self.exp_new.valid():
                self.errorMsg(m)
                return False
            e = self.exp_new.getvalue()
        return e

    def getTag(self):
        """ return the tag"""
        tag = self.tag_entry.getvalue()
        return tag


    def checkDuplicates(self):
        """ check that the jobs that are going to be 
            submitted do not have the same name of 
            already submitted jobs
        """
        m = ('The submission cannot be performed because there '
             'are already jobs with the same name stored in project %s '
             '/experiment %s.\n\n'
             'Either create new project/experiments or use a different tag.')
        job_info = {'prj' : self.getPrj(),
                    'exp' : self.getExp(),
                    'tag' : self.getTag()
                   }
        report = self.app.testSshJobs(job_info)
        e = []
        if len(report['server_duplicates']):
            e.append('the current server')
        if len(report['local_duplicates']):
            e.append('the local client')
        if len(e):
            m = m % ( job_info['prj'], job_info['exp'])
            self.errorMsg(m)
            return False
        return True

    def checkinfo(self):
        """ check that user provided info are valid"""
        if not self.getPrj():
            return False
        if not self.getExp():
            return False
        if not self.checkDuplicates():
            return False
        return True


    def errorMsg(self, message):
        """ display submission entries error"""
        t = 'Incorrect name entry'
        i = 'error'
        tmb.showinfo(parent=self.win.interior(), title=t, message=message, icon=i)
        return


    def getinfo(self):
        """ return the user provided info"""
        return self.jobdata


    def _setprjname(self, event=None):
        choice = self.prj_pull.getvalue()
        if choice == self._new:
            self.prj_new.grid(row=4, column=2, sticky='we',padx=4,pady=4)
            self.prj_new.checkentry()
        else:
            self.prj_new.grid_forget()
        exp_list = self._getexplist()
        self.exp_pull.setitems( exp_list )
        self.exp_pull.setvalue( exp_list[-1])
        self.exp_pull.invoke()

    def _getexplist(self, event=None):
        prj = self.prj_pull.getvalue()
        if prj == self._new:
            return [self._new]
        else:
            exp_list = sorted(self.info[prj].keys())
            return exp_list + [self._new]

    def _setexpname(self, event=None):
        choice = self.exp_pull.getvalue()
        if choice == self._new:
            self.exp_new.grid(row=8,column=2, sticky='we', padx=4,pady=4)
            self.exp_new.checkentry()
        else:
            self.exp_new.grid_forget()

    def build(self):
        # get info from the current manager
        self.info = self.jmanager.getTreeGraph()
        self.prj_list = sorted(self.info.keys()) + [self._new]
        #self.prj_list.append(self._new)
        self.win = Pmw.Dialog(parent=self.parent, buttons=('OK', 'Cancel'),
            title = 'Submit jobs', command = self.close)
        w = self.win.interior()
        bbox = self.win.component('buttonbox')
        for i in range(bbox.numbuttons()):
            bbox.button(i).configure(font=self.FONT, default='disabled', **self.BORDER)

        tk.Label(w, text='Select the new VS properties', font=self.FONT).grid(row=0,column=1, sticky='we', columnspan=3,padx=5,pady=5)
        tk.Frame(w,height=2,bd=1,relief='sunken').grid(row=1, column=0, sticky='ew', columnspan=3, pady=3)
        # project 
        tk.Label(w, text='Project', font=self.FONTbold, width=12,anchor='e').grid(row=3,column=1,sticky='we')
        tk.Label(w, text='', font=self.FONT, width=10).grid(row=4,column=1,sticky='we',pady=5) # placeholder for entry

        self.prj_pull = OptionMenuFix(w,
               menubutton_width=30,
               menubutton_font=self.FONT,
               menu_font=self.FONT,
               menubutton_bd = 1, menubutton_highlightbackground = 'black',
               menubutton_borderwidth=1, menubutton_highlightcolor='black', 
               menubutton_highlightthickness = 1,
               menubutton_height=1,
               items = self.prj_list,
               initialitem=-1,
               command = self._setprjname)
        self.prj_pull.grid(row=3,column=2,sticky='we',padx=3)

        self.prj_new = Pmw.EntryField(w, value='', validate = {'validator' : hf.validateAscii, 'minstrict': 0}) #,
        self.prj_new.component('entry').configure(justify='left', font=self.FONT, bg='pink',width=33, **self.BORDER)

        # --------------------------------
        tk.Frame(w,height=2,bd=1,relief='sunken').grid(row=6, column=0, sticky='ew', columnspan=3, pady=3)
        
        # experiment
        tk.Label(w, text='Experiment', font=self.FONTbold, width=12,anchor='e').grid(row=7,column=1,sticky='we')
        tk.Label(w, text='', font=self.FONT, width=10).grid(row=8,column=1,sticky='we',pady=5) # placeholder for entry

        self.exp_pull = OptionMenuFix(w,labelpos='w',
                       menubutton_width=30,
                       menubutton_font=self.FONT,
                       menu_font=self.FONT,
               menubutton_bd = 1, menubutton_highlightbackground = 'black',
               menubutton_borderwidth=1, menubutton_highlightcolor='black', 
               menubutton_highlightthickness = 1,
               menubutton_height=1,
                       items=[self._new],
                       initialitem=-1,
                       command = self._setexpname)
        self.exp_pull.grid(row=7, column =2, sticky='we',padx=3)
        self.exp_new = Pmw.EntryField(w, value='', validate = {'validator' : hf.validateAscii, 'minstrict':0}) #,
        self.exp_new.component('entry').configure(justify='left', font=self.FONT, bg='pink',width=30, **self.BORDER)
        # initialize the interface with the projects
        self._setprjname()
        self.prj_pull.setvalue( self.prj_list[-1])

        # --------------------------------
        tk.Frame(w,height=2,bd=1,relief='sunken').grid(row=9, column=0, sticky='ew', columnspan=3, pady=3)
        # job tag 
        tk.Label(w, text='Optional jobs name tag', font=self.FONT).grid(row=10, column=1,columnspan=3,sticky='we',padx=5)
        self.tag_entry = Pmw.EntryField(w, value='', validate = hf.validateAsciiEmpty) #,
        self.tag_entry.component('entry').configure(justify='left', font=self.FONT, bg='white',width=30, **self.BORDER)
        self.tag_entry.grid(row=11,column=1, columnspan=3, sticky='we', padx=4,pady=4)

        self.win.bind('<Escape>', self.close)
        self.setSuggest()
        self.win.activate()


    def setSuggest(self):
        """ fill the submission with the suggestions"""
        if self.suggest == {}:
            return
        if 'prj' in self.suggest.keys():
            prj = self.suggest.pop('prj')
            self.prj_pull.setvalue(prj)
            self.prj_pull.invoke()
        if 'exp' in self.suggest.keys():
            exp = self.suggest.pop('exp')
            self.exp_pull.setvalue(exp)
            self.exp_pull.invoke()
        if 'tag' in self.suggest.keys():
            tag = self.suggest.pop('tag')
        else:
            tag = 'RESTARTED'
        self.tag_entry.setvalue(tag)




class ManageJobOverlaps(rb.RaccoonDefaultWidget):
    
    
    def __init__(self, parent, duplicates):
        rb.RaccoonDefaultWidget.__init__(self, parent)
        self.count = count
        #self.names = names
        self.remotenames = duplicates['server_duplicates']
        self.localnames = duplicates['local_duplicates']
        self.dialog = Pmw.Dialog(parent,
            buttons = ('Skip', 'Modify tag', 'Auto-rename', 'Overwrite', 'Cancel'),
            default_button = 'Modify tag',
            title = 'Jobs naming issues',
            command = self.execute)
        self.dialog.withdraw()
        d = self.dialog.interior()

        msg = ("The following jobs to be generated are going to "
               "overwrite jobs with the same names already "
               "present on the server.")
        pack_def = { 'side': 'top', 'anchor':'n', 'expand':0, 'fill':'x'}
        tk.Label(d, text = msg).pack(**pack_def)
        if len(self.remotenames):
            slb = Pmw.ScrolledListBox(d, listbox_font=self.FONT, items = self.remotenames,
                label_text = 'Server job names', labelpos='nw', label_font=self.FONTbold,
                listbox_selectmode='EXTENDED')
            slb.pack(side='left', anchor='w', expand='1', fill='both')
        if len(self.localnames):
            llb = Pmw.ScrolledListBox(d, listbox_font=self.FONT, items = self.localnames,
                label_text = 'Local job names', labelpos='nw', label_font=self.FONTbold,
                listbox_selectmode='EXTENDED')
            llb.pack(side='left', anchor='w', expand='1', fill='both')
        self.dialog.activate(globalMode=1)

        
    def execute(self, result):
        if result == 'Overwrite':
            t = 'Overwrite jobs'
            i = 'warning'
            m = ('Are you sure you want to overwrite %d jobs?' % len(names) )
            if not tmb.askyesno(parent=self.parent, title=t, icon=i, message=m):
                return
            choice == 'overwrite'
        elif result == 'Skip':
            choice = 'skip'
        elif result == 'Modify tag':
            choice = 'tag'
        elif result == 'Auto-rename':
            choice = 'rename'
        elif result == 'Cancel':
            choice = 'cancel'
        self.dialog.deactivate(choice)
            
