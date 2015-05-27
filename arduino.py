# Sample Python module to use python plugin 

import collectd
import serial
import os

class ArduinoReadSerial:
   def __init__(self,dataDefinition,shift=2):
      self.plugin_name = 'arduino'
      self.speed = 57600
      self.device = '/dev/ttyUSB1'
      self.ser = None
      self.debug = False
      self.timeout = 1
      self.plugin_instance = None
      self.dataDefinition = dataDefinition
      self.shift = shift
      self.lastValues = {}

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
	    return False

      if not self.ser.isOpen():
         self.ser.open()
         self.log_debug('ArduinoSerial: serial connection is ok')
      self.ser.nonblocking()
      return True

   def isLineOK(self,line):
      lineSize = len(line)
      if lineSize == 0:
         return False
      if not line[0] == 'OK':
         return False
      if not lineSize >= self.shift:
         return False
      return True
    
   def openAndFirstCheck(self):
      if self.open() == False:
	 return False
      bufferInputLen = self.ser.inWaiting()
      if bufferInputLen == 0:
         self.log_debug('empty buffer')
         return False
      self.log_debug('read serial launched : %d bytes waiting in buffer' % self.ser.inWaiting())
      return self.ser.read(bufferInputLen)
    
   def getFormattedLine(self):
      lines = []
      serial_buffer = self.openAndFirstCheck()
      if(serial_buffer == False):
	 return lines
      for line in serial_buffer.split('\n'): 
         line = line.replace('\0','')
         self.log_debug(line)
         if len(line) == 0:
            continue
         lineSplitted = filter(None,line.strip().split(' '))
         if not self.isLineOK(lineSplitted):
            continue
	 lines.append(lineSplitted)
      return lines

   def read_serial_bytes(self):
      values = {}
      for lineSplitted in self.getFormattedLine():
	 try:
	    bytesLine = bytearray(map(lambda x: int(x),lineSplitted[self.shift:]))
	 except ValueError as ve:
	    self.log_warning(str(ve))
	    continue
         line = (str(lineSplitted[1]) + ' ' + str(bytesLine)).replace('\0','')
         lineSplitted = line.split()
         self.log_debug(line)
         self.add_values(lineSplitted,values)
      if len(values) == 0:
         values = self.lastValues
      else:
         self.lastValues = values
      self.dispatch(values)
      return

   def add_values(self,lineSplitted,values):
      lineSplittedSize = len(lineSplitted)
      # check that node number exist in dataDefinition
      if lineSplitted[0] not in self.dataDefinition:
	 self.log_warning('node number %s not in data definition' % (lineSplitted[0]))
	 return
      dataToGet = self.dataDefinition[lineSplitted[0]]
      for key in dataToGet.keys():
         position = dataToGet[key]
         if not lineSplittedSize >= (position + 1):
            continue
         if not key in values:
            values[key] = []
         try:
            values[key].append(int(lineSplitted[position]))
         except ValueError as ve:
            self.log_warning(str(ve))

   def dispatch(self,values):
      self.lastValues = values
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


# name and postion of the data to get from every line read from ttyUSB
# it must contains the node number and the data for this node number
# exemple: dataDefinition = { '2' : { 'tension':2 } ,
#                             '3' : { 'temperature':1 }
#                           } 
#          lines = OK 2 3 4
#                  OK 3 30
#          tension will be 4
#          temperature will be 30

dataDefinition = { '2' : {'Puissance apparente':2, 'Heures Creuses':3, 'Heures pleines':4, 'tension':5, 'Compteur production':7, 'RAM libre':8 } }
arduino = ArduinoReadSerial(dataDefinition)
#== Hook Callbacks, Order is important! ==#
collectd.register_config(arduino.config,name=arduino.plugin_name)
collectd.register_init(arduino.init)
collectd.register_read(arduino.read_serial_bytes)

