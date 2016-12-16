#!/bin/bash
JAVA_OPTS="-XX:+HeapDumpOnOutOfMemoryError -Xms512m -Xmx1024m"
JAVA_OPTS="-Xms512m -Xmx2048m"
JAVA_OPTS="$JAVA_OPTS -XX:+UseParallelGC -Xss4m -XX:+UseCompressedOops -Xverify:none -server"

JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.port=9998"
JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.authenticate=false"
JAVA_OPTS="$JAVA_OPTS -Dcom.sun.management.jmxremote.ssl=false"

LAC_OPTS="-c 0.000001 -m 2 -p 39737 -s 0.001 -d -i $1 -b $2"
CLASSPATH=bin:lib/* java $JAVA_OPTS br.org.inweb.ctweb.lac.server.LacServer $LAC_OPTS 
