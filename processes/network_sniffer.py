import os
import subprocess
import time
import platform
from datetime import datetime
from typing import List, Set, Dict

from gabru.process import Process
from services.network_signatures import NetworkSignatureService
from services.events import EventService
from model.event import Event
from model.network_signature import NetworkSignature

class NetworkSniffer(Process):
    """
    Simplified Network Sniffer.
    Monitors device presence on the local network using MAC addresses.
    Uses 'arp-scan' (Linux/Pi) or 'arp -a' (macOS) to detect devices.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sig_service = NetworkSignatureService()
        self.event_service = EventService()
        self.last_seen: Dict[int, float] = {}  # {sig_id: timestamp}
        self.cooldown = 60  # 1 minute cooldown per signature
        self.is_mac_os = platform.system() == "Darwin"
        self.active_sigs: List[NetworkSignature] = []
        self.last_db_refresh = 0

    def process(self):
        """Main loop called by the Gabru ProcessManager."""
        self.log.info(f"Network Sniffer (MAC Only) started on {platform.system()}")
        
        while self.running:
            try:
                # 1. Respect the 'is_active' toggle from the UI
                if not self.enabled:
                    time.sleep(10)
                    continue

                # 2. Refresh active signatures from DB every 60 seconds
                now = time.time()
                if now - self.last_db_refresh > 60:
                    self.active_sigs = self.sig_service.find_all(filters={"is_active": True})
                    self.last_db_refresh = now
                    self.log.debug(f"Refreshed {len(self.active_sigs)} active network signatures.")

                if not self.active_sigs:
                    time.sleep(30)
                    continue

                # 3. Scan the local network for active MAC addresses
                active_macs = self._scan_presence()
                self.log.debug(f"Scan complete. Found {len(active_macs)} devices.")

                # 4. Match signatures to found MACs
                for sig in self.active_sigs:
                    mac_to_check = sig.mac_address.lower().strip()
                    if mac_to_check in active_macs:
                        if self._should_trigger(sig):
                            self._trigger_event(sig)

                # Scan every 5 seconds
                time.sleep(5)
                
            except Exception as e:
                self.log.error(f"Error in NetworkSniffer: {e}", exc_info=True)
                time.sleep(60)

    def _scan_presence(self) -> Set[str]:
        """Discovers active MAC addresses on the local network."""
        active_macs = set()
        
        # Strategy A: arp-scan (Best for Pi/Linux)
        try:
            # We try a few common interface names or just localnet
            cmd = ['sudo', 'arp-scan', '--localnet', '--retry=1', '--timeout=500']
            if self.is_mac_os:
                # On Mac, en0 is usually Wi-Fi
                cmd = ['sudo', 'arp-scan', '-I', 'en0', '--localnet']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        mac = parts[1].lower()
                        if len(mac) == 17 and mac.count(':') == 5:
                            active_macs.add(mac)
        except Exception:
            pass

        # Strategy B: arp -a (Fallback for Mac and generic systems)
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                # Format varies, but we extract anything that looks like a MAC
                parts = line.split()
                for p in parts:
                    clean_p = p.lower().strip('()[]')
                    # Standard 17-char MAC (00:11:22:33:44:55)
                    if len(clean_p) == 17 and clean_p.count(':') == 5:
                        active_macs.add(clean_p)
                    # Mac short-format (0:1:2:3:4:5)
                    elif ':' in clean_p and 12 <= len(clean_p) <= 17:
                        normalized = ":".join([x.zfill(2) for x in clean_p.split(':')])
                        if len(normalized) == 17:
                            active_macs.add(normalized)
        except Exception as e:
            self.log.debug(f"ARP fallback scan failed: {e}")

        return active_macs

    def _should_trigger(self, sig: NetworkSignature) -> bool:
        """Check 1-hour cooldown to prevent event spam."""
        now = time.time()
        last_time = self.last_seen.get(sig.id, 0)
        
        if (now - last_time) > self.cooldown:
            self.last_seen[sig.id] = now
            return True
        return False

    def _trigger_event(self, sig: NetworkSignature):
        """Creates a new entry in the Event timeline."""
        self.log.info(f"MATCH: Found {sig.name} ({sig.mac_address}). Triggering event.")
        try:
            new_event = Event(
                user_id=sig.user_id,
                event_type=sig.event_type,
                timestamp=datetime.now(),
                description=f"Network activity detected from {sig.name}",
                tags=sig.tags
            )
            self.event_service.create(new_event)
        except Exception as e:
            self.log.error(f"Failed to save network event: {e}")
