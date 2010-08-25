#!/usr/bin/env python
"""
_LoadByID_

SQLite implementation of BossLite.Task.LoadByID
"""

__all__ = []
__revision__ = "$Id: LoadByID.py,v 1.1 2010/03/30 10:21:52 mnorman Exp $"
__version__ = "$Revision: 1.1 $"

from WMCore.BossLite.MySQL.Task.LoadByID import LoadByID as MySQLLoadByID

class LoadByID(MySQLLoadByID):
    """
    Identical to MySQL

    """
