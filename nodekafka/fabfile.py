import os
import configparser
import sys
from fabric import task, Connection

CONFIG_FILE = "kafka.cfg"
config = configparser.RawConfigParser()
config.read(CONFIG_FILE)

@task
def start(ctx):
	staging(ctx)

@task
def staging(ctx):
	ctx.name = 'staging'
	ctx.user = config._sections['node_kafka']['user']
	ctx.connect_kwargs = {"key_filename":[config._sections['node_kafka']['keyfile']]}
	ctx.host = config._sections['node_kafka']['host'] + ':' + config._sections['node_kafka']['port']
	servertasks(ctx)
	
@task
def servertasks(ctx):
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
		installkafka(ctx)

@task
def installkafka(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing Kafka 2.12-2.1.1\n")
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Creating a new user as kafka\n")
		sys.stdout.write("*** Specify the password: \n")
		conn.sudo('useradd kafka -m')
		conn.sudo('passwd kafka')
		conn.sudo('adduser kafka sudo')
		conn.sudo('su -l kafka -c "mkdir ~/Downloads"')
		conn.sudo('su -l kafka -c "curl \"http://www-eu.apache.org/dist/kafka/2.1.1/kafka_2.12-2.1.1.tgz\"\
		 -o ~/Downloads/kafka.tgz"')
		conn.sudo('su -l kafka -c "mkdir ~/kafka"')
		conn.sudo('su -l kafka -c "tar -xvzf ~/Downloads/kafka.tgz -C ~/kafka --strip 1"')
		conn.sudo('su -l kafka -c "sed -i  \'$ a delete.topic.enable = true\' ~/kafka/config/server.properties"')
		conn.put(config._sections['node_kafka']['kafka_servicefile'])
		conn.sudo('cp ' + config._sections['node_kafka']['kafka_servicefile'] + ' /etc/systemd/system/kafka.service')
		installzookeeper(ctx)

@task
def installzookeeper(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing Zookeper\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt-get -y install zookeeper')
		conn.put(config._sections['node_kafka']['zookeeper_servicefile'])
		conn.sudo('cp ' + config._sections['node_kafka']['zookeeper_servicefile'] + ' /etc/systemd/system/zookeeper.service')
		conn.sudo('/usr/share/zookeeper/bin/zkServer.sh start')
		conn.sudo('sleep 3')
		sys.stdout.write("*** Zookeper installed ***\n\n")
		conn.run('netstat -ntlp | grep 2181')
		conn.sudo('rm ' + config._sections['node_kafka']['kafka_servicefile'])
		conn.sudo('rm ' + config._sections['node_kafka']['zookeeper_servicefile'])
		installjava(ctx)	
		
@task
def installjava(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing Oracle JDK 8\n")
		sys.stdout.write("****************************\n")
		conn.sudo('add-apt-repository ppa:webupd8team/java')
		conn.sudo('apt-get update')
		conn.sudo('echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections')
		conn.sudo('echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections')
		conn.sudo('apt-get install -y oracle-java8-installer')
		sys.stdout.write("*** Oracle JDK 8 installed ***\n\n")
		startkafka(ctx)

@task
def startkafka(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("starting kafka node\n")
		conn.sudo('systemctl start kafka')
		conn.sudo('sleep 10')
		conn.sudo('journalctl -u kafka')
		conn.sudo('systemctl enable kafka')
		installkafkat(ctx)

@task
def installkafkat(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing KafkaT\n")
		sys.stdout.write("****************************\n")
		conn.sudo('apt install -y ruby ruby-dev build-essential')
		conn.sudo('gem install kafkat')
		conn.put(config._sections['node_kafka']['kafkat_cfgfile'])
		conn.sudo('cp ' + config._sections['node_kafka']['kafkat_cfgfile'] + ' /home/kafka/.kafkatcfg')
		conn.sudo('rm ' + config._sections['node_kafka']['kafkat_cfgfile'])
		conn.sudo('su -l kafka -c "kafkat partitions"')
		conn.sudo('deluser kafka sudo')
		conn.sudo('passwd kafka -l')
		conn.sudo('systemctl stop kafka')
		conn.sudo('cp -R /tmp/kafka-logs ~/kafla-log-backup')
		conn.sudo('mkdir -p /opt/kafka')
		conn.sudo('cp -R /tmp/kafka-logs /opt/kafka/')
		conn.sudo('chown -R kafka:kafka /opt/kafka')
		conn.sudo('sed -i \'s/log.dirs=\\/tmp\\/kafka-logs/log.dirs=\\/opt\\/kafka\\/logs/g\' /home/kafka/kafka/config/server.properties')
		conn.sudo('systemctl start kafka')
		conn.sudo('systemctl enable zookeeper')
		setupiptables(ctx)

@task
def setupiptables(ctx):
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 22 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 22 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 9092 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 9092 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 2181 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 2181 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 2888 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 2888 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 3888 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 3888 proto tcp')
		sys.stdout.write("persistent installation\n")
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections')
		conn.sudo('echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections')
		conn.sudo('apt-get install -y iptables-persistent')
		sys.stdout.write("starting persistent\n")
		conn.sudo('service netfilter-persistent start')
		conn.sudo('netfilter-persistent save')
		conn.sudo('rm /var/lib/apt/lists/lock')
		conn.sudo('rm /var/cache/apt/archives/lock')
		conn.sudo('rm /var/lib/dpkg/lock')
		conn.sudo('dpkg --configure -a')
		sys.stdout.write("*** Kafka node successfully installed ***\n")
		sys.stdout.write("*** Node deployment finished ***\n")
