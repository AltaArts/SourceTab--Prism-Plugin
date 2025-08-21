# **Interface**

<br>

## **Quick Index**

[**Source Browser**](#source-browser)<br>
[**File Tile**](#file-tiles)<br>
[**Preview Player**](#preview-viewer)<br>
[**Functions Panel**](#functions-panel)<br>
[**Transfer Popup**](#transfer-popup)<br>
[**Transfer Report**](#transfer-report)<br>
[**Sidecar Files**](#sidecar-files)<br>
[**Drag / Drop**](#drag--drop)<br>
[**Keyboard Shortcuts**](#keyboard-shortcuts-hotkeys)<br>



<br>

## **Basic Transfer Flow**
This is a simple overview of a typical transfer job:
- Source:
    - Source Directory is added to Source Panel
    - then each File is:
        - Scanned to get its details (frames, size, etc) and Metadata
        - Hashed for future reference.
        - Scanned for a associated Proxy
        - Thumbnail generated
        - A File Tile is constructed and displayed in the Source Panel

- Destination:
    - Destination Directory is added to Destination Panel
    - Desired Files added from Source to Destination
    - Files to be transferred checked

- Functions Panel:
    - Proxy Handling configured
    - File Naming configured
    - Metadata configured

- Transfer is Initiated with the *Start Transfer* button
    - All Checked File Tiles are put in Queue for transfer 
    - Checked File Tile's Mainfile are copied in parallel (up to max workers [default is 6])

- After Mainfile transfer is complete:
    - The transferred file is hashed
    - Source and Destination's file's hashes are compared
    - If Source Proxy exists it is added to the transfer queue (if applicable), or
    - Proxy generation job is added to the queue (if applicable)

- After the Proxy is complete, its hash is compared (if applicable)

- After all File's have been completed
    - Transfer Report is generated (if enabled)
    - Metadata Sidecar file(s) are generated (if enabled)
    - Complete sound and popup are displayed (if enabled)

<br>



## **Source Browser**

![SourceBrowser Overview](DocsImages/sourceBrowser_overview.png)

The main window is the SourceBrowser in the "Source" tab.  The SourceTab plugin will add the tab to the main Prism Project Browser top bar, in the position set in the [**Settings**](Doc-Settings.md/#sourcetab-project-settings).

There are 4 main panels that make up the SourceBrowser:
- **Source List:**  displays all the files in the Source Directory.  
- **Destination List:** holds added File Tiles for transfer.
- **Preview Player:** plays the selected media for review.
- **Functions Panel:** transfer-specific configuration options.

### **Icons**

![Help Icon](DocsImages/sourceBrowser_icon_help.png) **Help:**  Hovering will display quick details.  Clicking will open the Web Browser to the SourceTab Documentation on GitHub.<br>
![Up Dir Icon](DocsImages/sourceBrowser_icon_up.png) **Up:** go up one directory level.<br>
![Explorer Icon](DocsImages/sourceBrowser_icon_explorer.png) **Explorer:** open the File Explorer to select the directory (or optionally in the Destination side will open the Libraries popup to choose a directory).<br>
![Refresh Icon](DocsImages/sourceBrowser_icon_refresh.png) **Refresh:** reload the File Tiles.<br>
![Sort Icon](DocsImages/sourceBrowser_icon_sort.png) **Sorting:** open the Sorting Menu for the list.<br>
![Frames Icon](DocsImages/sourceBrowser_icon_frames.png) **Frames Display:** toggle frames/duration display in the File Tile.<br>
![Filter Icon](DocsImages/sourceBrowser_icon_filters.png) **Filters:** enables filtering of File Tiles. Click to toggle enabled, right-click for the Filters Menu.<br>
![Sequences Icon](DocsImages/sourceBrowser_icon_seqs.png) **Group Sequences:** toggle grouping of image sequences into one File Tile.




<br>

## **File Tiles**

![FileTile Overview](DocsImages/FileTile_overview.png)

Each file is represented by a File Tile.  This is aimed to quickly display each file and its relevant information.  File Tiles contain the file's information and have additional functionality (**see below**).

File Tiles can be added from the Source to the Destination by several ways including [**Drag/Drop**](#drag--drop), [**Keyboard Shortcuts**](Doc-Interface.md/#keyboard-shortcuts-hotkeys), and through the [**Right-click Menu**](#right-click-menu).

<br>

### **Details**
File Tiles have additional functionality and Tooltips to help in quick viewing and handling.

![FileTile Details](DocsImages/FileTile_details.png)<br>

<br>

### **Right-click Menu**

![FileTile RCL Source](DocsImages/FileTile_rclMenu_source.png)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
![FileTile RCL Dest](DocsImages/FileTile_rclMenu_dest.png)


(see [**Shortcuts**](#keyboard-shortcuts-hotkeys) below)





## **Preview Viewer**

![Preview Player](DocsImages/PreviewPlayer_overview.png)

### **Right-click Menu**

![Preview Player - RCL Menu](DocsImages/PreviewPlayer_rclMenu.png)



## **Functions Panel**

![Functions Panel](DocsImages/functsPanel.png)

![Main Progress - Transferring](DocsImages/mainProg_transferring.png)

![Main Progress - Complete](DocsImages/mainProg_complete.png)







## **Transfer Popup**

![Transfer Popup](DocsImages/transferPopup.png)



## **Transfer Report**

![Transfer Report](DocsImages/transferReport_pg1.png)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
![Transfer Report](DocsImages/transferReport_pg2.png)




## **Sidecar Files**




## **Drag / Drop**

![Drag/Drop Single](DocsImages/dragDrop_single.png)

![Drag/Drop Multi](DocsImages/dragDrop_multi.png)

![Drag/Drop Player](DocsImages/dragDrop_player.png)


## **Keyboard Shortcuts (Hotkeys)**


<br>

___
jump to:

[**Table of Contents / Index**](Doc-Docs_TOC.md)<br>

[**Installation**](Doc-Installation.md)<br>
[**Settings**](Doc-Settings.md)<br>
[**Proxys**](Doc-Proxys.md)<br>
[**File Naming**](Doc-FileNaming.md)<br>
[**Metadata**](Doc-Metadata.md)<br>
