##############################################################################
# Copyright by The HDF Group.                                                #
# All rights reserved.                                                       #
#                                                                            #
# This file is part of H5Serv (HDF5 REST Server) Service, Libraries and      #
# Utilities.  The full HDF5 REST Server copyright notice, including          #
# terms governing use, modification, and redistribution, is contained in     #
# the file COPYING, which can be found at the root of the source code        #
# distribution tree.  If you do not have access to this file, you may        #
# request a copy from help@hdfgroup.org.                                     #
##############################################################################
import sys
import json
import argparse
import os.path as op
import os
import tempfile

import logging
import logging.handlers

from hdf5db import Hdf5db
import hdf5dtype 


"""
DumpJson - return json representation of all objects within the given file
"""

class DumpJson:
    def __init__(self, db, app_logger=None, options=None):
        self.options = options
        self.db = db
        if app_logger:
            self.log = app_logger
        else:
            # print "default logger"
            self.log = logging.getLogger()
        self.json = {}
        
    def dumpAttribute(self, col_name, uuid, attr_name):
        self.log.info("dumpAttribute: [" + attr_name + "]")
        item = self.db.getAttributeItem(col_name, uuid, attr_name)
        response = { 'name': attr_name }
        typeItem = item['type']
        response['type'] = hdf5dtype.getTypeResponse(typeItem)
        response['shape'] = item['shape']
        if not self.options.D:
            if 'value' not in item:
                self.log.warning("no value key in attribute: " + attr_name)
            else:
                response['value'] = item['value']   # dump values unless header -D was passed
        return response
     
        
    def dumpAttributes(self, col_name, uuid):
        attr_list = self.db.getAttributeItems(col_name, uuid)
        self.log.info("dumpAttributes: " + uuid)
        items = []
        for attr in attr_list:
            item = self.dumpAttribute(col_name, uuid, attr['name'])
            items.append(item)
                   
        return items    
        
    def dumpLink(self, uuid, name):
        item = self.db.getLinkItemByUuid(uuid, name)
        for key in ('ctime', 'mtime', 'href'):
            if key in item:
                del item[key]
        return item
        
    
    def dumpLinks(self, uuid):
        link_list = self.db.getLinkItems(uuid)
        items = []
        for link in link_list:
            item = self.dumpLink(uuid, link['title'])
            items.append(item)
        return items
       
        
    def dumpGroup(self, uuid):
        item = self.db.getGroupItemByUuid(uuid)
        if 'alias' in item:
            alias = item['alias']
            if alias:
                self.log.info("dumpGroup alias: [" + alias[0] + "]")
        for key in ('ctime', 'mtime', 'linkCount', 'attributeCount', 'id'):
            if key in item:
                del item[key]
        attributes = self.dumpAttributes('groups', uuid)
        if attributes:
            item['attributes'] = attributes
        links = self.dumpLinks(uuid)
        if links:
            item['links'] = links
        return item
        
        
    def dumpGroups(self):
        groups = {}
        item = self.dumpGroup(self.root_uuid)
        groups[self.root_uuid] = item
        uuids = self.db.getCollection("groups") 
        for uuid in uuids:
            item = self.dumpGroup(uuid)
            groups[uuid] = item
        
        self.json['groups'] = groups
        
        
    def dumpDataset(self, uuid):
        response = { }
        self.log.info("dumpDataset: " + uuid)
        item = self.db.getDatasetItemByUuid(uuid)
        if 'alias' in item:
            alias = item['alias']
            if alias:
                self.log.info("dumpDataset alias: [" + alias[0] + "]")
            response['alias'] = item['alias']
        
        typeItem = item['type']
        response['type'] = hdf5dtype.getTypeResponse(typeItem)
        shapeItem = item['shape']
        shape_rsp = {}
        num_elements = 1
        shape_rsp['class'] = shapeItem['class']
        if 'dims' in shapeItem:
            shape_rsp['dims'] = shapeItem['dims']
            for dim in shapeItem['dims']:
                num_elements *= dim
        if 'maxdims' in shapeItem:
            maxdims = []
            for dim in shapeItem['maxdims']:
                if dim == 0:
                    maxdims.append('H5S_UNLIMITED')
                else:
                    maxdims.append(dim)
            shape_rsp['maxdims'] = maxdims
        response['shape'] = shape_rsp
       
        if 'creationProperties' in item:
            response['creationProperties'] = item['creationProperties']
            
        attributes = self.dumpAttributes('datasets', uuid)
        if attributes:
            response['attributes'] = attributes
        
        
        if not (self.options.D or self.options.d):
            if num_elements > 0:
                value = self.db.getDatasetValuesByUuid(uuid)
                response['value'] = value   # dump values unless header flag was passed
            else:
                response['value'] = []  # empty list
        return response
        
    def dumpDatasets(self):
        uuids = self.db.getCollection("datasets") 
        if uuids:
            datasets = {}
            for uuid in uuids:
                item = self.dumpDataset(uuid)
                datasets[uuid] = item
        
            self.json['datasets'] = datasets
        
    def dumpDatatype(self, uuid):
        response = { }
        item = self.db.getCommittedTypeItemByUuid(uuid)
        response['alias'] = item['alias']
        typeItem = item['type']
        response['type'] = hdf5dtype.getTypeResponse(typeItem)
        attributes = self.dumpAttributes('datatypes', uuid)
        if attributes:
            response['attributes'] = attributes
        return response
         
        
    def dumpDatatypes(self):    
        uuids = self.db.getCollection("datatypes") 
        if uuids:
            datatypes = {}
            for uuid in uuids:
                item = self.dumpDatatype(uuid)
                datatypes[uuid] = item
        
            self.json['datatypes'] = datatypes
        
    def dumpFile(self):
        
        self.root_uuid = self.db.getUUIDByPath('/')
        
        db_version_info = self.db.getVersionInfo()
          
        self.json['apiVersion'] = db_version_info['hdf5-json-version']
        self.json['root'] = self.root_uuid
        
        self.dumpGroups()
        
        self.dumpDatasets()
            
        self.dumpDatatypes()
            
        # print json.dumps(self.json, sort_keys=True, indent=4)

"""
  Generate a temporary filename to avoid problems with trying to create a dbfile
  in a read-only directory.  (See: https://github.com/HDFGroup/h5serv/issues/37)
"""        
def getTempFileName():
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    return f.name

if __name__ == "__main__":
    # Create logger.
    # logging.basicConfig()
    log = logging.getLogger("h5serv")
    log.addHandler(logging.NullHandler())
    
    args = argparse.Namespace()
    args.d = True
    args.D = False

    filename = sys.argv[1]
    # Create temp file.
    f = tempfile.NamedTemporaryFile(delete=False)
    f.close()
    dbFilename = f.name
    print dbFilename
    with Hdf5db(filename, dbFilePath=dbFilename, readonly=True,
                app_logger=log) as db:
        dumper = DumpJson(db, app_logger=log, options=args)
        dumper.dumpFile()
    with open(filename+'.json', "w") as text_file:
        text_file.write(json.dumps(dumper.json))

    
	
