const fs = require('fs-extra');
const path = require('path');
const log = require('electron-log');

class FileManager {
  /**
   * Initializes the FileManager instance with the given base directory.
   *
   * The base directory is where all the files are saved and read from. If
   * not given, it defaults to a directory in the same directory as the
   * script.
   *
   * @param {string} [baseDir] - The base directory for the FileManager.
   */
  constructor(baseDir) {
    this.baseDir = baseDir || path.join(__dirname, '../../files');
    fs.ensureDirSync(this.baseDir);
  }

  /**
   * Saves the given content to the given file name.
   *
   * If the file already exists, it will be overwritten.
   *
   * @param {string} filename - The filename to save the file as.
   * @param {string} content - The content to save to the file.
   * @returns {Promise<string>} A promise that resolves with the full path of the saved file.
   */
  async saveFile(filename, content) {
    const filePath = path.join(this.baseDir, filename);
    await fs.writeFile(filePath, content);
    log.info(`File saved at ${filePath}`);
    return filePath;
  }

  /**
   * Reads the content of a file with the given filename.
   *
   * Checks if the file exists in the base directory, and if it does, reads and returns
   * its content as a UTF-8 encoded string. Throws an error if the file is not found.
   *
   * @param {string} filename - The name of the file to read.
   * @returns {Promise<string>} A promise that resolves with the file content as a string.
   * @throws {Error} If the file is not found.
   */

  async readFile(filename) {
    const filePath = path.join(this.baseDir, filename);
    if (!(await fs.pathExists(filePath))) {
      throw new Error('File not found');
    }
    return fs.readFile(filePath, 'utf8');
  }

  /**
   * Deletes a file with the given filename.
   *
   * Checks if the file exists in the base directory, and if it does, deletes it.
   * Throws an error if the file is not found.
   *
   * @param {string} filename - The name of the file to delete.
   * @throws {Error} If the file is not found.
   */
  async deleteFile(filename) {
    const filePath = path.join(this.baseDir, filename);
    await fs.remove(filePath);
    log.info(`File deleted: ${filePath}`);
  }
}

module.exports = FileManager;
