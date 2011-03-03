#!/usr/bin/env python
#pylint: disable-msg=E1101, W6501, W0142
# E1101:  Doesn't recognize section_() as defining objects
# W6501:  String formatting in log output
# W0142:  Dave likes himself some ** magic

"""
_Step.Executor.StageOut_

Implementation of an Executor for a StageOut step

"""

import os
import os.path
import logging
import signal

from WMCore.WMSpec.Steps.Executor           import Executor
from WMCore.FwkJobReport.Report             import Report

import WMCore.Storage.StageOutMgr as StageOutMgr
import WMCore.Storage.FileManager
#from WMCore.Storage.StageOutError import StageOutFailure

from WMCore.WMSpec.ConfigSectionTree import nodeParent, nodeName
from WMCore.WMSpec.Steps.StepFactory import getStepTypeHelper
from WMCore.Lexicon                  import lfn as lfnRegEx

from WMCore.WMSpec.Steps.Executors.LogArchive import Alarm, alarmHandler

class StageOut(Executor):
    """
    _StageOut_

    Execute a StageOut Step

    """

    def pre(self, emulator = None):
        """
        _pre_

        Pre execution checks

        """

        #Are we using an emulator?
        if (emulator != None):
            return emulator.emulatePre( self.step )



        print "Steps.Executors.StageOut.pre called"
        return None


    def execute(self, emulator = None):
        """
        _execute_


        """
        #Are we using emulators again?
        if (emulator != None):
            return emulator.emulate( self.step, self.job )


        overrides = {}
        if hasattr(self.step, 'override'):
            overrides = self.step.override.dictionary_()

        # Set wait to 15 minutes
        waitTime = overrides.get('waitTime', 900)

        logging.info("StageOut override is: %s " % self.step)

        # Pull out StageOutMgr Overrides

        # switch between old stageOut behavior and new, fancy stage out behavior
        useNewStageOutCode = False
        if overrides.has_key('newStageOut') and overrides.get('newStageOut'):
            useNewStageOutCode = True


        stageOutCall = {}
        if overrides.has_key("command") and overrides.has_key("option") \
               and overrides.has_key("se-name") and overrides.has_key("lfn-prefix"):
            logging.critical('using override in StageOut')
            stageOutCall['command']    = overrides.get('command')
            stageOutCall['option']     = overrides.get('option')
            stageOutCall['se-name']    = overrides.get('se-name')
            stageOutCall['lfn-prefix'] = overrides.get('lfn-prefix')

        # naw man, this is real
        # iterate over all the incoming files
        if not useNewStageOutCode:
            # old style
            manager = StageOutMgr.StageOutMgr(**stageOutCall)
            manager.numberOfRetries = self.step.retryCount
            manager.retryPauseTime  = self.step.retryDelay
        else:
            # new style
            logging.critical("STAGEOUT IS USING NEW STAGEOUT CODE")
            print "STAGEOUT IS USING NEW STAGEOUT CODE"
            manager = WMCore.Storage.FileManager.StageOutMgr(
                                retryPauseTime  = self.step.retryDelay,
                                numberOfRetries = self.step.retryCount,
                                **stageOutCall)

        # We need to find a list of steps in our task
        # And eventually a list of jobReports for out steps

        # Search through steps for report files
        filesTransferred = []

        for step in self.stepSpace.taskSpace.stepSpaces():
            if step == self.stepName:
                #Don't try to parse your own report; it's not there yet
                continue
            stepLocation = os.path.join(self.stepSpace.taskSpace.location, step)
            logging.info("Beginning report processing for step %s" % (step))
            reportLocation = os.path.join(stepLocation, 'Report.pkl')
            if not os.path.isfile(reportLocation):
                logging.error("Cannot find report for step %s in space %s" \
                              % (step, stepLocation))
                continue
            # First, get everything from a file and 'unpersist' it
            stepReport = Report(step)
            stepReport.unpersist(reportLocation)
            taskID = getattr(stepReport.data, 'id', None)

            # Don't stage out files from bad steps.
            if not stepReport.stepSuccessful(step):
                continue

            # Okay, time to start using stuff
            # Now I'm a bit confused about this; each report should ONLY
            # Have the results of that particular step in it,
            # So getting all the files should get ONLY the files
            # for that step; or so I hope
            files = stepReport.getAllFileRefsFromStep(step = step)
            for file in files:
                if not hasattr(file, 'lfn') and hasattr(file, 'pfn'):
                    # Then we're truly hosed on this file; ignore it
                    msg = "Not a file: %s" % file
                    logging.error(msg)
                    continue
                # Support direct-to-merge
                # This requires pulling a bunch of stuff from everywhere
                # First check if it's needed
                if hasattr(self.step.output, 'minMergeSize') \
                       and hasattr(file, 'size') \
                       and not getattr(file, 'merged', False):
                    # We need both of those to continue, and we don't
                    # direct-to-merge
                    if file.size > self.step.output.minMergeSize:
                        # Then this goes direct to merge
                        try:
                            file = self.handleLFNForMerge(mergefile = file, step = step)
                        except Exception, ex:
                            logging.error("Encountered error while handling LFN for merge.\n")
                            logging.error(str(ex))
                            stepReport.addError(self.stepName, 50011,
                                                "DirectToMergeFailure", str(ex))

                # Save the input PFN in case we need it
                # Undecided whether to move file.pfn to the output PFN
                file.InputPFN   = file.pfn
                lfn = getattr(file, 'lfn')
                lfnRegEx(lfn)
                fileForTransfer = {'LFN': lfn,
                                   'PFN': getattr(file, 'pfn'),
                                   'SEName' : None,
                                   'StageOutCommand': None}
                signal.signal(signal.SIGALRM, alarmHandler)
                signal.alarm(waitTime)
                try:
                    manager(fileForTransfer)
                    #Afterwards, the file should have updated info.
                    filesTransferred.append(fileForTransfer)
                    file.StageOutCommand = fileForTransfer['StageOutCommand']
                    file.location        = fileForTransfer['SEName']
                    file.OutputPFN       = fileForTransfer['PFN']
                except Alarm:
                    msg = "Indefinite hang during stageOut of logArchive"
                    logging.error(msg)
                except Exception, ex:
                    stepReport.addError(self.stepName, 1,
                                        "StageOutFailure", str(ex))
                    stepReport.setStepStatus(self.stepName, 1)
                    stepReport.persist("Report.pkl")
                    raise

                signal.alarm(0)



            # Am DONE with report
            # Persist it
            stepReport.persist(reportLocation)



        #Done with all steps, and should have a list of
        #stagedOut files in fileForTransfer
        logging.info("Transferred %i files" %(len(filesTransferred)))
        return


    def post(self, emulator = None):
        """
        _post_

        Post execution checkpointing

        """
        #Another emulator check
        if (emulator != None):
            return emulator.emulatePost( self.step )

        for step in self.stepSpace.taskSpace.stepSpaces():

            if step == self.stepName:
                #Don't try to parse your own report; it's not there yet
                continue

            stepLocation = os.path.join(self.stepSpace.taskSpace.location, step)
            print "Beginning report processing for step %s" %step

            reportLocation = os.path.join(stepLocation, 'Report.pkl')
            if not os.path.isfile(reportLocation):
                logging.error("Cannot find report for step %s in space %s" \
                              % (step, stepLocation))
                continue

            # First, get everything from a file and 'unpersist' it
            stepReport = Report(step)
            stepReport.unpersist(reportLocation)

            # Don't stage out files from bad steps.
            if not stepReport.stepSuccessful(step):
               continue

            files = stepReport.getAllFileRefsFromStep(step = step)
            for file in files:

                if not hasattr(file, 'lfn') or not hasattr(file, 'location') or \
                       not hasattr(file, 'guid'):
                    continue

                file.user_dn = getattr(self.step, "userDN", None)
                file.async_dest = getattr(self.step, "asyncDest", None)

            stepReport.persist(reportLocation)

        print "Steps.Executors.StageOut.post called"
        return None


    # Accessory methods
    def handleLFNForMerge(self, mergefile, step):
        """
        _handleLFNForMerge_

        Digs up unmerged LFN out of WMStep outputModule and
        changes the current file to match.
        Requires a mergedLFNBase in the WMSpec output module
        """

        # First get the output module
        # Do this by finding the name in the step report
        # And then finding that module in the WMStep Helper

        outputName = getattr(mergefile, 'module_label', None)
        if not outputName:
            logging.error("Attempt to merge directly failed due to " \
                          + "No module_label in file.")
        if outputName.lower() == "merged":
            # Don't skip merge for merged files!
            return mergefile
        stepHelper = self.task.getStep(stepName = step)
        outputMod  = stepHelper.getOutputModule(moduleName = outputName)

        if not outputMod:
            # Then we couldn't get the output module
            logging.error("Attempt to directly merge failed " \
                          + "due to no output module %s in WMStep" \
                          % (outputName))
            return mergefile


        # Okay, now we should have the output Module
        # Now we just need a second LFN

        newBase = getattr(outputMod, 'mergedLFNBase', None)
        oldBase = getattr(outputMod, 'lfnBase', None)

        if not newBase:
            # Then we don't have a base to change it to
            logging.error("Direct to Merge failed due to no mergedLFNBase in %s" \
                          % (outputName))
            return mergefile

        # Replace the actual LFN base
        oldLFN = getattr(mergefile, 'lfn')
        newLFN = oldLFN.replace(oldBase, newBase)

        # Set the file attributes
        setattr(mergefile, 'lfn', newLFN)
        setattr(mergefile, 'merged', True)

        # Return the file
        return mergefile
