#!/bin/bash

while true; do
  echo `date`>>/home/ubuntu/to-backup/test_file.txt
  /home/ubuntu/python-duplicity-backup/duplicity-backup.py
  #rsync -aut /home/ubuntu/test-backup/ /home/ubuntu/simulated-tape/
  #-a=rlptgoD
  #r= recurse into directories
  #l=copy symlinks as symlinks
  #p=preserve permissions
  #t=preserve modification times
  #g=preserve group
  #o=preserve owner
  #D= preserve device files, preserve special files
  
  sleep 10
done
