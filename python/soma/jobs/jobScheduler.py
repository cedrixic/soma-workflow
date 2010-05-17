'''
@author: Yann Cointepas
@author: Soizic Laguitton
@organization: U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''


from __future__ import with_statement
from soma.pipeline.somadrmaajobssip import DrmaaJobs
from soma.jobs.jobServer import JobServer
import Pyro.naming, Pyro.core
from Pyro.errors import NamingError
from datetime import date
from datetime import timedelta
import pwd
import os
import threading
import time
from datetime import datetime
import logging

__docformat__ = "epytext en"


refreshment_interval = 1 #seconds

class JobSchedulerError( Exception ): 
  def __init__(self, msg):
    self.args = (msg,)
    logger = logging.getLogger('ljp.js')
    logger.critical('EXCEPTION ' + msg)



class DrmaaJobScheduler( object ):

  '''
  Instances of this class opens a DRMAA session and allows to submit and control 
  the jobs. It updates constantly the jobs status on the L{JobServer}. 
  The L{DrmaaJobScheduler} must be created on one of the machine which is allowed
  to submit jobs by the DRMS.
  '''
  def __init__( self, job_server, parallel_job_submission_info = None):
    '''
    Opens a connection to the pool of machines and to the data server L{JobServer}.

    @type  job_server: L{JobServer}
    @type  parallel_job_submission_info: dictionary 
    @param parallel_job_submission_info: DRMAA doesn't provide an unified way of submitting
    parallel jobs. The value of parallel_job_submission is cluster dependant. 
    The keys are:
      - Drmaa job template attributes 
      - parallel configuration name as defined in JobServer
    '''
    self.logger = logging.getLogger('ljp.drmaajs')
    
    self.__drmaa = DrmaaJobs()
    
    self.__jobServer = job_server

    self.logger.debug("Parallel job submission info: %s", repr(parallel_job_submission_info))
    self.__parallel_job_submission_info = parallel_job_submission_info

    try:
      userLogin = pwd.getpwuid(os.getuid())[0] 
    except Exception, e:
      self.logger.critical("Couldn't identify user %s: %s \n" %(type(e), e))
      raise SystemExit
    
    self.__user_id = self.__jobServer.registerUser(userLogin) 

    self.__jobs = set([])
    self.__drmaa_lock = threading.RLock()
    self.__jobs_lock = threading.RLock()
    
    self.__jobsEnded = False
    
    def startJobStatusUpdateLoop( self, interval ):
      logger_su = logging.getLogger('ljp.drmaajs.su')
      while True:
        # get rid of all the jobs that doesn't exist anymore
        serverJobs = self.__jobServer.getJobs(self.__user_id)
        with self.__jobs_lock:
          self.__jobs = self.__jobs.intersection(serverJobs)
        allJobsEnded = True
        ended = []
        with self.__jobs_lock:
          for job_id in self.__jobs:
            # get back the status from DRMAA
            status = self.__status(job_id)
            logger_su.debug("job " + repr(job_id) + " : " + status)
            if status == JobServer.DONE or status == JobServer.FAILED:
              # update the exit status and status on the job server 
              self.__endOfJob(job_id, status)
              ended.append(job_id)
            else:
              allJobsEnded = False
              # update the status on the job server 
              self.__jobServer.setJobStatus(job_id, status)
        self.__jobsEnded = allJobsEnded

        # get the exit information for terminated jobs and update the jobServer
        for job_id in ended:
          with self.__jobs_lock:
            self.__jobs.discard(job_id)
        logger_su.debug("---------- all jobs done : " + repr(self.__jobsEnded))
      
        time.sleep(interval)
    
    
    self.__job_status_thread = threading.Thread(name = "job_status_loop", 
                                                target = startJobStatusUpdateLoop, 
                                                args = (self, refreshment_interval))
    self.__job_status_thread.setDaemon(True)
    self.__job_status_thread.start()


   

  def __del__( self ):
    pass
    '''
    Closes the connection with the pool and the data server L{JobServer} and
    stops updating the L{JobServer}. (should be called when all the jobs are
    done) 
    '''
 
    
  


  ########## JOB SUBMISSION #################################################

  def submit( self,
          command,
          required_local_input_files,
          required_local_output_files,
          stdin,
          join_stderrout,
          disposal_timeout,
          name_description,
          stdout_path,
          stderr_path,
          working_directory,
          parallel_job_info):
    
    '''
    Implementation of the L{JobScheduler} method.
    '''
        
    self.logger.debug("submit")
    self.logger.debug("parallel_job_info", repr(parallel_job_info))
    
    expiration_date = date.today() + timedelta(hours=disposal_timeout) 
    parallel_config_name = None
    max_node_number = 1

    if not stdout_path:
      stdout_path = self.__jobServer.generateLocalFilePath(self.__user_id)
      stderr_path = self.__jobServer.generateLocalFilePath(self.__user_id)
      custom_submit = False #the std out and err file has to be removed with the job
    else:
      custom_submit = True #the std out and err file won't to be removed with the job
      
    with self.__drmaa_lock:
      drmaaJobTemplateId = self.__drmaa.allocateJobTemplate()
      self.__drmaa.setCommand(drmaaJobTemplateId, command[0], command[1:])
    
      self.__drmaa.setAttribute(drmaaJobTemplateId, "drmaa_output_path", "[void]:" + stdout_path)
     
      if join_stderrout:
        self.__drmaa.setAttribute(drmaaJobTemplateId,"drmaa_join_files", "y")
      else:
        if stderr_path:
          self.__drmaa.setAttribute(drmaaJobTemplateId, "drmaa_error_path", "[void]:" + stderr_path)
     
      if stdin:
        self.__drmaa.setAttribute(drmaaJobTemplateId, "drmaa_input_path", "[void]:" + stdin)
        
      if working_directory:
        self.__drmaa.setAttribute(drmaaJobTemplateId, "drmaa_wd", working_directory)
      
      if parallel_job_info:
        self.logger.debug("parallel_job_info: ", repr(parallel_job_info))
        parallel_config_name, max_node_number = parallel_job_info
        self.__setDrmaaParallelJobTemplate(drmaaJobTemplateId, parallel_config_name, max_node_number)

      drmaaSubmittedJobId = self.__drmaa.runJob(drmaaJobTemplateId)
      self.__drmaa.deleteJobTemplate(drmaaJobTemplateId)
    
    # for user information only
    command_info = ""
    for command_element in command:
      command_info = command_info + " " + command_element
    
    job_id = self.__jobServer.addJob(self.__user_id, 
                                      custom_submit,
                                      expiration_date, 
                                      stdout_path,
                                      stderr_path,
                                      join_stderrout,
                                      stdin, 
                                      name_description, 
                                      drmaaSubmittedJobId,
                                      working_directory,
                                      command_info,
                                      parallel_config_name,
                                      max_node_number)
                                    
    if required_local_input_files:
      self.__jobServer.registerInputs(job_id, required_local_input_files)
    if required_local_output_files:
      self.__jobServer.registerOutputs(job_id, required_local_output_files)

    with self.__jobs_lock:
      self.__jobs.add(job_id)
    
    return job_id

  def __setDrmaaParallelJobTemplate(self, drmaa_job_template_id, configuration_name, max_num_node):
    '''
    Set the DRMAA job template information for a parallel job submission.
    The configuration file must provide the parallel job submission information specific 
    to the cluster in use. 

    @type  drmaa_job_template_id: string 
    @param drmaa_job_template_id: id of drmaa job template
    @type  parallel_job_info: tuple (string, int)
    @param parallel_job_info: (configuration_name, max_node_num)
    configuration_name: type of parallel job as defined in jobServer.py (eg MPI, OpenMP...)
    max_node_num: maximum node number the job requests (on a unique machine or separated machine
    depending on the parallel configuration)
    ''' 

    if not self.__parallel_job_submission_info:
      raise JobSchedulerError("Configuration file : Couldn't find parallel job submission information for this cluster.")
    
    if configuration_name not in self.__parallel_job_submission_info:
      raise JobSchedulerError("Configuration file : couldn't find the parallel configuration %s for the current cluster.", configuration_name)

    cluster_specific_config_name = self.__parallel_job_submission_info[configuration_name]
    
    #NOT Safe ??
    #for key in self.__parallel_job_submission_info.iterkeys():
      #if "drmaa_" == key[0:5]:
        #value = self.__parallel_job_submission_info[key]
        #value = value.format(config_name=cluster_specific_config_name, max_node=max_num_node)
        #with self.__drmaa_lock:
          #self.__drmaa.setAttribute( drmaa_job_template_id, 
                                     #key, 
                                     #value)
        #self.logger.debug("Parallel job, drmaa attribute = %s, value = %s ", key, value)

    for drmaa_attribute in ("drmaa_native_specification", "drmaa_job_category"):
      value = self.__parallel_job_submission_info.get(drmaa_attribute)
      if value: 
        #value = value.format(config_name=cluster_specific_config_name, max_node=max_num_node)
        value = value.replace("{config_name}", cluster_specific_config_name)
        value = value.replace("{max_node}", repr(max_num_node))
        with self.__drmaa_lock: 
          self.__drmaa.setAttribute(drmaa_job_template_id, 
                                    drmaa_attribute, 
                                    value)
        self.logger.debug("Parallel job, drmaa attribute = %s, value = %s ", drmaa_attribute, value) 

   

  def dispose( self, job_id ):
    '''
    Implementation of the L{JobScheduler} method.
    '''
    
    self.logger.debug("Dispose job %s", job_id)
    drmaaJobId=self.__jobServer.getDrmaaJobId(job_id)
    
    with self.__drmaa_lock:
      self.__drmaa.terminate(drmaaJobId)
    with self.__jobs_lock:
      self.__jobs.discard(job_id)
    
    self.__jobServer.deleteJob(job_id)
    

  ########### DRMS MONITORING ################################################


  def __status( self, job_id ):
    '''
    Returns the status of a submitted job. => add a converstion from DRMAA job 
    status strings to JobServer status ???
    
    @type  job_id: C{JobIdentifier}
    @param job_id: The job identifier (returned by L{submit} or L{jobs})
    @rtype:  C{JobStatus}
    @return: the status of the job. The possible values are UNDETERMINED, 
    QUEUED_ACTIVE, SYSTEM_ON_HOLD, USER_ON_HOLD, USER_SYSTEM_ON_HOLD, RUNNING,
    SYSTEM_SUSPENDED, USER_SUSPENDED, USER_SYSTEM_SUSPENDED, DONE, FAILED
    '''
    
    drmaaJobId = self.__jobServer.getDrmaaJobId(job_id)
    
    with self.__drmaa_lock:
      status = self.__drmaa.jobStatus(drmaaJobId) 
       #add conversion from DRMAA status strings to JobServer status strings if needed
      
    return status
   
     


  def __endOfJob(self, job_id, status):
    '''
    The method is called when the job status is JobServer.DONE or FAILED,
    to get the job exit inforation from DRMAA and update the JobServer.
    The job_id is also remove form the job list.
    '''
    
    drmaaJobId = self.__jobServer.getDrmaaJobId(job_id)
    self.logger.debug("End of job %s, drmaaJobId = %s", job_id, drmaaJobId)
    
    with self.__drmaa_lock:
      exit_status, exit_value, term_sig, resource_usage = self.__drmaa.wait(drmaaJobId, 0)
      
    self.logger.debug("job %s, exit_status=%s exit_value =%d", job_id, exit_status, exit_value)
    
    str_rusage = ''
    for rusage in resource_usage:
      str_rusage = str_rusage + rusage + ' '
    
    self.__jobServer.setJobExitInfo(job_id, exit_status, exit_value, term_sig, str_rusage)
    self.__jobServer.setJobStatus(job_id, status)
    
    assert(self.__jobServer.getJobStatus(job_id)[0] == status)


  def areJobsDone(self):
    return self.__jobsEnded
    
  ########## JOB CONTROL VIA DRMS ########################################
  

  def stop( self, job_id ):
    '''
    Implementation of the L{JobScheduler} method.
    '''
    drmaaJobId = self.__jobServer.getDrmaaJobId(job_id)
    status = self.__status(job_id)
    
    if status==JobServer.RUNNING:
      with self.__drmaa_lock:
        self.__drmaa.suspend(drmaaJobId)
      self.__waitForStatusUpdate(job_id)
    
    if status==JobServer.QUEUED_ACTIVE:
      with self.__drmaa_lock:
        self.__drmaa.hold(drmaaJobId)
      self.__waitForStatusUpdate(job_id)
    
    
    
  def restart( self, job_id ):
    '''
    Implementation of the L{JobScheduler} method.
    '''
    
    drmaaJobId = self.__jobServer.getDrmaaJobId(job_id)
    status = self.__status(job_id)
    
    if status==JobServer.USER_SUSPENDED or status==JobServer.USER_SYSTEM_SUSPENDED:
      with self.__drmaa_lock:
        self.__drmaa.resume(drmaaJobId)
      self.__waitForStatusUpdate(job_id)
      
    if status==JobServer.USER_ON_HOLD or status==JobServer.USER_SYSTEM_ON_HOLD :
      with self.__drmaa_lock:
        self.__drmaa.release(drmaaJobId)
      self.__waitForStatusUpdate(job_id)
    
    
  


  def kill( self, job_id ):
    '''
    Implementation of the L{JobScheduler} method.
    '''
    
    drmaaJobId = self.__jobServer.getDrmaaJobId(job_id)
    with self.__drmaa_lock:
      self.__drmaa.terminate(drmaaJobId)
    self.__jobServer.setJobExitInfo(job_id, 
                                    JobServer.USER_KILLED,
                                    None,
                                    None,
                                    None)
    self.__jobServer.setJobStatus(job_id, JobServer.FAILED)
    with self.__jobs_lock:
      self.__jobs.discard(job_id)
      


  def __waitForStatusUpdate(self, job_id):
    
    drmaaActionTime = datetime.now()
    time.sleep(refreshment_interval)
    (status, last_status_update) = self.__jobServer.getJobStatus(job_id)
    while not status == JobServer.DONE and not status == JobServer.FAILED and last_status_update < drmaaActionTime:
      time.sleep(refreshment_interval)
      (status, last_status_update) = self.__jobServer.getJobStatus(job_id) 
      if datetime.now() - last_status_update > timedelta(seconds = refreshment_interval*5):
        raise JobSchedulerError('Could not get back status of job %s. The process updating its status failed.' %(job_id))
    


class JobScheduler( object ):
  
  def __init__( self, job_server, drmaa_job_scheduler = None):
    ''' 
    @type  job_server: L{JobServer}
    @type  drmaa_job_scheduler: L{DrmaaJobScheduler} or None
    @param drmaa_job_scheduler: object of type L{DrmaaJobScheduler} to delegate all the tasks related to the DRMS. If None a new instance is created.
    '''
    
    self.logger = logging.getLogger('ljp.js')
    
    Pyro.core.initClient()

    # Drmaa Job Scheduler
    if drmaa_job_scheduler:
      self.__drmaaJS = drmaa_job_scheduler
    else:
      self.__drmaaJS = DrmaaJobScheduler()
    
    # Job Server
    self.__jobServer= job_server
    
    try:
      userLogin = pwd.getpwuid(os.getuid())[0]
    except Exception, e:
      raise JobSchedulerError("Couldn't identify user %s: %s \n" %(type(e), e))
    
    self.__user_id = self.__jobServer.registerUser(userLogin)
   
    self.__fileToRead = None
    self.__fileToWrite = None
    self.__stdoutFileToRead = None
    self.__stderrFileToRead = None
    
    

  def __del__( self ):
    pass

  ########## FILE TRANSFER ###############################################
  
  '''
  For the following methods:
    Local means that it is located on a directory shared by the machine of the pool
    Remote means that it is located on a remote machine or on any directory 
    owned by the user. 
    A transfer will associate remote file path to unique local file path.
  
  Use L{registerTransfer} then L{writeLine} or scp or 
  shutil.copy to tranfer input file from the remote to the local 
  environment.
  Use L{registerTransfer} and once the job has run use L{readline} or scp or
  shutil.copy to transfer the output file from the local to the remote environment.
  '''

  def registerTransfer(self, remote_file_path, disposal_timeout=168): 
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
      
    local_input_file_path = self.__jobServer.generateLocalFilePath(self.__user_id, remote_file_path)
    expirationDate = date.today() + timedelta(hours=disposal_timeout) 
    self.__jobServer.addTransfer(local_input_file_path, remote_file_path, expirationDate, self.__user_id)
    return local_input_file_path


  def writeLine(self, line, local_file_path):
    '''
    Writes a line to the local file. The path of the local input file
    must have been generated using the L{registerTransfer} method.
    
    @type  line: string
    @param line: line to write in the local input file
    @type  local_file_path: string
    @param local_file_path: local file path to fill up
    '''
    
    if not self.__jobServer.isUserTransfer(local_file_path, self.__user_id):
      raise JobSchedulerError("Couldn't write to file %s: the transfer was not registered using 'registerTransfer' or the user doesn't own the file. \n" % local_file_path)
    
    if not self.__fileToWrite or not self.__fileToWrite.name == local_file_path:
      if self.__fileToWrite: self.__fileToWrite.close()
      self.__fileToWrite = open(local_file_path, 'wt')
      
      
    self.__fileToWrite.write(line)
    self.__fileToWrite.flush()
    #os.fsync(self.__fileToWrite.fileno())
   
   
  
  def readline(self, local_file_path):
    '''
    Reads a line from the local file. The path of the local input file
    must have been generated using the L{registerTransfer} method.
    
    @type: string
    @param: local file path to fill up
    @rtype: string
    return: read line
    '''
    
    if not self.__jobServer.isUserTransfer(local_file_path, self.__user_id):
      raise JobSchedulerError("Couldn't read from file %s: the transfer was not registered using 'registerTransfer' or the user doesn't own the file. \n" % local_file_path)
    
    
    if not self.__fileToRead or not self.__fileToRead.name == local_file_path:
      self.__fileToRead = open(local_file_path, 'rt')
    
    return self.__fileToRead.readline()

  
  def endTransfers(self):
    if self.__fileToWrite:
      self.__fileToWrite.close()
    if self.__fileToRead:
      self.__fileToRead.close()
    

  def cancelTransfer(self, local_file_path):
    '''
     Implementation of the L{Jobs} method.
    '''
    
    if not self.__jobServer.isUserTransfer(local_file_path, self.__user_id) :
      print "Couldn't cancel transfer %s. It doesn't exist or is not owned by the current user \n" % local_file_path
      return

    self.__jobServer.removeTransferASAP(local_file_path)
    

  ########## JOB SUBMISSION ##################################################

  
  def submit( self,
              command,
              required_local_input_files=None,
              required_local_output_files=None,
              stdin=None,
              join_stderrout=False,
              disposal_timeout=168,
              name_description=None,
              stdout_path=None,
              stderr_path=None,
              working_directory=None,
              parallel_job_info=None):

    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''

    self.logger.debug("JobScheduler submit, parallel_job_info", repr(parallel_job_info))

    if len(command) == 0:
      raise JobSchedulerError("Submission error: the command must contain at least one element \n")

    # check the required_local_input_files, required_local_output_file and stdin ?
    job_id = self.__drmaaJS.submit( command,
                                    required_local_input_files,
                                    required_local_output_files,
                                    stdin,
                                    join_stderrout,
                                    disposal_timeout,
                                    name_description,
                                    stdout_path,
                                    stderr_path,
                                    working_directory,
                                    parallel_job_info)
    
    return job_id




  def dispose( self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      print "Couldn't dispose job %d. It doesn't exist or is not owned by the current user \n" % job_id
      return
    
    self.__drmaaJS.dispose(job_id)


  ########## SERVER STATE MONITORING ########################################


  def jobs(self):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    return self.__jobServer.getJobs(self.__user_id)
    
  def getTransfers(self):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    return self.__jobServer.getTransfers(self.__user_id)

    
  def getTransferInformation(self, local_file_path):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    #TBI raise an exception if local_file_path is not valid transfer??
    
    if not self.__jobServer.isUserTransfer(local_file_path, self.__user_id):
      print "Couldn't get transfer information of %s. It doesn't exist or is owned by a different user \n" % local_file_path
      return
      
    return self.__jobServer.getTransferInformation(local_file_path)
   


  def status( self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      print "Could get the job status of job %d. It doesn't exist or is owned by a different user \n" %job_id
      return 
    
    return self.__jobServer.getJobStatus(job_id)[0]
        

  def exitInformation(self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
  
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      print "Could get the exit information of job %d. It doesn't exist or is owned by a different user \n" %job_id
      return
  
    exit_status, exit_value, terminating_signal, resource_usage = self.__jobServer.getExitInformation(job_id)
    
    return (exit_status, exit_value, terminating_signal, resource_usage)
    
 
  def generalInformation(self, job_id):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    
    #if not self.__jobServer.isUserJob(job_id, self.__user_id):
    #print "Could get information about job %d. It doesn't exist or is owned by a different user \n" %job_id
    #return

    info = self.__jobServer.getGeneralInformation(job_id)
    
    return info
    


  def stdoutReadLine(self, job_id):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      print "Could get not read std output for the job %d. It doesn't exist or is owned by a different user \n" %job_id
      return   

    stdout_path, stderr_path = self.__jobServer.getStdOutErrFilePath(job_id)
    
    if not self.__stdoutFileToRead or not self.__stdoutFileToRead.name == stdout_path:
      self.__stdoutFileToRead = open(stdout_path, 'rt')
      
    return self.__stdoutFileToRead.readline()


  def stderrReadLine(self, job_id):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      print "Could get not read std error for the job %d. It doesn't exist or is owned by a different user \n" %job_id
      return   

    stdout_path, stderr_path = self.__jobServer.getStdOutErrFilePath(job_id)
    
    if not stderr_path:
      self.__stderrFileToRead = None
      return 

    if not self.__stderrFileToRead or not self.__stderrFileToRead.name == stderr_path:
      self.__stderrFileToRead = open(stderr_path, 'rt')
      
    return self.__stderrFileToRead.readline()

    
  ########## JOB CONTROL VIA DRMS ########################################
  
  
  def wait( self, job_ids, timeout = -1):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    for jid in job_ids:
      if not self.__jobServer.isUserJob(jid, self.__user_id):
        raise JobSchedulerError( "Could not wait for job %d. It doesn't exist or is owned by a different user \n" %jid )
      
    #self.__drmaaJS.wait(job_ids, timeout)
    self.logger.debug("        waiting...")
    
    waitForever = timeout < 0
    startTime = datetime.now()
    
    for jid in job_ids:
      (status, last_status_update) = self.__jobServer.getJobStatus(jid)
      self.logger.debug("        job %s status: %s", jid, status)
      delta = datetime.now()-startTime
      delta_status_update = datetime.now() - last_status_update
      while not status == JobServer.DONE and not status == JobServer.FAILED and (waitForever or delta < timedelta(seconds=timeout)):
        time.sleep(refreshment_interval)
        (status, last_status_update) = self.__jobServer.getJobStatus(jid) 
        self.logger.debug("        job %s status: %s", jid, status)
        delta = datetime.now() - startTime
        if datetime.now() - last_status_update > timedelta(seconds = refreshment_interval*10):
          raise JobSchedulerError('Could not wait for job %s. The process updating its status failed.' %(jid))
    

  def stop( self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      raise JobSchedulerError( "Could not stop job %d. It doesn't exist or is owned by a different user \n" %job_id )
    
    self.__drmaaJS.stop(job_id)
   
  
  
  def restart( self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''
    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      raise JobSchedulerError( "Could not restart job %d. It doesn't exist or is owned by a different user \n" %job_id )
    
    self.__drmaaJS.restart(job_id)


  def kill( self, job_id ):
    '''
    Implementation of soma.jobs.jobClient.Jobs API
    '''

    if not self.__jobServer.isUserJob(job_id, self.__user_id):
      raise JobSchedulerError( "Could not kill job %d. It doesn't exist or is owned by a different user \n" %job_id )
    
    self.__drmaaJS.kill(job_id)
