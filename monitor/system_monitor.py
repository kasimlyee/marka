import os
import platform
import time
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from threading import Thread, Event
from collections import deque
import psutil
import GPUtil
from dataclasses import dataclass
from enum import Enum

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    type: str
    level: AlertLevel
    message: str
    timestamp: str

class SystemMonitor:
    """Monitors system resources and performance metrics."""
    
    def __init__(self, options: Optional[Dict] = None):
        """
        Initialize the SystemMonitor with configuration options.
        
        Args:
            options: Dictionary of configuration options including:
                - monitoring_interval: Interval in seconds between checks
                - max_history: Maximum number of historical metrics to keep
                - cpu_threshold: CPU usage percentage threshold for alerts
                - memory_threshold: Memory usage percentage threshold for alerts
                - disk_threshold: Disk usage percentage threshold for alerts
        """
        self.options = {
            'monitoring_interval': 5,
            'max_history': 60,
            'cpu_threshold': 80,
            'memory_threshold': 80,
            'disk_threshold': 90,
            **(options or {})
        }
        
        self.monitoring_thread = None
        self.stop_event = Event()
        self.metrics_history = {
            'cpu': deque(maxlen=self.options['max_history']),
            'memory': deque(maxlen=self.options['max_history']),
            'disk': deque(maxlen=self.options['max_history'])
        }
        self.alerts = deque(maxlen=100)  # Keep last 100 alerts
        self.system_info = None
        self.logger = logging.getLogger('marka.system_monitor')
        
    def start(self) -> None:
        """Start the system monitoring."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.logger.warning('Monitoring already running')
            return
            
        # Get initial system info
        self.system_info = self.get_system_info()
        
        # Start monitoring thread
        self.stop_event.clear()
        self.monitoring_thread = Thread(
            target=self._monitoring_loop,
            daemon=True,
            name='SystemMonitor'
        )
        self.monitoring_thread.start()
        self.logger.info('System monitoring started')
        
    def stop(self) -> None:
        """Stop the system monitoring."""
        if not self.monitoring_thread or not self.monitoring_thread.is_alive():
            self.logger.warning('Monitoring not running')
            return
            
        self.stop_event.set()
        self.monitoring_thread.join(timeout=5)
        self.logger.info('System monitoring stopped')
        
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self.stop_event.is_set():
            try:
                metrics = self.get_performance_metrics()
                
                # Store metrics in history
                self._store_metric('cpu', metrics['cpu']['usage'])
                self._store_metric('memory', metrics['memory']['usage'])
                self._store_metric('disk', metrics['disk']['usage'])
                
                # Check for threshold alerts
                self._check_thresholds(metrics)
                
            except Exception as e:
                self.logger.error(f'Error in monitoring loop: {str(e)}')
                
            time.sleep(self.options['monitoring_interval'])
            
    def _store_metric(self, metric_type: str, value: float) -> None:
        """Store a metric in history."""
        self.metrics_history[metric_type].append({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })
        
    def _check_thresholds(self, metrics: Dict) -> None:
        """Check metrics against configured thresholds."""
        timestamp = datetime.now().isoformat()
        
        # CPU threshold check
        if metrics['cpu']['usage'] > self.options['cpu_threshold']:
            alert = Alert(
                type='cpu',
                level=AlertLevel.WARNING,
                message=f'High CPU usage: {metrics["cpu"]["usage"]:.1f}%',
                timestamp=timestamp
            )
            self._add_alert(alert)
            
        # Memory threshold check
        if metrics['memory']['usage'] > self.options['memory_threshold']:
            alert = Alert(
                type='memory',
                level=AlertLevel.WARNING,
                message=f'High memory usage: {metrics["memory"]["usage"]:.1f}%',
                timestamp=timestamp
            )
            self._add_alert(alert)
            
        # Disk threshold check
        if metrics['disk']['usage'] > self.options['disk_threshold']:
            alert = Alert(
                type='disk',
                level=AlertLevel.WARNING,
                message=f'High disk usage: {metrics["disk"]["usage"]:.1f}%',
                timestamp=timestamp
            )
            self._add_alert(alert)
            
    def _add_alert(self, alert: Alert) -> None:
        """Add an alert to the alerts queue."""
        self.alerts.append(alert)
        self.logger.warning(f'Alert: {alert.message}')
        
    def get_system_info(self) -> Dict:
        """Get static system information."""
        try:
            cpu_info = self._get_cpu_info()
            memory_info = self._get_memory_info()
            disk_info = self._get_disk_info()
            os_info = self._get_os_info()
            
            return {
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'os': os_info,
                'hostname': platform.node(),
                'uptime': int(time.time() - psutil.boot_time())
            }
        except Exception as e:
            self.logger.error(f'Failed to get system info: {str(e)}')
            raise
            
    def _get_cpu_info(self) -> Dict:
        """Get CPU information."""
        cpu_freq = psutil.cpu_freq()
        return {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'max_frequency': cpu_freq.max if cpu_freq else None,
            'min_frequency': cpu_freq.min if cpu_freq else None,
            'architecture': platform.machine(),
            'brand': platform.processor()
        }
        
    def _get_memory_info(self) -> Dict:
        """Get memory information."""
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'unit': 'bytes'
        }
        
    def _get_disk_info(self) -> List[Dict]:
        """Get disk information."""
        disks = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except Exception:
                continue
        return disks
        
    def _get_os_info(self) -> Dict:
        """Get OS information."""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.architecture()[0]
        }
        
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics."""
        try:
            cpu_metrics = self._get_cpu_metrics()
            memory_metrics = self._get_memory_metrics()
            disk_metrics = self._get_disk_metrics()
            process_metrics = self._get_process_metrics()
            
            return {
                'cpu': cpu_metrics,
                'memory': memory_metrics,
                'disk': disk_metrics,
                'processes': process_metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f'Failed to get performance metrics: {str(e)}')
            raise
            
    def _get_cpu_metrics(self) -> Dict:
        """Get CPU metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_times = psutil.cpu_times_percent(interval=1)
        
        return {
            'usage': cpu_percent,
            'user': cpu_times.user,
            'system': cpu_times.system,
            'idle': cpu_times.idle
        }
        
    def _get_memory_metrics(self) -> Dict:
        """Get memory metrics."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'free': mem.free,
            'percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free,
            'swap_percent': swap.percent
        }
        
    def _get_disk_metrics(self) -> Dict:
        """Get disk metrics."""
        disk_io = psutil.disk_io_counters()
        partitions = []
        
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except Exception:
                continue
                
        return {
            'partitions': partitions,
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0,
            'read_count': disk_io.read_count if disk_io else 0,
            'write_count': disk_io.write_count if disk_io else 0
        }
        
    def _get_process_metrics(self) -> Dict:
        """Get process metrics."""
        processes = []
        marka_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                process_info = proc.info
                if 'marka' in process_info['name'].lower():
                    marka_count += 1
                    
                processes.append({
                    'pid': process_info['pid'],
                    'name': process_info['name'],
                    'cpu': process_info['cpu_percent'],
                    'memory': process_info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return {
            'total': len(processes),
            'marka': marka_count,
            'list': processes[:50]  # Return first 50 processes
        }
        
    def get_network_info(self) -> Dict:
        """Get network information."""
        try:
            interfaces = []
            io_counters = psutil.net_io_counters(pernic=True)
            
            for name, stats in io_counters.items():
                addresses = []
                try:
                    addrs = psutil.net_if_addrs().get(name, [])
                    for addr in addrs:
                        addresses.append({
                            'family': addr.family.name,
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                except Exception:
                    pass
                    
                interfaces.append({
                    'name': name,
                    'addresses': addresses,
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv,
                    'packets_sent': stats.packets_sent,
                    'packets_recv': stats.packets_recv
                })
                
            return {
                'interfaces': interfaces,
                'total_bytes_sent': sum(i.bytes_sent for i in io_counters.values()),
                'total_bytes_recv': sum(i.bytes_recv for i in io_counters.values())
            }
        except Exception as e:
            self.logger.error(f'Failed to get network info: {str(e)}')
            raise
            
    def get_battery_info(self) -> Dict:
        """Get battery information."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {
                    'has_battery': False,
                    'is_charging': False,
                    'percent': 0,
                    'remaining': None
                }
                
            return {
                'has_battery': True,
                'is_charging': battery.power_plugged,
                'percent': battery.percent,
                'remaining': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }
        except Exception as e:
            self.logger.error(f'Failed to get battery info: {str(e)}')
            return {
                'has_battery': False,
                'is_charging': False,
                'percent': 0,
                'remaining': None
            }
            
    def get_temperature_info(self) -> Dict:
        """Get temperature information."""
        try:
            temps = psutil.sensors_temperatures()
            core_temps = []
            
            if 'coretemp' in temps:
                for entry in temps['coretemp']:
                    if 'Core' in entry.label:
                        core_temps.append(entry.current)
                        
            return {
                'core_temps': core_temps,
                'max_temp': max(core_temps) if core_temps else None
            }
        except Exception as e:
            self.logger.error(f'Failed to get temperature info: {str(e)}')
            return {
                'core_temps': [],
                'max_temp': None
            }
            
    def get_gpu_info(self) -> List[Dict]:
        """Get GPU information."""
        try:
            gpus = GPUtil.getGPUs()
            return [{
                'id': gpu.id,
                'name': gpu.name,
                'load': gpu.load * 100,
                'memory_total': gpu.memoryTotal,
                'memory_used': gpu.memoryUsed,
                'memory_free': gpu.memoryFree,
                'temperature': gpu.temperature
            } for gpu in gpus]
        except Exception as e:
            self.logger.error(f'Failed to get GPU info: {str(e)}')
            return []
            
    def get_load_history(self) -> Dict:
        """Get historical load metrics."""
        return {
            'cpu': list(self.metrics_history['cpu']),
            'memory': list(self.metrics_history['memory']),
            'disk': list(self.metrics_history['disk'])
        }
        
    def get_active_alerts(self) -> List[Dict]:
        """Get active alerts."""
        return [alert.__dict__ for alert in self.alerts]
        
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        
    def run_command(self, command: str) -> Tuple[str, str]:
        """Run a system command and return output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Command failed: {command} - {str(e)}')
            return e.stdout, e.stderr
            
    def get_system_logs(self, lines: int = 100) -> List[str]:
        """Get system logs."""
        try:
            if platform.system() == 'Windows':
                command = f'powershell -command "Get-EventLog -LogName Application -Newest {lines} | Format-Table -AutoSize"'
            else:
                command = f'tail -n {lines} /var/log/syslog'
                
            stdout, _ = self.run_command(command)
            return stdout.splitlines()
        except Exception as e:
            self.logger.error(f'Failed to get system logs: {str(e)}')
            return []