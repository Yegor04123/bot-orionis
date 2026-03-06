import socket
import struct
import time
from typing import Optional


class RconClient:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
        self.auth = False

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.auth = self._authenticate()
            return self.auth
        except (socket.error, ConnectionRefusedError) as e:
            print(f"RCON connection error: {e}")
            self.socket = None
            return False

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.auth = False

    def send_command(self, command: str) -> Optional[str]:
        if not self.auth or not self.socket:
            if not self.connect():
                return None

        try:
            self._send_packet(2, command)
            response_type, response_id, response_body = self._receive_packet()

            if response_type == 0:
                return response_body
            else:
                return None
        except Exception as e:
            print(f"RCON command error: {e}")
            self.disconnect()
            return None

    def _authenticate(self) -> bool:
        if not self.socket:
            return False

        try:
            # Send auth packet with password
            self._send_packet(3, self.password)
            response_type, response_id, response_body = self._receive_packet()

            return response_id != -1
        except Exception as e:
            print(f"RCON authentication error: {e}")
            return False

    def _send_packet(self, packet_type: int, packet_body: str) -> None:
        # Packet structure: ID (4) + Type (4) + Body + null terminator (1) + null terminator (1)
        packet_id = 0
        packet = struct.pack('<ii', packet_id, packet_type) + packet_body.encode('utf8') + b'\x00\x00'
        packet_length = len(packet)

        self.socket.sendall(struct.pack('<i', packet_length) + packet)

    def _receive_packet(self):
        # Read packet length
        packet_length_data = self._receive_all(4)
        if not packet_length_data:
            raise ConnectionError("RCON connection lost while receiving packet length")

        packet_length = struct.unpack('<i', packet_length_data)[0]

        # Read packet content
        packet_data = self._receive_all(packet_length)
        if not packet_data:
            raise ConnectionError("RCON connection lost while receiving packet data")

        # Extract packet components
        packet_id = struct.unpack('<i', packet_data[0:4])[0]
        packet_type = struct.unpack('<i', packet_data[4:8])[0]

        # Extract body (remove the two null terminators)
        packet_body = packet_data[8:-2].decode('utf8')

        return packet_type, packet_id, packet_body

    def _receive_all(self, length: int) -> bytes:
        data = b''
        while len(data) < length:
            packet = self.socket.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return data

    def add_to_whitelist(self, minecraft_nickname: str) -> bool:
        response = self.send_command(f"whitelist add {minecraft_nickname}")
        return response is not None and "to the white list" in response