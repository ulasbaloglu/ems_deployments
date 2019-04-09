#!/bin/bash
echo Creating sql tables for kaa
mysql -uroot -p$1 <<KAA_QUERY
CREATE USER 'sqladmin'@'localhost' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON *.* TO 'sqladmin'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
CREATE DATABASE kaa
   CHARACTER SET utf8
   COLLATE utf8_general_ci;
KAA_QUERY
