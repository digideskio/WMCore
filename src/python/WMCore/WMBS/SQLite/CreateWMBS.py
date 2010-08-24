"""
_CreateWMBS_

Implementation of CreateWMBS for SQLite.
"""

__revision__ = "$Id: CreateWMBS.py,v 1.11 2008/09/19 16:32:42 metson Exp $"
__version__ = "$Reivison: $"

from WMCore.WMBS.CreateWMBSBase import CreateWMBSBase

class CreateWMBS(CreateWMBSBase):
    def __init__(self, logger, dbInterface):
        """
        _init_

        Call the base class's constructor and create all necessary tables,
        constraints and inserts.
        """
        CreateWMBSBase.__init__(self, logger, dbInterface)
        self.requiredTables.append('20wmbs_subs_type')
        
        self.create["01wmbs_fileset"] = \
          """CREATE TABLE wmbs_fileset (
             id          INTEGER      PRIMARY KEY AUTOINCREMENT,
             name        VARCHAR(255) NOT NULL,
             open        BOOLEAN      NOT NULL DEFAULT FALSE,
             last_update TIMESTAMP    NOT NULL,
             UNIQUE (name))"""
        
        self.create["02wmbs_file_details"] = \
          """CREATE TABLE wmbs_file_details (
             id           INTEGER      PRIMARY KEY AUTOINCREMENT,
             lfn          VARCHAR(255) NOT NULL,
             size         INT(11),
             events       INT(11),
             first_event  INT(11),
             last_event   INT(11))"""
        
        self.create["03wmbs_fileset_files"] = \
          """CREATE TABLE wmbs_fileset_files (
             file        INT(11)   NOT NULL,
             fileset     INT(11)   NOT NULL,
             insert_time TIMESTAMP NOT NULL,
             status      INT(11),
             FOREIGN KEY(fileset) references wmbs_fileset(id)
             FOREIGN KEY(status)  references wmbs_file_status(id)
               ON DELETE CASCADE)"""

        self.create["04wmbs_file_parent"] = \
          """CREATE TABLE wmbs_file_parent (
             child  INT(11) NOT NULL,
             parent INT(11) NOT NULL,
             FOREIGN KEY (child)  references wmbs_file(id)
               ON DELETE CASCADE,
             FOREIGN KEY (parent) references wmbs_file(id),
             UNIQUE(child, parent))"""  
        
        self.create["05wmbs_file_runlumi_map"] = \
          """CREATE TABLE wmbs_file_runlumi_map (
             file    INT(11),
             run     INT(11),
             lumi    INT(11),
             FOREIGN KEY (file) references wmbs_file(id)
               ON DELETE CASCADE)"""
        
        self.create["06wmbs_location"] = \
          """CREATE TABLE wmbs_location (
             id      INTEGER      PRIMARY KEY AUTOINCREMENT,
             se_name VARCHAR(255) NOT NULL,
             UNIQUE(se_name))"""
             
        self.create["07wmbs_file_location"] = \
          """CREATE TABLE wmbs_file_location (
             file     INT(11),
             location INT(11),
             UNIQUE(file, location),
             FOREIGN KEY(file)     REFERENCES wmbs_file(id)
               ON DELETE CASCADE,
             FOREIGN KEY(location) REFERENCES wmbs_location(id)
               ON DELETE CASCADE)"""
        
        self.create["08wmbs_workflow"] = \
          """CREATE TABLE wmbs_workflow (
             id           INTEGER      PRIMARY KEY AUTOINCREMENT,
             spec         VARCHAR(255) NOT NULL,
             name         VARCHAR(255) NOT NULL,
             owner        VARCHAR(255))"""

        self.create["09wmbs_subscription"] = \
          """CREATE TABLE wmbs_subscription (
             id          INTEGER      PRIMARY KEY AUTOINCREMENT,
             fileset     INT(11)      NOT NULL,
             workflow    INT(11)      NOT NULL,
             split_algo  VARCHAR(255) NOT NULL DEFAULT 'File',
             type        INT(11)      NOT NULL,
             last_update TIMESTAMP    NOT NULL,
             FOREIGN KEY(fileset)  REFERENCES wmbs_fileset(id)
               ON DELETE CASCADE
             FOREIGN KEY(type)     REFERENCES wmbs_subs_type(id)
               ON DELETE CASCADE
             FOREIGN KEY(workflow) REFERENCES wmbs_workflow(id)
               ON DELETE CASCADE)""" 

        self.create["10wmbs_sub_files_acquired"] = \
          """CREATE TABLE wmbs_sub_files_acquired (
             subscription INT(11) NOT NULL,
             file         INT(11) NOT NULL,
             FOREIGN KEY (subscription) REFERENCES wmbs_subscription(id)
               ON DELETE CASCADE,
             FOREIGN KEY (file)         REFERENCES wmbs_file(id))
             """

        self.create["11wmbs_sub_files_failed"] = \
          """CREATE TABLE wmbs_sub_files_failed (
             subscription INT(11) NOT NULL,
             file         INT(11) NOT NULL,
             FOREIGN KEY (subscription) REFERENCES wmbs_subscription(id)
               ON DELETE CASCADE,
             FOREIGN KEY (file)         REFERENCES wmbs_file(id))"""

        self.create["12wmbs_sub_files_complete"] = \
          """CREATE TABLE wmbs_sub_files_complete (
          subscription INT(11) NOT NULL,
          file         INT(11) NOT NULL,
          FOREIGN KEY (subscription) REFERENCES wmbs_subscription(id)
            ON DELETE CASCADE,
          FOREIGN KEY (file)         REFERENCES wmbs_file(id))"""

        self.create["13wmbs_jobgroup"] = \
          """CREATE TABLE wmbs_jobgroup (
             id          INTEGER   PRIMARY KEY AUTOINCREMENT,
             subscription INT(11)   NOT NULL,
             last_update TIMESTAMP NOT NULL,
             FOREIGN KEY (subscription) REFERENCES wmbs_subscription(id)
               ON DELETE CASCADE)"""

        self.create["14wmbs_job"] = \
          """CREATE TABLE wmbs_job (
             id          INTEGER   PRIMARY KEY AUTOINCREMENT,
             jobgroup    INT(11)   NOT NULL,
             start       INT(11),
             completed   INT(11),
             retries     INT(11),
             last_update TIMESTAMP NOT NULL,
             FOREIGN KEY (jobgroup) REFERENCES wmbs_jobgroup(id)
               ON DELETE CASCADE)"""

        self.create["15wmbs_job_assoc"] = \
          """CREATE TABLE wmbs_job_assoc (
             job    INT(11) NOT NULL,
             file   INT(11) NOT NULL,
             FOREIGN KEY (job)  REFERENCES wmbs_job(id)
               ON DELETE CASCADE,
             FOREIGN KEY (file) REFERENCES wmbs_file(id)
               ON DELETE CASCADE)"""

        self.create["20wmbs_subs_type"] = \
          """CREATE TABLE wmbs_subs_type (
             id   INTEGER      PRIMARY KEY AUTOINCREMENT,
             name VARCHAR(255) NOT NULL)"""

        for subType in ("Processing", "Merge", "Job"):
            subTypeQuery = "INSERT INTO wmbs_subs_type (name) values ('%s')" % \
                           subType
            self.inserts["wmbs_subs_type_%s" % subType] = subTypeQuery
