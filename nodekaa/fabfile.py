# Copyright (C) 2019 Ulas Baloglu <ulasbaloglu@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import configparser
import sys
from fabric import task, Connection

CONFIG_FILE = "kaa.cfg"
config = configparser.RawConfigParser()
config.read(CONFIG_FILE)

@task
def deploy(ctx):
	'''
	Execute full tasks at once
	:return:
	'''
	staging(ctx)
	servertasks(ctx)
	installjava(ctx)
	installmariadb(ctx)
	securemariadb(ctx)
	createkaatables(ctx)
	installzookeeper(ctx)
	installmongodb(ctx)
	installkaanode(ctx)
	configurekaanode(ctx)
	initiatekaanode(ctx)
	finishdeployment(ctx)

@task
def staging(ctx):
	'''
	Setting up host credentials
	:return:
	'''
	ctx.name = 'staging'
	ctx.user = config._sections['node_kaa']['user']
	ctx.connect_kwargs = {"key_filename":[config._sections['node_kaa']['keyfile']]}
	ctx.host = config._sections['node_kaa']['host'] + ':' + config._sections['node_kaa']['port']

@task
def servertasks(ctx):
	'''
	Prepare the node, install updates
	:return:
	'''
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Starting Preperation of the Server\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt-get update')
		conn.sudo('apt-get -y upgrade')
		conn.sudo('mv /var/lib/dpkg/lock /var/lib/dpkg/lock_backup')
		conn.sudo('apt-get install -y wget ca-certificates curl')
		conn.sudo('rm -vf /var/lib/dpkg/lock_backup')
		sys.stdout.write("*** Server prepared ***\n\n")

@task
def installjava(ctx):
	'''
	Install OpenJDK 8
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing OpenJDK 8\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt install -y openjdk-8-jdk')

@task
def installmariadb(ctx):
	'''
	Install MariaDB 10.3
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** MariaDB 10.3\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt-get -y install software-properties-common')
		conn.sudo('apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8')
		conn.sudo('add-apt-repository \'deb [arch=amd64,arm64,ppc64el] http://sfo1.mirrors.digitalocean.com/mariadb/repo/10.3/ubuntu bionic main\'')
		conn.sudo('apt update')
		conn.sudo('debconf-set-selections <<< \'mariadb-server-10.3 mysql-server/root_password password ' + config._sections['node_kaa']['sql_password'] + '\'')
		conn.sudo('debconf-set-selections <<< \'mariadb-server-10.3 mysql-server/root_password_again password ' + config._sections['node_kaa']['sql_password'] + '\'')
		conn.sudo('apt install -y mariadb-server')
		conn.sudo('apt install -y mariadb-client')
		conn.sudo('apt install -y libmariadb-dev')
		conn.sudo('apt install -y libmariadb-dev-compat')
		conn.sudo('apt-get install -y libmariadbclient18')

@task
def securemariadb(ctx):
	'''
	Secure MariaDB Installation
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Securing MYSQL installation\n")
		sys.stdout.write("*** Root password remains UNCHANGED here, you can change it later in server console\n")
		sys.stdout.write("*** Removing anonymous users, removing test database and reloading privilage tables\n")
		sys.stdout.write("****************************\n")
		conn.sudo('sleep 6')
		conn.sudo('echo -e "' + config._sections['node_kaa']['sql_password'] + '\n'\
		 + 'n\ny\nn\ny\ny\n " | mysql_secure_installation')
		conn.sudo('netstat -ntlp | grep 3306')
		sys.stdout.write("*** MariaDB 10.3 installed ***\n\n")		

@task
def createkaatables(ctx):
	'''
	Create SQL Tables for Kaa
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Creation of SQL Tables for Kaa\n")
		sys.stdout.write("****************************\n")
		conn.put(config._sections['node_kaa']['kaa_sqlfile'])
		conn.run('chmod +x ' + config._sections['node_kaa']['kaa_sqlfile'])
		conn.run('./' + config._sections['node_kaa']['kaa_sqlfile'] + ' ' + config._sections['node_kaa']['sql_password'])
		conn.sudo('rm ' + config._sections['node_kaa']['kaa_sqlfile'])
		sys.stdout.write("*** SQL tables for Kaa prepared ***\n\n")

@task
def installzookeeper(ctx):
	'''
	Install Apache Zookeeper
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing Zookeeper\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt-get -y install zookeeper')
		conn.sudo('/usr/share/zookeeper/bin/zkServer.sh start')
		conn.sudo('sleep 3')
		sys.stdout.write("*** Zookeper installed ***\n\n")
		conn.run('netstat -ntlp | grep 2181')

@task
def installmongodb(ctx):
	'''
	Install MongoDB
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing MongoDB\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt-get remove mongodb* --purge')
		conn.sudo('apt-get update')
		conn.sudo('apt-get install -y mongodb')
		conn.sudo('sleep 2')
		conn.sudo('systemctl status mongodb')
		conn.sudo('sleep 1')
		conn.run('mongo --eval \'db.runCommand({ connectionStatus: 1 })\'')
		sys.stdout.write("*** MongoDB installed ***\n\n")

@task
def installkaanode(ctx):
	'''
	Install Kaa Node
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing Kaa Node\n")
		sys.stdout.write("****************************\n")
		conn.put(config._sections['node_kaa']['kaa_tarfile'])
		conn.sudo('tar -xvf kaa-deb-*.tar.gz')
		conn.sudo('dpkg -i ./deb/kaa-node-*.deb')
		conn.sudo('rm ./deb/flume*')
		conn.sudo('rm ./deb/kaa*')
		conn.sudo('rm ' + config._sections['node_kaa']['kaa_tarfile'])
		sys.stdout.write("Controlling installation\n")
		conn.run('cat /etc/kaa-node/conf/admin-dao.properties | grep jdbc_username')
		conn.run('cat /etc/kaa-node/conf/admin-dao.properties | grep jdbc_password')
		conn.run('cat /etc/kaa-node/conf/sql-dao.properties | grep jdbc_username')
		conn.run('cat /etc/kaa-node/conf/sql-dao.properties | grep jdbc_password')
		conn.run('cat /etc/kaa-node/conf/nosql-dao.properties | grep nosql_db_provider_name')
		sys.stdout.write("*** Kaa node installed ***\n\n")

@task
def configurekaanode(ctx):
	'''
	Configure Kaa Node
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Configuring Kaa Node\n")
		sys.stdout.write("****************************\n")
		conn.sudo('sed -i \'s/transport_public_interface=localhost/transport_public_interface='\
		 + config._sections['node_kaa']['host'] + '/g\' /etc/kaa-node/conf/kaa-node.properties')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 22 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 22 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 8080 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 8080 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 9888 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 9888 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 9889 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 9889 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 9997 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 9997 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 9999 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 9999 proto tcp')
		sys.stdout.write("persistent installation\n")
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections')
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections')
		conn.sudo('apt-get install -y iptables-persistent')
		sys.stdout.write("starting persistent\n")
		conn.sudo('service netfilter-persistent start')
		conn.sudo('netfilter-persistent save')

@task
def initiatekaanode(ctx):
	'''
	Initiate Kaa server from dump file or from stratch
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("Would you like to restore kaa server from sql dump file? (y/n): ")
		choice = input().lower()
		yes = {'yes','y', 'ye', ''}
		no = {'no','n'}
		if choice in yes:
			conn.put(config._sections['node_kaa']['kaa_dumpfile'])
			conn.sudo('mysql -uroot -p' + config._sections['node_kaa']['sql_password']\
			 + ' kaa < ' + config._sections['node_kaa']['kaa_dumpfile'])
			conn.sudo('rm ' + config._sections['node_kaa']['kaa_dumpfile'])
			startkaanode(ctx)
		elif choice in no:
   			startkaanode(ctx)
		else:
   			sys.stdout.write("Please respond with 'yes' or 'no'\n")
   			initiatekaanode(ctx)

@task
def startkaanode(ctx):
	'''
	Start Kaa server
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("starting kaa node\n")
		conn.sudo('service kaa-node start')
		sys.stdout.write("*** Kaa node configured ***\n")
		sys.stdout.write("*** Node deployment finished ***\n")
		sys.stdout.write("Open Administration UI http://" + config._sections['node_kaa']['host']\
		 + ":8080/kaaAdmin\n")

@task
def finishdeployment(ctx):
	'''
	Final tasks for the deployment
	:return:
	'''
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('rm /var/lib/apt/lists/lock')
		conn.sudo('rm /var/cache/apt/archives/lock')
		conn.sudo('rm /var/lib/dpkg/lock')
		conn.sudo('dpkg --configure -a')

