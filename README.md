# KAA NODE INSTALLATION
For Ubuntu 18.04

## Configuration
- Put your kaa-deb file in your project folder.<BR/>
- Rename `nodekaa/kaa-template.cfg` as `kaa.cfg` and update with your server settings.<BR/>
Initiate your MySQL root password in the configuration file and it won't be changed during securing the installation.<BR/>
You may change it later at the server console.<BR/>
- If you are restoring from another Kaa instance, put your kaa sql dump file in your project folder, <BR/>
update `kaadumpfile` field of `kaa.cfg` , and during installation answer "Y" to restore question. <BR/>

# KAFKA NODE INSTALLATION
For Ubuntu 18.04

## Configuration
- Rename `nodekafka/kafka-template.cfg` as `kafka.cfg` and update with your settings.<BR/>

# TIMESCALEDB NODE INSTALLATION
For Ubuntu 18.04

## Configuration
- Rename `nodetimescaledb/timescaledb-template.cfg` as `timescaledb.cfg` and update with your settings.<BR/>
