
import asyncio
import aiohttp
from aiohttp import web
from cbpi.api.step import CBPiStep, StepResult
from cbpi.api.timer import Timer
from cbpi.api.dataclasses import Kettle, Props
from datetime import datetime
import time
from cbpi.api import *
import logging
from socket import timeout
from typing import KeysView
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
from voluptuous.schema_builder import message
from cbpi.api.dataclasses import NotificationAction, NotificationType
import numpy as np
import requests
import warnings

@parameters([Property.Text(label="Notification",configurable = True, description = "Text for notification"),
             Property.Select(label="AutoNext",options=["Yes","No"], description="Automatically move to next step (Yes) or pause after Notification (No)")])

class BM_SimpleStep(CBPiStep):

    async def NextStep(self, **kwargs):
        await self.next()

    async def on_timer_done(self,timer):
        self.summary = self.props.get("Notification","")

        if self.AutoNext == True:
            self.cbpi.notify(self.name, self.props.get("Notification",""), NotificationType.INFO)
            await self.next()
        else:
            self.cbpi.notify(self.name, self.props.get("Notification",""), NotificationType.INFO, action=[NotificationAction("Next Step", self.NextStep)])
            await self.push_update()

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.summary=""
        self.AutoNext = False if self.props.get("AutoNext", "No") == "No" else True
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        await self.push_update()

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)
            if self.timer.is_running is not True:
                self.timer.start()
                self.timer.is_running = True

        return StepResult.DONE

@parameters([Property.Number(label="Temp", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle"),
             Property.Select(label="AutoMode",options=["Yes","No"], description="Switch Kettlelogic automatically on and off -> Yes")])

class BM_MashInStep(CBPiStep):

    async def NextStep(self, **kwargs):
        await self.next()

    async def on_timer_done(self,timer):
        self.summary = "MashIn Temp reached. Please add Malt Pipe."
        await self.push_update()
        if self.AutoMode == True:
            await self.setAutoMode(False)
        self.cbpi.notify(self.name, 'MashIn Temp reached. Please add malt pipe and malt. Move to next step', action=[NotificationAction("Next Step", self.NextStep)])

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.port = str(self.cbpi.static_config.get('port',8000))
        self.AutoMode = True if self.props.get("AutoMode","No") == "Yes" else False
        self.kettle=self.get_kettle(self.props.get("Kettle", None))
        self.kettle.target_temp = int(self.props.get("Temp", 0))
        if self.AutoMode == True:
            await self.setAutoMode(True)
        self.summary = "Waiting for Target Temp"
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        if self.AutoMode == True:
            await self.setAutoMode(False)
        await self.push_update()

    async def run(self):
        while self.running == True:
           await asyncio.sleep(1)
           sensor_value = self.get_sensor_value(self.props.get("Sensor", None)).get("value")
           if sensor_value >= int(self.props.get("Temp",0)) and self.timer.is_running is not True:
               self.timer.start()
               self.timer.is_running = True
        await self.push_update()
        return StepResult.DONE

    async def reset(self):
        self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                url="http://127.0.0.1:" + self.port + "/kettle/"+ self.kettle.id+"/toggle"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url) as response:
                        return await response.text()
                        await self.push_update()
            elif (self.kettle.instance.state == True) and (auto_state is False):

                await self.kettle.instance.stop()
                await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))

@parameters([Property.Number(label="Timer", description="Time in Minutes", configurable=True), 
             Property.Number(label="Temp", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle"),
             Property.Select(label="AutoMode",options=["Yes","No"], description="Switch Kettlelogic automatically on and off -> Yes")])

class BM_MashStep(CBPiStep):

    @action("Start Timer", [])
    async def start_timer(self):
        if self.timer.is_running is not True:
            self.cbpi.notify(self.name, 'Timer started', NotificationType.INFO)
            self.timer.start()
            self.timer.is_running = True
        else:
            self.cbpi.notify(self.name, 'Timer is already running', NotificationType.WARNING)

    @action("Add 5 Minutes to Timer", [])
    async def add_timer(self):
        if self.timer.is_running == True:
            self.cbpi.notify(self.name, '5 Minutes added', NotificationType.INFO)
            await self.timer.add(300)       
        else:
            self.cbpi.notify(self.name, 'Timer must be running to add time', NotificationType.WARNING)


    async def on_timer_done(self,timer):
        self.summary = ""
        if self.AutoMode == True:
            await self.setAutoMode(False)
        self.cbpi.notify(self.name, 'Step finished', NotificationType.SUCCESS)
       
        await self.next()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        await self.push_update()

    async def on_start(self):
        self.port = str(self.cbpi.static_config.get('port',8000))
        self.AutoMode = True if self.props.get("AutoMode", "No") == "Yes" else False
        self.kettle=self.get_kettle(self.props.Kettle)
        self.kettle.target_temp = int(self.props.get("Temp", 0))
        if self.AutoMode == True:
            await self.setAutoMode(True)
        await self.push_update()

        if self.timer is None:
            self.timer = Timer(int(self.props.get("Timer",0)) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.summary = "Waiting for Target Temp"
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        if self.AutoMode == True:
            await self.setAutoMode(False)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.get("Timer",0)) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)
            sensor_value = self.get_sensor_value(self.props.get("Sensor", None)).get("value")
            if sensor_value >= int(self.props.get("Temp",0)) and self.timer.is_running is not True:
                self.timer.start()
                self.timer.is_running = True
                estimated_completion_time = datetime.fromtimestamp(time.time()+ (int(self.props.get("Timer",0)))*60)
                self.cbpi.notify(self.name, 'Timer started. Estimated completion: {}'.format(estimated_completion_time.strftime("%H:%M")), NotificationType.INFO)
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                url="http://127.0.0.1:" + self.port + "/kettle/"+ self.kettle.id+"/toggle"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url) as response:
                        return await response.text()
                        await self.push_update()
            elif (self.kettle.instance.state == True) and (auto_state is False):

                await self.kettle.instance.stop()
                await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))


@parameters([Property.Number(label="Temp", configurable=True, description="Target temperature for cooldown. Notification will be send when temp is reached and Actor can be triggered"),
             Property.Number(label="Interval", configurable=True, description="Interval [min] for Notification and caclulate predicted End time"),
             Property.Sensor(label="Sensor", description="Sensor that is used during cooldown"),
             Property.Actor(label="Actor", description="Actor can trigger a valve for the cooldwon to target temperature"),
             Property.Kettle(label="Kettle")])
class BM_Cooldown(CBPiStep):

    async def on_timer_done(self,timer):
        self.summary = ""
        if self.actor is not None:
            await self.actor_off(self.actor)
        self.cbpi.notify('CoolDown', 'Wort cooled down. Please transfer to Fermenter.', NotificationType.INFO)
        await self.next()

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        warnings.simplefilter('ignore', np.RankWarning)
        self.temp_array = []
        self.time_array = []
        self.kettle = self.get_kettle(self.props.get("Kettle", None))
        self.actor = self.props.get("Actor", None)
        self.target_temp = int(self.props.get("Temp",0))
        self.Interval = int(self.props.get("Interval",10)) # Interval in minutes on how often cooldwon end time is calculated

        self.cbpi.notify(self.name, 'Cool down to {}°'.format(self.target_temp), NotificationType.INFO)
        if self.timer is None:
            self.timer = Timer(1,on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.start_time=time.time()
        self.temp_array.append(self.get_sensor_value(self.props.get("Sensor", None)).get("value"))
        self.time_array.append(time.time())
        self.next_check = self.start_time + self.Interval * 60
        self.count = 0

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        if self.actor is not None:
            await self.actor_off(self.actor)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(1,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        timestring = datetime.fromtimestamp(self.start_time)
        if self.actor is not None:
            await self.actor_on(self.actor)
        self.summary="Cool down to {}° started: {}".format(self.target_temp, timestring.strftime("%H:%M"))
        await self.push_update()
        while self.running == True:
            current_temp = self.get_sensor_value(self.props.get("Sensor", None)).get("value")
            if self.count == 19:
                self.temp_array.append(current_temp)
                self.time_array.append(time.time())
                self.count = 0
            if time.time() >= self.next_check:
                self.next_check = time.time() + (self.Interval * 60)
                cooldown_model = np.poly1d(np.polyfit(self.temp_array, self.time_array, 4))
                target_time=cooldown_model(self.target_temp)
                target_timestring= datetime.fromtimestamp(target_time)
                self.summary="EC: {}".format(target_timestring.strftime("%H:%M"))
                self.cbpi.notify("Cooldown Step","Current: {}°, reaching {}° at {}".format(round(current_temp,1), self.target_temp, target_timestring.strftime("%d.%m %H:%M")), NotificationType.INFO)
                await self.push_update()

            if current_temp <= self.target_temp and self.timer.is_running is not True:
                self.timer.start()
                self.timer.is_running = True

            self.count +=1
            await asyncio.sleep(1)

        return StepResult.DONE

@parameters([Property.Number(label="Timer", description="Time in Minutes", configurable=True), 
             Property.Number(label="Temp", description="Boil temperature", configurable=True),
             #Property.Number(label="DwellTime", description="Time in minutes (Recommended: 5). If temp is not changing significantly within this time, Timer will start. Defaul:0 disabled", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle"),
             Property.Select(label="LidAlert",options=["Yes","No"], description="Trigger Alert to remove lid if temp is close to boil"),
             Property.Select(label="AutoMode",options=["Yes","No"], description="Switch Kettlelogic automatically on and off -> Yes"),
             Property.Select(label="AutoTimer",options=["Yes","No"], description="Start Timer automatically if Temp does not change for 5 Minutes and is above 95C/203F"),
             Property.Select("First_Wort", options=["Yes","No"], description="First Wort Hop alert if set to Yes"),
             Property.Text("First_Wort_text", configurable = True, description="First Wort Hop alert text"),
             Property.Number("Hop_1", configurable = True, description="First Hop alert (minutes before finish)"),
             Property.Text("Hop_1_text", configurable = True, description="First Hop alert text"),
             Property.Number("Hop_2", configurable=True, description="Second Hop alert (minutes before finish)"),
             Property.Text("Hop_2_text", configurable = True, description="Second Hop alert text"),
             Property.Number("Hop_3", configurable=True, description="Third Hop alert (minutes before finish)"),
             Property.Text("Hop_3_text", configurable = True, description="Third Hop alert text"),
             Property.Number("Hop_4", configurable=True, description="Fourth Hop alert (minutes before finish)"),
             Property.Text("Hop_4_text", configurable = True, description="Fourth Hop alert text"),
             Property.Number("Hop_5", configurable=True, description="Fifth Hop alert (minutes before finish)"),
             Property.Text("Hop_5_text", configurable = True, description="Fifth Hop alert text"),
             Property.Number("Hop_6", configurable=True, description="Sixth Hop alert (minutes before finish)"),
             Property.Text("Hop_6_text", configurable = True, description="Sixth Hop alert text")])
class BM_BoilStep(CBPiStep):

    @action("Start Timer", [])
    async def start_timer(self):
        if self.timer.is_running is not True:
            self.cbpi.notify(self.name, 'Timer started', NotificationType.INFO)
            self.timer.start()
            self.timer.is_running = True
        else:
            self.cbpi.notify(self.name, 'Timer is already running', NotificationType.WARNING)

    @action("Add 5 Minutes to Timer", [])
    async def add_timer(self):
        if self.timer.is_running == True:
            self.cbpi.notify(self.name, '5 Minutes added', NotificationType.INFO)
            await self.timer.add(300)       
        else:
            self.cbpi.notify(self.name, 'Timer must be running to add time', NotificationType.WARNING)

    async def on_timer_done(self,timer):
        self.summary = ""
        self.kettle.target_temp = 0
        if self.AutoMode == True:
            await self.setAutoMode(False)
        self.cbpi.notify(self.name, 'Boiling completed', NotificationType.SUCCESS)
        await self.next()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        self.remaining_seconds = seconds
        await self.push_update()

    async def on_start(self):

        self.lid_temp = 95 if self.get_config_value("TEMP_UNIT", "C") == "C" else 203
        self.lid_flag = True if self.props.get("LidAlert", "No") == "Yes" else False
        self.AutoMode = True if self.props.get("AutoMode", "No") == "Yes" else False
        self.AutoTimer = True if self.props.get("AutoTimer", "No") == "Yes" else False
        self.first_wort_hop_flag = False 
        self.first_wort_hop=self.props.get("First_Wort", "No")
        self.first_wort_hop_text=self.props.get("First_Wort_text", None)
        self.hops_added=["","","","","",""]
        self.remaining_seconds = None
        self.temparray=np.array([])
        #self.dwelltime=int(self.props.get("DwellTime", 0))*60
        self.dwelltime=5*60 #tested with 5 minutes -> not exactly 5 min due to accuracy of asyncio.sleep
        self.deviationlimit=0.3 # derived from a test

        self.kettle=self.get_kettle(self.props.get("Kettle", None))
        if self.kettle is not None:
            self.kettle.target_temp = int(self.props.get("Temp", 0))

        if self.cbpi.kettle is not None and self.timer is None:
            self.timer = Timer(int(self.props.get("Timer", 0)) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

        elif self.cbpi.kettle is not None:
            try:
                if self.timer.is_running == True:
                    self.timer.start()
            except:
                pass

        self.summary = "Waiting for Target Temp"
        if self.AutoMode == True:
            await self.setAutoMode(True)
        await self.push_update()

    async def check_hop_timer(self, number, value, text):
        if value is not None and self.hops_added[number-1] is not True:
            if self.remaining_seconds != None and self.remaining_seconds <= (int(value) * 60 + 1):
                self.hops_added[number-1]= True
                if text is not None and text != "":
                    self.cbpi.notify('Hop Alert', "Please add %s (%s)" % (text, number), NotificationType.INFO)
                else:
                    self.cbpi.notify('Hop Alert', "Please add Hop %s" % number, NotificationType.INFO)

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        self.kettle.target_temp = 0
        if self.AutoMode == True:
            await self.setAutoMode(False)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.get("Timer", 0)) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        if self.first_wort_hop_flag == False and self.first_wort_hop == "Yes":
            self.first_wort_hop_flag = True
            if self.first_wort_hop_text is not None and self.first_wort_hop_text != "":
                self.cbpi.notify('First Wort Hop Addition!', 'Please add %s for first wort' % self.first_wort_hop_text, NotificationType.INFO)
            else:
                self.cbpi.notify('First Wort Hop Addition!', 'Please add hops for first wort', NotificationType.INFO)

        while self.running == True:

            await asyncio.sleep(1)
            sensor_value = self.get_sensor_value(self.props.get("Sensor", None)).get("value")
            self.temparray = np.append(self.temparray,sensor_value)
            if self.temparray.size > self.dwelltime:
                self.temparray =np.delete(self.temparray,0)
                deviation= np.std(self.temparray)
                if (sensor_value >= self.lid_temp) and (deviation <= self.deviationlimit) and (self.AutoTimer is True) and (self.timer.is_running is not True):
                    self.timer.start()
                    self.timer.is_running = True
                    estimated_completion_time = datetime.fromtimestamp(time.time()+ (int(self.props.get("Timer", 0)))*60)
                    self.cbpi.notify(self.name, 'Timer started automatically. Estimated completion: {}'.format(estimated_completion_time.strftime("%H:%M")), NotificationType.INFO)
            

                logging.info("Current: "+str(sensor_value)+" | Dev: " + str(deviation))
            if self.lid_flag == True and sensor_value >= self.lid_temp:
                self.cbpi.notify("Please remove lid!", "Reached temp close to boiling", NotificationType.INFO)
                self.lid_flag = False

            if sensor_value >= int(self.props.get("Temp", 0)) and self.timer.is_running is not True:
                self.timer.start()
                self.timer.is_running = True
                estimated_completion_time = datetime.fromtimestamp(time.time()+ (int(self.props.get("Timer", 0)))*60)
                self.cbpi.notify(self.name, 'Timer started. Estimated completion: {}'.format(estimated_completion_time.strftime("%H:%M")), NotificationType.INFO)
            else:
                for x in range(1, 6):
                    await self.check_hop_timer(x, self.props.get("Hop_%s" % x, None), self.props.get("Hop_%s_text" % x, None))

        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                await self.cbpi.kettle.toggle(self.kettle.id)
            elif (self.kettle.instance.state == True) and (auto_state is False):
                await self.cbpi.kettle.stop(self.kettle.id)
            await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))

@parameters([Property.Number(label="Timer", description="Time (Default: Minutes)", configurable=True),
    Property.Select(label="TimeUnit",options=["Min","Sec"], description="Specify timer units (Empty: Min)"),
            Property.Actor(label="Actor")])
class BM_ActorStep(CBPiStep):
    async def on_timer_done(self, timer):
        self.summary = ""
        await self.next()

    async def on_timer_update(self, timer, seconds):
        self.summary = Timer.format_time(seconds)
        await self.push_update()

    async def on_start(self):
        self.TimeUnit = 60 if self.props.get("TimeUnit", "Min") == "Min" else 1
        if self.timer is None:
            self.timer = Timer(int(self.props.Timer) * self.TimeUnit, on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.timer.start()
        await self.actor_on(self.props.Actor)

    async def on_stop(self):
        await self.actor_off(self.props.Actor)
        await self.timer.stop()
        self.summary = ""
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.Timer) * self.TimeUnit, on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)
        return StepResult.DONE

def setup(cbpi):
    '''
    This method is called by the server during startup 
    Here you need to register your plugins at the server

    :param cbpi: the cbpi core 
    :return: 
    '''    
    
    cbpi.plugin.register("BM_BoilStep", BM_BoilStep)
    cbpi.plugin.register("BM_Cooldown", BM_Cooldown)
    cbpi.plugin.register("BM_MashInStep", BM_MashInStep)
    cbpi.plugin.register("BM_MashStep", BM_MashStep)
    cbpi.plugin.register("BM_ActorStep", BM_ActorStep)
    cbpi.plugin.register("BM_SimpleStep", BM_SimpleStep)
   
    
    

    
