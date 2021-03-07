# CBPi4 Plugin for Mash Steps

Still under development and in Beta test phase 

** 03.03.21 (Still Beta Test)

- Added several steps
	- MashIn with Pause and request to add malt pipe before next step can be manually started
	- Mashout (SimpleStep) with Pause to remove Malt Pipe before boiling can be started -> Text Notificatrion to be set
	- Cooldown Step where Target temp can be set. Once temp is reached, notification is send
	- Modification of Voilstepd timer handling -> no mod of cbpi timer is required anymore
	
** Initial Test release

- Focused on Braumeister, but applicable to other systems
- Boil step with alarms for First wort and 5 Hop/Adjunct additions
-> currently only notification in bash -> to be added to notify system of CBPi, once available
- Auto mode for Kettle logic
-> Kettle logic is siwtched on, when step is starting and switched off, when step ends
