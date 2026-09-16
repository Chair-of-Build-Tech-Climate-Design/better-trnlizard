"""Grasshopper Python 3 Component - TRNLizard Multi-Surface Updater"""
import System
import Rhino
import Grasshopper

import os
import hashlib
import re

class LizardUpdaterComponent(Grasshopper.Kernel.GH_ScriptInstance):
    
    def RunScript(self, sourceFolder, runUpdate):
        # Initialize outputs
        log = []
        updated = []
        skipped = []
        errors = []
        
        # Early validation
        if not runUpdate:
            log.append("Set runUpdate to True to execute the updater.")
            return log, updated, skipped, errors
            
        if not sourceFolder or not os.path.isdir(sourceFolder):
            errors.append("Invalid source folder path.")
            return log, updated, skipped, errors
        
        log.append("=== TRNLizard Updater Started ===")
        log.append("Source folder: {}".format(sourceFolder))
        
        # Get current GH document
        doc = ghenv.Component.OnPingDocument()
        if not doc:
            errors.append("Could not access the current Grasshopper document.")
            return log, updated, skipped, errors
        
        # Find all Python scripts in source folder
        pyFiles = self._findPythonScripts(sourceFolder, log)
        if not pyFiles:
            log.append("No Python files found in source folder.")
            return log, updated, skipped, errors
        
        # Build lookup of script names to file paths
        scriptLookup = {}
        for fpath in pyFiles:
            baseName = os.path.splitext(os.path.basename(fpath))[0]
            scriptLookup[baseName] = fpath
        
        log.append("Found {} Python files in source.".format(len(pyFiles)))
        
        # Collect all GHPython components in document
        components = self._collectGHPythonComponents(doc, log)
        log.append("Found {} GHPython components in document.".format(len(components)))
        
        # Process each component
        for comp in components:
            try:
                compName = str(comp.Name)
                
                # Check if component name matches a script file
                if compName not in scriptLookup:
                    continue
                
                scriptPath = scriptLookup[compName]
                log.append("\n--- Processing: {} ---".format(compName))
                log.append("Source: {}".format(scriptPath))
                
                # Read source script content (remove BOM if present)
                with open(scriptPath, 'r', encoding='utf-8-sig') as f:
                    newCode = f.read()
                
                # Check if component has Code property
                if not hasattr(comp, 'Code'):
                    msg = "Component {} does not have a Code property (may not be a script component).".format(compName)
                    log.append(msg)
                    skipped.append(compName)
                    continue
                
                currentCode = comp.Code
                
                # Compare hashes
                currentHash = self._getHash(currentCode)
                newHash = self._getHash(newCode)
                
                log.append("Current hash: {}".format(currentHash[:12]))
                log.append("New hash:     {}".format(newHash[:12]))
                
                if currentHash == newHash:
                    msg = "Component {} is already up to date.".format(compName)
                    log.append(msg)
                    skipped.append(compName)
                    continue
                
                # Diagnostic: show first differing line (normalized view)
                diffHint = self._firstDiff(currentCode, newCode)
                if diffHint:
                    log.append("First diff: {}".format(diffHint))
                
                # Check if IronPython or CPython component
                isIronPython = self._isIronPythonComponent(comp)
                log.append("Component type: {}".format("IronPython" if isIronPython else "CPython"))
                
                # Analyze inputs/outputs before update
                currentInputs, currentOutputs = self._analyzeIO(comp)
                log.append("Current inputs:  {}".format(currentInputs))
                log.append("Current outputs: {}".format(currentOutputs))
                
                # Parse new script IO from normalized docstring
                newInputs, newOutputs = self._parseIOFromScript(newCode)
                log.append("New script inputs:  {}".format(newInputs))
                log.append("New script outputs: {}".format(newOutputs))
                
                # Compare IO (order-sensitive); code is updated either way,
                # but IO mismatch is flagged prominently for manual review
                ioChanged = (currentInputs != newInputs) or (currentOutputs != newOutputs)
                comp.Code = newCode
                self._expireComponent(comp, doc)
                if ioChanged:
                    msg = "Updated component: {} [IO CHANGED - review params manually!]".format(compName)
                    warning = "IO CHANGED for {}: in {}->{} / out {}->{}".format(
                        compName, currentInputs, newInputs, currentOutputs, newOutputs)
                    log.append("WARNING: " + warning)
                    errors.append(warning)
                else:
                    msg = "Updated component: {}".format(compName)
                log.append(msg)
                updated.append(compName)
                    
            except Exception as e:
                errorMsg = "Error processing {}: {}".format(comp.Name, str(e))
                log.append(errorMsg)
                errors.append(errorMsg)
        
        log.append("\n=== Update Summary ===")
        log.append("Updated: {}".format(len(updated)))
        log.append("Skipped: {}".format(len(skipped)))
        log.append("Errors:  {}".format(len(errors)))
        
        return log, updated, skipped, errors
    
    def _findPythonScripts(self, folder, log):
        """Find all .py files in folder (non-recursive for safety)."""
        pyFiles = []
        try:
            for fname in os.listdir(folder):
                if fname.endswith('.py') and not fname.startswith('_'):
                    fpath = os.path.join(folder, fname)
                    if os.path.isfile(fpath):
                        pyFiles.append(fpath)
        except Exception as e:
            log.append("Error scanning folder: {}".format(str(e)))
        return pyFiles
    
    def _collectGHPythonComponents(self, doc, log):
        """Collect all GHPython script components from document."""
        components = []
        try:
            # Check clusters first
            for obj in doc.Objects:
                if type(obj) == Grasshopper.Kernel.Special.GH_Cluster:
                    try:
                        clusterDoc = obj.Document("")
                        if clusterDoc:
                            for clusterObj in clusterDoc.Objects:
                                if self._isPythonComponent(clusterObj):
                                    components.append(clusterObj)
                    except:
                        pass
                elif self._isPythonComponent(obj):
                    # Exclude self
                    if obj.InstanceGuid != ghenv.Component.InstanceGuid:
                        components.append(obj)
        except Exception as e:
            log.append("Error collecting components: {}".format(str(e)))
        return components
    
    def _isPythonComponent(self, obj):
        """Check if object is a GHPython script component."""
        # Check for GH_Component type with Code property
        if not isinstance(obj, Grasshopper.Kernel.GH_Component):
            return False
        # Check if it has a Code attribute (script components do)
        return hasattr(obj, 'Code')
    
    def _isIronPythonComponent(self, comp):
        """Detect if component is IronPython (Rhino 7 style) vs CPython (Rhino 8)."""
        try:
            # IronPython components typically have a Script property
            # CPython components have different structure
            typeName = str(type(comp))
            if 'IronPython' in typeName or 'Python3' in typeName:
                return True
            # Alternative check: look for Script property
            return hasattr(comp, 'Script')
        except:
            return False
    
    def _analyzeIO(self, comp):
        """Extract current inputs and outputs from component (order preserved)."""
        inputs = []
        outputs = []
        try:
            for param in comp.Params.Input:
                inputs.append(str(param.Name))
            for param in comp.Params.Output:
                outputs.append(str(param.Name))
        except:
            pass
        return inputs, outputs
    
    def _parseIOFromScript(self, code):
        """Parse inputs/outputs from normalized docstring Args/Returns section.
        
        Expected format:
            Args:
                Name (type): description
                    Access: item|list|tree
                    Required: True|False
                --------------------- Separator
            Returns:
                out (type): description
                    Access: item
        Returns (inputs, outputs) as lists of param names, including separators.
        """
        # Extract docstring
        docMatch = re.search(r'"""(.*?)"""', code, re.DOTALL)
        if not docMatch:
            return [], []
        docstring = docMatch.group(1)
        
        # Param line: 4-space indent, "Name (type): desc" or bare separator
        inputs = []
        outputs = []
        section = None
        for line in docstring.split('\n'):
            if line.strip() == 'Args:':
                section = 'in'
                continue
            if line.strip() == 'Returns:':
                section = 'out'
                continue
            if section and re.match(r'^    \S', line):  # exactly 4-space indent
                m = re.match(r'^    ([^(:]+?)(?:\s*\([^)]*\))?\s*:\s', line)
                if m:  # param with description
                    name = m.group(1).strip()
                else:  # separator line (no colon)
                    name = line.strip()
                if section == 'in':
                    inputs.append(name)
                else:
                    outputs.append(name)
        return inputs, outputs
    
    def _firstDiff(self, a, b):
        """Return a short hint about the first differing line between two code strings."""
        aLines = a.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        bLines = b.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        for i in range(max(len(aLines), len(bLines))):
            la = aLines[i] if i < len(aLines) else '<missing>'
            lb = bLines[i] if i < len(bLines) else '<missing>'
            if la != lb:
                return "line {}: comp={!r} vs file={!r}".format(i + 1, la[:60], lb[:60])
        return None
    
    def _getHash(self, content):
        """Compute SHA256 hash of content, normalizing line endings and BOM.
        
        Grasshopper normalizes code line endings (\\r\\n) when saving/loading
        .ghx files, so raw comparison would always mismatch after reopen.
        """
        if not content:
            content = ""
        # normalize: strip BOM, unify line endings to \n, trim trailing newline
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        normalized = normalized.lstrip('﻿').rstrip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def _expireComponent(self, comp, doc):
        """Expire component to trigger recompute."""
        def callback(document):
            comp.ExpireSolution(False)
        doc.ScheduleSolution(1, Grasshopper.Kernel.GH_Document.GH_ScheduleDelegate(callback))
