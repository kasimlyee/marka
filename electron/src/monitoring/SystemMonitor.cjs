const os = require('os');
const log = require('electron-log');

class SystemMonitor {
  /**
   * Retrieves detailed system information.
   *
   * @returns {Object} An object containing the system's platform, OS release,
   * total memory, free memory, number of CPU cores, CPU model, and uptime.
   * - `platform`: The operating system platform.
   * - `release`: The OS release version.
   * - `totalMemory`: The total system memory in gigabytes.
   * - `freeMemory`: The available system memory in gigabytes.
   * - `cpuCores`: The number of CPU cores.
   * - `cpuModel`: The model of the CPU.
   * - `uptime`: The system uptime in hours.
   */

  getSystemInfo() {
    return {
      platform: os.platform(),
      release: os.release(),
      totalMemory: `${(os.totalmem() / (1024 * 1024 * 1024)).toFixed(2)} GB`,
      freeMemory: `${(os.freemem() / (1024 * 1024 * 1024)).toFixed(2)} GB`,
      cpuCores: os.cpus().length,
      cpuModel: os.cpus()[0].model,
      uptime: `${(os.uptime() / 3600).toFixed(2)} hrs`
    };
  }

  /**
   * Logs the current system health to the console.
   *
   * @returns {Object} The system health information.
   */
  logSystemHealth() {
    const info = this.getSystemInfo();
    log.info('System Info:', info);
    return info;
  }
}

module.exports = SystemMonitor;
