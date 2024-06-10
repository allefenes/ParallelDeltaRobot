from dynamixel_sdk import *
import time
import numpy as np

class Dynamixel():

    def __init__(self,BAUDRATE=1000000, DEVICENAME='COM3', PROTOCOL_VERSION=1.0, DXL_ID=[1,2,3]):
        
        self.ADDR_LED = 25
        self.ADDR_TEMPERATURE = 43
        self.ADDR_PRESENT_POSITION = 36
        self.ADDR_PRESENT_LOAD = 40
        self.ADDR_MOVING = 46
        self.ADDR_PRESENT_VOLTAGE = 42
        self.ADDR_GOAL_POSITION = 30
        self.ADDR_CCW_COMPLIANCE_SLOPE = 29
        self.ADDR_CCW_COMPLIANCE_MARGIN = 27
        self.ADDR_CW_COMPLIANCE_MARGIN = 26
        self.ADDR_CW_COMPLIANCE_SLOPE = 28
        self.ADDR_PUNCH = 48
        self.ADDR_TORQUE = 24

        self.PROTOCOL_VERSION        = PROTOCOL_VERSION

        self.DXL_ID                  = DXL_ID
        self.BAUDRATE                = BAUDRATE
        self.DEVICENAME              = DEVICENAME
        

    def connect(self):
        self.portHandler = PortHandler(self.DEVICENAME)
        self.packetHandler = PacketHandler(self.PROTOCOL_VERSION)

        if self.portHandler.openPort():
            print("Succeeded to open the port")
        else:
            print("Failed to open the port")
            print("Press any key to terminate...")
            getch()
            quit()
        
        if self.portHandler.setBaudRate(self.BAUDRATE):
            print("Succeeded to change the baudrate")
        else:
            print("Failed to change the baudrate")
            print("Press any key to terminate...")
            getch()
            quit()

    def disconnect(self):
        self.portHandler.closePort()

    def ping(self):
        for id in self.DXL_ID:
            dxl_model_number, dxl_comm_result, dxl_error = self.packetHandler.ping(self.portHandler, id)
            
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                print("%s" % self.packetHandler.getRxPacketError(dxl_error))
            else:
                print("[ID:%03d] ping Succeeded. Dynamixel model number : %d" % (id, dxl_model_number))

    def readTemperature(self,id):
        dxl_temperature, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, id, self.ADDR_TEMPERATURE)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_temperature

    def readPresentPosition(self, id):
        dxl_present_position, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, id, self.ADDR_PRESENT_POSITION)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_present_position

    def readPresentLoad(self, id):
        dxl_present_load, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, id, self.ADDR_PRESENT_LOAD)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_present_load
     
    def readMoving(self, id):
        dxl_moving, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, id, self.ADDR_MOVING)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_moving

    def readPresentVoltage(self, id):
        dxl_present_voltage, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, id, self.ADDR_PRESENT_VOLTAGE)
        dxl_present_voltage = dxl_present_voltage / 10 

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_present_voltage

    def led(self,id,state='off'):
        if state == 'off':
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_LED,0) 
        elif state == 'on':
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_LED,1)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def writeGoalPosition(self,id,raw):
        dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler,id,self.ADDR_GOAL_POSITION,raw)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def writeComplianceSlope(self,id,slope=254):
        """
        A : CCW Compliance Slope
        
        and 

        D : CW Compliance Slope
        """
        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_CCW_COMPLIANCE_SLOPE,slope)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def readComplianceSlope(self,id):
        dxl_slope, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler,id,self.ADDR_CCW_COMPLIANCE_SLOPE)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_slope

    def writeComplianceMargin(self,id,margin=1):
        """
        B : CCW Compliance Margin

        and

        C : CW Compliance Margin
        """
        if margin > 254:
            print("Too big margin!")
            return

        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_CCW_COMPLIANCE_MARGIN,margin)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_CW_COMPLIANCE_MARGIN,margin)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def readComplianceMargin(self,id):
        dxl_margin, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler,id,self.ADDR_CCW_COMPLIANCE_MARGIN)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))
        
        return dxl_margin

    def writePunch(self, id, current=0):
        """
        E : Punch
        """
        if current > 16 and current < 1024:
            print('Wrong Current Value!')

        dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler,id,self.ADDR_PUNCH,current)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def readPunch(self, id):
        dxl_punch, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler,id,self.ADDR_PUNCH)
        
        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

        return dxl_punch

    def torque(self, id, state='off'):
        if state == 'off':
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_TORQUE,0)
        elif state =='on':
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler,id,self.ADDR_TORQUE,1)

        if dxl_comm_result != COMM_SUCCESS:
            print("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
        elif dxl_error != 0:
            print("%s" % self.packetHandler.getRxPacketError(dxl_error))

    def syncWrite(self, plan = [], threshold = 5, timeout = 0.04):
        time.sleep(0.5)
        index = 0
        satirSayisi, sutunSayisi = np.shape(plan)
        sifirinci_sutun_degerleri = tuple(int((-row[0]+150)*(1023/300)) for row in plan)
        birinci_sutun_degerleri = tuple(int((-row[1]+150)*(1023/300)) for row in plan)
        ikinci_sutun_degerleri = tuple(int((-row[2]+150)*(1023/300)) for row in plan)
        dxl1_goal_position = tuple(sifirinci_sutun_degerleri)
        dxl2_goal_position = tuple(birinci_sutun_degerleri)
        dxl3_goal_position = tuple(ikinci_sutun_degerleri)

        groupSyncWrite = GroupSyncWrite(self.portHandler, self.packetHandler, self.ADDR_GOAL_POSITION, 4)

        self.torque(1,'on')
        self.torque(2,'on')
        self.torque(3,'on')

        while 1:

            param1_goal_position = [DXL_LOBYTE(DXL_LOWORD(dxl1_goal_position[index])), DXL_HIBYTE(DXL_LOWORD(dxl1_goal_position[index])), DXL_LOBYTE(DXL_HIWORD(dxl1_goal_position[index])), DXL_HIBYTE(DXL_HIWORD(dxl1_goal_position[index]))]
            param2_goal_position = [DXL_LOBYTE(DXL_LOWORD(dxl2_goal_position[index])), DXL_HIBYTE(DXL_LOWORD(dxl2_goal_position[index])), DXL_LOBYTE(DXL_HIWORD(dxl2_goal_position[index])), DXL_HIBYTE(DXL_HIWORD(dxl2_goal_position[index]))]
            param3_goal_position = [DXL_LOBYTE(DXL_LOWORD(dxl3_goal_position[index])), DXL_HIBYTE(DXL_LOWORD(dxl3_goal_position[index])), DXL_LOBYTE(DXL_HIWORD(dxl3_goal_position[index])), DXL_HIBYTE(DXL_HIWORD(dxl3_goal_position[index]))]


            dxl_addparam_result = groupSyncWrite.addParam(1, param1_goal_position)
            if dxl_addparam_result != True:
                print("[ID:%03d] groupSyncWrite addparam failed" % 1)

            dxl_addparam_result = groupSyncWrite.addParam(2, param2_goal_position)
            if dxl_addparam_result != True:
                print("[ID:%03d] groupSyncWrite addparam failed" % 2)

            dxl_addparam_result = groupSyncWrite.addParam(3, param3_goal_position)
            if dxl_addparam_result != True:
                print("[ID:%03d] groupSyncWrite addparam failed" % 3)

            dxl_comm_result = groupSyncWrite.txPacket()
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % packetHandler.getTxRxResult(dxl_comm_result))

            dxl_comm_result = groupSyncWrite.txPacket()
            if dxl_comm_result != COMM_SUCCESS:
                print("%s" % packetHandler.getTxRxResult(dxl_comm_result))

            startTime = time.time()
            while True:
                dxl1_present_position = self.readPresentPosition(1)
                dxl2_present_position = self.readPresentPosition(2)
                dxl3_present_position = self.readPresentPosition(3)

                print("[ID:%03d] GoalPos:%03d  PresPos:%03d\t[ID:%03d] GoalPos:%03d  PresPos:%03d\t[ID:%03d] GoalPos:%03d  PresPos:%03d" % (1, dxl1_goal_position[index], dxl1_present_position, 2, dxl2_goal_position[index], dxl2_present_position, 3, dxl3_goal_position[index], dxl3_present_position))
                currTime = time.time()
                elapsedTime = currTime - startTime
                if elapsedTime > timeout:
                    break
                if not ((abs(dxl1_goal_position[index] - dxl1_present_position) > threshold) and (abs(dxl2_goal_position[index] - dxl2_present_position) > threshold) and (abs(dxl3_goal_position[index] - dxl3_present_position) > threshold)):
                    break


            groupSyncWrite.clearParam()

            if index == satirSayisi-1:
                break
            else:
                index += 1

        self.portHandler.closePort()