# Raccoon2 gUSE cloud

Requriements (on top of the regular Raccoon2 requirements, e.g. must have MGLTools installed):

- WS-PGRADE server (possibly including a WS-PGRADE portal) with the RemoteAPI portlet enabled.
- Cloudbroker account with access to the AutoDock Vina software. The WS-PGRADE server should be connected with Cloudbroker.

Installing procedure:

- In the WS-PGRADE portal, create a simple workflow with 4 inputs and 1 output:
  - Inputs should be named: 'ligands.zip', 'receptors.zip', 'conf.txt', 'output_names.txt'.
  - Output should be named: 'output.zip'.
  - The software should be: AutoDock Vina 1.1.2.
  - The executable should be: AutoDock Vina 1.1.2 output_names_vina.sh.
- Export it (and rename it to 'gUSE-cloud-vina.zip', the one in this repo is a working example).
- Copy it this exported 'gUSE-cloud-vina.zip' in the Raccoon2/ folder replacing the example file 'gUSE-cloud-vina.zip'.
- The entire Raccoon2/ folder should replace the MGLToolsPckgs/CADD/Raccoon2/ folder in your MGLTools.
- Install the Requests module which is responsible for using HTTP by typing (in linux):
MGLToolsPckgs/CADD/Raccoon2/bin/pythonsh -m pip install requests
(if you are in the rood mgtltools folder, if not you need the correct path to pythonsh).
- In a terminal navigate to your MGLToolsPckgs/CADD/Raccoon2/bin, then run '../../../../bin/pythonsh ../gui/Raccoon2GUI.py'.



I have prepared several video presentations with more information about the Raccoon2 extensions, and I'm putting them up on YouTube:

* https://www.youtube.com/watch?v=Cw2hioCKbns
* https://www.youtube.com/watch?v=j-CfNMmZzNQ

I will group them all in this playlist:
https://www.youtube.com/watch?v=j-CfNMmZzNQ&list=PL1V2xiZKwGVZFz2oFCOD8AxRXMEpSaMfc
