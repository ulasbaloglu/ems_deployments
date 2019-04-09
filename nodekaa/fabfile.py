import os
import configparser
from fabric import task, Connection

CONFIG_FILE = "kaa.cfg"
config = configparser.RawConfigParser()
config.read(CONFIG_FILE)

@task
def start(ctx):
	staging(ctx)

@task
def staging(ctx):
	ctx.name = 'staging'
	ctx.user = config._sections['node_kaa']['user']
	ctx.connect_kwargs = {"key_filename":[config._sections['node_kaa']['keyfile']]}
	ctx.host = config._sections['node_kaa']['host'] + ':' + config._sections['node_kaa']['port']
	servertasks(ctx)

@task
def servertasks(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('apt-get update')
		conn.sudo('apt-get upgrade')
		conn.sudo('mv /var/lib/dpkg/lock /var/lib/dpkg/lock_backup')
		conn.sudo('apt-get install wget ca-certificates curl')
		conn.sudo('rm -vf /var/lib/dpkg/lock_backup')
		installjava(ctx)

@task
def installjava(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('add-apt-repository ppa:webupd8team/java')
		conn.sudo('apt-get update')
		conn.sudo('echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections')
		conn.sudo('echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections')
		conn.sudo('apt-get install oracle-java8-installer')
		installmariadb(ctx)

@task
def installmariadb(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('apt-get install software-properties-common')
		conn.sudo('apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8')
		conn.sudo('add-apt-repository \'deb [arch=amd64,arm64,ppc64el] http://sfo1.mirrors.digitalocean.com/mariadb/repo/10.3/ubuntu bionic main\'')
		conn.sudo('apt update')
		conn.sudo('debconf-set-selections <<< \'mariadb-server-10.3 mysql-server/root_password password ' + config._sections['node_kaa']['sql_password'] + '\'')
		conn.sudo('debconf-set-selections <<< \'mariadb-server-10.3 mysql-server/root_password_again password ' + config._sections['node_kaa']['sql_password'] + '\'')
		conn.sudo('apt install mariadb-server')
		conn.sudo('apt install mariadb-client')
		conn.sudo('apt install libmariadb-dev')
		conn.sudo('apt install libmariadb-dev-compat')
		conn.sudo('apt-get install libmariadbclient18')
		conn.sudo('mysql_secure_installation')
		conn.sudo('netstat -ntlp | grep 3306')		
		createtables(ctx)

@task
def createtables(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.put(config._sections['node_kaa']['kaa_sqlfile'])
		conn.run('chmod +x ' + config._sections['node_kaa']['kaa_sqlfile'])
		conn.run('./' + config._sections['node_kaa']['kaa_sqlfile'] + ' ' + config._sections['node_kaa']['sql_password'])
		conn.sudo('rm ' + config._sections['node_kaa']['kaa_sqlfile'])
		installzookeeper(ctx)

@task
def installzookeeper(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('apt-get install zookeeper')
		conn.sudo('/usr/share/zookeeper/bin/zkServer.sh start')
		conn.run('netstat -ntlp | grep 2181')
		installmongodb(ctx)

@task
def installmongodb(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('apt-get remove mongodb* --purge')
		conn.sudo('apt-get update')
		conn.sudo('apt-get install -y mongodb')
		conn.sudo('systemctl status mongodb')
		conn.run('mongo --eval \'db.runCommand({ connectionStatus: 1 })\'')
		installkaaserver(ctx)

@task
def installkaaserver(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.put(config._sections['node_kaa']['kaa_tarfile'])
		conn.sudo('tar -xvf kaa-deb-*.tar.gz')
		conn.sudo('dpkg -i ./deb/kaa-node-*.deb')
		conn.sudo('rm ./deb/flume*')
		conn.sudo('rm ./deb/kaa*')
		conn.sudo('rm ' + config._sections['node_kaa']['kaa_tarfile'])
		conn.run('echo Controlling installation')
		conn.run('cat /etc/kaa-node/conf/admin-dao.properties | grep jdbc_username')
		conn.run('cat /etc/kaa-node/conf/admin-dao.properties | grep jdbc_password')
		conn.run('cat /etc/kaa-node/conf/sql-dao.properties | grep jdbc_username')
		conn.run('cat /etc/kaa-node/conf/sql-dao.properties | grep jdbc_password')
		conn.run('cat /etc/kaa-node/conf/nosql-dao.properties | grep nosql_db_provider_name')
		configurekaaserver(ctx)

@task
def configurekaaserver(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
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
		conn.run('echo persistent installation')
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections')
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections')
		conn.sudo('apt-get install iptables-persistent')
		conn.run('echo starting persistent')
		conn.sudo('service netfilter-persistent start')
		conn.sudo('netfilter-persistent save')
		conn.run('echo starting kaa node')
		conn.sudo('service kaa-node start')
		conn.run('echo Finished installation')
		conn.run('echo Open Administration UI http://' + config._sections['node_kaa']['host']\
		 + ':8080/kaaAdmin')

