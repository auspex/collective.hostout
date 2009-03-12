##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import logging, os, shutil, tempfile, urllib2, urlparse
import setuptools.archive_util
import datetime
import sha
import shutil
import zc.buildout
from os.path import join
import os

def system(c):
    if os.system(c):
        raise SystemError("Failed", c)

class Recipe:

    def __init__(self, buildout, name, options):
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)
        self.name, self.options = name, options
        directory = buildout['buildout']['directory']
        self.download_cache = buildout['buildout'].get('download-cache')
        self.install_from_cache = buildout['buildout'].get('install-from-cache')
        self.buildout = buildout

        if self.download_cache:
            # cache keys are hashes of url, to ensure repeatability if the
            # downloads do not have a version number in the filename
            # cache key is a directory which contains the downloaded file
            # download details stored with each key as cache.ini
            self.download_cache = os.path.join(
                directory, self.download_cache, 'cmmi')

        # we assume that install_from_cache and download_cache values
        # are correctly set, and that the download_cache directory has
        # been created: this is done by the main zc.buildout anyway

        options['location'] = os.path.join(
            buildout['buildout']['parts-directory'],
            self.name,
            )
        options['bin-directory'] = buildout['buildout']['bin-directory']
        self.dist_dir = options['dist_dir'] = dist_dir = self.options.get('dist_dir','dist')
        self.buildout_dir = self.buildout.get('buildout').get('directory')
        self.buildout_cfg = options['buildout'] = options.get('buildout','buildout.cfg')
        self.password = options.get('password','') 
        self.start_cmd = options.get('start_cmd',None)
        self.stop_cmd = options.get('stop_cmd', None)

    def install(self):
        logger = logging.getLogger(self.name)
        user = self.options.get('user','')
        identityfile = self.options.get('identityfile','')
        effectiveuser = self.options.get('effective-user','plone')
        self.remote_dir = self.options.get('remote_path','~%s/buildout'%user)
        host = self.options['host']
        #import pdb; pdb.set_trace()
        
        requirements, ws = self.egg.working_set()
        options = self.options
        location = options['location']
        from os.path import dirname, abspath
        if not os.path.exists(location):
            os.mkdir(location)
        #fabfile = template % (self.name, [host], base)
        #fname = join(location,'fabfile.py')
        #open(fname, 'w+').write(fabfile)
        extra_paths=[]
        self.develop = [p.strip() for p in self.buildout.get('buildout').get('develop').split()]
        packages = self.develop + self.options.get('packages','').split()
        #for package in self.options['buildout']['develop']:
        #    extra_paths+=[package]
        #extra_paths.append(os.path.join('c:\\python25'))
        #options['executable'] = 'c:\\Python25\\python.exe'
        config_file = self.buildout_cfg

#        buildoutroot = os.getcwd()
        
        hostout = self.genhostout()
        
        args = 'effectiveuser="%s",\
        remote_dir=r"%s",\
        dist_dir=r"%s",\
        packages=%s,\
        buildout_location="%s",\
        host="%s",\
        user=r"%s",\
        password=r"%s",\
        identityfile="%s",\
        config_file="%s",\
        start_cmd="%s",\
        stop_cmd="%s"'%\
                (
                 effectiveuser,
                 self.remote_dir,
                 self.dist_dir, 
                 str(packages), 
                 self.buildout_dir,
                 host,
                 user,
                 self.password,
                 identityfile, 
                 hostout,
                 self.start_cmd,
                 self.stop_cmd
                 )
                
        
        zc.buildout.easy_install.scripts(
                [(self.name, 'collective.recipe.hostout.hostout', 'main')],
                ws, options['executable'], options['bin-directory'],
                arguments=args,
                extra_paths=extra_paths
#                initialization=address_info,
#                arguments='host, port, socket_path', extra_paths=extra_paths
                )


        # now unpack and work as normal
        tmp = tempfile.mkdtemp('buildout-'+self.name)
#        logger.info('Unpacking and configuring')
#        setuptools.archive_util.unpack_archive(fname, tmp)

#        here = os.getcwd()
#        if not os.path.exists(dest):
#            os.mkdir(dest)


        return location

    def update(self):
        return self.install()


    def genhostout(self):
        """ generate a new buildout file which pins versions and uses our deployment distributions"""

    
        base = self.buildout_dir
        dist_dir = os.path.abspath(os.path.join(self.buildout_dir,self.dist_dir))
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)
        
        buildoutfile = relpath(self.buildout_cfg, base)
        dist_dir = relpath(self.dist_dir, base)
        #versions = self.getversions()
        versions = ""
        install_base = os.path.dirname(self.remote_dir)
        buildout_cache = os.path.join(install_base,'buildout-cache')
        hostout = HOSTOUT_TEMPLATE % dict(buildoutfile=buildoutfile,
                                          eggdir=dist_dir,
                                          versions=versions,
                                          buildout_cache=buildout_cache)
        path = os.path.join(base,'hostout.cfg')     
        hostoutf = open(path,'w')
        hostoutf.write(hostout)
        hostoutf.close()
        return path

    def getversions(self):
        versions = {}
        for part in self.buildout:
            options = self.buildout[part]
            if not options.get('recipe'):
                continue
            try:
                recipe,subrecipe = options['recipe'].split(':')
            except:
                recipe=options['recipe']
            try:
                egg = zc.recipe.egg.Egg(self.buildout, recipe, options)
                requirements, ws = egg.working_set()
            except:
                continue
            for dist in ws.by_key.values():
                project_name =  dist.project_name
                version = dist.version
                
                versions[project_name] =version
        spec = ""
        for project_name,version in versions.items():
            if version != '0.0':
                spec+='%s = %s' % (project_name,version)+'\n'
            else:
                spec+='#%s = %s' % (project_name,version)+'\n'
        return spec
                        
        

HOSTOUT_TEMPLATE = """
[buildout]
extends=%(buildoutfile)s

#Our own packaged eggs
find-links+=%(eggdir)s

#prevent us looking for them as developer eggs
develop=

#Match to unifiedinstaller
eggs-directory=%(buildout_cache)s/eggs
download-cache=%(buildout_cache)s/downloads

versions=versions
#non-newest set because we know exact versions we want
#newest=false
[versions]
%(versions)s
"""



    


template = """
set(
        project = '%s',
        fab_hosts = %s,
)
load(r'%s')
"""    


# relpath.py
# R.Barran 30/08/2004

import os

def relpath(target, base=os.curdir):
    """
    Return a relative path to the target from either the current dir or an optional base dir.
    Base can be a directory specified either as absolute or relative to current dir.
    """

    if not os.path.exists(target):
        raise OSError, 'Target does not exist: '+target

    if not os.path.isdir(base):
        raise OSError, 'Base is not a directory or does not exist: '+base

    base_list = (os.path.abspath(base)).split(os.sep)
    target_list = (os.path.abspath(target)).split(os.sep)

    # On the windows platform the target may be on a completely different drive from the base.
    if os.name in ['nt','dos','os2'] and base_list[0] <> target_list[0]:
        raise OSError, 'Target is on a different drive to base. Target: '+target_list[0].upper()+', base: '+base_list[0].upper()

    # Starting from the filepath root, work out how much of the filepath is
    # shared by base and target.
    for i in range(min(len(base_list), len(target_list))):
        if base_list[i] <> target_list[i]: break
    else:
        # If we broke out of the loop, i is pointing to the first differing path elements.
        # If we didn't break out of the loop, i is pointing to identical path elements.
        # Increment i so that in all cases it points to the first differing path elements.
        i+=1

    rel_list = [os.pardir] * (len(base_list)-i) + target_list[i:]
    return os.path.join(*rel_list)

    