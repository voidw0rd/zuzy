#!/bin/env python

import syslog
import subprocess
import json
import tempfile
from optparse import OptionParser
#
#
#
class Commit(object):
  #
  #
  def __init__(self, cmd):
    self.cmd = cmd
  #
  #
  def cmd_output(self, cmd):
    syslog.syslog("[func] cmd_output()")
    return subprocess.Popen(
      cmd.split(), stdout=subprocess.PIPE).communicate()[0]
  # get the commit file names
  # output list
  def get_commit_files(self):
    syslog.syslog("[func] get_commit_files()")
    # get the file name
    # input `U   trunk/<filename.*>` | output input `<filename.*>`
    def filename(line):
      syslog.syslog("[func] filename()")
      result = line[4:]
      return result
    # make sure the `line` ( U   trunk/<filename.*> ) 
    # is update or add
    def added_or_updated(line):
      syslog.syslog("[func] added_or_updated()")
      if len(line) is 0:
        return False
      if str(line[0]) in ("A", "U"):
        #syslog.syslog("[xx] added_or_updated() - %s " % str(line[0]))
        return True
      else:
        #syslog.syslog("[xxxx] added_or_updated() - %s " % str(line[0]))
        return False
    # get all files that are U | A 
    # ignore the rest (eg, D)
    result = []
    for line in self.cmd_output(self.cmd % "changed").split("\n"):
      if added_or_updated(line):
        line = filename(line)
        #syslog.syslog("[i] %s" % line)
        result.append(line)
      else:
        pass
        #syslog.syslog("[i] %s" % line)
    return result
  # write the content of the file to a new temp file 
  # in order to be able to run cmd's on it (eg, `stat`)
  def write_tmp_files(self, file, extension):
    syslog.syslog("[func] write_tmp_files()")
    _f = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    content = self.get_file_content(file)
    _f.write(content)
    _f.flush()
    _f.close()
    return _f.name
  # get the file contents from the commit
  #
  def get_file_content(self, filename):
    syslog.syslog("[func] get_file_content()")
    return self.cmd_output(
      "%s %s" % (self.cmd % "cat", filename))
  # get all the commit files and write them to disk
  # return a list of dict's 
  def get_file_info(self):
    syslog.syslog("[func] get_file_info()")
    files = self.get_commit_files()

    files_info = []
    for file in files:
      extension = "." + str(file.split(".")[-1:][0])
      path = self.write_tmp_files(file, extension)
      file_dict = {
        "name": str(file),
        "path": path,
        #"mimetype": "",
        #"size": "",
      }
      files_info.append(file_dict)
      #syslog.syslog(str(file_dict))
    return files_info
  # return the commit info as a dict 
  # 
  def get_commit_data(self):
    syslog.syslog("[func] get_commit_data()")
    data = self.get_file_info()
    return {"commit": data}
#
#
#
class Policy(object):
  #
  #
  #
  def __init__(self, policy=None):
    if policy:
      self.policy = policy
    else:
      self.policy = {
        "size": 10485760, # 10MB, this size is in bytes
        "mimetypes": [
          'text/plain', 
          'text/x-python', 
          "application/octet-stream"
        ],
        "baned-chars": ['~', "#"]
      }
  #
  #
  def cmd_output(self, cmd):
    syslog.syslog("[func] cmd_output()")
    return subprocess.Popen(
      cmd.split(), stdout=subprocess.PIPE).communicate()[0]
  # run file --mime-type on the 
  # temp files and return the type
  def __run_file_cmd(self, filepath):
    syslog.syslog("[func] __run_file_cmd()")
    cmd = "file --mime-type %s" % filepath
    output = self.cmd_output(cmd)
    output = output.split(": ")[-1:][0]
    syslog.syslog("[x] File: %s - mimetype: %s" % (filepath, output))
    return output.strip()
  # return the mimetype
  #
  def __run_stat_cmd(self, filepath):
    syslog.syslog("[func] __run_stat_cmd()")
    cmd = "stat -c %s " + filepath
    output = self.cmd_output(cmd)
    return output
  #
  #
  def __check_mimetype(self, file):
    syslog.syslog("[func] check_mimetype()")
    return self.__run_file_cmd(file['path'])
  # 
  #
  def check_mimetypes(self, files):
    """return the mimetypes of all files"""
    syslog.syslog("[func] check_mimetypes()")
    for file in files['commit']:
      mimetype = self.__check_mimetype(file)
      syslog.syslog(mimetype)
      if mimetype not in self.policy['mimetypes']:
        syslog.syslog("mimetype: %s is not allowed." % mimetype)
        sys.stderr.write("mimetype: %s is not allowed." % mimetype)
        return False
    return True
  # check to see if files start with `.`
  # on windows or OS X this tend's to brake
  def __check_hidden_file(self, file):
    syslog.syslog("[func] __check_hidden_file() - %s" % file['name'])
    return file['name'].startswith(".")
  #
  #
  def check_special_chars(self, files):
    """check to see if the file names contain special
    chars, some chars tend to brake on windows and OS X"""
    syslog.syslog("[func] check_special_chars()")
    for file in files['commit']:
      if self.__check_hidden_file(file):
        syslog.syslog("Files starting with `.` are not allowed.")
        sys.stderr.write("Files starting with `.` are not allowed.")
        return False
      for char in self.policy['baned-chars']:
        if char in str(file):
          syslog.syslog("Funny chars are not allowed.")
          sys.stderr.write("Funny chars are not allowed.")
          return False
    return True
  # 
  # 
  def check_files_size(self, files):
    """check too see if the file is in range of the 
    allowed file size"""
    for file in files['commit']:
      size = int(self.__run_stat_cmd(file['path']))
      if size > self.policy['size']:
        syslog.syslog("[x] file %s is too big - filesize: %d" % (str(file['path']), size))
        sys.stderr.write("[x] file %s is too big" % str(file['path']))
        return False
    return True
  #
  #
  def validate(self, files):
    syslog.syslog("[func] validate() - begin")
    #
    for policy in Policy.__dict__.items():
      if policy[0].startswith("check_"):
        method = self.__getattribute__(policy[0])
        outcome = method(files)
        if not outcome:
          syslog.syslog(method.__doc__)
          return False
      # policy[1]._notes % self.policy
    return True
# # # # # # # # # # # # # # # # # # # # # # # # # #      
#               ZuZy svn pre-commit               #
# # # # # # # # # # # # # # # # # # # # # # # # # #
def main():
  usage = """usage: %prog REPOS TXN

  Run pre-commit options on a repository transaction."""
  parser = OptionParser(usage=usage)
  parser.add_option("-r", "--revision",
                    help="TXN actually refers to a revision.",
                    action="store_true", default=False)
  errors = 0
  try:
      (opts, (repos, txn_or_rvn)) = parser.parse_args()
      look_opt = ("--transaction", "--revision")[opts.revision]
      look_cmd = "svnlook %s %s %s %s" % (
          "%s", repos, look_opt, txn_or_rvn)
      commit = Commit(look_cmd)
      policy = Policy()
      data = commit.get_commit_data()
      if not policy.validate(data): 
        errors += 1
      syslog.syslog("pre-commit hook exiting.")
  except:
      parser.print_help()
      errors += 1
  return errors

if __name__ == "__main__":
  import sys
  sys.exit(main())
  