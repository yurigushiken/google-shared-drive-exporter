# Google Workspace Shared Drive Backup Script

This script allows you to export all files from a Google Workspace Shared Drive to your local machine. As of November 2024, there is currently no way to backup or export Shared Drive content using Google Takeout or by right-clicking and downloading the files, due to errors such as files being too large, file names containing strange characters, or file names being too long. This program was written to address these challenges.

![Run Script GIF](https://github.com/yurigushiken/google-shared-drive-exporter/blob/main/images/YouCut_20241115_174925804_1.gif?raw=true)

**Use Case:** If you have a Shared Drive with tens of thousands of files and need to update them, but encounter errors when trying to download from within the browser, this script provides a reliable solution to back up your data.

## Improvements in This Project

- **Enhanced Filename Sanitization:**
  - Removes additional special characters.
  - Limits filenames to 50 characters.
  - Ensures cleaner, compatible filenames to prevent errors during downloads.

- **Path Length Handling:**
  - Truncates folder and file names to avoid issues with excessively long paths.

- **File Size Verification:**
  - Checks file size in addition to file existence to prevent re-downloading incomplete or unchanged files.

- **Improved Handling of Google-native Formats:**
  - Provides specific messages for files that exceed export size limits.
  - Suggests alternative actions for problematic files.

- **Optimized Duplicate File Avoidance:**
  - Compares file names and sizes more effectively to avoid duplicates.

- **Enhanced Error Handling:**
  - Incorporates specific messages for issues like export size limits.
  - Logs errors and continues the backup process without interruption.

## Step-by-Step Instructions for Setting Up and Running the Google Drive Backup Script

### 1. Prerequisites

Before you start, ensure the following:

- **Python Installed:** Python 3.6 or higher installed on your system. You can download it from [python.org](https://www.python.org/downloads/).

- **Google Cloud Project:** Access to the [Google Cloud Console](https://console.cloud.google.com/) to enable the Google Drive API and create credentials.

- **GitHub Repository:** Download this script from the repository.

- **Required Python Libraries:**
  - Install libraries using:
    ```bash
    pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
    ```

### 2. Setting Up Google Cloud Project

#### Step 2.1: Create a New Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click on the project dropdown in the top-left corner.
3. Select **New Project** and provide a name (e.g., `DriveBackupProject`).
4. Click **Create**.

#### Step 2.2: Enable the Google Drive API

1. In your project, navigate to **APIs & Services > Library**.
2. Search for **Google Drive API** and click on it.
3. Click **Enable**.

#### Step 2.3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. You may need to configure the OAuth consent screen:
   - Select **External** for testing purposes.
   - Add an app name under **App Information** (e.g., `Drive Backup`).
   - Add your email in the **User Support Email** field.
   - Add `https://www.googleapis.com/auth/drive` as a scope.
   - Save and continue.
4. After configuring the OAuth screen, return to **Create Credentials > OAuth client ID**.
   - Set the application type to **Desktop app**.
   - Click **Create**.
5. Download the `client_secret.json` file and place it in the same directory as the script.

### 3. Preparing the Script

#### Step 3.1: Clone or Download the GitHub Repository

1. Visit the repository: **[GitHub Link](https://github.com/yourusername/your-repo-name)**.
2. Download the repository as a ZIP file or clone it using:
   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   ```
3. Navigate to the folder containing the script:
   ```bash
   cd your-repo-name
   ```

#### Step 3.2: Install Python Libraries
Run the following command in the terminal to install dependencies:
```bash
pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

#### Step 3.3: Update the Script

1. Place the `client_secret.json` file in the same folder as the `script.py` file.
2. Set Your Shared Drive ID:
   - Open the script (`script.py`) in a text editor.
   - Locate the line:
     ```python
     shared_drive_id = 'YOUR_SHARED_DRIVE_ID'  # Replace with your Shared Drive ID
     ```
   - Replace 'YOUR_SHARED_DRIVE_ID' with the ID of your Shared Drive.
   - You can find the Shared Drive ID in the URL of the drive:
     `https://drive.google.com/drive/u/0/folders/{SHARED_DRIVE_ID}`
3. Ensure the Local Path for Backups is Correctly Set:
   - Update the base_path and local_path variables in the script to point to your desired backup directory.
     ```python
     base_path = "E:/"  # Replace with your preferred base directory
     local_path = os.path.join(base_path, "GoogleDriveBackup")
     ```

### 4. Running the Script

1. Open a terminal (or command prompt) and navigate to the script folder.
2. Run the script:
   ```bash
   python script.py
   ```
3. A browser window will open, asking you to log in and authorize access.
4. After authorizing, the script will begin downloading files to your specified local directory.

### 5. Common Errors and Fixes

**Error: "Path Too Long"**
- Cause: Windows path length exceeds 260 characters.
- Fix: The script truncates folder and file names to avoid this issue.

**Error: "Invalid Characters in File Name"**
- Cause: Some file names contain invalid characters (<, >, :, etc.).
- Fix: The script automatically removes or replaces invalid characters.

**Error: "File Too Large to Export"**
- Cause: Google-native files exceed export size limits.
- Fix: The script logs the error and continues with the next file.

**Error: "File Not Found"**
- Cause: The file was deleted, moved, or inaccessible.
- Fix: The script logs the error and continues with the next file.

### 6. Verifying Progress

- The script skips files that already exist and haven't changed since the last backup.
- If the script is interrupted, you can re-run it to continue from where it left off.
- Backup reports are generated after each run in the reports directory.

### 7. Troubleshooting

- **Log Files:** Review the backup reports in the reports directory for details on skipped or failed files.
- **Permissions:** Ensure you have the correct permissions for all files in the Shared Drive.
- **Google API Quota:** If you hit Google API quota limits, wait for the quota to reset (usually 24 hours).

_Note: This script has been tested on Windows 11._
