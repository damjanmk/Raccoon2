# Raccoon2 gUSE cloud

Requriements (on top of the regular Raccoon2 requirements, e.g. must have MGLTools installed):

- WS-PGRADE server (possibly a gUSE/WS-PGRADE portal) with RemoteAPI enabled 
- Cloudbroker account with access to the AutoDock Vina software

Installing procedure:

- create a simple workflow with 4 inputs and 1 output
  - inputs should be named: 'ligands.zip', 'receptors.zip', 'conf.txt', 'output_names.txt'
  - output should be named: 'output.zip'
  - the software should be: AutoDock Vina 1.1.2
  - the executable should be: AutoDock Vina 1.1.2 output_names_vina.sh
- export it (and rename it to 'gUSE-cloud-vina.zip', the one in this repo is a working example)
- copy it in the Raccoon2/ folder in place of the example 'gUSE-cloud-vina.zip'
- the entire Raccoon2/ folder should replace the MGLToolsPckgs/CADD/Raccoon2/ folder in your MGLTools
- then "In a terminal navigate to your MGLToolsPckgs directory, then run '../bin/pythonsh ./CADD/Raccoon2/bin/raccoonLauncher'" as per usual
