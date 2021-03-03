
import asyncio
import aiohttp
from aiohttp import web
from cbpi.api.step import CBPiStep, StepResult
from cbpi.api.timer import Timer
from cbpi.api.dataclasses import Kettle, Props
import datetime
import time
from cbpi.api import *
import logging

@parameters([Property.Text(label="Notification",configurable = True, description = "Text for notification")])

class BM_SimpleStep(CBPiStep):

    async def on_timer_done(self,timer):
        self.summary = self.props.Notification
        self.cbpi.notify(self.props.Notification)
        await self.push_update()

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.timer.start()
        await self.push_update()

    async def on_stop(self):
        self.timer.stop()
        self.summary = ""
        await self.push_update()

    async def run(self):
        while True:
           await asyncio.sleep(1)
        return StepResult.DONE

@parameters([Property.Number(label="Temp", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle")])

class BM_MashInStep(CBPiStep):

    async def on_timer_done(self,timer):
        self.summary = "MashIn Temp reached. Please add Malt Pipe and malt. Press 'Start Mashing'"
        self.cbpi.notify("MashIn Temp reached. Please add Malt Pipe and malt. Press 'Start Mashing'")
        await self.push_update()
        await self.setAutoMode(False)

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.kettle=self.get_kettle(self.props.Kettle)
        self.kettle.target_temp = int(self.props.Temp)
        await self.setAutoMode(True)
        self.summary = "Waiting for Target Temp"
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def on_stop(self):
        self.timer.stop()
        self.summary = ""
        await self.setAutoMode(False)
        await self.push_update()

    async def run(self):
        while True:
           await asyncio.sleep(1)
           sensor_value = self.get_sensor_value(self.props.Sensor).get("value")
           if sensor_value >= int(self.props.Temp) and self.timer._task == None:
               self.timer.start()
        await self.push_update()
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            #todo: get port from config
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                url="http://127.0.0.1:8000/kettle/"+ self.kettle.id+"/toggle"
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
             Property.Kettle(label="Kettle")])
class BM_MashStep(CBPiStep):

    @action("Start Timer", [])
    async def star_timer(self):
        self.cbpi.notify("Timer started")
        self.timer.start()
        
    async def on_timer_done(self,timer):
        self.summary = ""
        await self.setAutoMode(False)
        await self.next()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        await self.push_update()

    async def on_start(self):
        self.kettle=self.get_kettle(self.props.Kettle)
        self.kettle.target_temp = int(self.props.Temp)
        await self.setAutoMode(True)
        await self.push_update()

        if self.timer is None:
            self.timer = Timer(int(self.props.Timer) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.summary = "Waiting for Target Temp"
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        await self.setAutoMode(False)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.Timer) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        while True:
            await asyncio.sleep(1)
            sensor_value = self.get_sensor_value(self.props.Sensor).get("value")
            if sensor_value >= int(self.props.Temp) and self.timer._task == None:
                self.timer.start()
                self.cbpi.notify("Timer started")
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            #todo: get port from config
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                url="http://127.0.0.1:8000/kettle/"+ self.kettle.id+"/toggle"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url) as response:
                        return await response.text()
                        await self.push_update()
            elif (self.kettle.instance.state == True) and (auto_state is False):

                await self.kettle.instance.stop()
                await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))


@parameters([Property.Number(label="Temp", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle")])
class BM_Cooldown(CBPiStep):

    async def on_timer_done(self,timer):
        self.summary = ""
        self.cbpi.notify("Wort cooled down. Please transfer to Fermenter.")
        await self.next()

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.kettle = self.get_kettle(self.props.Kettle)
        self.target_temp= int(self.props.Temp)
        self.summary="Cool down to {}°".format(self.target_temp)
        self.cbpi.notify("Cool down to {}°".format(self.target_temp))
        if self.timer is None:
            self.timer = Timer(1,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        await self.push_update()

    async def reset(self):
        self.timer = Timer(1,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):
        while True:
            if self.get_sensor_value(self.props.Sensor).get("value") <= self.target_temp:
                self.timer.start()
            await asyncio.sleep(1)
        return StepResult.DONE

@parameters([Property.Number(label="Timer", description="Time in Minutes", configurable=True),
                Property.Actor(label="Actor")])
class BM_ActorStep(CBPiStep):
    async def on_timer_done(self,timer):
        self.summary = ""
        await self.next()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        await self.push_update()

    async def on_start(self):
        if self.timer is None:
            self.timer = Timer(int(self.props.Timer) * 60,on_update=self.on_timer_update, on_done=self.on_timer_done)
        self.timer.start()
        await self.actor_on(self.props.Actor)

    async def on_stop(self):
        await self.actor_off(self.props.Actor)
        await self.timer.stop()
        self.summary = ""
        await self.push_update()
        
    async def reset(self):
        self.timer = Timer(int(self.props.Timer) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    async def run(self):

        while True:
            await asyncio.sleep(1)
        return StepResult.DONE


@parameters([Property.Number(label="Timer", description="Time in Minutes", configurable=True), 
             Property.Number(label="Temp", description="Boil temperature", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle"),
             Property.Select("First_Wort", options=["Yes","No"], description="First Wort Hop alert if set to Yes"),
             Property.Number("Hop_1", configurable = True, description="First Hop alert (minutes before finish)"),
             Property.Number("Hop_2", configurable=True, description="Second Hop alert (minutes before finish)"),
             Property.Number("Hop_3", configurable=True, description="Third Hop alert (minutes before finish)"),
             Property.Number("Hop_4", configurable=True, description="Fourth Hop alert (minutes before finish)"),
             Property.Number("Hop_5", configurable=True, description="Fifth Hop alert (minutes before finish)")])

class BM_BoilStep(CBPiStep):

    async def on_timer_done(self,timer):
        self.summary = ""
        self.kettle.target_temp = 0
        await self.setAutoMode(False)
        await self.next()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        self.remaining_seconds = seconds
        await self.push_update()

    async def on_start(self):
        self.first_wort_hop_flag = False 
        self.first_wort_hop=self.props.First_Wort 
        self.hops_added=["","","","",""]
        self.remaining_seconds = None

        self.kettle=self.get_kettle(self.props.Kettle)
        self.kettle.target_temp = int(self.props.Temp)

        if self.timer is None:
            self.timer = Timer(int(self.props.Timer) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

        self.summary = "Waiting for Target Temp"
        await self.setAutoMode(True)
        await self.push_update()

    async def check_hop_timer(self, number, value):
        if value is not None and self.hops_added[number-1] is not True:
            if self.remaining_seconds != None and self.remaining_seconds <= (int(value) * 60 + 1):
                self.hops_added[number-1]= True
                self.cbpi.notify("Hop Alert. Please add Hop %s" % number, timeout = None)

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        self.kettle.target_temp = 0
        await self.setAutoMode(False)
        await self.push_update()

    async def reset(self):
        self.timer = Timer(int(self.props.Timer) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

    @action("Start Timer", [])
    async def start_timer(self):
        self.cbpi.notify("Timer started")
        self.timer.start()

    async def run(self):
        if self.first_wort_hop_flag == False and self.first_wort_hop == "Yes":
            self.first_wort_hop_flag = True
            self.cbpi.notify("First Wort Hop Addition! Please add hops for first wort")

        while True:
            await asyncio.sleep(1)
            sensor_value = self.get_sensor_value(self.props.Sensor)
            if sensor_value is not None and sensor_value.get("value") >= int(self.props.Temp) and self.timer._task == None:
                self.timer.start()
            else:
                await self.check_hop_timer(1, self.props.Hop_1)
                await self.check_hop_timer(2, self.props.Hop_2)
                await self.check_hop_timer(3, self.props.Hop_3)
                await self.check_hop_timer(4, self.props.Hop_4)
                await self.check_hop_timer(5, self.props.Hop_5)
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            #todo: get port from config
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                url="http://127.0.0.1:8000/kettle/"+ self.kettle.id+"/toggle"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url) as response:
                       return await response.text()
            elif (self.kettle.instance.state == True) and (auto_state is False):
                await self.kettle.instance.stop()
                await self.push_update

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))


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
   
    
    

    
