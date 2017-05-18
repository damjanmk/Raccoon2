import datetime
import threading
from time import sleep
from zipfile import ZipFile
import pycurl
from StringIO import StringIO
import os
import shutil
import xml.etree.ElementTree as ET

class gUseThread(threading.Thread):
    def __init__(self, queue, app):
        self.app = app
        threading.Thread.__init__(self)
        self.queue = queue
        self.resultFolderName = self.app.engine.guseResultFolderName
        
    def run(self):
        """ Starts the new thread that creates the correct input files and starts running and processing workflows        
        """
        # create the certs authentication file
        self.createCertsZip(self.app.engine.guseCredentialsId.get(), self.app.engine.gusePortalUsername.get(), self.app.engine.gusePortalPassword.get())
        
        # create a receptors.zip file and write all attached receptors to it,
        # and create output_names.txt as a string
        zreceptors = ZipFile(".." + os.sep + "receptors.zip", "w") 
        output_names_content = ""
        # needed for properly splitting the workflows later
        numberOfLigands = 0
        # attached receptors stored in RecBook as attributes to the keys
        for r in self.app.engine.RecBook.keys():
            # write each receptor to the receptors.zip
            zreceptors.write(self.app.engine.RecBook[r]['filename'], arcname=os.path.splitext(os.path.basename(self.app.engine.RecBook[r]['filename']))[0] + ".pdbqt")
            # loop through all ligands and create the output_names.txt file
            # data structure is a little comples - *could be done more efficiently
            llib = self.app.ligand_source
            for a in llib:
                temp_lib = a['lib']
                for ligandPath in temp_lib.get_ligands():
                    # fill in the string for output_names.txt
                    output_names_content += os.path.splitext(os.path.basename(self.app.engine.RecBook[r]['filename']))[0] + "_" + os.path.splitext(os.path.basename(ligandPath))[0] + "_out.pdbqt" + os.linesep
                    numberOfLigands = numberOfLigands + 1    
        zreceptors.close()
        #store the string into a txt file
        output_names_file = open(".." + os.sep + "output_names.txt", "w")
        output_names_file.write(output_names_content)
        output_names_file.close()
 
        # process the selected configuration (conf)
        config_content = ""
        for keyword in self.app.engine.vina_settings["KEYWORD_ORDER"]:
            # ignore 'cpu' or 'out' or some other options
            if keyword == "cpu" or keyword == "out":
                continue
            if keyword in self.app.engine.vina_settings["OPTIONAL"]:
                if self.app.engine.vina_settings["OPTIONAL"][keyword] == False:
                    continue                    
            # otherwise, write each conf option as a key = value pairs in a new line (as per Vina conf format) 
            else:
                config_content += keyword + " = " + str(self.app.engine.vina_settings[keyword]) + os.linesep
        # write string into a txt file 
        conf = open(".." + os.sep + "conf.txt", "w")
        conf.write(config_content)
        conf.close()
        
        # calculate how many ligands per instance should be used based on 
        # the number of instances selected (this number is the same as number of folders) 
        instances = int( self.app.engine.guseNumberOfInstances.get() )
        print instances        
        numberOfLigandsPerFolder = numberOfLigands / instances
        modLigandsPerFolder = numberOfLigands % instances 
        i = 0;
        # create a new folder for each instance and fill it with the (copied) input files 
        for numberOfInstance in range(0, instances):
            newFolderName = self.resultFolderName + os.sep + "files" + str(numberOfInstance)
            shutil.copy(".." + os.sep + "receptors.zip", newFolderName + os.sep)
            shutil.copy(".." + os.sep + "conf.txt", newFolderName + os.sep)
            addToLimit = 0
            if modLigandsPerFolder > 0:
                addToLimit = 1
                modLigandsPerFolder = modLigandsPerFolder - 1
            
            # make a new smaller output_names.txt for each folder only
            output_names_file = open(newFolderName + os.sep + "output_names.txt", "w")
            currentLine = 0
            for line in output_names_content.split(os.linesep):
                if currentLine >= i:
                    if currentLine - i < numberOfLigandsPerFolder + addToLimit:
                        output_names_file.write(line + os.linesep)
                    else:
                        break
                currentLine = currentLine + 1
            output_names_file.close()            
            i = i + numberOfLigandsPerFolder + addToLimit
            
        self.prepareWorkflows(instances)
        self.runGuse(self.app.engine.guseRemoteAPIURL.get(), self.app.engine.guseRemoteAPIPassword.get(), instances)
                
    def createCertsZip(self, CredentialsId, PortalUsername, PortalPassword):
        """ Create the certs zip file needed by the gUSE RemoteAPI for authentication 
        
        Arguments:        
        CredentialsId -- the name of the resource, called credentialsID, in case of a cloud the name of the specific cloud subgroup
        PortalUsername -- in case of basic authentication, the username for the CloudBroker user
        PortalPassword -- in case of basic authentication, the password for the CloudBroker user        
        
        Create the properly formatted certs.zip as requested by WS-PGRADE convention  
        """
        # although the X.509 is not used, by convention, this file has to be named x509up.<credentialsID>
        GuseAuthenticationFileName = 'x509up.' + CredentialsId
        # open it, and write exactly:
        # password=<portal_password>
        # username=<portal_username>
        authenticationFile = open(GuseAuthenticationFileName, 'w')
        authenticationFile.write("password=" + PortalPassword + os.linesep + "username=" + PortalUsername)
        authenticationFile.close()
        # put this file into a zip archive, name it 'certs.zip' (the name of the zip file can be anything)
        GuseCertsZip = ZipFile(".." + os.sep + "certs.zip", 'w')
        GuseCertsZip.write(GuseAuthenticationFileName)
        GuseCertsZip.close()
        # remove the x509up.<credentialsID> file, it is not needed anymore
        os.remove(GuseAuthenticationFileName)

    def prepareWorkflows(self, numberOfFolders):
        """ Prepare all workflow.xml files and properly organise all the workflow zip files according to WS-PGRADE convention 
        
        Arguments:        
        numberOfFolders -- int, number of folders and workflows needed
        
        For each folder in numberOfFolders, copy the workflow.xml from ...gUSE-cloud-vina.zip and alter it to include
        - resourcename as chosen by the user
        - regionname as chosen by the user
        - instancetypename as chosen by the user
        Then form the correct workflow zip file, all according to WS-PGRADE convention  
        """
        # read the properly formed WS-PGRADE zip file to read from
        zin = ZipFile('..' + os.sep + 'gUSE-cloud-vina.zip', 'r')
        # read the WS-PGRADE workflow.xml of that file            
        workflow_xml = zin.read('workflow.xml')    
        zin.close()
        # loop through all folders in numberOfFolders and create a correct workflow.xml and properly organised workflow zip
        for folderNumber in range(0, numberOfFolders):
            folderNumber = str(folderNumber)
            zout = ZipFile(self.resultFolderName + os.sep + "files" + folderNumber + os.sep + 'gUSE-cloud-vina.zip', 'w')
            # find the needed xml elements in workflow.zip:
            # <execute desc="null" inh="null" key="regionname" label="null" value="94245f0d-fd8b-4034-bbd8-f662cfd006aa" />
            # <execute desc="null" inh="null" key="instancetypename" label="null" value="a38839e9-8b14-45b2-8485-4cdaec584f63" />
            # <execute desc="null" inh="null" key="resourcename" label="null" value="5d9a4557-4cb4-48b9-bdc9-25c0fe8bb59d" />    
            root = ET.fromstring(workflow_xml)
            # find the resourcename attribute and set its value to ...guseWhichCloudEncoded
            workflow_xml_resourcename = root.find(".//execute[@key='resourcename']")
            workflow_xml_resourcename.set("value", self.app.engine.guseWhichCloudEncoded.get())
            # find the regionname attribute and set its value to ...guseWhichRegionCloudEncoded
            workflow_xml_regionname = root.find(".//execute[@key='regionname']")
            workflow_xml_regionname.set("value", self.app.engine.guseWhichCloudRegionEncoded.get())
            # find the instancetypename attribute and set its value to ...guseWhichCloudInstanceEncoded
            workflow_xml_instancetypename = root.find(".//execute[@key='instancetypename']")
            workflow_xml_instancetypename.set("value", self.app.engine.guseWhichCloudInstanceEncoded.get())
            # write the altered xml tree into workflow.xml in zout
            zout.writestr("workflow.xml", ET.tostring(root, "utf-8"))
            # write the 4 input files in zout
            zout.write(self.resultFolderName + os.sep + "files" + folderNumber + os.sep + "ligands.zip", arcname="vina_output_names/4in1out/inputs/0/0")  
            zout.write(self.resultFolderName + os.sep + "files" + folderNumber + os.sep + "receptors.zip", arcname="vina_output_names/4in1out/inputs/1/0")
            zout.write(self.resultFolderName + os.sep + "files" + folderNumber + os.sep + "conf.txt", arcname="vina_output_names/4in1out/inputs/2/0")
            zout.write(self.resultFolderName + os.sep + "files" + folderNumber + os.sep + "output_names.txt", arcname="vina_output_names/4in1out/inputs/3/0")
            zout.close()
    
    def runGuse(self, gUSEurl, RemoteAPIPassword, numberOfFolders):
        """ Submit all workflows in self.resultFolderName + os.sep + "files" + folderName + os.sep + "gUSE-cloud-vina.zip"
        
        Arguments:
        gUSEurl -- the URL to the gUSE server, will be passed to RemoteApiSubmit()
        RemoteAPIPassword -- the RemoteAPI password of the gUSE server, will be passed to RemoteApiSubmit()
        numberOfFolders -- int, number of folders and workflows needed  
        """
        wfidsList = list()
        # used when calculating the Execution time for each workflow
        self.startTime = datetime.datetime.now()
        # loop through all folders and submit workflows
        for folderName in range(0, numberOfFolders):
            folderName = str(folderName)
            workflowZip = self.resultFolderName + os.sep + "files" + folderName + os.sep + "gUSE-cloud-vina.zip"
            # call the RemoteAPI 'submit' method
            wfid = self.RemoteApiSubmit(gUSEurl, RemoteAPIPassword, workflowZip, ".." + os.sep + "certs.zip")
            # to be written on the panel
            self.queue.put("Submitted " + workflowZip + " via gUSE")
            # wfid must be trimmed (stripped); it is the worfklowID of the newly submitted workflow which is added to the wfidsList
            wfidsList.append(wfid.strip())
            print 'wfid = ' + wfid
            # to prevent DDOS timeouts of the server, wait for 10 seconds
            sleep(10)
        # once done with submitting all the workflows, call processGuseStatus for all of them (using the wfidsList)
        self.processGuseStatus(wfidsList, RemoteAPIPassword, gUSEurl)
    
    def RemoteApiSubmit(self, gUSEurl, RemoteAPIPassword, workflowZip, certs):
        """ Call gUSE RemoteAPI, method='submit'
        
        Arguments:
        gUSEurl -- the URL of the gUSE server
        RemoteAPIPassword -- the RemoteAPI password as defined on the gUSE server
        workflowZip -- the well-formed zip archive of the WS-PGRADE workflow
        certs -- the zip file containing the gUSE authentication file
        
        Returns:
        The workflowID of the submitted (newly created) workflow e.g. 1492944544633364
        
        This method uses pycurl to send a HTTP request to the gUSE server at gUSEurl, and submit
        a workflow which is define din workflowZip. It is equivalent to
        guse_submit = subprocess.check_output(['curl', '-k', '-s', '-S', '-F', 'm=submit', '-F', 'pass=' + RemoteAPIPassword, '-F', 'gusewf=@' + workflowZip, '-F', 'certs=@' + certs, gUSEurl])
            
        Raises pycurl.error (prints the error code and error message on terminal beforehand)     
        """
        try:
            # the post parameters: m='submit', pass='...', gusewf='...' (file), certs='...'(file)
            pf = [('m', 'submit'),
                  ('pass', RemoteAPIPassword),
                  ('gusewf', (pycurl.FORM_FILE, workflowZip)),
                  ('certs', (pycurl.FORM_FILE, certs))
                 ]
            # create new pycurl object
            c = pycurl.Curl()
            # set the parameters: URL, HTTPPOST parameters
            c.setopt(c.URL, gUSEurl)
            c.setopt(c.HTTPPOST, pf)
            # ignore SSL error (equivalent to curl --insecure or curl -k)
            c.setopt(pycurl.SSL_VERIFYPEER, False) # equivalent to curl's --insecure
#            # uncomment the next line for verbose (curl -v)  
#             c.setopt(c.VERBOSE, False)
            #this StringIO is needed to store the response in
            response_buffer = StringIO()
            # set the option to write the response into the response_buffer
            c.setopt(c.WRITEDATA, response_buffer)
            # send the request
            c.perform()            
            # get the HTTP response code, e.g. 200.
            response_code = c.getinfo(c.RESPONSE_CODE) 
            if response_code != 200:
                print('Response Code: %d' % response_code)
            c.close()
            return response_buffer.getvalue()
        except pycurl.error, e:
            # print the error code and message and raise the error again
            print "Error code: ", e[0]
            print "Error message: ", e[1]  
            raise e
    
    def RemoteApiDetailsInfo(self, gUSEurl, RemoteAPIPassword, workflowId):
        """ Call gUSE RemoteAPI, method='submit'
        
        Arguments:
        gUSEurl -- the URL of the gUSE server
        RemoteAPIPassword -- the RemoteAPI password as defined on the gUSE server
        workflowZip -- the well-formed zip archive of the WS-PGRADE workflow
        certs -- the zip file containing the gUSE authentication file
        
        Returns:
        The detailed information as returne dby the RemoteAPI method 'detailsinfo'
        
        This method uses pycurl to send a HTTP request to the gUSE server at gUSEurl, and submit
        a workflow which is define din workflowZip. It is equivalent to
        guse_submit = subprocess.check_output(['curl', '-k', '-s', '-S', '-F', 'm=submit', '-F', 'pass=' + RemoteAPIPassword, '-F', 'gusewf=@' + workflowZip, '-F', 'certs=@' + certs, gUSEurl])
            
        Raises pycurl.error (prints the error code and error message on terminal beforehand)     
        """
        try:
            # the post parameters: m='detailsinfo', pass='...', ID='...'
            pf = [('m', 'detailsinfo'),
                  ('pass', RemoteAPIPassword),
                  ('ID', workflowId)
                 ]
            # create new pycurl object
            c = pycurl.Curl()
            # set the parameters: URL, HTTPPOST parameters
            c.setopt(c.URL, gUSEurl)
            c.setopt(c.HTTPPOST, pf)
            # ignore SSL error (equivalent to curl --insecure or curl -k)
            c.setopt(pycurl.SSL_VERIFYPEER, False) # equivalent to curl's --insecure
#            # uncomment the next line for verbose (curl -v)  
#             c.setopt(c.VERBOSE, False)
            #this StringIO is needed to store the response in
            response_buffer = StringIO()
            # set the option to write the response into the response_buffer
            c.setopt(c.WRITEDATA, response_buffer)
            # send the request
            c.perform()            
            # get the HTTP response code, e.g. 200.
            response_code = c.getinfo(c.RESPONSE_CODE) 
            if response_code != 200:
                print('Response Code: %d' % response_code)
            c.close()
            return response_buffer.getvalue()
        except pycurl.error, e:
            # print the error code and message and raise the error again
            print "Error code: ", e[0]
            print "Error message: ", e[1]  
            raise e    
    
    def RemoteApiDownload(self, gUSEurl, RemoteAPIPassword, workflowId, resultFileName):
        """ Call gUSE RemoteAPI, method='download'
        
        Arguments:
        gUSEurl -- the URL of the gUSE server
        RemoteAPIPassword -- the RemoteAPI password as defined on the gUSE server
        workflowId -- the ID of the workflow, as returned by RemoteAPI, m='submit'
        resultFileName -- the full name (including path) to the new result zip file which will be created
        
        This method uses pycurl to send a HTTP request to the gUSE server at gUSEurl, and puts the content
        of the file which is returned as a result into resultFileName. It is the equivalent of
        with open(resultFileName, "w") as redirect_to_file:
            subprocess.call(['curl', '-k', '-s', '-S', '-F', 'm=download', '-F', 'pass=' + RemoteAPIPassword, '-F', 'ID=' + workflowId, gUSEurl], stdout=redirect_to_file)
            
        Raises pycurl.error (prints the error code and error message on terminal beforehand)     
        """
        try:
            # the post parameters: m='download', pass='...', ID='...'
            pf = [('m', 'download'),
                     ('pass', RemoteAPIPassword),
                     ('ID', workflowId)
                    ]
            # create new pycurl object
            c = pycurl.Curl()
            # set the parameters: URL, HTTPPOST parameters
            c.setopt(c.URL, gUSEurl)
            c.setopt(c.HTTPPOST, pf)
            # ignore SSL error (equivalent to curl --insecure or curl -k), and verbose (curl -v)
            c.setopt(pycurl.SSL_VERIFYPEER, False) 
            c.setopt(c.VERBOSE, 1)
            # open (create) a new file and write the content of the downloaded file there
            with open(resultFileName, 'w') as f:
                c.setopt(c.WRITEDATA, f)
                c.perform()
                c.close()
        except pycurl.error, e:
            # print the error code and message and raise the error again
            print "Error code: ", e[0]
            print "Error message: ", e[1]  
            raise e     
                 
    def processDetailsinfo(self, wfstatus):
        """ Process the output of the RemoteAPI method 'detailsinfo' and write messages for the user on the panel 
        
        Arguments:        
        wfstatus -- the output of the RemteAPI method 'detailsinfo'        
        
        Process or parse the wfstatus, taking in consideration all possibilities and write a message for the user.
        The format of wfstatus is "submitted;job1name;running=10:finished=0;"  
        """
        # counting which substring we're on - if 0, print 'submitted', or 'running' etc.
        substringNumber = 0
        # how many jobs are 'init', 'running', 'finished', or 'error'
        init = 0
        running = 0
        finished = 0
        error = 0
        # value to return: 0 - suspended, or not valid data. 1 - finished, or error. 2 - submitted, or running.
        returnVal = 0 
        # split the wfstatus where there is a ';'
        for wfstatusSegment in wfstatus.split(";"):
            # the first substring segment is saying what the status is        
            if substringNumber == 0:
                if wfstatusSegment == "submitted":
                    self.queue.put("Raccoon VS via gUSE submitted.")
                    returnVal = 2
                elif wfstatusSegment == "running":
                    self.queue.put("Raccoon VS via gUSE running...")
                    returnVal = 2
                elif wfstatusSegment == "finished":
                    self.queue.put("Raccoon VS via gUSE finished successfully!")
                    self.queue.put("Please open the folder \'gUSE-cloud-vina-filtered-results-\' + today\'s date and time to view the results.")
                    returnVal = 1
                elif wfstatusSegment == "error":
                    self.queue.put("Part of the Raccoon execution on the cloud had errors.")
                    returnVal = 1
                elif wfstatusSegment == "suspended":
                    self.queue.put("Raccoon VS via gUSE stopped by administrator.")
                elif wfstatusSegment == "not valid data":
                    self.queue.put("Data for Raccoon VS via gUSE not valid.")
                # calculate the execution time so far (using self.startTime)    
                currentTime = datetime.datetime.now()
                timeDifference = currentTime - self.startTime
                self.queue.put("Execution time: " + str(timeDifference))
            else:
                # the rest of the wfstatus contains the status of specific jobs within the workflow separated by ':'
                for jobstatus in wfstatusSegment.split(":"):
                    # count how many jobs are in what stage, the job status and number of jobs are separated by '='
                    jobstatusList = jobstatus.split("=")            
                    if jobstatusList[0] == "init":
                        init = init + int(jobstatusList[1])
                    elif jobstatusList[0] == "running":
                        running = running + int(jobstatusList[1])
                    elif jobstatusList[0] == "finished":
                        finished = finished + int(jobstatusList[1])
                    elif jobstatusList[0] == "error":
                        error = error + int(jobstatusList[1])                    
            substringNumber = substringNumber + 1
        # calculate total number of jobs
        total = str(init + running + finished + error)
        # format grammatically correct user message
        if init > 0:
            isare = "s"
            if init == 1:
                isare = ""
            self.queue.put("Initialising " + str(init) + "/" + total + " job" + isare + "...")
        if running > 0:
            isare = "s"
            if running == 1:
                isare = ""
            self.queue.put("Running " + str(running) + "/" + total + " job" + isare + "...")
        if finished > 0:
            hashave = "s have"
            if finished == 1:
                hashave = " has"
            self.queue.put(str(finished) + "/" + total + " job" + hashave + " finished.")
        if error > 0:
            hashave = "s "
            if error == 1:
                error = " "
            self.queue.put(str(error) + "/" + total + " job" + hashave + "had errors.")
        # return the returnVal
        print wfstatus
        return returnVal

    def processGuseStatus(self, wfidsList, RemoteAPIPassword, gUSEurl):        
        """ Process the status of the workflow, if running call processDetailsinfo, if finished download results using the RemoteAPI 
        
        Arguments:        
        wfidsList -- list of workflow IDs to loop through
        RemoteAPIPassword -- the RemoteAPI password as defined on the gUSE server
        gUSEurl -- the URL of the gUSE server
        
        Process the status for each workflow. Status is what is returend by RemoteApiDetailsInfo (called returnVal there)
        Based  on this value, if the workflow is running call processDetailsInfo, if it is finished call the RemoteApi 'download' method.
        Once finished remove id from wfidsList, this method runs until this list is empty
        """
        # folders to write the result file to (in the beginning the same as number of worlfows)
        folderNumbers = range(0, len(wfidsList))
        while True:
            # index of the folderNumbers list - *could be done more efficiently
            i = 0
            # loop through all IDs of active workflows
            for wfid in wfidsList:
                # get the folderNumber to write the results into e.g. files0
                folderNumber = folderNumbers[i]
                # call RemoteAPI m='detailsinfo' for the workflow with wfid
                try:
                    wfstatus = self.RemoteApiDetailsInfo(gUSEurl, RemoteAPIPassword, wfid)
                except Exception as e:
                    print e                    
                    wfstatus = -1
                
                # if there is an exception make wfstatus = -1, then wait for 15 seconds and continue
                # this was a workaround to prevent clogging the gUSE server
                if wfstatus == -1:
                    sleep(15)
                    continue;
                # if there was no errors with RemoteAPI m='detailsinfo', process the result it returned
                wfstate = self.processDetailsinfo(wfstatus)
                # value returned: 0 - suspended, or not valid data.
                if wfstate == 0:
                    # just remove the wfid from the list and start over looping through the new list of workflow IDs
                    wfidsList.remove(wfid)
                    folderNumbers.remove(folderNumber)
                    break
                # value returned: 1 - finished, or error.
                elif wfstate == 1:
                    # download the results into this file
                    resultFileName = self.resultFolderName + os.sep + "files" + str(folderNumber) + os.sep + "gUSE-cloud-vina-results.zip"
                    # call RemoteAPI m='download'
                    self.RemoteApiDownload(gUSEurl, RemoteAPIPassword, wfid, resultFileName)
                    
                    # get a new timestamp of when the workflow finished according to the Raccoon2 UI (small delay)
                    timestamp = datetime.datetime.now().strftime("%d-%m-%y--%H-%M-%S-%f")
                    # open the  returned zip file and extract only the Vina output files which are stored in "output.zip"
                    # store the extracted zip in a temporary folder which will be deleted at the end
                    z = ZipFile(self.resultFolderName + os.sep + "files" + str(folderNumber) + os.sep + 'gUSE-cloud-vina-results.zip', 'r')
                    temporary_folder = "res" + timestamp
                    os.mkdir(temporary_folder)
                    z.extractall(temporary_folder, filter(lambda f: f.endswith('output.zip'), z.namelist()))
                    output_zip_name_path = ""
                    for name in z.namelist():
                        if name.endswith("output.zip"):
                            output_zip_name_path = name
                    z.close()
                    # in case nothing is downloaded - *could be done more efficiently
                    if output_zip_name_path == "":
                        print "Error in downloading results or in the job"
                    # if no error    
                    else:
                        # open the "output.zip" where the results are stored
                        z = ZipFile(temporary_folder + os.sep + output_zip_name_path)
                        # this is the new folder where the results will be extracted into, with the new timestamp
                        results_folder = self.resultFolderName + os.sep + "files" + str(folderNumber) + os.sep + "gUSE-cloud-vina-results-" + timestamp
                        os.mkdir(results_folder)
                        # extract only files ending with .pdbqt_log.txt or .pdbqt
                        z.extractall(results_folder, filter(lambda f: f.endswith(('.pdbqt_log.txt', '.pdbqt')), z.namelist()))
                        z.close()
                        # remove "temporary_folder" and all its empty and non-empty sub-folders
                        os.remove(temporary_folder + os.sep + output_zip_name_path)
                        last_separator = output_zip_name_path.rfind(os.sep)
                        os.removedirs(temporary_folder + os.sep + output_zip_name_path[0:last_separator])
                    
                    # maybe remove all input files too (*leave for now)    
                    #os.remove("../ligands.zip")
                    #os.remove("../receptors.zip")
                    #os.remove("../conf.txt")
                    #os.remove("../output_names.txt")
                    #os.remove("../certs.zip")
                    
                    # once downloaded, remove the workflow id from the list and start over looping through the new list of workflow IDs    
                    wfidsList.remove(wfid)
                    folderNumbers.remove(folderNumber)  
                    break
                # increment the folder number and start processing the next workflow in 5 seconds
                i = i + 1 
                sleep(5)                          
            if not wfidsList:
                # print when all workflows have been processed
                self.queue.put("VS experiment finished.")
                print "VS experiment finished."
                break
            else:
                # restart getting details for all workflows in 15 seconds        
                sleep(15)
