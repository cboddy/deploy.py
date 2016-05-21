from subprocess import Popen
import argparse, os, os.path, shutil


upstart_template = """
description "{} service runtime"
author "chris@boddy.im"


# Start on startup
start on runlevel [2345]

# Stop on restart / shutdown 
stop on runlevel [016]

# Automatically restart process if crashed
respawn

# Essentially lets upstart know the process will detach itself to the background
# This option does not seem to be of great importance, so it does not need to be set.
# expect fork

# Specify working directory
chdir /root/{}

# Specify the process/command to start, e.g.
script
        exec bash -c '{}'
end script

"""

def buildUpstart(name, directory, runtime):
    return upstart_template.format(name, runtime, directory)

def run(args):
    proc = Popen(args) 
    proc.wait()

BUNDLE = "app.bundle.tar.gz"
REMOTE_SCRIPT ="ssh_command"

def deploy(
        remote, 
        serviceName, 
        serviceExec,
        deployDirectory, 
        tarTargets,
        extra,
        make,
        clean
        ):
    serviceConf = serviceName +".conf"
    #make
    run(make)
    #write upstart script
    with open(serviceConf, "w") as f:
        f.write(buildUpstart(serviceName, deployDirectory, serviceExec))

    ###define script to run on remote env
    ssh = [
            "mkdir -p "+ deployDirectory,
            "service "+ serviceName +" stop",
            "cp "+ BUNDLE +" "+ deployDirectory,
            "cd "+ deployDirectory,
            "tar -zxvf "+ BUNDLE,
            "chown -R root:root *",
            "cp "+serviceConf+" /etc/init/",
            "service "+ serviceName +" start"
            ]
    if not extra is None:
        ssh.append(extra)
    
    if clean:
        ssh = ssh[:4] + map(lambda x: "rm -rf "+x, tarTargets) + ssh[4:]
    
    with open(REMOTE_SCRIPT, "w") as f:
        f.write(reduce(lambda a,b : a+"\n"+b, ssh))


    tarTargets.append(serviceConf)
    tarTargets.append(REMOTE_SCRIPT)

    #remove old bundles
    run(["rm", "-f", BUNDLE])
    #build tarball
    run(["tar", "-zcvf", BUNDLE] + tarTargets)
    #copy over tarball
    run(["scp", BUNDLE, "ssh_command", remote +":/root/"])
    #tidy up temp upstart conf 
    run(["rm", "-f", serviceConf, REMOTE_SCRIPT])
    #run remote script over ssh on remote
    run(["ssh", remote, "source "+REMOTE_SCRIPT ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Service deployment app.')
    parser.add_argument('-remote', required=True , help='remote host eg. root@localhost.')
    parser.add_argument('-name', required=True, help='upstart service name.')
    parser.add_argument('-dir', required=True, help='remote directory to deploy to in /root/')
    parser.add_argument('-targets', nargs="+", required=True, help='files and directories to deploy')
    parser.add_argument('-extra', default=None , help='additional command to run on the remote during deployment eg. mongo/mysql setup script')
    parser.add_argument('-execs', required=True, help="escaped executable to be run in upstart eg. \'java -jar Jet.jar\'")
    parser.add_argument('-make', nargs="+", default="make", help="make command")
    parser.add_argument('-clean', type=bool, default=True, help="Remove existing package from remote host before deployment")
    args = parser.parse_args()
    
    print("deployment params", args)
    
    deploy(
            args.remote,
            args.name,
            args.execs,
            args.dir,
            args.targets,
            args.extra,
            args.make,
            args.clean
            )
