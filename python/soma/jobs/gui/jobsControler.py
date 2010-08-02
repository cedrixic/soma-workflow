
from soma.jobs.constants import *
from soma.jobs.jobClient import *
import socket
import os
import ConfigParser


class JobsControler(object):
  
  def __init__(self, TestConfigFilePath, test_no = 1):
    
    
    self.hostname = socket.gethostname()
    
    self.jobs = None
    
    self.somajobs_config = ConfigParser.ConfigParser()
    self.somajobs_config.read(os.environ["SOMA_JOBS_CONFIG"])
    
    self.test_no = test_no
    # Test config 
    self.test_config = ConfigParser.ConfigParser()
    self.test_config.read(TestConfigFilePath)
    self.output_dir = self.test_config.get(self.hostname, 'job_output_dir') + repr(self.test_no) + "/"
    
    
    

  def isConnected(self):
    return not self.jobs == None 
  
  def getRessourceIds(self):
    resource_ids = []
    for cid in self.somajobs_config.sections():
      if cid != OCFG_SECTION_CLIENT:
        resource_ids.append(cid)
        
  def isRemoteConnection(self, resource_id):
    submitting_machines = config.get(resource_id, CFG_SUBMITTING_MACHINES).split()
    is_remote = True
    for machine in submitting_machines: 
      if self.hostname == machine: 
        is_remote = False
        break
    return is_remote
    
    
  def connect(self, resource_id, login = None, password = None):
    self.jobs = Jobs(os.environ["SOMA_JOBS_CONFIG"],
                resource_id, 
                login, 
                password,
                log=self.test_no)
    
    
  def generateWorkflowExample(self):
    examples_dir = self.test_config.get(self.hostname, 'job_examples_dir')
    python = self.test_config.get(self.hostname, 'python')
    
      # outputs
    file11 = FileRetrieving(self.output_dir + "file11", 168, "file11")
    file12 = FileRetrieving(self.output_dir + "file12", 168, "file12")
    file2 = FileRetrieving(self.output_dir + "file2", 168, "file2")
    file3 = FileRetrieving(self.output_dir + "file3", 168, "file3")
    file4 = FileRetrieving(self.output_dir + "file4", 168, "file4")
    
    # inputs
    file0 = FileSending(examples_dir + "complete/" + "file0", 168, "file0")
    script1 = FileSending(examples_dir + "complete/" + "job1.py", 168, "job1_py")
    stdin1 = FileSending(examples_dir + "complete/" + "stdin1", 168, "stdin1")
    script2 = FileSending(examples_dir + "complete/" + "job2.py", 168, "job2_py")
    stdin2 = FileSending(examples_dir + "complete/" + "stdin2", 168, "stdin2")
    script3 = FileSending(examples_dir + "complete/" + "job3.py", 168, "job3_py")
    stdin3 = FileSending(examples_dir + "complete/" + "stdin3", 168, "stdin3")
    script4 = FileSending(examples_dir + "complete/" + "job4.py", 168, "job4_py")
    stdin4 = FileSending(examples_dir + "complete/" + "stdin4", 168, "stdin4")
    
    exceptionJobScript = FileSending(examples_dir + "simple/exceptionJob.py", 168, "exception_job")
                                                                                                          
    # jobs
    job1 = JobTemplate([python, script1, file0,  file11, file12, "20"], 
                      [file0, script1, stdin1], 
                      [file11, file12], 
                      stdin1, False, 168, "job1")
                              
    job2 = JobTemplate([python, script2, file11,  file0, file2, "30"], 
                      [file0, file11, script2, stdin2], 
                      [file2], 
                      stdin2, False, 168, "job2")
                              
    job3 = JobTemplate([python, script3, file12,  file3, "30"], 
                      [file12, script3, stdin3], 
                      [file3], 
                      stdin3, False, 168, "job3")
    
    #job3 = JobTemplate([python, exceptionJobScript],
                      #[exceptionJobScript, file12, script3, stdin3],
                      #[file3],
                      #None, False, 168, "job3")
    
    job4 = JobTemplate([python, script4, file2,  file3, file4, "10"], 
                              [file2, file3, script4, stdin4], 
                              [file4], 
                              stdin4, False, 168, "job4")
  
    
  
    #building the workflow
    
    #nodes = [file11, file12, file2, file3, file4,
           #file0, script1, stdin1, 
           #script2, stdin2, 
           #script3, stdin3, #exceptionJobScript,
           #script4, stdin4, 
           #job1, job2, job3, job4]
           
    nodes = [job1, job2, job3, job4]
  

    dependencies = [(job1, job2), 
                    (job1, job3),
                    (job2, job4), 
                    (job3, job4)]
  
    group_1 = Group([job2, job3], 'group_1')
    group_2 = Group([job1, group_1], 'group_2')
    mainGroup = Group([group_2, job4])
    
    return Workflow(nodes, dependencies, mainGroup, [group_1, group_2])
    
    
  def submitWorkflow(self, workflow):
    return self.jobs.submitWorkflow(workflow) 
    
  def transferInputFiles(self, workflow):
    for node in workflow.full_nodes:
      if isinstance(node, FileSending):
        if self.jobs.transferStatus(node.local_file_path) == READY_TO_TRANSFER:
          self.jobs.sendRegisteredFile(node.local_file_path)
    
  def transferOutputFiles(self, workflow):
    for node in workflow.full_nodes:
      if isinstance(node, FileRetrieving):
        if self.jobs.transferStatus(node.local_file_path) == READY_TO_TRANSFER:
          self.jobs.retrieveFile(node.local_file_path)
          
  def printWorflow(self, workflow):
    GRAY="0.8,0.8,0.8"
    BLUE="0,0.8,1.0"
    RED="1.0,0.4,0.2"
    GREEN="0.6,1.0,0.2"
    LIGHT_BLUE="0.8,1.0,1.0"
    
    dot_file_path = self.output_dir + "tmp.dot"
    graph_file_path = self.output_dir + "tmp.png"
    if dot_file_path and os.path.isfile(dot_file_path):
      os.remove(dot_file_path)
    file = open(dot_file_path, "w")
    print >> file, "digraph G {"
    for ar in self.workflow.dependencies:
      print >> file, ar[0].name + " -> " + ar[1].name
    for node in self.workflow.nodes:
      if isinstance(node, JobTemplate):
        status = self.jobs.status(node.job_id)
        if status == NOT_SUBMITTED:
          print >> file, node.name + "[shape=box label="+ node.name +", style=filled, color=" + GRAY +"];"
        elif status == DONE:
          print >> file, node.name + "[shape=box label="+ node.name +", style=filled, color=" + LIGHT_BLUE +"];"
        elif status == FAILED:
          print >> file, node.name + "[shape=box label="+ node.name +", style=filled, color=" + RED +"];"
        else:
          print >> file, node.name + "[shape=box label="+ node.name +", style=filled, color=" + GREEN +"];"
      if isinstance(node, FileTransfer):
        status = self.jobs.transferStatus(node.local_file_path)
        if status == TRANSFER_NOT_READY:
           print >> file, node.name + "[label="+ node.name +", style=filled, color=" + GRAY +"];"
        elif status == READY_TO_TRANSFER:
          print >> file, node.name + "[label="+ node.name +", style=filled, color=" + BLUE +"];"
        elif status == TRANSFERING:
          print >> file, node.name + "[label="+ node.name +", style=filled, color=" + GREEN +"];"
        elif status == TRANSFERED:
          print >> file, node.name + "[label="+ node.name +", style=filled, color=" + LIGHT_BLUE +"];"
        
    print >> file, "}"
    file.close()
    return graph_file_path
    
  
  
  
 
 