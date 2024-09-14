from . import bus
from .. import configfile


'''
[esp_mmu]
spi_bus: spi2
cs_pin: gpio10
'''

ESPMMU_CHIP_ADDR = 0x96
REG_MOD_READ = 0x80

REG_VERSION     = 0x00 # ro
REG_LANE_COUNT  = 0x01 # ro
REG_ACTIVE_LANE = 0x02 # rw
REG_LANE_ID     = 0x03 # ro
REG_LANE_ACTION = 0x04 # rw
REG_LANE_STATUS = 0x05 # ro

ACTION_STOP   = 0x00
ACTION_LOAD   = 0x01
ACTION_UNLOAD = 0x02
ACTION_TBD    = 0x03

STATUS_FILAMENT_ACTION_OFFSET  = 0b00000000 >> 1
STATUS_FILAMENT_ACTION_SIZE    = 0b00000011 >> STATUS_FILAMENT_ACTION_OFFSET
STATUS_FILAMENT_PRESENT_OFFSET = 0b00000100 >> 1
STATUS_FILAMENT_PRESENT_SIZE   = 0b00000100 >> STATUS_FILAMENT_PRESENT_OFFSET

# present = (status >> STATUS_FILAMENT_ACTION_OFFSET) & STATUS_FILAMENT_ACTION_SIZE
# present = (status >> STATUS_FILAMENT_PRESENT_OFFSET) & STATUS_FILAMENT_PRESENT_SIZE

class EspMMU:
    def __init__(self, config: configfile.ConfigWrapper):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.spi = bus.MCU_SPI_from_config(config, 3, default_speed=5000000)
        self.mcu = self.spi.get_mcu()

    def _read_lane_count(self):
        return self.read_reg(REG_LANE_COUNT)
    
    def _read_lane_id(self, lane):
        self._select_lane(lane)
        return self.read_reg(REG_LANE_ID)
    
    def _read_active_lane(self):
        return self.read_reg(REG_ACTIVE_LANE)
    
    def _select_lane(self, lane):
        self.set_reg(REG_ACTIVE_LANE, lane)
    
    def _unload_lane(self, lane):
        self._select_lane(lane)
        self.set_reg(REG_LANE_ACTION, ACTION_UNLOAD)
        return
    
    def _load_lane(self, lane):
        self._select_lane(lane)
        self.set_reg(REG_LANE_ACTION, ACTION_LOAD)
        return
    
    def _stop_lane(self, lane):
        self._select_lane(lane)
        self.set_reg(REG_LANE_ACTION, ACTION_STOP)
        return
    
    def read_reg(self, reg):
        params = self.spi.spi_transfer([reg | REG_MOD_READ, 0x00])
        response = bytearray(params['response'])
        return response[1]

    def set_reg(self, reg, val, minclock=0):
        self.spi.spi_send([reg, val & 0xFF], minclock=minclock)
        stored_val = self.read_reg(reg)
        if stored_val != val:
            raise self.printer.command_error(
                    "Failed to set ADXL345 register [0x%x] to 0x%x: got 0x%x. "
                    "This is generally indicative of connection problems "
                    "(e.g. faulty wiring) or a faulty adxl345 chip." % (
                        reg, val, stored_val))