# Sample Python module to use python plugin 

import collectd
import serial
import os

class ArduinoReadSerial:
   def __init__(self,dataToGet,shift=2):
      self.plugin_name = 'arduino'
      self.speed = 57600
      self.device = '/dev/ttyUSB0'
      self.ser = None
      self.debug = False
      self.timeout = 1
      self.plugin_instance = None
      self.dataToGet = dataToGet
      self.shift = shift

   def config(self, obj):
      for child in obj.children:
         if child.key == 'Debug' and child.values[0] == True:
            self.debug = True
         elif child.key == 'SerialDevice':
            self.device = child.values[0]
         elif child.key == 'SerialSpeed':
            self.speed = int(child.values[0])
      collectd.info('ArduinoSerial: configuration')


   def init(self):
      self.open()
   
   def log_warning(self,msg):
      collectd.warning('%s: %s' % (self.plugin_name,str(msg)))

   def log_debug(self,msg):
      if self.debug == False:
         return
      collectd.info('%s: %s' % (self.plugin_name,str(msg)))

   def open(self):
      if not os.path.exists(self.device):
         self.log_warning('device %s not found')
         return False
      if self.ser == None: 
         try:
            self.log_debug('ArduinoSerial: ' +
                    'trying to connect to %s with speed %s' %
                    (self.device, self.speed))
            self.ser = serial.Serial(self.device,
                                     self.speed,
                                     timeout=self.timeout)
         except:
            self.log_warning('error on the serial device %s with the speed %d' %
                (self.device, self.speed))

      if not self.ser.isOpen():
         self.ser.open()
         self.log_debug('ArduinoSerial: serial connection is ok')
      self.log_debug('serial already opened')
      self.ser.nonblocking()
 
   def read_serial(self):
      self.open()
      bufferInputLen = self.ser.inWaiting()
      if bufferInputLen == 0:
         self.log_debug('empty buffer')
         return
      self.log_debug('read serial launched : %d bytes waiting in buffer' % self.ser.inWaiting())
      values = {}
      byteRead = self.ser.read(bufferInputLen)
      for line in byteRead.split('\n'): 
         self.log_debug(line.replace('\0',''))
         if len(line) == 0:
            continue
         lineSplitted = filter(None,line.strip().split(' '))
         lineSplittedSize = len(lineSplitted)
         if lineSplittedSize == 0:
            continue
         if not lineSplitted[0] == 'OK':
            continue
         if not lineSplittedSize >= self.shift:
            continue
         lineSplitted = lineSplitted[self.shift:]
         for key in self.dataToGet.keys():
            position = self.dataToGet[key]
            if not lineSplittedSize >= position:
               continue
            self.add_values(values,key,lineSplitted[position - 1])
      self.dispatch(values)
      return

   def add_values(self,values,key,value):
      if not key in values:
         values[key] = []
      values[key].append(int(value))

   def dispatch(self,values):
      for key,value in values.iteritems():
         if len(value) == 0:
            return
         self.log_debug((key,value))
         metric = collectd.Values();
         metric.plugin = self.plugin_name
         metric.plugin_instance = key
         metric.type = 'gauge'
         metric.type_instance = key
         metric.values = [reduce(lambda x, y: x + y,value) / len(value)]
         metric.dispatch()       

dataToGet = { 'tension': 1 }
arduino = ArduinoReadSerial(dataToGet)
#== Hook Callbacks, Order is important! ==#
collectd.register_config(arduino.config,name=arduino.plugin_name)
collectd.register_init(arduino.init)
collectd.register_read(arduino.read_serial)

