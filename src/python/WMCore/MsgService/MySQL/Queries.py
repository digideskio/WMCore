#!/usr/bin/env python

"""
_Queries_

This module implements the mysql backend for the message
service.

"""

__revision__ = \
    "$Id: Queries.py,v 1.2 2008/08/28 20:40:50 fvlingen Exp $"
__version__ = \
    "$Revision: 1.2 $"
__author__ = \
    "fvlingen@caltech.edu"

import threading

from WMCore.Database.DBFormatter import DBFormatter

class Queries(DBFormatter):
    """
    _Queries_
    
    This module implements the mysql backend for the message
    service.
    
    """
    
    def __init__(self):
        myThread = threading.currentThread()
        DBFormatter.__init__(self, myThread.logger, myThread.dbi)
        
    def checkName(self, args):
        """
        __checkName__

        Checks the name of the component in the backend.
        """

        sqlStr = """ 
SELECT procid, host, pid FROM ms_process WHERE name = :name 
""" 
        result = self.execute(sqlStr, args)
        return self.formatOneDict(result)

    def updateName(self, args):
        """
        __updateName__

        Updates the name of the component in the backend.
        """

        sqlStr = """
UPDATE ms_process SET pid = :currentPid, host = :currentHost WHERE name = :name
"""
        self.execute(sqlStr, args)

    def insertProcess(self, args):
        """
        __insertProcess__

        Inserts the name of the component in the backend
        """

        sqlStr = """
INSERT INTO ms_process(host,pid,name) VALUES (:host,:pid,:name)
"""
        self.execute(sqlStr, args)

    def lastInsertId(self, args = {}):
        """
        __lastInsertId__

        Checks for last inserted id 
        """

        sqlStr = """
SELECT LAST_INSERT_ID()
"""
        result = self.execute(sqlStr, args)
        return self.formatOne(result)[0]

    def checkMessageType(self, args = {}):
        """
        __checkMessageType__
 
        Checks if the name for a message is already registered in the database
        """
        sqlStr = """
SELECT typeid,name FROM ms_type WHERE name = :name """ 
        result = self.execute(sqlStr, args)
        return self.formatOneDict(result)

    def insertMessageType(self,args = {}):
        """
        __insertMessageType__
 
        Inserts a new message type
        """
        sqlStr = """
INSERT INTO ms_type(name) VALUES(:name)
"""
        self.execute(sqlStr, args)

    def checkSubscription(self, args = {}):
        """

        __checkSubscription__

        Checks if a component is already subscribed
        """
        sqlStr = """
SELECT procid, typeid FROM ms_subscription WHERE procid = :procid 
AND typeid = :typeid
""" 
        result = self.execute(sqlStr, args)
        return self.formatOneDict(result)

    def insertSubscription(self, args = {}):
        """
        __insertSubscription__

        Inserts a subscription to a message.
        """

        sqlStr = """
INSERT INTO ms_subscription(procid,typeid) VALUES(:procid,:typeid)
"""
        self.execute(sqlStr, args)

    def checkPrioritySubscription(self, args = {}):
        """

        __checkPrioritySubscription__

        Checks if a component is already subscribed
        """
        sqlStr = """
SELECT procid, typeid FROM ms_subscription_priority WHERE procid = :procid 
AND typeid = :typeid
""" 
        result = self.execute(sqlStr, args)
        return self.formatOneDict(result)

    def insertPrioritySubscription(self, args = {}):
        """
        __insertPrioritySubscription__

        Inserts a subscription to a message.
        """

        sqlStr = """
INSERT INTO ms_subscription_priority(procid,typeid) VALUES(:procid,:typeid)
"""
        self.execute(sqlStr, args)

    def subscriptions(self, args ={}):
        """
        __subscriptions__

        Returns a list (array) of subscriptions
        """
        sqlStr = """ 
SELECT ms_type.name FROM ms_subscription,ms_type WHERE procid = :procid 
AND ms_subscription.typeid = ms_type.typeid 
        """
        result = self.execute(sqlStr, args)
        return self.format(result)

    def prioritySubscriptions(self, args ={}):
        """
        __prioritySubscriptions__

        Returns a list (array) of subscriptions
        """
        sqlStr = """ 
SELECT ms_type.name FROM ms_subscription_priority,ms_type WHERE procid = :procid 
AND ms_subscription_priority.typeid = ms_type.typeid 
        """
        result = self.execute(sqlStr, args)
        return self.format(result)

    def getDestinations(self, args = {}):
        """
        __getDestinations__

        Find out who are the receivers of your published message.
        """

        sqlStr = """
SELECT ms_subscription.procid,ms_process.name FROM ms_subscription, ms_process WHERE ms_subscription.typeid = :typeid AND 
ms_subscription.procid = ms_process.procid
 """ 
        result = self.execute(sqlStr, args)
        return self.format(result)

    def getPriorityDestinations(self, args={}):
        """
        __getPriorityDestinations__

        Find out who are the receivers of your published message.
        """

        sqlStr = """
SELECT ms_subscription_priority.procid,ms_process.name FROM ms_subscription_priority, ms_process WHERE ms_subscription_priority.typeid = :typeid AND 
ms_subscription_priority.procid = ms_process.procid
""" 
        result = self.execute(sqlStr, args)
        return self.format(result)

    def initializeAvailable(self, args= {}):
        """
        __initializeArrive__

        initializes meta data on arriving messages.
        """
        sqlStr1 = """
INSERT INTO ms_available(procid) VALUES(:procid)
"""
        sqlStr2 = """
INSERT INTO ms_available_priority(procid) VALUES(:procid)
"""
        self.execute(sqlStr1, args)        
        self.execute(sqlStr2, args)        

    def msgArrived(self, args = {}):
        """
        __msgArrived__

        sets the flag in a small table (metadata) that
        a message has arrived for a component so the component
        does not need to check a big table for this.
        """
        sqlStr = """
INSERT INTO %s(procid) VALUES(:procid) ON DUPLICATE KEY UPDATE status = 'there'
""" %(args['table'])

        # format for bind input
        input = []
        for dest in args['msgs'].keys():
            input.append({'procid':dest})
        self.execute(sqlStr, input)

    def insertMsg(self, args = {}):
        """
        __insertMsg__

        inserts messages in specific (buffer) tables.
        """
        sqlStr = """
INSERT INTO %s(type,source,dest,payload,delay) VALUES(:type,:source,:dest,:payload,:delay)
""" %(args['table'])

        # we need to cut things up as mysql can not deal with very large 
        # inserts (over 500). We are conservative and stop at 100
        if len(args['msgs'])>100:
            start = 0
            end = 100
            while start < len(args['msgs']):
                if end > len(args['msgs']):
                    end = len(args['msgs']) 
                self.execute(sqlStr, args['msgs'][start:end])
                start += 100
                end += 100 
            return 
        self.execute(sqlStr, args['msgs'])

    def insertComponentMsgTables(self, componentName):
        prefix1 = 'ms_message_'+componentName
        prefix2 = 'ms_priority_message_'+componentName

        for prefix in [prefix1,prefix2]:
              for postfix in ['','_buffer_in','_buffer_out']:
                  tableName = prefix+postfix
                  sqlStr = """
CREATE TABLE `%s` (
   `messageid` int(11) NOT NULL auto_increment,
   `type` int(11) NOT NULL default '0',
   `source` int(11) NOT NULL default '0',
   `dest` int(11) NOT NULL default '0',
   `payload` text NOT NULL,
   `time` timestamp NOT NULL default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   `delay` varchar(50) NOT NULL default '00:00:00',

   PRIMARY KEY `messageid` (`messageid`),
   FOREIGN KEY(`type`) references `ms_type`(`typeid`),
   FOREIGN KEY(`source`) references `ms_process`(`procid`),
   FOREIGN KEY(`dest`) references `ms_process`(`procid`)
   ) ENGINE=InnoDB DEFAULT CHARSET=latin1;
""" %(tableName)
                  self.execute(sqlStr, {})

    def tableSize(self, args):
        """
        __tableSize__

        returns the table size to deal with buffer movements.
        """
        sqlStr = """
SELECT COUNT(*) FROM %s """  %(args)
        result = self.execute(sqlStr, {})
        result = self.formatOne(result)[0]
        return result

    def showTables(self):
        result = self.execute("show tables", {})
        return self.format(result)

    def moveMsg(self, args):
        """
        __moveMsg__

        Moves message from one table to another.

        """
        sqlStr1 = """
INSERT INTO %s(type,source,dest,payload,time,delay) SELECT type,source,dest,payload,time,delay FROM %s
""" %(str(args['target']), str(args['source']))
        sqlStr2 = """ 
DELETE FROM %s 
""" %(str(args['source']))

        self.execute(sqlStr1, {})
        self.execute(sqlStr2, {})

    def maxId(self, args):
        sqlStr = """
SELECT MAX(messageid) from %s
""" %(args['table'])
        result = self.execute(sqlStr, {})
        return self.formatOne(result)

    def purgeHistory(self, args):
        sqlStr = """
DELETE FROM %s WHERE messageid < %s
""" %(args['table'], str(args['maxId']))
        self.execute(sqlStr, {})

    def execute(self, sqlStr, args):
        """"
        __execute__
        Executes the queries by getting the current transaction
        and dbinterface object that is stored in the reserved words of
        the thread it operates in.
        """
        myThread = threading.currentThread()
        currentTransaction = myThread.transaction
        return currentTransaction.processData(sqlStr, args) 
