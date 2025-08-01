const os = require('os');
const process = require('process');
const log = require('electron-log');
const { exec } = require('child_process');
const { promisify } = require('util');
const si = require('systeminformation');
const { EventEmitter } = require('events');

const execAsync = promisify(exec);

class SystemMonitor extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = {
      monitoringInterval: 5000,
      maxHistory: 60,
      cpuThreshold: 80,
      memoryThreshold: 80,
      diskThreshold: 90,
      ...options
    };

    this.monitoringInterval = null;
    this.metricsHistory = {
      cpu: [],
      memory: [],
      disk: []
    };
    this.alerts = [];
    this.systemInfo = null;
  }

  /**
   * Starts system monitoring
   */
  async start() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    // Get initial system info
    this.systemInfo = await this.getSystemInfo();

    // Start monitoring loop
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics().catch(error => {
        log.error('Metrics collection failed:', error);
      });
    }, this.options.monitoringInterval);

    log.info('System monitoring started');
  }

  /**
   * Stops system monitoring
   */
  stop() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    log.info('System monitoring stopped');
  }

  /**
   * Collects system metrics
   */
  async collectMetrics() {
    try {
      const metrics = await this.getPerformanceMetrics();
      
      // Store in history
      this.storeMetric('cpu', metrics.cpu.usage);
      this.storeMetric('memory', metrics.memory.usage);
      this.storeMetric('disk', metrics.disk.usage);

      // Check thresholds
      this.checkThresholds(metrics);

      // Emit metrics
      this.emit('metrics', metrics);
    } catch (error) {
      log.error('Failed to collect metrics:', error);
      throw error;
    }
  }

  storeMetric(type, value) {
    this.metricsHistory[type].push({
      timestamp: Date.now(),
      value
    });

    // Trim history
    if (this.metricsHistory[type].length > this.options.maxHistory) {
      this.metricsHistory[type].shift();
    }
  }

  checkThresholds(metrics) {
    const now = new Date().toISOString();

    // CPU threshold check
    if (metrics.cpu.usage > this.options.cpuThreshold) {
      const alert = {
        type: 'cpu',
        level: 'warning',
        message: `High CPU usage: ${metrics.cpu.usage}%`,
        timestamp: now
      };
      this.addAlert(alert);
      this.emit('alert', alert);
    }

    // Memory threshold check
    if (metrics.memory.usage > this.options.memoryThreshold) {
      const alert = {
        type: 'memory',
        level: 'warning',
        message: `High memory usage: ${metrics.memory.usage}%`,
        timestamp: now
      };
      this.addAlert(alert);
      this.emit('alert', alert);
    }

    // Disk threshold check
    if (metrics.disk.usage > this.options.diskThreshold) {
      const alert = {
        type: 'disk',
        level: 'warning',
        message: `High disk usage: ${metrics.disk.usage}%`,
        timestamp: now
      };
      this.addAlert(alert);
      this.emit('alert', alert);
    }
  }

  addAlert(alert) {
    this.alerts.push(alert);
    
    // Keep only the last 100 alerts
    if (this.alerts.length > 100) {
      this.alerts.shift();
    }
  }

  /**
   * Gets system information
   * @returns {Promise<Object>}
   */
  async getSystemInfo() {
    try {
      const [cpuInfo, memInfo, osInfo, diskInfo] = await Promise.all([
        si.cpu(),
        si.mem(),
        si.osInfo(),
        si.fsSize()
      ]);

      return {
        cpu: {
          manufacturer: cpuInfo.manufacturer,
          brand: cpuInfo.brand,
          cores: cpuInfo.cores,
          speed: cpuInfo.speed
        },
        memory: {
          total: memInfo.total,
          unit: 'bytes'
        },
        os: {
          platform: osInfo.platform,
          distro: osInfo.distro,
          release: osInfo.release,
          arch: osInfo.arch
        },
        disk: diskInfo.map(disk => ({
          fs: disk.fs,
          size: disk.size,
          used: disk.used,
          mount: disk.mount
        })),
        nodeVersion: process.version,
        electronVersion: process.versions.electron,
        hostname: os.hostname(),
        uptime: os.uptime()
      };
    } catch (error) {
      log.error('Failed to get system info:', error);
      throw error;
    }
  }

  /**
   * Gets performance metrics
   * @returns {Promise<Object>}
   */
  async getPerformanceMetrics() {
    try {
      const [cpuUsage, memUsage, diskUsage, processes] = await Promise.all([
        si.currentLoad(),
        si.mem(),
        si.fsSize(),
        si.processes()
      ]);

      // Find Marka processes
      const markaProcesses = processes.list.filter(proc => 
        proc.command.includes('Marka') || 
        proc.command.includes('electron')
      );

      return {
        cpu: {
          usage: cpuUsage.currentLoad.toFixed(1),
          user: cpuUsage.currentLoadUser.toFixed(1),
          system: cpuUsage.currentLoadSystem.toFixed(1),
          idle: cpuUsage.currentLoadIdle.toFixed(1)
        },
        memory: {
          total: memUsage.total,
          free: memUsage.free,
          used: memUsage.used,
          active: memUsage.active,
          usage: ((memUsage.used / memUsage.total) * 100).toFixed(1)
        },
        disk: {
          total: diskUsage[0]?.size || 0,
          used: diskUsage[0]?.used || 0,
          free: diskUsage[0]?.available || 0,
          usage: diskUsage[0]?.use || 0
        },
        processes: {
          total: processes.all,
          running: processes.running,
          blocked: processes.blocked,
          sleeping: processes.sleeping,
          marka: markaProcesses.length
        },
        uptime: os.uptime(),
        timestamp: Date.now()
      };
    } catch (error) {
      log.error('Failed to get performance metrics:', error);
      throw error;
    }
  }

  /**
   * Gets network information
   * @returns {Promise<Object>}
   */
  async getNetworkInfo() {
    try {
      const [networkInterfaces, networkStats] = await Promise.all([
        si.networkInterfaces(),
        si.networkStats()
      ]);

      return {
        interfaces: networkInterfaces.map(iface => ({
          name: iface.iface,
          ip4: iface.ip4,
          ip6: iface.ip6,
          mac: iface.mac,
          speed: iface.speed
        })),
        stats: networkStats.map(stat => ({
          name: stat.iface,
          rx: stat.rx_sec,
          tx: stat.tx_sec
        }))
      };
    } catch (error) {
      log.error('Failed to get network info:', error);
      throw error;
    }
  }

  /**
   * Gets battery information
   * @returns {Promise<Object>}
   */
  async getBatteryInfo() {
    try {
      const battery = await si.battery();
      return {
        hasBattery: battery.hasBattery,
        isCharging: battery.isCharging,
        level: battery.percent,
        remaining: battery.timeRemaining
      };
    } catch (error) {
      log.error('Failed to get battery info:', error);
      return {
        hasBattery: false,
        isCharging: false,
        level: 0,
        remaining: 0
      };
    }
  }

  /**
   * Gets system load history
   * @returns {Object}
   */
  getLoadHistory() {
    return {
      cpu: this.metricsHistory.cpu,
      memory: this.metricsHistory.memory,
      disk: this.metricsHistory.disk
    };
  }

  /**
   * Gets active alerts
   * @returns {Array<Object>}
   */
  getActiveAlerts() {
    return this.alerts;
  }

  /**
   * Clears all alerts
   */
  clearAlerts() {
    this.alerts = [];
  }

  /**
   * Runs a system command
   * @param {string} command Command to run
   * @returns {Promise<{stdout: string, stderr: string}>}
   */
  async runCommand(command) {
    try {
      return await execAsync(command);
    } catch (error) {
      log.error(`Command failed: ${command}`, error);
      throw error;
    }
  }

  /**
   * Gets system temperature information
   * @returns {Promise<Object>}
   */
  async getTemperatureInfo() {
    try {
      const temps = await si.cpuTemperature();
      return {
        main: temps.main,
        cores: temps.cores,
        max: temps.max
      };
    } catch (error) {
      log.error('Failed to get temperature info:', error);
      return {
        main: 0,
        cores: [],
        max: 0
      };
    }
  }

  /**
   * Gets detailed process information
   * @returns {Promise<Array<Object>>}
   */
  async getProcessDetails() {
    try {
      const processes = await si.processes();
      return processes.list.map(proc => ({
        pid: proc.pid,
        name: proc.name,
        command: proc.command,
        cpu: proc.cpu,
        memory: proc.mem,
        priority: proc.priority,
        started: proc.started
      }));
    } catch (error) {
      log.error('Failed to get process details:', error);
      throw error;
    }
  }

  /**
   * Gets system logs
   * @param {number} [lines=100] Number of lines to retrieve
   * @returns {Promise<Array<string>>}
   */
  async getSystemLogs(lines = 100) {
    try {
      let command;
      if (process.platform === 'win32') {
        command = `powershell -command "Get-EventLog -LogName Application -Newest ${lines} | Format-Table -AutoSize"`;
      } else {
        command = `tail -n ${lines} /var/log/syslog`;
      }

      const { stdout } = await this.runCommand(command);
      return stdout.split('\n').filter(line => line.trim());
    } catch (error) {
      log.error('Failed to get system logs:', error);
      return [];
    }
  }
}

module.exports = SystemMonitor;