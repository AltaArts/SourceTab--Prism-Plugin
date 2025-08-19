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

- Source:
    - Source Directory is added to Source Panel
    - for Each File:
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
    - Checked File Tile's Mainfile are copied in parallel (up to max workers [default is 5])

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














## **Source Browser**






<br>

## **File Tiles**

![FileTile Overview](DocsImages/FileTile_overview.png)

Each file is represented by a File Tile.  This is aimed to quickly display each file and its relevant information.

<br>

### **Details**
![FileTile Details](DocsImages/FileTile_details.png)<br>
File Tiles have additional functionality and Tooltips

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

[**Installation**](Doc-Installation.md)

[**Settings**](Doc-Settings.md)

[**Proxys**](Doc-Proxys.md)

[**File Naming**](Doc-FileNaming.md)

[**Metadata**](Doc-Metadata.md)
