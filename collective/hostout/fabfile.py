import os
import os.path
from fabric import api
from fabric.contrib.files import append
from collective.hostout.hostout import buildoutuser
from fabric.context_managers import cd
from pkg_resources import resource_filename


def bootstrap():
    hostos = api.env.get('hostos')
    users = getattr(api.env.hostout, 'bootstrap_users_%s'%hostos, None)
    if users is not None:
        users()
    else:
        api.env.hostout.bootstrap_users()

    cmd = getattr(api.env.hostout, 'bootstrap_python_%s'%hostos, None)
    if users is not None:
        cmd()
    else:
        api.env.hostout.bootstrap_python()

    try:
        api.sudo("test -e  %(path)s/bin/buildout " % dict(path=api.env.path), pty=True)
        return
    except:
        pass

    api.env.hostout.bootstrap_buildout()


def bootstrap_users():
    """ create users if needed """

    hostout = api.env.get('hostout')
    buildout = api.env['buildout-user']
    effective = api.env['effective-user']
    buildoutgroup = api.env['buildout-group']
    owner = buildout
    
    api.sudo('groupadd %s || echo "group exists"' % buildoutgroup)
    addopt = "--no-user-group -M -g %s" % buildoutgroup
    api.sudo('egrep ^%(owner)s: /etc/passwd || useradd %(owner)s %(addopt)s' % dict(owner=owner, addopt=addopt))
    api.sudo('egrep ^%(effective)s: /etc/passwd || useradd %(effective)s %(addopt)s' % dict(effective=effective, addopt=addopt))
    api.sudo('gpasswd -a %(owner)s %(buildoutgroup)s' % dict(owner=owner, buildoutgroup=buildoutgroup))
    api.sudo('gpasswd -a %(effective)s %(buildoutgroup)s' % dict(effective=effective, buildoutgroup=buildoutgroup))

    #Copy authorized keys to buildout user:
    key_filename, key = api.env.hostout.getIdentityKey()
    for owner in [api.env['buildout-user']]:
        api.sudo("mkdir -p ~%s/.ssh" % owner)
        api.sudo('touch ~%s/.ssh/authorized_keys' % owner)
        append(key, '~%s/.ssh/authorized_keys' % owner, use_sudo=True)
        api.sudo("chown -R %(owner)s ~%(owner)s/.ssh" % locals() )



def bootstrap_python():
    "Install python from source"
    
    path = api.env.path

    BUILDOUT = """
[buildout]
extends =
      src/base.cfg
      src/readline.cfg
      src/libjpeg.cfg
      src/python%(majorshort)s.cfg
      src/links.cfg

parts =
      ${buildout:base-parts}
      ${buildout:readline-parts}
      ${buildout:libjpeg-parts}
      ${buildout:python%(majorshort)s-parts}
      ${buildout:links-parts}

# ucs4 is needed as lots of eggs like lxml are also compiled with ucs4 since most linux distros compile with this      
[python-%(major)s-build:default]
extra_options +=
    --enable-unicode=ucs4
      
"""


    
    hostout = api.env.hostout
    hostout = api.env.get('hostout')
    buildout = api.env['buildout-user']
    effective = api.env['effective-user']
    buildoutgroup = api.env['buildout-group']

    #hostout.setupusers()
    api.sudo('mkdir -p %(path)s' % locals())
    hostout.setowners()

    version = api.env['python-version']
    major = '.'.join(version.split('.')[:2])
    majorshort = major.replace('.','')
    api.sudo('mkdir -p /var/buildout-python')
    with cd('/var/buildout-python'):
        #api.sudo('wget http://www.python.org/ftp/python/%(major)s/Python-%(major)s.tgz'%locals())
        #api.sudo('tar xfz Python-%(major)s.tgz;cd Python-%(major)s;./configure;make;make install'%locals())

        api.sudo('svn co http://svn.plone.org/svn/collective/buildout/python/')
        with cd('python'):
            api.sudo('curl -O http://python-distribute.org/distribute_setup.py')
            api.sudo('python distribute_setup.py')
            api.sudo('python bootstrap.py --distribute')
            append(BUILDOUT%locals(), 'buildout.cfg', use_sudo=True)
            api.sudo('bin/buildout')
    api.env['python'] = "source /var/buildout-python/python/python-%(major)s/bin/activate; python "
        
    #api.env.cwd = api.env.path
    #api.sudo('wget -O bootstrap.py http://python-distribute.org/bootstrap.py')
    #api.sudo('echo "[buildout]" > buildout.cfg')
    #api.sudo('source /var/buildout-python/python/python-%(major)s/bin/activate; python bootstrap.py --distribute' % locals())
    #api.sudo('chown -R %(buildout)s:%(buildoutgroup)s /var/buildout-python '%locals())

    #ensure bootstrap files have correct owners
    hostout.setowners()

def bootstrap_python_ubuntu():
    """Update ubuntu with build tools, python and bootstrap buildout"""
    hostout = api.env.get('hostout')
    path = api.env.path
 
    # Add the plone user:
    hostout.setupusers()
    api.sudo('mkdir -p %(path)s' % locals())
    hostout.setowners()

    #http://wiki.linuxquestions.org/wiki/Find_out_which_linux_distribution_a_system_belongs_to
    d = api.run(
    #    "[ -e /etc/SuSE-release ] && echo SuSE "
    #            "[ -e /etc/redhat-release ] && echo redhat"
    #            "[ -e /etc/fedora-release ] && echo fedora || "
                "lsb_release -rd "
    #            "[ -e /etc/debian-version ] && echo debian or ubuntu || "
    #            "[ -e /etc/slackware-version ] && echo slackware"
               )
    print d
    api.run('uname -r')

#    api.sudo('apt-get -y update')
#    api.sudo('apt-get -y upgrade ')
    
    
    version = api.env['python-version']
    major = '.'.join(version.split('.')[:2])
    
    #Install and Update Dependencies

    #contrib.files.append(apt_source, '/etc/apt/source.list', use_sudo=True)
    api.sudo('apt-get -yq install '
             'build-essential '
#             'python%(major)s python%(major)s-dev '
#             'python-libxml2 '
#             'python-elementtree '
#             'python-celementtree '
             'ncurses-dev '
             'libncurses5-dev '
# needed for lxml on lucid
             'libz-dev '
             'libdb4.6 '
             'libxp-dev '
             'libreadline5 '
             'libreadline5-dev '
             'libbz2-dev '
             % locals())

    try:
        api.sudo('apt-get -yq install python%(major)s python%(major)s-dev '%locals())
        #install buildout
        api.env.cwd = api.env.path
        api.sudo('wget -O bootstrap.py http://python-distribute.org/bootstrap.py')
        api.sudo('echo "[buildout]" > buildout.cfg')
        api.sudo('python%(major)s bootstrap.py' % locals())
    except:
        hostout.bootstrapsource()

    #api.sudo('apt-get -yq update; apt-get dist-upgrade')

#    api.sudo('apt-get install python2.4=2.4.6-1ubuntu3.2.9.10.1 python2.4-dbg=2.4.6-1ubuntu3.2.9.10.1 \
# python2.4-dev=2.4.6-1ubuntu3.2.9.10.1 python2.4-doc=2.4.6-1ubuntu3.2.9.10.1 \
# python2.4-minimal=2.4.6-1ubuntu3.2.9.10.1')
    #wget http://mirror.aarnet.edu.au/pub/ubuntu/archive/pool/main/p/python2.4/python2.4-minimal_2.4.6-1ubuntu3.2.9.10.1_i386.deb -O python2.4-minimal.deb
    #wget http://mirror.aarnet.edu.au/pub/ubuntu/archive/pool/main/p/python2.4/python2.4_2.4.6-1ubuntu3.2.9.10.1_i386.deb -O python2.4.deb
    #wget http://mirror.aarnet.edu.au/pub/ubuntu/archive/pool/main/p/python2.4/python2.4-dev_2.4.6-1ubuntu3.2.9.10.1_i386.deb -O python2.4-dev.deb
    #sudo dpkg -i python2.4-minimal.deb python2.4.deb python2.4-dev.deb
    #rm python2.4-minimal.deb python2.4.deb python2.4-dev.deb

    # python-profiler?
    

    #ensure bootstrap files have correct owners
    hostout.setowners()

    

def bootstrap_buildout():
    """ Create an initialised buildout directory """
    # bootstrap assumes that correct python is already installed
    path = api.env.path
    buildout = api.env['buildout-user']
    buildoutgroup = api.env['buildout-group']
    api.sudo('mkdir -p %(path)s' % locals())
    api.sudo('chown -R %(buildout)s:%(buildoutgroup)s %(path)s'%locals())

    buildoutcache = api.env['buildout-cache']
    api.sudo('mkdir -p %s/eggs' % buildoutcache)
    api.sudo('mkdir -p %s/downloads/dist' % buildoutcache)
    api.sudo('mkdir -p %s/extends' % buildoutcache)
    api.sudo('chown -R %s:%s %s' % (buildout, buildoutgroup, buildoutcache))
    api.env.cwd = api.env.path
   
    bootstrap = resource_filename(__name__, 'bootstrap.py')
    api.put(bootstrap, '%s/bootstrap.py' % path)
    
    # put in simplest buildout to get bootstrap to run
    api.sudo('echo "[buildout]" > buildout.cfg')

    python = api.env.get('python')
    if not python:
        
        version = api.env['python-version']
        major = '.'.join(version.split('.')[:2])
        python = "python%s" % major

    api.sudo('%s bootstrap.py --distribute' % python)


def setowners():
    """ Ensure ownership and permissions are correct on buildout and cache """
    hostout = api.env.get('hostout')
    buildout = api.env['buildout-user']
    effective = api.env['effective-user']
    buildoutgroup = api.env['buildout-group']
    owner = buildout


    path = api.env.path
    bc = hostout.buildout_cache
    dl = hostout.getDownloadCache()
    dist = os.path.join(dl, 'dist')
    bc = hostout.getEggCache()
    var = os.path.join(path, 'var')
    
    # What we want is for
    # - login user to own the buildout and the cache.
    # - effective user to be own the var dir + able to read buildout and cache.
    
    api.sudo("find %(path)s  -maxdepth 0 ! -name var -exec chown -R %(buildout)s:%(buildoutgroup)s '{}' \; "
             " -exec chmod -R u+rw,g+r-w,o-rw '{}' \;" % locals())
    api.sudo('mkdir -p %(var)s && chown -R %(effective)s:%(buildoutgroup)s %(var)s && '
             ' chmod -R u+rw,g+wrs,o-rw %(var)s ' % locals())
#    api.sudo("chmod g+x `find %(path)s -perm -g-x` || find %(path)s -perm -g-x -exec chmod g+x '{}' \;" % locals()) #so effective can execute code
#    api.sudo("chmod g+s `find %(path)s -type d` || find %(path)s -type d -exec chmod g+s '{}' \;" % locals()) # so new files will keep same group
#    api.sudo("chmod g+s `find %(path)s -type d` || find %(path)s -type d -exec chmod g+s '{}' \;" % locals()) # so new files will keep same group
    
    for cache in [bc, dl, bc]:
        #HACK Have to deal with a shared cache. maybe need some kind of group
        api.sudo('mkdir -p %(cache)s && chown -R %(buildout)s:%(buildoutgroup)s %(cache)s && '
                 ' chmod -R u+rw,a+r %(cache)s ' % locals())


#def initcommand(cmd):
#    if cmd in ['uploadeggs','uploadbuildout','buildout','run']:
#        api.env.user = api.env.hostout.options['buildout-user']
#    else:
#        api.env.user = api.env.hostout.options['user']
#    key_filename = api.env.get('identity-file')
#    if key_filename and os.path.exists(key_filename):
#        api.env.key_filename = key_filename

def deploy():
    "predeploy, uploadeggs, uploadbuildout, buildout and then postdeploy"
    hostout = api.env['hostout']
    hostout.predeploy()
    hostout.uploadeggs()
    hostout.uploadbuildout()
    hostout.buildout()
    hostout.postdeploy()

def predeploy():
    """Perform any initial plugin tasks. Call bootstrap if needed"""
    hostout = api.env['hostout']

    #run('export http_proxy=localhost:8123') # TODO get this from setting

    path = api.env.path
    api.env.cwd = ''

    #if not contrib.files.exists(hostout.options['path'], use_sudo=True):
    try:
        api.sudo("ls  %(path)s/bin/buildout " % locals(), pty=True)
    except:
        hostout.bootstrap()
        hostout.setowners()

    api.env.cwd = api.env.path
    for cmd in hostout.getPreCommands():
        api.sudo('sh -c "%s"'%cmd)
    api.env.cwd = ''




@buildoutuser
def uploadeggs():
    """Release developer eggs and send to host """
    
    hostout = api.env['hostout']

    #need to send package. cycledown servers, install it, run buildout, cycle up servers

    dl = hostout.getDownloadCache()
    contents = api.run('ls %s/dist' % dl).split()

    for pkg in hostout.localEggs():
        name = os.path.basename(pkg)
        if name not in contents:
            tmp = os.path.join('/tmp', name)
            api.put(pkg, tmp)
            api.run("mv -f %(tmp)s %(tgt)s && "
                "chown %(buildout)s %(tgt)s && "
                "chmod a+r %(tgt)s" % dict(
                    tmp = tmp,
                    tgt = os.path.join(dl, 'dist', name),
                    buildout=api.env.hostout.options['buildout-user'],
                    ))

@buildoutuser
def uploadbuildout():
    """Upload buildout pinned version of buildouts to host """
    hostout = api.env.hostout
    buildout = api.env['buildout-user']

    package = hostout.getHostoutPackage()
    tmp = os.path.join('/tmp', os.path.basename(package))
    tgt = os.path.join(hostout.getDownloadCache(), 'dist', os.path.basename(package))

    #api.env.warn_only = True
    if api.run("test -f %(tgt)s || echo 'None'" %locals()) == 'None' :
        api.put(package, tmp)
        api.run("mv %(tmp)s %(tgt)s" % locals() )
        #sudo('chown $(effectiveuser) %s' % tgt)


    user=hostout.options['buildout-user']
    install_dir=hostout.options['path']
    with cd(install_dir):
        api.run('tar -p -xvf %(tgt)s' % locals())
#    hostout.setowners()

@buildoutuser
def buildout():
    """ Run the buildout on the remote server """

    hostout = api.env.hostout
    hostout_file=hostout.getHostoutFile()
    #api.env.user = api.env['effective-user']
    api.env.cwd = hostout.remote_dir
    api.run('bin/buildout -c %(hostout_file)s' % locals())
    #api.sudo('sudo -u $(effectiveuser) sh -c "export HOME=~$(effectiveuser) && cd $(install_dir) && bin/buildout -c $(hostout_file)"')

#    sudo('chmod 600 .installed.cfg')
#    sudo('find $(install_dir)  -type d -name var -exec chown -R $(effectiveuser) \{\} \;')
#    sudo('find $(install_dir)  -type d -name LC_MESSAGES -exec chown -R $(effectiveuser) \{\} \;')
#    sudo('find $(install_dir)  -name runzope -exec chown $(effectiveuser) \{\} \;')



def postdeploy():
    """Perform any final plugin tasks """

    hostout = api.env.get('hostout')
    hostout.setowners()

    api.env.cwd = api.env.path
    hostout_file=hostout.getHostoutFile()
    sudoparts = hostout.options.get('sudo-parts',None)
    if sudoparts:
        api.sudo('bin/buildout -c %(hostout_file)s install %(sudoparts)s' % locals())

 
    api.env.cwd = api.env.path
    for cmd in hostout.getPostCommands():
        api.sudo('sh -c "%s"'%cmd)

@buildoutuser
def run(*cmd):
    """Execute cmd on remote as login user """
    api.env.cwd = api.env.path
    api.run(' '.join(cmd))

def sudo(*cmd):
    """Execute cmd on remote as root user """
    api.env.cwd = api.env.path
    api.sudo(' '.join(cmd))

@buildoutuser
def put(file, target=None):
    if not target:
        target = file
    api.put(file, target)

@buildoutuser
def get(file, target=None):
    if not target:
        target = file
    with cd(api.env.path):
        api.get(file, target)
