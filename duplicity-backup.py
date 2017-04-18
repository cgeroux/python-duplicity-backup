#!/usr/bin/env python

import optparse as op
import os
import glob
import datetime

class backupData:
  
  def __init__(self,**kwargs):
    
    #set default values
    self.nDaysBeforeFullBackups=2
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
      
      #set directory to backup
      if key=="fromDirectory":
        self.fromDirectory=kwargs[key]
        
      #set directory to hold backup
      if key=="toDirectory":
        self.toDirectory=kwargs[key]
      
      #set number of days before full backup
      if key=="nDaysBeforeFull":
        self.nDaysBeforeFullBackups=kwargs[key]
      
      #set number of full backups to keep
      if key=="nFullToKeep":
        self.nBackupsToKeep=kwargs[key]
      
      #set list of paths to exclude from backup
      if key=="lExcludePaths":
        self.pathsToExclude=kwargs[key]
      
      #set list of paths to include in backup
      if key=="lIncludePaths":
        self.pathsToInclude=kwargs[key]
        
      #set path to put mysql dump in
      if key=="lIncludePaths":
        self.mySQLDumpPath=kwargs[key]
      
      if key=="mySQLUser":
        self.mySQLUser=kwargs[key]
      
      if key=="mySQLPass":
        self.mySQLPass=kwargs[key]
  def setDryRun(self):
    self.dryRun=True
  def setRestorePath(self,sRestorePath):
    self.fromDirectory=sRestorePath
def main():
  
  #set backup persistent options
  
  backupInfo=backupData(
    logFileDirectory="/home/cgeroux/Documents/backup"#place to store log files
    ,fromDirectory="/home/"#path to backup
    #,fromDirectory="/home/cgeroux/Documents/HOME/minecraft_server/world1" #path to backup
    ,toDirectory="/home/common/SHARE/VIDEO/.backup"#path to place backup in
    ,nDaysBeforeFull=30#Number of days before preforming a full backup
    ,nFullToKeep=2#Number of full backups to keep
    ,lExcludePaths=["/home/common/SHARE/MUSIC","/home/common/SHARE/SOFTWARE"
      ,"/home/common/SHARE/VIDEO"]#list of paths to exclude from backup
    ,lIncludePaths=[]# a list of paths to include in backup under fromDirectory
    ,mySQLDumpPath="/home/common/"
    ,mySQLUser="root"
    ,mySQLPass="password")
  
  '''
  #test backup settings
  backupInfo=backupData(
    logFileDirectory="/home/cgeroux/Documents/backup/test"#place to store log files
    ,fromDirectory="/home/cgeroux/Documents/backup/test"#path to backup
    ,toDirectory="/home/cgeroux/Documents/backup/test_archive"#path to place backup in
    ,nDaysBeforeFull=1#Number of days before preforming a full backup
    ,nFullToKeep=1#Number of full backups to keep
    ,lExcludePaths=[]#list of paths to exclude from backup
    ,lPathsToInclude=[]
    )#list of paths to include in backup
  '''
  
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
    
  restore_group.add_option("-t","--time",type="int",dest="timeToRestoreFrom",default=0
    ,help="This option sets the time at which to restore the file from in days from the current "+
    "day.")
  
  parser.add_option_group(restore_group)
  
  #parse arguments and options
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
      
    restore(backupInfo,options.pathToRestore,options.timeToRestoreFrom,pathToRestoreTo)
    
  else:
    
    #do backup
    backup(backupInfo)
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
    if daysSinceLastLogFile>=backupInfo.nDaysBeforeFullBackups:
      fullBackup(backupInfo) #do full backup
    
    #if date of last log file is < younger than specified number of days do incremental backup
    if daysSinceLastLogFile<backupInfo.nDaysBeforeFullBackups:
      incrementalBackup(backupInfo) #do incremental backup
def restore(backupInfo,pathToRestore,time,pathToRestoreTo):
  
  cmd="duplicity --no-encryption "
  if pathToRestore!=None:
    cmd=cmd+"--file-to-restore "+pathToRestore
  if time>0:
    cmd=cmd+" -t "+str(time)+"D"
  if pathToRestoreTo!=None:
    pathToRestoreTo=pathToRestoreTo
  else :
    pathToRestoreTo=backupInfo.fromDirectory
    
  cmd=cmd+" "+" file://"+backupInfo.toDirectory+" "+pathToRestoreTo
  if backupInfo.dryRun:
    print cmd
  else:
    success=os.system(cmd)
    if success!=0:
      msg=str(__name__)+":"+str(restore.__name__)+": error restoring backup!"
      print msg
      return False
  return True
def getDaysSinceLastLogFile(backupInfo):
  
  #get most recent log file date
  logFiles=glob.glob(backupInfo.logFileDirectory+"*.log")
  logFileDate=datetime.date.min
  if len(logFiles)==0:
    return None
  for logFile in logFiles:
    dateLogFile=logFile.rpartition('/')#remove path
    dateLogFile=dateLogFile[2].rstrip('.log')#remove extension
    fileDate=dateLogFile.split("-")#break up into year/month/day
    logFileDateTemp=datetime.date(int(fileDate[0]),int(fileDate[1]),int(fileDate[2]))
    if logFileDateTemp>logFileDate:
      logFileDate=logFileDateTemp
  
  #take difference with today's date
  todaysDate=datetime.date.today()
  timeSinceLastLogFile=(todaysDate-logFileDate)
  return timeSinceLastLogFile.days
def getLastLogFileName(backupInfo):
  
  #get most recent log file date
  logFiles=glob.glob(backupInfo.logFileDirectory+"*.log")
  logFileDate=datetime.date.min
  if len(logFiles)==0:
    return None
  for logFile in logFiles:
    dateLogFile=logFile.rpartition('/')#remove path
    dateLogFile=dateLogFile[2].rstrip('.log')#remove extension
    fileDate=dateLogFile.split("-")#break up into year/month/day
    logFileDateTemp=datetime.date(int(fileDate[0]),int(fileDate[1]),int(fileDate[2]))
    if logFileDateTemp>logFileDate:
      logFileDate=logFileDateTemp
  
  return backupInfo.logFileDirectory+str(logFileDate)+".log"
def fullBackup(backupInfo):
  #does a full backup
  
  #get today's date
  todaysDate=datetime.date.today()
  
  #make log file name with full path
  logFileName=str(todaysDate)+".log"
  logFileWithPath=backupInfo.logFileDirectory+logFileName
  
  #create duplicity command
  cmd="duplicity full --no-encryption  --allow-source-mismatch"
  if backupInfo.pathsToInclude != None:
    for path in backupInfo.pathsToInclude:
      cmd=cmd+" --include "+path
  if backupInfo.pathsToExclude != None:
    for path in backupInfo.pathsToExclude:
      cmd=cmd+" --exclude "+path
  cmd=cmd+" "+backupInfo.fromDirectory+" file://"+backupInfo.toDirectory+">>"\
    +logFileWithPath
  
  if backupInfo.dryRun:
    print cmd
  else:
    f=open(logFileWithPath,'a')
    f.write("====================FULL BACK UP====================\n")
    f.close()
    success=os.system(cmd)
    if success!=0:
      f=open(logFileWithPath,'a')
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
  
  cmd="duplicity incremental --no-encryption --allow-source-mismatch"
  if backupInfo.pathsToInclude != None:
    for path in backupInfo.pathsToInclude:
      cmd=cmd+" --include "+path
  if backupInfo.pathsToExclude != None:
    for path in backupInfo.pathsToExclude:
      cmd=cmd+" --exclude "+path
  
  cmd=cmd+" "+backupInfo.fromDirectory+" file://"+backupInfo.toDirectory+">>"+logFileName
  if backupInfo.dryRun:
    print cmd
  else:
    f=open(logFileName,'a')
    f.write("\n=================INCREMENTAL BACK UP=================\n")
    f.close()
    success=os.system(cmd)
    if success!=0:
      f=open(logFileName,'a')
      msg=str(__name__)+":"+str(fullBackup.__name__)+": error performing incremental backup!"
      f.write(msg)
      f.close()
      return False
    f.close()
  return True
def removeOldBackups(backupInfo):
  
  cmd="duplicity remove-all-but-n-full "+str(backupInfo.nBackupsToKeep)+" --force --no-encryption"

  #get most recent log file name
  logFileName=getLastLogFileName(backupInfo)
  
  if logFileName !=None:
    cmd=cmd+" file://"+backupInfo.toDirectory+">>"+logFileName
  else:
    cmd=cmd+" file://"+backupInfo.toDirectory
  
  if backupInfo.dryRun:
    print cmd
  else:
    f=open(logFileName,'a')
    f.write("\n=================REMOVE OLD BACK UPS=================\n")
    f.close()
    success=os.system(cmd)
    if success!=0:
      f=open(logFileName,'a')
      msg=str(__name__)+":"+str(fullBackup.__name__)+": error removing old backups!"
      f.write(msg)
      f.close()
      return False
    f.close()
  return True
def cleanUp(backupInfo):
  
  cmd="duplicity cleanup "+" --extra-clean --force --no-encryption"

  #get most recent log file name
  logFileName=getLastLogFileName(backupInfo)
  if logFileName !=None:
    cmd=cmd+" file://"+backupInfo.toDirectory+">>"+logFileName
  else:
    cmd=cmd+" file://"+backupInfo.toDirectory
  if backupInfo.dryRun:
    print cmd
  else:
    f=open(logFileName,'a')
    f.write("\n=================CLEANUP=================\n")
    f.close()
    success=os.system(cmd)
    if success!=0:
      f=open(logFileName,'a')
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
