#! /usr/bin/env python

'''
@author: Soizic Laguitton
@organization: U{IFR 49<http://www.ifr49.org>}
@license: U{CeCILL version 2<http://www.cecill.info/licences/Licence_CeCILL_V2-en.html>}
'''


from __future__ import with_statement
import ConfigParser
from soma.workflow.constants import *

soma_wf_cfg = ConfigParser.ConfigParser()


##########################
# NEUROSPIN TEST CLUSTER #
##########################

s = 'neurospin_test_cluster'

soma_wf_cfg.add_section(s)

#Parallel job specific submission information
soma_wf_cfg.set(s, OCFG_PARALLEL_COMMAND,      "-pe  {config_name} {max_node}") 
soma_wf_cfg.set(s, OCFG_PARALLEL_PC_MPI,       'mpi')
soma_wf_cfg.set(s, OCFG_PARALLEL_ENV_MPI_BIN,  '/volatile/laguitton/sge6-2u5/mpich/mpich-1.2.7/bin/')
soma_wf_cfg.set(s, OCFG_PARALLEL_ENV_NODE_FILE, '$TMPDIR/machines')
#Engine
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_FORMAT, '%(asctime)s => %(module)s line %(lineno)s : %(message)s      %(threadName)s')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_DIR,    '/neurospin/tmp/Soizic/soma_workflow_files/logs/')
#Computing resource
soma_wf_cfg.set(s, CFG_SUBMITTING_MACHINES, "is143016")# is204723")
soma_wf_cfg.set(s, CFG_CLUSTER_ADDRESS,     "is143016")
soma_wf_cfg.set(s, OCFG_DRMS,               'SGE') 
#Server
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FORMAT,   "%(asctime)s => line %(lineno)s: %(message)s")
soma_wf_cfg.set(s, OCFG_SERVER_LOG_LEVEL,    'DEBUG')
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FILE,     '/volatile/laguitton/log_soma_workflow_server')
soma_wf_cfg.set(s, CFG_NAME_SERVER_HOST,     'is143016')
soma_wf_cfg.set(s, CFG_SERVER_NAME,          'soma_workflow_server')
soma_wf_cfg.set(s, CFG_TRANSFERED_FILES_DIR, '/neurospin/tmp/Soizic/soma_workflow_files/')
soma_wf_cfg.set(s, CFG_DATABASE_FILE,        '/volatile/laguitton/soma_workflow.db')
#Shared resource path translation file
soma_wf_cfg.set(s, OCFG_PATH_TRANSLATION_FILES, 'example{/neurospin/tmp/Soizic/jobFiles/translation_files/job_examples.sjtr} brainvisa{/home/sl225510/.brainvisa/soma-workflow.translation}')

##########################
# SOIZIC HOME CLUSTER #
##########################

s = 'soizic_home_cluster'

soma_wf_cfg.add_section(s)
#Engine
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_FORMAT, '%(asctime)s => %(module)s line %(lineno)s: %(message)s          %(threadName)s')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_LEVEL, 'DEBUG')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_DIR,   '/home/soizic/soma-jobs-server/logs/')
#Computing resource
soma_wf_cfg.set(s, CFG_SUBMITTING_MACHINES, "soizic-vaio")
soma_wf_cfg.set(s, CFG_CLUSTER_ADDRESS,     "soizic-vaio")
soma_wf_cfg.set(s, OCFG_DRMS,               'SGE')
#Server
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FORMAT,   "%(asctime)s => line %(lineno)s: %(message)s")
soma_wf_cfg.set(s, OCFG_SERVER_LOG_LEVEL,    'DEBUG')
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FILE,     '/home/soizic/soma-jobs-server/log_jobServer')
soma_wf_cfg.set(s, CFG_NAME_SERVER_HOST,     'None')
soma_wf_cfg.set(s, CFG_SERVER_NAME,          'JobServer')
soma_wf_cfg.set(s, CFG_TRANSFERED_FILES_DIR, '/home/soizic/soma-jobs-server/jobFiles/')
soma_wf_cfg.set(s, CFG_DATABASE_FILE,        '/home/soizic/soma-jobs-server/jobs.db')

###############
# DSV CLUSTER #
###############

s = 'DSV_cluster'

soma_wf_cfg.add_section(s)
#Parallel job specific submission information
soma_wf_cfg.set(s, OCFG_PARALLEL_COMMAND,   "-l nodes={max_node}") 
soma_wf_cfg.set(s, OCFG_PARALLEL_PC_MPI,  'mpi')
soma_wf_cfg.set(s, OCFG_PARALLEL_ENV_MPI_BIN,   '/opt/mpich/gnu/bin/')
soma_wf_cfg.set(s, OCFG_PARALLEL_ENV_NODE_FILE, '$PBS_NODEFILE')
#Engine
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_FORMAT, '%(asctime)s => %(module)s line %(lineno)s: %(message)s                 %(threadName)s')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_DIR,    '/home/sl225510/soma-jobs-server/logs/')
#Computing resource
soma_wf_cfg.set(s, CFG_SUBMITTING_MACHINES,    'gabriel.intra.cea.fr')
soma_wf_cfg.set(s, CFG_CLUSTER_ADDRESS,        'gabriel.intra.cea.fr')
soma_wf_cfg.set(s, OCFG_DRMS,               'PBS') 
#Server
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FORMAT, "%(asctime)s => line %(lineno)s: %(message)s")
soma_wf_cfg.set(s, OCFG_SERVER_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FILE,   '/home/sl225510/soma-jobs-server/logs/log_jobServer')
soma_wf_cfg.set(s, CFG_NAME_SERVER_HOST,   'gabriel.intra.cea.fr')
soma_wf_cfg.set(s, CFG_SERVER_NAME,        'JobServer')
soma_wf_cfg.set(s, CFG_TRANSFERED_FILES_DIR,  '/home/sl225510/soma-jobs-server/jobFiles/')
soma_wf_cfg.set(s, CFG_DATABASE_FILE,      '/home/sl225510/soma-jobs-server/jobs.db')

#################
# HIPIP CLUSTER #
#################

s = 'HiPiP_cluster'

soma_wf_cfg.add_section(s)
#Engine
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_FORMAT, '%(asctime)s => %(module)s line %(lineno)s: %(message)s                 %(threadName)s')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_DIR,    '/home/cea/soma-jobs-server/logs/')
#Computing resource
soma_wf_cfg.set(s, CFG_SUBMITTING_MACHINES,    'hipip0')
soma_wf_cfg.set(s, CFG_CLUSTER_ADDRESS,        'hipipcluster')
soma_wf_cfg.set(s, OCFG_DRMS,               'SGE') 
#Server
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FORMAT, "%(asctime)s => line %(lineno)s: %(message)s")
soma_wf_cfg.set(s, OCFG_SERVER_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FILE,   '/home/cea/soma-jobs-server/logs/log_jobServer')
soma_wf_cfg.set(s, CFG_NAME_SERVER_HOST,       'hipip0')
soma_wf_cfg.set(s, CFG_SERVER_NAME,        'JobServer')
soma_wf_cfg.set(s, CFG_TRANSFERED_FILES_DIR,      '/home/cea/soma-jobs-server/jobFiles/')
soma_wf_cfg.set(s, CFG_DATABASE_FILE,          '/home/cea/soma-jobs-server/jobs.db')
#Shared resource path translation file
soma_wf_cfg.set(s, OCFG_PATH_TRANSLATION_FILES, 'example{/home/cea/soma-jobs-server/translation_file_examples/job_examples.sjtr}  brainvisa{/home/cea/.brainvisa/soma-workflow.translation}')


##################
# LOCAL is206464 #
##################

s = 'local_is206464'

soma_wf_cfg.add_section(s)
#Engine
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_FORMAT, '%(asctime)s => %(module)s line %(lineno)s: %(message)s                 %(threadName)s')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_LEVEL,  'DEBUG')
soma_wf_cfg.set(s, OCFG_ENGINE_LOG_DIR,    '/home/soizic/soma_workflow_server/logs/')
#Computing resource
soma_wf_cfg.set(s, CFG_SUBMITTING_MACHINES, 'is206464')
soma_wf_cfg.set(s, CFG_CLUSTER_ADDRESS,     'is206464')
soma_wf_cfg.set(s, OCFG_DRMS,               'SGE') 
#Server
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FORMAT,   "%(asctime)s => line %(lineno)s: %(message)s")
soma_wf_cfg.set(s, OCFG_SERVER_LOG_LEVEL,    'DEBUG')
soma_wf_cfg.set(s, OCFG_SERVER_LOG_FILE,     '/home/soizic/soma_workflow_server/logs/log_server')
soma_wf_cfg.set(s, CFG_NAME_SERVER_HOST,     'is206464')
soma_wf_cfg.set(s, CFG_SERVER_NAME,          'workflow_server')
soma_wf_cfg.set(s, CFG_TRANSFERED_FILES_DIR, '/home/soizic/soma_workflow_server/transfered_files/')
soma_wf_cfg.set(s, CFG_DATABASE_FILE,        '/home/soizic/soma_workflow_server/soma_workflow.db') 
#Shared resource path translation file
soma_wf_cfg.set(s, OCFG_PATH_TRANSLATION_FILES, 'example{/home/soizic/soma_workflow_server/translation_file_examples/job_examples.sjtr}  brainvisa{/home/soizic/.brainvisa/soma-workflow.translation}')



#####################################################"
with open('soma_workflow.cfg', 'wb') as configfile:
    soma_wf_cfg.write(configfile)