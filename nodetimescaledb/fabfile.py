import os
import configparser
import sys
from fabric import task, Connection

CONFIG_FILE = "timescaledb.cfg"
config = configparser.RawConfigParser()
config.read(CONFIG_FILE)

@task
def deploy(ctx):
	'''
	Execute full tasks at once
	:return:
	'''
	staging(ctx)

@task
def staging(ctx):
	'''
	Setting up host credentials
	:return:
	'''
	ctx.name = 'staging'
	ctx.user = config._sections['node_timescaledb']['user']
	ctx.connect_kwargs = {"key_filename":[config._sections['node_timescaledb']['keyfile']]}
	ctx.host = config._sections['node_timescaledb']['host'] + ':' + config._sections['node_timescaledb']['port']
	servertasks(ctx)

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
		installpostgresql(ctx)

@task
def installpostgresql(ctx):
	'''
	Install PostgreSQL 11
	:return:
	'''	
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing PostgreSQL 11\n")
		sys.stdout.write("****************************\n")
		conn.sudo('wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -')
		conn.put(config._sections['node_timescaledb']['repository_file'])
		conn.sudo('cp ' + config._sections['node_timescaledb']['repository_file'] + ' /etc/apt/sources.list.d/pgdg.list')
		conn.sudo('rm ' + config._sections['node_timescaledb']['repository_file'])
		conn.sudo('apt-get update')
		conn.sudo('apt-get install -y postgresql-11')
		conn.sudo('apt-get install -y postgresql-contrib')
		sys.stdout.write("***Changing postgres password \n")
		conn.sudo('-u postgres psql -U postgres -d postgres -c "alter user postgres with password \''\
		 + config._sections['node_timescaledb']['postgres_password'] + '\';"')
		installtimescaledb(ctx)

@task
def installtimescaledb(ctx):
	'''
	Install TimescaleDB 1.2.2
	:return:
	'''
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		sys.stdout.write("****************************\n")
		sys.stdout.write("*** Installing TimescaleDB 1.2.2\n")
		sys.stdout.write("****************************\n")
		conn.sudo('add-apt-repository ppa:timescale/timescaledb-ppa')
		conn.sudo('apt-get update')
		conn.sudo('apt install -y timescaledb-postgresql-11')
		conn.sudo('timescaledb-tune --quiet --yes')
		conn.sudo('service postgresql restart')
		setupiptables(ctx)

@task
def setupiptables(ctx):
	'''
	Setup IP Tables open ports for outside access
	:return:
	'''
	with Connection(ctx.host, ctx.user, connect_kwargs=ctx.connect_kwargs) as conn:
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 22 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 22 proto tcp')
		conn.sudo('iptables -I INPUT -p tcp -m tcp --dport 5432 -j ACCEPT')
		conn.sudo('ufw allow from any to any port 5432 proto tcp')
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
		sys.stdout.write("*** TimescaleDB node successfully installed ***\n")
		sys.stdout.write("*** Node deployment finished ***\n")
		sys.stdout.write("*** If you want to open timescaledb to outside connections\n")
		sys.stdout.write("*** Edit /etc/postgresql/11/main/pg_hba.conf file\n")
		sys.stdout.write("*** Under (# IPv4 local connections:) insert allowed IP addresses such as \n")
		sys.stdout.write("*** host    all             all             10.0.3.2/32            md5\n")
		sys.stdout.write("*** host    all             all             0.0.0.0/0            md5\n")


