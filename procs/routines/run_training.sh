#!/bin/bash

count_training=`python /scratch/bigsea_active_learning/routines/update_training_file.py`
change_supervisord=`python /scratch/bigsea_active_learning/routines/configure_supervisor_ini.py`

if [ $change_supervisord -eq 1 ]
then
	supervisorctl reread;
	supervisorctl update;
	supervisorctl mstop *lac_classification*;
	supervisorctl mstop *lac_classifier*;
	supervisorctl mstart *lac_classifier*;
	supervisorctl mstart *lac_classification*;

	echo -e "Supervisor was updated.";
else
	echo -e "No changes for supervisord.";
fi

if [ $count_training -gt 0 ]
then
	supervisorctl mstop *lac_classification*;
	supervisorctl mstop *lac_classifier*;
	supervisorctl mstart *lac_classifier*;
	supervisorctl mstart *lac_classification*; 
	
	echo -e "Was added $count_training.";
else
	echo -e "No instances to be added.";
fi
