#!/usr/bin/env python

import optparse as op
import os
import glob
import datetime
import subprocess as sp
import sys

secondsPerDay=60.0*60.0*24.0

class backupData:
  
  def __init__(self,**kwargs):
    
    #set default values
    self.daysBeforeFullBackups=2
    self.nBackupsToKeep=2
    self.pathsToExclude=None
    self.pathsToInclude=None
    self.lPathsToRestore=None
    self.dryRun=False
    
    for key in kwargs:
      
      #set directory to store log files
      if key=="logFileDirectory":
        #make sure log file path ends with '/'
        logFileDirectoryTemp=kwargs[key]
        if logFileDirectoryTemp[len(logFileDirectoryTemp)-1] !='/':
          logFileDirectoryTemp=logFileDirectoryTemp+'/'
        self.logFileDirectory=logFileDirectoryTemp
      else:
        
        #other variables just add
        self.__dict__[key]=kwargs[key]
      
      '''
        #set directory to backup
        if key=="fromDirectory":
          self.fromDirectory=kwargs[key]
          
        #set directory to hold backup
        if key=="toDirectory":
          self.toDirectory=kwargs[key]
        
        #set number of days before full backup
        if key=="daysBeforeFullBackups":
          self.daysBeforeFullBackups=kwargs[key]
        
        #set number of full backups to keep
        if key=="nBackupsToKeep":
          self.nBackupsToKeep=kwargs[key]
        
        #set list of paths to exclude from backup
        if key=="pathsToExclude":
          self.pathsToExclude=kwargs[key]
        
        #set list of paths to include in backup
        if key=="pathsToInclude":
          self.pathsToInclude=kwargs[key]
          
        #set path to put mysql dump in
        if key=="mySQLDumpPath":
          self.mySQLDumpPath=kwargs[key]
        
        if key=="mySQLUser":
          self.mySQLUser=kwargs[key]
        
        if key=="mySQLPass":
          self.mySQLPass=kwargs[key]'''
  def setDryRun(self):
    self.dryRun=True
  def setRestorePath(self,sRestorePath):
    self.fromDirectory=sRestorePath
def getParser():
  
  #create parser for command line options and arguments
  parser=op.OptionParser(usage="%prog [options] [path to restore to]", version="%prog 0.0"
    ,description="This script provides a simple front end for duplicity, allowing settings to be "+
    "set in this script, so that when called from crotab those settings can be applied. It also "+
    "adds a log management system allowing log files to be created for each new full backup, and "+
    "added to for each incremental backup until the next full backup. [options] is the list of "+
    "options given below, and [path to restore to] sets either the path and directory name, or "+
    "filename, if it is a specific file, to restore the backup to and cannot "+
    "already exist. The [path to restore to] only has an effect if the -r options is set also."+
    "See \"man duplicity\" for more backup functionality not provided with this script.")
  
  restore_group=op.OptionGroup(parser,"Restore options", "All of these options only have an "+
    "effect if the -r option is also specified")
  
  parser.add_option("-d","--dry-run",action="store_true",dest="dryRun",default=False
    ,help="If set it will perform a dry run only, which will print the duplicity commands that "+
    "would be issued if it wasn't a dry run, but doesn't actually run the commands")
  
  #add restore options
  restore_group.add_option("-r","--restore",action="store_true",dest="restore",default=False
    ,help="setting this flag activates restore mode, which if no path-to-restore is given it will "+
    "restore the entire backup to the directory specified, or the directory set in the "+
    "script.")
  
  restore_group.add_option("-p","--path-to-restore",type="string",dest="pathToRestore"
    ,help="This option sets a path to be restored from the archive. If not set when the -r option "+
    "is set the entire backup will be restored. This path is RELATIVE TO THE ROOT DIRECTORY OF "+
    "THE INITIAL BACKUP. This can be either a directory or a file.")
    
  restore_group.add_option("-t","--time",type="string",dest="timeToRestoreFrom",default="now"
    ,help="This option sets the time at which to restore the file from. This is"
    +" the same as the duplicity time string, see 'man duplicity' for details. "
    +"[default: %default]")
  
  parser.add_option_group(restore_group)
  
  return parser
def main():
  
  #set backup persistent options
  backupInfo=backupData(
    logFileDirectory="/var/log/python-duplicity-backup-logs"#place to store log files
    ,fromDirectory="/"#path to backup
    ,toDirectory="sftp://Acenet@142.12.33.10/diversity_vm_data_backup"#path to place backup in (can be local directory (file://) or some remote (sftp://) etc.)
    ,daysBeforeFullBackups=90#Number of days before pqreforming a full backup (0.010417, every 15 mins)
    ,nBackupsToKeep=2#Number of full backups to keep
    ,daysBeforeLogsRemoved=180#30 mins
    ,pathsToExclude=["/"]#list of paths to exclude from backup under fromDirectory
    ,pathsToInclude=["/var/lib/mysqlbackups/mysql","/usr/local/fedora","/var/www","/opt","/etc/apache2","/etc/letsencrypt"]# a list of paths to include in backup under fromDirectory
    ,mySQLDumpPath=""
    ,mySQLUser=""
    ,mySQLPass="")
  
  #parse arguments and options
  parser=getParser()
  (options,args)=parser.parse_args()
  
  if options.dryRun:
    backupInfo.setDryRun()
  
  #restore the backup
  if options.restore :
    
    pathToRestore=None
    if options.pathToRestore!=None:
      if len(options.pathToRestore)>0:
        pathToRestore=options.pathToRestore
    
    pathToRestoreTo=None
    if len(args)>0:
      if args[0]!=None:
        if len(args[0])>0 :
          pathToRestoreTo=args[0]
      
    restore(backupInfo,options.pathToRestore,options.timeToRestoreFrom
      ,pathToRestoreTo)
  else:
    
    #do backup
    backup(backupInfo)
def removeOldLogs(backupInfo):
  logFiles=glob.glob(backupInfo.logFileDirectory+"*.log")
  now=datetime.datetime.now()
  for logFile in logFiles:
    dateLogFile=logFile.rpartition('/')#remove path
    dateLogFile=dateLogFile[2].rstrip('.log')#remove extension
    fileDate=dateLogFile.split("-")#break up into year/month/day/hour/min/second
    logFileDateTime=datetime.datetime(int(fileDate[0]),int(fileDate[1])
      ,int(fileDate[2]),int(fileDate[3]),int(fileDate[4]),int(fileDate[5]))
    
    delta=now-logFileDateTime
    if delta.total_seconds()/secondsPerDay>backupInfo.daysBeforeLogsRemoved:
      #remove log
      os.remove(logFile)
def backup(backupInfo):
  
  #dump mysql databases if path setDryRun
  if backupInfo.mySQLDumpPath:
    mysqldump(backupInfo)
  
  #get date of last log file
  daysSinceLastLogFile=getDaysSinceLastLogFile(backupInfo)
  
  #if none found, assume no full backup
  if daysSinceLastLogFile==None:
    fullBackup(backupInfo) #do full backup
  else:
    
    #if date of last log file is older than specified number of days do full backup
    if daysSinceLastLogFile>=backupInfo.daysBeforeFullBackups:
      fullBackup(backupInfo) #do full backup
    
    #if date of last log file is < younger than specified number of days do incremental backup
    if daysSinceLastLogFile<backupInfo.daysBeforeFullBackups:
      incrementalBackup(backupInfo) #do incremental backup
  
  #remove old log files
  removeOldLogs(backupInfo)
def runCommand(cmd,dryRun,stream):
  if dryRun:
    print cmd
  else:
    #run the command
    process=sp.Popen(cmd,stdout=sp.PIPE,stderr=sp.PIPE)
    stdout,stderr=process.communicate()
    stream.write(stdout)
    stream.write(stderr)
    
    #if there was an error
    returnCode=process.returncode
    if returnCode!=0:
      return False
    return True
def restore(backupInfo,pathToRestore,time,pathToRestoreTo):
  
  cmd=["duplicity","--no-encryption"]
  if pathToRestore!=None:
    cmd.append("--file-to-restore")
    cmd.append(pathToRestore)
  cmd.append("-t")
  cmd.append(time)
  if pathToRestoreTo!=None:
    pathToRestoreTo=pathToRestoreTo
  else :
    pathToRestoreTo=backupInfo.fromDirectory
    
  cmd.append(backupInfo.toDirectory)
  cmd.append(pathToRestoreTo)
  
  if not runCommand(cmd,backupInfo.dryRun,sys.stdout):
    msg=str(__name__)+":"+str(restore.__name__)+": error restoring backup!"
    print msg
    return False
  
  return True
def getDaysSinceLastLogFile(backupInfo):
  """Returns days since last log file
  
  It includes fractional part of days as a decimal and is accurate to the second.
  """
  
  #get most recent log file date
  logFiles=glob.glob(backupInfo.logFileDirectory+"*.log")
  logFileDateTime=datetime.datetime.min
  if len(logFiles)==0:
    return None
  for logFile in logFiles:
    dateLogFile=logFile.rpartition('/')#remove path
    dateLogFile=dateLogFile[2].rstrip('.log')#remove extension
    fileDate=dateLogFile.split("-")#break up into year/month/day/hour/min/second
    logFileDateTimeTemp=datetime.datetime(int(fileDate[0]),int(fileDate[1])
      ,int(fileDate[2]),int(fileDate[3]),int(fileDate[4]),int(fileDate[5]))
    if logFileDateTimeTemp>logFileDateTime:
      logFileDateTime=logFileDateTimeTemp
  
  #take difference with today's date
  todaysDateTime=datetime.datetime.now()
  timeSinceLastLogFile=(todaysDateTime-logFileDateTime)
  return timeSinceLastLogFile.total_seconds()/secondsPerDay
def getLastLogFileName(backupInfo):
  
  #get most recent log file date
  logFiles=glob.glob(backupInfo.logFileDirectory+"*.log")
  logFileDateTime=datetime.datetime.min
  if len(logFiles)==0:
    return None
  for logFile in logFiles:
    dateLogFile=logFile.rpartition('/')#remove path
    dateLogFile=dateLogFile[2].rstrip('.log')#remove extension
    fileDate=dateLogFile.split("-")#break up into year/month/day/hour/min/second
    logFileDateTimeTemp=datetime.datetime(int(fileDate[0]),int(fileDate[1])
      ,int(fileDate[2]),int(fileDate[3]),int(fileDate[4]),int(fileDate[5]))
    if logFileDateTimeTemp>logFileDateTime:
      logFileDateTime=logFileDateTimeTemp
  
  logFileName=str(logFileDateTime.date())+"-"+str(logFileDateTime.hour)+"-" \
    +str(logFileDateTime.minute)+"-"+str(logFileDateTime.second)+".log"
  
  return os.path.join(backupInfo.logFileDirectory,logFileName)
def fullBackup(backupInfo):
  #does a full backup
  
  #get today's date
  todaysDateTime=datetime.datetime.now()
  
  #make log file name with full path
  logFileName=str(todaysDateTime.date())+"-"+str(todaysDateTime.hour)+"-" \
    +str(todaysDateTime.minute)+"-"+str(todaysDateTime.second)+".log"
  logFileWithPath=backupInfo.logFileDirectory+logFileName
  
  #create duplicity command
  cmd=["duplicity","full","--no-encryption","--allow-source-mismatch"]
  if backupInfo.pathsToInclude != None:
    for path in backupInfo.pathsToInclude:
      cmd.append("--include")
      cmd.append(path)
  if backupInfo.pathsToExclude != None:
    for path in backupInfo.pathsToExclude:
      cmd.append("--exclude")
      cmd.append(path)
  cmd.append(backupInfo.fromDirectory)
  cmd.append(backupInfo.toDirectory)
  
  f=open(logFileWithPath,'a')
  if not backupInfo.dryRun:
    f.write("====================FULL BACK UP====================\n")
  
  if not runCommand(cmd,backupInfo.dryRun,f):
    msg=str(__name__)+":"+str(fullBackup.__name__)+": error performing full backup!"
    f.write(msg)
    f.close()
    return False
  f.close()
  
  #remove old backups
  removeOldBackups(backupInfo) #remove all backups before y full backups
  cleanUp(backupInfo) #clean up left over stuff
  return True
def incrementalBackup(backupInfo):
  
  #get most recent log file name
  logFileName=getLastLogFileName(backupInfo)
  
  cmd=["duplicity","incremental","--no-encryption","--allow-source-mismatch"]
  if backupInfo.pathsToInclude != None:
    for path in backupInfo.pathsToInclude:
      cmd.append("--include")
      cmd.append(path)
  if backupInfo.pathsToExclude != None:
    for path in backupInfo.pathsToExclude:
      cmd.append("--exclude")
      cmd.append(path)
  cmd.append(backupInfo.fromDirectory)
  cmd.append(backupInfo.toDirectory)
  
  f=open(logFileName,'a')
  if not backupInfo.dryRun:
    f.write("\n=================INCREMENTAL BACK UP=================\n")
  
  if not runCommand(cmd,backupInfo.dryRun,f):
    msg=str(__name__)+":"+str(incrementalBackup.__name__)+": error performing incremental backup!\n"
    f.write(str(datetime.datetime.now())+" UTC")
    f.write(msg)
    f.close()
    return False
  f.close()

  return True
def removeOldBackups(backupInfo):
  
  cmd=["duplicity","remove-all-but-n-full",str(backupInfo.nBackupsToKeep),"--force","--no-encryption"]

  #get most recent log file name
  logFileName=getLastLogFileName(backupInfo)
  
  cmd.append(backupInfo.toDirectory)
  
  f=open(logFileName,'a')
  if not backupInfo.dryRun:
    f.write("\n=================REMOVE OLD BACK UPS=================\n")
  
  if not runCommand(cmd,backupInfo.dryRun,f):
    msg=str(__name__)+":"+str(fullBackup.__name__)+": error removing old backups!"
    f.write(msg)
    f.close()
    return False
  f.close()
  
  return True
def cleanUp(backupInfo):
  
  cmd=["duplicity","cleanup","--extra-clean","--force","--no-encryption"]

  #get most recent log file name
  logFileName=getLastLogFileName(backupInfo)
  
  cmd.append(backupInfo.toDirectory)
  
  f=open(logFileName,'a')
  if not backupInfo.dryRun:
    f.write("\n=================CLEANUP=================\n")
  
  if not runCommand(cmd,backupInfo.dryRun,f):
    msg=str(__name__)+":"+str(fullBackup.__name__)+": error cleaning up!"
    f.write(msg)
    f.close()
    return False
  
  f.close()
  return True
def mysqldump(backupInfo):
  os.system("mysqldump -u "+backupInfo.mySQLUser+" -p"+backupInfo.mySQLPass+" --all-databases>"+backupInfo.mySQLDumpPath\
    +"mysql_all_databases_dump.sql");
if __name__=="__main__":
  main()
