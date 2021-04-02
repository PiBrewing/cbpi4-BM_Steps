# CBPi4 Plugin for Mash Steps

Still under development and in Beta test phase 

## Several steps for CBPi4 that allow a full brewing
### These steps can be used to run a Speidel Braumeister automatically if the corresponding KettleLogic Plugin (cbpi4-BM_PIDSmartBoilWithPump) is also used

- BM_MashInStep:
	- Heats up to the target temp and stops when temp is reached. This can be used to add e.g. Malt Pipe. User has to manually move to next step
	- Parameters:
		- Temp: Target Temp for MashInStep
		- Sensor: Sensor to be used for this step
		- Kettle: Kettle to be used for this step
		- AutoMode: If yes: Kettle Logic will be switched on/off when step starts/stops

- BM_MashStep:
	- Heats up to the target temp and runs until Timer is done.
	- Parameters:
		- Time: Time in Minutes for Timer
		- Temp: Target Temp for MashStep
		- Sensor: Sensor to be used for this step
		- Kettle: Kettle to be used for this step
		- AutoMode: If yes: Kettle Logic will be switched on/off when step starts/stops

- BM_BoilStep:
	- Heats up to the target temp and runs until Timer is done. Is sending notifications to add hops
	- Parameters:
		- Time: Time in Minutes for Timer
		- Temp: Target Temp for BoilStep
		- Sensor: Sensor to be used for this step
		- Kettle: Kettle to be used for this step
		- AutoMode: If yes: Kettle Logic will be switched on/off when step starts/stops
		- First Wort: Sends a notification for First Wort Hops on Start if set to 'Yes'
		- Hop [1-6]: Sends up to 6 notifications for Hop alarms on specified times
			- Time is remaining Boil time in Minutes

- BM_Cooldown:
	- Waits that Wort is cooled down to target temp and is sending a notification. Active Step if Actor is selected.
	- Parameters:
		- Temp: Target Temp for Notification
		- Sensor: Sensor to be used for this step
		- Kettle: Kettle to be used for this step
		- Actor: Actor that is switched on during cooldown f selected (can be used to trigger a magnetic valve)
		- Interval: Interval in minutes when Step is checking current temp and calclulating estimated end time (2nd degree polynomial model)

- BM_SimpleStep:
	- Is sending a Notification and can wait on user
	- Parameters:
		- Notification: Notification text that can be specified by user
		- AutoNext: If set to 'No', step is wating for user input to move to next step. Otherwsie, next step is automatically started.

Changelog:

** 02.04.21:

- 2nd degree polynomial model to predict ECD of cooldown
- Added Actor to cooldown step to trigger magnetic valve is required. No selection won't trigger anything and step will run as passive step

** 28.03.21:

- Added Parameter to Cooldown Step to calculate estimated completion time (ECT). -> Notifications on ECT are send with Interval frequency
- Notifications are changed for mash steps and boil step. -> On Timer start, estimated end time will be send as notification

** 24.03.21:

- Added one Hop alarm -> Total of 6 Alarms are currently possible

** 15.03.21:

- Requirement is now cbpi >= 4.0.0.33 to accomodate the new notification system

** 09.03.2021

- Updated Notifications to accomodate changes starting in cbpi 4.0.0.31 which is now required

** 07.03.2021

- Added AutoNext function to Simple Step
	- If 'Yes', next step will be started automatically, if 'No' user has to push next to start next step
- Added selection for AutoMode in Mash and Boilsteps
	- If set to 'yes', Kettle Logic will be switched on when Step starts and switched off when Step ends

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
